# Plan: regression-green

Goal: `.loop/goals/regression-green.md` (done lines and Verify by hand belong to delivery; not restated or reopened here).
Design: `.loop/goals/regression-green.design.md`.
Reviewed by /autoplan (unattended, CEO + Eng; no UI or developer-tool scope). Every question took the recommended answer.

## Findings from reading the repo

- **adopt-set-1 to 5: pycache.** `PYTHONDONTWRITEBYTECODE=1` is set in the owner's shell and not on GitHub, so earlier toy tests leave `skills/*/scripts/__pycache__/` and `dev/package.py` refuses the package. Per the design, reproduced with `env -u PYTHONDONTWRITEBYTECODE bash dev/toy/test-adopt.sh SET-4`.
- **wiki-release / wiki-release-pycache: git identity, not pycache.** The design left this unexplained. Reproduced here: with `GIT_CONFIG_GLOBAL` holding only `user.useConfigOnly=true` and `GIT_CONFIG_NOSYSTEM=1`, `bash dev/toy/test-wiki.sh` dies with `fatal: no email was given`. `docs.py publish` commits in the wiki clone with no identity (`grep` finds no `user.email` or `-c user.` in `skills/workflow-docs/scripts/docs.py`). A runner has no global identity; the owner's machine does. The row's command ends in `grep -q`, so the issue body is empty.
- **Both rows are one root cause pair, so step 1 of the design is already answered.** The "find the cause first" step shrinks to confirming it with the CI-like shell below.
- **DEL-4 already has a row, but it is the wrong kind.** `pr-body-no-checks` is `category defect`, and `criteria.py` keeps defect rows out of the Tests table. So `docs/wiki/Delivery.md:41` shows DEL-4 as **not enforced**. DEL-4 needs a `criterion` row; the defect row stays.
- **REG-3 has none.** `docs/wiki/Regression.md:36` shows it **not enforced**. The workflow still embeds its own python loop (`.github/workflows/regression.yml`), while `regression.py run` is the local command, so REG-3 is also false today.
- **Size limit.** `regression.py` is 16,352 bytes and `actions.py` is 4,486 bytes (cap 20,480 each). Moving the issue sync into `actions.py` has room.
- **Generator.** `regression.py workflow` writes the file (`cmd_workflow`); the setting is `regression_cron`.

## Steps

1. **CI-like runner (design step 1, narrowed).** Add `dev/toy/ci-env.sh`: runs a command with `env -u PYTHONDONTWRITEBYTECODE`, `GIT_CONFIG_GLOBAL` pointing at a file with `user.useConfigOnly=true`, `GIT_CONFIG_NOSYSTEM=1`, and a clean copy of HEAD. Used to prove each failure red before the fix and green after.
2. **Fix wiki-release at the root.** In `docs.py`, commit in the wiki clone with `git -c user.name=... -c user.email=...`, applied only when `git config user.email` is empty (a real identity is never overridden). Add a case to `dev/toy/test-docs.sh` or `test-wiki.sh`: publish succeeds with no global identity. Change the two wiki rows so the failing line reaches stdout (print the `FAIL` lines to stdout, not stderr) so the issue body is no longer empty. Re-prove with `regression.py red`.
3. **Fix adopt-set-1 to 5 and the pycache row at the root.** Make the earlier toy tests not leave bytecode in the checkout: run skill scripts under `PYTHONDONTWRITEBYTECODE=1` in the shared toy helper (`dev/toy/make.sh`) and make `mk` in `test-adopt.sh` copy skills without `__pycache__`. `package.py` stays strict.
4. **REG-3: one command everywhere.** Move the issue sync from the workflow's inline python into `actions.py`/`regression.py run` (`run` already has `--live`). The generated workflow then calls `python3 skills/workflow-regression/scripts/regression.py run --live` (and uploads the step summary). Change the generator and `workflow-setup`'s copy together; rewrite `.github/workflows/regression.yml` with `regression.py workflow`. The file is under `.github/`, a risky path, so the diff goes to the owner's review. This takes the design's open question (see PENDING in the gate) toward the stricter reading, since "the same way for me, the loop and GitHub" is REG-3's own text.
5. **Criterion tests, seen failing once (done line 2).**
   - DEL-4: `dev/toy/test-defect.sh` case `pr-body-criterion` asserting the body carries the done lines, the plan, the Verify by hand steps and each step's result. Register as a `criterion` row with goal `DEL-4`. Prove red by breaking the body builder, then green.
   - REG-3: a case in `dev/toy/test-regression.sh` asserting the generated workflow contains `regression.py run` and no inline loop, and that `run` gives the same output in the CI-like env as in a plain one. Register with goal `REG-3`. Prove red against the old workflow file, then green.
   - Both go through `regression.py red`, which records `seen_red`.
6. **Checks.** Repo checks, the full suite locally through `dev/toy/ci-env.sh` and plainly, then `criteria.py render` so DEL-4 and REG-3 show their tests. Issues 58, 68-72 and 74 close from the next GitHub run through the workflow's existing close path; no manual closing.

## Failure modes

| Step | Failure | Handling |
|---|---|---|
| 2 | Fallback identity overrides a real one | Apply only when `git config user.email` is empty |
| 3 | Bytecode still appears from another test | `ci-env.sh` full-suite run finds it; fix there, never relax `BAD_DIRS` |
| 4 | Adopting repos get a changed workflow | SET toy tests cover it; hand-edited workflow guard stays |
| 4 | `run --live` in CI mis-handles issues | Existing `fakegh` toy tests extended to the CI call |
| 5 | A test that never fails | `regression.py red` is required before the row counts |

## Not in scope

- Adding rows to `.loop/regression-known.tsv` or setting `PYTHONDONTWRITEBYTECODE` in the workflow (both hide the fault).
- Loosening `package.py`'s refusal of `__pycache__`.
- Other criteria shown as **not enforced**.

## What already exists

`regression.py red`, `run --live`, `workflow`, `actions.py`, `fakegh`, `criteria.py render`, `dev/toy/test-defect.sh pr-body`. Only `ci-env.sh` is new.

## Decision audit

| # | Decision | Class | Principle |
|---|---|---|---|
| 1 | Fix identity in `docs.py`, not the toy or workflow | Mechanical | P4, root cause |
| 2 | Bytecode fixed in the toy helpers; `package.py` stays strict | Mechanical | P1, P5 |
| 3 | DEL-4 gets a new `criterion` row beside the defect row | Mechanical | P4, reuse the existing test |
| 4 | Workflow calls `regression.py run --live` | Taste | P1, makes REG-3 true; changes adopting repos' workflow |
| 5 | Add `dev/toy/ci-env.sh` | Taste | P1, so the owner's shell never again hides a CI failure |

## Review record

<!-- autoplan-accepted:ceo -->
- None: a repair inside the named Touches; scope is right-sized and no premise was challenged beyond the wiki-release cause, now reproduced.
<!-- /autoplan-accepted:ceo -->
<!-- autoplan-accepted:eng -->
- Each fix has a toy case seen failing under `dev/toy/ci-env.sh` before the fix and passing after; scripts stay under 20 KB.
<!-- /autoplan-accepted:eng -->
