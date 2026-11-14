#!/usr/bin/env python3
# windows: ok
# reads: skills/workflow-regression/scripts/lanes.py
"""lane-skips-node-modules (#3939, #3943): the lane's file walk never enters node_modules or __pycache__, so a worktree with a
large node_modules is walked fast and the files it returns are unchanged.

Builds a folder app/ with two real files and a node_modules of 3000 files and a __pycache__, and walks it."""
import os
import sys
import tempfile
import time

root = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.path.insert(0, os.path.join(root, "skills", "workflow-regression", "scripts"))
sys.dont_write_bytecode = True
import lanes  # noqa: E402

fails = 0


def check(name, ok):
    global fails
    print(("PASS: " if ok else "FAIL: ") + name)
    fails += 0 if ok else 1


with tempfile.TemporaryDirectory() as repo:
    for rel in ("app/a.py", "app/sub/b.py"):
        os.makedirs(os.path.dirname(os.path.join(repo, rel)), exist_ok=True)
        open(os.path.join(repo, rel), "w").close()
    for n in range(3000):
        folder = os.path.join(repo, "app", "node_modules", "pkg%d" % (n % 50))
        os.makedirs(folder, exist_ok=True)
        open(os.path.join(folder, "f%d.js" % n), "w").close()
    os.makedirs(os.path.join(repo, "app", "__pycache__"))
    open(os.path.join(repo, "app", "__pycache__", "a.cpython-313.pyc"), "w").close()
    calls = []
    real = os.walk

    def counting(top, *a, **k):
        for entry in real(top, *a, **k):
            calls.append(entry[0])
            yield entry

    os.walk = counting
    start = time.time()
    found = sorted(p.replace("\\", "/") for p in lanes.walk(repo, "app/"))
    took = time.time() - start
    os.walk = real
    check("the walk returns only the real files", found == ["app/a.py", "app/sub/b.py"])
    check("the walk never enters node_modules or __pycache__", not any("node_modules" in c or "__pycache__" in c for c in calls))
    check("the walk is fast with 3000 files in node_modules", took < 2)

print("ALL PASS" if not fails else "%d FAILED" % fails)
sys.exit(1 if fails else 0)
