#!/usr/bin/env python3
"""The reply hook's whole-picture check (MON-14): a check-in's Dependencies section draws every live and queued goal of
the pod, so each goal checkin.expected() lists must be named in it. The expected set comes from the run records and
queue files, not from the reply, so the check is the same every time.

usage: reply_deps.py [--cwd DIR] < reply     prints one line per missing goal, `repo/slug`; nothing when the reply is whole"""
import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

HEAD = re.compile(r"^[\s>#*_`-]*([A-Za-z ]+?)[\s:*_`]*(?:\(\d+\))?\s*$")
NEXT = ("needs you", "coming up")


def body(text):
    """The text of the Dependencies section, fences included, or None when the reply has none."""
    lines, start = str(text or "").splitlines(), None
    for i, line in enumerate(lines):
        name = (HEAD.match(line) or [None, ""])[1].strip().lower()
        if start is None and name == "dependencies":
            start = i + 1
        elif start is not None and name in NEXT:
            return "\n".join(lines[start:i])
    return None if start is None else "\n".join(lines[start:])


def blocks(section):
    """{repo name: its text} for each `== name ==` block; the whole section under '' when it has none."""
    found, name = {"": []}, ""
    for line in section.splitlines():
        head = re.match(r"^\s*==\s*(.+?)\s*==\s*$", line)
        name = head.group(1) if head else name
        found.setdefault(name, []).append("" if head else line)
    return {key: re.sub(r"-\s*\n\s*", "-", "\n".join(rows)) for key, rows in found.items()}  # a long name wraps at a hyphen


def missing(text, cwd=None):
    """['repo/slug', ...] of the goals the Dependencies section leaves out; [] when whole or when it cannot be told."""
    section = body(text)
    if section is None:
        return []  # the missing section is reported by the layout check
    import checkin
    parts = blocks(section)
    found = []
    for repo, slug in checkin.expected(cwd or None):
        where = parts.get(repo if len(repo) <= 54 else repo[:51] + "...", parts.get("") if len(parts) == 1 else "")
        if not re.search(r"(?<![\w-])%s(?![\w-])" % re.escape(slug), where or ""):
            found.append("%s/%s" % (repo, slug))
    return found


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--cwd", default=None)
    for line in missing(sys.stdin.read(), parser.parse_args().cwd):
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
