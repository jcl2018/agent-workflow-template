#!/usr/bin/env python3
# windows: ok
# reads: skills/workflow-release/scripts/mergebatch.py
"""DEL-15, batch merge: ready goals with disjoint touches group into batches of 3 or 4; a failing batch splits to name the culprit."""
import json
import os
import subprocess
import sys
import tempfile

here = os.path.dirname(os.path.abspath(__file__))
script = os.path.join(here, "..", "..", "skills", "workflow-release", "scripts", "mergebatch.py")
sys.path.insert(0, os.path.dirname(script))
import mergebatch  # noqa: E402

failed = []


def check(ok, text):
    print(("PASS: " if ok else "FAIL: ") + text)
    if not ok:
        failed.append(text)


goals = [("a", ["x"]), ("b", ["y"]), ("c", ["z"]), ("d", ["w"]), ("e", ["x/1"])]
names = [[slug for slug, _ in batch] for batch in mergebatch.group(goals, 3)]
check(names == [["a", "b", "c"], ["d", "e"]], "ready goals group into batches of 3 whose touches overlap none of their batch-mates: %s" % names)
check([len(b) for b in mergebatch.group([(str(i), [str(i)]) for i in range(9)], 9)] == [4, 4, 1], "a batch holds at most 4 goals")
check(mergebatch.group([("p", ["a"]), ("q", [])], 3) == [[("p", ["a"])], [("q", [])]], "a goal with no touches overlaps everything and batches alone")
check(mergebatch.culprits(["a", "b", "c"], lambda part: True) == [], "a batch of 3 passing goals has no culprit and merges together")
seen = []
found = mergebatch.culprits(["a", "b", "c", "d"], lambda part: seen.append(list(part)) or "c" not in part)
check(found == ["c"] and len(seen) <= 6, "a failing batch splits and names the one culprit in a few checks: %s after %d" % (found, len(seen)))
both = mergebatch.culprits(["a", "b", "c"], lambda part: not ("a" in part and "c" in part))
check(both == ["a+b+c"], "a failure between goals that pass alone is named for the whole batch, not hidden: %s" % both)
with tempfile.TemporaryDirectory() as tmp:
    subprocess.run(["git", "init", "-q", tmp], check=True)
    runs = os.path.join(tmp, ".git", "loop", "runs")
    os.makedirs(runs)
    for slug, touches, extra in (("g1", ["skills/a"], {}), ("g2", ["skills/b"], {}), ("g3", ["skills/c"], {}), ("g4", ["skills/d"], {"hold_at": "now"}),
                                 ("g5", ["skills/a/x"], {}), ("g6", ["skills/e"], {"status": "running"})):
        with open(os.path.join(runs, slug + ".json"), "w") as handle:
            json.dump(dict({"slug": slug, "status": "done", "pr": "https://example.test/pull/1", "touches": touches}, **extra), handle)
    out = subprocess.run([sys.executable, script, "plan"], cwd=tmp, capture_output=True, text=True).stdout.splitlines()
    check(out == ["BATCH 1: g1, g2, g3", "BATCH 2: g5"], "plan lists the ready, unheld goals in batches and leaves held and running goals out: %s" % out)
    os.chdir(here)
if not failed:
    print("PASS: DEL-15: a batch of 3 passing goals merges together and a failing batch splits to name the culprit")
sys.exit(1 if failed else 0)
