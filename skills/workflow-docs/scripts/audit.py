#!/usr/bin/env python3
"""The one docs command: check every required doc, fix what is mechanical, list the wording to rewrite.

usage: docs.py audit [--base REF] [--dry-run]

It checks the pages against the template sheet (references/template.md), the code (stale pages), the tests (the Tests
tables, and which Reviewed criteria have no test or tests that no longer match), and the required docs (each feature
page's Milestone line, the Backlog milestone, a release note per tag). It fixes the mechanical trouble itself (the
Tests tables and a missing Milestone line) and prints the rest as REWRITE lines for a person or agent. It never
deletes a page and never changes a criterion's wording. --dry-run only says what it would fix. Exit 0 only when
nothing is left. UNTESTED lines are written to untested.tsv (id, reason) in the repo's .git/loop folder for the loop to queue goals from, and
do not fail the audit. It runs git and gh, and nothing else.
"""
import argparse
import contextlib
import io
import json
import os
import re
import subprocess
import sys

import criteria
import docs

# No terminal, no waiting: a prompt from git or gh must fail, not block.
os.environ.update(GIT_TERMINAL_PROMPT="0", GH_PROMPT_DISABLED="1", GIT_EDITOR="true", GIT_ASKPASS="true", SSH_ASKPASS="true")
if not sys.stdin or not sys.stdin.isatty():
    os.dup2(os.open(os.devnull, os.O_RDONLY), 0)

REWRITE = {"CAP", "SCRIPT", "STALE", "UNWRITTEN", "SUMMARY", "SECTIONS", "CRITERION"}
TITLE = re.compile(r"^# .*$", re.M)


def milestones(root):
    """The repo's milestones as {title: url}, or None when gh gives no answer."""
    try:
        done = subprocess.run(["gh", "api", "repos/{owner}/{repo}/milestones?state=all&per_page=100"], cwd=root,
                              capture_output=True, text=True, timeout=60)
        return {item["title"]: item["html_url"] for item in json.loads(done.stdout)}
    except (OSError, subprocess.SubprocessError, ValueError, KeyError, TypeError):
        return None


def milestone_line(text, label, url):
    """The page text with a '<label>: <url>' line under its title, or None when it already has one."""
    if re.search(r"^%s: \S" % re.escape(label), text.partition("\n## ")[0], re.M):
        return None
    return TITLE.sub(lambda m: "%s\n\n%s: %s" % (m.group(0), label, url), text, 1)


def features(root):
    return [page for page in sorted(docs.read_map(root)) if page != "Home"]


def milestone_trouble(root, fix):
    """(kind, page, detail) for the milestone links and the Backlog; fixes a missing link unless fix is false."""
    held = milestones(root)
    if held is None:
        print("SKIP milestones: no answer from gh")
        return [], []
    label, found, fixed = criteria.rules()["milestone"], [], []
    if "Backlog" not in held:
        found.append(("MILESTONE", "Backlog", "missing. Fix: milestone.py new backlog --live"))
    for page in features(root):
        rel = os.path.join(root, docs.wiki_dir(root), page + ".md")
        if not os.path.exists(rel):
            continue
        if page not in held:
            found.append(("MILESTONE", page, "no milestone. Fix: milestone.py new %s --live" % page))
            continue
        with open(rel) as handle:
            text = handle.read()
        fresh = milestone_line(text, label, held[page])
        if fresh is not None:
            fixed.append("%s: add the %s line" % (page, label))
            if fix:
                with open(rel, "w") as handle:
                    handle.write(fresh)
    return found, fixed


def release_trouble(root):
    """A tag with neither a CHANGELOG section nor a GitHub release has no release note."""
    try:
        with open(os.path.join(root, "CHANGELOG.md")) as handle:
            notes = handle.read()
    except OSError:
        notes = ""
    out = []
    for tag in criteria.git("tag", "-l", "v*", check=False).split():
        if not re.search(r"^## \[?%s\b" % re.escape(tag), notes, re.M):
            have = subprocess.run(["gh", "release", "view", tag], cwd=root, capture_output=True, text=True)
            if have.returncode:
                out.append(("RELEASE", tag, "has no release note. Fix: add its CHANGELOG section or a GitHub release"))
    return out


def untested(root):
    """(id, reason) for each Reviewed criterion with no test, or none that passed since its wording appeared."""
    linked, _ = criteria.test_rows(root)
    rows = {row[0]: row for row in criteria.tsv(root, "regression.tsv")}
    ran = {row[0]: row[2] for row in criteria.tsv(root, "regression-runs.tsv") if row[1] == "PASS"}
    out = []
    for rel in criteria.pages(root):
        with open(os.path.join(root, rel)) as handle:
            lines = handle.read().splitlines()
        for match in filter(None, (criteria.LINE.match(line) for line in lines)):
            key, text = match.group(1), match.group(4)
            if match.group(2) == "Unreviewed":
                continue
            if not linked.get(key):
                out.append((key, "no test"))
                continue
            since = subprocess.run(["git", "log", "-1", "--format=%cs", "-S" + text, "--", rel], cwd=root,
                                   capture_output=True, text=True).stdout.strip()
            gone = [name for name in linked[key] if any(not os.path.exists(os.path.join(root, f))
                    for f in criteria.SCRIPT_FILE.findall(rows[name][2]))]
            if gone or not any(ran.get(name, "") >= since for name in linked[key]):
                out.append((key, "test no longer matches"))
    return out


def render(check):
    """Re-render the Tests tables (or only list the stale ones when check is true), as page paths."""
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        criteria.cmd_render(argparse.Namespace(check=check))
    return [line.split(" ", 1)[1] for line in out.getvalue().splitlines() if line.startswith(("STALE ", "RENDERED "))]


def audit(root, base, dry):
    fix = not dry
    would = []
    if not docs.read_map(root):
        print("NO PAGES: run add first")
        return 1
    if config_criteria(root):
        would += ["%s: re-render the Tests table" % name for name in render(not fix)]
    found, moved = milestone_trouble(root, fix)
    would += moved
    for line in would:
        print("%s %s" % ("WOULD FIX" if dry else "FIXED", line))
    found += docs.problems(root, base) + docs.contract(root) + docs.counts(root) + release_trouble(root)
    if dry:
        found = [item for item in found if item[0] != "TESTS"]
    for kind, page, detail in found:
        print("%s %s: %s" % ("REWRITE" if kind in REWRITE else kind, page, "%s %s" % (kind, detail) if kind in REWRITE else detail))
    todo = untested(root) if config_criteria(root) else []
    for key, why in todo:
        print("UNTESTED %s: %s" % (key, why))
    if fix:
        with open(os.path.join(os.path.dirname(docs.state_file()), "untested.tsv"), "w") as handle:
            handle.writelines("%s\t%s\n" % item for item in todo)
    left = len(found) + (len(would) if dry else 0)
    print("DOCS OK: %d pages" % len(docs.read_map(root)) if not left else "DOCS: %d to do" % left)
    return 1 if left else 0


def config_criteria(root):
    return bool(docs.config(root).get("criteria"))
