#!/usr/bin/env python3
"""Live-board estimate candidates, time-ordered selection, and per-goal predictions."""
import math
import os
import statistics
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from board_log import STEPS, current, flow_seconds, git, named, size_of, stamp  # noqa: E402
import board_page  # noqa: E402

SIMILAR = 5     # similar finished goals needed before an estimate stops being rough
STEP_UP = 60    # seconds one more done line or touched area adds at least
STALL = 3       # a current step past this many times its estimate is stalled
STALL_FLOOR = 900   # seconds: a step is never stalled before 15 minutes, however short its estimate
MIN_BACKTEST = 10   # scorable finished goals the backtest needs before it picks a candidate over the size rule
TILT = 1        # seconds one more unit adds for the size-light candidates: only keeps a larger goal strictly longer
CANDIDATES = ("steps", "size", "blend")   # a new candidate is a cell function in CELLS and its name here; ties go first
LABELS = {"steps": "step medians", "size": "size rule", "blend": "blend"}
MODEL = {}
span = board_page.span


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
    """Finished goals as (slug, size, flow_seconds) and their History, worked out once per set of runs; the backtest's
    scores and the chosen candidate are kept here too, so a run that finishes or changes recomputes them."""
    key = (at, root, tuple((r.get("slug"), r.get("status"), r.get("updated")) for r in runs))
    if MODEL.get("key") != key:
        MODEL.clear()
        done = [(r["slug"], size_of(r, root), flow_seconds(r, at)) for r in runs if r.get("status") == "done"]
        MODEL.update(key=key, done=done, hist=History(done))
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


class History:
    """Finished goals [(slug, size, seconds per step)] with each size's similar goals found once. Every lookup leaves out
    one goal, out: a backtest fold's held-out goal, or the goal being estimated; results are kept per (cell, step, out)
    only when out changes them, so a backtest reuses every cell its held-out goal is not in."""
    def __init__(self, done):
        self.done, self.memo, self.near = done, {}, {}

    def pooled(self, step, out):
        key = ("pool", step, out)
        if key not in self.memo:
            self.memo[key] = spread([t[step] for s, _, t in self.done if s != out and t.get(step)])
        return self.memo[key]

    def logged(self, step, out):
        """How many finished goals other than out logged the step."""
        return sum(1 for s, _, t in self.done if s != out and t.get(step))

    def top(self, out):
        """One past the largest done lines and areas of the finished goals other than out (the size clamp)."""
        sizes = [z for s, z, _ in self.done if z and s != out]
        return max([z[0] for z in sizes] + [1]) + 1, max([z[1] for z in sizes] + [1]) + 1

    def base(self, cell, step, out):
        """base() over every finished goal but out."""
        if not cell:
            return self.pooled(step, out), 0
        if cell not in self.near:
            self.near[cell] = [i for i in self.done if i[1] and abs(i[1][0] - cell[0]) <= 1 and abs(i[1][1] - cell[1]) <= 1]
        key = (cell, step, out if any(s == out for s, _, _ in self.near[cell]) else None)
        if key not in self.memo:
            similar = [t for s, _, t in self.near[cell] if s != out]
            own = len(similar) >= SIMILAR and any(t.get(step) for t in similar)
            self.memo[key] = spread([t[step] for t in similar if t.get(step)]) if own else "pool", len(similar)
        found, count = self.memo[key]
        return (self.pooled(step, out) if found == "pool" else found), count


def size_cell(hist, out):
    """The size rule's cell: each step's base over the goals similar to that size."""
    return lambda x, y: {step: hist.base((x, y), step, out)[0] for step in STEPS}


def steps_cell(hist, out):
    """The step medians' cell: each step's spread over every finished goal that logged it, the same for every size."""
    flat = {step: hist.pooled(step, out) for step in STEPS}
    return lambda x, y: flat


