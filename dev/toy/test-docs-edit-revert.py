#!/usr/bin/env python3
# windows: ok
# reads: skills/workflow-docs/scripts/docs.py skills/workflow-docs/scripts/counting.py skills/workflow-docs/scripts/pageformat.py
"""DOC-9, DOC-10: a page a branch edited and then put back is still judged, so merging that branch doesn't stale it (#3875).

The release's wiki step may undo an edit on the branch (a line in a generated section). The page then reads the same as
before, and once the branch is merged git's history simplification hides both commits, so the code commits looked newer
than the page and the check said STALE. The page's judged commits are read with --full-history."""
import os
import subprocess
import sys
import tempfile

root = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
docs = os.path.join(root, "skills", "workflow-docs", "scripts", "docs.py")
failed = []


def git(tmp, *args):
    subprocess.run(["git", "-C", tmp, "-c", "user.name=t", "-c", "user.email=t@t", *args], check=True, capture_output=True)


def write(tmp, rel, text):
    path = os.path.join(tmp, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="\n") as handle:
        handle.write(text)


def commit(tmp, message):
    git(tmp, "add", "-A")
    git(tmp, "commit", "-q", "-m", message)


PAGE = "<!-- workflow-docs -->\n# Calc\n\nThe calc script reads a list of numbers and prints the median, the mean and the spread of them.\n"
with tempfile.TemporaryDirectory() as tmp:
    git(tmp, "init", "-q", "-b", "main")
    write(tmp, "src/calc.py", "print(1)\n")
    write(tmp, "docs/wiki/Calc.md", PAGE)
    write(tmp, ".loop/docs.tsv", "Calc\tsrc\n")
    write(tmp, ".loop/config.json", '{"base": "main"}\n')
    commit(tmp, "start")
    git(tmp, "switch", "-q", "-c", "goal")
    write(tmp, "src/calc.py", "print(2)\n")
    commit(tmp, "Calc code")
    write(tmp, "docs/wiki/Calc.md", PAGE + "\nA line the wiki step later removes.\n")
    commit(tmp, "Calc page: add a line")
    write(tmp, "docs/wiki/Calc.md", PAGE)
    commit(tmp, "Wiki: update pages (the line removed again)")
    git(tmp, "switch", "-q", "main")
    git(tmp, "merge", "-q", "--no-ff", "-m", "Merge goal", "goal")
    done = subprocess.run([sys.executable, docs, "check"], cwd=tmp, capture_output=True, text=True)
    out = done.stdout + done.stderr
    ok = "STALE" not in out
    print(("PASS: " if ok else "FAIL: ") + "a merged branch that edited a page and put it back leaves the page current, not STALE" + ("" if ok else ": " + out.strip()[:200]))
    if not ok:
        failed.append(out)
    # the page's own edit still counts: a code change after the merge makes it stale again
    write(tmp, "src/calc.py", "print(3)\n")
    commit(tmp, "Calc code again")
    again = subprocess.run([sys.executable, docs, "check"], cwd=tmp, capture_output=True, text=True).stdout
    ok = "STALE Calc" in again
    print(("PASS: " if ok else "FAIL: ") + "a later code change after the merge still makes the page STALE")
    if not ok:
        failed.append(again)
if not failed:
    print("PASS: DOC-9: a page edited and put back on a merged branch is judged by its commits, not STALE")
sys.exit(1 if failed else 0)
