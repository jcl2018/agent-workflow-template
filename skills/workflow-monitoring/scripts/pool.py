#!/usr/bin/env python3
"""The session pool (MON-12) and the clean-up after a goal (MON-6): idle worker sessions kept ready, sized by
`pool_size` in .loop/config.json (default 20).

usage: pool.py <command> [options]

  status              pool: F free, B busy, T total (target N)
  need                how many sessions to create now (K) and the one action that does it; K is 0 unless the pool runs
                      low (fewer free sessions than ready goals), then K = pool_size - total (every missing session)
  add ID [ID ...]     register sessions the operation session just created with the app, as free (POOLED)
  decline             the owner said "no pool": hide the ask until K grows past today's K (cleared once K is 0)
  return SLUG         a goal ended: its sessions go back to the pool, or are marked archive when the total is above
                      pool_size (the check-in tells the operation session to archive them with the app); a merged
                      goal's worktree and loop/SLUG branch are removed (a dirty worktree is kept and named)

Only the desktop app can create, rename or archive a session, so this script records and asks; the operation session
acts. The pool file is <git common dir>/loop/session-pool.json (sessions.py owns its lock). A malformed entry is set
aside in session-pool.bad.json and named under Issues; the rest of the pool keeps working (issue 122).
Attempt identity (issue 114): each bind raises the run's `attempt`; a report that names an older attempt is recorded but
not applied (attempt_ok). A freed session keeps who it was freed from in `history`, so a reuse never loses it.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import graph  # noqa: E402
import board_lines as prs  # noqa: E402  (its pull request lookups)
import sessions as se  # noqa: E402
os.environ.update(GIT_TERMINAL_PROMPT="0", GH_PROMPT_DISABLED="1", GIT_EDITOR="true", GIT_ASKPASS="true", SSH_ASKPASS="true")  # no prompt ever blocks

DEFAULT_SIZE = 20


def config():
    top = se.git("rev-parse", "--show-toplevel")
    return se.read(os.path.join(top, ".loop", "config.json"), {}) if top else {}


def size_of(cfg):
    try:
        return max(1, int(cfg.get("pool_size") or DEFAULT_SIZE))
    except (TypeError, ValueError):
        return DEFAULT_SIZE


def counts(found):
    entries = [item for item in found.values() if isinstance(item, dict) and item.get("state") in ("free", "busy")]
    free = sum(item["state"] == "free" for item in entries)
    return free, len(entries) - free, len(entries)


def status_line(found, cfg):
    free, busy, total = counts(found)
    return "pool: %d free, %d busy, %d total (target %d)" % (free, busy, total, size_of(cfg))


def board_line(found, root):
    """The pool line under the live board's Running goals; '' if it can't be built (the board never fails for it)."""
    try:
        return status_line(found, se.read(os.path.join(root, ".loop", "config.json"), {}))
    except Exception:
        return ""


def side_path():
    return os.path.join(se.base(), "pool.json")


def need(found, cfg, ready):
    """(K, declined): K sessions to create now. The pool runs low when free sessions are fewer than ready goals; then
    every missing session (pool_size - total) is created in one step. K never takes the total past pool_size."""
    free, _, total = counts(found)
    k = max(size_of(cfg) - total, 0) if free < ready else 0
    if k and graph.memory_room() == 0:  # under min_free_memory_gb of free commit memory no session is created: nothing starts
        k = 0
    side = se.read(side_path(), {})
    declined = side.get("declined")
    if k == 0 and declined is not None:
        side.pop("declined")
        se.write(side_path(), side)
        declined = None
    return k, isinstance(declined, int) and k <= declined


def ask_lines(found, cfg, ready):
    """The Needs you lines for the pool: the fill ask, or a ready goal's wait when the pool is full or declined."""
    k, declined = need(found, cfg, ready)
    free, busy, total = counts(found)
    if k and not declined:
        return ['- the session pool is low: %d free for %d ready goal%s; create %d session%s?' % (
            free, ready, "" if ready == 1 else "s", k, "" if k == 1 else "s"),
            '    fix: type "fill pool" (the operation session creates all %d in one step, then pool.py add ID ...) or "no pool"' % k]
    if ready > free:
        why = "pool full (%d of %d busy)" % (busy, size_of(cfg)) if not k else "pool fill declined"
        return ["- %d ready goal%s wait for a session: %s" % (ready - free, "" if ready - free == 1 else "s", why),
                '    fix: free a session (sessions.py free SLUG), raise pool_size, or type "fill pool"']
    return []


