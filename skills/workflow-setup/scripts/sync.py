#!/usr/bin/env python3
"""The repo half of update.py: bring one repo's generated files and settings up to the installed template version.

usage: sync.py [--repo DIR] [--version X] [--wrote-skills]   (update.py --apply runs it; alone it syncs to the installed version)

It reads the base branch's .loop/config.json, never the person's checkout, and writes in a temporary worktree on
branch workflow-update-vX cut from the base branch:

    base ──(git worktree add -b workflow-update-vX)──> <git common dir>/loop/update-worktree
      fill missing repo settings (settings.fill_repo) · template_version = X · entry.py write · agents.py wire
      commit .loop/config.json .loop/START.md and the agent files ──> remove the worktree (always)
    branch states: none -> cut from base; unmerged -> reused (no new commit if nothing changed: PENDING);
                   merged but base's config still older -> refused (UPDATE_BRANCH_MERGED)

Hand-written data (config values already set, pages, rules, local settings) is only added to; the generated files
(START.md, the marked agent blocks, the stamp) are replaced. It never merges or pushes: NEXT says how to merge.
"""
import argparse
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import agents  # noqa: E402
import settings  # noqa: E402

os.environ.update(GIT_TERMINAL_PROMPT="0", GH_PROMPT_DISABLED="1", GIT_EDITOR="true", GIT_ASKPASS="true", SSH_ASKPASS="true")


def version_key(text):
    import re
    return tuple(int(x) for x in re.findall(r"\d+", str(text or ""))[:3])


def git(repo, *args, check=True):
    done = subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True)
    if check and done.returncode:
        raise RuntimeError("git %s: %s" % (" ".join(args), (done.stderr or done.stdout).strip()[-400:]))
    return done.stdout.strip() if done.returncode == 0 else ""


def base_of(repo):
    try:
        with open(os.path.join(repo, ".loop", "config.json")) as handle:
            return json.load(handle).get("base") or "main"
    except (OSError, ValueError, AttributeError):
        return git(repo, "symbolic-ref", "--short", "refs/remotes/origin/HEAD", check=False).split("/")[-1] or "main"


def base_config(repo):
    """The base branch's .loop/config.json ({} when the base has none)."""
    base = base_of(repo)
    text = git(repo, "show", "%s:.loop/config.json" % base, check=False)
    try:
        found = json.loads(text) if text else {}
    except ValueError:
        found = {}
    return dict(found, base=found.get("base") or base) if found else {}


def branch(version):
    return "workflow-update-v%s" % version


def state(repo, base, name):
    """none, unmerged or merged: the update branch against the base branch."""
    if not git(repo, "rev-parse", "--verify", "--quiet", "refs/heads/" + name, check=False):
        return "none"
    return "merged" if subprocess.run(["git", "-C", repo, "merge-base", "--is-ancestor", name, base]).returncode == 0 else "unmerged"


def report(repo, cfg, target):
    """Print the REPO line; True when the repo is behind or waits on a merge."""
    if not cfg:
        print("REPO: %s has no .loop/config.json on its base branch (merge the setup branch first)" % os.path.basename(repo))
        return False
    held = cfg.get("template_version") or ""
    if version_key(held) >= version_key(target) and held:
        print("REPO: template_version %s" % held)
        return False
    if state(repo, cfg["base"], branch(target)) == "unmerged":
        print("PENDING: %s is not merged into %s; merge it" % (branch(target), cfg["base"]))
        return True
    print("REPO: template_version %s, older than %s: run update --apply" % (held or "unknown", target))
    return True


def stamp_version(path, version):
    with open(path) as handle:
        held = json.load(handle)
    held["template_version"] = version
    with open(path, "w") as handle:
        json.dump(held, handle, indent=2)
        handle.write("\n")


def write_tree(tree, version):
    """Write the repo half inside the worktree; return the paths to commit."""
    config = os.path.join(tree, ".loop", "config.json")
    settings.fill_repo(config)
    stamp_version(config, version)
    paths = [".loop/config.json"] + agents.apply(tree)
    return paths


