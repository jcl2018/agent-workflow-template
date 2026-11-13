#!/usr/bin/env python3
# windows: ok
# reads: skills/workflow-monitoring/scripts/govern_hook.py
"""MON-7, issue 2850: the govern hook refuses the operation session's Edit and Write inside a followed repo and lets
one to a path outside every followed repo pass (its own memory notes). Commits and pushes stay refused.

Builds a throwaway repo with a .loop config and an operation.id, then feeds the hook its PreToolUse JSON."""
import json
import os
import subprocess
import sys
import tempfile

root = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
hook = os.path.join(root, "skills", "workflow-monitoring", "scripts", "govern_hook.py")
failed = []


def check(ok, text):
    print(("PASS: " if ok else "FAIL: ") + text)
    if not ok:
        failed.append(text)


with tempfile.TemporaryDirectory() as tmp:
    tmp = os.path.realpath(tmp)
    repo, home, other = (os.path.join(tmp, n) for n in ("repo", "home", "other"))
    for folder in (repo, home, other, os.path.join(home, "notes"), os.path.join(repo, "sub")):
        os.makedirs(folder, exist_ok=True)
    subprocess.run(["git", "init", "-q", "-b", "main", repo], check=True, capture_output=True)
    os.makedirs(os.path.join(repo, ".loop"))
    with open(os.path.join(repo, ".loop", "config.json"), "w") as handle:
        json.dump({}, handle)
    os.makedirs(os.path.join(repo, ".git", "loop"))
    with open(os.path.join(repo, ".git", "loop", "operation.id"), "w") as handle:
        handle.write("op1\n")
    env = dict(os.environ, HOME=home, USERPROFILE=home)
    for key in ("LOOP_ROLE", "LOOP_GOVERN_HOOK"):
        env.pop(key, None)

    def run(tool, **given):
        payload = {"session_id": "op1", "cwd": repo, "tool_name": tool, "tool_input": given}
        done = subprocess.run([sys.executable, hook], input=json.dumps(payload), capture_output=True, text=True, env=env)
        return "deny" in done.stdout

    check(run("Edit", file_path="x.py"), "#2850: a relative Edit inside the repo is refused")
    check(run("Write", file_path=os.path.join(repo, "sub", "x.py")), "#2850: an absolute Write inside the repo is refused")
    check(run("NotebookEdit", notebook_path=os.path.join(repo, "n.ipynb")), "#2850: a NotebookEdit inside the repo is refused")
    check(run("Edit", file_path=os.path.join(repo, "..", "repo", "x.py")), "#2850: a ../ path that lands in the repo is refused")
    check(not run("Write", file_path=os.path.join(home, "notes", "memory.md")), "#2850: a Write outside every repo passes")
    check(not run("Edit", file_path=os.path.join(home, "notes", "memory.md")), "#2850: an Edit outside every repo passes")
    check(run("Write", file_path=os.path.join(repo, "..", "other", "f.py")) is False, "#2850: ../other, outside the repo, passes")
    os.makedirs(os.path.join(home, ".workflow-loop"), exist_ok=True)
    with open(os.path.join(home, ".workflow-loop", "repos"), "w") as handle:
        handle.write(other + "\n")
    check(run("Write", file_path=os.path.join(other, "f.py")), "#2850: a path in another followed repo (the repos list) is refused")
    check(run("Edit"), "#2850: an Edit with no path is refused (fail closed)")
    check(run("Bash", command="git commit -m x") and run("Bash", command="git push origin main"), "MON-7: commit and push stay refused")
    check(not run("Bash", command="git status"), "MON-7: git status still passes")

print("ALL PASS" if not failed else "%d FAILED" % len(failed))
sys.exit(1 if failed else 0)
