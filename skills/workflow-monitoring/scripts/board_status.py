#!/usr/bin/env python3
"""The estimates and run facts the live board is built from; running it prints the live board (see live_board.py).

usage: board_status.py [--html]

Prints the live board as text, or with --html as the fragment board-artifact.html embeds. Estimates come from the median of other
runs' steps, read from their logs, and read "no estimate yet" when there is none.
"""
import argparse
import datetime
import json
import os
import re
import statistics
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import graph  # noqa: E402
import status_graph  # noqa: E402

FLOW = ("idea", "plan", "build", "review", "qa", "ship", "pr", "release")
STEPS = FLOW[:-1]
SIMILAR = 5     # similar finished goals needed before an estimate stops being rough
STEP_UP = 60    # seconds one more done line or touched area adds at least
STALL = 3       # a current step past this many times its estimate is stalled
ASKING = ("waiting", "failed", "stopped")

# No terminal, no waiting: a prompt from git or gh must fail, not block.
os.environ.update(GIT_TERMINAL_PROMPT="0", GH_PROMPT_DISABLED="1", GIT_EDITOR="true", GIT_ASKPASS="true", SSH_ASKPASS="true")


def git(*args, cwd=None):
    done = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    return done.stdout.strip() if done.returncode == 0 else ""


def read_json(path):
    try:
        with open(path) as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return None


def stamp(text):
    try:
        return datetime.datetime.fromisoformat(str(text).split(" ", 1)[0].replace("Z", "+00:00"))
    except ValueError:
        return None


span = status_graph.span


def seconds_by_step(run, at):
    """Time each step took, from the gaps before its log entries, plus the gap since the last entry for the current step."""
    found, log = {}, run.get("log") or []
    for before, entry in zip(log, log[1:]):
        word = entry.split(" ", 2)[1] if entry.count(" ") else ""
        a, b = stamp(before), stamp(entry)
        if word in STEPS and a and b:
            found[word] = found.get(word, 0) + (b - a).total_seconds()
    last = stamp(log[-1]) if log else None
    if run.get("status") == "running" and run.get("step") in STEPS and last:
        found[run["step"]] = found.get(run["step"], 0) + max(0, (at - last).total_seconds())
    return found


def tokens_by_step(run):
    value = run.get("tokens")
    return {step: n for step, n in value.items() if step in STEPS and isinstance(n, int)} if isinstance(value, dict) else {}


def usual(runs, mine, step, pick):
    values = [pick(run).get(step) for run in runs if run["slug"] != mine["slug"] and run.get("status") == "done"]
    values = [v for v in values if v]
    return statistics.median(values) if values else None


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


def current(run):
    """Index in FLOW of the step a goal is on: a finished, unmerged goal waits at release. A step outside the flow (a check,
    say) keeps the newest timestamped evidence naming a flow step (a report's at, a log entry), else the furthest step in
    the run's flow record, else idea."""
    if run.get("status") == "done":
        return FLOW.index("release")
    if run.get("step") in FLOW:
        return FLOW.index(run["step"])
    seen = [(stamp(item.get("at")), item["step"]) for item in (run.get("reports") if isinstance(run.get("reports"), list) else [])
            if isinstance(item, dict) and item.get("step") in FLOW and stamp(item.get("at"))]
    seen += [(stamp(entry), named(entry)) for entry in run.get("log") or [] if named(entry) and stamp(entry)]
    if seen:
        return FLOW.index(max(seen, key=lambda pair: pair[0])[1])
    known = [FLOW.index(step) for step in (run.get("flow") or {}) if step in FLOW]
    return max(known) if known else 0


def named(entry):
    """The flow step a log entry names: its first word, or 'step X' in a session report; '' when none."""
    parts = str(entry).split(" ", 2)
    word = parts[1].rstrip(":") if len(parts) > 1 else ""
    if word in FLOW:
        return word
    found = re.search(r"\bstep ([a-z]+)\b", parts[2] if len(parts) > 2 else "")
    return found.group(1) if found and found.group(1) in FLOW else ""


