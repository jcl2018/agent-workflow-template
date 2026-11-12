# red-off-platform-prd plan

Checked against the code: `cmd_red` and `SEEN` exist in skills/workflow-regression/scripts/regression.py (exit 77 refused at the break run; `edit_rows` is the only writer of seen_red); `runs.SKIP_CODE` = 77; dev/toy/skip-windows.sh and the '# windows: ok' marker skip bash toys on Windows; fit.py and health read seen_red only as a date, so it stays a date.

Build steps
1. skills/workflow-regression/scripts/offred.py (new, small): `record(root, id, runner, commit, edit_rows, read_rows)` refuses (exit 1) `REFUSED: no row <id>`, `REFUSED: runner <r> is Windows ...` (Windows can only skip), `REFUSED: <sha> is not a commit here. Fix: fetch it`; otherwise sets seen_red to today and appends id, date, runner, commit to .loop/regression-red.tsv; prints `SEEN RED <id> on <date> (proved on <runner> at <commit>)`.
2. regression.py: `red ID --off-platform --runner R --commit SHA` (--break no longer required then; plain red still requires it and still refuses exit 77). Update the header usage.
3. docs/wiki/Regression.md: REG-10 Unreviewed "Red proof for rows a platform can't run", usage line for the flag, a criterion-row link (goal REG-10).
4. dev/toy/test-regression.sh: section proving (a) a row exiting 77 under red leaves seen_red empty, (b) off-platform with a Windows runner refused and row stays unproven, (c) with runner linux and the HEAD commit, seen_red is a date and regression-red.tsv names both. Rows in .loop/regression.tsv (REG-10, land). Toy runs on Linux/Mac only, so seen-red for the new rows is owed off-platform: the PR lists the exact red commands.
5. Run docs check (DOCS OK), python syntax check, the offred logic on a throwaway repo here by hand.

Could break: regression.py size cap (20,480 bytes; code goes in offred.py); the docs check's rule that every requirement has a row or says it is not enforced.
Out of scope: auto-running red on Linux CI, changing `run`.
No PENDING decisions.
DEPTH: full
