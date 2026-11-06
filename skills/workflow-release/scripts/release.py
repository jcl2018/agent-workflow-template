#!/usr/bin/env python3
"""Ask whether a finished goal is released, then cut a draft GitHub release or leave it unreleased.

usage: release.py <command> <slug> [options]

  ask SLUG                         ask cut or leave; a batch answers leave by itself
  leave SLUG                       keep the work unreleased; changes nothing versioned
  cut SLUG [--bump patch|minor|major] [--user]
                                   bump the version, write the changelog, commit, push,
                                   and create a DRAFT release. You publish it.
  show SLUG                        print the goal's release field

A batch goal never cuts unless --user is given, and --user means the human's own message said to cut.
It runs git and gh, and nothing else. It never publishes a release, never pushes a tag and never merges.
"""
import argparse
import datetime
import json
import os
import re
import subprocess
import sys
import tempfile

SEMVER = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")
ASK = "Cut a release or leave it unreleased?"


def run(args, cwd=None):
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True)


def git(*args, cwd=None, check=True):
    done = run(["git"] + list(args), cwd=cwd)
    if check and done.returncode:
        sys.exit("REFUSED: git %s: %s" % (" ".join(args), done.stderr.strip()))
    return done.stdout.strip()


def now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def state_path(slug):
    if not re.match(r"^[a-z0-9][a-z0-9-]{0,50}$", slug):
        sys.exit("REFUSED: bad slug. Fix: lowercase letters, digits and dashes.")
    common = os.path.abspath(git("rev-parse", "--git-common-dir"))
    path = os.path.join(common, "loop", "runs")
    os.makedirs(path, exist_ok=True)
    return os.path.join(path, slug + ".json")


def load(slug):
    try:
        with open(state_path(slug)) as handle:
            return json.load(handle)
    except OSError:
        sys.exit("REFUSED: no goal named %s. Fix: run it with workflow-delivery first." % slug)
    except ValueError:
        sys.exit("REFUSED: the run record for %s is not readable JSON." % slug)


def save(state, note=None):
    """Write through a temporary file and a rename, so a reader never sees half a file."""
    state["updated"] = now()
    if note:
        state.setdefault("log", []).append("%s %s" % (state["updated"], note))
    path = state_path(state["slug"])
    temp = path + ".%d.tmp" % os.getpid()
    with open(temp, "w") as handle:
        json.dump(state, handle, indent=2)
    os.replace(temp, path)


def finished(state):
    """Refuse a goal whose checks don't hold."""
    if state.get("release") in ("cut", "leave"):
        print("ALREADY %s %s" % (state["release"], state["slug"]))
        sys.exit(0)
    if state.get("status") not in ("done", "waiting") or not state.get("pr"):
        sys.exit("REFUSED: %s is %s with no finished pull request. Fix: finish it with workflow-delivery."
                 % (state["slug"], state.get("status")))
    if state.get("checks") != "pass":
        sys.exit("REFUSED: the checks of %s have not passed. Fix: run goal.py check." % state["slug"])
    if state.get("level") != "quick" and state.get("judge") != "pass":
        sys.exit("REFUSED: the fresh judge has not passed %s. Fix: run goal.py judge." % state["slug"])


def do_leave(state, by):
    state["release"] = "leave"
    state["status"] = "done"
    state["step"] = "release"
    state["waiting"] = None
    save(state, "release leave, answered by " + by)
    print("LEFT %s unreleased (answered by %s). Nothing versioned changed." % (state["slug"], by))
    return 0


def cmd_ask(args):
    state = load(args.slug)
    if state.get("release") in ("cut", "leave"):
        print("ALREADY %s %s" % (state["release"], args.slug))
        return 0
    if state.get("status") != "done":
        sys.exit("REFUSED: %s is %s, not done. Fix: finish it with workflow-delivery." % (args.slug, state.get("status")))
    finished(state)
    if state.get("batch") and state.get("release") != "ask":
        return do_leave(state, "the batch")
    words = ["cut %s" % args.slug, "leave %s" % args.slug]
    state["status"] = "waiting"
    state["step"] = "release"
    state["release"] = "ask"
    state["waiting"] = {"ask": ASK, "words": words}
    save(state, "waiting: " + ASK)
    print("WAITING %s: %s" % (args.slug, ASK))
    print("PR: %s" % state.get("pr"))
    print("Type exactly one of:")
    for word in words:
        print("  " + word)
    return 0


