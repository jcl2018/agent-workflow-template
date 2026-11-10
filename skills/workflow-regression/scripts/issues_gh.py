#!/usr/bin/env python3
"""A local `regression.py run`'s GitHub issues: one issue per failing row, keyed by a marker in its body (imported, not run).

Dry-run (WOULD lines) unless live; live, it creates, labels, reopens, comments on and closes issues with gh.
The GitHub Actions run keeps its own copy of this logic inside regression.yml (actions.py).
"""
import json
import re
import os
import subprocess

# No terminal, no waiting: a prompt from gh must fail, not block.
os.environ.update(GIT_TERMINAL_PROMPT="0", GH_PROMPT_DISABLED="1", GIT_EDITOR="true", GIT_ASKPASS="true", SSH_ASKPASS="true")

LABELS = ("regression", "defect")  # the tool's own label, and the defect label every failing row's issue carries
MARK = "<!-- loop-regression %s -->"


def gh(*args):
    return subprocess.run(["gh"] + list(args), capture_output=True, text=True)


def sync_issues(results, live, day):
    """One issue per failing row, keyed by a marker in its body."""
    issues = []
    if live:
        gh("label", "create", "regression", "--force", "--description", "A regression row is failing")
        gh("label", "create", "defect", "--description", "A test that guards it is failing")
        out = gh("issue", "list", "--label", "regression", "--state", "all", "--limit", "200",
                 "--json", "number,state,body,comments,labels")
        if out.returncode:
            print("NOTE: can't read issues, so none changed: " + out.stderr.strip()[:200])
            return
        issues = json.loads(out.stdout or "[]")
    for item in results:
        mark = MARK % item["id"]
        hits = [issue for issue in issues if re.search(r"<!-- loop-regression %s(?: placed=\S*)? -->" % re.escape(item["id"]), issue.get("body", ""))]
        hit = next((issue for issue in hits if issue.get("state") == "OPEN"), hits[0] if hits else None)
        number = str(hit["number"]) if hit else ""
        if item["state"] == "FAIL":
            line = "Failing on %s." % day
            body = "%s\nThe row `%s` fails.\n\n```\n%s\n```\n" % (mark, item["id"], item["tail"])
            if not live:
                print("WOULD open or update the issue for " + item["id"])
            elif not hit:
                gh("issue", "create", "--title", "Regression: " + item["id"], *("--label=" + n for n in LABELS), "--body", body)
                print("OPENED issue for " + item["id"])
            else:
                if "defect" not in [x.get("name") for x in hit.get("labels") or []]:
                    gh("issue", "edit", number, "--add-label", "defect")
                if hit.get("state") != "OPEN":
                    gh("issue", "reopen", number)
                    print("REOPENED issue %s" % number)
                said = [note.get("body", "") for note in hit.get("comments") or []]
                if line not in said:
                    gh("issue", "comment", number, "--body", line)
                    print("UPDATED issue %s" % number)
        elif item["state"] == "PASS" and not live:
            print("WOULD close any open issue for " + item["id"])
        elif item["state"] == "PASS":
            for issue in hits:
                if issue.get("state") == "OPEN":
                    gh("issue", "close", str(issue["number"]), "--comment", "Passing again on %s." % day)
                    print("CLOSED issue %s" % issue["number"])
