"""regression.py red --off-platform: record a red result proven on another runner (REG-10).

A row the local platform can't run exits 77 and is skipped: a skip never sets seen_red. The red proof runs on a capable
runner (Linux CI or a Linux session); this records its result on the row, naming the runner and the commit, in
.loop/regression-red.tsv (id, date, runner, commit). seen_red stays a plain date.
"""
import os
import re
import subprocess
import sys

WINDOWS = re.compile(r"\b(win(dows)?(32|64)?|msys\d*|mingw\d*|cygwin)\b|\b(msys|mingw)\w*", re.I)  # a Windows machine can only skip a bash row
SHA = re.compile(r"^[0-9a-f]{7,40}$")


def record(root, row_id, runner, commit, today, read_rows, edit_rows):
    if row_id not in read_rows(root):
        sys.exit("REFUSED: no row %s. Fix: add it first." % row_id)
    runner = (runner or "").strip()
    if not runner or "\t" in runner or "\n" in runner:
        sys.exit("REFUSED: --runner names the machine that saw the row fail (linux-ci, a Linux session). Fix: pass --runner NAME.")
    if WINDOWS.search(runner):
        sys.exit("REFUSED: runner %s is Windows, where these rows only skip (exit 77) and a skip never sets seen red. "
                 "Fix: prove it red on a Linux or Mac runner." % runner)
    if not SHA.match(commit or "") or subprocess.run(["git", "cat-file", "-e", commit + "^{commit}"], cwd=root,
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
