#!/usr/bin/env python3
"""The private-name scan: nothing private ships (DEL-9). Every push or GitHub write in delivery, release and monitoring
runs it first.

usage: private.py check                 say where the list is and how many patterns it holds (never a pattern)
       private.py scan [--base REF]     scan this branch from REF (default origin/<base>) to HEAD

The list lives outside the repo: `$LOOP_PRIVATE_NAMES` (a file path) or `~/.workflow-loop/private-names`, one regular
expression per line, matched without case; a line starting with `#` is a comment. No file: the scan passes and says nothing was checked.
A file holding only comments: off on purpose. A file that can't be read or holds a bad pattern: every scan refuses.

What a scan reads: the branch name, every changed file name, the added lines and the message of every commit from the
base to HEAD (a name added and removed later still counts; a line that only removes one doesn't), and any named texts
(the pull request title and body, release notes, wiki pages). A hit names its place and the list line, never the text
(a place that itself matches, such as a private file name, is masked).
"""
import os
import re
import subprocess
import sys
import time

# No terminal, no waiting: a prompt from git must fail, not block.
os.environ.update(GIT_TERMINAL_PROMPT="0", GH_PROMPT_DISABLED="1", GIT_EDITOR="true", GIT_ASKPASS="true", SSH_ASKPASS="true")

DEFAULT = "~/.workflow-loop/private-names"
LIMIT, WIDTH = 60, 4096  # seconds for a whole scan (git included), characters per matched piece of a line
PRIVATE_NAME, PRIVATE_LIST = "PRIVATE_NAME", "PRIVATE_LIST"


def source():
    """(path to open, the name shown): the shown name is never an expanded home path."""
    given = os.environ.get("LOOP_PRIVATE_NAMES")
    return (given, "$LOOP_PRIVATE_NAMES") if given else (os.path.expanduser(DEFAULT), DEFAULT)


def patterns():
    """(state, [(list line, compiled)], error): state is none, off, on or broken."""
    path, shown = source()
    if not os.path.exists(path):
        return "none", [], ""
    try:
        with open(path, encoding="utf-8") as handle:
            lines = handle.read().splitlines()
    except (OSError, UnicodeDecodeError) as error:
        return "broken", [], "%s can't be read (%s)" % (shown, type(error).__name__)
    found = []
    for number, line in enumerate(lines, 1):
        text = line.strip()
        if not text or text.startswith("#"):
            continue
        try:
            found.append((number, re.compile(text, re.I)))
        except re.error:
            return "broken", [], "%s line %d isn't a valid pattern" % (shown, number)
    return ("on" if found else "off"), found, ""


def git(top, *args, stop=None):
    try:
        done = subprocess.run(["git"] + list(args), cwd=top, capture_output=True, text=True, errors="replace",
                              timeout=max(1, (stop or time.time() + LIMIT) - time.time()))
    except subprocess.TimeoutExpired:
        raise RuntimeError("git %s passed the %d second limit" % (" ".join(args[:2]), LIMIT))
    if done.returncode:
        raise RuntimeError("git %s failed: %s" % (" ".join(args[:2]), done.stderr.strip()[:200]))
    return done.stdout


def places(top, base, stop=None):
    """Yield (place, text) for everything a push from base to HEAD would publish."""
    branch = git(top, "branch", "--show-current", stop=stop).strip()
    if branch:
        yield "branch", branch
    for name in git(top, "diff", "--name-only", "--no-renames", base + "...HEAD", stop=stop).splitlines():
        yield "file name " + name, name
    for sha in git(top, "rev-list", "--reverse", base + "..HEAD", stop=stop).split():
        for line in git(top, "log", "-1", "--format=%B", sha, stop=stop).splitlines():
            yield "commit:%s message" % sha[:7], line
        path, line, header = "", 0, False
        for row in git(top, "show", "--format=", "--no-color", "--no-ext-diff", "-U0", sha, stop=stop).splitlines():
            if row.startswith("diff "):  # a file's header runs from here to its first @@ (a "+++ " row there names it)
                header = True
            elif header and row.startswith("+++ "):
                path = row[6:] if row.startswith("+++ b/") else row[4:]
            elif row.startswith("@@"):
                header, hunk = False, re.search(r"\+(\d+)", row)
                line = int(hunk.group(1)) if hunk else 0
            elif row.startswith("+") and path and not header:
                yield "%s:%d (commit:%s)" % (path, line, sha[:7]), row[1:]
                line += 1


