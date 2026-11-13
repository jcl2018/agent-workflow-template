#!/usr/bin/env python3
# windows: ok
# reads: skills/workflow-monitoring/scripts/sessions.py skills/workflow-monitoring/scripts/worker.py
"""#3868: a goal's pull request merges only through its own merge.py, never as a side effect of a report.

Two goals sit at pr in a repo with auto_merge on. A session report for one of them (waiting, or merged for a PR that is
still open) must not run merge.py for either; merge.py for one goal runs only when asked for that goal."""
import argparse
import json
import os
import subprocess
import sys
import tempfile

here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(here, "..", "..", "skills", "workflow-monitoring", "scripts"))
import sessions  # noqa: E402
import worker  # noqa: E402

failed = []


def check(ok, text):
    print(("PASS: " if ok else "FAIL: ") + text)
    if not ok:
        failed.append(text)


real = subprocess.run
calls = []


def run(command, *a, **k):
    if isinstance(command, list) and any("merge.py" in str(part) for part in command) or isinstance(command, list) and command[:3] == ["gh", "pr", "merge"]:
        calls.append(command)
        return type("R", (), {"returncode": 0, "stdout": "", "stderr": ""})()
    return real(command, *a, **k)


subprocess.run = run
worker.merged = sessions.merged = lambda url: False


def report(slug, status):
    args = argparse.Namespace(slug=slug, status=status, step="", pr="https://example.test/pull/" + slug[-1], ask="", words=[],
                              text="PR open; holding before merge.py", recommend="", kind="", attempt=None)
    try:
        sessions.cmd_report(args)
    except SystemExit as stop:
        print("(exit: %s)" % stop)


with tempfile.TemporaryDirectory() as tmp:
    real(["git", "init", "-q", tmp], check=True)
    os.makedirs(os.path.join(tmp, ".loop"))
    with open(os.path.join(tmp, ".loop", "config.json"), "w") as handle:
        json.dump({"auto_merge": True}, handle)
    os.chdir(tmp)
    runs = os.path.join(tmp, ".git", "loop", "runs")
    os.makedirs(runs)
    for slug in ("goal1", "goal2"):
        with open(os.path.join(runs, slug + ".json"), "w") as handle:
            json.dump({"slug": slug, "status": "running", "step": "pr", "worktree": tmp, "branch": "loop/" + slug,
                       "pr": "https://example.test/pull/" + slug[-1]}, handle)
    report("goal1", "waiting")
    check(not calls, "a waiting report for a goal at pr, with auto_merge on, runs no merge.py")
    report("goal2", "merged")
    check(not calls, "a merged report for a PR that is still open runs no merge.py for either goal")
    state = sessions.load("goal1")
    check(state.get("status") == "done" and state.get("pr"), "the report still records the goal as done with its pull request")
    worker.release_step(dict(state, release=""))
    check(len(calls) == 1 and calls[0][-1] == "goal1", "the release step for one goal runs merge.py for only that goal")
    os.chdir(here)
subprocess.run = real
# no other monitoring or delivery script starts merge.py or gh pr merge: watch.py and auto.py only advise it in prompts
scripts = os.path.join(here, "..", "..", "skills")
runs = []
for folder in ("workflow-monitoring", "workflow-delivery"):
    for name in sorted(os.listdir(os.path.join(scripts, folder, "scripts"))):
        if name.endswith(".py"):
            text = open(os.path.join(scripts, folder, "scripts", name), encoding="utf-8").read()
            if '"merge.py"' in text or '"pr", "merge"' in text:
                runs.append(name)
check(runs == ["worker.py"], "only worker.py (the worker's own exit) starts merge.py among the monitoring and delivery scripts: %s" % runs)
if not failed:
    print("PASS: #3868: a report merges neither goal; merge.py runs only for the goal it is asked for")
sys.exit(1 if failed else 0)
