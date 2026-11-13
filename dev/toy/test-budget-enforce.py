#!/usr/bin/env python3
# windows: ok
# reads: skills/workflow-delivery/scripts/fit.py skills/workflow-delivery/scripts/goal.py skills/workflow-delivery/scripts/flow.py
# reads: skills/workflow-monitoring/scripts/pool.py skills/workflow-monitoring/scripts/watch.py skills/workflow-monitoring/scripts/checkin.py
# reads: skills/workflow-health/scripts/cost.py skills/workflow-setup/scripts/settings.py
"""GRD-2: time, token, merge-round, active-goal and plan-usage limits in .loop/config.json stop new work.

Calls the real functions: fit.budget_stop / add_tokens / round_stop (delivery), pool.active_limit / plan_pause / cmd_usage
(monitoring), cost.limit_rows (health) and the settings table, in throwaway repos. No model, no network."""
import datetime
import json
import os
import subprocess
import sys
import tempfile
from types import SimpleNamespace

root = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
for skill in ("delivery", "monitoring", "health", "setup"):
    sys.path.insert(0, os.path.join(root, "skills", "workflow-" + skill, "scripts"))
os.environ.pop("LOOP_ROLE", None)
import fit  # noqa: E402
import pool  # noqa: E402
import cost  # noqa: E402
import settings  # noqa: E402

failed = []


def check(ok, text):
    print(("PASS: " if ok else "FAIL: ") + text)
    if not ok:
        failed.append(text)


def refused(call, *args):
    try:
        call(*args)
    except SystemExit as stop:
        return str(stop)
    return ""


def ago(minutes):
    return (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=minutes)).strftime("%Y-%m-%dT%H:%M:%SZ")


def goal(minutes, **more):
    return dict({"slug": "g", "log": [ago(minutes) + " frozen 1 done lines"]}, **more)


# 1. time and token budgets (GRD-2): a goal past either starts no new step
cfg = {"time_budget_minutes": 120, "token_budget": 1000}
check(refused(fit.budget_stop, "g", goal(30), "/none", cfg) == "", "a goal inside its budgets starts its step")
said = refused(fit.budget_stop, "g", goal(130), "/none", cfg)
check("BUDGET_MINUTES" in said and "goal.py set g --budget-minutes" in said and "\n" not in said, "a goal past time_budget_minutes is refused with one line naming goal.py set")
said = refused(fit.budget_stop, "g", goal(5, tokens={"build": 1500}), "/none", cfg)
check("BUDGET_TOKENS" in said and "--budget-tokens" in said, "a goal past token_budget is refused with one line naming goal.py set")
check(refused(fit.budget_stop, "g", goal(500), "/none", {}) == "", "no budget set means no stop")
check(refused(fit.budget_stop, "g", goal(500, budget={"minutes": 600, "tokens": 0}), "/none", cfg) == "", "the operation's goal.py set budget wins over the repo's")

# 2. tokens from a session worker: a number adds up, unknown stays unread (never 0)
state = goal(5)
fit.add_tokens(state, "idea", "unknown")
fit.add_tokens(state, "idea", "")
check("tokens" not in state and fit.tokens_text(state) == "tokens unread", "unknown tokens record nothing and read 'tokens unread'")
fit.add_tokens(state, "idea", "400")
fit.add_tokens(state, "idea", "100")
check(state["tokens"] == {"idea": 500} and fit.spent_tokens(state) == 500, "a session worker's counts add up per step")

# 3. merge rounds: the 4th merge-main-and-rerun round is refused and the goal waits
saved = []
fake = SimpleNamespace(config=lambda: {}, save=lambda st, note=None: saved.append(note), no=lambda text: (_ for _ in ()).throw(SystemExit("REFUSED: " + text)))
state = {"slug": "g"}
check([refused(fit.round_stop, fake, state, "merged") for _ in range(3)] == ["", "", ""] and state["merge_rounds"] == 3, "three merge rounds are allowed and counted")
fit.round_stop(fake, state, "current")
check(state["merge_rounds"] == 3, "a pr that merged nothing is not a round")
said = refused(fit.round_stop, fake, state, "conflict")
check("MERGE_ROUNDS" in said and state["status"] == "waiting" and "MERGE_ROUNDS" in state["waiting"]["ask"] and state["merge_rounds"] == 0, "the 4th round is refused, the goal waits for the owner and the count starts again")
fake.config = lambda: {"max_merge_rounds": 1}
state = {"slug": "g"}
refused(fit.round_stop, fake, state, "merged")
check("MERGE_ROUNDS" in refused(fit.round_stop, fake, state, "merged"), "max_merge_rounds sets the limit")

