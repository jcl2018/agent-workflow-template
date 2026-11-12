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

The time budget of an in-loop test run lives here too (budget, fit, execute): a run with --reuse (the loop's qa, ship
and pull-request lanes) never goes past test_budget_minutes in .loop/config.json (default 15, floor 15). Rows run in
tier order (the rows a change affects first) while their estimated seconds fit, a row still running at the budget is
stopped, and every row not run is left to the scheduled full suite and listed. A left row is recorded as LEFT, so a
later lane on the same content doesn't rerun it.
The row and page readers of regression.py (chosen, clean, criteria_ids and others) sit at the end, moved here unchanged.
"""
import datetime
import glob
import json
import os
import re
import subprocess
import sys
import tempfile
import time

import actions
import lanes

# No terminal, no waiting: a prompt from gh must fail, not block.
os.environ.update(GIT_TERMINAL_PROMPT="0", GH_PROMPT_DISABLED="1", GIT_EDITOR="true", GIT_ASKPASS="true", SSH_ASKPASS="true")
if not sys.stdin or not sys.stdin.isatty():
    os.dup2(os.open(os.devnull, os.O_RDONLY), 0)

NAME = "regression-runs.tsv"
HEADER = "# id\tstatus\tdate\trun\tflaky\n"
SKIP_CODE = 77  # a row exits 77 when it cannot run on this machine (no Codex): SKIPPED, never PASS, never FAIL
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
        if item["state"] == "SKIPPED" and (ran.get(item["id"]) or [""] * 5)[1] == "PASS":
            continue  # a skip here says nothing against the last pass
        flag = item["flaky"] if "flaky" in item else ran.get(item["id"], [""] * 5)[4]
        ran[item["id"]] = [item["id"], item["state"] if item["state"] in ("PASS", "SKIPPED") else "FAIL", date, run, flag[:12]]
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


FLOOR, DEFAULT = 15, 15


def minutes(cfg, key, default=DEFAULT):
    """The setting in minutes; exits with a fix line when it is not a whole number of at least 15."""
    value = cfg.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int) or value < FLOOR:
        sys.exit("REFUSED: %s is %r in .loop/config.json, under the %d-minute floor. Fix: set it to %d or more." % (
            key, value, FLOOR, FLOOR))
    return value


def budget(root):
    """Seconds the loop's test run may take."""
    try:
        with open(os.path.join(root, ".loop", "config.json")) as handle:
            cfg = json.load(handle)
    except (OSError, ValueError):
        cfg = {}
    return minutes(cfg if isinstance(cfg, dict) else {}, "test_budget_minutes") * 60


def fit(todo, est, limit):
    """(rows that fit, rows left): todo in tier order, each kept while the estimated total stays within limit."""
    keep, left, used = [], [], 0.0
    for key in todo:
        if used + est.get(key, 0) <= limit:
            keep.append(key)
            used += est.get(key, 0)
        else:
            left.append(key)
    return keep, left


def execute(root, picked, todo, est, limit, timeout, expected, reuse):
    """Run the rows of todo within limit seconds (None: no limit). Returns (results, left ids)."""
    keep, left = fit(todo, est, limit) if limit else (todo, [])
    by, results, start = {row["id"]: row for row in picked}, [], time.time()
    for key in keep:
        remaining = limit - (time.time() - start) if limit else None
        if remaining is not None and remaining < 1:
            left.append(key)
            continue
        cap = timeout if remaining is None else min(timeout, remaining)
        began = time.time()
        skip = os.path.join(tempfile.gettempdir(), "loop-skip-%d-%s" % (os.getpid(), key))  # a test that cannot run here writes it
        code, text, pid, signal = lanes.run_row(by[key]["command"], root, dict(actions.row_env(), TOY_SKIP_FILE=skip), cap)
        if code and os.path.exists(skip):  # a pipe in the row hides the test's own exit 77
            os.remove(skip)
            code = SKIP_CODE
        if code == 124 and cap < timeout:  # stopped by the budget, not by its own limit: it didn't fail, it wasn't finished
            left.append(key)
            continue
        state = "PASS" if code == 0 else "SKIPPED" if code == SKIP_CODE else ("KNOWN" if key in expected else "FAIL")
        if code == 0 and key in expected:
            print("FIXED %s: remove it from the known list" % key)
        print("%s %s%s" % (state, key, " (%s)" % expected[key] if state == "KNOWN" else ""), flush=True)
        if signal and state != "PASS":  # workflow-regression/references/commands.md
            print("KILLED %s: signal %s (pid %d). Note: a signal stopped this row; see the lane log" % (key, signal, pid))
        if state == "FAIL" and reuse:
            print("\n".join("    " + line for line in text.rstrip().splitlines()[-20:]), file=sys.stderr)
        results.append({"id": key, "state": state, "tail": text[-1500:], "seconds": round(time.time() - began, 1),
                        "pid": pid, "rc": code, "signal": signal})
    if left:
        print("BUDGET %d min: ran %d of %d rows; LEFT %d to the scheduled full suite: %s" % (
            (limit or 0) // 60, len(results), len(results) + len(left), len(left), ", ".join(left[:20]) + (
                ", +%d more" % (len(left) - 20) if len(left) > 20 else "")))
    return results, left


