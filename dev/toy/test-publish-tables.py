#!/usr/bin/env python3
# windows: ok
# reads: skills/workflow-release/scripts/wiki.py skills/workflow-docs/scripts/criteria.py skills/workflow-docs/scripts/docs.py
"""DOC-11: the publish tree re-renders generated Tests tables, so a generated-only staleness never blocks the wiki; a stale
hand-written page still refuses. Runs on a throwaway detached worktree of HEAD."""
import os
import shutil
import subprocess
import sys
import tempfile

root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
scripts = os.path.join(root, "skills", "workflow-release", "scripts")
docs = os.path.join(root, "skills", "workflow-docs", "scripts", "docs.py")
sys.path.insert(0, scripts)
os.environ["LOOP_ROLE"] = "worker"
import wiki  # noqa: E402

fails = 0


def check(name, ok):
    global fails
    print(("PASS: " if ok else "FAIL: ") + name)
    fails += 0 if ok else 1


def git(*args, cwd):
    return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t"] + list(args), cwd=cwd, capture_output=True, text=True)


def stale(tree):
    out = subprocess.run([sys.executable, docs, "check"], cwd=tree, capture_output=True, text=True)
    return [l for l in (out.stdout + out.stderr).splitlines() if l.startswith("STALE ")]


temp = tempfile.mkdtemp(prefix="pubtables-")
tree = os.path.join(temp, "tree")
try:
    git("worktree", "add", "-q", "--detach", tree, "HEAD", cwd=root)
    tests = os.path.join(tree, "docs", "wiki", "Tests.md")
    with open(tests, encoding="utf-8") as handle:
        text = handle.read()
    with open(tests, "w", encoding="utf-8", newline="") as handle:
        handle.write(text + "\nA stale generated line.\n")
    git("commit", "-qam", "make Tests stale", cwd=tree)
    check("setup: a corrupted Tests page is STALE Tests", any(l.startswith("STALE Tests") for l in stale(tree)))
    pages = wiki.rerender(tree, {})
    check("rerender names the Tests page", "Tests" in pages)
    check("after rerender no STALE Tests", not any(l.startswith("STALE Tests") for l in stale(tree)))
    check("the re-render is committed in the tree", not git("status", "--porcelain", "--", "docs/wiki", cwd=tree).stdout.strip())
    check("generated-only staleness: a second rerender changes nothing", wiki.rerender(tree, {}) == [])
    # a hand-written page: change a path it maps, in a later commit than the page
    rows = [l.split("\t") for l in open(os.path.join(tree, ".loop", "docs.tsv"), encoding="utf-8").read().splitlines() if l.strip()]
    page, path = None, None
    held = [l.split()[1] for l in stale(tree)]
    for row in rows:
        if len(row) > 1 and row[0] not in ("Home", "Tests") and row[0] not in held and os.path.isfile(os.path.join(tree, row[1].split(",")[0].strip())):
            page, path = row[0], row[1].split(",")[0].strip()
            break
    if page and os.path.isfile(os.path.join(tree, path)):
        with open(os.path.join(tree, path), "a", encoding="utf-8", newline="") as handle:
            handle.write("\n")
        git("commit", "-qam", "touch a mapped path", cwd=tree)
        wiki.rerender(tree, {})
        check("a stale hand-written page (%s) still refuses after rerender" % page, any(l.startswith("STALE " + page) for l in stale(tree)))
    else:
        check("a mapped hand-written page and path exist for the toy", False)
finally:
    git("worktree", "remove", "--force", tree, cwd=root)
    shutil.rmtree(temp, ignore_errors=True)
sys.exit(1 if fails else 0)
