# automation-budgets plan

Claims checked against the code: actions.py:44 (`timeout-minutes: 90`) and :106 (JOB_SECONDS 88 min) in the WORKFLOW template; rows loop at :165-170 filters with `wanted(row)`; digest `open_issues` is skills/workflow-health/scripts/automation.py:92 (`--limit 300`); the Mac tick is workflows.py `tick_repo` (health check, file, judge, regression, digest in one pass, so health already follows a local regression; for Actions it only fetches the suite time); health.yml is gone (rules.py:155 WARNs on one).

## Build steps
1. actions.py: add `REGRESSION_BUDGET_MINUTES = 30` and a shard count; the template gets `timeout-minutes: @BUDGET@`, JOB_SECONDS = (budget - 2) * 60, a `strategy: fail-fast: false, matrix: shard: [...]` and `REGRESSION_SHARD` env; the rows loop keeps row k of the wanted rows when `k % n == i`. Suite-time artifact name gets the shard.
2. regression.yml: regenerate with `regression.py workflow`.
3. automation.py (health): `open_issues` pages with `--limit 1000`; when a label returns that many it returns a truncated flag and the digest prints `TRUNCATED: counts are cut off at 1000 issues` instead of presenting counts as complete. `regression_line` reports a regression run still in progress.
4. workflows.py tick: for a public repo, before the digest, wait up to the cap for the newest regression run to complete (`gh run list`), so health follows regression completion, not the 30-minute clock offset. (health.yml no longer exists, so a literal workflow_run trigger cannot be written; reported as a wording conflict.)
5. Wiki: REG-7 and AUT-7 name the same budget (suite 30 min per job, round 45 = 30 + 15). Both are Unreviewed, so editable; run `docs.py audit` and `entry.py write`.

## Tests (each seen red first, then green)
- `dev/toy/test-automation-budgets.sh`: (a) the budget in actions.py, regression.yml, REG-7 and AUT-7 agree and the YAML has a shard matrix; (b) sharded runs of a toy rows file cover every row exactly once; (c) a fake gh with 301 issues gives TRUNCATED or all issues; (d) the tick waits for a running regression. Rows `budgets-agree` (REG-7, AUT-7) and `digest-not-cut` added to .loop/regression.tsv, with `regression.py red`.

## Risks
Sharded jobs each open issues for their own rows only; summary tables are per shard. A shard count too low still hits the budget and skips rows (they show SKIPPED, no issue).

## Out of scope
Recreating health.yml; new settings; Windows posix fixes (win-posix-calls, win-flock).

PENDING: none
