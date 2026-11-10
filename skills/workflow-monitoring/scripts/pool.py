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
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import graph  # noqa: E402
import prs  # noqa: E402
import sessions as se  # noqa: E402

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
        for sid in args.ids:
            found[sid] = dict(found.get(sid) or {}, name=found.get(sid, {}).get("name") or "worker · idle", state="free", since=se.now())
        se.save_pool(found)
        print("POOLED %d session(s); %s" % (len(args.ids), status_line(found, config())))
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
