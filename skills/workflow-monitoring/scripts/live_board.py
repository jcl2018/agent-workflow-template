#!/usr/bin/env python3
"""The live board: the one status format every check-in prints, as text or as the HTML fragment the board page embeds.

usage: live_board.py [--html]

LIVE BOARD header (repo, local time, version, health), then Issues (only what is open now, a stuck worker first, each with its
fix in plain words), Running goals (10-cell bar with percent, time left and the try count, the step flow with done steps ticked
and the current step in brackets, the worker: its session name or background, one next step; a goal a session was handed
before it was frozen shows as [freezing]), Queued goals (held goals among them, marked held: running, but no worker has
them), Dependencies (arrows between running and queued goals) and one Finish time. The session pool is read with
graph.read_pool; when it can't be read, nothing is called held or freezing and Issues says so.
Merged work, history and totals are left out. Estimates and the finish come from board_status.py and status_graph.py.
Health is workflow-health's verdict, or "unknown"; LOOP_BOARD_HEALTH replaces it (tests). Imported by board_status.py.
"""
import argparse
import datetime
import html
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import board_status as bs  # noqa: E402
import graph  # noqa: E402
import status_graph  # noqa: E402

# No terminal, no waiting: a prompt from git or gh must fail, not block (board_status sets the rest).
os.environ.setdefault("GIT_TERMINAL_PROMPT", "0")

FLOW = ("idea", "plan", "build", "review", "qa", "ship", "pr", "release")
QUIET = int(os.environ.get("LOOP_SESSION_QUIET", "3600"))  # seconds a worker session may stay silent before Issues names it
HEALTH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "workflow-health", "scripts", "health.py")


def plain(text, size=200):
    """One line with every local path cut to its last name (URLs stay)."""
    words = []
    for word in str(text or "").split():
        core = word.strip("`'\".,;:()")
        if "://" not in core and re.match(r"^(/|~|\.{1,2}/|\.git|\.loop)", core):
            word = word.replace(core, core.rstrip("/").rsplit("/", 1)[-1])
        words.append(word)
    return " ".join(words)[:size]