def blend_cell(hist, out):
    """The blend's cell: per step and per value, the geometric mean of the step medians and the size rule's base; a step
    only one of them has comes from that one."""
    flat, by_size = steps_cell(hist, out)(1, 1), size_cell(hist, out)

    def cell(x, y):
        sized = by_size(x, y)
        return {s: tuple(math.sqrt(p * q) for p, q in zip(flat[s], sized[s])) if flat[s] and sized[s] else flat[s] or sized[s]
                for s in STEPS}
    return cell


CELLS = {"steps": steps_cell, "size": size_cell, "blend": blend_cell}


def envelope(cell, size, top, up):
    """Per step (est, low, high) or None for a goal of size, and the size it was clamped to: every size's cell total is
    lifted to at least `up` seconds more than each size one smaller (one rule for every candidate), and the goal's own
    cell is scaled to its lifted total. A cell with no time under a lifted total takes that total split evenly."""
    total = lambda per: sum(b[0] for b in per.values() if b)
    d, a = min(size[0], top[0]), min(size[1], top[1])
    lifted = {}
    for x in range(1, d + 1):
        for y in range(1, a + 1):
            lifted[x, y] = max([total(cell(x, y))] + [lifted[k] + up for k in ((x - 1, y), (x, y - 1)) if k in lifted])
    own = cell(d, a)
    whole, target = total(own), lifted[d, a] + up * (size[0] - d + size[1] - a)
    if whole:
        return {s: tuple(v * target / whole for v in b) if b else None for s, b in own.items()}, (d, a)
    if not any(lifted[x, y] > up * (x + y - 2) for x, y in lifted):
        return dict(own), (d, a)   # no finished goal logged anything
    return {s: (target / len(own),) * 3 for s in own}, (d, a)


def table(name, hist, size, out=None):
    """(per step (est, low, high) or None, info) for a goal of size estimated by candidate name from every finished goal
    but out. info: (similar count, size known, clamped, {step: finished goals that logged it}, name)."""
    logged = {step: hist.logged(step, out) for step in STEPS}
    if not size:
        return {step: hist.pooled(step, out) for step in STEPS}, (0, False, False, logged, name)
    per, clamp = envelope(CELLS[name](hist, out), size, hist.top(out), STEP_UP if name == "size" else TILT)
    return per, (hist.base(size, STEPS[0], out)[1], True, size != clamp, logged, name)


def cached(m, name, slug, size):
    """table() for a goal, kept in the model under ("steps", name, slug, size)."""
    key = ("steps", name, slug, size)
    if key not in m:
        m[key] = table(name, m["hist"], size, slug)
    return m[key]


def steps_for(run, runs, at, root):
    """Per step (est, low, high) or None from the chosen candidate, lifted so a larger goal is longer; plus info (see
    table)."""
    return cached(model(runs, at, root), chosen(runs, at, root), run.get("slug"), size_of(run, root))


def lifted_steps(run, m, root):
    """The size rule's steps_for, worked out."""
    return table("size", m["hist"], size_of(run, root), run.get("slug"))


def folds(hist, names=CANDIDATES, memo=None):
    """Each finished goal with logged time that every candidate estimates above 0 when it is queued and left out of the
    history: {slug, size, actual, seconds, per: {name: per step}, left: {name: seconds}}."""
    out = []
    for slug, size, seconds in hist.done:
        actual = sum(seconds.get(s, 0) for s in STEPS)
        if actual <= 0:
            continue
        per = {c: (cached(memo, c, slug, size) if memo is not None else table(c, hist, size, slug))[0] for c in names}
        left = {c: sum(b[0] for b in p.values() if b) for c, p in per.items()}
        if all(v > 0 for v in left.values()):
            out.append(dict(slug=slug, size=size, actual=actual, seconds=seconds, per=per, left=left))
    return out


def score(rows, name):
    """Median over the rows of |ln(estimate / actual)|: how many times off the whole-goal estimate typically was."""
    return statistics.median(abs(math.log(r["left"][name] / r["actual"])) for r in rows)


