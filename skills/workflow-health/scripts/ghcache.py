"""The repo's GitHub issues, read once per run for the rules, review, file and triage. Read-only.

issues(root) -> (list, why): every issue (open and closed), fetched with `gh api --paginate --slurp`, so no page cap.
None and a reason when gh is missing, signed out or fails: the rules then say "gh not available here" (INFO), and a
writer (file, triage) stops before writing anything (it must never act on a partial list).
LOOP_HEALTH_GH_FIXTURE names a JSON file of issues to use instead (the negative controls and toy tests).
"""
import json
import os
import subprocess

# No terminal, no waiting: a prompt from git or gh must fail, not block.
os.environ.update(GIT_TERMINAL_PROMPT="0", GH_PROMPT_DISABLED="1", GIT_EDITOR="true", GIT_ASKPASS="true", SSH_ASKPASS="true")

CACHE = {}
FIELDS = ("number", "title", "body", "state", "labels", "milestone", "created_at", "closed_at", "pull_request")


def slim(item):
    out = {key: item.get(key) for key in FIELDS}
    out["labels"] = [label.get("name") if isinstance(label, dict) else str(label) for label in item.get("labels") or []]
    stone = item.get("milestone")
    out["milestone"] = stone.get("title") if isinstance(stone, dict) else stone
    return out


def issues(root):
    """(issues or None, why). Pull requests are left out."""
    if root in CACHE:
        return CACHE[root]
    fixture = os.environ.get("LOOP_HEALTH_GH_FIXTURE")
    if fixture:
        try:
            with open(fixture) as handle:
                found = [slim(item) for item in json.load(handle)]
            CACHE[root] = ([i for i in found if not i.get("pull_request")], "")
        except (OSError, ValueError, AttributeError) as error:
            CACHE[root] = (None, "the issue fixture can't be read: %s" % error)
        return CACHE[root]
    try:
        done = subprocess.run(["gh", "api", "--paginate", "--slurp", "repos/{owner}/{repo}/issues?state=all&per_page=100"],
                              cwd=root, capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError) as error:
        CACHE[root] = (None, "gh not available here (%s)" % str(error)[:80])
        return CACHE[root]
    if done.returncode:
        CACHE[root] = (None, "gh not available here (%s)" % ((done.stderr.strip().splitlines() or ["exit %d" % done.returncode])[0][:100]))
        return CACHE[root]
    try:
        pages = json.loads(done.stdout or "[]")
        found = [slim(item) for page in pages for item in (page if isinstance(page, list) else [page])]
    except (ValueError, AttributeError) as error:
        CACHE[root] = (None, "gh gave unreadable output (%s)" % str(error)[:80])
        return CACHE[root]
    CACHE[root] = ([i for i in found if not i.get("pull_request")], "")
    return CACHE[root]


def is_health(issue):
    return "health" in (issue.get("labels") or [])
