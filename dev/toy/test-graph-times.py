#!/usr/bin/env python3
# windows: ok
# reads: skills/workflow-monitoring/scripts/checkin.py
"""MON-14 (graph-times): the check-in Dependencies map draws only real, live goals, each with its time left, draws every
wait as an arrow, ends each repo block with its expected finish, and calls a worker held at pr holding, not stuck."""
import datetime
import json
import os
import subprocess
import sys
import tempfile

here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(here, "..", "..", "skills", "workflow-monitoring", "scripts"))
import checkin  # noqa: E402

failed = []


def check(ok, text):
    print(("PASS: " if ok else "FAIL: ") + text)
    if not ok:
        failed.append(text)


def stamp(at):
    return at.strftime("%Y-%m-%dT%H:%M:%SZ")


with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as home:
    for key in ("HOME", "USERPROFILE"):
        os.environ[key] = home
    root = os.path.join(tmp, "toyrepo")
    subprocess.run(["git", "init", "-q", "-b", "main", root], check=True)
    os.makedirs(os.path.join(root, ".loop"))
    with open(os.path.join(root, ".loop", "config.json"), "w") as f:
        json.dump({"base": "main"}, f)
    runs = os.path.join(root, ".git", "loop", "runs")
    os.makedirs(runs)
    now = datetime.datetime.now(datetime.timezone.utc)
    old = stamp(now - datetime.timedelta(hours=3))
    quiet = stamp(now - datetime.timedelta(hours=2))

    def write(slug, **more):
        base = {"slug": slug, "goal": "Goal " + slug, "status": "running", "step": "build", "worker": "session",
                "pid": os.getpid(), "updated": stamp(now), "report": {"at": stamp(now), "text": "working"}, "waits_on": []}
        with open(os.path.join(runs, slug + ".json"), "w") as f:
            json.dump(dict(base, **more), f)

    steps = ["%s %s" % (stamp(now - datetime.timedelta(hours=9) + datetime.timedelta(minutes=10 * n)), w)
             for n, w in enumerate(["queued", "idea", "plan", "build", "review", "qa", "ship", "pr"])]
    write("hist", status="done", step="pr", release="merged", log=steps)  # gives every step an estimate
    write("first")
    write("second", waits_on=["first"])
    write("holdpr", step="pr", updated=quiet, report={"at": quiet, "text": "holding"})
    write("gone", status="stopped")
    write("abandoned", status="done", release="leave", step="release")
    with open(os.path.join(runs, "stray.json"), "w") as f:
        json.dump({"slug": "stray", "statuses": "ok"}, f)  # a record with only a slug
    text = "\n".join(checkin.render(root, now))
    deps = text.split("Dependencies")[1].split("Needs you")[0]
    check("[>] first" in deps and "second" in deps, "the live goals are drawn")
    check("stray" not in deps, "a record with no goal or status is skipped")
    check("gone" not in deps, "a stopped goal is not drawn")
    check("left" not in deps.replace("left\n", "").replace(" left", ""), "a goal left with release: leave is not drawn")
    check("first -> second" in deps, "a wait is drawn as an arrow")
    check("[=] holdpr" in deps, "a worker held at pr reads holding, not stuck")
    check("first ~" in deps and " left" in deps, "each goal shows its time left")
    check("expected finish" in deps, "the repo block ends with its expected finish")
sys.exit(1 if failed else 0)