def time_folds(runs, hist, names=CANDIDATES):
    """Retrospective folds with only goals finished strictly before each target started."""
    windows = {}
    for run in runs:
        if run.get("status") != "done":
            continue
        log = run.get("log") or []
        ends = [stamp(e) for e in log if named(e) and stamp(e)]
        windows[run["slug"]] = (stamp(log[0]) if log else None, max(ends) if ends else None)
    rows = []
    for slug, size, seconds in hist.done:
        start, finish = windows.get(slug, (None, None))
        actual = sum(seconds.get(s, 0) for s in STEPS)
        if not start or not finish or actual <= 0:
            continue
        earlier = [item for item in hist.done if item[0] != slug and windows.get(item[0], (None, None))[1] and windows[item[0]][1] < start]
        if not earlier:
            continue
        past = History(earlier)
        per = {c: table(c, past, size)[0] for c in names}
        left = {c: sum(b[0] for b in p.values() if b) for c, p in per.items()}
        if all(v > 0 for v in left.values()):
            rows.append(dict(slug=slug, size=size, actual=actual, seconds=seconds, per=per, left=left))
    return rows


def backtest(runs, at, root):
    """Time-ordered scores for the common eligible goals; cached per set of runs."""
    m = model(runs, at, root)
    if "scores" not in m:
        m["folds"] = rows = time_folds(runs, m["hist"], CANDIDATES)
        m["scores"] = ({c: score(rows, c) for c in CANDIDATES} if len(rows) >= MIN_BACKTEST else {}), len(rows)
    return m["scores"]


def chosen(runs, at, root):
    """The candidate with the lowest backtest score; scores within 1e-9 tie and the first in CANDIDATES wins. The size
    rule under MIN_BACKTEST scorable goals, or when the backtest fails (its traceback goes to stderr). The name and the
    reason are kept in the model as "chosen"."""
    m = model(runs, at, root)
    if "chosen" not in m:
        try:
            scores, n = backtest(runs, at, root)
        except (ArithmeticError, ValueError, TypeError, KeyError) as error:
            traceback.print_exc(limit=3, file=sys.stderr)
            m["chosen"] = "size", "backtest failed (%s)" % type(error).__name__
            return "size"
        low = min(scores.values()) if scores else 0
        tied = [c for c in CANDIDATES if c in scores and scores[c] - low <= 1e-9]
        m["chosen"] = (("size", "fewer than %d scorable goals (%d)" % (MIN_BACKTEST, n)) if not scores else
                       (tied[0], "exact tie, first in CANDIDATES" if len(tied) > 1 else "lowest time-ordered score"))
    return m["chosen"][0]


def accuracy_text(runs, at, root=None):
    """The line under Finish: the candidate in use and how many times off its whole-goal estimate typically was in the
    backtest, or why that is not known (at most 60 columns)."""
    root = root or git("rev-parse", "--show-toplevel")
    name = chosen(runs, at, root)
    m = model(runs, at, root)
    if "scores" not in m:
        return "estimates: size rule, %s" % m["chosen"][1]
    scores, n = m["scores"]
    if not scores:
        return "estimates: size rule, error not known yet (%d of %d goals)" % (n, MIN_BACKTEST)
    return "estimates: %s, time-ordered off x%.1f (%d goals)" % (LABELS[name], math.exp(scores[name]), n)


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
    step past its estimate is re-estimated by step_left. Rough: unknown size, a step still to run with no estimate, and
    for the size rule fewer than SIMILAR similar goals or a size past every finished goal's, for the others a step
    still to run that fewer than SIMILAR other finished goals logged. A held goal's step time stops growing."""
    if run.get("status") == "done":
        return 0, 0, 0, False, False
    root = root or git("rev-parse", "--show-toplevel")
    per, (similar, known, clamped, logged, name) = steps_for(run, runs, at, root)
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
    few = similar < SIMILAR or clamped if name == "size" else any(logged[s] < SIMILAR for s in STEPS[here:] if per[s])
    return left, low, high, few or not known or partial, partial


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
