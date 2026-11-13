#!/usr/bin/env python3
"""Who a goal at pr waits for (DEL-15, parallel by files); imported by pool.py's pr_turn, not a command.

Goals at pr used to take turns one at a time. Two goals whose touches share no path can't move each other's rows, so their pr
lanes may run at once: a goal waits only for the goals ahead of it in the queue whose touches overlap its own (a path equal to,
inside or above the other's). A goal with no touches recorded overlaps everything, so it keeps the old one-at-a-time turn.
"""
import json
import os


def touches_of(runs, slug):
    """The touches a goal's run record holds, [] when it has none or the record can't be read."""
    try:
        with open(os.path.join(runs, slug + ".json")) as handle:
            found = json.load(handle).get("touches")
        return [str(t).strip("/") for t in found] if isinstance(found, list) else []
    except (OSError, ValueError, AttributeError):
        return []


def overlap(mine, theirs):
    """True when any two paths are the same or one is inside the other; an empty list overlaps everything."""
    if not mine or not theirs:
        return True
    return any(a == b or a.startswith(b + "/") or b.startswith(a + "/") for a in mine for b in theirs)


def first_ahead(runs, line, slug):
    """The goal slug must wait for, or '': the earliest in line (joined time, name) that joined before slug and whose touches
    overlap slug's."""
    joined = dict((name, at) for at, name in line).get(slug)
    mine = touches_of(runs, slug)
    ahead = [(at, name) for at, name in line if name != slug and (joined is None or at < joined) and overlap(mine, touches_of(runs, name))]
    return min(ahead)[1] if ahead else ""
