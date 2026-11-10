#!/usr/bin/env python3
"""Propose skill files edited in an adopted repo (LOCAL FIX lines) back to the template, as one GitHub issue.

usage: update.py --propose [--file-issue]   (update.py calls run(); this file has no command of its own)

The preview prints the full title and body; --file-issue files it with gh. The body is the unified diff of each local
fix against the package copy it was made on, and that version. Before printing or filing it refuses when the text holds
the repo's folder name, its origin owner or name, or the user name (as whole words or path parts; a name under 3
characters is skipped and said so), the home folder path, or any private leak_prefixes pattern; a refusal names only
the kind of match. An open issue on the template with the same title (it carries a hash of the diff) is not filed again.
"""
import difflib
import getpass
import hashlib
import json
import os
import re
import subprocess
import sys


# No terminal, no waiting: a prompt from git or gh must fail, not block.
os.environ.update(GIT_TERMINAL_PROMPT="0", GH_PROMPT_DISABLED="1", GIT_EDITOR="true", GIT_ASKPASS="true", SSH_ASKPASS="true")

def base_copy(skills, old, rel):
    """The package copy a local fix was made on: the kept copy, else what the stamp's hash says was installed (unknown)."""
    kept = os.path.join(skills, ".workflow-kept", rel)
    if os.path.isfile(kept) and (old.get("kept") or {}).get(rel):
        return open(kept, encoding="utf-8", errors="replace").read(), (old["kept"][rel].get("base_version") or old.get("version"))
    return None, old.get("version") or "unknown"


def names(repo):
    """(kind, value) pairs the text must not carry."""
    out = [("repo folder name", os.path.basename(os.path.abspath(repo))), ("user name", getpass.getuser())]
    url = subprocess.run(["git", "-C", repo, "remote", "get-url", "origin"], capture_output=True, text=True).stdout.strip()
    found = re.search(r"[:/]([^/:]+)/([^/]+?)(?:\.git)?$", url)
    if found:
        out += [("origin owner", found.group(1)), ("origin name", found.group(2))]
    return out


def leak_patterns():
    try:
        with open(os.path.expanduser(os.environ.get("LOOP_FLOW") or "~/.workflow-loop/flow.json")) as handle:
            return [p for p in json.load(handle).get("leak_prefixes") or [] if isinstance(p, str)]
    except (OSError, ValueError, AttributeError):
        return []


def scrub(text, repo):
    """(kinds matched, skipped notes)."""
    hits, notes = [], []
    for kind, value in names(repo):
        if len(value) < 3:
            notes.append("SCRUB: skipped %s (shorter than 3 characters)" % kind)
        elif re.search(r"(?<![A-Za-z0-9_])%s(?![A-Za-z0-9_])" % re.escape(value), text, re.I):
            hits.append(kind)
    if os.path.expanduser("~") in text:
        hits.append("home folder path")
    for pattern in leak_patterns():
        try:
            if re.search(pattern, text, re.I):
                hits.append("a leak_prefixes pattern")
        except re.error:
            continue
    return sorted(set(hits)), notes


def draft(skills, old, fixes):
    parts = []
    for rel in fixes:
        mine = open(os.path.join(skills, rel), encoding="utf-8", errors="replace").read()
        base, version = base_copy(skills, old, rel)
        diff = "".join(difflib.unified_diff((base or "").splitlines(True), mine.splitlines(True), "a/" + rel, "b/" + rel))
        parts.append("### %s (made on v%s)\n\n```diff\n%s```\n" % (rel, version, diff if base is not None else
                                                                   "(no package copy kept: the whole file)\n" + mine))
    body = "A fix made in an adopted repo, proposed back to the template.\n\n" + "\n".join(parts)
    digest = hashlib.sha256(body.encode()).hexdigest()[:8]
    return "Fix from an adopted repo: %s (%s)" % (", ".join(fixes), digest), body


def save(repo, title, body):
    common = subprocess.run(["git", "-C", repo, "rev-parse", "--git-common-dir"], capture_output=True, text=True).stdout.strip()
    path = os.path.join(repo, common, "loop", "propose-%s.md" % hashlib.sha256(title.encode()).hexdigest()[:8])
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as handle:
        handle.write("%s\n\n%s" % (title, body))
    return os.path.abspath(path)


def gh(*args):
    return subprocess.run(["gh", *args], capture_output=True, text=True, timeout=30)


def run(skills, old, fixes, template, repo, file_issue):
    if not fixes:
        print("NOTHING TO PROPOSE: no skill file differs from the installed package (PROPOSE_NONE)")
        return 0
    title, body = draft(skills, old, fixes)
    hits, notes = scrub(title + "\n" + body, repo or ".")
    for note in notes:
        print(note)
    if hits:
        path = save(repo or ".", title, body)
        print("REFUSED: the proposal holds %s (PROPOSE_SCRUB). Fix: edit %s, then gh issue create --repo %s --title "
              "\"<title>\" --body-file <that file>" % (", ".join(hits), path, template or "OWNER/NAME"), file=sys.stderr)
        return 2
    print("TITLE: " + title)
    print(body)
    if not file_issue:
        print("PREVIEW: nothing filed. Run update --propose --file-issue to file it on %s" % (template or "the template"))
        return 0
    if not template:
        print("REFUSED: no template repo is known (UPDATE_NO_TEMPLATE). Fix: set template_repo, or pass --template", file=sys.stderr)
        return 2
    for _ in range(2):
        try:
            listed = gh("issue", "list", "--repo", template, "--state", "open", "--limit", "200", "--json", "title,url")
            same = [i for i in json.loads(listed.stdout or "[]") if i.get("title") == title] if listed.returncode == 0 else []
            if same:
                print("ALREADY FILED: %s" % same[0].get("url", ""))
                return 1
            path = save(repo or ".", title, body)
            done = gh("issue", "create", "--repo", template, "--title", title, "--body-file", path)
            if done.returncode == 0:
                print("FILED: " + done.stdout.strip())
                return 0
        except (OSError, ValueError, subprocess.TimeoutExpired):
            continue
    path = save(repo or ".", title, body)
    print("REFUSED: gh couldn't file the issue (PROPOSE_GH). Fix: edit %s, then gh issue create --repo %s --title \"%s\" "
          "--body-file %s" % (path, template, title, path), file=sys.stderr)
    return 2


if __name__ == "__main__":
    print(__doc__.strip())
