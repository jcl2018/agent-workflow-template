#!/usr/bin/env python3
"""FLAKY (REG-9): a row whose result flipped on the same clean commit, runner and python version. Imported, not run.

Each result keeps its raw PASS/FAIL; the mark is a separate sticky `flaky` flag (the commit it flipped on). The previous
result is the row in the branch's lane record (<git common dir>/loop/tests/, lanes.py), which keeps commit, clean,
host (the runner) and python per row. Only two results on the same commit, both on a clean tree, from the same host
and python version count: either order (FAIL then PASS, PASS then FAIL) marks the row, and the mark stays on that
commit (FAIL, PASS, PASS is still flaky), until a later commit's clean run passes. A dirty tree, `regression.py red`,
another runner, or an older record or regression-runs.tsv without these fields never marks. The exit status follows
the actual result, and a flaky row is never reused (lanes.plan, tiers.reason). workflow-regression/references/lanes.md.
"""
import json
import platform
import socket


def runner():
    return socket.gethostname(), platform.python_version()


def previous(record):
    """The lane record's rows as written, with no schema or code check: the same commit means the same code."""
    try:
        with open(record) as handle:
            rows = json.load(handle).get("rows")
        return rows if isinstance(rows, dict) else {}
    except (OSError, ValueError, TypeError, AttributeError):
        return {}


def compare(prev, state, head, clean):
    """The row's flaky flag after this result: the commit it flipped on, or ''."""
    prev = prev if isinstance(prev, dict) else {}
    mark = str(prev.get("flaky") or "")
    if not clean:
        return mark
    if prev.get("commit") == head and prev.get("clean") == "yes" and (prev.get("host"), prev.get("python")) == runner():
        if mark == head or (prev.get("status") == "PASS") != (state == "PASS"):
            return head
    return "" if state == "PASS" and mark != head else mark


def word(passed):
    return "passed" if passed else "failed"


def apply(record, results, head, clean):
    """Give each result its commit, clean, host, python and (on a clean tree) flaky fields; return the FLAKY lines."""
    rows, (host, python), lines = previous(record) if record else {}, runner(), []
    for item in results:
        item.update(commit=head, clean="yes" if clean else "no", host=host, python=python)
        if not clean:
            continue
        item["flaky"] = compare(rows.get(item["id"]), item["state"], head, clean)
        if item["flaky"] == head:
            now = item["state"] == "PASS"
            lines.append("FLAKY %s: %s then %s on %s (same clean tree; runner %s, python %s). Note: the result counts as %s; "
                         "the row is never reused while flaky" % (item["id"], word(not now), word(now), head[:12], host,
                                                                 python, word(now)))
    return lines
