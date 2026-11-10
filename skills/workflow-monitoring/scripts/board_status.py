#!/usr/bin/env python3
"""The run facts the live board is built from, plus every name of board_log.py and board_model.py (the estimate model),
re-exported so readers keep using board_status; running it prints the live board (see live_board.py).

usage: board_status.py [--html]

Prints the live board as text, or with --html as the fragment board-artifact.html embeds.
"""
import argparse
import json
import os
import re
import statistics
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import graph  # noqa: E402
import status_graph  # noqa: E402
# board_log sets the no-prompt guard (GIT_TERMINAL_PROMPT and the rest) before any git or gh process starts.
from board_log import (COMMON, FLOW, HOLD, STEPS, UNHOLD, after, current, flow_seconds, git, goal_file,  # noqa: E402,F401
                       holding, named, read_json, size_of, stamp)
from board_model import (MODEL, SIMILAR, STALL, STALL_FLOOR, STEP_UP, base, estimate, estimate_full, estimate_text,  # noqa: E402,F401
                         holds, left_time, lifted_steps, model, overrun, pace_of, span, spread, stall_lines, stalled,
                         step_left, step_now, steps_for)

ASKING = ("waiting", "failed", "stopped")


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


def board_items(live, queue, freezing, lines, runs, at, root, waits, held=None):
    """The board's goal items: slug, mark, depends, stage, left, the estimate, and partial (a step with no estimate). held:
    the slugs the session pool says are held (None when unknown), whose step time stops growing."""
    def item(run, mark, depends):
        found = estimate_full(run, runs, at, root, held)
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