def attempt_ok(state, attempt):
    """False when a report names an attempt older than the run's own: a late report from an old worker."""
    try:
        return attempt in (None, "") or int(attempt) >= int(state.get("attempt") or 0)
    except (TypeError, ValueError):
        return True


def stale(state, args):
    """sessions.py report's guards: refuse a --recommend that isn't one of --words; record, not apply, a report from an
    older attempt. True when the report is fully handled here."""
    if args.attempt not in (None, "") and not str(args.attempt).isdigit():
        sys.exit("REFUSED: --attempt %r is not a number. Fix: pass the attempt the WORKER line named; nothing was changed." % args.attempt)
    if args.recommend and args.recommend not in args.words:
        sys.exit("REFUSED: --recommend %r is not one of --words. Fix: pass it as a --words too; nothing was changed." % args.recommend)
    if attempt_ok(state, args.attempt):
        return False
    state.setdefault("reports", []).append({"at": se.now(), "step": args.step or "-", "status": "stale", "text": "attempt %s" % args.attempt})
    se.save(state, "report from old attempt %s recorded, not applied (the run is on attempt %s)" % (args.attempt, state.get("attempt")))
    return True


def remember(item, slug):
    """Keep who a session was freed from across reuse."""
    item.setdefault("history", []).append({"slug": slug, "at": se.now()})
    del item["history"][:-10]


def quarantine():
    """Move malformed entries graph.read_pool set aside into session-pool.bad.json; their keys, or []."""
    bad = graph.LAST_BAD.pop(se.pool_path(), {})
    if bad:
        path = os.path.join(se.base(), "session-pool.bad.json")
        kept = se.read(path, {})
        kept.update(bad)
        se.write(path, kept)
    return sorted(bad)


def remove_tree(slug, state):
    """The merged goal's worktree (never forced) and branch; what was done, one line each."""
    said, tree = [], state.get("worktree") or ""
    common = os.path.realpath(os.path.join(se.base(), ".."))
    listed = subprocess.run(["git", "worktree", "list", "--porcelain"], capture_output=True, text=True).stdout.splitlines()
    main = next((line[9:] for line in listed if line.startswith("worktree ")), "")
    if main and os.path.isdir(main):  # every git call runs from the main checkout: the worker may be standing in the tree
        os.chdir(main)
    if tree and os.path.isdir(tree) and os.path.realpath(tree).startswith(os.path.join(common, "loop", "worktrees") + os.sep):
        done = subprocess.run(["git", "worktree", "remove", tree], capture_output=True, text=True)
        said.append("removed worktree %s" % os.path.basename(tree) if done.returncode == 0 else
                    "KEPT worktree %s: %s" % (os.path.basename(tree), (done.stderr.strip().splitlines() or ["git refused"])[-1]))
    branch, base = "loop/" + slug, config().get("base") or "main"
    if se.git("rev-parse", "--verify", "--quiet", "refs/heads/" + branch):
        try:
            subprocess.run(["git", "fetch", "-q", "origin"], capture_output=True, timeout=60)
        except (OSError, subprocess.SubprocessError):
            pass  # an offline fetch: decide on the origin we have
        base = "origin/" + base if se.git("rev-parse", "--verify", "--quiet", "origin/" + base) else base
        inside = subprocess.run(["git", "merge-base", "--is-ancestor", "refs/heads/" + branch, base], capture_output=True).returncode == 0
        done = subprocess.run(["git", "branch", "-D", branch], capture_output=True, text=True) if inside else None
        said.append("deleted branch %s" % branch if done and done.returncode == 0 else
                    "KEPT branch %s: %s" % (branch, "it has commits not in %s" % base if not inside else "checked out somewhere"))
    return said


