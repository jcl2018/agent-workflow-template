#!/usr/bin/env python3
# windows: ok
# reads: dev/toy/test-local-schedule.sh dev/toy/reap.sh
"""A macOS-only toy run on a host that reports Linux exits 77 with its reason and writes the skip file, so a row that pipes
the toy into grep is SKIPPED and opens no issue. A fake `uname` stands in for the Linux host."""
import os
import subprocess
import sys
import tempfile

root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
script = os.path.join(root, "dev", "toy", "test-local-schedule.sh")
if sys.platform == "darwin":
    print("SKIP: this is macOS, where the toy runs for real")
    sys.exit(77)
temp = tempfile.mkdtemp(prefix="macskip-")
fake = os.path.join(temp, "bin")
os.makedirs(fake)
with open(os.path.join(fake, "uname"), "w", newline="\n") as handle:
    handle.write('#!/bin/sh\necho Linux\n')
os.chmod(os.path.join(fake, "uname"), 0o755)
skip = os.path.join(temp, "skip")
env = dict(os.environ, PATH=fake + os.pathsep + os.environ["PATH"], TOY_SKIP_FILE=skip)
done = subprocess.run(["bash", script], cwd=root, capture_output=True, text=True, timeout=120, env=env)
fails = 0
for name, ok in (("a macOS-only toy exits 77 on a Linux host", done.returncode == 77),
                 ("it says why: SKIP and macOS", "SKIP" in done.stdout and "macOS only" in done.stdout),
                 ("it writes the skip file a pipe can't hide", os.path.exists(skip)),
                 ("it prints no FAIL line", "FAIL:" not in done.stdout)):
    print(("PASS: " if ok else "FAIL: ") + name)
    fails += 0 if ok else 1
if fails:
    print(done.stdout[-400:], done.stderr[-400:])
sys.exit(1 if fails else 0)
