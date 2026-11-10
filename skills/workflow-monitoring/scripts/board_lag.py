#!/usr/bin/env python3
"""The live board's template lag: each followed repo on an older template version than the operator's installed skills.

usage: board_lag.py   (prints the Issues lines; live_board.py calls template_lag)

The baseline is the installed workflow-package.json beside the skills, else a checkout's VERSION. Each repo's version is
template_version in its base branch's .loop/config.json; a repo with none reads "template version unknown". A repo that
holds the board's own skills checkout is the template itself and is skipped. It runs git and nothing else.
"""
import json
import os
import re
import subprocess
import sys

# No terminal, no waiting: a prompt from git must fail, not block.
os.environ.update(GIT_TERMINAL_PROMPT="0", GH_PROMPT_DISABLED="1", GIT_EDITOR="true", GIT_ASKPASS="true", SSH_ASKPASS="true")


def git(*args, cwd=None):
    try:
        done = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.SubprocessError):
        return ""
    return done.stdout.strip() if done.returncode == 0 else ""


def read_json(path):
    try:
        with open(path) as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return None


SKILLS = os.path.realpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, os.pardir))


def version_key(text):
    """The first three integers of a version; empty or unreadable is older than any version."""
    return tuple(int(x) for x in re.findall(r"\d+", str(text or ""))[:3])


def baseline():
    """The operator's installed template version: workflow-package.json beside the skills, else a checkout's VERSION."""
    held = read_json(os.path.join(SKILLS, "workflow-package.json"))
    if isinstance(held, dict) and held.get("version"):
        return str(held["version"]), False
    try:
        with open(os.path.join(SKILLS, os.pardir, "VERSION")) as handle:
            return handle.read().strip(), True
    except OSError:
        return "", True


def followed(root):
    try:
        with open(os.path.expanduser("~/.workflow-loop/repos")) as handle:
            extra = [line.strip() for line in handle if line.strip()]
    except OSError:
        extra = []
    return list(dict.fromkeys([root] + extra))


def template_lag(root):
    """Issues lines for each followed repo on an older template version than the operator's installed skills (the
    baseline); a repo holding the board's own skills checkout is the template itself and is skipped."""
    want, source = baseline()
    out = []
    for repo in followed(root):
        if source and SKILLS.startswith(os.path.realpath(repo) + os.sep) or not os.path.isdir(repo):
            continue
        cfg = read_json(os.path.join(repo, ".loop", "config.json"))
        if not isinstance(cfg, dict):
            continue
        base = git("show", "%s:.loop/config.json" % (cfg.get("base") or "main"), cwd=repo)
        try:
            held = str((json.loads(base) if base else cfg).get("template_version") or "")
        except ValueError:
            held = str(cfg.get("template_version") or "")
        name = os.path.basename(os.path.realpath(repo))
        if not held:
            out.append("- %s: template version unknown" % name)
        elif version_key(held) < version_key(want):
            out.append("- %s runs template v%s, older than v%s" % (name, held, want))
        else:
            continue
        out.append("    fix: ask for workflow-setup update in that repo")
    return out



if __name__ == "__main__":
    root = git("rev-parse", "--show-toplevel") or os.getcwd()
    print("\n".join(template_lag(root)) or "- (none)")
    sys.exit(0)
