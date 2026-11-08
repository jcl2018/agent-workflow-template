#!/usr/bin/env python3
"""Survey a git repo and write its .loop/ config on a branch.

usage: setup.py [--repo DIR] [--branch NAME] [--dry-run]

Writes .loop/config.json, .loop/queue.md and .loop/findings.md, and commits them on
a new branch (default workflow-setup). It runs only git. It keeps every value already
in a config, so a second run changes nothing.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys

# No terminal, no waiting: a prompt from git or gh must fail, not block.
os.environ.update(GIT_TERMINAL_PROMPT="0", GH_PROMPT_DISABLED="1", GIT_EDITOR="true", GIT_ASKPASS="true", SSH_ASKPASS="true")
if not sys.stdin or not sys.stdin.isatty():
    os.dup2(os.open(os.devnull, os.O_RDONLY), 0)

RISKY = ["^\\.github/", "(^|/)auth", "(^|/)migrations?/", "(^|/)(schema|data)\\b"]
QUEUE = """# Goal queue

One goal a line. Other lines are ignored. Example:

    - slug: fix-title | level: 0 | touches: README.md | goal: Fix the title | done: The title reads right
"""
FINDINGS = "# Findings\n\nOpen findings, one line each.\n"


def git(repo, *args, check=True):
    done = subprocess.run(["git", "-C", repo] + list(args), capture_output=True, text=True)
    if check and done.returncode:
        sys.exit("REFUSED: git %s: %s" % (" ".join(args), done.stderr.strip()))
    return done.stdout.strip() if done.returncode == 0 else ""


def base_branch(repo):
    head = git(repo, "symbolic-ref", "--quiet", "refs/remotes/origin/HEAD", check=False)
    if head:
        return head.rsplit("/", 1)[-1]
    for name in ("main", "master", "trunk"):
        if git(repo, "rev-parse", "--verify", "--quiet", name, check=False):
            return name
    return git(repo, "branch", "--show-current") or "main"


def survey_agent():
    """The agent commands this machine has. Permissions stay as the user set them."""
    if shutil.which("claude"):
        return ["claude", "-p"]
    if shutil.which("codex"):
        return ["codex", "exec"]
    return []


def merged(repo, old):
    """The config: values already there win, the survey fills the rest."""
    agent = survey_agent()
    config = {
        "base": base_branch(repo),
        "agent_command": agent,
        "parallel": 3,
        "risky_paths": RISKY,
        "version_file": "VERSION",
        "wiki_dir": "docs/wiki",
        "pr_bumps_version": False,
        "mend": False,
        "resume_on_limit": False,
    }
    config.update(old)
    return config


def on_branch(repo, branch, path):
    """The file's text on a branch, or None."""
    done = subprocess.run(["git", "-C", repo, "show", "%s:%s" % (branch, path)], capture_output=True, text=True)
    return done.stdout if done.returncode == 0 else None


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo", default=".")
    parser.add_argument("--branch", default="workflow-setup")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    repo = git(args.repo, "rev-parse", "--show-toplevel")
    config_path = os.path.join(repo, ".loop", "config.json")

    texts = [on_branch(repo, "HEAD", ".loop/config.json")]
    if git(repo, "rev-parse", "--verify", "--quiet", args.branch, check=False):
        texts.append(on_branch(repo, args.branch, ".loop/config.json"))
    held = next((text for text in texts if text), None)
    old = json.loads(held) if held else {}
    config = merged(repo, old)
    if held and config == old:
        print("NO CHANGE: .loop/config.json is complete")
        return 0

    text = json.dumps(config, indent=2) + "\n"
    print(text, end="")
    if not config["agent_command"]:
        print("NOTE: no claude or codex on PATH; add \"agent_command\"")
    else:
        print("NOTE: a background agent stops at any permission prompt. For workflow-monitoring, add the tools you "
              "allow to \"agent_command\" yourself, or goals show failed")
    if args.dry_run:
        print("DRY RUN: nothing written")
        return 0

    current = git(repo, "branch", "--show-current")
    if current != args.branch:
        if git(repo, "rev-parse", "--verify", "--quiet", args.branch, check=False):
            git(repo, "switch", args.branch)
        else:
            git(repo, "switch", "-c", args.branch)
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    with open(config_path, "w") as handle:
        handle.write(text)
    for name, body in (("queue.md", QUEUE), ("findings.md", FINDINGS)):
        path = os.path.join(repo, ".loop", name)
        if not os.path.exists(path):
            with open(path, "w") as handle:
                handle.write(body)
    git(repo, "add", ".loop/config.json", ".loop/queue.md", ".loop/findings.md")
    git(repo, "commit", "-m", "Add workflow config", "--", ".loop/config.json", ".loop/queue.md", ".loop/findings.md")
    print("WROTE .loop/ on branch %s at %s" % (args.branch, git(repo, "rev-parse", "--short", "HEAD")))
    print("NEXT: review the config, then merge the branch into %s" % config["base"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
