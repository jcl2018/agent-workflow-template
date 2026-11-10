#!/usr/bin/env python3
"""The release notes' proof lines (REG-6): one "Fixes #N: test ROW, seen failing DATE, passing" line per issue fixed
since the previous v* tag, from workflow-regression's tests.py fixes. Imported by release.py (cut) and autorelease.py.

A missing tests.py gives "Fixes: unknown (workflow-regression not installed)"; a failing one gives "Fixes: not listed
(<first line>). Note: ...": a report never fails a release. docs: Regression#lane-messages.
"""
import os
import subprocess
import sys

TESTS = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "workflow-regression",
                                      "scripts", "tests.py"))


def since(top):
    """The previous v* tag reachable from HEAD, else the first commit."""
    tag = subprocess.run(["git", "describe", "--tags", "--abbrev=0", "--match", "v*"], cwd=top, capture_output=True, text=True)
    if tag.returncode == 0 and tag.stdout.strip():
        return tag.stdout.strip()
    roots = subprocess.run(["git", "rev-list", "--max-parents=0", "HEAD"], cwd=top, capture_output=True, text=True)
    return (roots.stdout.split() or ["HEAD"])[-1]


def lines(top, start=None):
    """The Fixes lines (or the one line saying why there are none listed) for the release notes and CHANGELOG."""
    if not os.path.exists(TESTS):
        return ["Fixes: unknown (workflow-regression not installed)"]
    start = start or since(top)
    done = subprocess.run([sys.executable, TESTS, "fixes", "--since", start, "--root", top], cwd=top, capture_output=True,
                          text=True)
    if done.returncode:
        first = ((done.stderr or done.stdout).strip().splitlines() or ["exit %d" % done.returncode])[0]
        return ["Fixes: not listed (%s). Note: issue states are unchanged; run tests.py fixes --since %s by hand"
                % (first[:200], start)]
    return [line for line in done.stdout.splitlines() if line.startswith("Fixes #")]
