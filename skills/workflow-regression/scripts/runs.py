"""Read and write .loop/regression-runs.tsv: each row's last run as id, status, date, run, flaky.

run is the GitHub Actions run URL when GITHUB_SERVER_URL, GITHUB_REPOSITORY and GITHUB_RUN_ID are all set, else
empty, so same-day runs on two branches write identical lines and merge cleanly. flaky is empty, or the commit a row's
result flipped on (tiers.py flaky_apply, REG-9); status stays the raw PASS or FAIL. The per-result evidence (commit, clean, host,
python) lives in the branch's lane record in the git common dir, never here: a commit cell would differ on every
branch and turn each same-day merge of this file into a conflict. Files from before the run or flaky column still
read, with those cells empty. A line carries the 5th cell only while it is set, so the upgrade changes no other line
and an unflagged line is the same as before. A row not rerun keeps its cells, and a result with no flaky field (a dirty
tree) keeps the row's flaky cell.

It also holds a local `regression.py run`'s GitHub issues (sync_issues): one issue per failing row, keyed by a marker in
its body. Dry-run (WOULD lines) unless live; live, it creates, labels, reopens, comments on and closes issues with gh.
The GitHub Actions run keeps its own copy of this logic inside regression.yml (actions.py).
"""
import json
import os
import re
import subprocess

# No terminal, no waiting: a prompt from gh must fail, not block.
os.environ.update(GIT_TERMINAL_PROMPT="0", GH_PROMPT_DISABLED="1", GIT_EDITOR="true", GIT_ASKPASS="true", SSH_ASKPASS="true")

NAME = "regression-runs.tsv"
HEADER = "# id\tstatus\tdate\trun\tflaky\n"
LABELS = ("regression", "defect")  # the tool's own label, and the defect label every failing row's issue carries
MARK = "<!-- loop-regression %s -->"


def path(root):
    return os.path.join(root, ".loop", NAME)


def read(root):
    """Return {id: [id, status, date, run, flaky]}; missing cells read as ""."""
    try:
        with open(path(root)) as handle:
            rows = [line.rstrip("\n").split("\t") for line in handle if line.strip() and line[0] != "#"]
    except OSError:
        return {}
    return {cells[0]: (cells + [""] * 5)[:5] for cells in rows}


def where(sha=None):
    """The run cell: the Actions run URL in CI, else empty (sha is unused, kept for callers)."""
    parts = [os.environ.get(key, "") for key in ("GITHUB_SERVER_URL", "GITHUB_REPOSITORY", "GITHUB_RUN_ID")]
    return "%s/%s/actions/runs/%s" % tuple(parts) if all(parts) else ""


def write(root, results, date, sha):
    """Merge results ([{"id", "state", "flaky"?}]) into the file; nothing is written when results is empty."""
    if not results:
        return
    ran, run = read(root), where(sha)
    for item in results:
        flag = item["flaky"] if "flaky" in item else ran.get(item["id"], [""] * 5)[4]
        ran[item["id"]] = [item["id"], "PASS" if item["state"] == "PASS" else "FAIL", date, run, flag[:12]]
    with open(path(root), "w") as handle:
        handle.write(HEADER + "".join("\t".join(ran[key][:4 + bool(ran[key][4])]) + "\n" for key in sorted(ran)))


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
