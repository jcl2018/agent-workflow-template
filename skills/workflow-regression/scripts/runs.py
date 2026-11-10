"""Read and write .loop/regression-runs.tsv: each row's last run as id, status, date, run.

run is the GitHub Actions run URL when GITHUB_SERVER_URL, GITHUB_REPOSITORY and GITHUB_RUN_ID are all set, else the
full commit sha the run was recorded on. A 3-column file from before the run column still reads, with run empty, and
is rewritten with 4 columns on the next write. A row not rerun keeps its cells.
"""
import os

NAME = "regression-runs.tsv"
HEADER = "# id\tstatus\tdate\trun\n"


def path(root):
    return os.path.join(root, ".loop", NAME)


def read(root):
    """Return {id: [id, status, date, run]}; missing cells read as ""."""
    try:
        with open(path(root)) as handle:
            rows = [line.rstrip("\n").split("\t") for line in handle if line.strip() and line[0] != "#"]
    except OSError:
        return {}
    return {cells[0]: (cells + [""] * 4)[:4] for cells in rows}


def where(sha):
    """The run cell: the Actions run URL in CI, else the commit sha."""
    parts = [os.environ.get(key, "") for key in ("GITHUB_SERVER_URL", "GITHUB_REPOSITORY", "GITHUB_RUN_ID")]
    return "%s/%s/actions/runs/%s" % tuple(parts) if all(parts) else sha


def write(root, results, date, sha):
    """Merge results ([{"id", "state"}]) into the file; nothing is written when results is empty."""
    if not results:
        return
    ran, run = read(root), where(sha)
    for item in results:
        ran[item["id"]] = [item["id"], "PASS" if item["state"] == "PASS" else "FAIL", date, run]
    with open(path(root), "w") as handle:
        handle.write(HEADER + "".join("\t".join(ran[key]) + "\n" for key in sorted(ran)))
