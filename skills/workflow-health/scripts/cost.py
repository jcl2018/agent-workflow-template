"""Cost rule: a goal over its time or token budget warns, naming its slowest or costliest steps.

Reads the run records of the last RECENT finished goals (status done) from the git common dir, so the same repo gives the
same answer twice. Seconds per step come from the log gaps (board_status.seconds_by_step), tokens from the record.
Budgets are time_budget_minutes and token_budget in .loop/config.json. No model, no network.

timing_rows is REG-7 for the same cost group: a goal's regression lane over goal_lane_minutes, or the newest full suite
over 30 minutes (SUITE_LIMIT), is a WARN row (rule time, counted under the cost rule). Goal lanes: each
`<slug>.<name>-lane.last` in <git common dir>/loop/runs of a goal still being built (its run record not done, failed,
retired or stopped); its LANE line gives the time. A lane that planned FULL has no merge-base and is left out. The full suite: the newest
`full` line of <git common dir>/loop/suite-times.tsv (sha, kind, seconds, date), written by a plain
`regression.py run nightly` here or downloaded from the CI run by the scheduled health job. No line: an INFO row saying
how to get one. Reads only local files: no network. workflow-regression/references/commands.md.
"""
import datetime
import glob
import importlib.util
import json
import os
import re
import subprocess
import sys

# No terminal, no waiting: a prompt from git must fail, not block.
os.environ.update(GIT_TERMINAL_PROMPT="0", GH_PROMPT_DISABLED="1", GIT_EDITOR="true", GIT_ASKPASS="true", SSH_ASKPASS="true")
if not sys.stdin or not sys.stdin.isatty():
    os.dup2(os.open(os.devnull, os.O_RDONLY), 0)

RECENT = 10
NAMED = 3


def row(state, subject, rule, detail, fix=""):
    return {"state": state, "family": "cost", "subject": subject, "rule": rule, "detail": detail, "fix": fix}


def board_status(here):
    path = os.path.join(here, "..", "..", "workflow-monitoring", "scripts", "board_status.py")
    if not os.path.exists(path):
        return None
    spec = importlib.util.spec_from_file_location("board_status", path)
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception:  # a broken sibling is UNREAD, not a crash
        return None
    return module


def finished(root):
    """The last RECENT finished run records, newest first, as dicts."""
    done = subprocess.run(["git", "rev-parse", "--git-common-dir"], cwd=root, capture_output=True, text=True)
    common = os.path.abspath(os.path.join(root, done.stdout.strip() or ".git"))
    runs = []
    for path in glob.glob(os.path.join(common, "loop", "runs", "*.json")):
        try:
            with open(path) as handle:
                state = json.load(handle)
        except (OSError, ValueError):
            continue
        if isinstance(state, dict) and state.get("status") == "done":
            state.setdefault("slug", os.path.basename(path)[:-5])
            runs.append(state)
    runs.sort(key=lambda run: (str(run.get("updated") or (run.get("log") or [""])[-1]), run["slug"]), reverse=True)
    return runs[:RECENT]


def budgets(root):
    try:
        with open(os.path.join(root, ".loop", "config.json")) as handle:
            config = json.load(handle)
    except (OSError, ValueError):
        return None, None
    time_budget, token_budget = config.get("time_budget_minutes"), config.get("token_budget")
    ok = lambda value: isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0
    return (time_budget if ok(time_budget) else None), (token_budget if ok(token_budget) else None)


def steps_of(run, module):
    return module.seconds_by_step(run, datetime.datetime.now(datetime.timezone.utc)), module.tokens_by_step(run)


def worst(values, unit):
    top = sorted(values.items(), key=lambda pair: (-pair[1], pair[0]))[:NAMED]
    return ", ".join("%s %s" % (name, unit(number)) for name, number in top)


def facts(root, here):
    """(runs, module, per-goal (seconds, tokens)) for the recent finished goals, or None when they cannot be read."""
    module = board_status(here)
    if module is None:
        return None
    runs = finished(root)
    return runs, module, {run["slug"]: steps_of(run, module) for run in runs}