def cmd_leave(args):
    state = load(args.slug)
    if state.get("release") == "cut":
        sys.exit("REFUSED: %s was already cut as v%s." % (args.slug, state.get("release_version")))
    return do_leave(state, "the user")


def cmd_show(args):
    state = load(args.slug)
    print("release=%s" % (state.get("release") or ""))
    if state.get("release_version"):
        print("release_version=%s" % state["release_version"])
    if state.get("release_url"):
        print("release_url=%s" % state["release_url"])
    return 0


def read_config(top):
    try:
        with open(os.path.join(top, ".loop", "config.json")) as handle:
            return json.load(handle)
    except (OSError, ValueError):
        sys.exit("REFUSED: no readable .loop/config.json. Fix: run workflow-setup and merge its branch.")


def bump(version, part):
    match = SEMVER.match(version)
    if not match:
        sys.exit("REFUSED: the version %r is not plain X.Y.Z. Fix: set it by hand." % version)
    major, minor, patch = (int(item) for item in match.groups())
    if part == "major":
        return "%d.0.0" % (major + 1)
    if part == "minor":
        return "%d.%d.0" % (major, minor + 1)
    return "%d.%d.%d" % (major, minor, patch + 1)


def loop_only(sha, cwd):
    files = git("diff-tree", "--no-commit-id", "--name-only", "-r", "-m", sha, cwd=cwd).splitlines()
    return bool(files) and all(name.startswith(".loop/") for name in files)


def subjects(base, cwd):
    out = git("log", "--reverse", "--format=%H %s", "%s..HEAD" % base, cwd=cwd)
    lines = []
    for line in out.splitlines():
        sha, _, subject = line.partition(" ")
        if not loop_only(sha, cwd):
            lines.append(" ".join(subject.split()))
    return lines


def changelog_text(old, version, day, bullets):
    entry = "## v%s - %s\n\n%s\n" % (version, day, "\n".join("- " + item for item in bullets) or "- No code changes")
    if not old.strip():
        return "# Changelog\n\n" + entry
    if old.startswith("# Changelog"):
        head, _, rest = old.partition("\n")
        return head + "\n\n" + entry + "\n" + rest.lstrip("\n")
    return entry + "\n" + old


def restore(cwd, files, sha_before, message):
    """Undo only what this run did: unstaged edits, or the one commit it just made."""
    if git("rev-parse", "HEAD", cwd=cwd) != sha_before:
        if git("log", "-1", "--format=%s", cwd=cwd) == message:
            git("reset", "--hard", "HEAD~1", cwd=cwd)
            print("RESTORED: removed the release commit")
        else:
            print("NOTE: HEAD is not the release commit, so nothing was reset. Check the branch by hand.")
            return
    for name in files:
        if run(["git", "ls-files", "--error-unmatch", name], cwd=cwd).returncode == 0:
            git("checkout", "--", name, cwd=cwd, check=False)
        elif os.path.exists(os.path.join(cwd, name)):
            os.remove(os.path.join(cwd, name))
    print("RESTORED: %s" % ", ".join(files))


