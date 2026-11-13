#!/usr/bin/env python3
# windows: ok
# reads: skills/workflow-monitoring/scripts/board_status.py skills/workflow-monitoring/scripts/graph.py skills/workflow-monitoring/scripts/pool.py skills/workflow-monitoring/scripts/operate.py skills/workflow-monitoring/scripts/checkin.py
"""machine-status: the check-in's Machine line, the memory floor, the main-checkout check, a queued goal reading alive, this pod only."""
import datetime
import json
import os
import subprocess
import sys
import tempfile

root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(root, "skills", "workflow-monitoring", "scripts"))
os.chdir(root)
os.environ.pop("LOOP_ROLE", None)
os.environ["LOOP_POD_ID"] = "mine"
fails = 0


def check(ok, what):
    global fails
    print("%s: %s" % ("PASS" if ok else "FAIL", what))
    fails += not ok


import board_status as bs  # noqa: E402
import graph  # noqa: E402

os.environ["LOOP_MACHINE"] = "8,4.5,30,5,12"
line = bs.machine_line({})
check("RAM 8.0 GB" in line and "commit 4.5 GB free" in line and "CPU 30%" in line and "5 claude, 12 node" in line, "the Machine line shows RAM, commit, CPU and the claude and node counts: " + line)
check("memory allows 1 goal start" in line, "4.5 GB free over the 3.5 floor allows one goal start")
os.environ["LOOP_MACHINE"] = "8,9,,,"
check("memory allows 4 goal starts" in bs.machine_line({}), "9 GB free allows four goal starts")
goals = [{"slug": "a-goal", "depends": []}, {"slug": "b-goal", "depends": []}]
os.environ["LOOP_MACHINE"] = "8,2.0,,,"
start, held = graph.ready(goals, {}, 0, {}, "")
check(not start and len(held) == 2 and "memory low" in held[0][1], "under min_free_memory_gb no goal starts: %s" % held[:1])
os.environ["LOOP_MACHINE"] = "8,9,,,"
start, held = graph.ready(goals, {}, 0, {}, "")
check(len(start) == 2, "above the floor both goals start")
import pool  # noqa: E402
os.environ["LOOP_MACHINE"] = "8,2.0,,,"
check(pool.need({}, {"pool_size": 5}, 2)[0] == 0, "under the floor the pool creates no session")
os.environ["LOOP_MACHINE"] = "8,9,,,"
check(pool.need({}, {"pool_size": 5}, 2)[0] == 5, "above the floor it asks for the missing sessions")
del os.environ["LOOP_MACHINE"]

now = datetime.datetime.now(datetime.timezone.utc)
old = graph.iso(now - datetime.timedelta(hours=2))
run = {"slug": "q-goal", "status": "running", "updated": old, "bound_at": old, "pid": 1}
check(graph.classify(run, None, now, {}) == "silent", "a goal that said nothing for 2 hours reads silent")
with tempfile.TemporaryDirectory() as folder:
    os.makedirs(os.path.join(folder, "pr-queue"))
    open(os.path.join(folder, "pr-queue", "q-goal"), "w").write("1")
    graph.with_held([run], folder)
    check(graph.classify(run, None, now, {}) == "running", "the same goal with a fresh pr-queue file reads alive")


def git(repo, *args):
    return subprocess.run(["git", "-C", repo] + list(args), capture_output=True, text=True, check=True).stdout.strip()


with tempfile.TemporaryDirectory() as tmp:
    origin, mine, other = (os.path.join(tmp, n) for n in ("origin.git", "mine", "other"))
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", origin], check=True)
    for repo in (mine, other):
        subprocess.run(["git", "clone", "-q", origin, repo], check=True, capture_output=True)
        git(repo, "config", "user.email", "t@t")
        git(repo, "config", "user.name", "t")
        git(repo, "checkout", "-q", "-B", "main")
    open(os.path.join(mine, "f"), "w").write("1")
    git(mine, "add", "-A")
    git(mine, "commit", "-qm", "one")
    git(mine, "push", "-q", "origin", "main")
    git(other, "pull", "-q", "origin", "main")
    open(os.path.join(other, "f"), "w").write("2")
    git(other, "commit", "-qam", "two")
    git(other, "push", "-q", "origin", "main")
    git(mine, "fetch", "-q", "origin")
    loop = os.path.join(mine, ".git", "loop")
    os.makedirs(loop)
    json.dump({"s1": {"state": "free", "name": "worker free one"}}, open(os.path.join(loop, "session-pool.json"), "w"))
    import operate  # noqa: E402
    ask = operate.behind_ask(os.path.join(mine, ".git"))
    check("CHECKOUT BEHIND" in ask and "1 commits behind" in ask and "worker free one" in ask and "merge --ff-only origin/main" in ask, "a main checkout behind origin/main asks a free worker: " + ask[:100])
    git(mine, "merge", "-q", "--ff-only", "origin/main")
    check(operate.behind_ask(os.path.join(mine, ".git")) == "" and not os.path.exists(os.path.join(loop, "checkout-behind.txt")), "a current checkout asks nothing")
    # this pod only: another pod's goal is one line, never a row
    os.makedirs(os.path.join(mine, ".loop"))
    json.dump({}, open(os.path.join(mine, ".loop", "config.json"), "w"))
    runs = os.path.join(loop, "runs")
    os.makedirs(runs)
    for slug, pod in (("mine-goal", "mine"), ("far-goal", "elsewhere")):
        json.dump({"slug": slug, "status": "running", "pod": pod, "goal": slug, "updated": graph.iso(now), "pid": 1}, open(os.path.join(runs, slug + ".json"), "w"))
    import checkin  # noqa: E402
    seen = checkin.gather(mine, now)
    check([r["slug"] for r in seen["live"]] == ["mine-goal"] and list(seen["away"]) == ["elsewhere"] and seen["away"]["elsewhere"][0] == 1,
          "the check-in reads only this pod's goals and counts the other pod's")
    os.chdir(mine)
    text = "\n".join(checkin.render(mine, now))
    check("elsewhere: 1 goal, last activity " in text and "far-goal" not in text and "Machine:" in text and "mine-goal" in text,
          "the check-in prints the Machine line and one line for the other pod, never its goals")
    import reply_hook  # noqa: E402
    check(not any("headline" in p for p in reply_hook.problems(text)), "the reply hook lets the Machine and pod lines follow the headline: %s" % reply_hook.problems(text)[:1])
    os.chdir(root)
raise SystemExit(1 if fails else 0)
