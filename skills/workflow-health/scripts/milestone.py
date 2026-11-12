#!/usr/bin/env python3
"""Milestones for features and the Backlog. A feature is a page in .loop/docs.tsv other than Home.

usage: milestone.py <command> [options]

  features                              list the features
  new FEATURE|backlog|--all [--live]    create the milestone unless it exists, so running it again creates nothing
  attach SLUG [--live]                  put the goal's pull request in the milestone of the feature its touches name
  move ISSUE FEATURE|backlog [--live]   put an issue in a milestone

Nothing is written to GitHub without --live, GH_TOKEN or GITHUB_TOKEN: it prints WOULD lines instead. It never closes,
deletes or merges anything. It runs git and gh, and nothing else.
"""
import argparse
import json
import os
import re
import subprocess
import sys

# No terminal, no waiting: a prompt from git or gh must fail, not block.
os.environ.update(GIT_TERMINAL_PROMPT="0", GH_PROMPT_DISABLED="1", GIT_EDITOR="true", GIT_ASKPASS="true", SSH_ASKPASS="true")
if not sys.stdin or not sys.stdin.isatty():
    os.dup2(os.open(os.devnull, os.O_RDONLY), 0)

BACKLOG = "Backlog"
URLS = {}
LIST = "repos/{owner}/{repo}/milestones?state=all&per_page=100"


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


def features(root):
    found = {}
    try:
        with open(os.path.join(root, ".loop", "docs.tsv")) as handle:
            for line in handle:
                page, _, paths = line.rstrip("\n").partition("\t")
                if page and page != "Home" and not line.startswith("#"):
                    found[page] = [item.strip() for item in paths.split(",") if item.strip()]
    except OSError:
        pass
    return found


def page_of(root, subject):
    """The feature page a path belongs to: the page whose path is the longest prefix of subject (the path itself or a
    folder above it), else the page whose name is the subject (any case), else ""."""
    best, size = "", -1
    for page, paths in features(root).items():
        for path in paths + ["docs/wiki/%s.md" % page]:
            path = path.rstrip("/")
            if (subject == path or subject.startswith(path + "/")) and len(path) > size:
                best, size = page, len(path)
    if best:
        return best
    return next((page for page in features(root) if page.lower() == (subject or "").lower()), "")


