#!/usr/bin/env python3
"""The preparation budget of a goal's lane (REG-7, DEL-8), imported by lane.py; not a command.

What a lane does before its first row (the Tests-table prep, planning which rows to run, and waiting for a slot) shares one
budget, prep_budget_minutes (default 15, floor 15; budget.prep_seconds reads it). The lane child (lane.py lane-exec) writes one
`.times` record (planning seconds, slot-wait seconds and, for a cut, the part that was running); finalize reads it here, says the
three parts on every LANE line, and on a cut prints LANE_PREP_BUDGET and records the hit (kind prep) on the goal's run file so the
board and health list it with the part that ran long.
"""
import glob
import os

import budget
import lanekit
from lanekit import NOTHING, read_json


def holders(pool):
    """Labels of the lanes holding slots now, for the cut line."""
    out = []
    for path in sorted(glob.glob(os.path.join(pool or "", "slot-*"))):
        label = (read_json(path) or {}).get("label")
        if label:
            out.append(str(label)[:60])
    return out


def timing(held, rc):
    """(plan, wait, cut) seconds and part from the lane child's one .times record; zeros when absent or malformed."""
    data = read_json(rc + ".times") or {}
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
                                                      held.get("prep_s") or 0, plan, wait, got, NOTHING))


def prep_hit(base, name, held, plan, wait, part):
    """Record the cut on the goal's run file (kind prep), so the board and health list it with the part."""
    left = "%s ran long (prep %ds, planning %ds, slot wait %ds)" % (part or "preparation", held.get("prep_s") or 0, plan, wait)
    budget.hit(os.path.dirname(base), os.path.basename(base)[:-len(".%s-lane" % name)], name, "prep",
               round(held.get("budget", 0) / 60), left)