def windows(text):
    """The whole text in overlapping WIDTH-character pieces, so a long line is read to its end."""
    return [text[at:at + WIDTH] for at in range(0, max(len(text), 1), WIDTH - 256)]


def shown_place(place, found):
    """The place as a hit names it: a part that itself matches a pattern (a private file name) is masked."""
    for _, pattern in found:
        place = pattern.sub("<private>", place)
    return place


def scan(top, base, texts=None):
    """{"state": clean|hit|none|off|broken, "hits": [...], "note": str}. base None scans only the texts."""
    state, found, error = patterns()
    shown = source()[1]
    if state == "broken":
        return {"state": "broken", "hits": [], "note": error}
    if state == "none":
        return {"state": "none", "hits": [], "note": "Private-name scan: no list at %s, nothing was checked." % shown}
    if state == "off":
        return {"state": "off", "hits": [], "note": "Private-name scan: off on purpose (%s holds only comments)." % shown}
    hits, stop = [], time.time() + LIMIT
    items = []
    if base:
        try:
            items = list(places(top, base, stop))
        except RuntimeError as failed:
            return {"state": "broken", "hits": [], "note": "the scan couldn't read the branch: %s" % failed}
    for name, text in (texts or {}).items():
        items += [("%s:%d" % (name, number), line) for number, line in enumerate((text or "").splitlines() or [""], 1)]
    for place, text in items:
        if time.time() > stop:
            return {"state": "broken", "hits": hits, "note": "the scan passed its %d second limit" % LIMIT}
        for number, pattern in found:
            if any(pattern.search(piece) for piece in windows(text)):
                hits.append("%s matches list line %d" % (shown_place(place, found), number))
                break
    note = "Private-name scan: %d pattern%s from %s, %s." % (
        len(found), "" if len(found) == 1 else "s", shown, "%d hit%s" % (len(hits), "" if len(hits) == 1 else "s") if hits else "clean")
    return {"state": "hit" if hits else "clean", "hits": hits, "note": note}


def refusal(result, base="the base branch", pushed=False):
    """(why, fix, code) when the result must stop a push, else None."""
    if result["state"] == "broken":
        return ("the private-name list or scan is broken: %s; nothing was pushed" % result["note"],
                "repair the list (private.py check names the line), then run the command again", PRIVATE_LIST)
    if result["state"] != "hit":
        return None
    shown = "; ".join(result["hits"][:8]) + (" and %d more" % (len(result["hits"]) - 8) if len(result["hits"]) > 8 else "")
    if pushed:
        fix = ("the branch is already on origin: the owner decides how to rewrite it (the loop never force-pushes); for a "
               "false positive, edit that line of the list")
    else:
        fix = ("remove the text, then squash so no commit keeps it: git reset --soft $(git merge-base HEAD %s) && git "
               "commit -m \"<goal>\", and run the command again; for a false positive, edit that line of the list" % base)
    return "a private name would be pushed: %s; nothing was pushed" % shown, fix, PRIVATE_NAME


def main():
    args = sys.argv[1:]
    if args[:1] == ["check"]:
        state, found, error = patterns()
        shown = source()[1]
        if state == "broken":
            print("PRIVATE LIST: broken: %s (%s)" % (error, PRIVATE_LIST))
            return 1
        print("PRIVATE LIST: none at %s" % shown if state == "none" else
              "PRIVATE LIST: off on purpose (%s holds only comments)" % shown if state == "off" else
              "PRIVATE LIST: %d pattern%s from %s" % (len(found), "" if len(found) == 1 else "s", shown))
        return 0
    if args[:1] == ["scan"]:
        top = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True).stdout.strip()
        base = args[args.index("--base") + 1] if "--base" in args else "origin/main"
        result = scan(top, base)
        print(result["note"])
        for hit in result["hits"]:
            print("HIT " + hit)
        stop = refusal(result, base)
        if stop:
            print("REFUSED: %s. Fix: %s (%s)" % stop)
            return 2
        return 0
    print(__doc__.strip().splitlines()[2])
    return 0 if args in ([], ["-h"], ["--help"]) else 2


if __name__ == "__main__":
    sys.exit(main())
