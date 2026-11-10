#!/usr/bin/env python3
"""Ask whether a finished goal is released, then cut a draft GitHub release or leave it unreleased.

usage: release.py <command> <slug> [options]

  ask SLUG    show the docs and verify steps, then ask cut or leave; a batch answers leave by itself
  leave SLUG  keep the work unreleased; changes nothing versioned
  cut SLUG [--bump patch|minor|major] [--user]
              refuse without verify steps, with stale docs or an unmet criterion; bump the version,
              write the changelog, commit, push, create a DRAFT release. You publish it.
  show SLUG   print the goal's release field

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
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fixes  # noqa: E402

# No terminal, no waiting: a prompt from git or gh must fail, not block.
os.environ.update(GIT_TERMINAL_PROMPT="0", GH_PROMPT_DISABLED="1", GIT_EDITOR="true", GIT_ASKPASS="true", SSH_ASKPASS="true")
if not sys.stdin or not sys.stdin.isatty():
    os.dup2(os.open(os.devnull, os.O_RDONLY), 0)

VERSION = re.compile(r"^\d+(\.\d+){2,3}$")
ASK = "Cut a release or leave it unreleased?"
DOCS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "workflow-docs", "scripts", "docs.py")


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
    os.makedirs(os.path.join(common, "loop", "runs"), exist_ok=True)
    return os.path.join(common, "loop", "runs", slug + ".json")


def load(slug):
    try:
        return json.load(open(state_path(slug)))
    except OSError:
        sys.exit("REFUSED: no goal named %s. Fix: run it with workflow-delivery first." % slug)
    except ValueError:
        sys.exit("REFUSED: the run record for %s is not readable JSON." % slug)


def save(state, note=None):
    state["updated"] = now()
    if note:
        state.setdefault("log", []).append("%s %s" % (state["updated"], note))
    path = state_path(state["slug"])
    temp = path + ".%d.tmp" % os.getpid()
    with open(temp, "w") as handle:
        json.dump(state, handle, indent=2)
    os.replace(temp, path)


def finished(state):
    if state.get("release") in ("cut", "leave"):
        print("ALREADY %s %s" % (state["release"], state["slug"]))
        sys.exit(0)
    if state.get("status") not in ("done", "waiting") or not state.get("pr"):
        sys.exit("REFUSED: %s is %s with no finished pull request. Fix: finish it with workflow-delivery."
                 % (state["slug"], state.get("status")))


def do_leave(state, by):
    state.update(release="leave", status="done", step="release", waiting=None)
    save(state, "release leave, answered by " + by)
    print("LEFT %s unreleased (answered by %s). Nothing versioned changed." % (state["slug"], by))
    return 0


def cmd_ask(args):
    state = load(args.slug)
    if state.get("release") not in ("cut", "leave") and state.get("status") != "done":
        sys.exit("REFUSED: %s is %s, not done. Fix: finish it with workflow-delivery." % (args.slug, state.get("status")))
    finished(state)
    tree = state.get("worktree") or ""
    top = git("rev-parse", "--show-toplevel", cwd=tree if os.path.isdir(tree) else None)
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
    words = ["cut " + args.slug, "leave " + args.slug]
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
    for line in docs_trouble(top, base, whole=True):
        print("DOCS, which cut will refuse: " + line)
    print("How to verify:\n%s" % (verify_steps(top, args.slug) or "NONE YET, which cut will refuse."))
    print("Type exactly one of:")
    for word in words:
        print("  " + word)
    return 0


def auto_on(top):
    try:
        return read_config(top).get("release_auto") is True
    except (SystemExit, AttributeError):
        return False


def auto_need(top, state):
    base = base_of(top, read_config(top))
    rows = [line.split("\t") for line in git("diff", "--name-status", "--no-renames", base + "...HEAD", cwd=top, check=False).splitlines()]
    rows = [(r[0][0], r[-1]) for r in rows if len(r) > 1 and not r[-1].startswith(".loop/")]
    docs = re.compile(r"^(docs|tests?|dev/toy)/|\.md$|(^|/)test[-_.]|[-_.]test\.")
    code = [r for r in rows if not docs.search(r[1])]
    msgs = git("log", "--format=%s%n%b", base + "..HEAD", cwd=top, check=False)
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
    for key in ("release_version", "release_url"):
        if state.get(key):
            print("%s=%s" % (key, state[key]))
    return 0


def read_config(top):
    try:
        return json.load(open(os.path.join(top, ".loop", "config.json")))
    except (OSError, ValueError):
        sys.exit("REFUSED: no readable .loop/config.json. Fix: run workflow-setup and merge its branch.")


def bump(version, part):
    if not VERSION.match(version):
        sys.exit("REFUSED: the version %r is not X.Y.Z or W.X.Y.Z. Fix: set it by hand." % version)
    numbers = [int(item) for item in version.split(".")]
    at = {"major": 0, "minor": 1}.get(part, len(numbers) - 1)
    numbers[at] += 1
    numbers[at + 1:] = [0] * (len(numbers) - at - 1)
    return ".".join(str(item) for item in numbers)


def verify_steps(top, slug):
    try:
        text = open(os.path.join(top, ".loop", "goals", slug + ".md")).read()
    except OSError:
        return ""
    part = text.partition("## Verify by hand")[2].split("\n## ", 1)[0]
    part = re.sub(r"<!--.*?-->", "", part, flags=re.S).strip()
    steps = re.split(r"^\s*\d+\.\s+(?=\S)", part, flags=re.M)[1:]
    return part if steps and all(re.search(r"Expect:\s*\S", step) for step in steps) else ""


def doc_rows(top):
    try:
        lines = [line.rstrip("\n").partition("\t") for line in open(os.path.join(top, ".loop", "docs.tsv")) if line.strip() and line[0] != "#"]
    except OSError:
        return {}
    return {page: [i.strip() for i in paths.split(",") if i.strip()] for page, _, paths in lines}


def docs_trouble(top, base, fix=False, whole=False):
    """The docs audit's findings; [] when the docs are in step. whole: every page docs.py check calls stale, list only."""
    if not doc_rows(top):
        return []
    done = run([sys.executable, DOCS, "audit", "--base", "" if whole else base] + ([] if fix and not whole else ["--dry-run"]), top)
    lines = [l for l in done.stdout.splitlines() if not l.startswith(("UNTESTED", "SKIP", "MILESTONE", "DOCS"))]
    if done.returncode and not done.stdout.strip():
        return ["the docs audit failed: " + (done.stderr.strip().splitlines() or ["no output"])[-1]]
    return lines * bool(done.returncode)


