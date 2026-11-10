#!/usr/bin/env python3
"""Done lines with no regression row, for regression.py sync. A goal whose file was first committed before
done_lines_since (YYYY-MM-DD in .loop/config.json) owes no done-line rows: it finished before the repo adopted the
table (issue 124). Imported by regression.py; not run."""
import glob
import json
import os
import subprocess


def since(root):
    try:
        with open(os.path.join(root, ".loop", "config.json")) as handle:
            return str(json.load(handle).get("done_lines_since") or "")
    except (OSError, ValueError, AttributeError):
        return ""


def first_added(root, folder):
    """{slug: YYYY-MM-DD} when each goal file was first committed, from one git log."""
    out = subprocess.run(["git", "log", "--diff-filter=A", "--format=@%cs", "--name-only", "--", folder], cwd=root,
                         capture_output=True, text=True).stdout
    added, day = {}, ""
    for line in out.splitlines():
        if line.startswith("@"):
            day = line[1:]
        elif line.endswith(".md"):
            added[os.path.basename(line)[:-3]] = day  # git log runs newest first: the last seen is the first add
    return added


def gaps(root, rows, path_of, done_lines):
    covered = {row["goal"] for row in rows.values() if row["goal"]}
    cut = since(root)
    added = first_added(root, path_of(root, "goals")) if cut else {}
    out = []
    for path in sorted(glob.glob(path_of(root, "goals/*.md"))):
        slug = os.path.basename(path)[:-3]
        if cut and added.get(slug, cut) < cut:
            continue
        for number, line in done_lines(path):
            if "%s:%s" % (slug, number) not in covered:
                out.append((slug, number, line))
    return out
