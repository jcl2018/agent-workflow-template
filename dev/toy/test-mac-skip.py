#!/usr/bin/env python3
# windows: ok
# reads: dev/toy/test-local-schedule.sh
"""A macOS-only toy run on a host that is not macOS exits 77 with its reason, so its rows are SKIPPED and open no issue."""
import os
import subprocess
import sys

root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
script = os.path.join(root, "dev", "toy", "test-local-schedule.sh")
if sys.platform == "darwin":
    print("SKIP: this is macOS, where the toy runs for real")
    sys.exit(77)
done = subprocess.run(["bash", script], cwd=root, capture_output=True, text=True, timeout=120)
fails = 0
for name, ok in (("a macOS-only toy exits 77 off macOS", done.returncode == 77),
                 ("it says why: SKIP and macOS", "SKIP" in done.stdout and "macOS" in done.stdout),
                 ("it prints no FAIL line", "FAIL" not in done.stdout.replace("fails_when", ""))):
    print(("PASS: " if ok else "FAIL: ") + name)
    fails += 0 if ok else 1
sys.exit(1 if fails else 0)