def health(root):
    if os.environ.get("LOOP_BOARD_HEALTH"):
        return os.environ["LOOP_BOARD_HEALTH"]
    try:
        done = subprocess.run([sys.executable, HEALTH, "check"], cwd=root, capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return "unknown"
    found = re.search(r"^HEALTH: (not green|green)", done.stdout, re.M)
    return found.group(1) if found else "unknown"


def version(root):
    cfg = bs.read_json(os.path.join(root, ".loop", "config.json")) or {}
    try:
        with open(os.path.join(root, cfg.get("version_file") or "VERSION")) as handle:
            return "v" + handle.read().strip()
    except OSError:
        return "unknown"


def loop_dir(root):
    return os.path.join(os.path.abspath(os.path.join(root, bs.git("rev-parse", "--git-common-dir", cwd=root))), "loop")


def load(root):
    folder = os.path.join(loop_dir(root), "runs")
    runs = [bs.read_json(os.path.join(folder, name)) for name in sorted(os.listdir(folder)) if name.endswith(".json")] if os.path.isdir(folder) else []
    return [run for run in runs if isinstance(run, dict) and run.get("slug") and run.get("status") != "retired"]


def run_files(root):
    """Every goal with a run file on disk, retired ones included: a busy pool entry for one of these is not freezing."""
    folder = os.path.join(loop_dir(root), "runs")
    return {name[:-5] for name in os.listdir(folder) if name.endswith(".json")} if os.path.isdir(folder) else set()


def parse_at(text):
    """A recorded time as an aware UTC datetime (naive counts as UTC), or None when it is missing or bad."""
    try:
        found = datetime.datetime.fromisoformat(str(text).replace("Z", "+00:00"))
    except ValueError:
        return None
    return found if found.tzinfo else found.replace(tzinfo=datetime.timezone.utc)


def age(text, at):
    """How long ago a recorded time was: Nm under an hour, Nh under two days, else Nd; '' when the time is unknown."""
    then = parse_at(text)
    if not then or not at:
        return ""
    minutes = max(0, int((at - then).total_seconds() // 60))
    return "%dm" % minutes if minutes < 60 else "%dh" % (minutes // 60) if minutes < 48 * 60 else "%dd" % (minutes // 1440)


def current(run):
    """Index of the step a goal is on: a finished, unmerged goal waits at release. A step outside the flow (a check,
    say) keeps the last known flow step: the newest report naming one, else the furthest step in the run's flow record."""
    if run.get("status") == "done":
        return FLOW.index("release")
    if run.get("step") in FLOW:
        return FLOW.index(run["step"])
    for item in reversed(run.get("reports") or []):
        if isinstance(item, dict) and item.get("step") in FLOW:
            return FLOW.index(item["step"])
    known = [FLOW.index(step) for step in (run.get("flow") or {}) if step in FLOW]
    return max(known) if known else 0


def flow_line(run):
    if run.get("status") == "freezing":
        return " > ".join(("[freezing]",) + FLOW)
    here = current(run)
    return " > ".join("[%s]" % step if i == here else step + "✓" if i < here else step for i, step in enumerate(FLOW))


def latest_report(run):
    """The newer of the run's report and its last session report (a tie or a missing time: the last report), unless it
    is older than the run's bound_at, when a new worker took the goal."""
    report = run.get("report") if isinstance(run.get("report"), dict) else {}
    last = (run.get("reports") or [{}])[-1]
    last = last if isinstance(last, dict) else {}
    when, then = parse_at(report.get("at")), parse_at(last.get("at"))
    pick = report if report.get("text") and (not last.get("text") or (when and then and when > then)) else last
    bound, said = parse_at(run.get("bound_at")), parse_at(pick.get("at"))
    return "" if bound and said and said < bound else pick.get("text") or ""


def next_line(run):
    if run.get("status") == "done":
        return plain((run.get("report") or {}).get("text") or "merge the pull request", 120)
    text = plain(latest_report(run) or run.get("next") or "", 120)
    if text:
        return text
    if run.get("status") == "waiting":
        return "answer the question under Issues"
    here = current(run)
    return "finish release" if here == len(FLOW) - 1 else "finish %s, then %s" % (FLOW[here], FLOW[here + 1])


def worker_of(run, taken=None):
    """Which worker has the goal: its app session by name (from the run, or the pool), or a background process and why."""
    if run.get("worker") == "session" or run.get("session"):
        return "session %s" % ((run.get("session") or {}).get("name") or "worker · " + run["slug"])
    if taken and run["slug"] in taken:
        return "session %s" % (taken[run["slug"]].get("name") or taken[run["slug"]]["id"])
    return "background" + (" (%s)" % plain(run["worker_why"], 80) if run.get("worker_why") else "")


def is_held(run, taken):
    """Running with no worker: the pool is known, no busy session names it, and it has no pid (a dead pid is watch's)."""
    return run.get("status") == "running" and taken is not None and run["slug"] not in taken and not run.get("pid")


def tries(run, most):
    done = run.get("tries") or 0
    if not isinstance(done, int) or done <= 0:
        return ""
    return "  try %d of %d" % (done + 1, most) if done < most else "  tries used up (%d of %d)" % (done, most)


def max_tries(root):
    try:
        return max(1, int((bs.read_json(os.path.join(root, ".loop", "config.json")) or {}).get("max_tries") or 3))
    except (TypeError, ValueError):
        return 3


def issues(runs, gone, root, at=None, taken=None, why="", freezing=()):
    stuck, other = [], []
    if why:
        other += ["- the session pool can't be read (%s)" % plain(why, 120),
                  "    fix: check it with python3 -m json.tool <git common dir>/loop/session-pool.json, then repair it or move it "
                  "aside; nothing was started or changed, and the next pass retries"]
    for run in runs:
        slug, report = run["slug"], (run.get("report") or {}).get("text", "")
        if run.get("status") in bs.ASKING:
            ask = run.get("waiting") or {}
            words = ask.get("words") or ["resume " + slug]
            stuck.append("- %s is %s: %s" % (slug, run["status"], plain(ask.get("ask") or report or run.get("finding") or "see its log")))
            stuck.append("    fix: answer by typing %s" % " or ".join('"%s"' % w for w in words))
        if run.get("release_error") and bs.error_open(run, gone, "release failed"):
            other += ["- %s: the release failed: %s" % (slug, plain(run["release_error"])), '    fix: look at the problem, then type "resume %s"' % slug]
    for run in runs:
        try:
            last = datetime.datetime.fromisoformat(str(run.get("updated")).replace("Z", "+00:00"))
        except ValueError:
            last = None
        quiet = bool(at and last and (at - last).total_seconds() >= QUIET)
        if quiet and is_held(run, taken) and graph.holds_slot(run):
            other += ["- %s: held %s and holds a slot" % (run["slug"], age(run.get("updated"), at)),
                      "    fix: give it a session with sessions.py bind %s ID, or, once its old session has stopped, "
                      "sessions.py free %s to give the slot back" % (run["slug"], run["slug"])]
        elif quiet and run.get("worker") == "session" and run.get("status") == "running" and not is_held(run, taken):
            name = (run.get("session") or {}).get("name") or "worker · " + run["slug"]
            other += ["- %s: its session %s has sent nothing for %dm" % (run["slug"], name, (at - last).total_seconds() // 60),
                      '    fix: look at the session %s; when it answers, record it with sessions.py report %s' % (name, run["slug"])]
    for entry in freezing:
        since = parse_at(entry.get("since"))
        if at and since and (at - since).total_seconds() >= QUIET:
            name = entry.get("name") or entry["id"]
            other += ["- %s: assigned to session %s %s ago and still not frozen" % (entry["slug"], name, age(entry["since"], at)),
                      "    fix: look at the session %s; once it has stopped, drop the assignment with sessions.py free %s"
                      % (name, entry["slug"])]
    found = bs.wiki_check(root)
    parts = ["%s %s" % (kind.lower(), page) for kind, page in found or []]
    for run in runs:
        if run.get("wiki_error") and bs.error_open(run, gone, "wiki not published") and (
                found is None or not re.search(r"(?:^page |\b[A-Z]{3,} )[A-Z][\w-]*[: ]", " ".join(str(run["wiki_error"]).split()))):
            parts.append("saved: " + plain(run["wiki_error"], 120))
    if parts:
        other += ["- wiki pages are out of date: %s" % "; ".join(dict.fromkeys(parts)), "    fix: bring those wiki pages up to date, then run the docs audit"]
    return stuck + other or ["- (none)"]


def render(root=None, at=None):
    root = root or bs.git("rev-parse", "--show-toplevel")
    at = at or datetime.datetime.now(datetime.timezone.utc)
    runs = load(root)
    pool, why = graph.read_pool(os.path.join(loop_dir(root), "session-pool.json"))
    taken = graph.assigned(pool)
    on_disk = run_files(root)
    freezing = [dict(entry, slug=slug) for slug, entry in sorted((taken or {}).items()) if slug not in on_disk]
    states = bs.pr_states(runs, root)
    gone = {r["slug"] for r in runs if graph.merged(r) or states.get(r["slug"]) == "MERGED"}
    shut = {r["slug"] for r in runs if r["slug"] not in gone and states.get(r["slug"]) == "CLOSED"}
    live = [r for r in runs if r["slug"] not in gone | shut]
    held = [r for r in live if is_held(r, taken)]
    running = [r for r in live if r.get("status") in ("running", "waiting", "done") and r not in held]
    waits = lambda deps: [d for d in deps if d not in gone]
    lines = {g["slug"]: g for g in bs.queued(root, runs)}
    queue = [g for g in lines.values() if g["slug"] not in {f["slug"] for f in freezing}]
    items = [dict(slug=r["slug"], mark=status_graph.mark(r.get("status")), depends=waits(r.get("waits_on") or []), stage=0,
                  left=bs.left_time(r, runs, at)) for r in live]
    items += [dict(slug=g["slug"], mark="queued", depends=waits(g["depends"]), stage=0,
                   left=bs.left_time({"slug": g["slug"], "status": "queued"}, runs, at)) for g in queue]
    items += [dict(slug=f["slug"], mark=status_graph.mark("running"), depends=waits((lines.get(f["slug"]) or {}).get("depends") or []),
                   stage=0, left=bs.left_time({"slug": f["slug"], "status": "queued"}, runs, at)) for f in freezing]
    names = {item["slug"] for item in items}
    out = ["LIVE BOARD  %s  %s  %s  health: %s" % (os.path.basename(root), graph.clock(at), version(root), health(root)), "", "Issues"]
    out += issues([r for r in runs if r["slug"] not in shut], gone, root, at, taken, why, freezing) + ["", "Running goals"]
    most = max_tries(root)
    bar = lambda run, done, end="": "- %s  [%s%s] %d%%  %s%s%s" % (
        run["slug"], "#" * round(10 * done / len(FLOW)), "-" * (10 - round(10 * done / len(FLOW))), round(100 * done / len(FLOW)),
        "no estimate yet" if left_of(run) is None else "%s left" % status_graph.span(left_of(run)), tries(run, most), end)
    left_of = lambda run: next(i["left"] for i in items if i["slug"] == run["slug"])
    for run in running:
        out += [bar(run, current(run)), "    " + flow_line(run), "    worker: " + worker_of(run, taken), "    next: " + next_line(run)]
    for entry in freezing:
        name, ago = entry.get("name") or entry["id"], age(entry.get("since"), at)
        out += [bar(dict(entry, status="freezing"), 0), "    " + flow_line({"status": "freezing"}), "    worker: session " + name,
                "    next: the worker freezes it (goal.py new %s --here in its worktree), binds again, then idea%s"
                % (entry["slug"], " (assigned %s ago)" % ago if ago else "")]
    out += ([] if running or freezing else ["- (none)"]) + ["", "Queued goals"]
    for run in held:
        tree = run.get("worktree") and os.path.isdir(run["worktree"])
        ago = age(run.get("updated"), at)
        state = ", ".join(x for x in ("held", "last change %s ago" % ago if ago else "", "worktree kept" if tree else "worktree gone",
                                       "holds a slot" if graph.holds_slot(run) else "") if x)
        fix = "" if tree else "; make its worktree again first (git worktree add <common>/loop/worktrees/%s loop/%s)" % (run["slug"], run["slug"])
        out += [bar(run, current(run), "  held"), "    " + flow_line(run), "    worker: none (%s)" % state,
                "    next: give it a worker session (sessions.py bind %s ID, where ID is the session's id from the app)%s" % (run["slug"], fix)]
    for goal in queue:
        left = next(i["left"] for i in items if i["slug"] == goal["slug"])
        out.append("- %s  %s%s" % (goal["slug"], "no estimate yet" if left is None else "%s left" % status_graph.span(left),
                                   "  waits on " + ", ".join(waits(goal["depends"])) if waits(goal["depends"]) else ""))
    out += ([] if queue or held else ["- (none)"]) + ["", "Dependencies"]
    edges = ["%s --> %s" % (dep, item["slug"]) for item in items for dep in item["depends"] if dep in names]
    out += edges or ["- (none)"]
    seconds, _, _ = status_graph.chain(items)
    missing = status_graph.unknown(items) or held or freezing
    finish = "nothing left" if not items else "no estimate yet" if not seconds else "%sfinish about %s" % (
        "at least " if missing else "", graph.clock(at + datetime.timedelta(seconds=seconds)))
    return out + ["", "Finish", finish]


def fragment(lines):
    return "<section><pre>%s</pre></section>" % html.escape("\n".join(lines))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--html", action="store_true")
    args = parser.parse_args()
    lines = render()
    sys.stdout.write(fragment(lines) if args.html else "\n".join(lines) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
