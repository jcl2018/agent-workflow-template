#!/usr/bin/env python3
# windows: ok
# reads: skills/workflow-regression/scripts/tiers.py
"""DEL-15, affected-only rerun: a lane that runs again after main moved reruns a row only when the paths changed since it last
ran reach it AND the goal's own diff reaches it. A row only main's new commits reach keeps its earlier result."""
import os
import sys

here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(here, "..", "..", "skills", "workflow-regression", "scripts"))
import tiers  # noqa: E402

failed = []


def check(ok, text):
    print(("PASS: " if ok else "FAIL: ") + text)
    if not ok:
        failed.append(text)


GOAL = ["g.py"]  # the goal's own diff against the base
SINCE = ["m.py", "g.py"]  # changed since the row last ran: main's new commit m.py and the goal's g.py
tiers.since = lambda root, row, old, ok, base, memo: ("c0", list(SINCE))
tiers.changed = lambda root, commit, memo: list(GOAL)
tiers.ancestor = lambda root, commit, memo: True
tiers.hit = lambda root, row, path, at, cache, memo: path in row["reads"]
tiers.lanes.table = lambda root, at, name, memo: {"r": "same"}
tiers.lanes.closure = lambda root, command, cache: ([], False)
memo = {"tsv": {"r": "same"}}
old = {"rows": {"r": {"commit": "c0", "status": "PASS"}}}


def why(reads, record=old, goal=None):
    GOAL[:] = goal or ["g.py"]
    return tiers.reason("/", {"id": "r", "command": "x", "reads": reads}, record, True, "base", {}, memo)


check(why(["m.py"]) == "", "a row only main's new commit reaches is reused, not rerun")
check(why(["m.py", "g.py"]).startswith("reaches"), "a row both main's commit and the goal's diff reach reruns")
check(why(["g.py"]).startswith("reaches"), "a row only the goal's diff reaches reruns")
check(why(["m.py"], goal=["m.py"]).startswith("reaches"), "a row the goal's own diff also changes in a path main touched reruns")
check(why(["m.py"], {"rows": {}}).startswith("reaches"), "a row with no earlier result still runs")
if not failed:
    print("PASS: DEL-15: a main-moved rerun runs only the rows both the goal's diff and main's new commits reach")
sys.exit(1 if failed else 0)
