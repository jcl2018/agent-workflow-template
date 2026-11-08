# Plan: regression-format

Goal: `.loop/goals/regression-format.md` (done lines are frozen and belong to delivery; not restated or reopened here).
Reviewed by /autoplan (unattended, CEO + Eng; no UI or developer-tool scope). Every question took the recommended answer.

## Findings from reading the repo

- **Failing test, root cause found.** `wiki-release` runs `docs.py publish`, which clones the wiki and runs `git commit` (`skills/workflow-docs/scripts/docs.py:280`) with no author identity. The toy sets identity only in its own repos (`dev/toy/make.sh`), so the clone commits fine on a machine with a global git identity and fails on a GitHub runner. Reproduced locally with `GIT_CONFIG_GLOBAL` pointing at `user.useConfigOnly=true` and `GIT_CONFIG_NOSYSTEM=1`: `REFUSED: git commit ... Author identity unknown`. The issue body is empty because the row's command ends in `grep -q`, which hides the output.
- **Issue 58** ("Regression: wiki-release", OPEN) is closed by the workflow's own pass path (`gh issue close ... "Passing again."`), so no code is needed beyond making the row pass in CI.
- **Size limit.** `regression.py` is 19,866 bytes against the 20 KB cap (20,480) that `test-wiki.sh` and the health check enforce. Adding the schedule setting and the description column will cross it, so the Actions runner text moves out of the script first.
- **Table owner.** The Tests tables are rendered by `skills/workflow-docs/scripts/criteria.py` (`table()`, `tsv()`), not by `regression.py`. `tsv()` pads rows to 5 cells, and `regression.py` indexes `seen_red` as cell 5.
- `regression-known.tsv` does not exist, so nothing masks the failure.

## Steps

1. **Fix the CI failure (done line 3).** In `docs.py` pass an identity to the wiki commit: `git -c user.name=... -c user.email=... commit`. Use the existing git identity when one is set and fall back to a fixed bot identity. This fixes the cause for every caller rather than guarding the test. Also add `; echo` or `tee` so the row's failing output is kept: change the `wiki-release` command so the CI issue shows the test output (for example by capturing to a variable and printing before `grep -q`). Keep the `seen_red` date valid because the command text changes: re-prove with `regression.py red`.
2. **Schedule setting (done line 2).**
   - Add `regression_schedule` to `.loop/config.json`, a five-field cron string, default `17 9 * * *`.
   - Move the workflow text from the `WORKFLOW` constant in `regression.py` to a template file next to it, `skills/workflow-regression/scripts/workflow.yml`, with a `{{cron}}` placeholder. `cmd_workflow` reads it, validates the setting (five fields, else `REFUSED` with a fix), and writes `.github/workflows/regression.yml`.
   - Rewrite `.github/workflows/regression.yml` with `regression.py workflow` so the file matches the setting. The file lives under `.github/`, a risky path in `config.json`, so the diff goes to the owner's PR review as usual.
   - Document the setting in `SKILL.md` and `references/commands.md`.
3. **Description column (done line 1).**
   - Add `description` as a sixth tab column in `.loop/regression.tsv`, after `seen_red`, so existing indices hold. Update `HEADER`, `read_rows`, `write_rows`, `cmd_add` (`--describe "<one line>"`, kept when a row is re-added without it) and `cmd_seed`. Update `tsv()` padding in `criteria.py` to 6.
   - `run` refuses nothing new, but `sync` lists any row with an empty description as a `GAP`, and `criteria` counts it, so a row cannot be added without one going unnoticed.
   - Backfill a plain one-line description on all 74 current rows, written from each row's command and toy test (what it checks, not how). Rows with a `-` goal keep one too.
4. **Tests tables in the fixed REG-2 format (done line 1).** Change `table()` in `criteria.py` to emit: Criterion (id plus the criterion's own words), Test, What it checks, Runs (`land` is push and nightly, shown as `both`; `nightly` is `nightly`), Last result and date, Seen failing (the `seen_red` date, or `no`). A criterion with no passing test keeps the `**not enforced**` line. Re-render every wiki page with `criteria.py render` so `tests-table-stale` stays green.
5. **Toy tests (done line 4).**
   - `dev/toy/test-docs.sh`: a wiki publish succeeds with no global git identity (the CI failure, written as a test that fails before step 1 and passes after).
   - `dev/toy/test-regression.sh`: `workflow` writes the cron from the setting, and changing the setting then rewriting changes the file; a bad cron is refused; `add --describe` stores the text and `sync` reports a row without one.
   - `dev/toy/test-criteria.sh`: the rendered table has the new columns, including the criterion words, description, runs, last result and seen failing.
   - Register each as a row in `.loop/regression.tsv` with a description and the right criterion (REG-2, REG-4, DOC-4), and prove each with `regression.py red`. Keep every script under 20 KB.
6. **Docs.** Update `docs/wiki/Regression.md` (re-rendered table), `skills/workflow-regression/SKILL.md` and `references/commands.md`. Run the repo checks and `regression.py run land`.

## Failure modes

| Step | Failure | Handling |
|---|---|---|
| 1 | Identity fallback overrides a real identity | Only apply it when `git config user.email` is empty |
| 2 | A cron string GitHub rejects | Validate five fields in `cmd_workflow` and refuse before writing |
| 2 | Hand-edited workflow file | Existing guard stays: refuse to replace a file the tool did not write |
| 3 | Row text containing a tab | Existing `clean()` guard covers the new column |
| 4 | Old pages with a 3-column table | `render` rewrites them; `tests-table-stale` fails until it does |

## Not in scope

- REG-4's "on every push": the workflow runs on `v*` tags, the schedule and by hand, not on every push. The goal's done lines cover the schedule only, so this stays a separate goal.
- REG-3, which the table shows as not enforced.
- Any change to the regression runner's issue handling (REG-5).

## What already exists

`regression.py red` (proves a row fails), `workflow` (writes the file), `criteria.py render` (tables), `fakegh`, and the `dev/toy` harness. Nothing new is built beside them.

## Decision audit

| # | Decision | Class | Principle |
|---|---|---|---|
| 1 | Fix the identity in `docs.py`, not in the toy | Mechanical | P4, root cause |
| 2 | Move the workflow text to a template file | Mechanical | P5, forced by the 20 KB cap |
| 3 | Sixth column after `seen_red` | Mechanical | P3, keeps every index |
| 4 | Setting is a raw cron string, `regression_schedule` | Taste | P5, one plain value; friendly words like `hourly` can map later |
| 5 | `land` shows as `both` in Runs | Taste | P5, matches REG-2's own wording |
| 6 | Leave "on every push" to a later goal | Taste | P2, outside the blast radius named in Touches |

## Review record

<!-- autoplan-accepted:ceo -->
- None: a repair and a format change inside the named Touches; scope is right-sized and no premise was challenged.
<!-- /autoplan-accepted:ceo -->

<!-- autoplan-accepted:eng -->
- The workflow runner text moves to a template file before any `regression.py` growth, and every script stays under 20 KB, verified by the toy size test.
- The wiki publish works with no global git identity, verified by a toy test that fails before the fix.
<!-- /autoplan-accepted:eng -->

Outside voice: not run (unattended session, no recorded consent).
