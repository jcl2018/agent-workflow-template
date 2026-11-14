# Plan: regression-issues-trust

Checked: actions.py (the `hit` choice and `gh()` in the CI block), runs.py `sync_issues`, regression.py `run` (the `live` line),
the workflow step command line, and the bash toys that cut the CI block out of the workflow all exist as the design says.

1. actions.py: `python3 - --live <<'PY'`; `gh()` prints `WOULD gh ...` and writes nothing unless `--live` is in argv; `hit` is the oldest open issue.
2. runs.py `sync_issues`: sort by number, keep the oldest open issue, close newer open copies as duplicates (live only).
3. regression.py: `live = args.live` (a token no longer turns it on). SKILL.md and the Regression page's Runbook say so.
4. Regenerate `.github/workflows/regression.yml`; bash toys: `--live` on every `ci-block.py` run and in the cut-out regex; the email toy now expects the oldest kept.
5. `dev/toy/test-regression-issues.py` and four rows (REG-5, GRD-5), each seen red.

**What could break.** A caller that relied on a token alone (the Mac tick already passes `--live`). Bash toys that run the block
cannot run on native Windows; the Mac scheduled run proves them.

**Out of scope.** Closing the 1,948 extra issues now (a cleanup dispatch does that); the 20-per-run cap; health's own issue writer (HLT-4).
