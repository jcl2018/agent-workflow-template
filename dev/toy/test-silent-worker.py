#!/usr/bin/env python3
# windows: ok
# reads: skills/workflow-monitoring/scripts/checkin.py skills/workflow-monitoring/scripts/graph.py
# reads: skills/workflow-monitoring/scripts/live_board.py
"""MON-8: a worker with no report for 30 minutes shows under Needs you in the check-in; a fresh one does not."""
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


NOW = datetime.datetime(2026, 11, 13, 12, 0, 0, tzinfo=datetime.timezone.utc)


def stamp(minutes):
    return (NOW - datetime.timedelta(minutes=minutes)).strftime("%Y-%m-%dT%H:%M:%SZ")


def needs(text):
    """The lines of the Needs you section."""
    lines = text if isinstance(text, list) else text.splitlines()
    start = lines.index("Needs you") + 1
    stop = next((i for i, l in enumerate(lines) if i >= start and l == "Coming up"), len(lines))
    return "\n".join(lines[start:stop])


with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as home:
    for key in ("HOME", "USERPROFILE"):
        os.environ[key] = home  # the pod list comes from the home folder: keep the toy off the real one
    for args in (("init", "-q", "-b", "main", tmp), ("-C", tmp, "config", "user.email", "t@example.test"), ("-C", tmp, "config", "user.name", "t")):
        subprocess.run(("git",) + args, check=True, capture_output=True)
    os.makedirs(os.path.join(tmp, ".loop"))
    with open(os.path.join(tmp, ".loop", "config.json"), "w") as f:
        json.dump({"base": "main"}, f)
    runs = os.path.join(tmp, ".git", "loop", "runs")
    os.makedirs(runs)
    for slug, minutes in (("quietone", 31), ("freshone", 5)):
        run = {"slug": slug, "goal": "Goal " + slug, "status": "running", "step": "build", "worker": "session", "branch": "loop/" + slug,
               "pid": os.getpid(), "updated": stamp(minutes), "report": {"at": stamp(minutes), "text": "working"}}
        with open(os.path.join(runs, slug + ".json"), "w") as f:
            json.dump(run, f)
    out = checkin.render(tmp, NOW)
    section = needs(out)
    check("quietone" in section and "sent nothing" in section, "MON-8: a worker silent for 31 minutes shows under Needs you")
    check("freshone" not in section, "MON-8: a worker that reported 5 minutes ago does not")
    os.environ["LOOP_SESSION_QUIET"] = str(10 * 60)
    check("freshone" not in needs(checkin.render(tmp, NOW)), "MON-8: 5 minutes is still inside a 10 minute LOOP_SESSION_QUIET")
    with open(os.path.join(tmp, ".loop", "config.json"), "w") as f:
        json.dump({"base": "main", "silent_minutes": 60}, f)
    os.environ.pop("LOOP_SESSION_QUIET")
    check("quietone" not in needs(checkin.render(tmp, NOW)), "MON-8: silent_minutes 60 lets a 31 minute silence pass")
sys.exit(1 if failed else 0)
