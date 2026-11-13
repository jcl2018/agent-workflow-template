#!/usr/bin/env python3
# windows: ok
# reads: skills/workflow-monitoring/scripts/mend.py skills/workflow-monitoring/scripts/watch.py skills/workflow-monitoring/scripts/worker.py
"""Issue 812: a goal set to `release: ask` keeps its ask across a resume when auto_merge is on.

The resume prompt (mend.release_text, watch.release_text) must not tell the worker to run merge.py, and the worker's
release step must not run merge.py for it; a goal with no ask still gets both."""
import json
import os
import sys
import tempfile

here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(here, "..", "..", "skills", "workflow-monitoring", "scripts"))
import mend  # noqa: E402
import watch  # noqa: E402
import worker  # noqa: E402

failed = []


def check(ok, text):
    print(("PASS: " if ok else "FAIL: ") + text)
    if not ok:
        failed.append(text)


mend.config = watch.config = lambda: {"auto_merge": True}
for name, module in (("resume prompt (mend)", mend), ("goal prompt (watch)", watch)):
    ask = module.release_text({"slug": "g", "release": "ask"})
    check("merge.py" not in ask and "Cut a release or leave" in ask, "#812: a goal set to ask keeps its ask in the %s with auto_merge on" % name)
    plain = module.release_text({"slug": "g", "release": ""})
    check("merge.py g" in plain, "#812: a goal with no ask still gets merge.py in the %s with auto_merge on" % name)

calls = []
worker.merged = lambda url: False
worker.subprocess.run = lambda *a, **k: calls.append(a[0]) or type("R", (), {"returncode": 0, "stdout": "", "stderr": ""})()
with tempfile.TemporaryDirectory() as tree:
    os.makedirs(os.path.join(tree, ".loop"))
    with open(os.path.join(tree, ".loop", "config.json"), "w") as handle:
        json.dump({"auto_merge": True}, handle)
    base = {"slug": "g", "worktree": tree, "status": "done", "pr": "https://example.test/pull/1"}
    worker.release_step(dict(base, release="ask"))
    check(not calls, "#812: the worker's release step does not merge a goal set to ask")
    del calls[:]
    worker.release_step(dict(base, release=""))
    check(len(calls) == 1 and "merge.py" in calls[0][1], "#812: the worker's release step still merges an unresumed goal")

sys.exit(1 if failed else 0)
