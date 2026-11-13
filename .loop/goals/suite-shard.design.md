# suite-shard: design

## Problem
The scheduled regression run skips about 500 of ~730 land and nightly rows per run (run 43381770191: 209 PASS, 13 FAIL, 8 KNOWN, 501 SKIPPED), so REG-4's "the full suite runs on the schedule" is not true. Two shards already exist (#3792 and REG-7). The cause is not only too few shards: each row is skipped when `elapsed + ROW_SECONDS (900 s) > JOB_SECONDS (1680 s)`, so every row after minute 13 is skipped even though a row takes about 7 s. Shard 1 ended at 14 minutes with half its rows unrun.

## Approaches
1. Only raise SHARDS to 4. Cheap, but the 15-minute reserve still skips every row after minute 13, whatever the shard count. Rejected: it hides the bug.
2. Give each row the time that is left, not a fixed reserve, and raise SHARDS to 4. A row runs while at least 30 s remain, with its timeout set to min(ROW_SECONDS, time left), so a hang cannot cost the job its summary. Rows are about 90 minutes of work in all, so 4 shards come to about 23 minutes each, inside the 28-minute job budget. Risk: rows are dealt round-robin by position, so a cluster of slow rows can unbalance a shard. The real run measures it.
3. A dynamic queue across jobs. Balanced, but needs shared state between jobs. Not worth it.

## Chosen: approach 2, plus one combined summary
- `SHARDS = 4`; the matrix and the `REGRESSION_SHARD` split come from it.
- Each shard uploads its results file (`results-<n>`, always). A new `summary` job (`needs: regression`, `if: always()`) downloads them, merges them, and writes ONE summary (tests.py summary) with the totals, plus a line `UNRUN n` counting rows that were skipped for time. The per-job summary step goes.
- A row skipped for time is also recorded as a `# unrun <id>` line in the results file, so the combined summary can tell it from a row that cannot run here (exit 77).
- One issue per failing row across shards: already true, since each row belongs to exactly one shard; the issue lookup is by row id. A toy test covers it.

## Each done line
- "A scheduled run's summary shows every land and nightly row ran, with no 'out of job time' skip": the combined summary prints `UNRUN 0` and every row's state; proven by one real `gh workflow run regression.yml` on the branch, counts posted in the PR.

## Open questions
- Whether 4 shards balance. If one shard still runs out of time in the real run, raise SHARDS to 5 and say so.
