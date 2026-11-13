#!/usr/bin/env python3
# windows: ok
# reads: skills/workflow-release/scripts/release.py skills/workflow-release/scripts/autorelease.py
# reads: skills/workflow-delivery/scripts/fit.py
"""DEL-5, issue 3787: the goal's recorded bump wins on a docs-only goal; with none it stays a leave (a patch).

Builds a throwaway repo whose branch changes only a .md file, then asks release.auto_need what the release needs
with and without a recorded `goal.py set --bump minor` (the `set.bump` of the goal's extra record)."""
import json
import os
import subprocess
import sys
import tempfile

here = os.path.dirname(os.path.abspath(__file__))
root = os.path.abspath(os.path.join(here, "..", ".."))
sys.path.insert(0, os.path.join(root, "skills", "workflow-release", "scripts"))
sys.path.insert(0, os.path.join(root, "skills", "workflow-delivery", "scripts"))
import release  # noqa: E402

failed = []


def check(ok, text):
    print(("PASS: " if ok else "FAIL: ") + text)
    if not ok:
        failed.append(text)


def git(*args):
    subprocess.run(("git",) + args, check=True, capture_output=True, text=True)


with tempfile.TemporaryDirectory() as tmp:
    os.chdir(tmp)
    git("init", "-q", "-b", "main", ".")
    git("config", "user.email", "t@example.test")
    git("config", "user.name", "t")
    git("config", "core.autocrlf", "false")
    os.makedirs(".loop")
    with open(os.path.join(".loop", "config.json"), "w") as f:
        json.dump({"base": "main", "release_auto": True}, f)
    with open("notes.md", "w") as f:
        f.write("one\n")
    git("add", "-A")
    git("commit", "-qm", "base")
    git("switch", "-qc", "loop/docsonly")
    with open("notes.md", "a") as f:
        f.write("two\n")
    git("commit", "-qam", "docs only")
    runs = os.path.join(tmp, ".git", "loop", "runs")
    os.makedirs(runs)
    release.save = lambda state, note="": None
    state = {"slug": "docsonly"}

    part, why = release.auto_need(tmp, dict(state))
    check(part == "leave", "#3787: a docs-only goal with no bump releases a patch (need: %s)" % part)

    with open(os.path.join(runs, "docsonly.extra.json"), "w") as f:
        json.dump({"set": {"bump": "minor"}}, f)
    part, why = release.auto_need(tmp, dict(state))
    check(part == "minor", "#3787: a docs-only goal with goal.py set --bump minor releases a minor (need: %s)" % part)
    os.chdir(root)

sys.exit(1 if failed else 0)
