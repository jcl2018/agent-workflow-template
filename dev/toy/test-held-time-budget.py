#!/usr/bin/env python3
# windows: ok
# reads: skills/workflow-delivery/scripts/fit.py skills/workflow-monitoring/scripts/board_log.py skills/workflow-monitoring/scripts/board_status.py
"""held-time-budget (#3878): a goal's time budget counts only active step time. A goal held 10 hours in the pr queue, on a
session hold, on an owner answer or after a stop, then run 20 minutes, reads 20 minutes spent; a goal that truly runs past its
budget is still stopped. Calls the real fit.active_minutes / fit.budget_stop (delivery) and board_status.seconds_by_step."""
import datetime
import importlib.util
import os
import sys

root = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
for part in ("workflow-delivery", "workflow-monitoring"):
    sys.path.insert(0, os.path.join(root, "skills", part, "scripts"))
import board_status  # noqa: E402
import fit  # noqa: E402

fails = 0
T0 = datetime.datetime(2026, 11, 13, 1, 0, 0, tzinfo=datetime.timezone.utc)


def check(name, ok):
    global fails
    print(("PASS: " if ok else "FAIL: ") + name)
    fails += 0 if ok else 1


def run(*entries, step="pr"):
    """A running goal whose log entries are (minutes after freeze, text); 'now' is the last entry."""
    log = ["%s %s" % ((T0 + datetime.timedelta(minutes=m)).strftime("%Y-%m-%dT%H:%M:%SZ"), text) for m, text in entries]
    return {"slug": "g", "status": "running", "step": step, "log": log}, T0 + datetime.timedelta(minutes=entries[-1][0])


FIVE = [(0, "frozen 1 done lines"), (5, "idea done"), (10, "plan done"), (15, "build done"), (20, "review done")]
TEN_HOURS = 600


def spent(*entries, **kw):
    state, at = run(*entries, **kw)
    return fit.active_minutes(state, at), state, at


m, state, at = spent(*FIVE, (20, "waiting: pr queue, behind other"), (20 + TEN_HOURS, "pr queue: its turn"), (20 + TEN_HOURS, "pr"))
check("held 10 hours in the pr queue, run 20 minutes, reads 20 minutes spent", m == 20)
m, _, _ = spent(*FIVE, (20, "waiting: pr queue, behind other"))
check("still waiting in the pr queue, nothing more is spent", m == 20 and fit.active_minutes(state, at + datetime.timedelta(hours=9)) >= 20)
live, now = run(*FIVE, (20, "waiting: pr queue, behind other"))
check("the live tail of a goal waiting in the pr queue counts nothing", fit.active_minutes(live, now + datetime.timedelta(hours=10)) == 20)
m, _, _ = spent(*FIVE, (20, "session report: held at qa"), (20 + TEN_HOURS, "qa done"))
check("a session hold (sessions.py report --hold) counts nothing", m == 20)
m, _, _ = spent(*FIVE, (20, "qa waits for the owner (no try used): ask"), (20 + TEN_HOURS, "answered"), (25 + TEN_HOURS, "qa done"))
check("waiting for the owner counts nothing, the time after the answer does", m == 25)
m, _, _ = spent(*FIVE, (20, "stopped: owner asked"), (20 + TEN_HOURS, "start qa"), (30 + TEN_HOURS, "qa done"))
check("stopped until resume counts nothing", m == 30)
m, _, _ = spent(*FIVE, (20, "waiting: pr queue, behind other"), (20 + TEN_HOURS, "pr queue: its turn"), (45 + TEN_HOURS, "pr"))
check("work after the pr queue's turn counts", m == 45)
check("the board's per-step seconds follow the same rule", sum(board_status.seconds_by_step(*run(*FIVE, (20, "waiting: pr queue, behind other"), (620, "pr queue: its turn"), (620, "pr"))).values()) == 20 * 60)

cfg = {"time_budget_minutes": 300, "token_budget": 0}


def stopped(state, at, cfg=cfg):
    try:
        fit.budget_stop("g", state, "/none", cfg, at)
    except SystemExit as exit:
        return str(exit.code)
    return ""


state, at = run(*FIVE, (20, "waiting: pr queue, behind other"), (20 + 772, "pr queue: its turn"), (20 + 772, "pr"))
check("a goal held 772 minutes but active 20 is not stopped at a 300 minute budget", stopped(state, at) == "")
real = [(0, "frozen 1 done lines")] + [(60 * i, "%s done" % s) for i, s in enumerate(("idea", "plan", "build", "review", "qa", "ship"), 1)]
state, at = run(*real)
said = stopped(state, at)
check("a goal that truly runs 360 minutes of steps is stopped at 300 (REFUSED, BUDGET_MINUTES)", "360 minutes spent, at the minute budget of 300" in said and "BUDGET_MINUTES" in said)
state, at = run(*real, (360, "stopped: x"), (360 + TEN_HOURS, "start ship"), (360 + TEN_HOURS, "ship running"))
check("a stop's idle time does not hide steps that really ran past the budget", "360 minutes spent" in stopped(state, at))
check("no budget set means no stop", stopped(state, at, {}) == "")
sys.exit(1 if fails else 0)