def return_session(slug, merged=False):
    """Give the goal's busy sessions back (free, or archive above pool_size); on a merge also remove its tree."""
    cfg, said, state = config(), [], se.load(slug)
    merged = merged or bool(state.get("pr") and prs.state(state["pr"], se.git("rev-parse", "--show-toplevel") or ".") == "MERGED")
    with se.locked():
        found = se.pool()
        for sid, item in sorted(found.items()):
            if item.get("slug") == slug and item.get("state") == "busy":
                _, _, total = counts(found)
                item["state"] = "archive" if total > size_of(cfg) else "free"
                if merged:  # a merged goal is over: block a rebind to it; a failed one may take the same session back
                    item.update(freed_from=slug, freed_at=se.now())
                remember(item, slug)
                said.append("%s session %s" % ("ARCHIVE" if item["state"] == "archive" else "POOLED", item.get("name") or sid))
        se.save_pool(found)
    if merged:
        said += remove_tree(slug, state)  # only once GitHub says merged: an open pull request keeps its tree
    return said


def cmd_status(args):
    found = se.pool()
    print(status_line(found, config()))
    archive = [item.get("name") or sid for sid, item in found.items() if item.get("state") == "archive"]
    if archive:
        print("ARCHIVE: " + ", ".join(sorted(archive)) + " (archive with the app, then sessions.py list drops them)")
    return 0


def cmd_need(args):
    found, cfg = se.pool(), config()
    k, declined = need(found, cfg, args.ready)
    print("NEED %d%s" % (k, " (declined)" if declined else ""))
    for line in ask_lines(found, cfg, args.ready):
        print(line)
    return 0


def cmd_add(args):
    with se.locked():
        found = se.pool()
        for sid in args.ids:
            if found.get(sid, {}).get("state") == "busy":
                sys.exit("REFUSED: session %s is busy with %s; nothing was added." % (sid, found[sid].get("slug")))
        new = [sid for sid in dict.fromkeys(args.ids) if (found.get(sid) or {}).get("state") != "free"]
        for sid in new:
            found[sid] = dict(found.get(sid) or {}, name=found.get(sid, {}).get("name") or "worker · idle", state="free", since=se.now())
        se.save_pool(found)
        print("POOLED %d session(s); %s" % (len(new), status_line(found, config())))
    return 0


def cmd_decline(args):
    k, _ = need(se.pool(), config(), args.ready)
    side = se.read(side_path(), {})
    side["declined"] = k
    se.write(side_path(), side)
    print("DECLINED %d: the pool ask stays hidden until more than %d sessions are missing" % (k, k))
    return 0


def cmd_return(args):
    se.bad_slug(args.slug)
    state = se.load(args.slug)
    merged = graph.merged(state) or (state.get("report") or {}).get("status") == "merged"
    for line in return_session(args.slug, merged) or ["NOTHING TO RETURN for %s" % args.slug]:
        print(line)
    return 0


# The pr queue (#3877): goal.py pr asks here. Goals at pr take turns per repo, so main can't move under a running pr lane, and a try
# lost to main moving has its own cap. graph.pr_queue(op, ...) forwards here (graph.py is at its size budget).
def pr_turn(runs, slug):
    """Join the repo's queue (one file per goal in <loop>/pr-queue holding its joining time; asking again keeps the place and
    refreshes the file). Returns "" when it is slug's turn, else the goal ahead. A goal whose run is no longer running or waiting,
    or no longer at the pr step (it failed a try or opened its PR), or whose file is older than LOOP_MERGE_LOCK_SECONDS (1800), loses its place."""
    folder = os.path.join(os.path.dirname(runs), "pr-queue")
    os.makedirs(folder, exist_ok=True)
    mine = os.path.join(folder, slug)
    if not os.path.exists(mine):
        with open(mine, "w") as handle:
            handle.write(str(time.time_ns()))
    os.utime(mine)
    line = []
    for name in os.listdir(folder):
        path = os.path.join(folder, name)
        try:
            joined, age = int(open(path).read()), time.time() - os.path.getmtime(path)
            if name != slug and (age > int(os.environ.get("LOOP_MERGE_LOCK_SECONDS") or 1800) or
                                 (run := se.read(os.path.join(runs, name + ".json"), {})).get("status") not in graph.LIVE or run.get("step") not in ("checks", "pr")):
                os.unlink(path)
                continue
            line.append((joined, name))
        except (OSError, ValueError):
            continue
    return min(line)[1] if line and min(line)[1] != slug else ""


