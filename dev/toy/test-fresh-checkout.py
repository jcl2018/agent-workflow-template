#!/usr/bin/env python3
# windows: ok
# reads: skills/workflow-monitoring/scripts/operate.py
"""checkout: the operation loop moves a main checkout that is behind origin with --ff-only, says so in one line, and
never makes a merge commit or touches uncommitted work; it says so when it cannot."""
import os
import subprocess
import sys
import tempfile

here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(here, "..", "..", "skills", "workflow-monitoring", "scripts"))
import operate as fresh  # noqa: E402

failed = []


def check(ok, text):
    print(("PASS: " if ok else "FAIL: ") + text)
    if not ok:
        failed.append(text)


def git(where, *args):
    done = subprocess.run(["git", "-C", where] + list(args), capture_output=True, text=True)
    return done.stdout.strip()


def commit(where, name, text):
    with open(os.path.join(where, name), "a", newline="\n") as f:
        f.write(text)
    git(where, "add", "-A")
    git(where, "commit", "-qm", "edit " + name)


with tempfile.TemporaryDirectory() as tmp:
    origin, work, other = (os.path.join(tmp, n) for n in ("origin.git", "work", "other"))
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", origin], check=True)
    for where in (work, other):
        subprocess.run(["git", "clone", "-q", origin, where], check=True, capture_output=True)
        for key, value in (("user.email", "t@example.test"), ("user.name", "t"), ("core.autocrlf", "false")):
            git(where, "config", key, value)
    git(work, "checkout", "-qB", "main")
    os.makedirs(os.path.join(work, ".loop"))
    commit(work, "a.txt", "one\n")
    commit(work, ".loop/queue.md", "queue\n")
    git(work, "push", "-q", "origin", "main")
    git(other, "pull", "-q", "origin", "main")
    common = os.path.join(work, ".git")

    check(fresh.refresh(common) == "", "checkout: a current checkout prints nothing")

    for n in range(3):
        commit(other, "b%d.txt" % n, "x\n")
    git(other, "push", "-q", "origin", "main")
    with open(os.path.join(work, ".loop", "queue.md"), "a") as f:
        f.write("uncommitted line\n")
    line = fresh.refresh(common)
    check(line.startswith("CHECKOUT FAST-FORWARDED main by 3 commits"), "checkout: a checkout 3 behind moves and says so (%s)" % line)
    check(git(work, "rev-parse", "HEAD") == git(other, "rev-parse", "HEAD") and len(git(work, "log", "--merges", "--oneline").splitlines()) == 0,
          "checkout: it is at origin's commit with no merge commit")
    with open(os.path.join(work, ".loop", "queue.md")) as f:
        check("uncommitted line" in f.read(), "checkout: the uncommitted .loop/queue.md is left alone")
    check("\n" not in line, "checkout: the report is one line")

    commit(other, "a.txt", "two\n")
    git(other, "push", "-q", "origin", "main")
    commit(work, "mine.txt", "local\n")
    line = fresh.refresh(common)
    check(line.startswith("CHECKOUT NOT FAST-FORWARDED") and "lacks" in line, "checkout: a diverged checkout is reported, not merged (%s)" % line)
    check(len(git(work, "log", "--merges", "--oneline").splitlines()) == 0, "checkout: still no merge commit")

    git(work, "reset", "-q", "--hard", "origin/main")
    git(work, "checkout", "-qb", "side")
    line = fresh.refresh(common)
    check("is on side, not main" in line, "checkout: a checkout on another branch is reported (%s)" % line)

    git(work, "checkout", "-q", "main")
    commit(other, "a.txt", "three\n")
    git(other, "push", "-q", "origin", "main")
    with open(os.path.join(work, "a.txt"), "a") as f:
        f.write("my uncommitted change\n")
    line = fresh.refresh(common)
    check(line.startswith("CHECKOUT NOT FAST-FORWARDED") and "git refused" in line, "checkout: git refusing over uncommitted work is reported (%s)" % line)
    with open(os.path.join(work, "a.txt")) as f:
        check("my uncommitted change" in f.read(), "checkout: and the uncommitted change survives")
sys.exit(1 if failed else 0)
