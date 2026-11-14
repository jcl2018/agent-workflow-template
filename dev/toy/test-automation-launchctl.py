#!/usr/bin/env python3
# windows: ok
# reads: skills/workflow-docs/scripts/audit.py skills/workflow-docs/scripts/counting.py skills/workflow-docs/scripts/docs.py
"""automation-launchctl-windows: docs.py automation reports a routine's live state as unknown, and exits 0, when the program
that would answer (launchctl, gh) is missing, instead of crashing with FileNotFoundError.

Builds a throwaway repo whose config names a mac and a github routine, and runs docs.py with launchctl and gh made missing."""
import json
import os
import subprocess
import sys
import tempfile

root = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
docs = os.path.join(root, "skills", "workflow-docs", "scripts", "docs.py")
fails = 0


def check(name, ok):
    global fails
    print(("PASS: " if ok else "FAIL: ") + name)
    fails += 0 if ok else 1


with tempfile.TemporaryDirectory() as tmp:
    repo = os.path.join(tmp, "repo")
    os.makedirs(os.path.join(repo, ".loop"))
    subprocess.run(["git", "init", "-q", repo], check=True)
    cfg = {"automation": [{"name": "nightly-mac", "does": "x", "cadence": "daily", "runs": "mac:com.toy.nightly"},
                          {"name": "toy-flow", "does": "y", "cadence": "daily", "runs": "github:toy.yml"}]}
    with open(os.path.join(repo, ".loop", "config.json"), "w") as handle:
        json.dump(cfg, handle)
    shim = ("import os, runpy, subprocess, sys" + chr(10) + "orig = subprocess.run" + chr(10)
            + "def run(cmd, *a, **k):" + chr(10) + "    if cmd[0] in ('launchctl', 'gh'):" + chr(10)
            + "        raise FileNotFoundError(cmd[0])" + chr(10) + "    return orig(cmd, *a, **k)" + chr(10)
            + "subprocess.run = run" + chr(10) + "sys.path.insert(0, os.path.dirname(sys.argv[1]))" + chr(10)
            + "script = sys.argv[1]" + chr(10) + "sys.argv = [script, 'automation']" + chr(10)
            + "runpy.run_path(script, run_name='__main__')" + chr(10))
    env = dict(os.environ, LOOP_ROLE="worker", PYTHONDONTWRITEBYTECODE="1")
    done = subprocess.run([sys.executable, "-c", shim, docs], cwd=repo, env=env, capture_output=True, text=True)
    out = done.stdout + done.stderr
    check("automation exits 0 with no launchctl and no gh", done.returncode == 0)
    check("a mac routine's state is unknown when launchctl is missing", "nightly-mac: unknown: launchctl" in out)
    check("a github routine's state is unknown when gh is missing", "toy-flow: unknown: gh" in out)
    check("no traceback", "Traceback" not in out)

print("ALL PASS" if not fails else "%d FAILED" % fails)
sys.exit(1 if fails else 0)