def pr_ahead(runs, base):
    """True when origin/<base> holds commits this branch lacks: main moved since the last merge of it."""
    subprocess.run(["git", "fetch", "origin", base], capture_output=True)
    return subprocess.run(["git", "merge-base", "--is-ancestor", "origin/" + base, "HEAD"], capture_output=True).returncode != 0


def pr_moved(runs, g, state, why, fix):
    """A try lost to main moving (a conflict with it, or a lane that failed while it moved) is not the goal's fault: it counts
    in state["moved"], capped by max_moved (default 5), and leaves tries and max_tries alone. Past the cap it counts as a try."""
    state["moved"] = state.get("moved", 0) + 1
    most = int(g.config().get("max_moved") or 5)
    if state["moved"] > most:
        g.failed_try(state, why, "build", fix)
        return True
    state["step"] = "build"
    g.save(state, "main moved, try not counted (%d of %d)" % (state["moved"], most))
    print("TRY NOT COUNTED (main moved: %d of %d; past %d it counts): %s\nNEXT: %s" % (state["moved"], most, most, why, fix))
    return True


# The goal's defect-test check (E-10), moved here from fit.py to keep it under its size budget: fit.owed calls pr_owed.
VERB = r"\b(?:fix(?:es|ed)?|close[sd]?|resolve[sd]?)\s+"
SEEN = re.compile(r"\d{4}-\d{2}-\d{2}$")  # seen_red counts only as a date
FIXES = re.compile(VERB + r"(?:issue\s+)?#(\d+)|" + VERB + r"finding:([a-z0-9][a-z0-9-]*)", re.I)


def _rows(root):
    try:
        with open(os.path.join(root, ".loop", "regression.tsv")) as handle:
            cells = [line.rstrip("\n").split("\t") + [""] * 8 for line in handle if line.strip() and line[0] != "#"]
    except OSError:
        return []
    return [(c[0], c[2], c[4], c[7]) for c in cells if c[6] == "defect"]


def _has(link, ref):
    return re.search(r"(?:issues/|#)%s\b" % re.escape(ref), link) if ref.isdigit() else re.search(r"finding:%s(?![\w-])" % re.escape(ref), link)


def _before(root):
    try:
        with open(os.path.join(root, ".loop", "config.json")) as handle:
            base = json.load(handle).get("base") or "main"
    except (OSError, ValueError):
        base = "main"
    git = lambda *a: subprocess.run(("git",) + a, cwd=root, capture_output=True, text=True, env=dict(os.environ, LC_ALL="C"))
    found = next((x for x in (git("merge-base", "HEAD", ref).stdout.strip() for ref in ("origin/" + base, base)) if x), "")
    shown = git("show", found + ":.loop/regression.tsv") if found else None
    if not shown or shown.returncode and "exists on disk" not in shown.stderr and "does not exist" not in shown.stderr:
        return None
    return {c[0]: (c + [""] * 5)[4] for c in (line.split("\t") for line in shown.stdout.splitlines()) if c[0][:1] not in ("", "#")}


def pr_owed(runs, root, text):
    owe, old = [], _before(root)
    for number, finding in FIXES.findall(text):
        ref = number or finding.lower()
        if not any(SEEN.match(seen) and _has(link, ref) and (old is None or old.get(name) != seen)
                   and subprocess.run(command, shell=True, cwd=root, capture_output=True).returncode == 0
                   for name, command, seen, link in _rows(root)):
            owe.append(("#" if number else "finding ") + ref)
    return owe


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status")
    for name in ("need", "decline"):
        item = sub.add_parser(name)
        item.add_argument("--ready", type=int, default=0, help="ready goals waiting for a session")
    item = sub.add_parser("add")
    item.add_argument("ids", nargs="+")
    item = sub.add_parser("return")
    item.add_argument("slug")
    args = parser.parse_args()
    try:
        return {"status": cmd_status, "need": cmd_need, "add": cmd_add, "decline": cmd_decline, "return": cmd_return}[args.cmd](args)
    except se.PoolUnreadable as error:
        sys.exit("REFUSED: " + graph.pool_fix(error))


if __name__ == "__main__":
    sys.exit(main())