def criteria_trouble(top, cfg):
    try:
        rows = [line.rstrip("\n").split("\t") + [""] * 5 for line in open(os.path.join(top, ".loop", "regression.tsv")) if line[0] != "#"]
    except OSError:
        rows = []
    out = []
    for page in doc_rows(top):
        try:
            part = (re.split(r"\n## (?:Requirements|Criteria)[ \t]*\n", re.sub(r"(?ms)^```.*?^```[^\n]*$", "", open(os.path.join(top, cfg.get("wiki_dir") or "docs/wiki", page + ".md")).read()), maxsplit=1) + [""])[1].split("\n## ")[0]
        except OSError:
            continue
        for key in re.findall(r"^- ([A-Z]{2,5}-\d+): \S", part, re.M):
            found = [r for r in rows if key in (r[0], r[3])]
            out += ["%s (no regression row)" % key] * (not found)
            for row in found:
                if row[1] == "draft" or (row[1] != "covered" and run(["sh", "-c", row[2]], cwd=top).returncode):
                    out.append("%s (row %s is a draft or failing)" % (key, row[0]))
    return out


def wiki_link(top):
    match = re.search(r"github\.com[:/](.+?)(\.git)?$", git("remote", "get-url", "origin", cwd=top, check=False))
    return "https://github.com/%s/wiki" % match.group(1) if match else ""


