#!/usr/bin/env python3
"""Ask whether a finished goal is released, then cut a draft GitHub release or leave it unreleased.

usage: release.py <command> <slug> [options]

  ask SLUG                         show the docs and verify steps, then ask cut or leave;
                                   a batch answers leave by itself
  leave SLUG                       keep the work unreleased; changes nothing versioned
  cut SLUG [--bump patch|minor|major] [--user]
                                   refuse without verify steps or with stale docs; bump the version,
                                   write the changelog, commit, push, create a DRAFT release. You publish it.
  show SLUG                        print the goal's release field

A batch goal never cuts unless --user is given, and --user means the human's own message said to cut.
With "release_auto": true in .loop/config.json, a batch ask reads the diff: leave, patch or minor cut or leave by
itself (a DRAFT, no --user); a breaking change waits.
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

VERSION = re.compile(r"^\d+(\.\d+){2,3}$")
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
    if state.get("level") not in ("minimum", "quick") and state.get("judge") != "pass":
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
    tree = state.get("worktree") or ""
    top = git("rev-parse", "--show-toplevel", cwd=tree if tree and os.path.isdir(tree) else None)
    if state.get("batch") and state.get("release") != "ask":
        need = auto_need(top, state) if auto_on(top) else None
        if need is None:
            return do_leave(state, "the batch")
        print("NEED %s: %s" % need)
        if need[0] == "leave":
            return do_leave(state, "the batch (%s)" % need[1])
        if need[0] != "ask":
            try:
                return cmd_cut(argparse.Namespace(slug=args.slug, bump=need[0], user=False, auto=True))
            except SystemExit as stop:
                print(stop, "\nThe owner decides.")
                state = load(args.slug)
    words = ["cut %s" % args.slug, "leave %s" % args.slug]
    state["status"] = "waiting"
    state["step"] = "release"
    state["release"] = "ask"
    state["waiting"] = {"ask": ASK, "words": words}
    save(state, "waiting: " + ASK)
    print("WAITING %s: %s" % (args.slug, ASK))
    print("PR: %s" % state.get("pr"))
    cfg = read_config(top)
    base = base_of(top, cfg)
    for line in docs_lines(top, cfg, base):
        print(line)
    stale = stale_pages(top, cfg, base)
    if stale:
        print("STALE pages, which cut will refuse: " + ", ".join(stale))
    print("How to verify:\n%s" % (verify_steps(top, args.slug) or "NONE YET, which cut will refuse."))
    print("Type exactly one of:")
    for word in words:
        print("  " + word)
    return 0


def auto_on(top):
    try:
        with open(os.path.join(top, ".loop", "config.json")) as handle:
            return json.load(handle).get("release_auto") is True
    except (OSError, ValueError, AttributeError):
        return False


def auto_need(top, state):
    """(need, reason) from the diff: leave, patch, minor or ask; recorded in the run state."""
    base = base_of(top, read_config(top))
    rows = [line.split("\t") for line in git("diff", "--name-status", "--no-renames", "%s...HEAD" % base, cwd=top,
                                             check=False).splitlines()]
    rows = [(r[0][0], r[-1]) for r in rows if len(r) > 1 and not r[-1].startswith(".loop/")]
    docs = re.compile(r"^(docs|dev|tests?)/|\.md$|(^|/)test[-_.]|[-_.]test\.")
    code = [r for r in rows if not docs.search(r[1])]
    msgs = git("log", "--format=%s%n%b", "%s..HEAD" % base, cwd=top, check=False)
    if not code:
        need = ("leave", "only docs, tests or .loop changed")
    elif re.search(r"BREAKING|^\w+(\([^)]*\))?!:", msgs, re.M) or any(k == "D" for k, _ in code):
        need = ("ask", "a breaking change: a commit says so or a file was removed")
    elif any(k == "A" for k, _ in code) or re.search(r"^feat\b", msgs, re.M | re.I):
        need = ("minor", "a new feature or command")
    else:
        need = ("patch", "a fix")
    state["release_need"], state["release_reason"] = need
    save(state, "release need %s: %s" % need)
    return need


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
    """Move one number and zero the ones after it. Patch is the last number, so 1.3.3.3 becomes 1.3.3.4."""
    if not VERSION.match(version):
        sys.exit("REFUSED: the version %r is not X.Y.Z or W.X.Y.Z. Fix: set it by hand." % version)
    numbers = [int(item) for item in version.split(".")]
    at = {"major": 0, "minor": 1}.get(part, len(numbers) - 1)
    numbers[at] += 1
    numbers[at + 1:] = [0] * (len(numbers) - at - 1)
    return ".".join(str(item) for item in numbers)


def verify_steps(top, slug):
    """The goal's Verify by hand section, or "" unless it has numbered steps and each has an Expect: line."""
    try:
        with open(os.path.join(top, ".loop", "goals", slug + ".md")) as handle:
            text = handle.read()
    except OSError:
        return ""
    if "## Verify by hand" not in text:
        return ""
    part = text.split("## Verify by hand", 1)[1].split("\n## ", 1)[0]
    part = re.sub(r"<!--.*?-->", "", part, flags=re.S).strip()
    steps = re.split(r"^\s*\d+\.\s+(?=\S)", part, flags=re.M)[1:]
    return part if steps and all(re.search(r"Expect:\s*\S", step) for step in steps) else ""


