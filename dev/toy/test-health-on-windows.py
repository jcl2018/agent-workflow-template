#!/usr/bin/env python3
# windows: ok
# reads: skills/workflow-health/scripts/automation.py skills/workflow-health/scripts/rounds.py skills/workflow-health/scripts/workflows.py
"""health-on-windows: local register writes the registry with no launch agent, LOOP_MAIL_ENV names the mail file, and a mail.env is not refused on Windows."""
import json
import os
import subprocess
import sys
import tempfile

root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SCRIPTS = os.path.join(root, "skills", "workflow-health", "scripts")
AUT = os.path.join(SCRIPTS, "automation.py")
fails = 0


def check(ok, what):
    global fails
    print("%s: %s" % ("PASS" if ok else "FAIL", what))
    fails += not ok


with tempfile.TemporaryDirectory() as tmp:
    repo, home, agents = (os.path.join(tmp, n) for n in ("repo", "home", "agents"))
    os.makedirs(repo)
    for cmd in (["init", "-q"], ["remote", "add", "origin", "https://github.com/o/r.git"]):
        subprocess.run(["git"] + cmd, cwd=repo, check=True)
    env = dict(os.environ, LOOP_SCHEDULE_HOME=home, LOOP_AGENTS_DIR=agents, LOOP_SCHEDULE_PLATFORM="linux", PYTHONUTF8="1")
    done = subprocess.run([sys.executable, AUT, "local", "register", "--root", repo], capture_output=True, text=True, env=env)
    data = json.load(open(os.path.join(home, "repos.json"))) if os.path.exists(os.path.join(home, "repos.json")) else {"repos": {}}
    entries = list(data["repos"].values())
    check(done.returncode == 0 and len(entries) == 1 and entries[0]["cron"] == "47 */4 * * *" and entries[0]["path"] == os.path.realpath(repo),
          "local register writes the repo into repos.json on a platform that is not macOS (%s)" % (done.stdout + done.stderr).strip()[-80:])
    check(not os.path.exists(agents), "register writes no launch agent")
    again = subprocess.run([sys.executable, AUT, "local", "register", "--root", repo], capture_output=True, text=True, env=env)
    check(again.returncode == 0 and len(json.load(open(os.path.join(home, "repos.json")))["repos"]) == 1, "registering twice keeps one entry")
    plan = subprocess.run([sys.executable, AUT, "local", "tick", "--dry-run"], capture_output=True, text=True, env=env).stdout
    check("PLAN " in plan, "the registered repo is planned by tick --dry-run")
    bare = os.path.join(tmp, "bare")
    os.makedirs(bare)
    subprocess.run(["git", "init", "-q"], cwd=bare, check=True)
    refused = subprocess.run([sys.executable, AUT, "local", "register", "--root", bare], capture_output=True, text=True, env=env)
    check(refused.returncode != 0 and "SCHEDULE_NO_ORIGIN" in refused.stdout + refused.stderr, "a repo with no origin is refused")

    other = os.path.join(tmp, "other")
    os.makedirs(other)
    for cmd in (["init", "-q"], ["remote", "add", "origin", "https://github.com/o/other.git"]):
        subprocess.run(["git"] + cmd, cwd=other, check=True)
    subprocess.run([sys.executable, AUT, "local", "register", "--root", other], capture_output=True, env=env)
    subprocess.run([sys.executable, AUT, "local", "uninstall", "--root", repo], capture_output=True, env=env)
    left = len(json.load(open(os.path.join(home, "repos.json")))["repos"])
    check(left == 1 and (os.name != "nt" or not os.path.exists(agents)), "uninstall on Windows removes the repo and writes no launch agent")

    sys.path.insert(0, SCRIPTS)
    import rounds as register
    for name in ("LOOP_MAIL_ENV",):
        os.environ.pop(name, None)
    check(register.mail_path(home) == os.path.join(home, "mail.env"), "the mail file defaults to mail.env in the schedule home")
    os.environ["LOOP_MAIL_ENV"] = os.path.join(tmp, "shared.env")
    check(register.mail_path(home) == os.path.join(tmp, "shared.env"), "LOOP_MAIL_ENV names the mail file")
    mail = os.path.join(tmp, "shared.env")
    open(mail, "w").write("DIGEST_TO=a@b\n")
    os.chmod(mail, 0o644)
    if os.name == "nt":
        check(register.mail_mode(mail) == "", "on Windows a mail.env is not refused as MAIL_ENV_MODE")
    else:
        check(register.mail_mode(mail) == "MAIL_ENV_MODE", "on a posix machine a group-readable mail.env is still refused")
        os.chmod(mail, 0o600)
        check(register.mail_mode(mail) == "", "on a posix machine a 0600 mail.env is read")
    src = open(os.path.join(SCRIPTS, "workflows.py")).read()
    check("rounds.mail_path(home())" in src and "rounds.mail_mode(mail)" in src, "the tick reads the mail file through rounds")

sys.exit(1 if fails else 0)
