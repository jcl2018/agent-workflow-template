"""Cost rule: a goal over its time or token budget warns, naming its slowest or costliest steps.

Reads the run records of the last RECENT finished goals (status done) from the git common dir, so the same repo gives the
same answer twice. Seconds per step come from the log gaps (board_status.seconds_by_step), tokens from the record.
Budgets are time_budget_minutes and token_budget in .loop/config.json. No model, no network.
"""
import datetime
import glob
import importlib.util
import json
import os
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
    if runs and not any(per[run["slug"]][1] for run in runs):
        rows.append(row("UNREAD", "tokens", "cost", "no tokens recorded in the last %d finished goals" % len(runs),
                        "report tokens with goal.py step SLUG NAME --tokens N"))
    if not runs:
        rows.append(row("PASS", "goals", "cost", "no finished goals to measure"))
    elif not any(item["state"] in ("WARN", "UNREAD") for item in rows):
        rows.append(row("PASS", "goals", "cost", "%d recent goals within budget" % len(runs)))
    return rows
