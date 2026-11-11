"""Read and write .loop/regression-runs.tsv: each row's last run as id, status, date, run, flaky.

run is the GitHub Actions run URL when GITHUB_SERVER_URL, GITHUB_REPOSITORY and GITHUB_RUN_ID are all set, else
empty, so same-day runs on two branches write identical lines and merge cleanly. flaky is empty, or the commit a row's
result flipped on (tiers.py flaky_apply, REG-9); status stays the raw PASS or FAIL. The per-result evidence (commit, clean, host,
python) lives in the branch's lane record in the git common dir, never here: a commit cell would differ on every
branch and turn each same-day merge of this file into a conflict. Files from before the run or flaky column still
read, with those cells empty. A line carries the 5th cell only while it is set, so the upgrade changes no other line
and an unflagged line is the same as before. A row not rerun keeps its cells, and a result with no flaky field (a dirty
tree) keeps the row's flaky cell.
"""
import os

NAME = "regression-runs.tsv"
HEADER = "# id\tstatus\tdate\trun\tflaky\n"


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
