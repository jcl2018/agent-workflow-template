#!/usr/bin/env python3
"""Issues lines a phone can read (issue 97). A stopped or failed goal is shown by its cause in plain words, never by
the agent's raw output, and goals stopped by one cause share one line: "usage limit: 4 goals paused until Nov 11
16:00; they resume by themselves". While every live goal is paused by one cause, the finish says "paused until ...".
Pure functions; imported by live_board.py, not run.

  cause(run)          (key, words, until): the plain cause of a failed or stopped goal
  stuck(runs)         the Issues lines for failed and stopped goals, grouped by cause, each with its fix
  paused(runs)        "paused until <when>" when all live goals wait out one usage limit, else ""
"""
import re

LIMIT = re.compile(r"usage limit|rate limit|limit reached|hit your (?:weekly |daily )?limit|out of (?:usage|credits)|quota", re.I)
RESET = re.compile(r"(?:resets?|reset at|until|try again (?:at|after))\s+(?:at\s+)?([A-Z][a-z]{2,8}\.? \d{1,2},? \d{1,2}(?::\d\d)?\s*(?:[ap]m)?|\d{1,2}(?::\d\d)?\s*[ap]m|\d\d:\d\d(?: UTC)?)", re.I)
CAUSES = [
    ("limit", LIMIT, "usage limit"),
    ("permission", re.compile(r"permission|not allowed|denied|unauthori[sz]ed|forbidden", re.I), "a permission was refused"),
    ("tests", re.compile(r"\btests? (?:failed|red)|lane (?:failed|red)|\bFAIL\b|regression", re.I), "its tests failed"),
    ("tries", re.compile(r"3 failed tries|tries used up|stopped after", re.I), "it used up its tries"),
    ("crash", re.compile(r"ended without finishing|traceback|crash|killed|exit code|no STEP", re.I), "its worker ended early"),
]
LIVE = ("running", "waiting", "failed", "stopped")


def text_of(run):
    return " ".join(str(x) for x in ((run.get("report") or {}).get("text"), run.get("finding")) if x)


def cause(run):
    said = text_of(run)
    for key, pattern, words in CAUSES:
        if pattern.search(said):
            found = RESET.search(said) if key == "limit" else None
            return key, words, found.group(1).strip() if found else ""
    return "other", "it %s; see its log" % (run.get("status") or "stopped"), ""


def stuck(runs):
    """Grouped lines: one per cause shared by two or more goals, one per goal otherwise. Each line pair stays short;
    live_board.fit wraps anything over 60 columns at word boundaries."""
    groups = {}
    for run in runs:
        if run.get("status") in ("failed", "stopped"):
            groups.setdefault(cause(run)[0], []).append(run)
    out = []
    for key, members in groups.items():
        _, words, until = cause(members[0])
        slugs = [run["slug"] for run in members]
        if key == "limit":
            when = " until " + until if until else " until the limit resets"
            out.append("- usage limit: %d goal%s paused%s" % (len(slugs), "" if len(slugs) == 1 else "s", when))
            out.append("    %s" % ", ".join(slugs))
            out.append("    fix: none needed; they resume by themselves" if len(slugs) > 1 else
                       '    fix: none needed, or type "resume %s" after it resets' % slugs[0])
        elif len(slugs) > 1:
            out.append("- %d goals stopped: %s" % (len(slugs), words))
            out.append("    %s" % ", ".join(slugs))
            out.append('    fix: look at one, then type "resume <goal>" for each')
        else:
            out.append("- %s is %s: %s" % (slugs[0], members[0].get("status"), words))
            out.append('    fix: look at the problem, then type "resume %s"' % slugs[0])
    return out


def paused(runs):
    live = [run for run in runs if run.get("status") in LIVE]
    if not live or any(run.get("status") not in ("failed", "stopped") or cause(run)[0] != "limit" for run in live):
        return ""
    until = next((cause(run)[2] for run in live if cause(run)[2]), "")
    return "paused until " + (until or "the usage limit resets")