def live(args):
    return bool(args.live or os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN"))


def held(root):
    done = run(["gh", "api", LIST], root)
    try:
        URLS.update({item["title"]: item.get("html_url", "") for item in json.loads(done.stdout)})
        return {item["title"]: item["number"] for item in json.loads(done.stdout)}
    except (ValueError, KeyError, TypeError):
        sys.exit("REFUSED: could not read the milestones: %s" % (done.stderr.strip() or "no answer")[:200])


def title_of(root, name):
    if name.lower() == BACKLOG.lower():
        return BACKLOG
    for page in features(root):
        if page.lower() == name.lower():
            return page
    sys.exit("REFUSED: %r is not a feature. Fix: use backlog or one of %s." % (name, ", ".join(features(root)) or "none"))


def link_page(root, title):
    """Put 'Milestone: <url>' under the feature page's title, unless the page has one."""
    try:
        folder = json.load(open(os.path.join(root, ".loop", "config.json"))).get("wiki_dir") or "docs/wiki"
        path = os.path.join(root, folder, title + ".md")
        text = open(path).read()
    except (OSError, ValueError):
        return
    if URLS.get(title) and not re.search(r"^Milestone: \S", text.partition("\n## ")[0], re.M):
        with open(path, "w") as handle:
            handle.write(re.sub(r"^# .*$", lambda m: "%s\n\nMilestone: %s" % (m.group(0), URLS[title]), text, count=1, flags=re.M))
        print("LINKED %s to its milestone" % title)


def ensure(root, title, args, have):
    if title in have:
        print("EXISTS %s" % title)
        if live(args) and title != BACKLOG:
            link_page(root, title)
    elif not live(args):
        print("WOULD create milestone %s" % title)
    else:
        text = "Goals and pull requests for the %s feature." % title if title != BACKLOG else "Findings nobody has placed yet."
        made = run(["gh", "api", "repos/{owner}/{repo}/milestones", "-f", "title=" + title, "-f", "description=" + text], root)
        if made.returncode:
            sys.exit("REFUSED: could not create %s: %s" % (title, made.stderr.strip()[:200]))
        have[title] = 0
        try:
            URLS[title] = json.loads(made.stdout)["html_url"]
        except (ValueError, KeyError, TypeError):
            pass
        print("CREATED %s" % title)
        if title != BACKLOG:
            link_page(root, title)


def cmd_features(_args):
    for page, paths in features(top()).items():
        print("%s\t%s" % (page, ", ".join(paths)))
    return 0


def cmd_new(args):
    root = top()
    have = held(root)
    names = [BACKLOG] + list(features(root)) if args.all else [title_of(root, args.name or "")]
    for title in names:
        ensure(root, title, args, have)
    return 0


def goal_feature(root, slug):
    try:
        with open(os.path.join(root, ".loop", "goals", slug + ".md")) as handle:
            text = handle.read()
    except OSError:
        sys.exit("REFUSED: no goal file for %s." % slug)
    match = re.search(r"^- Touches: (.*)$", text, re.M)
    touches = [item.strip().rstrip("/") for item in (match.group(1) if match else "").split(",") if item.strip()]
    for page, paths in features(root).items():
        wiki = ["docs/wiki/%s.md" % page]
        if any(t == p or t.startswith(p + "/") for t in touches for p in paths + wiki):
            return page
    return ""


def cmd_attach(args):
    root = top()
    common = os.path.abspath(os.path.join(root, run(["git", "rev-parse", "--git-common-dir"], root).stdout.strip()))
    try:
        with open(os.path.join(common, "loop", "runs", args.slug + ".json")) as handle:
            url = json.load(handle).get("pr") or ""
    except (OSError, ValueError):
        url = ""
    number = re.search(r"/pull/(\d+)", url)
    if not number:
        sys.exit("REFUSED: %s has no pull request yet." % args.slug)
    page = goal_feature(root, args.slug)
    if not page:
        print("NO FEATURE: the touches of %s name no feature page, so its pull request gets no milestone" % args.slug)
        return 0
    ensure(root, page, args, held(root))
    if not live(args):
        print("WOULD put pull request %s in milestone %s" % (number.group(1), page))
        return 0
    done = run(["gh", "pr", "edit", number.group(1), "--milestone", page], root)
    if done.returncode:
        sys.exit("REFUSED: could not set the milestone: %s" % done.stderr.strip()[:200])
    print("ATTACHED pull request %s to milestone %s" % (number.group(1), page))
    return 0


def cmd_move(args):
    root = top()
    title = title_of(root, args.feature)
    ensure(root, title, args, held(root))
    if not live(args):
        print("WOULD move issue %d to milestone %s" % (args.issue, title))
        return 0
    done = run(["gh", "issue", "edit", str(args.issue), "--milestone", title], root)
    if done.returncode:
        sys.exit("REFUSED: could not move issue %d: %s" % (args.issue, done.stderr.strip()[:200]))
    print("MOVED issue %d to milestone %s" % (args.issue, title))
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("features").set_defaults(func=cmd_features)
    item = sub.add_parser("new")
    item.add_argument("name", nargs="?")
    item.add_argument("--all", action="store_true")
    item.set_defaults(func=cmd_new)
    item = sub.add_parser("attach")
    item.add_argument("slug")
    item.set_defaults(func=cmd_attach)
    item = sub.add_parser("move")
    item.add_argument("issue", type=int)
    item.add_argument("feature")
    item.set_defaults(func=cmd_move)
    for name in ("new", "attach", "move"):
        sub.choices[name].add_argument("--live", action="store_true")
    args = parser.parse_args()
    if args.command == "new" and not args.all and not args.name:
        sys.exit("REFUSED: name a feature, backlog, or --all.")
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
