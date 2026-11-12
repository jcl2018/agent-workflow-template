# automation-budgets design

## Problem
Three places state different budgets for the scheduled regression: REG-7 says the full suite finishes in under 30 minutes (health WARNs over 30, SUITE_LIMIT), AUT-7 says a round (regression plus health) finishes in 45, and the generated regression.yml (actions.py:44, :106) allows 90 minutes (job 88). Health starts 30 minutes after regression by clock, not by completion, and the digest (workflow-health/scripts/automation.py:92) lists open issues with `--limit 300`, so past 300 the counts are cut off silently. The queue named stale paths: the digest lives in skills/workflow-health/scripts/automation.py, and health.yml no longer exists (health runs on the Mac; rules.py WARNs on one).

## Approaches
1. Keep one job, only lower the timeout to 30. Cheap, but a suite that grows past 30 minutes just loses rows to JOB_SECONDS with no way to fit.
2. One budget of 30 minutes per regression job, the suite sharded across a matrix of jobs so each fits (shard count from the recorded suite time), with the round budget of 45 = 30 regression + 15 health/digest. Costs more YAML and a merge step for the summary and issues; chosen.

## Chosen
- One constant, `REGRESSION_BUDGET_MINUTES = 30`, in actions.py: timeout-minutes 30, JOB_SECONDS = budget minus 2 minutes. REG-7 names 30 for the scheduled suite (already) and the job; AUT-7 names the round as 30 + 15 = 45. Same number in the text, the workflow and the health rule.
- Sharding: `regression.py run` takes `--shard i/n` (rows split by recorded seconds, deterministic); the workflow runs a matrix of n shards, n derived from the suite time at write time and set in the matrix; issues are opened per row by the shard that ran it.
- Health "after regression": no health.yml exists, so done line 2 as written cannot hold. Equivalent: the Mac tick no longer relies on a fixed offset; it runs health when the newest regression run is completed (gh run list), and the digest reads that run. Reported as a wording conflict.
- Digest: page with `gh api --paginate` (or `gh issue list --limit 1000` with a check); if the list reaches the limit print `TRUNCATED` in the digest instead of presenting counts as complete.

## Done lines
1. Same budget: constant in actions.py, regenerated regression.yml, REG-7/AUT-7 wording (both Unreviewed, editable), suite fits via shards; test asserts the three agree.
2. Digest never silently cut: paging test with >300 issues, TRUNCATED on cap. Health start follows regression completion (conflict noted above).

## Open questions
- Whether to keep a health.yml purely for workflow_run: not chosen, it is deprecated.
