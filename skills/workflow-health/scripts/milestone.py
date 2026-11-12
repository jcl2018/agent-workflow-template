#!/usr/bin/env python3
"""Free-form milestones, an owner's command (no check, rule or setup step runs it). A milestone is only for planning
by version, for example v1.0; nothing requires one.

usage: milestone.py <command> [options]

  new TITLE [--live]            create the milestone unless it exists, so running it again creates nothing
  move ISSUE TITLE|none [--live]   put an issue on an existing milestone, or clear it with none

Nothing is written to GitHub without --live: a dry run prints WOULD lines. It never closes, deletes or merges anything.
It runs git and gh, and nothing else.
"""
import argparse
import json
import os
import subprocess
import sys

# No terminal, no waiting: a prompt from git or gh must fail, not block.
os.environ.update(GIT_TERMINAL_PROMPT="0", GH_PROMPT_DISABLED="1", GIT_EDITOR="true", GIT_ASKPASS="true", SSH_ASKPASS="true")
if not sys.stdin or not sys.stdin.isatty():
    os.dup2(os.open(os.devnull, os.O_RDONLY), 0)

LIST = "repos/{owner}/{repo}/milestones?state=all&per_page=100"
REMOVED = ("features", "attach", "--all")


def run(args, cwd=None):
    try:
        return subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError) as error:
        return subprocess.CompletedProcess(args, 127, "", str(error))


def top():
    done = run(["git", "rev-parse", "--show-toplevel"])
    if done.returncode:
        sys.exit("REFUSED: not inside a git repo.")
    return done.stdout.strip()


def held(root):
    done = run(["gh", "api", LIST], root)
    try:
        return {item["title"]: item["number"] for item in json.loads(done.stdout)}
    except (ValueError, KeyError, TypeError):
        sys.exit("REFUSED: could not read the milestones: %s" % (done.stderr.strip() or "no answer")[:200])


def no_token(root):
    """True when --live has nothing to write with: no token in the environment and no gh login."""
    if os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN"):
        return False
    return run(["gh", "auth", "token"], root).returncode != 0


def cmd_new(args):
    root = top()
    have = held(root)
    title = args.title
    if title in have:
        print("EXISTS %s" % title)
    elif not args.live:
        print("WOULD create milestone %s (dry run; add --live)" % title)
    elif no_token(root):
        sys.exit("REFUSED: no GitHub token, nothing created. Fix: set GH_TOKEN or run gh auth login, or drop --live to preview.")
    else:
        made = run(["gh", "api", "repos/{owner}/{repo}/milestones", "-f", "title=" + title], root)
        if made.returncode:
            sys.exit("REFUSED: could not create %s: %s" % (title, made.stderr.strip()[:200]))
        print("CREATED %s" % title)
    return 0


def cmd_move(args):
    root = top()
    clear = args.title.lower() == "none"
    if not clear and args.title not in held(root):
        sys.exit("REFUSED: no milestone %s (issue %d unchanged). Fix: milestone.py new %s --live" % (args.title, args.issue, args.title))
    if not args.live:
        print("WOULD move issue %d to %s (dry run; add --live)" % (args.issue, "no milestone" if clear else "milestone " + args.title))
        return 0
    edit = ["--remove-milestone"] if clear else ["--milestone", args.title]
    done = run(["gh", "issue", "edit", str(args.issue)] + edit, root)
    if done.returncode:
        sys.exit("REFUSED: could not move issue %d: %s. Fix: gh issue view %d to see whether it moved before retrying"
                 % (args.issue, done.stderr.strip()[:200], args.issue))
    print("MOVED issue %d to %s" % (args.issue, "no milestone" if clear else "milestone " + args.title))
    return 0


def main():
    gone = [word for word in sys.argv[1:3] if word in REMOVED]
    if gone or "--all" in sys.argv:
        sys.exit("REFUSED: %s was removed, milestones are free form. Fix: drop the call." % (gone or ["--all"])[0])
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    item = sub.add_parser("new")
    item.add_argument("title")
    item.set_defaults(func=cmd_new)
    item = sub.add_parser("move")
    item.add_argument("issue", type=int)
    item.add_argument("title")
    item.set_defaults(func=cmd_move)
    for name in ("new", "move"):
        sub.choices[name].add_argument("--live", action="store_true")
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
