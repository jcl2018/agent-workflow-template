#!/usr/bin/env python3
# windows: ok
# reads: skills/workflow-docs/scripts/pageformat.py skills/workflow-docs/scripts/counting.py skills/workflow-docs/scripts/criteria.py
"""drop-usage: a Runbook and Deployments stay separate sections but link. A Runbook's Output may name the Deployments row
it produces ('Deployments row: NAME'), and the docs check verifies that row exists; the generated Automation block links
each routine to its page's Runbook."""
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "skills", "workflow-docs", "scripts"))
import counting  # noqa: E402
import pageformat as pf  # noqa: E402

bad = 0


def ok(good, text):
    global bad
    print(("PASS: " if good else "FAIL: ") + text)
    bad += not good


deploy = [(30, "| Row | Where |"), (31, "|---|---|"), (32, "| Health digest | issue |")]
run = lambda text: [(10, "- **Output:** " + text), (11, "- **Never:** shortcuts")]
ok(pf.linked("Health", "Runbook", run("one comment (Deployments row: Health digest)."), deploy) == [], "an Output naming an existing Deployments row passes")
missing = pf.linked("Health", "Runbook", run("one comment (Deployments row: Nope)."), deploy)
ok(len(missing) == 1 and "Nope" in str(missing), "an Output naming a Deployments row that does not exist is refused, naming it")
ok(pf.linked("Health", "Runbook", run("one comment, no clause."), deploy) == [], "an Output with no Deployments row clause passes")
ok(len(pf.linked("Health", "Runbook", [(10, "- **Output:** one comment (Deployments row: Gone)")], [])) == 1, "an Output naming a row on a page with no Deployments section is refused")

with tempfile.TemporaryDirectory() as tmp:
    shutil.copytree(os.path.join(ROOT, ".loop"), os.path.join(tmp, ".loop"))
    for cmd in (["init", "-q", "-b", "main"], ["remote", "add", "origin", "https://github.com/o/r.git"]):
        subprocess.run(["git", "-C", tmp] + cmd, capture_output=True)
    block = counting.automation_block(tmp)
    ok("[health](https://github.com/o/r/wiki/Health#health-round)" in block, "the Automation block links health to its page's Runbook")
    ok("[regression](https://github.com/o/r/wiki/Regression#regression-round)" in block, "the Automation block links regression to its page's Runbook")
    ok("[digest email](" not in block, "a routine with no Runbook stays plain text")
print("ALL PASS" if not bad else "%d FAILED" % bad)
sys.exit(1 if bad else 0)
