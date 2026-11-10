"""DOC-10 for health.py's docs-check rule: every open issue sits on a milestone (its feature's, or Backlog).

rows(root) runs `gh issue list --state open --limit 1000 --json number,title,milestone` and gives one FAIL row per open
issue with no milestone. When gh is missing, fails, or returns exactly LIMIT issues (the list may be cut), it gives one
UNREAD row instead; report.py shows that row but never lets it turn the verdict red (SOFT). A repo with no GitHub remote
has no issues to read, so it gives no row and makes no gh call. Read-only: it never edits an issue.
"""
import json
import os
import subprocess
import sys

os.environ.update(GIT_TERMINAL_PROMPT="0", GH_PROMPT_DISABLED="1", GIT_EDITOR="true", GIT_ASKPASS="true", SSH_ASKPASS="true")
if not sys.stdin or not sys.stdin.isatty():
    os.dup2(os.open(os.devnull, os.O_RDONLY), 0)

LIMIT = 1000
RULE = "milestone"
FIX_UNREAD = "gh auth login, then rerun health.py check"


def row(state, subject, detail, fix):
    return {"state": state, "family": "docs", "subject": subject, "rule": RULE, "detail": detail, "fix": fix}


def on_github(root):
    """True when a remote points at a GitHub host: only then can the repo have issues."""
    try:
        done = subprocess.run(["git", "remote", "-v"], cwd=root, capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return False
    return "github" in done.stdout.lower()


def unread(text):
    first = next((line.strip() for line in (text or "").splitlines() if line.strip()), "no answer")
    return [row("UNREAD", "issues", first[:120], FIX_UNREAD)]


def rows(root, gh="gh"):
    if not on_github(root):
        return []
    args = [gh, "issue", "list", "--state", "open", "--limit", str(LIMIT), "--json", "number,title,milestone"]
    try:
        done = subprocess.run(args, cwd=root, capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.SubprocessError) as error:
        return unread(str(error))
    try:
        issues = json.loads(done.stdout) if not done.returncode else None
    except ValueError:
        issues = None
    if not isinstance(issues, list):
        return unread(done.stderr or done.stdout)
    if len(issues) >= LIMIT:
        return unread("truncated at %d open issues" % LIMIT)
    return [row("FAIL", "#%s" % one.get("number"), (one.get("title") or "")[:120],
                "gh issue edit %s --milestone <Feature|Backlog>" % one.get("number"))
            for one in sorted(issues, key=lambda one: one.get("number") or 0) if not one.get("milestone")]
