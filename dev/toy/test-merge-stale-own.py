#!/usr/bin/env python3
# windows: ok
# reads: skills/workflow-release/scripts/wiki.py skills/workflow-release/scripts/merge.py skills/workflow-docs/scripts/audit.py
"""merge-stale-own (#3941): merge.py's wiki check (wiki.pending) refuses only for a page the goal's own diff made stale,
the scope of docs.py check --own. A page stale from a commit the goal never touched is a FINDING line, and on main itself
every stale page still counts.

Builds a throwaway repo: main has page B stale (b.txt changed after B.md); a goal branch changes a.txt (A goes stale) or
nothing mapped. usage: test-merge-stale-own.py"""
import contextlib
import io
import os
import subprocess
import sys
import tempfile

root = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.path.insert(0, os.path.join(root, "skills", "workflow-release", "scripts"))
os.environ["LOOP_ROLE"] = "worker"
import wiki  # noqa: E402

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


def pending():
    """(the stale lines wiki.pending returns, what it printed)."""
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        lines = wiki.pending(repo, {})
    return [l for l in lines if ": STALE " in l], out.getvalue()


PAGE = "<!-- workflow-docs -->\n# %s\nThis page describes the %s file in this throwaway repo and what it is for today.\n"
repo = tempfile.mkdtemp(prefix="merge-stale-own-")
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
git("update-ref", "refs/remotes/origin/main", "main")
git("checkout", "-q", "-b", "goal")
write("c.txt", "goal work\n")  # the goal's own commit touches no mapped path
commit("the goal adds c.txt")

stale, said = pending()
check("a page stale from main's commit, which the goal never touches, does not refuse (stale lines: %s)" % stale, not stale)
check("and it is printed as a FINDING for health", "FINDING STALE B" in said)
write("a.txt", "two\n")  # now the goal's own diff makes A stale
commit("the goal changes a.txt, so A is stale")
stale, said = pending()
check("a page the goal's own diff made stale still refuses (stale lines: %s)" % stale,
      len(stale) == 1 and stale[0].startswith("REWRITE A:"))
check("while main's B stays a FINDING, not a refusal", "FINDING STALE B" in said and not any("STALE B" in l for l in stale))
git("checkout", "-q", "main")
stale, said = pending()
check("on main itself every stale page still counts (stale lines: %s)" % stale,
      len(stale) == 1 and stale[0].startswith("REWRITE B:") and "FINDING" not in said)
print("PASS: merge.py's wiki check refuses only for pages the goal's own diff made stale" if not fails else "FAILED %d" % fails)
sys.exit(1 if fails else 0)