def base_of(top, cfg):
    base = cfg.get("base", "main")
    return "origin/" + base if run(["git", "rev-parse", "--verify", "--quiet", "origin/" + base], cwd=top).returncode == 0 else base


def docs_lines(top, cfg, base):
    if not doc_rows(top):
        return ["Documentation: not set up (run workflow-docs init)."]
    out = git("diff", "--name-only", base + "...HEAD", "--", cfg.get("wiki_dir") or "docs/wiki", cwd=top, check=False)
    changed = [os.path.basename(name)[:-3] for name in out.splitlines() if name.endswith(".md")]
    link = wiki_link(top)
    lines = ["Documentation changed: %s." % (", ".join(changed) if changed else "none")]
    return lines + (["Wiki: " + link] if link else [])


def subjects(base, cwd):
    lines = []
    for line in git("log", "--reverse", "--format=%H %s", base + "..HEAD", cwd=cwd).splitlines():
        sha, _, subject = line.partition(" ")
        files = git("diff-tree", "--no-commit-id", "--name-only", "-r", "-m", sha, cwd=cwd).splitlines()
        if not (files and all(name.startswith(".loop/") for name in files)):
            lines.append(" ".join(subject.split()))
    return lines


def changelog_text(old, version, day, bullets, steps):
    title = "## [%s] - %s" % (version, day) if re.search(r"^## \[", old, re.M) else "## v%s - %s" % (version, day)
    entry = "%s\n\n%s\n\n### How to verify\n\n%s\n" % (title, "\n".join("- " + item for item in bullets) or "- No code changes", steps)
    if not old.strip():
        return "# Changelog\n\n" + entry
    first = re.search(r"^## ", old, re.M)
    return old[:first.start()] + entry + "\n" + old[first.start():] if first else old.rstrip("\n") + "\n\n" + entry


def restore(cwd, files, sha_before, message):
    if git("rev-parse", "HEAD", cwd=cwd) != sha_before:
        if git("log", "-1", "--format=%s", cwd=cwd) != message:
            return print("NOTE: HEAD is not the release commit, so nothing was reset. Check the branch by hand.")
        git("reset", "--hard", "HEAD~1", cwd=cwd)
        print("RESTORED: removed the release commit")
    for name in files:
        if run(["git", "ls-files", "--error-unmatch", name], cwd=cwd).returncode == 0:
            git("checkout", "--", name, cwd=cwd, check=False)
        elif os.path.exists(os.path.join(cwd, name)):
            os.remove(os.path.join(cwd, name))
    print("RESTORED: %s" % ", ".join(files))


