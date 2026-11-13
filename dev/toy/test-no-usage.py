#!/usr/bin/env python3
# windows: ok
# reads: skills/workflow-docs/scripts/docs.py skills/workflow-docs/scripts/criteria.py skills/workflow-docs/scripts/prd.py skills/workflow-docs/scripts/entry.py
# Value: protects=feature pages carry no Usage section, because a feature has no API and the README and the skills' command maps cover usage; fails_when=the docs check passes a page that still has a Usage section, or fails a page that has none; why_new=Usage pages drifted from the commands they described; seam=none; no_claim=a published wiki
"""drop-usage: a temp git repo holding this repo's wiki pages and docs config. The docs check passes; one page gets a
Usage section and the check names USAGE and exits 1; START.md still builds its Features table from the command maps."""
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
DOCS = os.path.join(ROOT, "skills", "workflow-docs", "scripts")
bad = 0


def ok(good, text):
    global bad
    print(("PASS: " if good else "FAIL: ") + text)
    bad += not good


def run(cwd, *args):
    done = subprocess.run(args, cwd=cwd, capture_output=True, text=True)
    return done.returncode, done.stdout + done.stderr


with tempfile.TemporaryDirectory() as tmp:
    for name in ("docs", ".loop", "README.md"):
        src = os.path.join(ROOT, name)
        (shutil.copytree if os.path.isdir(src) else shutil.copy)(src, os.path.join(tmp, name))
    for cmd in (["init", "-q", "-b", "main"], ["add", "-A"], ["-c", "user.name=t", "-c", "user.email=t@example.test", "commit", "-qm", "toy"]):
        run(tmp, "git", *cmd)
    code, out = run(tmp, sys.executable, os.path.join(DOCS, "docs.py"), "check")
    ok("USAGE" not in out and "CHANGED" not in out, "pages with no Usage section raise no USAGE and no CHANGED line")
    page = os.path.join(tmp, "docs", "wiki", "Health.md")
    with open(page, encoding="utf-8", newline="") as handle:
        text = handle.read()
    with open(page, "w", encoding="utf-8", newline="") as handle:
        handle.write(text.replace("\n## Requirements", "\n## Usage\n\n- `/workflow-health check` — Runs the rules.\n\n## Requirements", 1))
    code, out = run(tmp, sys.executable, os.path.join(DOCS, "docs.py"), "check")
    ok(code == 1 and "USAGE Health" in out, "a page that still has a Usage section fails the check with a USAGE line")
    code, out = run(tmp, sys.executable, os.path.join(DOCS, "entry.py"), "render")
    ok("`/workflow-health`:" in out and "Usage" not in out.split("## Features", 1)[-1].split("## Settings table")[0], "START.md's Features table lists each page's skill commands from the command maps")
print("ALL PASS" if not bad else "%d FAILED" % bad)
sys.exit(1 if bad else 0)
