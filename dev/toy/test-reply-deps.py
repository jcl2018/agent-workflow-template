#!/usr/bin/env python3
# windows: ok
# reads: skills/workflow-monitoring/scripts/checkin.py skills/workflow-monitoring/scripts/reply_hook.py
# reads: skills/workflow-monitoring/scripts/checkin.py
"""MON-14: the reply hook flags a Dependencies section that leaves out a running, holding or queued goal, naming each
one; the expected set comes from the run records and the queue file."""
import datetime
import json
import os
import subprocess
import sys
import tempfile

here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(here, "..", "..", "skills", "workflow-monitoring", "scripts"))
import checkin as reply_deps  # noqa: E402
import reply_hook  # noqa: E402

failed = []


def check(ok, text):
    print(("PASS: " if ok else "FAIL: ") + text)
    if not ok:
        failed.append(text)


def reply(deps):
    return ("Two goals run, one is queued.\n\n## All sessions\n| a | b |\n|---|---|\n| x | y |\n\n## Dependencies\n" + deps +
            "\n\n## Needs you\nNothing needs you\n\n## Coming up\n- soon\n")


with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as home:
    for key in ("HOME", "USERPROFILE"):
        os.environ[key] = home  # the pod list comes from the home folder: keep the toy off the real one
    root = os.path.join(tmp, "toyrepo")
    subprocess.run(["git", "init", "-q", "-b", "main", root], check=True)
    os.makedirs(os.path.join(root, ".loop"))
    with open(os.path.join(root, ".loop", "config.json"), "w") as f:
        json.dump({"base": "main"}, f)
    with open(os.path.join(root, ".loop", "queue.md"), "w") as f:
        f.write("- slug: later-goal | level: quick | touches: a.md | goal: Later | done: Done\n")
    runs = os.path.join(root, ".git", "loop", "runs")
    os.makedirs(runs)
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    for slug in ("first-goal", "second-goal"):
        with open(os.path.join(runs, slug + ".json"), "w") as f:
            json.dump({"slug": slug, "status": "running", "step": "build", "worker": "session", "pid": os.getpid(),
                       "updated": now, "report": {"at": now, "text": "working"}}, f)
    whole = reply("```\n== toyrepo ==\n[>] first-goal  [>] second-goal\n[ ] later-goal\n```")
    check(reply_deps.missing(whole, root) == [], "MON-14: a Dependencies section that draws every goal passes")
    no_run = reply("```\n== toyrepo ==\n[>] first-goal\n[ ] later-goal\n```")
    check(reply_deps.missing(no_run, root) == ["toyrepo/second-goal"], "MON-14: a reply that drops a running goal is flagged by name (%s)" % reply_deps.missing(no_run, root))
    no_queue = reply("```\n== toyrepo ==\n[>] first-goal  [>] second-goal\n```")
    check(reply_deps.missing(no_queue, root) == ["toyrepo/later-goal"], "MON-14: a reply that drops a queued goal is flagged by name")
    none = reply("```\n== toyrepo ==\n- (none)\n```")
    check(len(reply_deps.missing(none, root)) == 3, "MON-14: a block that draws nothing names all three goals")
    other = reply("```\n== other ==\n[>] first-goal  [>] second-goal\n[ ] later-goal\n```")
    check(len(reply_deps.missing(other, root)) == 3, "MON-14: a goal drawn under another repo's block does not count")
    wrapped = reply("```\n== toyrepo ==\n[>] first-\n    goal  [>] second-goal\n[ ] later-goal\n```")
    check(reply_deps.missing(wrapped, root) == [], "MON-14: a name wrapped at a hyphen still counts")
    check(reply_hook.left_out(no_run, root) == ["Dependencies leaves out toyrepo/second-goal (MON-14)"], "MON-14: the hook reports it in one line")
    check(reply_deps.missing("one line only", root) == [], "MON-14: a reply with no Dependencies section is left to the layout check")
sys.exit(1 if failed else 0)
