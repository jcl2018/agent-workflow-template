#!/usr/bin/env python3
"""The check-in (MON-4, MON-5): what operate.py prints each pass instead of the live board, in the one layout the reply
hook checks. The board itself prints only for `report`, `dashboard` and "where do things stand".

usage: checkin.py [--since ISO]

  headline        one line: how many goals run, wait on you or are queued, and the session pool
  All sessions    one table row per live goal: session, repo, what it is for, status, progress, time left, latest
  Re-plan         what replan.py changed since the last check-in, each with its reason (MON-10)
  Auto-answered   what auto.py answered or sent to you since the last check-in, with the words that revert it (MON-11)
  Dependencies    one block per repo of the pod, headed `== name ==` (MON-14), each board_lines' top-to-bottom graph; a
                  `repo/slug` in depends-on is listed under `Between repos`; the legend prints once
  Needs you       numbered: questions with their options and the recommended answer, stuck goals by cause, workers
                  silent past silent_minutes (MON-8), the pool ask (MON-12), sessions to archive, kept worktrees;
                  or "Nothing needs you"
  Coming up       the next expected step of each goal and what the owner will need to do

--since defaults to the last check-in time in <git common dir>/loop/checkin.json. Read-only.
"""
import argparse
import datetime
import os
import re
import sys
import textwrap

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import auto  # noqa: E402
import board as bd  # noqa: E402
import board_status as bs  # noqa: E402
import board_lines  # noqa: E402
import govern_hook  # noqa: E402
import graph  # noqa: E402
import live_board as lb  # noqa: E402
import pool as pl  # noqa: E402
import replan  # noqa: E402
import board_page  # noqa: E402

MARK = {"running": "running", "held": "holding", "waiting": "waiting", "failed": "stuck", "stopped": "stuck",
        "silent": "silent", "done": "awaiting merge", "queued": "queued"}


def cell(text, size=48):
    return lb.plain(text, size).replace("|", "/") or "-"


def gather(root, at, stamp=None):
    """One repo's state, read from its own .loop: name, root, cfg, folder, runs, found, why, taken, states, live, queue."""
    folder, cfg = lb.loop_dir(root), bs.read_json(os.path.join(root, ".loop", "config.json")) or {}
    runs = lb.load(root)
    found, why = graph.read_pool(os.path.join(folder, "session-pool.json"))
    taken = graph.assigned(found)
    states = {r["slug"]: graph.classify(r, taken, at, cfg) for r in runs}
    live = [r for r in runs if states[r["slug"]] not in ("merged", "retired")]
    return dict(name=os.path.basename(root), root=root, cfg=cfg, folder=folder, runs=runs, found=found, why=why, taken=taken,
                states=states, live=live, queue=bs.queued(root, runs))


def grouped(blocks):
    """The Dependencies section: [(repo name, items)] as one `== name ==` block per repo (MON-14), then `Between repos`
    for each `repo/slug` dependency, then the legend once. Every line is wrapped at board_lines.WIDTH."""
    out, edges, marks = [], [], {}
    for name, items in blocks:
        marks[name] = {item["slug"]: item.get("mark") for item in items}
    for name, items in blocks:
        local = [dict(item, depends=[d for d in item.get("depends") or [] if "/" not in d]) for item in items]
        out += ["== %s ==" % (name if len(name) <= 54 else name[:51] + "...")]
        out += board_lines.render(local)[:-2] if items else ["- (none)"]
        edges += [(name, item["slug"], dep.partition("/")[0], dep.partition("/")[2]) for item in items
                  for dep in item.get("depends") or [] if "/" in dep]
    if edges:
        out += ["Between repos"]
        for name, slug, repo, goal in edges:
            mark = marks.get(repo, {}).get(goal, 0)
            out.append("%s/%s <- %s/%s %s" % (name, slug, repo, goal, "(unknown)" if mark == 0 else "[%s]" % board_lines.MARKS.get(mark, " ")))
    out += ["", board_lines.LEGEND]
    return [row for line in out for row in (textwrap.wrap(line, board_lines.WIDTH, subsequent_indent="    ") or [""])]


def expected(root=None, at=None):
    """[(repo name, slug)] of every goal the Dependencies section must draw: each live goal and each queued line of the
    pod, read from the run records and queue files. The reply hook (missing, below) checks a reply against it."""
    root = bs.git("rev-parse", "--show-toplevel", cwd=root or None) or root
    at = at or datetime.datetime.now(datetime.timezone.utc)
    pod, here = [gather(root, at)], os.getcwd()
    os.chdir(root)  # bd.followed() starts from the working directory
    try:
        followed = bd.followed()
    finally:
        os.chdir(here)
    for name, path, _ in followed:
        if os.path.realpath(path) != os.path.realpath(root):
            try:
                pod.append(gather(path, at))
            except Exception:  # one unreadable repo never hides the others
                continue
    return [(g["name"], item["slug"]) for g in pod for item in g["live"] + g["queue"]]


