#!/usr/bin/env python3
"""The check-in (MON-4, MON-5): what operate.py prints each pass instead of the live board, in the one layout the reply
hook checks. The board itself prints only for `report`, `dashboard` and "where do things stand".

usage: checkin.py [--since ISO]

  headline        one line: how many goals run, wait on you or are queued, and the session pool
  All sessions    one table row per live goal: session, repo, what it is for, status, progress, time left, latest
  Re-plan         what replan.py changed since the last check-in, each with its reason (MON-10)
  Auto-answered   what auto.py answered or sent to you since the last check-in, with the words that revert it (MON-11)
  Dependencies    board_lines' top-to-bottom graph
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

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import auto  # noqa: E402
import board_status as bs  # noqa: E402
import board_lines  # noqa: E402
import goal_state  # noqa: E402
import govern_hook  # noqa: E402
import graph  # noqa: E402
import live_board as lb  # noqa: E402
import pool as pl  # noqa: E402
import replan  # noqa: E402
import status_graph  # noqa: E402

MARK = {"running": "running", "held": "holding", "waiting": "waiting", "failed": "stuck", "stopped": "stuck",
        "silent": "silent", "done": "awaiting merge", "queued": "queued"}


def cell(text, size=48):
    return lb.plain(text, size).replace("|", "/") or "-"


def render(root=None, at=None, stamp=None):
    root = root or bs.git("rev-parse", "--show-toplevel")
    at = at or datetime.datetime.now(datetime.timezone.utc)
    folder, cfg = lb.loop_dir(root), bs.read_json(os.path.join(root, ".loop", "config.json")) or {}
    stamp = stamp or (bs.read_json(os.path.join(folder, "checkin.json")) or {}).get("at") or "0000"
    runs = lb.load(root)
    found, why = graph.read_pool(os.path.join(folder, "session-pool.json"))
    taken = graph.assigned(found)
    states = {r["slug"]: goal_state.classify(r, taken, at, cfg) for r in runs}
    live = [r for r in runs if states[r["slug"]] not in ("merged", "retired")]
    queue = bs.queued(root, runs)
    ready, _ = graph.ready(queue, {r["slug"]: r for r in runs}, graph.parallel_of(cfg), taken, why)
    counts = lambda *names: sum(states[r["slug"]] in names for r in live)
    pool_line = pl.status_line(found or {}, cfg) if found is not None else "pool: unreadable"
    out = ["%d running, %d waiting on you, %d queued; %s" % (counts("running", "held", "silent"),
                                                            counts("waiting", "failed", "stopped"), len(queue), pool_line), "",
           "All sessions", "| session | repo | for | status | progress | left | latest |", "|---|---|---|---|---|---|---|"]
    for run in live:
        step = lb.current(run)
        left = bs.left_time(run, runs, at)
        out.append("| %s | %s | %s | %s | %s %d/8 | %s | %s |" % (
            cell(lb.worker_of(run, taken), 30), os.path.basename(root), cell(run.get("goal"), 40), MARK.get(states[run["slug"]], states[run["slug"]]),
            lb.FLOW[step], step + 1, "?" if left is None else status_graph.span(left), cell(lb.latest_report(run) or run.get("next"), 60)))
    if not live:
        out.append("| - | %s | nothing running | - | - | - | - |" % os.path.basename(root))
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
    items = [dict(slug=r["slug"], mark=states[r["slug"]] if states[r["slug"]] != "done" else "awaiting merge",
                  depends=[d for d in r.get("waits_on") or []]) for r in live]
    items += [dict(slug=g["slug"], mark="queued", depends=g["depends"]) for g in queue]
    out += ["", "Dependencies"] + board_lines.render(items) + ["", "Needs you"]
    needs = []
    for run in live:
        state, ask = states[run["slug"]], run.get("waiting") or {}
        if state == "waiting":
            words = ask.get("words") or ["go on " + run["slug"]]
            rec = ask.get("recommend") or words[0]
            needs.append("%s asks: %s; options: %s; recommended: %s" % (run["slug"], lb.plain(ask.get("ask"), 160),
                                                                       " / ".join('"%s"' % w for w in words), rec))
        elif state == "silent":
            needs.append("%s: its worker has sent nothing for %dm; look at its session" % (
                run["slug"], goal_state.silent_for(run, at) // 60))
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
    out += ["%d. %s" % (i, text) for i, text in enumerate(needs, 1)] or ["Nothing needs you"]
    out += ["", "Coming up"]
    for run in live:
        if states[run["slug"]] == "done":
            out.append("- %s: its pull request waits for merge (you: review %s)" % (run["slug"], run.get("pr") or "it"))
        elif states[run["slug"]] in ("running", "silent", "held"):
            out.append("- %s: %s" % (run["slug"], lb.next_line(run)))
    paused = board_lines.paused(live)
    out.append("- " + (paused or "next check-in in %s minutes" % (cfg.get("cadence") or 30)))
    return lb.fit(out, 100)


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