# regression.py's row and page readers, moved here unchanged (size); regression.py imports them back.
def today():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")


def path_of(root, name):
    return os.path.join(root, ".loop", name)


def clean(text):
    if "\t" in text or "\n" in text:
        sys.exit("REFUSED: a row can't hold a tab or new line. Fix: use a script.")
    return text


def done_lines(path):
    with open(path) as handle:
        part = handle.read().split("## Done lines", 1)[-1].split("\n## ", 1)[0]
    return re.findall(r"^(\d+)\.\s+(.+)$", part, re.M)


def criteria_ids(root):
    """Requirement ids written under ## Requirements (or the old ## Criteria) in the wiki pages, outside code fences."""
    try:
        with open(path_of(root, "config.json")) as handle:
            folder = json.load(handle).get("wiki_dir") or "docs/wiki"
    except (OSError, ValueError):
        folder = "docs/wiki"
    ids = []
    for name in sorted(glob.glob(os.path.join(root, folder, "*.md"))):
        with open(name) as handle:
            text = re.sub(r"(?ms)^```.*?^```[^\n]*$", "", handle.read())
        if re.search(r"\n## (?:Requirements|Criteria)[ \t]*\n", text):
            part = re.split(r"\n## (?:Requirements|Criteria)[ \t]*\n", text, maxsplit=1)[1].split("\n## ", 1)[0]
            ids += re.findall(r"^- ([A-Z]{2,5}-\d+): \S", part, re.M)
    return ids


def criterion_rows(rows, key):
    return [row for row in rows.values() if key in (row["id"], row["goal"]) and row["category"] != "defect"]


def chosen(rows, target):
    if target in rows:
        return [rows[target]]
    if target == "land":
        return [row for row in rows.values() if row["level"] == "land"]
    if target == "nightly":
        return [row for row in rows.values() if row["level"] in ("land", "nightly")]
    sys.exit("REFUSED: no row or level called %s." % target)


def lines_of(root, name):
    return {line.split("\t")[0]: line.rstrip("\n") for line in open(path_of(root, name)) if line.strip() and line[0] != "#"} \
        if os.path.exists(path_of(root, name)) else {}


# regression.py red --off-platform (REG-10): a red result proven on another runner, with the runner and commit named.
OFF_WINDOWS = re.compile(r"\b(win(dows)?(32|64)?|msys\d*|mingw\d*|cygwin)\b|\b(msys|mingw)\w*", re.I)  # a Windows machine can only skip a bash row
OFF_SHA = re.compile(r"^[0-9a-f]{7,40}$")


def off_record(root, row_id, runner, commit, today, read_rows, edit_rows):
    if row_id not in read_rows(root):
        sys.exit("REFUSED: no row %s. Fix: add it first." % row_id)
    runner = (runner or "").strip()
    if not runner or "\t" in runner or "\n" in runner:
        sys.exit("REFUSED: --runner names the machine that saw the row fail (linux-ci, a Linux session). Fix: pass --runner NAME.")
    if OFF_WINDOWS.search(runner):
        sys.exit("REFUSED: runner %s is Windows, where these rows only skip (exit 77) and a skip never sets seen red. "
                 "Fix: prove it red on a Linux or Mac runner." % runner)
    if not OFF_SHA.match(commit or "") or subprocess.run(["git", "cat-file", "-e", commit + "^{commit}"], cwd=root,
                                                     capture_output=True).returncode:
        sys.exit("REFUSED: %s is not a commit in this repo. Fix: git fetch, and pass the commit the red run used." % commit)
    day = today()
    edit_rows(root, lambda current: current[row_id].update(seen_red=day))
    path = os.path.join(root, ".loop", "regression-red.tsv")
    kept = [line for line in (open(path).read().splitlines() if os.path.exists(path) else []) if line and line.split("\t")[0] != row_id]
    with open(path, "w", newline="\n") as out:
        out.write("\n".join(kept + ["\t".join((row_id, day, runner, commit))]) + "\n")
    print("SEEN RED %s on %s (proved on %s at %s)" % (row_id, day, runner, commit))
    return 0
