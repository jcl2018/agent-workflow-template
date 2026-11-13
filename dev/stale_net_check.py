"""Row stale-net-diff: the docs stale check counts net change, not commits (#3771).

Builds a scratch repo with one page that maps src/a.txt. Commits that add a change and then revert it leave the page not
STALE; a commit that really changes the file reads STALE. Same on every platform; exit 0 when both hold."""
import os
import shutil
import subprocess
import sys
import tempfile

TOP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(TOP, "skills", "workflow-docs", "scripts", "docs.py")


def git(scratch, *args):
    done = subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.com", "-C", scratch] + list(args),
                          capture_output=True, text=True)
    if done.returncode:
        sys.exit("FAIL: git %s: %s" % (" ".join(args), done.stderr.strip()[:200]))
    return done.stdout


def write(scratch, rel, text):
    path = os.path.join(scratch, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="\n") as handle:
        handle.write(text)


def stale(scratch, *extra):
    done = subprocess.run([sys.executable, DOCS, "check"] + list(extra), cwd=scratch, capture_output=True, text=True)
    return [line for line in done.stdout.splitlines() if line.startswith("STALE Page")]


def main():
    scratch = tempfile.mkdtemp(prefix="stale-net-")
    try:
        git(scratch, "init", "-q")
        write(scratch, ".loop/config.json", "{}\n")
        write(scratch, ".loop/docs.tsv", "# page\tpaths\nPage\tsrc\n")
        write(scratch, "docs/wiki/Page.md", "<!-- workflow-docs -->\n# Page\n\nThis page says what the source file holds, in more than ten words.\n")
        write(scratch, "src/a.txt", "one\n")
        git(scratch, "add", "-A")
        git(scratch, "commit", "-q", "-m", "page and source")
        write(scratch, "src/a.txt", "one\ntwo\n")
        git(scratch, "commit", "-q", "-am", "add a line")
        write(scratch, "src/a.txt", "one\n")
        git(scratch, "commit", "-q", "-am", "revert it")
        first = git(scratch, "rev-list", "--max-parents=0", "HEAD").strip()
        if stale(scratch) or stale(scratch, "--base", first):
            print("FAIL: an add and its revert read STALE: %s" % (stale(scratch) or stale(scratch, "--base", first)))
            return 1
        write(scratch, "src/a.txt", "one\nthree\n")
        git(scratch, "commit", "-q", "-am", "a real change")
        if not stale(scratch) or not stale(scratch, "--base", first):
            print("FAIL: a real net change no longer reads STALE")
            return 1
        print("OK: an add and its revert leave the page current; a real change reads STALE")
        return 0
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
