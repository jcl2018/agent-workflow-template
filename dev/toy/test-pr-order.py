#!/usr/bin/env python3
# windows: ok
# reads: skills/workflow-monitoring/scripts/pool.py
"""#3922: every goal at pr sees one queue order. A goal's place is its first-join time, written once; a retry touches only its
heartbeat, and only the heartbeat drives expiry. Three goals retrying in a loop never reorder or livelock."""
import json
import os
import subprocess
import sys
import tempfile
import time

here = os.path.dirname(os.path.abspath(__file__))
pool_py = os.path.join(here, "..", "..", "skills", "workflow-monitoring", "scripts", "pool.py")
sys.path.insert(0, os.path.dirname(pool_py))
import pool  # noqa: E402

failed = []


def check(ok, text):
    print(("PASS: " if ok else "FAIL: ") + text)
    if not ok:
        failed.append(text)


with tempfile.TemporaryDirectory() as tmp:
    subprocess.run(["git", "init", "-q", tmp], check=True)
    runs = os.path.join(tmp, ".git", "loop", "runs")
    folder = os.path.join(tmp, ".git", "loop", "pr-queue")
    os.makedirs(runs)

    def goal(slug, step="pr"):
        with open(os.path.join(runs, slug + ".json"), "w") as handle:
            json.dump({"slug": slug, "status": "running", "step": step}, handle)

    for slug in ("g1", "g2", "g3"):
        goal(slug)
    seen = []
    for slug in ("g1", "g2", "g3"):  # the order they first ask in
        pool.pr_turn(runs, slug)
        time.sleep(0.01)
    tickets = {slug: open(os.path.join(folder, slug)).read() for slug in ("g1", "g2", "g3")}
    for _ in range(6):  # three goals retrying in a loop, in a different order each round
        for slug in ("g3", "g1", "g2"):
            seen.append((slug, pool.pr_turn(runs, slug)))
            seen.append(("order", [n for _, n, _ in pool.pr_order(runs)]))
        time.sleep(0.01)
    orders = [what for who, what in seen if who == "order"]
    check(all(o == ["g1", "g2", "g3"] for o in orders), "every retry sees the same order: g1, g2, g3")
    check({slug: what for slug, what in seen if slug != "order" and what == ""} == {"g1": ""} and
          all(what == "g1" for slug, what in seen if slug in ("g2", "g3")), "exactly one goal is first and the others wait for it, every round")
    check(tickets == {slug: open(os.path.join(folder, slug)).read() for slug in tickets}, "a retry never rewrites a ticket: the first-join time stays")
    old = time.time() - 7200
    for slug in ("g1", "g2", "g3"):
        os.utime(os.path.join(folder, slug), (old, old))  # the tickets are old; only their heartbeats are fresh
    check([n for _, n, _ in pool.pr_order(runs, "g1")] == ["g1", "g2", "g3"], "an old ticket with a fresh heartbeat keeps its place: only the heartbeat drives expiry")
    os.utime(os.path.join(folder, "g2.beat"), (old, old))
    check([n for _, n, _ in pool.pr_order(runs, "g1")] == ["g1", "g3"], "a goal whose heartbeat has stopped loses its place")
    with open(os.path.join(folder, "g4"), "w") as handle:  # a ticket caught half written
        handle.write("")
    check(pool.pr_turn(runs, "g4") != "", "a goal whose ticket can't be read never counts as first")
    goal("g1", step="release")
    check(pool.pr_turn(runs, "g3") == "", "when the first goal leaves, the next in the one order has its turn")
    listed = subprocess.run([sys.executable, pool_py, "pr_turn", "--list"], cwd=tmp, capture_output=True, text=True).stdout.splitlines()
    check([line.split()[1] for line in listed] == ["g3"] and listed[0].startswith("1 g3 joined="), "pool.py pr_turn --list prints the queue in its one order: %s" % listed)
    os.chdir(here)
if not failed:
    print("PASS: #3922: three goals retrying in a loop see one pr queue order and never livelock")
sys.exit(1 if failed else 0)