def apply_repo(repo, cfg, target, wrote_skills):
    """The repo half; returns the exit code."""
    if not cfg:
        print("SKIPPED repo: %s has no .loop/config.json on its base branch (merge the setup branch first) (UPDATE_SKIPPED_REPO)"
              % os.path.basename(repo))
        return 0
    base, name = cfg["base"], branch(target)
    held = cfg.get("template_version") or ""
    where = state(repo, base, name)
    if held and version_key(held) >= version_key(target):
        print("UP TO DATE: %s is at template %s" % (os.path.basename(repo), held))
        return 0
    if agents.entry(repo, "check")[0] is None:
        print("SKIPPED entry point: workflow-docs not installed beside workflow-setup (UPDATE_NO_ENTRY)")
        return 1
    if where == "merged":
        print("REFUSED: %s is already merged into %s but %s's config says template_version %s (UPDATE_BRANCH_MERGED). Fix: git "
              "branch -d %s, then run update --apply again" % (name, base, base, held or "unknown", name), file=sys.stderr)
        return 2
    common = os.path.join(repo, git(repo, "rev-parse", "--git-common-dir"))
    tree = os.path.join(os.path.abspath(common), "loop", "update-worktree")
    upstream = git(repo, "rev-list", "--count", "%s..%s@{upstream}" % (base, base), check=False)
    if upstream not in ("", "0"):
        print("WARN: local %s is %s commit(s) behind its upstream; git fetch origin %s first to cut from the latest" % (base, upstream, base))
    try:
        git(repo, "worktree", "remove", "--force", tree, check=False)
        git(repo, "worktree", "prune")
        if where == "none":
            git(repo, "worktree", "add", "-q", "-b", name, tree, base)
        else:
            git(repo, "worktree", "add", "-q", tree, name)
        paths = write_tree(tree, target)
        git(tree, "add", "-A", "--", *paths)
        if not git(tree, "diff", "--cached", "--name-only"):
            print("PENDING: %s is not merged into %s; merge it" % (name, base))
            return 1
        git(tree, "commit", "-q", "-m", "Update the workflow loop to v%s" % target)
        print("WROTE the repo half on branch %s at %s: %s" % (name, git(tree, "rev-parse", "--short", "HEAD"), ", ".join(paths)))
        print("NEXT: merge %s into %s (git switch %s && git merge %s, or open a pull request from it)" % (name, base, base, name))
        return 0
    except (RuntimeError, OSError, SystemExit) as error:
        why = str(error).strip().splitlines()[-20:]
        if where == "none":  # a branch cut this run with no commit would read as merged and refuse the rerun
            git(repo, "worktree", "remove", "--force", tree, check=False)
            if git(repo, "rev-list", "--count", "%s..%s" % (base, name), check=False) == "0":
                git(repo, "branch", "-D", name, check=False)
        if wrote_skills:
            print("PARTIAL: skills updated to v%s; repo half not written: %s (UPDATE_PARTIAL). Fix: fix the cause, then run "
                  "update --apply again (safe to rerun)" % (target, " ".join(why)), file=sys.stderr)
        else:
            print("REFUSED: repo half not written: %s (UPDATE_PARTIAL). Fix: fix the cause, then run update --apply again"
                  % " ".join(why), file=sys.stderr)
        return 2
    finally:
        git(repo, "worktree", "remove", "--force", tree, check=False)
        git(repo, "worktree", "prune", check=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo", default="")
    parser.add_argument("--version", default="")
    parser.add_argument("--wrote-skills", action="store_true", help="update.py already wrote the skills (a failure is PARTIAL)")
    args = parser.parse_args()
    repo = args.repo or git(".", "rev-parse", "--show-toplevel", check=False)
    version = args.version or agents.installed_version()
    if not repo or not version:
        sys.exit("REFUSED: need a repo and an installed version (UPDATE_SKIPPED_REPO). Fix: pass --repo and --version")
    return apply_repo(repo, base_config(repo), version, args.wrote_skills)


if __name__ == "__main__":
    sys.exit(main())
