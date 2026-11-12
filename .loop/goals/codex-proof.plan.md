# Plan: codex-proof

Goal: `.loop/goals/codex-proof.md`. Design: `.loop/goals/codex-proof.design.md`.

1. `skills/workflow-regression/scripts/runs.py`, `lanes.py`, `actions.py`: exit 77 is SKIPPED (done line 3). Reference: regression `references/commands.md` and the Regression page's Usage.
2. `skills/workflow-setup/scripts/setup.py`: an unwritable home is a NOTE, not a crash (done line 2: anything that breaks is fixed). `SKILL.md` names `~/.workflow-loop` as a Codex writable root.
3. `dev/toy/test-codex.sh` and `dev/toy/fakecodex`: the five parts (done lines 2 and 3, and the collision test the owner asked for).
4. `.loop/regression.tsv`: five rows, each seen failing (done line 3; line 4 links them to SET-3's Tests table).
5. `docs/wiki/Setup.md`: SET-3 word for word, Unreviewed (done line 1); the Tests table scenarios (done line 4).
6. Run: lanes, docs check, package check, the live Codex run; record the results in the goal file.

## Amendments from the /autoplan review (2026-11-11)

The branch holds steps 1 to 6 as first written; the items below are pending on it. The four done lines stay as frozen.

- Item 1 (step 1; also `.github/workflows/regression.yml`): regenerate it with `regression.py workflow`, so the nightly job maps exit 77 to SKIPPED and opens no issue. Verify: `actions.render(...)` equals the file and the diff holds only the two exit-77 lines.
- Item 2 (step 1; also `tiers.py`, `regression.py`): `lanes.plan` and `tiers.plan` never reuse a SKIPPED row (lanes.py:343-373 never reads that status). `RESULT` keeps its fields and appends `, <n> skipped` last. Verify: a record with a SKIPPED row and a PASS row, same unchanged dependency-backed command, plans the SKIPPED row to run and reuses the PASS row, through `lanes.plan` and `--tier`.
- Item 4 (step 3): the `home` part prints SKIPPED, not FAIL, as root (`id -u`; chmod 555 does not bind root); the script exits 77 only when asked for `home` alone. Row `codex-ro-home` stops piping through `grep -qx "ALL PASS"` so its exit status is the row's. Verify: non-root passes and fails with the setup.py guard removed; under a stub `id` printing 0 the row is recorded SKIPPED.
- Item 4b (step 1; `docs/wiki/Regression.md` Usage, `references/commands.md`): say that any row exiting 77, a land row included, is SKIPPED and does not fail a lane; add `SKIPPED <id>` to the Usage list of printed lines.
- Item 5 (step 1; `regression.py`, `tiers.py`): `regression.py red` refuses a break run that exits 77, with exit 1 and the message on stderr; `tiers.compare` does not read PASS then SKIPPED as a flaky flip (probed: it returns the commit, so the row is marked FLAKY and never reused).
- Item 6 and 10 (step 3 and 6): `verify` in `test-codex.sh` asserts setup's exit 1 with its REFUSED line and a `0 failed` RESULT line (the `^RESULT [0-9]* passed` match accepts a run with failed rows); the goal's Codex run report names setup's exit 1.
- Item 7 (`setup.py`, `runs.py`, `goal.py`): the NOTE, the SKIPPED line and `go`'s missing-flow refusal carry a stable UPPER_SNAKE code and a fix on the line.
- Item 8 (`README.md`, `docs/wiki/Setup.md`): a Codex quickstart naming `-s workspace-write`, the writable roots (git folder, remote, `~/.workflow-loop`), the expected first-run exit 1, and the `.git/hooks` risk with `.git/loop` as the narrower root.
- Item 9 (step 3, replaces the old positive control): the codex-skip-77 fixtures read a file under the toy repo, so neither is always-run (lanes.py:232); the same run shows the PASS row REUSED and the SKIPPED row run again.
- Item 11 (step 3): `collide` asserts the final pool's exact slug-to-session mappings, not four ASSIGNED messages.
- Item 12 (step 2; `setup.py`, `settings.py`): setup catches only EACCES, EPERM and EROFS; `settings.write_json` writes a temp file and renames it.
- Item 13 (step 1; `regression.py`): `regression.py criteria` reports a row exiting 77 as skipped, not failing.

Deferred (each repeated at the gate): a Codex-capable runner for the live row, so the SET-3 scenario can show a dated PASS; a default flow that picks its agent from the host (`settings.py` defaults to `claude -p`); regeneration of an adopter's `regression.yml` by the update path; a strict-skip option for CI; an environment fingerprint in the reuse key.

## Build status after the review

Items 1, 2, 4, 4b, 5, 6, 7 (setup's code, not the runner's UPPER_SNAKE for `go`), 8, 9, 10, 11, 12 and 13 are built and committed on the branch; the deferred list stands. Item 7's missing-flow refusal for `go` already says the fix on its line.
