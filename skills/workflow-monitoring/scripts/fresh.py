#!/usr/bin/env python3
"""Keep the main checkout current (MON-4): the operation session's skills and hooks run from it, so each pass of
operate.py moves it to origin/<base> with `git merge --ff-only`, never a merge commit and never over uncommitted work.

usage: fresh.py [--base BRANCH]   prints one line when the checkout moved or could not move, nothing when it is current"""
import argparse
import os
import subprocess
import sys

ENV = dict(os.environ, GIT_TERMINAL_PROMPT="0", GH_PROMPT_DISABLED="1", GIT_EDITOR="true")


def git(root, *args, timeout=60):
    try:
        done = subprocess.run(["git", "-C", root] + list(args), capture_output=True, text=True, timeout=timeout, env=ENV)
    except (OSError, subprocess.TimeoutExpired) as error:
        return 1, str(error)
    return done.returncode, (done.stdout if done.returncode == 0 else done.stderr or done.stdout).strip()


def refresh(common, base="main"):
    """One line when the main checkout moved or could not, else ''. `common` is the repo's git common dir."""
    common = os.path.abspath(common)
    root = os.path.dirname(common) if os.path.basename(common) == ".git" else ""
    if not root or not os.path.isdir(root):
        return ""  # a bare repo has no checkout to move
    head = git(root, "rev-parse", "--abbrev-ref", "HEAD")[1]
    if head != base:
        return "CHECKOUT NOT FAST-FORWARDED: %s is on %s, not %s; its skills run as they are" % (os.path.basename(root), head or "no branch", base)
    code, said = git(root, "fetch", "-q", "origin", base)
    if code:
        return "CHECKOUT NOT FAST-FORWARDED: cannot fetch origin/%s (%s)" % (base, said.splitlines()[0][:80] if said else "no reply")
    behind = git(root, "rev-list", "--count", "HEAD..origin/" + base)[1]
    ahead = git(root, "rev-list", "--count", "origin/%s..HEAD" % base)[1]
    if behind in ("", "0"):
        return ""
    if ahead not in ("", "0"):
        return "CHECKOUT NOT FAST-FORWARDED: %s has %s commits origin/%s lacks and is %s behind; merge or push by hand" % (base, ahead, base, behind)
    code, said = git(root, "merge", "--ff-only", "-q", "origin/" + base)
    if code:
        return "CHECKOUT NOT FAST-FORWARDED: %s commits behind origin/%s; git refused (%s)" % (behind, base, said.splitlines()[0][:80] if said else "no reason")
    return "CHECKOUT FAST-FORWARDED %s by %s commits to %s" % (base, behind, git(root, "rev-parse", "--short", "HEAD")[1])


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--base", default="main")
    args = parser.parse_args()
    top = subprocess.run(["git", "rev-parse", "--git-common-dir"], capture_output=True, text=True).stdout.strip()
    line = refresh(top, args.base) if top else ""
    line and print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