with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
    tmp = os.path.realpath(tmp)
    os.chdir(tmp)
    subprocess.run(["git", "init", "-q", "-b", "main", "."], check=True, capture_output=True)
    loop = os.path.join(tmp, ".git", "loop")
    os.makedirs(os.path.join(loop, "runs"))
    # 4. active goals and plan usage
    check(pool.active_limit({}) == 20, "max_active_goals defaults to 20")
    check(pool.active_limit({"max_active_goals": 5, "parallel": 3}) == 3 and pool.active_limit({"max_active_goals": 5}) == 5, "the smaller of parallel and max_active_goals counts")
    check(pool.active_limit({"max_active_goals": 0}) == 0, "max_active_goals 0 means no limit")
    check(pool.plan_pause({}) == "", "plan usage that was never recorded pauses nothing")
    pool.cmd_usage(SimpleNamespace(percent=83))
    said = pool.plan_pause({})
    check("PLAN_PAUSE" in said and "83%" in said, "plan usage above plan_pause_percent (default 80) pauses new goals and says why")
    check(pool.plan_pause({"plan_pause_percent": 90}) == "" and pool.plan_pause({"plan_pause_percent": 0}) == "", "a higher plan_pause_percent, or 0, lets goals start")
    with open(os.path.join(loop, "plan-usage.json"), "w") as handle:
        json.dump({"percent": 99, "at": ago(60 * 13)}, handle)
    check(pool.plan_pause({}) == "", "a plan reading older than 12 hours is unread and pauses nothing")
    pool.cmd_usage(SimpleNamespace(percent=83))
    # 5. health warns on each limit exceeded
    os.makedirs(os.path.join(tmp, ".loop"))
    with open(os.path.join(tmp, ".loop", "config.json"), "w") as handle:
        json.dump({"max_active_goals": 1}, handle)
    for slug, extra in (("a", {}), ("b", {"waiting": {"ask": "merge round 4 would pass max_merge_rounds (3) (MERGE_ROUNDS)"}})):
        with open(os.path.join(loop, "runs", slug + ".json"), "w") as handle:
            json.dump(dict({"slug": slug, "status": "running"}, **extra), handle)
    rows = cost.limit_rows(tmp)
    check({r["rule"] for r in rows if r["state"] == "WARN"} == {"rounds", "active", "usage"}, "health warns on merge rounds, active goals and plan usage over their limits")

# 6. every setting is in the settings table with its default, and this repo's config carries them
table = {name: default for name, home, default, _ in settings.TABLE}
check(table.get("time_budget_minutes") == 120 and table.get("max_merge_rounds") == 3 and table.get("max_active_goals") == 20 and table.get("plan_pause_percent") == 80,
      "the settings table lists time_budget_minutes, max_merge_rounds, max_active_goals and plan_pause_percent with their defaults")
with open(os.path.join(root, ".loop", "config.json")) as handle:
    live = json.load(handle)
check(all(key in live for key in ("max_merge_rounds", "max_active_goals", "plan_pause_percent", "time_budget_minutes")), "this repo's config carries the new settings")
with open(os.path.join(root, "skills", "workflow-delivery", "scripts", "flow.py")) as handle:
    text = handle.read()
check("fit.budget_stop(" in text, "flow.py checks the budgets before it starts a step")
import watch  # noqa: E402
check(watch.limit_of(SimpleNamespace(max=0), {}) == 20 and watch.limit_of(SimpleNamespace(max=0), {"max_active_goals": 2}) == 2, "watch starts no goal past max_active_goals")
helped = subprocess.run([sys.executable, os.path.join(root, "skills", "workflow-delivery", "scripts", "goal.py"), "record", "-h"], capture_output=True, text=True).stdout
check("--tokens" in helped, "goal.py record takes the session's tokens")
os.chdir(root)
print("ALL PASS" if not failed else "%d FAILED" % len(failed))
sys.exit(1 if failed else 0)
