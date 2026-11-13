#!/usr/bin/env python3
# windows: ok
# reads: skills/workflow-health/scripts/milestone.py skills/workflow-health/scripts/lean.py
"""REG-7: a full-suite record whose 5th column (rows left unrun) is above 0 WARNs in cost.py and lean.py.

Writes suite-times.tsv in a throwaway git repo and calls both rule functions."""
import os
import subprocess
import sys
import tempfile

root = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(root, "skills", "workflow-health", "scripts"))
import milestone as cost  # noqa: E402
import lean  # noqa: E402

repo = tempfile.mkdtemp()
subprocess.run(["git", "init", "-q", repo], check=True)
os.makedirs(os.path.join(repo, ".git", "loop"))
table = os.path.join(repo, ".git", "loop", "suite-times.tsv")
fails = 0


def check(name, ok):
    global fails
    print(("PASS: " if ok else "FAIL: ") + name)
    fails += not ok


def write(unrun):
    with open(table, "w", newline="\n") as handle:
        handle.write("abcdef123456\tfull\t600\t2026-11-13\t%s\n" % unrun)


write(7)
check("cost.py warns when the newest full line left rows unrun",
      any(r["state"] == "WARN" and "7 rows" in r["detail"] for r in cost.suite_rows(os.path.join(repo, ".git"), 30, {})))
check("lean.py warns when the newest full line left rows unrun",
      any(r["state"] == "WARN" and "7 rows" in r["detail"] for r in lean.unrun_rows(repo)))
write(0)
check("a record with no unrun rows does not warn", not lean.unrun_rows(repo)
      and not any(r["state"] == "WARN" for r in cost.suite_rows(os.path.join(repo, ".git"), 30, {})))
sys.exit(1 if fails else 0)
