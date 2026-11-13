# Plan: machine-local

## Build steps
1. runs.py: `owed_read`, `owed_clear`, `unproven` (PENDING lines), `owed_issue` (to-do on the page's milestone, label other-machine), `owed_record`; `off_record` clears the owed record.
2. regression.py: `red ID --owed --runner R [--live]`; sync and run use `runs.unproven`; a real `--break` red clears the record.
3. health.py: a PENDING line older than 7 days is a WARN (owed-proof), never a FAIL.
4. checkin.py: Coming up lists `off-machine to-do` lines from `.loop/regression-owed.tsv`; operation.md says a goal never waits on another pod or machine.
5. Docs: regression SKILL.md and commands.md; DECISIONS.md holds GRD-11 and the REG, HLT, MON sub-bullets for the owner (Reviewed pages).
6. Test: dev/toy/test-machine-local.py, row machine-local-owed (land), seen red by renaming `unproven`.

## Verified against the code
runs.py off_record, regression.py cmd_red/cmd_sync/cmd_run, health.py criteria_rows, checkin.py Coming up all exist and were edited as above; each script stays under 19,000 bytes, no new file under skills/.

## Could break
fit.py off_rows counts UNPROVEN lines only, so owed rows no longer print one and the lane passes: intended. A dry run opens no issue (needs --live or a token).

## Out of scope
Applying GRD-11 to the Reviewed pages; closing the issue automatically.
