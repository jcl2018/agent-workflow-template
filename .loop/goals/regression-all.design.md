# Design: regression-all

Status: APPROVED (recommended answers taken; nothing asked, merged or pushed)

## Problem

Done lines (frozen, in regression-all.md) want every criterion enforced by a test seen failing and now passing, every
row run and recorded, the GitHub workflow running all rows green, slow rows moved to `nightly`, and `docs check` and
health green.

## What the repo shows today

- `.loop/regression.tsv` has 135 rows, all at level `land`. No row is `nightly`.
- `.loop/regression-runs.tsv` records 128. Seven rows have no recorded result: `live-board-arrows`, `-cadence`,
  `-flow`, `-header`, `-issues`, `-leftouts`, `-no-oneline`.
- `.github/workflows/regression.yml` already runs every `land` and `nightly` row, writes a job summary, and opens one
  issue per failing row. It runs on a schedule, a `v*` tag and by hand, but not on push.
- The wiki Tests table (`skills/workflow-docs/scripts/criteria.py`) shows level (as "both" / "nightly"), last result
  and date, and a `**not enforced**` marker.
- The current wiki holds no `**not enforced**` cell. The "10 on Documentation, 3 on Regression" in the done line
  comes from an earlier state, or from criteria whose rows are unlinked or not run. I could not reproduce that count
  from the files; delivery must derive the real list first.

## Premises (taken as agreed)

1. The work is mostly run-and-record plus a few missing rows. It needs no new subsystem.
2. A criterion counts as enforced only when a linked row has PASS in the runs file and a `seen_red` date.
3. "Slow" is measured, not guessed: time each row, move the ones over a threshold to `nightly`, never delete.
4. Where a criterion cannot be tested yet (needs a real GitHub, a person), the report says why exactly and the row
   stays `covered`, not dropped.

## Approaches

- A. Minimal: run all rows once, write the 7 missing results, add rows for any gap, flip slow rows to `nightly`.
- B. Ideal: A, plus teach `regression.py run` to time each row and flag slow ones automatically, plus a `sync` gate
  that fails when a row lacks a result.
- C. Lateral: generate rows from the criteria text. Rejected: tests that restate the criterion don't prove anything.

**Recommendation: A, with one small piece of B**: have `run` record elapsed seconds so the nightly move is a measured
call, kept as an optional extra column so nothing existing breaks. Keep `regression.py` under the 20 KB script limit
that health checks.

## Plan

1. Derive the truth: run `docs check`, `regression.py sync`, and the full `regression.py run land`. List criteria
   shown not enforced and rows with no result.
2. For each not-enforced criterion on Documentation and Regression: add a toy test in `dev/toy/`, register it with
   `regression.py add ... --goal <ID>`, break the code once with `regression.py red ID --break "..."` to get `seen_red`,
   then pass. A criterion that really cannot be tested gets a named reason in the report.
3. Run every row, record all in `regression-runs.tsv` (the 7 live-board rows included).
4. Time the rows; move those over the threshold to `nightly`. The workflow already runs both levels.
5. Regenerate the wiki Tests tables so level and last result show for every row.
6. Run `docs check` and health. Update `docs/wiki` and the `workflow-regression` skill text if behaviour changes.

## Risks

- A row that passes only on a Mac fails on `ubuntu-latest` (the regression-ci goal found none, but the new rows are
  new). Run them under `dev/toy/ci-env.sh`.
- The workflow's 40-minute limit and 900 s per-row timeout: moving slow rows to nightly does not reduce the nightly
  total, so check the sum.
- The wiki Tests table can go stale after every run. Regenerate after the last run.
- `regression.py` and `criteria.py` size limits.

## Out of scope

Run-on-push (REG-4 says "every push"; the workflow has no push trigger today). This is a gap against a Reviewed
criterion, but changing the workflow trigger is a decision for the owner (see PENDING).

## Verify by hand

Left to delivery.
