#!/usr/bin/env python3
"""Survey a git repo for setup: what it holds, and what adopting it would add or convert.

usage: survey.py [--repo DIR]

Prints the FOUND line and the add:/convert:/skip:/no fit: plan that setup.py would apply. Read-only.
"""
import argparse
import json
import os
import re
import subprocess
import sys

# No terminal, no waiting: a prompt from git or gh must fail, not block.
os.environ.update(GIT_TERMINAL_PROMPT="0", GH_PROMPT_DISABLED="1", GIT_EDITOR="true", GIT_ASKPASS="true", SSH_ASKPASS="true")
if not sys.stdin or not sys.stdin.isatty():
    os.dup2(os.open(os.devnull, os.O_RDONLY), 0)

CODE = {".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs", ".java", ".rb", ".c", ".cc", ".cpp", ".h", ".sh", ".swift", ".kt", ".php"}
NOT_AREAS = {"docs", "doc", "test", "tests", "dist", "build", "node_modules", "vendor", "scripts", "dev", "examples", "tools"}
MARKER = "<!-- workflow-docs -->"


def git(repo, *args):
    done = subprocess.run(["git", "-C", repo] + list(args), capture_output=True, text=True)
    return done.stdout.strip() if done.returncode == 0 else ""


def page_name(folder):
    name = re.sub(r"[^A-Za-z0-9-]+", "-", folder).strip("-")
    return name[:1].upper() + name[1:]


def read(repo, rel):
    try:
        with open(os.path.join(repo, rel), errors="replace") as handle:
            return handle.read()
    except OSError:
        return None


def survey(repo, config):
    """What the repo holds. config is the merged .loop/config.json."""
    files = git(repo, "ls-files").splitlines()
    wiki = config.get("wiki_dir") or "docs/wiki"
    areas = sorted({f.split("/")[0] for f in files if "/" in f and not f.startswith(".") and f.split("/")[0] not in NOT_AREAS
                    and os.path.splitext(f)[1] in CODE})
    pages = {os.path.basename(f)[:-3]: f for f in files if f.startswith(wiki + "/") and f.endswith(".md") and f.count("/") == wiki.count("/") + 1}
    tests = [f for f in files if re.search(r"(^|/)(tests?|spec)(/|_)|(^|/)test_|_test\.|\.test\.", f)]
    return {"kind": "new" if len(files) < 3 else "existing", "files": len(files), "wiki": wiki, "pages": pages,
            "areas": {page_name(a): a for a in areas}, "tests": len(tests), "readme": read(repo, "README.md"),
            "tags": git(repo, "tag").splitlines(), "version": (read(repo, "VERSION") or "").strip(),
            "ci": [f for f in files if f.startswith(".github/workflows/")]}


def found_line(found, config):
    return "FOUND: %s repo, base %s, %d files, checks %s, areas %s, %d test files, tags %s, CI %s" % (
        found["kind"], config["base"], found["files"], config["checks"] or "none", ", ".join(found["areas"]) or "none",
        found["tests"], ", ".join(found["tags"][-3:]) or "none", len(found["ci"]) or "none")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo", default=".")
    args = parser.parse_args()
    repo = git(args.repo, "rev-parse", "--show-toplevel")
    if not repo:
        sys.exit("REFUSED: not inside a git repo.")
    config = json.loads(read(repo, ".loop/config.json") or "{}")
    config.setdefault("base", "main")
    config.setdefault("checks", [])
    print(found_line(survey(repo, config), config))
    return 0


if __name__ == "__main__":
    sys.exit(main())
