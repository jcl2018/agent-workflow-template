#!/usr/bin/env python3
"""Adopt a new or existing git repo: survey it, print what it would add or convert, then write it on a branch.

usage: setup.py [--repo DIR] [--branch NAME] [--dry-run] [--bare]
       setup.py [--repo DIR] --reply-hook [--remove]
       setup.py [--repo DIR] --govern-hook [--remove]
       setup.py [--repo DIR] --git-hooks [--remove | --check [--json]]

Writes .loop/ (config with every repo setting and its default, queue, findings, docs map, regression rows), a page
with a criterion and a Tests table for each top-level code folder and Home, and the regression workflow, and commits
them on a branch (default workflow-setup). It also adds every missing private setting outside the repo. An existing
file is adapted, never overwritten: a config keeps its values, a page keeps its words. It runs git and the sibling
docs and regression scripts. A second run changes nothing. --bare writes only the config, queue and findings, and skips the agent_command refusal.

--reply-hook installs the operation session's reply-format hook (workflow-monitoring's reply_hook.py, the copy beside this
skill) as a Stop hook in the repo's .claude/settings.local.json, which stays on this machine: git is told to ignore it
first. Every other key and hook in that file is kept; a second run changes nothing, and an entry with an old path is
updated. --remove takes it out again. Neither writes a branch, a commit, or any settings outside the repo.
--git-hooks writes the private-name scan as three git hooks (pre-commit, commit-msg, pre-push: seed.py) into the git
common folder's hooks, each calling workflow-delivery's private.py hook by absolute path; a default run installs them too
unless --no-git-hooks or LOOP_NO_GIT_HOOKS=1, after scanning its own staged adoption files (SET-8). A hook that is not ours
is never touched (its line to add is printed, exit 1); --remove takes out only a hook that is the stub setup wrote; --check
[--json] prints the list's and each hook's state. Exit codes and messages: skills/workflow-delivery/references/commands.md, "Private-name hooks".
--govern-hook installs govern_hook.py (MON-7) the same way, as a PreToolUse hook on Edit, Write, NotebookEdit and Bash;
--reply-hook installs it too, and --govern-hook --remove takes out only it.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import agents  # noqa: E402
import seed  # noqa: E402
import settings  # noqa: E402
import survey  # noqa: E402

# No terminal, no waiting: a prompt from git or gh must fail, not block.
os.environ.update(GIT_TERMINAL_PROMPT="0", GH_PROMPT_DISABLED="1", GIT_EDITOR="true", GIT_ASKPASS="true", SSH_ASKPASS="true")
if not sys.stdin or not sys.stdin.isatty():
    os.dup2(os.open(os.devnull, os.O_RDONLY), 0)

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


ALLOWS = {"claude": ("--allowedtools", "--allowed-tools", "--permission-mode"),
          "codex": ("-s", "--sandbox", "--full-auto")}
ADD = {"claude": ["--allowedTools", "Bash,Read,Write,Edit"], "codex": ["--full-auto"]}


def bare_agent(command):
    """The line to add when the agent command grants no tools, else None."""
    name = os.path.basename(command[0]) if command else ""
    if name in ALLOWS and not any(a.lower().split("=")[0] in ALLOWS[name] or a.lower().startswith("--dangerous") for a in command[1:]):
        return '"agent_command": %s' % json.dumps(command + ADD[name])
    return None


def merged(repo, old):
    """The config: values already there win, the survey fills the rest."""
    agent = survey_agent()
    config = settings.repo_defaults()
    files = git(repo, "ls-files").splitlines()
    config.update(base=base_branch(repo), checks=survey.checks(repo, files)[0], agent_command=agent)
    version = survey.version_habit(repo, files)[0]
    if version and "version_file" not in old:
        config["version_file"] = version
    settings.check_depth(old, ".loop/config.json")
    config.update(old)
    config["_help"] = settings.repo_help(old)
    return config


def on_branch(repo, branch, path):
    """The file's text on a branch, or None."""
    done = subprocess.run(["git", "-C", repo, "show", "%s:%s" % (branch, path)], capture_output=True, text=True)
    return done.stdout if done.returncode == 0 else None


