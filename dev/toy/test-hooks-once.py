#!/usr/bin/env python3
# windows: ok
# reads: skills/workflow-setup/scripts/setup.py skills/workflow-setup/scripts/agents.py
# reads: skills/workflow-monitoring/scripts/reply_hook.py skills/workflow-monitoring/scripts/govern_hook.py
"""SET-13, issue 2880: setup installs the reply and govern hooks exactly once each, however often it runs.

Copies the setup and monitoring skills outside any goal worktree, makes a throwaway repo, and runs setup.py
--reply-hook (which adds the govern hook beside it), --govern-hook and --reply-hook again, then counts each hook in
.claude/settings.local.json. A file that already holds two copies of the govern hook ends with one."""
import json
import os
import shutil
import subprocess
import sys
import tempfile

root = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
tmp = tempfile.mkdtemp()
fails = 0


def check(label, ok, detail=""):
    global fails
    print(("PASS: " if ok else "FAIL: ") + label + ("" if ok else " " + str(detail)))
    fails += not ok


try:
    for skill in ("workflow-setup", "workflow-monitoring"):
        shutil.copytree(os.path.join(root, "skills", skill), os.path.join(tmp, "skills", skill),
                        ignore=shutil.ignore_patterns("__pycache__"))
    setup = os.path.join(tmp, "skills", "workflow-setup", "scripts", "setup.py")
    repo = os.path.join(tmp, "repo")
    os.makedirs(repo)
    for cmd in (["init", "-q"], ["config", "user.email", "t@example.com"], ["config", "user.name", "t"],
                ["commit", "--allow-empty", "-q", "-m", "init"]):
        subprocess.run(["git", "-C", repo] + cmd, check=True, capture_output=True)
    path = os.path.join(repo, ".claude", "settings.local.json")

    def run(flag):
        done = subprocess.run([sys.executable, setup, "--repo", repo, flag], capture_output=True, text=True)
        return done.returncode, done.stdout + done.stderr

    def counts():
        data = json.load(open(path))
        found = {}
        for groups in data.get("hooks", {}).values():
            for group in groups:
                for hook in group.get("hooks", []):
                    for name in ("reply_hook.py", "govern_hook.py"):
                        if "/%s'" % name in hook.get("command", "").replace("\\", "/"):
                            found[name] = found.get(name, 0) + 1
        return found

    for flag in ("--reply-hook", "--govern-hook", "--reply-hook", "--govern-hook"):
        code, out = run(flag)
        check("setup.py %s exits 0" % flag, code == 0, out[-200:])
    check("each hook is installed exactly once after four runs", counts() == {"reply_hook.py": 1, "govern_hook.py": 1}, counts())
    code, out = run("--govern-hook")
    check("a repeat install says the hook is already installed", "HOOK: already installed" in out, out[-200:])
    data = json.load(open(path))
    pre = [g for g in data["hooks"]["PreToolUse"] if "govern_hook.py" in json.dumps(g)]
    data["hooks"]["PreToolUse"] = pre + pre
    json.dump(data, open(path, "w"))
    check("the fixture holds two govern hooks", counts().get("govern_hook.py") == 2, counts())
    run("--govern-hook")
    check("an install collapses a duplicate govern hook to one", counts() == {"reply_hook.py": 1, "govern_hook.py": 1}, counts())
finally:
    shutil.rmtree(tmp, ignore_errors=True)
if not fails:
    print("PASS: SET-13: the reply and govern hooks are installed exactly once each")
sys.exit(1 if fails else 0)
