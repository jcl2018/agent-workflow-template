#!/usr/bin/env python3
# windows: ok
# reads: dev/package.py skills/
"""DEL-5, SET-3 (package-gate): a pull request whose merged head breaks the package fails its lane.

Runs dev/package.py's own checks (walk, check_files, check_scripts: the 99-file cap, the 20,480-byte script cap and
`--help` run alone with only its sibling files) on the tracked files of this checkout, in plain Python, so it
runs on Windows too (the package-passes row skips there). The controls build a small package and show each rule fails.

usage: test-package-gate.py [controls|head]   one part only, so a row's exit status is its answer and its failure prints why
PACKAGE_GATE_ROOT names the checkout whose tracked files the head part checks (default: this one; the toy sets it for its controls)."""
import contextlib
import importlib.util
import io
import os
import shutil
import subprocess
import sys
import tempfile

here = os.path.dirname(os.path.abspath(__file__))
root = os.path.abspath(os.path.join(here, "..", ".."))
spec = importlib.util.spec_from_file_location("package", os.path.join(root, "dev", "package.py"))
pk = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pk)
failed = []


def check(ok, text):
    print(("PASS: " if ok else "FAIL: ") + text)
    if not ok:
        failed.append(text)


def verdict(tree):
    """package.py's own file and script checks on a tree: the failures it prints, as 'rule: text' lines."""
    del pk.failures[:]
    files = pk.walk(tree)
    with contextlib.redirect_stdout(io.StringIO()):  # package.py prints each FAIL as it finds it; the lines below say it once
        pk.check_files(tree, files)
        pk.check_scripts(tree, files)
    return len(files), ["%s: %s" % item for item in pk.failures]


def put(tree, rel, text):
    path = os.path.join(tree, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="\n") as handle:
        handle.write(text)


OK = '"""A script that runs alone."""\nimport os\nprint(os.name)\n'
def controls(tmp):
    tree = os.path.join(tmp, "base")
    put(tree, "skills/demo/scripts/ok.py", OK)
    count, found = verdict(tree)
    check(not found, "control: a small package passes package.py's file and script checks (%d file)" % count)
    big = os.path.join(tmp, "big")
    shutil.copytree(tree, big)
    put(big, "skills/demo/scripts/big.py", OK + "#" + "x" * 20500 + "\n")
    check(any("big.py is" in line and "bytes" in line for line in verdict(big)[1]), "control: a script over 20,480 bytes fails the package")
    many = os.path.join(tmp, "many")
    shutil.copytree(tree, many)
    for number in range(99):
        put(many, "skills/demo/references/r%02d.md" % number, "text\n")
    check(any(line.startswith("Size:") and "files" in line for line in verdict(many)[1]), "control: more than 99 files fails the package")
    alone = os.path.join(tmp, "alone")
    shutil.copytree(tree, alone)
    put(alone, "skills/demo/scripts/needs.py", "import sibling_skill_helper\n")
    check(any("needs.py" in line for line in verdict(alone)[1]), "control: a script that needs a file outside its own folder fails the package")


def head_of(tmp):
    """The tracked files of PACKAGE_GATE_ROOT (else this checkout) copied to a new tree and put through package.py's checks."""
    top = os.environ.get("PACKAGE_GATE_ROOT") or root
    head = os.path.join(tmp, "head")
    names = subprocess.run(["git", "ls-files", "-z", "skills", "listing.json", "README.md", "LICENSE"], cwd=top, capture_output=True).stdout
    for rel in filter(None, names.decode("utf-8").split("\0")):
        if os.path.isfile(os.path.join(top, rel)):
            os.makedirs(os.path.dirname(os.path.join(head, rel)) or head, exist_ok=True)
            shutil.copyfile(os.path.join(top, rel), os.path.join(head, rel))
    count, found = verdict(head)
    for line in found:
        print("FAIL: head: " + line)
    check(not found, "head: this checkout's package passes the file and script checks (%d files, %d failures)" % (count, len(found)))


part = sys.argv[1] if len(sys.argv) > 1 else "all"
with tempfile.TemporaryDirectory() as tmp:
    if part in ("all", "controls"):
        controls(tmp)
    if part in ("all", "head"):
        head_of(tmp)
sys.exit(1 if failed else 0)
