#!/usr/bin/env python3
# windows: ok
# reads: skills/workflow-docs/scripts/deployments.py skills/workflow-docs/scripts/docs.py skills/workflow-docs/scripts/counting.py
# reads: skills/workflow-health/scripts/report.py skills/workflow-health/scripts/rules.py skills/workflow-health/scripts/controls.py
"""AUT-1, AUT-2: a routine a repo adds to the config's automation list beside health and regression.

It gets a row in the Automation block, owes a Runbook on its page (docs check), gets a generated one-line prompt that points
to the repo's Runbook (docs.py prompts), and health warns when an installed scheduled prompt holds more than that pointer."""
import json
import os
import subprocess
import sys
import tempfile

here = os.path.dirname(os.path.abspath(__file__))
root = os.path.abspath(os.path.join(here, "..", ".."))
docs = os.path.join(root, "skills", "workflow-docs", "scripts")
health = os.path.join(root, "skills", "workflow-health", "scripts")
sys.path[:0] = [docs, health]
import counting  # noqa: E402
import deployments  # noqa: E402
import report  # noqa: E402

failed = []
ENTRY = {"name": "site-deploy", "does": "Deploys the site.", "cadence": "0 6 * * *", "runs": "claude:t1", "page": "Health"}
POINTER = "In acme/site, fast-forward to origin/main, then read docs/wiki/Health.md's Runbook section site-deploy and follow it exactly."


def check(ok, text):
    print(("PASS: " if ok else "FAIL: ") + text)
    if not ok:
        failed.append(text)


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="\n") as handle:
        handle.write(text)


with tempfile.TemporaryDirectory() as tmp:
    subprocess.run(["git", "init", "-q", tmp], check=True)
    subprocess.run(["git", "-C", tmp, "remote", "add", "origin", "https://github.com/acme/site.git"], check=True)
    write(os.path.join(tmp, ".loop", "config.json"), json.dumps({"base": "main", "automation": [ENTRY]}))
    write(os.path.join(tmp, ".loop", "routines.tsv"), "health-round\tHealth\n")

    rows = [r for r in counting.automation_block(tmp).splitlines() if r.startswith("| site-deploy")]
    check(len(rows) == 1 and "Claude scheduled task t1" in rows[0], "a routine added to the config registry gets a row in the Automation block")

    held = {"Health": [(1, "### health-round")]}
    found = deployments.owed(tmp, held, "Runbook")
    check(len(found) == 1 and "site-deploy" in str(found), "a config routine with no Runbook on its page is a docs finding")
    held["Health"].append((2, "### site-deploy"))
    check(deployments.owed(tmp, held, "Runbook") == [], "a config routine with its Runbook on its page passes the docs check")
    write(os.path.join(tmp, ".loop", "config.json"), json.dumps({"base": "main", "automation": [dict(ENTRY, page="")]}))
    check(len(deployments.owed(tmp, held, "Runbook")) == 1, "a config routine that names no page is a docs finding")
    write(os.path.join(tmp, ".loop", "config.json"), json.dumps({"base": "main", "automation": [ENTRY]}))

    done = subprocess.run([sys.executable, os.path.join(docs, "docs.py"), "prompts"], cwd=tmp, capture_output=True, text=True)
    check("PROMPT site-deploy: " + POINTER in done.stdout.splitlines(), "docs.py prompts prints the one-line prompt for the routine, pointing to the repo's Runbook")
    check("PROMPT health-round: In acme/site," in done.stdout, "docs.py prompts also prints the built-in routines from routines.tsv")

    tasks = os.path.join(tmp, "tasks")
    os.environ["LOOP_SCHEDULED_TASKS_DIR"] = tasks
    write(os.path.join(tasks, "t1", "SKILL.md"), "---\nname: t1\ndescription: site\n---\n" + POINTER + "\n")
    check(report.prompt_pointer(tmp) == [], "health is quiet when the installed prompt is only the pointer")
    write(os.path.join(tasks, "t1", "SKILL.md"), "---\nname: t1\n---\n" + POINTER + "\n1. Run the deploy script.\n2. Mail the result.\n")
    warn = report.prompt_pointer(tmp)
    check(len(warn) == 1 and warn[0]["state"] == "WARN" and warn[0]["rule"] == "prompt-pointer" and "2 line(s)" in warn[0]["detail"],
          "health warns on an installed prompt that holds steps beyond the pointer")
    os.remove(os.path.join(tasks, "t1", "SKILL.md"))
    check(report.prompt_pointer(tmp) == [], "health says nothing when the task is not installed on this machine")

sys.exit(1 if failed else 0)
