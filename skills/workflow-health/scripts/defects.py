#!/usr/bin/env python3
"""The health rule for defect tests: every closed issue or finding needs a regression row of category defect.

A closed issue or finding is one a merged goal says it fixed ("fixes #35", "fixes finding:SLUG" in .loop/goals/*.md),
or a line of .loop/findings.md marked [closed]. A defect row links it: its link holds the issue's URL or finding:SLUG.
Reads files only: health check makes no gh call.
"""
import glob
import os
import re

VERB = r"\b(?:fix(?:es|ed)?|close[sd]?|resolve[sd]?)\s+"
FIXES = re.compile(VERB + r"(?:issue\s+)?#(\d+)|" + VERB + r"finding:([a-z0-9][a-z0-9-]*)", re.I)


def read(path):
    try:
        with open(path) as handle:
            return handle.read()
    except OSError:
        return ""


def closed(root):
    """Ref -> where it was closed: '#N' for an issue, 'finding:SLUG' for a finding."""
    found = {}
    for path in sorted(glob.glob(os.path.join(root, ".loop", "goals", "*.md"))):
        if path.endswith(".design.md"):
            continue
        for number, finding in FIXES.findall(read(path)):
            found.setdefault("#" + number if number else "finding:" + finding.lower(), os.path.basename(path)[:-3])
    for line in read(os.path.join(root, ".loop", "findings.md")).splitlines():
        named = re.match(r"^- ([a-z0-9][a-z0-9-]*):.*\[closed\]", line)
        if named:
            found.setdefault("finding:" + named.group(1), "findings.md")
    return found


def guarded(root):
    """The links of the defect rows, as one text."""
    cells = [line.rstrip("\n").split("\t") + [""] * 8 for line in read(os.path.join(root, ".loop", "regression.tsv")).splitlines()
             if line.strip() and line[0] != "#"]
    return " ".join(c[7] for c in cells if c[6] == "defect")


def missing(root):
    """(ref, source) for each closed issue or finding no defect row links."""
    links = guarded(root)
    out = []
    for ref, source in closed(root).items():
        pattern = r"(?:issues/|#)%s\b" % ref[1:] if ref[0] == "#" else re.escape(ref) + r"(?![\w-])"
        if not re.search(pattern, links):
            out.append((ref, source))
    return out
