#!/usr/bin/env python3
"""The time budgets of the loop's steps: read and check the two settings, and record a step or test run that hit one.

step_budget_minutes (default 30) bounds each review and ship step; test_budget_minutes (default 15) bounds each test
run (regression's tiers.py enforces it). Neither can be set under 15. A step that reaches its budget finishes with what
it has done, and its record (budget_hits in the goal's run file) names what it left; the board and health show those.
Imported by flow.py, role.py, guards.py and the monitoring and health reports.
"""
import json
import os
import re
import sys
import tempfile

FLOOR = 15
DEFAULTS = {"step_budget_minutes": 30, "test_budget_minutes": 15}
LEFT = re.compile(r"^\W*BUDGET:\s*left:\s*(.+)$", re.M | re.I)


def minutes(cfg, key):
    """The setting in whole minutes; exits with a fix line when it is under the 15-minute floor or not a whole number."""
    value = cfg.get(key, DEFAULTS[key])
    if isinstance(value, bool) or not isinstance(value, int) or value < FLOOR:
        sys.exit("REFUSED: %s is %r in .loop/config.json, under the %d-minute floor. Fix: set it to %d or more." % (
            key, value, FLOOR, FLOOR))
    return value


def seconds(cfg, key, limit=0):
    """Seconds a step or run may take: the budget, or the flow file's own limit when that is shorter."""
    budget = minutes(cfg, key) * 60
    return min(budget, limit) if limit else budget


def left_of(text):
    """What a reply says it left, from its last `BUDGET: left: ...` line, else ''."""
    found = LEFT.findall(text or "")
    return " ".join(found[-1].split())[:300] if found else ""


def hit(runs, slug, step, kind, limit, left):
    """Record that STEP (kind step: the step itself, test: its test run) reached its budget of LIMIT minutes and what it left."""
    path = os.path.join(runs, slug + ".json")
    try:
        with open(path) as handle:
            state = json.load(handle)
    except (OSError, ValueError):
        return
    kept = [h for h in state.get("budget_hits") or [] if not (h.get("step") == step and h.get("kind") == kind)]
    state["budget_hits"] = kept + [{"step": step, "kind": kind, "minutes": limit, "left": left or "not stated"}]
    with tempfile.NamedTemporaryFile("w", dir=runs, delete=False, suffix=".tmp") as handle:
        json.dump(state, handle, indent=2)
    os.replace(handle.name, path)


def reached(state, step):
    """Whether this goal's step was stopped at its step budget (recorded by flow.py, never by the step's own words)."""
    return any(h.get("step") == step and h.get("kind") == "step" for h in state.get("budget_hits") or [])


def lines(state):
    """One line per budget hit of a run record, for the board and for health."""
    return ["%s: %s hit its %s-minute budget; left: %s" % (
        state.get("slug", "?"), "%s %s" % (h.get("step"), "step" if h.get("kind") == "step" else "tests"), h.get("minutes"),
        h.get("left")) for h in state.get("budget_hits") or [] if isinstance(h, dict)]