def cost_rows(root, here):
    found = facts(root, here)
    if found is None:
        return [row("UNREAD", "monitoring", "cost", "workflow-monitoring is not installed beside this skill")]
    runs, _, per = found
    time_budget, token_budget = budgets(root)
    rows = []
    if time_budget is None and token_budget is None:
        rows.append(row("INFO", "budgets", "cost", "no time_budget_minutes or token_budget in .loop/config.json",
                        "set them in .loop/config.json"))
    for run in runs:
        seconds, tokens = per[run["slug"]]
        if time_budget is not None and sum(seconds.values()) > time_budget * 60:
            rows.append(row("WARN", run["slug"], "time", "%d min, over %g min; slowest: %s" % (
                sum(seconds.values()) // 60, time_budget, worst(seconds, lambda n: "%d min" % (n // 60))),
                "trim the slow steps or raise time_budget_minutes"))
        if token_budget is not None and sum(tokens.values()) > token_budget:
            rows.append(row("WARN", run["slug"], "tokens", "%d tokens, over %d; costliest: %s" % (
                sum(tokens.values()), token_budget, worst(tokens, lambda n: "%d" % n)),
                "trim the costly steps or raise token_budget"))
    if runs and not any(per[run["slug"]][1] for run in runs):  # issue 124: goals from before token recording
        rows.append(row("INFO", "tokens", "cost", "no tokens recorded in the last %d finished goals; the token check "
                        "covers goals that record them" % len(runs), "report tokens with goal.py step SLUG NAME --tokens N"))
    if not runs:
        rows.append(row("PASS", "goals", "cost", "no finished goals to measure"))
    elif not any(item["state"] in ("WARN", "UNREAD") for item in rows):
        rows.append(row("PASS", "goals", "cost", "%d recent goals within budget" % len(runs)))
    return rows


def timing_row(state, subject, detail, fix=""):
    return {"state": state, "family": "cost", "subject": subject, "rule": "time", "detail": detail, "fix": fix}


SUITE_LIMIT = 30  # minutes the scheduled full suite may take before health warns (REG-7)


def limits(root):
    try:
        with open(os.path.join(root, ".loop", "config.json")) as handle:
            cfg = json.load(handle)
    except (OSError, ValueError):
        cfg = {}
    cfg = cfg if isinstance(cfg, dict) else {}
    num = lambda key, default: cfg[key] if isinstance(cfg.get(key), (int, float)) and cfg[key] > 0 else default  # noqa: E731
    return num("goal_lane_minutes", 10), SUITE_LIMIT, cfg


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
        found = re.match(r"^(.+)\.([a-z]+)-lane\.last$", os.path.basename(path))
        state, last = read(os.path.join(runs, found.group(1) + ".json")) if found else {}, read(path)
        if not isinstance(state, dict) or not isinstance(last, dict) or state.get("status") in (None, "done", "failed", "retired", "stopped"):
            continue  # a stray file, or no goal still being built
        slug, name = found.groups()
        took = re.search(r"^LANE \S+ (\S+) \S+ in (\d+)s", str(last.get("line", "")), re.M)
        if took and took.group(1) != "FULL" and int(took.group(2)) > lane_limit * 60:
            rows.append(timing_row("WARN", "goal-lane", "%s %s took %d min (limit %d, goal_lane_minutes)" % (
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
        return [timing_row("INFO", "full-suite", "no full-suite time recorded yet", "run regression.py run nightly locally" if off
                    else "the scheduled health job downloads CI's time; locally, run regression.py run nightly")]
    sha, _, seconds, day = full[-1][:4]
    minutes, source = int(seconds) // 60, "CI artifact" if len(full[-1]) > 4 and full[-1][4] == "ci" else "local run"
    left = int(full[-1][4]) if len(full[-1]) > 4 and full[-1][4].isdigit() else 0  # the CI line's 5th column: rows left unrun (REG-7)
    if left:
        return [timing_row("WARN", "full-suite", "%d rows were left unrun by the full suite (%s on %s, %s)" % (left, source, day, sha[:12]),
                           "add a shard or move the slowest rows to nightly")]
    text = "%d min (limit %d, the full-suite limit), from %s on %s (%s)" % (minutes, suite_limit, source, day, sha[:12])
    if int(seconds) > suite_limit * 60:
        return [timing_row("WARN", "full-suite", text, "narrow the rows (regression.py reads ROW) or move the slowest to nightly")]
    return [timing_row("PASS", "full-suite", "suite: " + text)]


def timing_rows(root):
    lane_limit, suite_limit, cfg = limits(root)
    found = common(root)
    if not found:
        return [timing_row("UNREAD", "timing", "not a git repo, so no lane or suite times")]
    return lane_rows(os.path.join(found, "loop", "runs"), lane_limit) + suite_rows(found, suite_limit, cfg)
