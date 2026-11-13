#!/usr/bin/env python3
# windows: ok
# reads: dev/package.py dev/toy/test-package-gate.py dev/toy/test-package-headroom.py .loop/regression.tsv
"""SET-3 (package-rows-tracked): the package rows count only the files git tracks, and a failing row prints why.

Each control builds a small git repo, adds files git does not track (__pycache__, .pyc, a stray file under skills/) and
shows package.py's walk, the headroom row and the gate row ignore them; a tracked breach still fails with its reason."""
import importlib.util
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


def put(tree, rel, text):
    path = os.path.join(tree, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="\n") as handle:
        handle.write(text)


def git(tree, *args):
    return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "-C", tree] + list(args), capture_output=True, text=True)


def repo(tmp, name, extra=()):
    """A git repo holding a tiny package (tracked), then loose files git does not track."""
    tree = os.path.join(tmp, name)
    put(tree, "skills/demo/SKILL.md", "---\nname: demo\n---\nx\n")
    put(tree, "skills/demo/scripts/ok.py", '"""Runs alone."""\nprint(1)\n')
    put(tree, "README.md", "r\n")
    for rel, text in extra:
        put(tree, rel, text)
    git(tree, "init", "-q")
    git(tree, "add", "-A")
    git(tree, "commit", "-q", "-m", "x")
    return tree


def loose(tree):
    put(tree, "skills/demo/scripts/__pycache__/ok.cpython-312.pyc", "x")
    put(tree, "skills/demo/scripts/__pycache__/other.cpython-312.pyc", "x")
    put(tree, "skills/demo/lane-output.txt", "x")


def run(*args, env=None):
    done = subprocess.run([sys.executable] + list(args), capture_output=True, text=True, env=dict(os.environ, **(env or {})))
    return done.returncode, done.stdout + done.stderr


with tempfile.TemporaryDirectory() as tmp:
    tree = repo(tmp, "clean")
    base = pk.walk(tree)
    check(base == ["README.md", "skills/demo/SKILL.md", "skills/demo/scripts/ok.py"], "control: a clean checkout walks its three tracked files (%s)" % base)
    loose(tree)
    now = pk.walk(tree)
    check(now == base, "walk counts only tracked files: 3 loose files, __pycache__ and .pyc among them, add none (%d)" % len(now))
    check(not [f for f in now if f.endswith("/") or "__pycache__" in f], "walk lists no forbidden folder for an untracked __pycache__")

    plain = os.path.join(tmp, "plain")
    put(plain, "skills/demo/scripts/ok.py", "print(1)\n")
    put(plain, "skills/demo/scripts/__pycache__/ok.pyc", "x")
    found = pk.walk(plain)
    check("skills/demo/scripts/__pycache__/" in found, "outside a git checkout the walk still sees the folder, so a loose package is still checked (%s)" % found)

    vendor = repo(tmp, "vendor", [("skills/demo/vendor/lib.py", "x = 1\n")])
    check("skills/demo/vendor/" in pk.walk(vendor), "a forbidden folder that git does track still fails the package")

    gone = repo(tmp, "gone")
    os.remove(os.path.join(gone, "README.md"))
    check("README.md" not in pk.walk(gone), "a tracked file deleted from the working tree is not walked")

    nested = os.path.join(tmp, "outer")
    inner = repo(nested, "inner")
    check("README.md" in pk.walk(inner), "a package folder inside another repo is walked from its own top")
    sub = os.path.join(inner, "pkg")
    put(sub, "skills/demo/scripts/ok.py", "print(1)\n")
    check(pk.walk(sub) == ["skills/demo/scripts/ok.py"], "a folder inside a repo, not its top, falls back to the folder walk")

    # the headroom row counts through package.walk, so loose files cannot push it over 98
    code, text = run(os.path.join(here, "test-package-headroom.py"))
    check(code == 0 and "the package holds" in text, "the headroom row passes here with its count printed")
    loose_here = os.path.join(root, "skills", "workflow-docs", "scripts", "__pycache__")
    made = not os.path.isdir(loose_here)
    os.makedirs(loose_here, exist_ok=True)
    for n in range(90):
        put(loose_here, "pad%02d.pyc" % n, "x")
    try:
        code, text = run(os.path.join(here, "test-package-headroom.py"))
        check(code == 0, "the headroom row still passes with 90 loose .pyc files in the checkout")
        code, text = run(os.path.join(here, "test-package-caps.py"))
        check(code == 0, "the caps row still passes with 90 loose .pyc files in the checkout")
    finally:
        if made:
            shutil.rmtree(loose_here, ignore_errors=True)
        else:
            for n in range(90):
                os.remove(os.path.join(loose_here, "pad%02d.pyc" % n))

    # the gate's head row names what broke: a tracked script of 20,480 bytes in a stand-in checkout
    big = repo(tmp, "big", [("skills/demo/scripts/big.py", '"""Big."""\n#' + "x" * 20500 + "\n")])
    code, text = run(os.path.join(here, "test-package-gate.py"), "head", env={"PACKAGE_GATE_ROOT": big})
    check(code == 1 and "FAIL: head: Scripts: skills/demo/scripts/big.py is" in text, "gate head fails a tracked script over the cap and prints which (%s)" % text.strip()[-120:])
    code, text = run(os.path.join(here, "test-package-gate.py"), "head", env={"PACKAGE_GATE_ROOT": tree})
    check(code == 0 and "PASS: head:" in text, "gate head passes a clean stand-in checkout, loose files and all")

# a row that swallows its toy's output with grep -q hides the reason it failed
rows = {}
with open(os.path.join(root, ".loop", "regression.tsv"), encoding="utf-8") as handle:
    for line in handle:
        cells = line.rstrip("\n").split("\t")
        rows[cells[0]] = cells[2] if len(cells) > 2 else ""
for name in ("package-caps-held", "package-headroom-held", "package-gate-head", "settings-render-fresh"):
    command = rows.get(name, "")
    check(bool(command) and " -q" not in command and "grep -qF" not in command, "row %s keeps the reason: no grep -q swallows its output (%s)" % (name, command[:70]))

sys.exit(1 if failed else 0)
