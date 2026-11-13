#!/usr/bin/env python3
# windows: ok
# reads: skills/workflow-delivery/scripts/fit.py skills/workflow-delivery/scripts/goal.py
"""DEL-1, issue 3468: `goal.py new --here` refuses in the repo's main checkout and names the worktree command, and passes
in a goal worktree under <common>/loop/worktrees. Calls fit.main_here the way goal.py new does, in throwaway repos."""
import os
import subprocess
import sys
import tempfile
from types import SimpleNamespace

root = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
scripts = os.path.join(root, "skills", "workflow-delivery", "scripts")
sys.path.insert(0, scripts)
import fit  # noqa: E402

failed = []


def check(ok, text):
    print(("PASS: " if ok else "FAIL: ") + text)
    if not ok:
        failed.append(text)


def git(*args):
    return subprocess.run(("git",) + args, check=True, capture_output=True, text=True).stdout.strip()


def refusal():
    """The refusal text main_here raises from the current folder, or ''."""
    def no(text):
        raise SystemExit("REFUSED: " + text)
    try:
        fit.main_here(SimpleNamespace(git=git, no=no), SimpleNamespace(slug="demo"))
    except SystemExit as stop:
        return str(stop)
    return ""


with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
    main = os.path.join(tmp, "repo")
    os.makedirs(main)
    os.chdir(main)
    git("init", "-q", "-b", "main", ".")
    git("config", "user.email", "t@example.test")
    git("config", "user.name", "t")
    git("commit", "-q", "--allow-empty", "-m", "first")
    check(refusal() == "", "#3468: a main checkout of a repo with no worker worktrees is let through")
    os.makedirs(os.path.join(main, ".git", "loop", "worktrees"))
    said = refusal()
    check(said.startswith("REFUSED: --here in the repo's main checkout"), "#3468: the main checkout refuses")
    check("git worktree add -b loop/demo " in said and "/loop/worktrees/demo origin/main" in said, "#3468: the refusal names the worktree command")
    check("\n" not in said, "#3468: the refusal is one line")
    tree = os.path.join(main, ".git", "loop", "worktrees", "demo")
    git("worktree", "add", "-q", "-b", "loop/demo", tree)
    os.chdir(tree)
    check(refusal() == "", "#3468: a goal worktree under loop/worktrees is let through")
    os.chdir(root)

with open(os.path.join(scripts, "goal.py")) as handle:
    check("fit.main_here(" in handle.read(), "#3468: goal.py new calls the check")
print("ALL PASS" if not failed else "%d FAILED" % len(failed))
sys.exit(1 if failed else 0)
