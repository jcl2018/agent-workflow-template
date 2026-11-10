#!/usr/bin/env python3
"""REG-7 for health's cost group: a goal's regression lane over goal_lane_minutes, or the newest full suite over
full_suite_minutes, is a WARN row (rule time, counted under the cost rule). Imported by health.py.

Goal lanes: each `<slug>.<name>-lane.last` in <git common dir>/loop/runs of a goal still being built (its run record
not done, failed, retired or stopped); its LANE line gives the time. FULL lanes are left to full_suite_minutes. The full
suite: the newest `full` line of <git common dir>/loop/suite-times.tsv (sha, kind, seconds, date), written by a plain
`regression.py run nightly` here or downloaded from the CI run by the scheduled health job. No line: an INFO row saying
how to get one. Reads only local files: no network. docs: Regression#lane-messages.
"""
import glob
import json
import os
import re
import subprocess


def row(state, subject, detail, fix=""):
    return {"state": state, "family": "cost", "subject": subject, "rule": "time", "detail": detail, "fix": fix}


def limits(root):
    try:
        with open(os.path.join(root, ".loop", "config.json")) as handle:
            cfg = json.load(handle)
    except (OSError, ValueError):
        cfg = {}
    cfg = cfg if isinstance(cfg, dict) else {}
    num = lambda key, default: cfg[key] if isinstance(cfg.get(key), (int, float)) and cfg[key] > 0 else default  # noqa: E731
    return num("goal_lane_minutes", 10), num("full_suite_minutes", 30), cfg


def common(root):
    done = subprocess.run(["git", "rev-parse", "--git-common-dir"], cwd=root, capture_output=True, text=True)
    return os.path.join(root, done.stdout.strip()) if done.returncode == 0 else ""


def read(path):
    try:
        with open(path) as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return {}


def lane_rows(runs, lane_limit):
    rows = []
    for path in sorted(glob.glob(os.path.join(runs, "*-lane.last"))):
        slug, name = re.match(r"^(.+)\.([a-z]+)-lane\.last$", os.path.basename(path)).groups()
        state, last = read(os.path.join(runs, slug + ".json")), read(path)
        if not isinstance(state, dict) or state.get("status") in (None, "done", "failed", "retired", "stopped"):
            continue
        took = re.search(r"^LANE \S+ (\S+) \S+ in (\d+)s", str(last.get("line", "")), re.M)
        if took and took.group(1) != "FULL" and int(took.group(2)) > lane_limit * 60:
            rows.append(row("WARN", "goal-lane", "%s %s took %d min (limit %d, goal_lane_minutes)" % (
                slug, name, int(took.group(2)) // 60, lane_limit), "narrow the rows (regression.py reads ROW) or raise "
                "goal_lane_minutes"))
    return rows


def suite_rows(common_dir, suite_limit, cfg):
    lines = []
    try:
        with open(os.path.join(common_dir, "loop", "suite-times.tsv")) as handle:
            lines = [line.rstrip("\n").split("\t") for line in handle if line.strip() and not line.startswith("#")]
    except OSError:
        pass
    full = [cells for cells in lines if len(cells) >= 4 and cells[1] == "full" and cells[2].isdigit()]
    if not full:
        off = cfg.get("regression_cron") == "off" or cfg.get("ci_levels") == "land"
        return [row("INFO", "full-suite", "no full-suite time recorded yet", "run regression.py run nightly locally" if off
                    else "the scheduled health job downloads CI's time; locally, run regression.py run nightly")]
    sha, _, seconds, day = full[-1][:4]
    minutes, source = int(seconds) // 60, "CI artifact" if len(full[-1]) > 4 and full[-1][4] == "ci" else "local run"
    text = "%d min (limit %d, full_suite_minutes), from %s on %s (%s)" % (minutes, suite_limit, source, day, sha[:12])
    if int(seconds) > suite_limit * 60:
        return [row("WARN", "full-suite", text, "narrow the rows (regression.py reads ROW) or raise full_suite_minutes")]
    return [row("PASS", "full-suite", "suite: " + text)]


def rows(root):
    lane_limit, suite_limit, cfg = limits(root)
    found = common(root)
    if not found:
        return [row("UNREAD", "timing", "not a git repo, so no lane or suite times")]
    return lane_rows(os.path.join(found, "loop", "runs"), lane_limit) + suite_rows(found, suite_limit, cfg)
