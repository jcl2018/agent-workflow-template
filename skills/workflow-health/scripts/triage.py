"""Triage the filed health findings per feature (HLT-8). Used by health.py triage.

list: open health issues per feature milestone, by kind (their health:<group> or health:review-<kind> label), with the
count and the age in days of the oldest and newest. Read-only.
close: --close --kind K --why WORDS [--feature F] [--older DAYS] [--max N] always prints the matched issues first. With
--yes it closes exactly that list, each with the owner's words as its comment and the health:closed label, so file.py
does not refile a finding until its evidence changes. More matches than --max (20) is refused: narrow it or raise --max.
It stops before writing when gh can't list the issues.
"""
import datetime
import os
import subprocess

# No terminal, no waiting: a prompt from git or gh must fail, not block.
os.environ.update(GIT_TERMINAL_PROMPT="0", GH_PROMPT_DISABLED="1", GIT_EDITOR="true", GIT_ASKPASS="true", SSH_ASKPASS="true")

import ghcache

CAP = 20


def age(issue):
    try:
        when = datetime.date.fromisoformat(str(issue.get("created_at"))[:10])
    except ValueError:
        return 0
    return (datetime.date.today() - when).days


def kind_of(issue):
    tags = [t for t in issue.get("labels") or [] if t.startswith("health:") and t != "health:closed"]
    return tags[0][len("health:"):] if tags else "health"


def open_findings(root, only=None):
    found, why = ghcache.issues(root)
    if found is None:
        return None, why
    return [i for i in found if i.get("state") == "open" and ghcache.is_health(i)
            and (not only or (i.get("milestone") or "Backlog") == only)], ""


def listing(root, only=None):
    found, why = open_findings(root, only)
    if found is None:
        print("REFUSED[gh]: can't list the issues (%s). Nothing was read." % why)
        return 2
    if not found:
        print("TRIAGE: no open findings%s" % (" on " + only if only else ""))
        return 0
    table = {}
    for issue in found:
        table.setdefault(issue.get("milestone") or "Backlog", {}).setdefault(kind_of(issue), []).append(age(issue))
    print("TRIAGE: %d open findings on %d features" % (len(found), len(table)))
    for stone in sorted(table, key=lambda s: (-sum(len(v) for v in table[s].values()), s)):
        print("== %s: %d ==" % (stone, sum(len(v) for v in table[stone].values())))
        for kind, ages in sorted(table[stone].items(), key=lambda kv: (-len(kv[1]), kv[0])):
            print("  %-22s %3d open, oldest %d days, newest %d days" % (kind, len(ages), max(ages), min(ages)))
    return 0


def close(root, kind, why, only=None, older=0, yes=False, most=CAP):
    if not (why or "").strip():
        print("REFUSED[why]: close needs --why with the owner's words. Nothing was closed.")
        return 2
    found, reason = open_findings(root, only)
    if found is None:
        print("REFUSED[gh]: can't list the issues (%s). Nothing was closed." % reason)
        return 2
    match = [i for i in found if kind_of(i) == kind and age(i) >= older]
    if not match:
        print("NOTHING TO CLOSE: no open %s findings%s%s" % (kind, " on " + only if only else "", " %d days or older" % older if older else ""))
        return 0
    for issue in match:
        print("  #%d %s (%d days, %s)" % (issue["number"], issue.get("title") or "", age(issue), issue.get("milestone") or "Backlog"))
    if len(match) > most:
        print("REFUSED[cap]: %d match, over --max %d. Narrow it with --feature or --older, or raise --max." % (len(match), most))
        return 2
    if not yes:
        print("DRY RUN: %d would close with: %s. To close them, run again with --yes." % (len(match), why))
        return 0
    subprocess.run(["gh", "label", "create", "health:closed", "--description", "Closed in triage by the owner", "--force"],
                   cwd=root, capture_output=True, text=True)
    for issue in match:
        number = str(issue["number"])
        done = subprocess.run(["gh", "issue", "close", number, "--comment", "Closed in triage by the owner: " + why.strip()],
                              cwd=root, capture_output=True, text=True)
        if not done.returncode:
            done = subprocess.run(["gh", "issue", "edit", number, "--add-label", "health:closed"], cwd=root, capture_output=True, text=True)
        print(("FAILED #%s: %s" % (number, done.stderr.strip()[:120])) if done.returncode else "CLOSED #%s" % number)
    return 0