def doc_rows(top):
    rows = {}
    try:
        with open(os.path.join(top, ".loop", "docs.tsv")) as handle:
            for line in handle:
                if line.strip() and not line.startswith("#"):
                    page, _, paths = line.rstrip("\n").partition("\t")
                    rows[page] = [item.strip() for item in paths.split(",") if item.strip()]
    except OSError:
        pass
    return rows


def stale_pages(top, cfg, base):
    """Mapped pages that are missing, or older than a path they describe within this branch."""
    folder = cfg.get("wiki_dir") or "docs/wiki"
    out = []
    for page, paths in sorted(doc_rows(top).items()):
        rel = "%s/%s.md" % (folder, page)
        last = git("rev-list", "-1", "HEAD", "--", rel, cwd=top, check=False)
        if not last or not os.path.exists(os.path.join(top, rel)):
            out.append(page + " (missing)")
            continue
        start = base if run(["git", "merge-base", "--is-ancestor", last, base], cwd=top).returncode == 0 else last
        if git("log", "--format=%h", "%s..HEAD" % start, "--", *paths, cwd=top, check=False):
            out.append(page)
    return out


def docs_changed(top, cfg, base):
    folder = cfg.get("wiki_dir") or "docs/wiki"
    out = git("diff", "--name-only", "%s...HEAD" % base, "--", folder, cwd=top, check=False)
    return [os.path.basename(name)[:-3] for name in out.splitlines() if name.endswith(".md")]


def wiki_link(top):
    url = git("remote", "get-url", "origin", cwd=top, check=False)
    match = re.search(r"github\.com[:/](.+?)(\.git)?$", url)
    return "https://github.com/%s/wiki" % match.group(1) if match else ""


def base_of(top, cfg):
    base = cfg.get("base", "main")
    if run(["git", "rev-parse", "--verify", "--quiet", "origin/" + base], cwd=top).returncode == 0:
        return "origin/" + base
    return base


def docs_lines(top, cfg, base):
    if not doc_rows(top):
        return ["Documentation: not set up (run workflow-docs init)."]
    changed = docs_changed(top, cfg, base)
    link = wiki_link(top)
    lines = ["Documentation changed: %s." % (", ".join(changed) if changed else "none")]
    return lines + (["Wiki: " + link] if link else [])


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


def changelog_text(old, version, day, bullets, steps):
    title = "## [%s] - %s" % (version, day) if re.search(r"^## \[", old, re.M) else "## v%s - %s" % (version, day)
    body = "\n".join("- " + item for item in bullets) or "- No code changes"
    entry = "%s\n\n%s\n\n### How to verify\n\n%s\n" % (title, body, steps)
    if not old.strip():
        return "# Changelog\n\n" + entry
    first = re.search(r"^## ", old, re.M)
    if first:
        return old[:first.start()] + entry + "\n" + old[first.start():]
    return old.rstrip("\n") + "\n\n" + entry


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
    if state.get("batch") and not args.user and not getattr(args, "auto", False):
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
    base = base_of(cwd, cfg)
    steps = verify_steps(cwd, slug)
    if not steps:
        sys.exit("REFUSED: %s has no complete steps under ## Verify by hand. Fix: give every numbered step an Expect: "
                 "line in .loop/goals/%s.md, and commit it." % (slug, slug))
    stale = stale_pages(cwd, cfg, base)
    if stale:
        sys.exit("REFUSED: these pages are stale: %s. Fix: update them with workflow-docs, commit, and run goal.py "
                 "check again." % ", ".join(stale))
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
        handle.write(changelog_text(old, version, day, bullets, steps))
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
        notes.write("\n".join("- " + item for item in bullets) + "\n\n## How to verify\n\n%s\n\n" % steps)
        notes.write("## Documentation\n\n%s\n\n" % "\n\n".join(docs_lines(cwd, cfg, base)))
        notes.write("Pull request: %s\n" % state.get("pr", ""))
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
