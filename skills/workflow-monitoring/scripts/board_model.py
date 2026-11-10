#!/usr/bin/env python3
"""The estimate model of the live board: time left per goal, as a range, from finished goals of a similar size (done lines
and touched areas); the current step's pace and overrun; and stalled goals. Imported by board_status.py, which re-exports
every name here; it imports board_log.py, status_graph.py and the standard library, never board_status.py.
"""
import os
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from board_log import STEPS, current, flow_seconds, git, size_of  # noqa: E402
import status_graph  # noqa: E402

SIMILAR = 5     # similar finished goals needed before an estimate stops being rough
STEP_UP = 60    # seconds one more done line or touched area adds at least
STALL = 3       # a current step past this many times its estimate is stalled
STALL_FLOOR = 900   # seconds: a step is never stalled before 15 minutes, however short its estimate
MODEL = {}
span = status_graph.span


def step_left(est, spent):
    """(seconds the current step still needs, seconds it is over its usual time). Past the usual time, re-estimate from
    how long it has already run: half of that, never under a minute, so it keeps growing while the step does."""
    return (est - spent, 0) if spent <= est else (max(60, spent / 2), spent - est)


def left_time(run, runs, at, root=None):
    """Seconds a goal still needs: 0 when finished, None when no step has an estimate (see estimate)."""
    if run.get("status") == "done":
        return 0
    found = estimate(run, runs, at, root)
    return found[0] if found else None


def model(runs, at, root):
    """Finished goals as (slug, size, flow_seconds), worked out once per set of runs."""
    key = (at, root, tuple((r.get("slug"), r.get("status"), r.get("updated")) for r in runs))
    if MODEL.get("key") != key:
        MODEL.clear()
        MODEL.update(key=key, done=[(r["slug"], size_of(r, root), flow_seconds(r, at)) for r in runs if r.get("status") == "done"])
    return MODEL


def spread(times):
    """(median, q25, q75) of a list of seconds, or None when empty."""
    if not times:
        return None
    if len(times) == 1:
        return times[0], times[0], times[0]
    q25, _, q75 = statistics.quantiles(times, n=4, method="inclusive")
    return statistics.median(times), q25, q75


def base(done, size, step):
    """(median, q25, q75) of a step's actual times over the similar finished goals (each count within 1) that logged it
    when there are at least SIMILAR of them, else over every finished goal that logged it; and the similar count."""
    similar = [t for _, s, t in done if size and s and abs(s[0] - size[0]) <= 1 and abs(s[1] - size[1]) <= 1]
    pick = similar if len(similar) >= SIMILAR and any(t.get(step) for t in similar) else [t for _, _, t in done]
    return spread([t[step] for t in pick if t.get(step)]), len(similar)


def steps_for(run, runs, at, root):
    """Per step (est, low, high) or None, lifted so a larger goal is longer; plus (similar count, size known, clamped)."""
    m = model(runs, at, root)
    key = ("steps", run.get("slug"), size_of(run, root))
    if key not in m:
        m[key] = lifted_steps(run, m, root)
    return m[key]


def lifted_steps(run, m, root):
    """steps_for, worked out."""
    done = [item for item in m["done"] if item[0] != run.get("slug")]
    size = size_of(run, root)
    if not size:
        return {step: base(done, None, step)[0] for step in STEPS}, (0, False, False)
    top = (max([s[0] for _, s, _ in done if s] + [1]) + 1, max([s[1] for _, s, _ in done if s] + [1]) + 1)
    d, a = min(size[0], top[0]), min(size[1], top[1])
    lifted, total = {}, lambda x, y: sum(b[0] for b in (base(done, (x, y), step)[0] for step in STEPS) if b)
    for x in range(1, d + 1):
        for y in range(1, a + 1):
            lifted[x, y] = max([total(x, y)] + [lifted[k] + STEP_UP for k in ((x - 1, y), (x, y - 1)) if k in lifted])
    own = {step: base(done, (d, a), step)[0] for step in STEPS}
    whole = sum(b[0] for b in own.values() if b)
    target = lifted[d, a] + STEP_UP * (size[0] - d + size[1] - a)
    lift = target / whole if whole else 1
    out = {step: tuple(v * lift for v in b) if b else None for step, b in own.items()}
    return out, (base(done, size, STEPS[0])[1], True, size != (d, a))


def estimate(run, runs, at, root=None):
    """(left, low, high, rough) in seconds for what a goal still needs, or None (see estimate_full)."""
    found = estimate_full(run, runs, at, root)
    return found[:4] if found else None


