#!/usr/bin/env python3
"""Adopt a new or existing git repo: survey it, print what it would add or convert, then write it on a branch.

usage: setup.py [--repo DIR] [--branch NAME] [--dry-run] [--bare]
       setup.py [--repo DIR] --reply-hook [--remove]

Writes .loop/ (config with every repo setting and its default, queue, findings, docs map, regression rows), a page
with a criterion and a Tests table for each top-level code folder and Home, and the regression workflow, and commits
them on a branch (default workflow-setup). It also adds every missing private setting outside the repo. An existing
file is adapted, never overwritten: a config keeps its values, a page keeps its words. It runs git and the sibling
docs and regression scripts. A second run changes nothing. --bare writes only the config, queue and findings, and skips the agent_command refusal.

--reply-hook installs the operation session's reply-format hook (workflow-monitoring's reply_hook.py, the copy beside this
skill) as a Stop hook in the repo's .claude/settings.local.json, which stays on this machine: git is told to ignore it
first. Every other key and hook in that file is kept; a second run changes nothing, and an entry with an old path is
updated. --remove takes it out again. Neither writes a branch, a commit, or any settings outside the repo.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
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
    config.update(old)
    return config


def on_branch(repo, branch, path):
    """The file's text on a branch, or None."""
    done = subprocess.run(["git", "-C", repo, "show", "%s:%s" % (branch, path)], capture_output=True, text=True)
    return done.stdout if done.returncode == 0 else None


def refuse(what, fix):
    sys.stderr.write("REFUSED: %s. Fix: %s\n" % (what, fix))
    return 1


def reply_hook(repo, remove):
    """Add (or with remove, take out) the reply-format Stop hook in the repo's machine-local Claude settings."""
    script = os.path.realpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "workflow-monitoring",
                                           "scripts", "reply_hook.py"))
    common = os.path.realpath(os.path.join(repo, git(repo, "rev-parse", "--git-common-dir")))
    path = os.path.join(repo, ".claude", "settings.local.json")
    if not remove:
        if not os.path.exists(script):
            return refuse("%s is missing" % script, "install the workflow-monitoring skill beside workflow-setup")
        if "'" in script:
            return refuse("the hook's path %s holds a single quote" % script, "move the skills to a folder without one")
        if (script + os.sep).startswith(os.path.join(common, "loop", "worktrees") + os.sep) or \
                os.path.realpath(repo).startswith(os.path.join(common, "loop", "worktrees") + os.sep):
            return refuse("the hook (%s) or the repo is inside a goal's worktree, which goes away when the goal ends" % script,
                          "run setup.py from the main checkout or an installed copy of the skills")
    if not remove and git(repo, "ls-files", ".claude/settings.local.json", check=False):
        return refuse(".claude/settings.local.json is committed, so the hook's local path would be committed too",
                      "git rm --cached .claude/settings.local.json, commit that, then run again")
    try:
        with open(path) as handle:
            data = json.load(handle)
    except FileNotFoundError:
        data = {}
    except (OSError, ValueError) as error:
        return refuse("%s is not valid JSON (%s); nothing was written" % (path, error), "correct or move the file, then run again")
    stops = data.get("hooks", {}).get("Stop", []) if isinstance(data, dict) and isinstance(data.get("hooks", {}), dict) else None
    if not isinstance(stops, list) or not all(isinstance(g, dict) and isinstance(g.get("hooks", []), list) for g in stops):
        return refuse("%s has hooks in a shape this can't edit safely; nothing was written" % path,
                      'make "hooks" an object whose "Stop" is a list of {"hooks": [...]} groups')
    command = "if [ -f '%s' ]; then python3 '%s'; fi" % (script, script)
    mine = lambda h: isinstance(h, dict) and "/reply_hook.py'" in str(h.get("command", ""))
    had = [h for g in stops for h in g.get("hooks", []) if mine(h)]
    if remove and not had:
        print("HOOK: not installed")
        return 0
    if not remove and [h.get("command") for h in had] == [command]:
        print("HOOK: already installed")
        return 0
    kept = []  # every other group and hook as it was; a group left empty only by taking ours out goes
    for group in stops:
        rest = [h for h in group.get("hooks", []) if not mine(h)]
        if rest or not any(mine(h) for h in group.get("hooks", [])):
            kept.append(dict(group, hooks=rest) if "hooks" in group else group)
    if not remove:
        kept.append({"hooks": [{"type": "command", "command": command}]})
    if not subprocess.run(["git", "-C", repo, "check-ignore", "-q", ".claude/settings.local.json"]).returncode == 0:
        exclude = os.path.join(repo, git(repo, "rev-parse", "--git-path", "info/exclude"))
        os.makedirs(os.path.dirname(exclude), exist_ok=True)
        held = open(exclude).read() if os.path.exists(exclude) else ""
        if "/.claude/settings.local.json" not in held.splitlines():
            with open(exclude, "a") as handle:
                handle.write(("" if not held or held.endswith("\n") else "\n") + "/.claude/settings.local.json\n")
    data = data if isinstance(data, dict) else {}
    data.setdefault("hooks", {})["Stop"] = kept
    if not kept:
        del data["hooks"]["Stop"]
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = "%s.%d.tmp" % (path, os.getpid())
    with open(tmp, "w") as handle:
        handle.write(json.dumps(data, indent=2) + "\n")
    os.replace(tmp, path)
    print("HOOK: %s" % ("removed" if remove else "updated" if had else "added"))
    if not remove:
        print("NOTE: start a new Claude Code session (or open /hooks) to load it; it checks only the operation session")
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo", default=".")
    parser.add_argument("--branch", default="workflow-setup")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--bare", action="store_true", help="only the config, queue and findings")
    parser.add_argument("--reply-hook", action="store_true", help="install the operation session's reply-format hook")
    parser.add_argument("--remove", action="store_true", help="with --reply-hook: take the hook out")
    args = parser.parse_args()
    repo = git(args.repo, "rev-parse", "--show-toplevel")
    if args.reply_hook:
        return reply_hook(repo, args.remove)
    config_path = os.path.join(repo, ".loop", "config.json")

    texts = [on_branch(repo, "HEAD", ".loop/config.json")]
    if git(repo, "rev-parse", "--verify", "--quiet", args.branch, check=False):
        texts.append(on_branch(repo, args.branch, ".loop/config.json"))
    held = next((text for text in texts if text), None)
    old = json.loads(held) if held else {}
    config = merged(repo, old)
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
        return code
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
    seed.apply(repo, config, found, acts)
    paths = [p for p in (".loop", found["wiki"], ".github/workflows/regression.yml") if os.path.exists(os.path.join(repo, p))]
    git(repo, "add", "-A", "--", *paths)
    git(repo, "commit", "-m", "Adopt the workflow loop", "--allow-empty")
    print("WROTE the adoption on branch %s at %s" % (args.branch, git(repo, "rev-parse", "--short", "HEAD")))
    print("NEXT: review the branch, then merge it into %s; then run milestone.py new --all --live" % config["base"])
    return code


if __name__ == "__main__":
    sys.exit(main())
