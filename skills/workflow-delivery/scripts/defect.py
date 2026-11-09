#!/usr/bin/env python3
"""Find the issues and findings a goal fixes that still lack a defect test.

usage: defect.py owed SLUG

A goal fixes an issue when its text says "fixes #N" (or closes, resolves), and a finding when it says "fixes finding:ID".
Each needs a regression row with category defect, a link to it, a date it was seen failing, and a passing command.
Prints one line per ref with no such row, and exits 1 if any. goal.py pr calls owed() and refuses on its answer.
"""
import argparse
import os
import re
import subprocess
import sys

# No terminal, no waiting: a prompt from git or gh must fail, not block.
os.environ.update(GIT_TERMINAL_PROMPT="0", GH_PROMPT_DISABLED="1", GIT_EDITOR="true", GIT_ASKPASS="true", SSH_ASKPASS="true")
if not sys.stdin or not sys.stdin.isatty():
    os.dup2(os.open(os.devnull, os.O_RDONLY), 0)

VERB = r"\b(?:fix(?:es|ed)?|close[sd]?|resolve[sd]?)\s+"
UNSEEN = ("", "-")  # a seen_red that is not a date: never seen failing
FIXES = re.compile(VERB + r"(?:issue\s+)?#(\d+)|" + VERB + r"finding:([a-z0-9][a-z0-9-]*)", re.I)


def rows(root):
    """Defect rows as (id, command, seen_red, link)."""
    try:
        with open(os.path.join(root, ".loop", "regression.tsv")) as handle:
            cells = [line.rstrip("\n").split("\t") + [""] * 8 for line in handle if line.strip() and line[0] != "#"]
    except OSError:
        return []
    return [(c[0], c[2], c[4], c[7]) for c in cells if c[6] == "defect"]


def has(link, ref):
    return re.search(r"(?:issues/|#)%s\b" % re.escape(ref), link) if ref.isdigit() else re.search(r"finding:%s(?![\w-])" % re.escape(ref), link)


def owed(root, text):
    """The refs the text fixes with no defect row that was seen failing and passes now."""
    owe = []
    for number, finding in FIXES.findall(text):
        ref = number or finding.lower()
        if not any(seen not in UNSEEN and has(link, ref) and subprocess.run(command, shell=True, cwd=root, capture_output=True).returncode == 0
                   for _, command, seen, link in rows(root)):
            owe.append(("#" if number else "finding ") + ref)
    return owe


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=("owed",))
    parser.add_argument("slug")
    args = parser.parse_args()
    top = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True).stdout.strip()
    with open(os.path.join(top, ".loop", "goals", args.slug + ".md")) as handle:
        left = owed(top, handle.read())
    print("\n".join("OWED %s: no defect test seen failing and passing" % ref for ref in left) or "NONE OWED")
    return 1 if left else 0


if __name__ == "__main__":
    sys.exit(main())
