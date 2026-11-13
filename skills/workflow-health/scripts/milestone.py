#!/usr/bin/env python3
"""Milestones. Free-form ones (new, move) plan by version, for example v1.0; nothing requires one. The standing ones are
"Backlog: <Feature>" for each feature page and "Backlog: Other" (DOC-10): setup and health create them, ship files into them.

usage: milestone.py <command> [options]

  new TITLE [--live]            create the milestone unless it exists, so running it again creates nothing
  move ISSUE TITLE|none [--live]   put an issue on an existing milestone, or clear it with none
  backlog [--live]              create every missing "Backlog: <Feature>" milestone and "Backlog: Other"
  leftovers FILE [--goal SLUG] [--live]   file the FILE lines of a ship reply, once each (DEL-14):
                                "FILE defect|backlog <Feature>: text" -> an issue labelled defect, or labelled backlog on that
                                feature's Backlog milestone ("Other" when no page matches); a finding already filed is skipped

Nothing is written to GitHub without --live: a dry run prints WOULD lines. It never closes, deletes or merges anything.
It runs git and gh, and nothing else.
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile

# No terminal, no waiting: a prompt from git or gh must fail, not block.
os.environ.update(GIT_TERMINAL_PROMPT="0", GH_PROMPT_DISABLED="1", GIT_EDITOR="true", GIT_ASKPASS="true", SSH_ASKPASS="true")
if not sys.stdin or not sys.stdin.isatty():
    os.dup2(os.open(os.devnull, os.O_RDONLY), 0)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import issues as IS  # noqa: E402

LIST = "repos/{owner}/{repo}/milestones?state=all&per_page=100"
OTHER = "Backlog: Other"
FILED = re.compile(r"^\W*FILE\s+(defect|backlog)\s+([^:\n]*?)\s*:\s*(\S.*?)\s*$", re.M | re.I)
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


def make(root, title, have, live):
    """Create the milestone unless it exists: (printed line, failure or ''). Writes only with live."""
    if title in have:
        return "EXISTS %s" % title, ""
    if not live:
        return "WOULD create milestone %s (dry run; add --live)" % title, ""
    if no_token(root):
        return "", "no GitHub token, nothing created. Fix: set GH_TOKEN or run gh auth login, or drop --live to preview."
    made = run(["gh", "api", "repos/{owner}/{repo}/milestones", "-f", "title=" + title], root)
    if made.returncode:
        return "", "could not create %s: %s" % (title, made.stderr.strip()[:200])
    have[title] = 0
    return "CREATED %s" % title, ""


def cmd_new(args):
    root = top()
    line, why = make(root, args.title, held(root), args.live)
    if why:
        sys.exit("REFUSED: " + why)
    print(line)
    return 0


def standing(root):
    """The standing milestones this repo should have: one per feature page, then Backlog: Other."""
    return ["Backlog: " + page for page in sorted(IS.features(root))] + [OTHER]


def cmd_backlog(args):
    root = top()
    have, bad = held(root), 0
    for title in standing(root):
        line, why = make(root, title, have, args.live)
        print(line or "FAILED " + why)
        bad += bool(why)
    return 1 if bad else 0


def home_of(root, feature):
    """The standing milestone for a feature name (case-insensitive), Backlog: Other when no page matches."""
    page = next((p for p in IS.features(root) if p.lower() == feature.strip().lower()), "")
    return "Backlog: " + page if page else OTHER


def cmd_leftovers(args):
    root = top()
    try:
        text = open(args.file, encoding="utf-8", errors="replace").read()
    except OSError as error:
        sys.exit("REFUSED: could not read %s: %s" % (args.file, error))
    found, seen, home = [], set(), os.path.expanduser("~")
    for kind, feature, what in FILED.findall(text):
        mark = hashlib.sha1(("%s|%s|%s" % (kind.lower(), home_of(root, feature), what)).encode()).hexdigest()[:12]
        if (len(home) > 1 and home in what) or re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", what):
            print("NOTE: skipped a finding that holds a private value")
        elif mark not in seen:
            seen.add(mark)
            found.append((kind.lower(), home_of(root, feature), what, mark))
    for kind, stone, what, mark in found[:10]:
        where = "" if kind == "defect" else " on milestone " + stone
        if not args.live:
            print("WOULD file %s%s: %s (dry run; add --live)" % (kind, where, what[:80]))
            continue
        old = run(["gh", "issue", "list", "--state", "all", "--label", kind, "--limit", "500", "--json", "number,body"], root)
        try:
            if any(mark in (i.get("body") or "") for i in json.loads(old.stdout)):
                print("SAME %s: already filed (%s)" % (kind, mark))
                continue
        except ValueError:
            print("FAILED %s: could not read the issues, nothing filed" % kind)
            continue
        if kind == "backlog":
            line, why = make(root, stone, held(root), True)
            if why:
                print("FAILED milestone %s: %s" % (stone, why[:120]))
                where, stone = "", ""
        run(["gh", "label", "create", kind, "--description", "Filed at ship by workflow-delivery"], root)  # kept when it exists
        body = "<!-- loop-leftover %s -->\n\n%s\n\nFiled at ship%s.\n" % (mark, what, " by goal " + args.goal if args.goal else "")
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8", newline="\n") as handle:
            handle.write(body)
        make_args = ["gh", "issue", "create", "--title", what[:90], "--label", kind, "--body-file", handle.name]
        done = run(make_args + (["--milestone", stone] if kind == "backlog" and stone else []), root)
        os.remove(handle.name)
        print(("FAILED %s: %s" % (kind, done.stderr.strip()[:160])) if done.returncode else "FILED %s%s: %s" % (kind, where, what[:80]))
    for _, _, what, _ in found[10:]:
        print("NOTE: not filed (ten at most per ship): %s" % what[:60])
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
    item = sub.add_parser("backlog")
    item.set_defaults(func=cmd_backlog)
    item = sub.add_parser("leftovers")
    item.add_argument("file")
    item.add_argument("--goal", default="")
    item.set_defaults(func=cmd_leftovers)
    for name in ("new", "move", "backlog", "leftovers"):
        sub.choices[name].add_argument("--live", action="store_true")
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
