#!/usr/bin/env python3
"""The live board: the one status format every check-in prints, as text or as the HTML fragment the board page embeds.

usage: live_board.py [--html]

LIVE BOARD header (repo, local time, version, health), then Issues (only what is open now, a stuck worker first, each with its
fix in plain words), Running goals (10-cell bar with percent and time left, the step flow with done steps ticked and the current
step in brackets, the worker: its session name or background, each recorded step's depth, one next step), Queued goals, Dependencies (arrows between running and queued goals) and one Finish time.
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


def load(root):
    folder = os.path.join(os.path.abspath(os.path.join(root, bs.git("rev-parse", "--git-common-dir", cwd=root))), "loop", "runs")
    runs = [bs.read_json(os.path.join(folder, name)) for name in sorted(os.listdir(folder)) if name.endswith(".json")] if os.path.isdir(folder) else []
    return [run for run in runs if isinstance(run, dict) and run.get("slug") and run.get("status") != "retired"]


def current(run):
    """Index of the step a goal is on: a finished, unmerged goal waits at release."""
    if run.get("status") == "done":
        return FLOW.index("release")
    return FLOW.index(run["step"]) if run.get("step") in FLOW else 0


def flow_line(run):
    here = current(run)
    return " > ".join("[%s]" % step if i == here else step + "✓" if i < here else step for i, step in enumerate(FLOW))


def next_line(run):
    text = plain((run.get("report") or {}).get("text") or run.get("next") or "", 120)
    if text:
        return text
    here = current(run)
    if run.get("status") == "waiting":
        return "answer the question under Issues"
    return "merge the pull request" if run.get("status") == "done" else "finish %s, then %s" % (FLOW[here], FLOW[min(here + 1, len(FLOW) - 1)])


def worker_of(run):
    """Which worker has the goal: its app session by name, or a background process (the fallback) and why."""
    if run.get("worker") == "session" or run.get("session"):
        return "session %s" % ((run.get("session") or {}).get("name") or "worker · " + run["slug"])
    return "background" + (" (%s)" % plain(run["worker_why"], 80) if run.get("worker_why") else "")


def depth_of(run, setting):
    """Each recorded step's depth, in flow order, and the current review_depth setting."""
    got = run.get("depth") if isinstance(run.get("depth"), dict) else {}
    done = ", ".join("%s %s" % (step, got[step]) for step in FLOW if step in got)
    return "%s (setting %s)" % (done or "none recorded yet", setting)


def issues(runs, gone, root, at=None):
    stuck, other = [], []
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
        if at and run.get("worker") == "session" and run.get("status") == "running" and last and (at - last).total_seconds() >= QUIET:
            name = (run.get("session") or {}).get("name") or "worker · " + run["slug"]
            other += ["- %s: its session %s has sent nothing for %dm" % (run["slug"], name, (at - last).total_seconds() // 60),
                      '    fix: look at the session %s; when it answers, record it with sessions.py report %s' % (name, run["slug"])]
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
    states = bs.pr_states(runs, root)
    gone = {r["slug"] for r in runs if graph.merged(r) or states.get(r["slug"]) == "MERGED"}
    shut = {r["slug"] for r in runs if r["slug"] not in gone and states.get(r["slug"]) == "CLOSED"}
    live = [r for r in runs if r["slug"] not in gone | shut]
    running = [r for r in live if r.get("status") in ("running", "waiting", "done")]
    waits = lambda deps: [d for d in deps if d not in gone]
    queue = bs.queued(root, runs)
    items = [dict(slug=r["slug"], mark=status_graph.mark(r.get("status")), depends=waits(r.get("waits_on") or []), stage=0,
                  left=bs.left_time(r, runs, at)) for r in live]
    items += [dict(slug=g["slug"], mark="queued", depends=waits(g["depends"]), stage=0,
                   left=bs.left_time({"slug": g["slug"], "status": "queued"}, runs, at)) for g in queue]
    names = {item["slug"] for item in items}
    setting = "condensed" if (bs.read_json(os.path.join(root, ".loop", "config.json")) or {}).get("review_depth") == "condensed" else "full"
    out = ["LIVE BOARD  %s  %s  %s  health: %s" % (os.path.basename(root), graph.clock(at), version(root), health(root)), "", "Issues"]
    out += issues([r for r in runs if r["slug"] not in shut], gone, root, at) + ["", "Running goals"]
    for run in running:
        done = current(run)
        full = round(10 * done / len(FLOW))
        left = next(i["left"] for i in items if i["slug"] == run["slug"])
        out += ["- %s  [%s%s] %d%%  %s" % (run["slug"], "#" * full, "-" * (10 - full), round(100 * done / len(FLOW)),
                                         "no estimate yet" if left is None else "%s left" % status_graph.span(left)),
                "    " + flow_line(run), "    worker: " + worker_of(run), "    depth: " + depth_of(run, setting), "    next: " + next_line(run)]
    out += ([] if running else ["- (none)"]) + ["", "Queued goals"]
    for goal in queue:
        left = next(i["left"] for i in items if i["slug"] == goal["slug"])
        out.append("- %s  %s%s" % (goal["slug"], "no estimate yet" if left is None else "%s left" % status_graph.span(left),
                                   "  waits on " + ", ".join(waits(goal["depends"])) if waits(goal["depends"]) else ""))
    out += ([] if queue else ["- (none)"]) + ["", "Dependencies"]
    edges = ["%s --> %s" % (dep, item["slug"]) for item in items for dep in item["depends"] if dep in names]
    out += edges or ["- (none)"]
    seconds, _, _ = status_graph.chain(items)
    missing = status_graph.unknown(items)
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
