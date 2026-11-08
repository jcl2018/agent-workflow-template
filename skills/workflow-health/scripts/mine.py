"""The Mine group: the owner's own rules, named in a private file outside the repo.

~/.workflow-loop/health.json (or the file LOOP_HEALTH names):
  {"rules": [{"name": "lint", "command": ["make", "lint"], "fix": "run make lint"}]}
Each command runs in the repo. Exit 0 is PASS, 2 is WARN, 1 is FAIL; any other exit, a missing command, a timeout
or an unreadable setting is UNREAD, never a pass. Rules run the owner's commands, so Mine is outside the
"changes nothing" and "same answer twice" promises of the fixed rules.
"""
import json
import os
import subprocess

GROUP = "mine"


def setting_path():
    return os.environ.get("LOOP_HEALTH") or os.path.join(os.path.expanduser("~"), ".workflow-loop", "health.json")


def row(state, subject, detail, fix=""):
    return {"state": state, "family": GROUP, "subject": subject, "rule": "mine", "detail": detail, "fix": fix}


def mine_rows(root):
    path = setting_path()
    if not os.path.exists(path):
        return [row("INFO", "setting", "no private rules set (%s)" % path)]
    try:
        with open(path) as handle:
            rules = json.load(handle)["rules"]
        assert isinstance(rules, list)
    except (OSError, ValueError, KeyError, AssertionError):
        return [row("UNREAD", "setting", "cannot read the private rules at %s" % path, "fix the file: a JSON object with a rules list")]
    rows = []
    for number, rule in enumerate(rules, 1):
        name = rule.get("name") if isinstance(rule, dict) else None
        command = rule.get("command") if isinstance(rule, dict) else None
        name = str(name or "rule-%d" % number)
        if not (isinstance(command, list) and command and all(isinstance(part, str) for part in command)):
            rows.append(row("UNREAD", name, "the rule has no command list", "give the rule a command as a list of words"))
            continue
        fix = str(rule.get("fix") or "run: " + " ".join(command))
        try:
            done = subprocess.run(command, cwd=root, capture_output=True, text=True, timeout=int(rule.get("timeout") or 120))
        except (OSError, ValueError, subprocess.SubprocessError) as error:
            rows.append(row("UNREAD", name, "could not run: %s" % str(error)[:100], fix))
            continue
        out = ((done.stdout or "").strip().splitlines() or (done.stderr or "").strip().splitlines() or [""])[-1][:100]
        state = {0: "PASS", 1: "FAIL", 2: "WARN"}.get(done.returncode)
        if state is None:
            rows.append(row("UNREAD", name, "exited %d, not 0, 1 or 2" % done.returncode, fix))
        else:
            rows.append(row(state, name, out or "exit %d" % done.returncode, "" if state == "PASS" else fix))
    return rows or [row("INFO", "setting", "the private file lists no rules")]
