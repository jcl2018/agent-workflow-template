#!/usr/bin/env python3
# windows: ok
# reads: skills/workflow-docs/scripts/docs.py skills/workflow-docs/scripts/own.py
"""stale-blocks-all: docs.py check --own turns a stale page the goal's diff doesn't touch into a FINDING line, a page the goal made
stale still fails, and plain check (health, the scheduled run, main itself) still prints main's STALE line.

Builds a throwaway repo: main has page B stale (b.txt changed after B.md); a goal branch changes a.txt or nothing."""
import os
import subprocess
import sys
import tempfile

root = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
docs = os.path.join(root, "skills", "workflow-docs", "scripts", "docs.py")
os.environ["LOOP_ROLE"] = "worker"
fails = 0


def check(name, ok):
    global fails
    print(("PASS: " if ok else "FAIL: ") + name)
    fails += 0 if ok else 1


def git(*args):
    return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "core.autocrlf=false"] + list(args),
                          cwd=repo, capture_output=True, text=True)


def write(path, text):
    full = os.path.join(repo, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", newline="\n") as handle:
        handle.write(text)


def commit(message):
    git("add", "-A")
    git("commit", "-q", "-m", message)


def run(*extra):
    out = subprocess.run([sys.executable, docs, "check"] + list(extra), cwd=repo, capture_output=True, text=True)
    lines = (out.stdout + out.stderr).splitlines()
    return out.returncode, [l for l in lines if l.startswith("STALE ")], [l for l in lines if l.startswith("FINDING ")]


PAGE = "<!-- workflow-docs -->\n# %s\nThis page describes the %s file in this throwaway repo and what it is for today.\n"
repo = tempfile.mkdtemp(prefix="stale-own-")
git("init", "-q", "-b", "main")
write(".loop/config.json", "{}\n")
write(".loop/docs.tsv", "A\ta.txt\nB\tb.txt\n")
write("a.txt", "one\n")
write("b.txt", "one\n")
write("docs/wiki/A.md", PAGE % ("A", "a"))
write("docs/wiki/B.md", PAGE % ("B", "b"))
commit("pages")
write("b.txt", "two\n")
commit("main changes b.txt, so B is stale on main")
git("checkout", "-q", "-b", "goal")

code, stale, found = run()
check("plain check on a goal branch still prints main's STALE B", code == 1 and any("STALE B" in l for l in stale))
code, stale, found = run("--own")
check("--own: a stale page the goal never touched is a FINDING and the check passes",
      code == 0 and not stale and any("STALE B" in l for l in found))
git("checkout", "-q", "main")
code, stale, found = run()
check("plain check on main itself still prints its STALE B (health and the scheduled run keep seeing it)",
      code == 1 and any("STALE B" in l for l in stale))
git("checkout", "-q", "goal")
write("a.txt", "two\n")
commit("the goal changes a.txt, so A goes stale")
code, stale, found = run("--own")
check("--own: a page the goal's own diff made stale still fails", code == 1 and any("STALE A" in l for l in stale))
check("--own: main's stale B stays a FINDING beside it", any("STALE B" in l for l in found) and not any("STALE B" in l for l in stale))
sys.exit(1 if fails else 0)
