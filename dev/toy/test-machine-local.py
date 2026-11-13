#!/usr/bin/env python3
# windows: ok
# reads: skills/workflow-regression/scripts/regression.py skills/workflow-regression/scripts/runs.py skills/workflow-health/scripts/health.py skills/workflow-monitoring/scripts/checkin.py
"""machine-local: a red proof only another machine can give is recorded owed; the row and its goal go on, health warns after a week and never fails."""
import datetime
import os
import subprocess
import sys
import tempfile

root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
REG = os.path.join(root, "skills", "workflow-regression", "scripts", "regression.py")
sys.path.insert(0, os.path.join(root, "skills", "workflow-health", "scripts"))
ENV = {k: v for k, v in os.environ.items() if k not in ("GH_TOKEN", "GITHUB_TOKEN")}
fails = 0


def check(ok, what):
    global fails
    print("%s: %s" % ("PASS" if ok else "FAIL", what))
    fails += not ok


def reg(repo, *args):
    done = subprocess.run([sys.executable, REG] + list(args), cwd=repo, capture_output=True, text=True, env=ENV)
    return done.returncode, done.stdout + done.stderr


with tempfile.TemporaryDirectory() as repo:
    for cmd in (["init", "-q"], ["config", "user.email", "t@t"], ["config", "user.name", "t"]):
        subprocess.run(["git"] + cmd, cwd=repo, check=True)
    os.makedirs(os.path.join(repo, ".loop"))
    os.makedirs(os.path.join(repo, "docs", "wiki"))
    open(os.path.join(repo, ".loop", "regression.tsv"), "w").write(
        "# id\tlevel\tcommand\tgoal\tseen_red\tdescription\tcategory\tlink\nr1\tland\ttrue\t-\t-\tchecks r1\tcriterion\t\n")
    open(os.path.join(repo, "docs", "wiki", "Page.md"), "w").write("# Page\n\nMilestone: https://github.com/o/r/milestone/7\n\n[r1](Tests#t-r1)\n")
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", "x"], cwd=repo, check=True)
    code, out = reg(repo, "sync")
    check("UNPROVEN r1" in out, "before: a never-red row is UNPROVEN")
    code, out = reg(repo, "red", "r1", "--owed")
    check(code != 0 and "--runner" in out, "owed without a runner is refused")
    code, out = reg(repo, "red", "r1", "--owed", "--runner", "Mac")
    check(code == 0 and "OWED r1" in out and "WOULD open a to-do issue (milestone 7)" in out, "owed records and finds the feature milestone: " + out.strip()[:90])
    code, out = reg(repo, "sync")
    check("PENDING r1" in out and "UNPROVEN" not in out, "after: the row reads PENDING and is no longer UNPROVEN")
    sys.argv[0] = os.path.join(root, "skills", "workflow-health", "scripts", "health.py")  # health finds its siblings from here
    import health
    rows = health.criteria_rows(repo)
    check("FAIL" not in str(rows) and "UNREAD" not in str(rows), "a fresh owed proof is no failure: %s" % rows)
    owed = os.path.join(repo, ".loop", "regression-owed.tsv")
    old = (datetime.date.today() - datetime.timedelta(days=9)).isoformat()
    open(owed, "w").write("r1\t%s\tMac\t\n" % old)
    rows = health.criteria_rows(repo)
    check("WARN" in str(rows) and "FAIL" not in str(rows), "owed for 9 days warns and never fails")
    code, out = reg(repo, "red", "r1", "--owed", "--runner", "Mac")
    check(code == 0, "recording again is a no-op")
    sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True).stdout.strip()
    code, out = reg(repo, "red", "r1", "--off-platform", "--runner", "Mac", "--commit", sha)
    check(code == 0 and "OWED CLEARED r1" in out and not open(owed).read().strip(), "a real red proof clears the owed record")
checkin = open(os.path.join(root, "skills", "workflow-monitoring", "scripts", "checkin.py"), encoding="utf-8").read()
check("regression-owed.tsv" in checkin and "off-machine to-do" in checkin, "the check-in lists owed proofs under Coming up")
raise SystemExit(1 if fails else 0)
