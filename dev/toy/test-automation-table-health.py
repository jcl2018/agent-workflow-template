#!/usr/bin/env python3
# windows: ok
# reads: skills/workflow-docs/scripts/counting.py skills/workflow-docs/scripts/pageformat.py
"""AUT-3: the generated Automation table shows health run by the Mac's local schedule and owes no health workflow (#3857)."""
import json
import os
import sys
import tempfile

here = os.path.dirname(os.path.abspath(__file__))
docs = os.path.join(os.path.abspath(os.path.join(here, "..", "..")), "skills", "workflow-docs", "scripts")
sys.path.insert(0, docs)
import counting  # noqa: E402

failed = []


def check(ok, text):
    print(("PASS: " if ok else "FAIL: ") + text)
    if not ok:
        failed.append(text)


def block(config, files=()):
    with tempfile.TemporaryDirectory() as tmp:
        os.makedirs(os.path.join(tmp, ".loop"))
        with open(os.path.join(tmp, ".loop", "config.json"), "w") as handle:
            json.dump(config, handle)
        for name in files:
            os.makedirs(os.path.dirname(os.path.join(tmp, name)), exist_ok=True)
            open(os.path.join(tmp, name), "w").close()
        return counting.automation_block(tmp).splitlines()


def row(lines, name):
    return next(line for line in lines if line.startswith("| %s |" % name))


lines = block({"base": "main"})
health = row(lines, "health")
check("| on | every 4 hours | this Mac's local schedule |" in health, "health reads on, every 4 hours, the Mac's local schedule: " + health)
check(health.rstrip().endswith("| none |") and "health.yml" not in "\n".join(lines) and "not deployed" not in health,
      "health owes nothing and no table line names health.yml")
check("this Mac's local schedule" in row(lines, "digest email"), "the digest email goes with the health round, on the local schedule")
regression = row(lines, "regression")
check("not deployed" in regression and "regression.yml" in regression, "regression keeps its GitHub workflow, owed when missing")
check("| off | off |" in row(block({"health_cron": "off"}), "health"), "health turned off reads off")
leftover = row(block({"base": "main"}, [".github/workflows/health.yml"]), "health")
check("this Mac's local schedule" in leftover and "GitHub Actions" not in leftover, "a leftover health.yml never makes health read as run by Actions")
if failed:
    print("FAIL: %d" % len(failed))
    sys.exit(1)
print("PASS: AUT-3: the Automation table shows health on the Mac's local schedule with no workflow owed")
