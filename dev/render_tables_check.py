"""Row settings-render-tables: a lane's render rewrites the Tests tables and nothing else (#3777).

Copies the repo to a scratch git repo, makes the Settings block on Home and README stale (the state a lane finds when the
scripts it runs are older than the page), then checks that `criteria.py render --tables` leaves both pages as they were
and that a plain `render` still repairs them. Same on every platform; exit 0 when both hold."""
import os
import shutil
import subprocess
import sys
import tempfile

TOP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KEEP = ("README.md", "docs", ".loop", "skills")


def run(*cmd, cwd):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)


def read(path):
    with open(path, newline="") as handle:
        return handle.read()


def main():
    scratch = tempfile.mkdtemp(prefix="render-tables-")
    try:
        for name in KEEP:
            src = os.path.join(TOP, name)
            if os.path.isdir(src):
                shutil.copytree(src, os.path.join(scratch, name), ignore=shutil.ignore_patterns(".git", "__pycache__", "worktrees"))
            elif os.path.exists(src):
                shutil.copy(src, scratch)
        run("git", "init", "-q", cwd=scratch)
        pages = [os.path.join(scratch, "README.md"), os.path.join(scratch, "docs", "wiki", "Home.md")]
        for page in pages:
            text = read(page)
            if "| `automation` |" not in text:
                print("FAIL: %s has no automation row to make stale" % page)
                return 1
            stale = "\n".join(line for line in text.split("\n") if not line.startswith("| `automation` |"))
            with open(page, "w", newline="") as handle:
                handle.write(stale)
        before = [read(page) for page in pages]
        criteria = os.path.join(scratch, "skills", "workflow-docs", "scripts", "criteria.py")
        tables = run(sys.executable, criteria, "render", "--tables", cwd=scratch)
        if tables.returncode or [read(page) for page in pages] != before:
            print("FAIL: render --tables changed README.md or Home.md (exit %d): %s" % (tables.returncode, tables.stdout + tables.stderr))
            return 1
        full = run(sys.executable, criteria, "render", cwd=scratch)
        if full.returncode or [read(page) for page in pages] == before:
            print("FAIL: a plain render no longer repairs the Settings block (exit %d): %s" % (full.returncode, full.stdout + full.stderr))
            return 1
        print("OK: render --tables left README.md and Home.md alone; a plain render repaired them")
        return 0
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