def flow_seconds(run, at):
    """Time per step with one rule for past and live runs: a gap before an entry naming a step counts toward that step;
    any other gap counts toward the step in force (the last one named, or the next after a finished one). A gap after a
    stopped, failed or waiting entry is a pause and counts nothing; the time since the last entry counts while running."""
    found, force, log = {}, None, run.get("log") or []
    for before, entry in zip(log, log[1:]):
        a, b, word = stamp(before), stamp(entry), named(entry)
        pause = (str(before).split(" ", 2) + ["", ""])[1].rstrip(":") in ("stopped", "failed", "waiting")
        step = word if word in STEPS and not re.search(r"\bstep [a-z]+, running", str(entry)) else force
        if a and b and step in STEPS and not pause:
            found[step] = found.get(step, 0) + max(0, (b - a).total_seconds())
        if word:
            done = re.search(r"\b(done|auto-approved|approved)\b", str(entry)) and FLOW.index(word) + 1 < len(FLOW)
            force = FLOW[FLOW.index(word) + 1] if done else word
    last = stamp(log[-1]) if log else None
    step = run.get("step") if run.get("step") in STEPS else force
    if run.get("status") == "running" and step in STEPS and last:
        found[step] = found.get(step, 0) + max(0, (at - last).total_seconds())
    return found


def goal_file(run, root):
    """The goal file's text: in the run's worktree when it is one under <common>/loop/worktrees, else under root."""
    slug = run.get("slug") or ""
    if not graph.SLUG.match(slug):
        return ""
    if root and root not in COMMON:
        COMMON[root] = os.path.realpath(os.path.join(root, git("rev-parse", "--git-common-dir", cwd=root) or ".git"))
    common = COMMON.get(root, "")
    tree = run.get("worktree") or ""
    places = [tree] if tree and common and os.path.isdir(tree) and os.path.realpath(tree).startswith(os.path.join(common, "loop", "worktrees") + os.sep) else []
    for base in places + ([root] if root else []):
        goals = os.path.realpath(os.path.join(base, ".loop", "goals"))
        path = os.path.realpath(os.path.join(goals, slug + ".md"))
        if os.path.dirname(path) != goals:
            continue
        try:
            with open(path) as handle:
                return handle.read()
        except OSError:
            continue
    return ""


def size_of(run, root):
    """(done lines, touched areas) of a goal, or None. The goal file wins for both; then the queue line's done and
    touches, then the run record's touches. Done lines are the numbered lines under ## Done lines, outside code fences."""
    text, done, touches, fenced, inside = goal_file(run, root), [], [], False, False
    for line in text.splitlines():
        fenced = not fenced if line.startswith("```") else fenced
        if line.startswith("## "):
            inside = line.strip() == "## Done lines"
        elif inside and not fenced and re.match(r"\d+\. \S", line):
            done.append(line)
        found = re.match(r"- Touches: (.*)$", line)
        if found and not touches:
            touches = [x.strip() for x in found.group(1).split(",") if x.strip()]
    return graph.size(done or run.get("done") or [], touches or run.get("touches") or [])


MODEL, COMMON = {}, {}


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


def estimate_full(run, runs, at, root=None):
    """(left, low, high, rough, partial) in seconds for what a goal still needs, or None when no step has an estimate.
    Finished steps add nothing; a running goal's pace over its finished steps (0.5 to 2) scales the rest; the current
    step past its estimate is re-estimated by step_left. Rough: fewer than SIMILAR similar goals, unknown size, a
    step still to run with no estimate, or a size past every finished goal's."""
    if run.get("status") == "done":
        return 0, 0, 0, False, False
    root = root or git("rev-parse", "--show-toplevel")
    per, (similar, known, clamped) = steps_for(run, runs, at, root)
    queued = run.get("status") in ("queued", "freezing") or not run.get("log")
    here = 0 if queued else current(run)
    if here >= len(STEPS):
        return 0, 0, 0, False, False
    spent, pace = ({}, 1) if queued else (flow_seconds(run, at), pace_of(run, per, at, here))
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


def pace_of(run, per, at, here):
    """Actual over estimated time across a running goal's finished steps that had an estimate, clamped to 0.5..2; 1 else."""
    if run.get("status") != "running":
        return 1
    spent = flow_seconds(run, at)
    pairs = [(spent[s], per[s][0]) for s in STEPS[:here] if per.get(s) and per[s][0] and spent.get(s)]
    return min(2, max(0.5, sum(a for a, _ in pairs) / sum(e for _, e in pairs))) if pairs else 1