refuse = agents.refuse
HOOKS, reply_hook = agents.HOOKS, agents.reply_hook  # moved to agents.py; kept importable from here


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo", default=".")
    parser.add_argument("--branch", default="workflow-setup")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--bare", action="store_true", help="only the config, queue and findings")
    parser.add_argument("--reply-hook", action="store_true", help="install the operation session's reply-format hook")
    parser.add_argument("--govern-hook", action="store_true", help="install the operation session's govern-only hook (MON-7)")
    parser.add_argument("--git-hooks", action="store_true", help="install the private-name scan as git hooks")
    parser.add_argument("--no-git-hooks", action="store_true", help="a default run installs no git hooks")
    parser.add_argument("--check", action="store_true", help="with --git-hooks: print the state, write nothing")
    parser.add_argument("--json", action="store_true", help="with --check: schema-versioned JSON")
    parser.add_argument("--remove", action="store_true", help="with --reply-hook, --govern-hook or --git-hooks: take that hook out")
    args = parser.parse_args()
    repo = git(args.repo, "rev-parse", "--show-toplevel")
    if args.git_hooks:
        code = 0 if args.check else seed.git_hooks(repo, args.remove)
        return seed.show(repo, args.check and args.json) if args.check else (seed.show(repo, False), code)[1]
    if args.govern_hook:
        return reply_hook(repo, args.remove, "govern_hook.py")
    if args.reply_hook:  # installs the govern hook beside it, so repos that re-run setup get MON-7 (--remove: reply only)
        return reply_hook(repo, args.remove) or (0 if args.remove else reply_hook(repo, False, "govern_hook.py"))
    config_path = os.path.join(repo, ".loop", "config.json")

    def hooked():  # the default run installs the hooks (a refusal is only a NOTE); toys and owners opt out
        if not (args.bare or args.dry_run or args.no_git_hooks or os.environ.get("LOOP_NO_GIT_HOOKS") == "1"):
            seed.git_hooks(repo, adopting=True)

    texts = [on_branch(repo, "HEAD", ".loop/config.json")]
    if git(repo, "rev-parse", "--verify", "--quiet", args.branch, check=False):
        texts.append(on_branch(repo, args.branch, ".loop/config.json"))
    held = next((text for text in texts if text), None)
    old = json.loads(held) if held else {}
    config = merged(repo, old)
    if not args.bare and not config.get("template_version") and agents.installed_version():
        config["template_version"] = agents.installed_version()  # the version this repo was set up with; update moves it
    if args.bare and "criteria" not in old:
        config["criteria"] = False
    found = survey.survey(repo, config)
    print(survey.found_line(found, config))
    files = git(repo, "ls-files").splitlines()
    for note in survey.checks(repo, files)[1] + survey.version_habit(repo, files)[1]:
        print("NOTE: " + note)
    acts = seed.decide(repo, config, found)
    if args.bare:
        acts = [a for a in acts if a[3] in ("config", "file")]
    else:
        acts += agents.plan(repo)  # .loop/START.md and the workflow-loop block in CLAUDE.md and AGENTS.md
    for verb, path, note, _ in acts:
        print("%s: %s%s" % (verb, path, " (%s)" % note if note else ""))
    if not args.dry_run:
        print("PRIVATE settings added to %s: %s" % (settings.private_path(), ", ".join(settings.fill_private()) or "none missing"))
    bare = None if args.bare else bare_agent(config["agent_command"])
    code = 1 if bare and not args.dry_run else 0
    if bare:
        print("REFUSED to call this done: agent_command %s grants no tools, so a background agent stops at its first "
              "permission prompt. Add to .loop/config.json: %s" % (config["agent_command"], bare))
    blocked = survey.ignored(repo, [a[1] for a in acts if a[3] and a[0] in ("add", "convert")] + [".loop/config.json"])
    for path, line in blocked:
        print("BLOCKED by .gitignore: %s would be left out of the commit. Add this line to .gitignore: %s" % (path, line))
    if blocked and not args.dry_run:
        print("REFUSED: nothing written. Fix .gitignore, then run setup again.")
        return 1
    if not [a for a in acts if a[3]]:
        print("NO CHANGE: nothing to add or convert")
        hooked()
        return code
    if not args.dry_run and any(a[3] == "agents" for a in acts) and agents.dirty(repo):
        print("REFUSED: %s has uncommitted changes (SETUP_AGENT_FILE_DIRTY). Fix: commit or stash them, then run setup "
              "again; nothing written." % ", ".join(agents.dirty(repo)))
        return 2
    if not config["checks"]:
        print("NOTE: no test command found, so no regression row is seeded")
    if not config["agent_command"]:
        print("NOTE: no claude or codex on PATH; add \"agent_command\"")
    else:
        print("NOTE: a background agent stops at any permission prompt. For workflow-monitoring, add the tools you "
              "allow to \"agent_command\" yourself, or goals show failed")
    if args.dry_run:
        print("DRY RUN: nothing written")
        return code

    current = git(repo, "branch", "--show-current")
    if current != args.branch:
        if git(repo, "rev-parse", "--verify", "--quiet", args.branch, check=False):
            git(repo, "switch", args.branch)
        else:
            git(repo, "checkout", "-q", "-b", args.branch)
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    with open(config_path, "w") as handle:
        handle.write(json.dumps({k: v for k, v in config.items() if k != "checks"}, indent=2) + "\n")
    seed.apply(repo, config, found, [a for a in acts if a[3] != "agents"])
    paths = [p for p in (".loop", found["wiki"], ".github/workflows/regression.yml", ".github/workflows/health.yml") if os.path.exists(os.path.join(repo, p))]
    paths += [] if args.bare else agents.apply(repo)
    git(repo, "add", "-A", "--", *paths)
    scan = seed.sibling("workflow-delivery", "private.py")  # SET-8: nothing private goes into setup's own commit
    if scan and subprocess.run([sys.executable, scan, "hook", "staged"], cwd=repo).returncode:
        print("REFUSED: a staged adoption file holds a private name (places above). Fix: remove it from that file, then run "
              "setup again; nothing committed.")
        return 1
    git(repo, "commit", "-m", "Adopt the workflow loop", "--allow-empty")
    hooked()
    print("WROTE the adoption on branch %s at %s" % (args.branch, git(repo, "rev-parse", "--short", "HEAD")))
    print("NEXT: review the branch, then merge it into %s" % config["base"])
    return code


if __name__ == "__main__":
    sys.exit(main())