def render(root=None, at=None, stamp=None):
    root = root or bs.git("rev-parse", "--show-toplevel")
    at = at or datetime.datetime.now(datetime.timezone.utc)
    mine = gather(root, at)
    folder, cfg, runs, found, why, taken, states, live, queue = (mine[k] for k in (
        "folder", "cfg", "runs", "found", "why", "taken", "states", "live", "queue"))
    stamp = stamp or (bs.read_json(os.path.join(folder, "checkin.json")) or {}).get("at") or "0000"
    others, broken = [], []
    for name, path, _ in bd.followed():
        if os.path.realpath(path) != os.path.realpath(root):
            try:
                others.append(gather(path, at))
            except Exception as error:  # one unreadable repo never hides the others
                broken.append((name, lb.plain(type(error).__name__, 40)))
    pod = [mine] + others
    ready, _ = graph.ready(queue, {r["slug"]: r for r in runs}, graph.parallel_of(cfg), taken, why)
    counts = lambda *names: sum(g["states"][r["slug"]] in names for g in pod for r in g["live"] if not graph.foreign(r))
    pool_line = pl.status_line(found or {}, cfg) if found is not None else "pool: unreadable"
    out = ["%d running, %d waiting on you, %d queued; %s" % (counts("running", "held", "silent"),
                                                            counts("waiting", "failed", "stopped"), sum(len(g["queue"]) for g in pod), pool_line), "",
           "All sessions", "| session | repo | for | status | progress | left | latest |", "|---|---|---|---|---|---|---|"]
    for g in pod:
        for run in g["live"]:
            step = lb.current(run)
            left = bs.left_time(run, g["runs"], at)
            out.append("| %s | %s | %s | %s | %s %d/8 | %s | %s |" % (
                cell(lb.worker_of(run, g["taken"]), 30), g["name"], cell(run.get("goal"), 40), MARK.get(g["states"][run["slug"]], g["states"][run["slug"]]),
                lb.FLOW[step], step + 1, "?" if left is None else board_page.span(left), cell(lb.latest_report(run) or run.get("next"), 60)))
    if not any(g["live"] for g in pod):
        out.append("| - | %s | nothing running | - | - | - | - |" % mine["name"])
    changes = replan.since(root, stamp)
    decided = auto.since(root, stamp)
    open_now = replan.open_proposals(root)
    if changes or open_now:
        out += ["", "Re-plan (since the last check-in, then proposals still open):"] + ["- " + line[21:] for line in changes[-8:]]
        out += ["- open: %s" % line for line in open_now if not any(line in c for c in changes)][:6]
    if decided:
        out += ["", "Auto-answered (full auto):"]
        for line in decided[-8:]:
            parts = [p.strip() for p in line.split(" | ")]
            if len(parts) >= 6 and parts[2] == "AUTO":
                out.append('- %s: "%s" -> %s; revert: operate.py send %s "<other words>"' % (parts[1], parts[3][:60], parts[4], parts[1]))
            elif len(parts) >= 6:
                out.append("- %s waits for you: %s" % (parts[1], parts[5]))
    blocks = []
    for g in pod:
        items = [dict(slug=r["slug"], mark=g["states"][r["slug"]] if g["states"][r["slug"]] != "done" else "awaiting merge",
                      depends=[d for d in r.get("waits_on") or []], owner=graph.foreign(r)) for r in g["live"]]
        blocks.append((g["name"], items + [dict(slug=q["slug"], mark="queued", depends=q["depends"]) for q in g["queue"]]))
    out += ["", "Dependencies"] + grouped(blocks) + ["", "Needs you"]
    needs, readonly = [], []
    for run in live:
        state, ask = states[run["slug"]], run.get("waiting") or {}
        if graph.foreign(run):  # another pod's goal: shown, never a question for this pod
            readonly += ["- %s asks (owned by %s, read-only here)" % (run["slug"], graph.foreign(run))] * (state == "waiting")
        elif state == "waiting":
            words = ask.get("words") or ["go on " + run["slug"]]
            rec = ask.get("recommend") or words[0]
            needs.append("%s asks: %s; options: %s; recommended: %s" % (run["slug"], lb.plain(ask.get("ask"), 160),
                                                                       " / ".join('"%s"' % w for w in words), rec))
        elif state == "silent":
            needs.append("%s: its worker has sent nothing for %dm; look at its session" % (
                run["slug"], graph.silent_for(run, at) // 60))
        elif state == "held":
            needs.append("%s is held with no worker; give it a session (sessions.py bind %s ID)" % (run["slug"], run["slug"]))
    stuck = board_lines.stuck(live, cfg.get("resume_on_limit") is True)
    needs += [" ".join(line.split()) for line in stuck if line.startswith("- ")]
    if found is not None:
        needs += [line[2:] for line in pl.ask_lines(found, cfg, len(ready)) if line.startswith("- ")]
        needs += ["archive session %s with the app (pool above pool_size)" % (item.get("name") or sid)
                  for sid, item in sorted(found.items()) if item.get("state") == "archive"]
    elif why:
        needs.append(graph.pool_fix(why))
    for sid, item in sorted((found or {}).items()):  # a retired goal's session still busy holds a slot nobody sees (122)
        old = bs.read_json(os.path.join(folder, "runs", "%s.json" % item.get("slug"))) if item.get("state") == "busy" else None
        if isinstance(old, dict) and old.get("status") == "retired":
            needs.append("%s is retired but session %s is still busy; free it with pool.py return %s" % (
                old["slug"], item.get("name") or sid, old["slug"]))
    if os.path.exists(os.path.join(folder, "session-pool.bad.json")):
        needs.append("malformed session-pool entries were set aside in session-pool.bad.json; look and delete it")
    if os.path.exists(os.path.join(root, ".loop", "config.json")) and bs.read_json(os.path.join(root, ".loop", "config.json")) is None:
        needs.append(".loop/config.json can't be read, so every setting is at its default; fix the JSON (python3 -m json.tool)")
    _, fails, cause = govern_hook.health(os.path.dirname(folder))
    if fails:
        needs.append("the govern hook let %d call(s) through on an error (last: %s); fix it, then check govern-hook.log"
                     % (fails, lb.plain(cause, 80)))
    for g in others:
        for run in g["live"]:
            ask = run.get("waiting") or {}
            if graph.foreign(run) and g["states"][run["slug"]] == "waiting":
                readonly.append("- %s/%s asks (owned by %s, read-only here)" % (g["name"], run["slug"], graph.foreign(run)))
            elif g["states"][run["slug"]] == "waiting" and not graph.foreign(run):
                needs.append("%s/%s asks: %s; options: %s" % (g["name"], run["slug"], lb.plain(ask.get("ask"), 160),
                                                              " / ".join('"%s"' % w for w in ask.get("words") or ["go on"])))
    needs += ["%s: can't be read (%s); the other repos are shown" % item for item in broken]
    out += ["%d. %s" % (i, text) for i, text in enumerate(needs, 1)] or ["Nothing needs you"]
    out += readonly
    out += ["", "Coming up"]
    for run in live:
        if states[run["slug"]] == "done":
            out.append("- %s: its pull request waits for merge (you: review %s)" % (run["slug"], run.get("pr") or "it"))
        elif states[run["slug"]] in ("running", "silent", "held"):
            out.append("- %s: %s" % (run["slug"], lb.next_line(run)))
    paused = board_lines.paused(live)
    out.append("- " + (paused or "next check-in in %s minutes" % (cfg.get("cadence") or 30)))
    return lb.fit(out, 100)


HEAD = re.compile(r"^[\s>#*_`-]*([A-Za-z ]+?)[\s:*_`]*(?:\(\d+\))?\s*$")
NEXT = ("needs you", "coming up")


def body(text):
    """The text of the Dependencies section, fences included, or None when the reply has none."""
    lines, start = str(text or "").splitlines(), None
    for i, line in enumerate(lines):
        name = (HEAD.match(line) or [None, ""])[1].strip().lower()
        if start is None and name == "dependencies":
            start = i + 1
        elif start is not None and name in NEXT:
            return "\n".join(lines[start:i])
    return None if start is None else "\n".join(lines[start:])


def blocks(section):
    """{repo name: its text} for each `== name ==` block; the whole section under '' when it has none."""
    found, name = {"": []}, ""
    for line in section.splitlines():
        head = re.match(r"^\s*==\s*(.+?)\s*==\s*$", line)
        name = head.group(1) if head else name
        found.setdefault(name, []).append("" if head else line)
    return {key: re.sub(r"-\s*\n\s*", "-", "\n".join(rows)) for key, rows in found.items()}  # a long name wraps at a hyphen


def missing(text, cwd=None):
    """['repo/slug', ...] of the goals the Dependencies section leaves out; [] when whole or when it cannot be told."""
    section = body(text)
    if section is None:
        return []  # the missing section is reported by the layout check
    parts = blocks(section)
    found = []
    for repo, slug in expected(cwd or None):
        where = parts.get(repo if len(repo) <= 54 else repo[:51] + "...", parts.get("") if len(parts) == 1 else "")
        if not re.search(r"(?<![\w-])%s(?![\w-])" % re.escape(slug), where or ""):
            found.append("%s/%s" % (repo, slug))
    return found


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--since", default="")
    args = parser.parse_args()
    if args.since and not re.match(r"^\d{4}(-\d\d(-\d\d(T\d\d(:\d\d(:\d\dZ?)?)?)?)?)?$", args.since):
        sys.exit("REFUSED: --since %r is not a time. Fix: give it as YYYY-MM-DDTHH:MM:SSZ." % args.since)
    print("\n".join(render(stamp=args.since or None)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