def holds(run, held):
    """True or False when held (the session pool's held slugs) says whether a goal is held; None when held is None."""
    return None if held is None else run.get("slug") in held


def estimate_full(run, runs, at, root=None, held=None):
    """(left, low, high, rough, partial) in seconds for what a goal still needs, or None when no step has an estimate.
    Finished steps add nothing; a running goal's pace over its finished steps (0.5 to 2) scales the rest; the current
    step past its estimate is re-estimated by step_left. Rough: fewer than SIMILAR similar goals, unknown size, a
    step still to run with no estimate, or a size past every finished goal's. A held goal's step time stops growing."""
    if run.get("status") == "done":
        return 0, 0, 0, False, False
    root = root or git("rev-parse", "--show-toplevel")
    per, (similar, known, clamped) = steps_for(run, runs, at, root)
    queued = run.get("status") in ("queued", "freezing") or not run.get("log")
    here = 0 if queued else current(run)
    if here >= len(STEPS):
        return 0, 0, 0, False, False
    spent, pace = ({}, 1) if queued else (flow_seconds(run, at, holds(run, held)), pace_of(run, per, at, here, held))
    left = low = high = 0
    partial = False
    for index in range(here, len(STEPS)):
        est = per[STEPS[index]]
        if not est:
            partial = True
            continue
        e, lo, hi = (v * pace for v in est)
        if index == here and spent.get(STEPS[index], 0):
            sp = spent[STEPS[index]]
            e, lo, hi = (e - sp, min(max(0, lo - sp), e - sp), max(0, hi - sp)) if sp <= e else (step_left(e, sp)[0],) * 3
        left, low, high = left + e, low + lo, high + hi
    if partial and not any(per[s] for s in STEPS[here:]):
        return None
    return left, low, high, similar < SIMILAR or not known or partial or clamped, partial


def pace_of(run, per, at, here, held=None):
    """Actual over estimated time across a running goal's finished steps that had an estimate, clamped to 0.5..2; 1 else."""
    if run.get("status") != "running":
        return 1
    spent = flow_seconds(run, at, holds(run, held))
    pairs = [(spent[s], per[s][0]) for s in STEPS[:here] if per.get(s) and per[s][0] and spent.get(s)]
    return min(2, max(0.5, sum(a for a, _ in pairs) / sum(e for _, e in pairs))) if pairs else 1


def step_now(run, runs, at, root=None, held=None):
    """(step, seconds it has run, its pace-adjusted estimate) for a running goal's current step, or None."""
    if run.get("status") != "running":
        return None
    root = root or git("rev-parse", "--show-toplevel")
    here = current(run)
    if here >= len(STEPS):
        return None
    per, _ = steps_for(run, runs, at, root)
    est = per[STEPS[here]]
    if not est or not est[0]:
        return None
    return STEPS[here], flow_seconds(run, at, holds(run, held)).get(STEPS[here], 0), est[0] * pace_of(run, per, at, here, held)


def overrun(run, runs, at, root=None, held=None):
    """Seconds the current step has run past its pace-adjusted estimate; 0 when on time, finished or with no estimate."""
    now = step_now(run, runs, at, root, held)
    return max(0, now[1] - now[2]) if now else 0


def stalled(run, runs, at, root=None, held=()):
    """(step, spent, estimate) when a running goal that is not held has run its current step more than STALL times its
    pace-adjusted estimate and more than STALL_FLOOR seconds; None otherwise (never without an estimate)."""
    now = None if run.get("slug") in (held or ()) else step_now(run, runs, at, root, held)
    return now if now and now[1] > max(STALL * now[2], STALL_FLOOR) else None


def stall_lines(runs, at, root=None, held=()):
    """The Issues lines for stalled goals."""
    out = []
    for run in runs:
        found = stalled(run, runs, at, root, held)
        if found:
            out += ["- %s is stalled: %s has run %s (estimate %s)" % (run["slug"], found[0], span(found[1]), span(found[2])),
                    "    fix: look at its worker session; stop and resume the goal if it is stuck"]
    return out


def estimate_text(found):
    """'<low> to <high> left', with ', rough' when rough; '<1m left' when nothing is left; 'no estimate yet' for None."""
    if found is None:
        return "no estimate yet"
    left, low, high, rough = found
    if not high:
        return "<1m left"
    return "%s to %s left%s" % (span(low), span(high), ", rough" if rough else "")
