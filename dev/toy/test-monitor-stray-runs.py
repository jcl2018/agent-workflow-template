#!/usr/bin/env python3
# windows: ok
# reads: skills/workflow-monitoring/scripts/monitor.py
"""MON-3: a file in loop/runs that is not a run record (a list, a bare string) is skipped; report and dashboard still print."""
import json
import os
import subprocess
import sys
import tempfile

here = os.path.dirname(os.path.abspath(__file__))
monitor = os.path.join(here, "..", "..", "skills", "workflow-monitoring", "scripts", "monitor.py")
fails = 0


def check(ok, text):
    global fails
    print(("PASS: " if ok else "FAIL: ") + text)
    fails += 0 if ok else 1


repo = tempfile.mkdtemp()
git = ["git", "-c", "user.name=t", "-c", "user.email=t@t"]
subprocess.run(git + ["init", "-q", repo], check=True)
os.makedirs(os.path.join(repo, ".loop"))
with open(os.path.join(repo, ".loop", "config.json"), "w") as handle:
    json.dump({"version": 1}, handle)
runs = os.path.join(repo, ".git", "loop", "runs")
os.makedirs(runs)
with open(os.path.join(runs, "issues.json"), "w") as handle:
    json.dump([{"number": 1}], handle)
with open(os.path.join(runs, "note.json"), "w") as handle:
    json.dump("text", handle)
with open(os.path.join(runs, "real.json"), "w") as handle:
    json.dump({"slug": "real", "status": "running", "goal": "g"}, handle)
for command in ("report", "dashboard"):
    done = subprocess.run([sys.executable, monitor, command], cwd=repo, capture_output=True, text=True)
    check(done.returncode == 0 and "Traceback" not in done.stderr, "%s exits 0 with a list-shaped file in runs (%s)" % (command, done.stderr.strip()[-120:]))
    if command == "report":
        check("real" in done.stdout, "report still lists the real run")
sys.exit(1 if fails else 0)