def cmd_cut(args):
    state = load(args.slug)
    slug = args.slug
    if state.get("batch") and not args.user:
        sys.exit("REFUSED: %s is a batch goal. A batch may answer leave, never cut. Fix: cut only when the human's "
                 "own message says \"cut %s\", then pass --user." % (slug, slug))
    finished(state)
    branch = state.get("branch") or "loop/" + slug
    tree = state.get("worktree") or ""
    cwd = tree if tree and os.path.isdir(tree) else os.getcwd()
    cwd = git("rev-parse", "--show-toplevel", cwd=cwd)
    current = git("branch", "--show-current", cwd=cwd)
    if current != branch:
        sys.exit("REFUSED: %s is on branch %r, not %s. Fix: switch to %s first." % (cwd, current, branch, branch))
    if git("status", "--porcelain", "--untracked-files=no", cwd=cwd):
        sys.exit("REFUSED: uncommitted changes in %s. Fix: commit or set them aside first." % cwd)
    cfg = read_config(cwd)
    base = cfg.get("base", "main")
    if run(["git", "rev-parse", "--verify", "--quiet", "origin/" + base], cwd=cwd).returncode == 0:
        base = "origin/" + base
    checked = state.get("checks_sha")
    if checked and checked != git("rev-parse", "HEAD", cwd=cwd):
        later = git("log", "--format=%H", "%s..HEAD" % checked, cwd=cwd, check=False).splitlines()
        if not later or not all(loop_only(sha, cwd) for sha in later):
            sys.exit("REFUSED: code changed after the checks passed. Fix: run goal.py check (and judge) again.")
    version_file = cfg.get("version_file") or "VERSION"
    if os.path.isabs(version_file) or ".." in version_file.split("/"):
        sys.exit("REFUSED: version_file must be a path inside the repo.")
    vpath = os.path.join(cwd, version_file)
    if os.path.exists(vpath):
        with open(vpath) as handle:
            old_version = handle.read().strip()
        version = bump(old_version, args.bump)
    else:
        old_version, version = "none", "0.1.0"
    tag = "v" + version
    if run(["git", "rev-parse", "--verify", "--quiet", "refs/tags/" + tag], cwd=cwd).returncode == 0 or \
            run(["git", "ls-remote", "--exit-code", "--tags", "origin", tag], cwd=cwd).returncode == 0:
        sys.exit("REFUSED: tag %s already exists. Fix: pick another --bump or set the version by hand." % tag)
    bullets = subjects(base, cwd)
    day = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    cpath = os.path.join(cwd, "CHANGELOG.md")
    old = ""
    if os.path.exists(cpath):
        with open(cpath) as handle:
            old = handle.read()
    files = [version_file, "CHANGELOG.md"]
    message = "Release " + tag
    before = git("rev-parse", "HEAD", cwd=cwd)
    state["step"] = "release"
    save(state, "cutting %s from %s" % (tag, old_version))
    with open(vpath, "w") as handle:
        handle.write(version + "\n")
    with open(cpath, "w") as handle:
        handle.write(changelog_text(old, version, day, bullets))
    added = run(["git", "add", "--"] + files, cwd=cwd)
    made = added.returncode == 0 and run(["git", "commit", "-m", message, "--"] + files, cwd=cwd).returncode == 0
    if not made:
        restore(cwd, files, before, message)
        sys.exit("REFUSED: could not commit the release files.")
    pushed = run(["git", "push", "-u", "origin", branch], cwd=cwd)
    if pushed.returncode:
        restore(cwd, files, before, message)
        sys.exit("REFUSED: push failed, release undone: " + pushed.stderr.strip()[:300])
    notes = tempfile.NamedTemporaryFile("w", suffix=".md", prefix="release-notes-", delete=False)
    with notes:
        notes.write("\n".join("- " + item for item in bullets) + "\n\nPull request: %s\n" % state.get("pr", ""))
    try:
        made = run(["gh", "release", "create", tag, "--draft", "--title", tag, "--notes-file", notes.name,
                    "--target", branch], cwd=cwd)
    except OSError as error:
        made = subprocess.CompletedProcess([], 1, "", str(error))
    finally:
        os.remove(notes.name)
    if made.returncode:
        restore(cwd, files, before, message)
        released = git("rev-parse", "origin/" + branch, cwd=cwd, check=False)
        lease = run(["git", "push", "--force-with-lease=%s:%s" % (branch, released), "origin",
                     "%s:%s" % (before, branch)], cwd=cwd)
        if lease.returncode:
            print("NOTE: origin/%s still has the release commit; push the branch again to match." % branch)
        save(state, "cut %s failed at gh, restored" % tag)
        sys.exit("REFUSED: gh release create failed: " + (made.stderr or made.stdout).strip()[:300])
    url = (made.stdout.strip().splitlines() or [""])[-1]
    state["release"] = "cut"
    state["release_version"] = version
    state["release_url"] = url
    state["status"] = "done"
    state["waiting"] = None
    save(state, "release cut %s draft %s" % (tag, url))
    print("CUT %s %s -> %s on %s (%d changelog lines)" % (slug, old_version, version, branch, len(bullets)))
    print("DRAFT " + url)
    print("You publish it. The draft stays unpublished until you do. Nothing was merged.")
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    for name, func, text in (("ask", cmd_ask, "ask cut or leave"), ("leave", cmd_leave, "keep it unreleased"),
                             ("show", cmd_show, "print the release field")):
        item = sub.add_parser(name, help=text)
        item.add_argument("slug")
        item.set_defaults(func=func)
    item = sub.add_parser("cut", help="bump, changelog, commit, push, draft release")
    item.add_argument("slug")
    item.add_argument("--bump", choices=("patch", "minor", "major"), default="patch")
    item.add_argument("--user", action="store_true", help="the human's own message said to cut")
    item.set_defaults(func=cmd_cut)
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
