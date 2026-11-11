#!/usr/bin/env python3
"""The time budgets of the loop's steps: read and check the two settings, and record a step or test run that hit one.

step_budget_minutes (default 30) bounds each review and ship step; test_budget_minutes (default 15) bounds each test
run (regression's runs.py enforces it); prep_budget_minutes (default 15) bounds a lane's work before its first row (the
Tests-table prep, planning and the slot wait together). None can be set under 15. A step that reaches its budget finishes with what
it has done, and its record (budget_hits in the goal's run file) names what it left; the board and health show those.
Imported by flow.py, role.py, guards.py and the monitoring and health reports.
"""
import glob
import json
import os
import re
import sys
import tempfile

FLOOR = 15
DEFAULTS = {"step_budget_minutes": 30, "test_budget_minutes": 15, "prep_budget_minutes": 15}
LEFT = re.compile(r"^\W*BUDGET:\s*left:\s*(.+)$", re.M | re.I)


def minutes(cfg, key):
    """The setting in whole minutes; exits with a fix line when it is under the 15-minute floor or not a whole number."""
    value = cfg.get(key, DEFAULTS[key])
    if isinstance(value, bool) or not isinstance(value, int) or value < FLOOR:
        sys.exit("REFUSED: %s is %r in .loop/config.json, under the %d-minute floor. Fix: set it to %d or more." % (
            key, value, FLOOR, FLOOR))
    return value


def prep_seconds(cfg):
    """(seconds, override) a lane may spend before its first row: prep_budget_minutes, or the test-only LOOP_PREP_BUDGET
    (whole seconds, never read from config), which the lane line then says is in effect."""
    value = os.environ.get("LOOP_PREP_BUDGET", "")
    if value.isdigit() and int(value) > 0:
        return int(value), True
    return minutes(cfg, "prep_budget_minutes") * 60, False


def label(hit):
    """What a budget hit was: a step, preparation (before a lane's first row) or tests."""
    return {"step": "step", "prep": "preparation"}.get(hit.get("kind"), "tests")


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
        state.get("slug", "?"), "%s %s" % (h.get("step"), label(h)), h.get("minutes"),
        h.get("left")) for h in state.get("budget_hits") or [] if isinstance(h, dict)]

# The lane's preparation budget (REG-7, DEL-8): what a lane does before its first row (the Tests-table prep, planning and the
# slot wait) shares one budget, prep_budget_minutes. The lane child (lane.py lane-exec) writes one `.times` record (planning
# seconds, slot-wait seconds and, for a cut, the part that was running); lane.py's finalize reads it here, says the three parts
# on every LANE line, and on a cut prints LANE_PREP_BUDGET and records the hit (kind prep) so the board and health list it.

def _read(path):
    try:
        data = json.load(open(path))
        return data if isinstance(data, dict) else None
    except (OSError, ValueError):
        return None


def holders(pool):
    """Labels of the lanes holding slots now, for the cut line."""
    out = []
    for path in sorted(glob.glob(os.path.join(pool or "", "slot-*"))):
        label = (_read(path) or {}).get("label")
        if label:
            out.append(str(label)[:60])
    return out


def timing(held, rc):
    """(plan, wait, cut) seconds and part from the lane child's one .times record; zeros when absent or malformed."""
    data = _read(rc + ".times") or {}
    num = lambda key: float(data[key]) if isinstance(data.get(key), (int, float)) and not isinstance(data.get(key), bool) else 0.0
    return num("plan"), num("wait"), str(data.get("cut") or "")


def before_rows(held, plan, wait):
    """The LANE line's before-rows part (appended after the existing text): prep, planning and slot wait seconds."""
    note = "; before rows: prep %ds, planning %ds, slot wait %ds" % (held.get("prep_s") or 0, plan, wait)
    return note + ("; LOOP_PREP_BUDGET in effect" if held.get("override") else "")


def cut_line(name, held, plan, wait, part):
    """The LANE_PREP_BUDGET text: which part ran long, all three parts, the one shared budget, who holds the slots."""
    got = ", ".join(holders(held.get("pool"))) or "none"
    return ("LANE_PREP_BUDGET: the %s lane used its %s preparation budget before any row ran: %s ran long (prep %ds, "
            "planning %ds, slot wait %ds; the three share one budget); slots held by: %s; no row ran, %s beyond the prep "
            "commit. Fix: run the same command again (it replans on this HEAD); raise prep_budget_minutes only if prep or "
            "planning is the part that ran long." % (name, "%ds (LOOP_PREP_BUDGET)" % held["budget"] if held.get("override") else "%d-minute" % round(held.get("budget", 0) / 60),
                                                      part or "preparation",
                                                      held.get("prep_s") or 0, plan, wait, got, "the lane committed and pushed nothing"))


def prep_hit(base, name, held, plan, wait, part):
    """Record the cut on the goal's run file (kind prep), so the board and health list it with the part."""
    left = "%s ran long (prep %ds, planning %ds, slot wait %ds)" % (part or "preparation", held.get("prep_s") or 0, plan, wait)
    hit(os.path.dirname(base), os.path.basename(base)[:-len(".%s-lane" % name)], name, "prep",
               round(held.get("budget", 0) / 60), left)


