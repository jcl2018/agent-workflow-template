#!/usr/bin/env python3
"""The run-log and goal-file facts the live board's estimates are read from: which step a goal is on, how long each step
took (flow_seconds) and a goal's size (done lines and touched areas, from its goal file). Imported by board_model.py and
board_status.py; it imports only graph.py and the standard library.
"""
import datetime
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import graph  # noqa: E402

FLOW = ("idea", "plan", "build", "review", "qa", "ship", "pr", "release")
STEPS = FLOW[:-1]
COMMON = {}

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



def current(run):
    """Index in FLOW of the step a goal is on: a finished, unmerged goal waits at release. A step outside the flow (a check,
    say) keeps the newest timestamped evidence naming a flow step (a report's at, a log entry; see after), else the furthest step in
    the run's flow record, else idea."""
    if run.get("status") == "done":
        return FLOW.index("release")
    if run.get("step") in FLOW:
        return FLOW.index(run["step"])
    seen = [(stamp(item.get("at")), item["step"]) for item in (run.get("reports") if isinstance(run.get("reports"), list) else [])
            if isinstance(item, dict) and item.get("step") in FLOW and stamp(item.get("at"))]
    seen += [(stamp(entry), after(entry)) for entry in run.get("log") or [] if after(entry) and stamp(entry)]
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


def after(entry):
    """The flow step in force after a log entry: the step it names, or the next one when it says that step is done."""
    word = named(entry)
    done = word and re.search(r"\b(done|auto-approved|approved)\b", str(entry)) and FLOW.index(word) + 1 < len(FLOW)
    return FLOW[FLOW.index(word) + 1] if done else word


# A hold or free entry starts a pause that lasts until a step, a start, a bind or a resume (see holding).
HOLD = re.compile(r"session report: (?:worker · \S+: .*?; )?(?:held|holding) (?:at|before)\b|freed \d+ session")
UNHOLD = re.compile(r"(?:start [a-z]+|bound to session|assigned to session)\b|.*(?:resum|no longer held)")


def holding(entry, paused):
    """Whether a pause is in force after a log entry: a hold entry (a session report that the goal is held at or before a
    step) or a free entry (sessions.py free) starts one; an entry whose first word is a flow step, start <step>, bound or
    assigned to session, or one that says resum or no longer held ends it; any other entry keeps it as it was."""
    text = (str(entry).split(" ", 1) + [""])[1]
    if HOLD.match(text):
        return True
    return False if text.split(" ", 1)[0].rstrip(":") in FLOW or UNHOLD.match(text) else paused


# An entry that says the goal waits on someone else: the pr queue (goal.py pr), an owner question (a step that waits for or
# is pending on the owner, a refusal that asks, a waiting entry). The gap after it is held time (#3878).
WAIT = re.compile(r"waiting\b|[a-z]+ waits for the owner|[a-z]+ pending: |refused \(no try used\)")


def waiting(entry):
    return bool(WAIT.match((str(entry).split(" ", 1) + [""])[1]))


def flow_seconds(run, at, held=None):
    """Time per step with one rule for past and live runs: a gap before an entry naming a step counts toward that step;
    any other gap counts toward the step in force (the last one named, or the next after a finished one). A gap after a
    stopped or failed entry, or one that waits (see waiting), is a pause and counts nothing, and so is every gap while a hold or free pause is in
    force (see holding). The time since the last entry counts while running, unless the goal is held: held is True or
    False when the session pool says so, and None when it is unknown, when a pause in force at the last entry stops it."""
    found, force, paused, log = {}, None, False, run.get("log") or []
    for before, entry in zip(log, log[1:]):
        a, b, word = stamp(before), stamp(entry), named(entry)
        paused = holding(before, paused)
        pause = paused or waiting(before) or (str(before).split(" ", 2) + ["", ""])[1].rstrip(":") in ("stopped", "failed")
        step = word if word in STEPS and not re.search(r"\bstep [a-z]+, running", str(entry)) else force
        if a and b and step in STEPS and not pause:
            found[step] = found.get(step, 0) + max(0, (b - a).total_seconds())
        force = after(entry) or force
    last = stamp(log[-1]) if log else None
    step = run.get("step") if run.get("step") in STEPS else force
    idle = bool(log) and waiting(log[-1]) or (held if held is not None else bool(log) and holding(log[-1], paused))
    if run.get("status") == "running" and step in STEPS and last and not idle:
        found[step] = found.get(step, 0) + max(0, (at - last).total_seconds())
    return found


def active_minutes(run, at=None):
    """Whole minutes of active step time: flow_seconds summed, up to now when at is not given (the budget gate, #3878)."""
    return int(sum(flow_seconds(run, at or datetime.datetime.now(datetime.timezone.utc)).values()) // 60)


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

