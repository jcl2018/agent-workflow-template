#!/usr/bin/env python3
"""Keep the review state of wiki criteria honest. Nothing here blocks a change.

usage: criteria.py <command> [options]

  review ID [ID ...] --user    mark criteria reviewed; --user means the owner's own words said so
  sync [--commit] [--dry-run]  return every reviewed criterion whose text changed to Unreviewed, marked
                               (changed after review), and fix each page's banner; --commit commits the pages

A reviewed line ends with <!-- reviewed HASH -->, a hash of its text. A line with a reviewed stage and no matching
hash has changed, so sync returns it. It runs git and nothing else.
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys

# No terminal, no waiting: a prompt from git or gh must fail, not block.
os.environ.update(GIT_TERMINAL_PROMPT="0", GH_PROMPT_DISABLED="1", GIT_EDITOR="true", GIT_ASKPASS="true", SSH_ASKPASS="true")
if not sys.stdin or not sys.stdin.isatty():
    os.dup2(os.open(os.devnull, os.O_RDONLY), 0)

LINE = re.compile(r"^- ([A-Z]{2,5}-\d+): \*\*(Unreviewed|Reviewed|Enforced|Proven)\*\* (.+?)(?: <!-- reviewed (\w+) -->)?$")
ID = re.compile(r"^[A-Z]{2,5}-\d+$")
BANNER = "> **Unreviewed:** %d of %d criteria on this page have not been reviewed by the owner."
RETURNED = "(changed after review) "


def git(*args, check=True):
    done = subprocess.run(["git"] + list(args), capture_output=True, text=True)
    if check and done.returncode:
        sys.exit("REFUSED: git %s: %s" % (" ".join(args), done.stderr.strip()[:300]))
    return done.stdout.strip()


def seal(text):
    return hashlib.sha256(text.encode()).hexdigest()[:8]


def pages(root):
    try:
        with open(os.path.join(root, ".loop", "config.json")) as handle:
            folder = json.load(handle).get("wiki_dir") or "docs/wiki"
    except (OSError, ValueError):
        sys.exit("REFUSED: no readable .loop/config.json. Fix: run workflow-setup and merge its branch.")
    try:
        names = sorted(name for name in os.listdir(os.path.join(root, folder)) if name.endswith(".md"))
    except OSError:
        return []
    return [os.path.join(folder, name) for name in names]


def stage_from_rows(root, key):
    """The stage a reviewed criterion's tests earn: the same rule as docs check."""
    try:
        with open(os.path.join(root, ".loop", "regression.tsv")) as handle:
            rows = [line.rstrip("\n").split("\t") + [""] * 5 for line in handle if line.strip() and line[0] != "#"]
    except OSError:
        rows = []
    tests = [row for row in rows if row[1] != "draft" and (row[3] if ID.match(row[3]) else row[0]) == key]
    if not tests:
        return "Reviewed"
    return "Proven" if all(row[4] or row[1] == "covered" for row in tests) else "Enforced"


def banner(lines):
    """Put the banner right for the criteria in these lines."""
    lines = [line for line in lines if not line.startswith("> **Unreviewed:**")]
    found = [LINE.match(line) for line in lines]
    found = [match for match in found if match]
    waiting = sum(1 for match in found if match.group(2) == "Unreviewed")
    at = next((n for n, line in enumerate(lines) if line.startswith("Tests: ")), None)
    if waiting and at is not None:
        lines.insert(at + 1, BANNER % (waiting, len(found)))
    return lines


def rewrite(root, change):
    """Run change(match) over every criterion line. It returns a new line, or None to leave it."""
    touched, names = [], []
    for rel in pages(root):
        with open(os.path.join(root, rel)) as handle:
            text = handle.read()
        lines = text.split("\n")
        for number, line in enumerate(lines):
            match = LINE.match(line)
            fresh = change(match) if match else None
            if fresh:
                lines[number] = fresh
                names.append(match.group(1))
        result = "\n".join(banner(lines))
        if result != text:
            touched.append((rel, result))
    return touched, names


def write(root, touched):
    for rel, text in touched:
        with open(os.path.join(root, rel), "w") as handle:
            handle.write(text)


def cmd_sync(args):
    root = git("rev-parse", "--show-toplevel")

    def change(match):
        key, stage, text, mark = match.groups()
        if stage != "Unreviewed" and mark != seal(text):
            return "- %s: **Unreviewed** %s%s" % (key, RETURNED, text)
        return None

    touched, names = rewrite(root, change)
    for key in names:
        print("RETURNED %s: its text changed after review, so it is Unreviewed" % key)
    if not names:
        print("CRITERIA OK")
    elif args.dry_run:
        print("DRY RUN: nothing written")
    else:
        write(root, touched)
        if args.commit:
            paths = [rel for rel, _ in touched]
            git("add", "--", *paths)
            git("commit", "-m", "Return changed criteria to Unreviewed: " + ", ".join(names), "--", *paths)
    return 0


def cmd_review(args):
    if not args.user:
        sys.exit("REFUSED: only the owner reviews a criterion. Fix: pass --user when their own words said to.")
    bad = [key for key in args.ids if not ID.match(key)]
    if bad:
        sys.exit("REFUSED: not a criterion id: %s." % ", ".join(bad))
    root = git("rev-parse", "--show-toplevel")

    def change(match):
        key, _, text, _ = match.groups()
        if key not in args.ids:
            return None
        text = text[len(RETURNED):] if text.startswith(RETURNED) else text
        return "- %s: **%s** %s <!-- reviewed %s -->" % (key, stage_from_rows(root, key), text, seal(text))

    touched, names = rewrite(root, change)
    missing = sorted(set(args.ids) - set(names))
    if missing:
        sys.exit("REFUSED: no criterion %s. Nothing was changed." % ", ".join(missing))
    write(root, touched)
    for key in names:
        print("REVIEWED " + key)
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    item = sub.add_parser("review")
    item.add_argument("ids", nargs="+")
    item.add_argument("--user", action="store_true", help="the owner's own words said so")
    item.set_defaults(func=cmd_review)
    item = sub.add_parser("sync")
    item.add_argument("--commit", action="store_true")
    item.add_argument("--dry-run", action="store_true")
    item.set_defaults(func=cmd_sync)
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
