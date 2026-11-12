"""When a requirement with no regression row fails health (HLT-2, REG-1, DOC-1; issue 118).

A requirement with no passing test shows as not enforced. Health warns while it is new and fails only when it stays not
enforced: an Unreviewed requirement warns; a Reviewed one warns for GRACE days after its Reviewed date, then fails.
The date comes from the requirement's own line on its wiki page, so no goal mapping is needed.
"""
import datetime
import glob
import json
import os
import re
import subprocess

GRACE = 7  # days a Reviewed requirement may stay not enforced (HLT-2: "none stays not enforced over 7 days")


def stamp(root, key):
    """('Reviewed', date), ('Unreviewed', None), or (None, None) when no page holds the requirement."""
    try:
        with open(os.path.join(root, ".loop", "config.json")) as handle:
            folder = json.load(handle).get("wiki_dir", "docs/wiki")
    except (OSError, ValueError):
        folder = "docs/wiki"
    line = re.compile(r"^- %s: \*\*(Unreviewed|Reviewed (\d{4}-\d\d-\d\d))\*\*" % re.escape(key), re.M)
    for page in sorted(glob.glob(os.path.join(root, folder, "*.md"))):
        with open(page) as handle:
            found = line.search(handle.read())
        if found:
            return ("Unreviewed", None) if found.group(1) == "Unreviewed" else ("Reviewed", found.group(2))
    return None, None


def row(root, key, make, today=None):
    """The health row for requirement `key` with no regression row, made with health.py's row()."""
    mark, day = stamp(root, key)
    fix = "add a row with regression.py add"
    if mark == "Unreviewed":
        return make("WARN", "criteria", key, "rows", "not enforced: no regression row yet (Unreviewed)", fix)
    if mark == "Reviewed":
        try:
            age = ((today or datetime.date.today()) - datetime.date.fromisoformat(day)).days
        except ValueError:
            return make("FAIL", "criteria", key, "rows", "Reviewed date %s is not a real date" % day, "fix the date on its line")
        if age <= GRACE:
            return make("WARN", "criteria", key, "rows", "not enforced, %d days since Reviewed %s (fails after %d)"
                        % (age, day, GRACE), fix)
        return make("FAIL", "criteria", key, "rows", "not enforced for %d days since Reviewed %s, over %d" % (age, day, GRACE), fix)
    return make("FAIL", "criteria", key, "rows", "criterion has no regression row", fix)


# The Mine group (health.py reads it through sibling_module("enforce")): The Mine group: the owner's own rules, named in a private file outside the repo.
# 
# ~/.workflow-loop/health.json (or the file LOOP_HEALTH names):
#   {"rules": [{"name": "lint", "command": ["make", "lint"], "fix": "run make lint"}]}
# Each command runs in the repo. Exit 0 is PASS, 2 is WARN, 1 is FAIL; any other exit, a missing command, a timeout
# or an unreadable setting is UNREAD, never a pass. Rules run the owner's commands, so Mine is outside the
# "changes nothing" and "same answer twice" promises of the fixed rules.
# No terminal, no waiting: a prompt from git or gh must fail, not block. health.py sets the same.
os.environ.update(GIT_TERMINAL_PROMPT="0", GH_PROMPT_DISABLED="1", GIT_EDITOR="true", GIT_ASKPASS="true", SSH_ASKPASS="true")

GROUP = "mine"


def setting_path():
    return os.environ.get("LOOP_HEALTH") or os.path.join(os.path.expanduser("~"), ".workflow-loop", "health.json")


def mine_row(state, subject, detail, fix=""):
    return {"state": state, "family": GROUP, "subject": subject, "rule": "mine", "detail": detail, "fix": fix}


def mine_rows(root):
    path = setting_path()
    if not os.path.exists(path):
        return [mine_row("INFO", "setting", "no private rules set (%s)" % path)]
    try:
        with open(path) as handle:
            rules = json.load(handle)["rules"]
        assert isinstance(rules, list)
    except (OSError, ValueError, KeyError, AssertionError):
        return [mine_row("UNREAD", "setting", "cannot read the private rules at %s" % path, "fix the file: a JSON object with a rules list")]
    rows = []
    for number, rule in enumerate(rules, 1):
        name = rule.get("name") if isinstance(rule, dict) else None
        command = rule.get("command") if isinstance(rule, dict) else None
        name = str(name or "rule-%d" % number)
        if not (isinstance(command, list) and command and all(isinstance(part, str) for part in command)):
            rows.append(mine_row("UNREAD", name, "the rule has no command list", "give the rule a command as a list of words"))
            continue
        fix = str(rule.get("fix") or "run: " + " ".join(command))
        try:
            done = subprocess.run(command, cwd=root, capture_output=True, text=True, timeout=int(rule.get("timeout") or 120))
        except (OSError, ValueError, subprocess.SubprocessError) as error:
            rows.append(mine_row("UNREAD", name, "could not run: %s" % str(error)[:100], fix))
            continue
        out = ((done.stdout or "").strip().splitlines() or (done.stderr or "").strip().splitlines() or [""])[-1][:100]
        state = {0: "PASS", 1: "FAIL", 2: "WARN"}.get(done.returncode)
        if state is None:
            rows.append(mine_row("UNREAD", name, "exited %d, not 0, 1 or 2" % done.returncode, fix))
        else:
            rows.append(mine_row(state, name, out or "exit %d" % done.returncode, "" if state == "PASS" else fix))
    return rows or [mine_row("INFO", "setting", "the private file lists no rules")]
