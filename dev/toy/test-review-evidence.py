#!/usr/bin/env python3
# windows: ok
# reads: skills/workflow-health/scripts/judge.py skills/workflow-health/scripts/file.py
"""HLT-9: a review finding cites a file and line or a test row, else it is dropped; an answered review closes the open
review issues it no longer raises. Calls judge.located and file.plan directly: no repo, no network."""
import os
import sys

root = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(root, "skills", "workflow-health", "scripts"))
import judge  # noqa: E402
import file as filing  # noqa: E402

fails = 0


def check(name, ok):
    global fails
    print(("PASS: " if ok else "FAIL: ") + name)
    fails += not ok


rows = {"row-a"}
check("a file and line counts as evidence", judge.located("docs/wiki/Calc.md:3", rows) and judge.located("a/b.py:3-9", rows))
check("a test row counts as evidence", judge.located("row-a", rows))
check("a requirement id, an issue link or a file with no line alone do not", not any(
    judge.located(c, rows) for c in ("CAL-1", "#12", "docs/wiki/Calc.md", "row-b")))

old = {"review:Calc:gap": {"number": 7, "state": "open", "labels": ["health", "health:review-gap"], "body": ""}}
close = lambda reviewed: [a["number"] for a in filing.plan([], old, ["review"], reviewed=reviewed, root="") if a["kind"] == "close"]
check("an answered review that no longer raises an open review issue closes it", close(True) == ["7"])
check("a review the judge did not answer closes nothing", close(False) == [])
sys.exit(1 if fails else 0)
