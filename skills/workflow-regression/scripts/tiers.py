#!/usr/bin/env python3
"""The time budget of an in-loop test run: read and check the setting, fit the rows to it, run them, say what was left.

Imported by regression.py. A run with --reuse (the loop's qa, ship and pull-request lanes) never goes past
test_budget_minutes in .loop/config.json (default 15, floor 15): rows run in tier order (the rows a change affects
first) while their estimated seconds fit, a row still running at the budget is stopped, and every row not run is left to
the scheduled full suite and listed. A left row is recorded as LEFT, so a later lane on the same content doesn't rerun it.
"""
import json
import os
import subprocess
import sys
import time

import actions

FLOOR, DEFAULT = 15, 15


def minutes(cfg, key, default=DEFAULT):
    """The setting in minutes; exits with a fix line when it is not a whole number of at least 15."""
    value = cfg.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int) or value < FLOOR:
        sys.exit("REFUSED: %s is %r in .loop/config.json, under the %d-minute floor. Fix: set it to %d or more." % (
            key, value, FLOOR, FLOOR))
    return value


def budget(root):
    """Seconds the loop's test run may take."""
    try:
        with open(os.path.join(root, ".loop", "config.json")) as handle:
            cfg = json.load(handle)
    except (OSError, ValueError):
        cfg = {}
    return minutes(cfg if isinstance(cfg, dict) else {}, "test_budget_minutes") * 60


def fit(todo, est, limit):
    """(rows that fit, rows left): todo in tier order, each kept while the estimated total stays within limit."""
    keep, left, used = [], [], 0.0
    for key in todo:
        if used + est.get(key, 0) <= limit:
            keep.append(key)
            used += est.get(key, 0)
        else:
            left.append(key)
    return keep, left


def execute(root, picked, todo, est, limit, timeout, expected, reuse):
    """Run the rows of todo within limit seconds (None: no limit). Returns (results, left ids)."""
    keep, left = fit(todo, est, limit) if limit else (todo, [])
    by, results, start = {row["id"]: row for row in picked}, [], time.time()
    for key in keep:
        remaining = limit - (time.time() - start) if limit else None
        if remaining is not None and remaining < 1:
            left.append(key)
            continue
        cap = timeout if remaining is None else min(timeout, remaining)
        began = time.time()
        try:
            done = subprocess.run(by[key]["command"], shell=True, cwd=root, capture_output=True, text=True,
                                  env=actions.row_env(), timeout=cap)
            code, text = done.returncode, done.stdout + done.stderr
        except subprocess.TimeoutExpired:
            if cap < timeout:  # stopped by the budget, not by its own limit: it didn't fail, it wasn't finished
                left.append(key)
                continue
            code, text = 124, "timed out after %s seconds" % timeout
        state = "PASS" if code == 0 else ("KNOWN" if key in expected else "FAIL")
        if code == 0 and key in expected:
            print("FIXED %s: remove it from the known list" % key)
        print("%s %s%s" % (state, key, " (%s)" % expected[key] if state == "KNOWN" else ""), flush=True)
        if state == "FAIL" and reuse:
            print("\n".join("    " + line for line in text.rstrip().splitlines()[-20:]), file=sys.stderr)
        results.append({"id": key, "state": state, "tail": text[-1500:], "seconds": round(time.time() - began, 1)})
    if left:
        print("BUDGET %d min: ran %d of %d rows; LEFT %d to the scheduled full suite: %s" % (
            (limit or 0) // 60, len(results), len(results) + len(left), len(left), ", ".join(left[:20]) + (
                ", +%d more" % (len(left) - 20) if len(left) > 20 else "")))
    return results, left