def cmd_cut(args):
    slug = args.slug
    state = load(slug)
    if state.get("batch") and not (args.user or getattr(args, "auto", False)):
        sys.exit("REFUSED: %s is a batch goal. A batch may answer leave, never cut. Fix: cut only when the human's "
                 "own message says \"cut %s\", then pass --user." % (slug, slug))
    finished(state)
    branch = state.get("branch") or "loop/" + slug
    tree = state.get("worktree") or ""
    cwd = git("rev-parse", "--show-toplevel", cwd=tree if os.path.isdir(tree) else os.getcwd())
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
    trouble = docs_trouble(cwd, base, whole=True)
    if trouble:
        sys.exit("REFUSED: the docs audit found trouble:\n%s\nFix: run docs.py audit (workflow-docs), commit, and run "
                 "the release again." % "\n".join(trouble))
    unmet = criteria_trouble(cwd, cfg)
    if unmet:
        sys.exit("REFUSED: criteria without a passing regression row: %s." % ", ".join(unmet))
    version_file = cfg.get("version_file") or "VERSION"
    if os.path.isabs(version_file) or ".." in version_file.split("/"):
        sys.exit("REFUSED: version_file must be a path inside the repo.")
    vpath, cpath = os.path.join(cwd, version_file), os.path.join(cwd, "CHANGELOG.md")
    if os.path.exists(vpath):
        old_version = open(vpath).read().strip()
        version = bump(old_version, args.bump)
    else:
        old_version, version = "none", "0.1.0"
    tag = "v" + version
    if run(["git", "rev-parse", "--verify", "--quiet", "refs/tags/" + tag], cwd=cwd).returncode == 0 or \
            run(["git", "ls-remote", "--exit-code", "--tags", "origin", tag], cwd=cwd).returncode == 0:
        sys.exit("REFUSED: tag %s already exists. Fix: pick another --bump or set the version by hand." % tag)
    bullets = subjects(base, cwd) + fixes.lines(cwd)  # REG-6: each fixed issue with its test
    day = now()[:10]
    old = open(cpath).read() if os.path.exists(cpath) else ""
    files, message, before = [version_file, "CHANGELOG.md"], "Release " + tag, git("rev-parse", "HEAD", cwd=cwd)
    state["step"] = "release"
    save(state, "cutting %s from %s" % (tag, old_version))
    open(vpath, "w").write(version + "\n")
    open(cpath, "w").write(changelog_text(old, version, day, bullets, steps))
    if run(["git", "add", "--"] + files, cwd).returncode or run(["git", "commit", "-m", message, "--"] + files, cwd).returncode:
        restore(cwd, files, before, message)
        sys.exit("REFUSED: could not commit the release files.")
    pushed = run(["git", "push", "-u", "origin", branch], cwd)
    if pushed.returncode:
        restore(cwd, files, before, message)
        sys.exit("REFUSED: push failed, release undone: " + pushed.stderr.strip()[:300])
    notes = tempfile.NamedTemporaryFile("w", suffix=".md", prefix="release-notes-", delete=False)
    with notes:
        notes.write("\n".join("- " + item for item in bullets) + "\n\n## How to verify\n\n%s\n\n## Documentation\n\n%s\n\nPull request: %s\n"
                    % (steps, "\n\n".join(docs_lines(cwd, cfg, base)), state.get("pr", "")))
    try:
        made = run(["gh", "release", "create", tag, "--draft", "--title", tag, "--notes-file", notes.name,
                    "--target", branch], cwd=cwd)
    except OSError as error:
        made = subprocess.CompletedProcess([], 1, "", str(error))
    finally:
        os.remove(notes.name)
    if made.returncode:
        restore(cwd, files, before, message)
        lease = run(["git", "push", "--force-with-lease=%s:%s" % (branch, git("rev-parse", "origin/" + branch, cwd=cwd, check=False)),
                     "origin", "%s:%s" % (before, branch)], cwd)
        if lease.returncode:
            print("NOTE: origin/%s still has the release commit; push the branch again to match." % branch)
        save(state, "cut %s failed at gh, restored" % tag)
        sys.exit("REFUSED: gh release create failed: " + (made.stderr or made.stdout).strip()[:300])
    url = (made.stdout.strip().splitlines() or [""])[-1]
    state.update(release="cut", release_version=version, release_url=url, status="done", waiting=None)
    save(state, "release cut %s draft %s" % (tag, url))
    print("CUT %s %s -> %s on %s (%d changelog lines)" % (slug, old_version, version, branch, len(bullets)))
    print("DRAFT " + url)
    print("You publish it. The draft stays unpublished until you do. Nothing was merged.")
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    for name, func in (("ask", cmd_ask), ("leave", cmd_leave), ("show", cmd_show)):
        item = sub.add_parser(name)
        item.add_argument("slug")
        item.set_defaults(func=func)
    item = sub.add_parser("cut")
    item.add_argument("slug")
    item.add_argument("--bump", choices=("patch", "minor", "major"), default="patch")
    item.add_argument("--user", action="store_true", help="the human's own message said to cut")
    item.set_defaults(func=cmd_cut)
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