def step_now(run, runs, at, root=None):
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
    return STEPS[here], flow_seconds(run, at).get(STEPS[here], 0), est[0] * pace_of(run, per, at, here)


def overrun(run, runs, at, root=None):
    """Seconds the current step has run past its pace-adjusted estimate; 0 when on time, finished or with no estimate."""
    now = step_now(run, runs, at, root)
    return max(0, now[1] - now[2]) if now else 0


def stalled(run, runs, at, root=None, held=()):
    """(step, spent, estimate) when a running goal that is not held has run its current step more than STALL times its
    pace-adjusted estimate; None otherwise (never without an estimate)."""
    now = None if run.get("slug") in held else step_now(run, runs, at, root)
    return now if now and now[1] > STALL * now[2] else None


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


def board_items(live, queue, freezing, lines, runs, at, root, waits):
    """The board's goal items: slug, mark, depends, stage, left, the estimate, and partial (a step with no estimate)."""
    def item(run, mark, depends):
        found = estimate_full(run, runs, at, root)
        return dict(slug=run["slug"], mark=mark, depends=waits(depends), stage=0, est=found and found[:4],
                    left=found[0] if found else None, partial=bool(found and found[4]))
    out = [item(r, status_graph.mark(r.get("status")), r.get("waits_on") or []) for r in live]
    out += [item(dict(g, status="queued"), "queued", g["depends"]) for g in queue]
    out += [item(dict(lines.get(f["slug"]) or {"slug": f["slug"]}, status="queued"), status_graph.mark("running"),
                 (lines.get(f["slug"]) or {}).get("depends") or []) for f in freezing]
    return out


def queued(root, runs):
    """Queued goals, as queue.md lines parsed by graph.parse: the ones with no run record yet."""
    by_slug = {run["slug"] for run in runs}
    try:
        with open(os.path.join(root, ".loop", "queue.md")) as handle:
            return [item for item in map(graph.parse, handle.read().splitlines()) if item and item["slug"] not in by_slug]
    except OSError:
        return []


def github_state(url, cwd):
    """MERGED, CLOSED or OPEN as gh says it; any doubt (no gh, no answer) is an empty string."""
    try:
        done = subprocess.run(["gh", "pr", "view", url, "--json", "state"], cwd=cwd, capture_output=True, text=True, timeout=20)
        state = str(json.loads(done.stdout).get("state", "")).upper() if done.returncode == 0 else ""
        return state if state in ("MERGED", "CLOSED", "OPEN") else ""
    except (OSError, ValueError, AttributeError, subprocess.SubprocessError):
        return ""


def pr_states(runs, root):
    """GitHub's state of each done run's pull request, asked once per run."""
    return {run["slug"]: github_state(run["pr"], root) for run in runs if run.get("status") == "done" and run.get("pr") and not graph.merged(run)}


def error_open(run, gone, marker):
    """An error stays under Issues unless its goal merged. A record-merged goal's error stays when it was logged after the merge
    (the wiki publishes after it); one merged only on GitHub never merged through here, so what it logged came before."""
    log = [str(entry).split(" ", 2)[1:] or [""] for entry in run.get("log") or []]
    last = lambda test: max([n for n, parts in enumerate(log) if test(parts)] + [-1])
    if marker == "wiki not published" and last(lambda parts: " ".join(parts).startswith(("wiki published", "wiki unchanged"))) > last(lambda parts: " ".join(parts).startswith(marker)):
        return False   # a later publish went through or found nothing to change
    if run["slug"] not in gone:
        return True
    return graph.merged(run) and last(lambda parts: " ".join(parts).startswith(marker)) > last(lambda parts: parts[0] == "merged")


DOCS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "workflow-docs", "scripts", "docs.py")


def wiki_check(root):
    """The pages docs.py check reports now, as sorted [(kind, page)]; None when the check could not judge."""
    try:
        done = subprocess.run([sys.executable, DOCS, "check"], cwd=root, capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    if done.returncode not in (0, 1) or "NO PAGES" in done.stdout:
        return None
    return sorted({m.groups() for m in re.finditer(r"^([A-Z]+) (\S+): ", done.stdout, re.M)}) if done.returncode else []


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--html", action="store_true")
    args = parser.parse_args()
    import live_board  # noqa: E402  (live_board imports this module)
    lines = live_board.render()
    sys.stdout.write(live_board.fragment(lines) if args.html else "\n".join(lines) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
