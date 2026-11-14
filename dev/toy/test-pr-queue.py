#!/usr/bin/env python3
# windows: ok
"""pr-queue (#3877): pr lanes take turns per repo, and a try lost to main moving does not use up max_tries.

Parts: queue (order, a goal that left, a dead holder, a stale ticket), moved (the separate cap), pr (goal.py's cmd_pr end to end
with its collaborators stubbed). No network, no model. usage: python3 -I dev/toy/test-pr-queue.py [queue|moved|pr]
"""
import argparse
import contextlib
import importlib.util
import io
import json
import os
import sys
import tempfile
import time
import types

HERE = os.path.dirname(os.path.abspath(__file__))
SK = os.path.join(HERE, "..", "..", "skills")
MON, DEL = os.path.join(SK, "workflow-monitoring", "scripts"), os.path.join(SK, "workflow-delivery", "scripts")
sys.path[:0] = [DEL, MON]
os.environ["LOOP_ROLE"] = "worker"
FAILS = []


def check(name, ok):
    print(("PASS: " if ok else "FAIL: ") + name)
    if not ok:
        FAILS.append(name)


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def runs_dir(tmp, goals):
    runs = os.path.join(tmp, "loop", "runs")
    os.makedirs(runs)
    for slug, fields in goals.items():
        json.dump(dict({"slug": slug, "status": "running", "step": "checks", "tries": 0}, **fields), open(os.path.join(runs, slug + ".json"), "w"))
    return runs


def part_queue():
    pods = load("pods_graph", os.path.join(MON, "graph.py"))
    with tempfile.TemporaryDirectory() as tmp:
        runs = runs_dir(tmp, {"a": {}, "b": {}, "c": {}})
        turn = lambda slug: pods.pr_queue("turn", runs, slug)
        got = [turn("a"), turn("b"), turn("c"), turn("b")]
        check("goals ask in order: the first runs its lane, the others are told who is ahead", got == ["", "a", "a", "a"])
        check("asking again keeps the place: a is still first", turn("a") == "")
        run = json.load(open(os.path.join(runs, "a.json")))
        run["step"] = "build"  # a failed a try, or opened its PR: it is no longer at pr
        json.dump(run, open(os.path.join(runs, "a.json"), "w"))
        check("a goal that left the pr step gives its place to the next in order", [turn("b"), turn("c")] == ["", "b"])
        run = json.load(open(os.path.join(runs, "b.json")))
        run["status"] = "failed"
        json.dump(run, open(os.path.join(runs, "b.json"), "w"))
        check("a stopped or failed holder is replaced", turn("c") == "")
        turn("a")
        old = time.time() - 4000
        os.utime(os.path.join(tmp, "loop", "pr-queue", "c"), (old, old))
        os.utime(os.path.join(tmp, "loop", "pr-queue", "c.beat"), (old, old))  # #3922: only the heartbeat drives expiry
        run = json.load(open(os.path.join(runs, "a.json")))
        run["step"] = "checks"
        json.dump(run, open(os.path.join(runs, "a.json"), "w"))
        check("a ticket nobody refreshed for over 30 minutes is replaced", turn("a") == "")


def part_moved():
    pods = load("pods_graph", os.path.join(MON, "graph.py"))
    state, saved, failed = {"slug": "g", "tries": 0}, [], []
    fake = types.SimpleNamespace(config=lambda: {"max_tries": 3}, save=lambda s, note=None: saved.append(note),
                                 failed_try=lambda s, why, step, fix: failed.append(why))
    with contextlib.redirect_stdout(io.StringIO()) as out, tempfile.TemporaryDirectory() as tmp:
        runs = runs_dir(tmp, {"g": {}})
        answers = [pods.pr_queue("moved", runs, fake, state, "main moved", "run pr again") for _ in range(5)]
    check("five tries lost to main moving are not counted: tries and max_tries stay as they were", answers == [True] * 5 and state["tries"] == 0 and not failed)
    check("each says so and the goal goes back to build", "TRY NOT COUNTED" in out.getvalue() and state["step"] == "build" and len(saved) == 5)
    with tempfile.TemporaryDirectory() as tmp:
        runs = runs_dir(tmp, {"g": {}})
        pods.pr_queue("moved", runs, fake, state, "main moved again", "run pr again")
    check("the sixth counts as an ordinary failed try", failed == ["main moved again"])


def part_pr():
    goal = load("goal_under_test", os.path.join(DEL, "goal.py"))
    pods = goal.pods
    check("goal.py found the pods module", pods is not None and hasattr(pods, "pr_queue"))
    with tempfile.TemporaryDirectory() as tmp:
        runs = runs_dir(tmp, {"first": {}, "second": {}})
        flow = {step: "done" for step in goal.FLOW}
        states = {"first": {"slug": "first", "step": "checks", "flow": dict(flow), "tries": 0, "status": "running", "branch": "loop/first"},
                  "second": {"slug": "second", "step": "checks", "flow": dict(flow), "tries": 0, "status": "running", "branch": "loop/second"}}
        calls = []
        goal.held, goal.state_dir, goal.config = (lambda slug: states[slug]), (lambda: runs), (lambda: {"base": "main", "max_tries": 3})
        goal.save = lambda state, note=None: json.dump(state, open(os.path.join(runs, state["slug"] + ".json"), "w"))  # as the real one writes the run record
        goal.guards.waiting_gate = lambda me, state: None
        goal.role.sync = lambda base: calls.append(("sync", base)) or ("conflict", "x.txt")
        with contextlib.redirect_stdout(io.StringIO()) as out:
            code_first = goal.cmd_pr(argparse.Namespace(slug="first"))
            sync_after_first = [c for c in calls if c[0] == "sync"]
            code_second = goal.cmd_pr(argparse.Namespace(slug="second"))
        text = out.getvalue()
        check("the goal first in the queue runs: it merges main, and a conflict with main is a try not counted", code_first == 1 and len(sync_after_first) == 1
              and "TRY NOT COUNTED" in text and states["first"]["tries"] == 0 and states["first"]["moved"] == 1)
        check("the second goal, with the first no longer at pr, is next in line and is not held back", "WAITING pr queue" not in text and len([c for c in calls if c[0] == "sync"]) == 2)
        for slug in states:  # both are back at pr: first lost its place when it failed a try, so it queues behind second
            states[slug]["step"] = "checks"
            json.dump(states[slug], open(os.path.join(runs, slug + ".json"), "w"))
        before = len([c for c in calls if c[0] == "sync"])
        goal.role.sync = lambda base: calls.append(("sync", base)) or (_ for _ in ()).throw(RuntimeError("the lane would start here"))
        with contextlib.redirect_stdout(io.StringIO()) as out:
            try:
                goal.cmd_pr(argparse.Namespace(slug="second"))
                runs_now = 0
            except RuntimeError:
                runs_now = 1
            waits = goal.cmd_pr(argparse.Namespace(slug="first"))
        check("two goals at pr: the one in front runs its lane, the one behind waits and merges nothing",
              runs_now == 1 and waits == 0 and "WAITING pr queue: second first" in out.getvalue() and len([c for c in calls if c[0] == "sync"]) == before + 1)


if __name__ == "__main__":
    parts = {"queue": part_queue, "moved": part_moved, "pr": part_pr}
    for name in (sys.argv[1:] or list(parts)):
        print("== " + name)
        parts[name]()
    print("ALL PASS" if not FAILS else "%d FAILED" % len(FAILS))
    sys.exit(1 if FAILS else 0)
