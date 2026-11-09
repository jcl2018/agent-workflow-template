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

STEPS = ("idea", "plan", "build", "review", "qa", "ship", "pr")
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


def left_time(run, runs, at):
    """Seconds a goal still needs, from other runs' step medians: 0 when finished, None when no step has an estimate.
    A goal that has not started needs every step; a current step past its estimate is re-estimated (step_left)."""
    if run.get("status") == "done":
        return 0
    spent = seconds_by_step(run, at)
    here = -1 if run.get("status") == "queued" else STEPS.index(run["step"]) if run.get("step") in STEPS else 0
    left = [step_left(est, spent.get(step, 0))[0] if index == here else est
            for index, step in enumerate(STEPS) if index >= here
            for est in [usual(runs, run, step, lambda r: seconds_by_step(r, at))] if est]
    return sum(left) if left else None


def overrun(run, runs, at):
    """Seconds the current step has run past its usual time; 0 when on time, finished or with no estimate."""
    step = run.get("step")
    if run.get("status") != "running" or step not in STEPS:
        return 0
    est = usual(runs, run, step, lambda r: seconds_by_step(r, at))
    return step_left(est, seconds_by_step(run, at).get(step, 0))[1] if est else 0


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
