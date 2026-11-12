# Plan: regression-rows-set-grd

Checked against the code: `regression.py add/red/sync` exist (skills/workflow-regression/scripts/regression.py); rows live in
`.loop/regression.tsv`; SET-6/7/9 already have 10 rows seen red 2026-11-12 (lines 584-594), so only GRD-1..10 and the two named
rows are gaps. `token_budget` / `time_budget_minutes` are read only by fit.py (`budget()`, board OVER line); no step-start
refusal exists, and no loop command refuses `--no-verify` / empty hooksPath (private.py only warns in a message; health
`hooks` rule lean.py:297 reads hook state). So those two behaviours are NOT built.

## Build steps
1. Re-run `regression.py sync`: confirm the SET-6/7/9 rows still pass the check and have `seen_red`; fix nothing there.
2. Add one row per built part of GRD-1..10 (`regression.py add grdN-<part> --level land --goal GRD-N --category criterion
   --command 'bash dev/toy/<test>.sh 2>&1 | grep -qF "PASS: <label>"'`), reusing existing proofs:
   - GRD-1: docs check on the Guardrails page (test-docs-command.sh / test-health-prd.sh page checks)
   - GRD-2: del8-floor-step, del8-step-stops (test-budget.sh), prep budget (test-prep-budget.sh), board OVER (test-delivery-board.sh)
   - GRD-3: private-name hooks refuse a private line (test-guard-enforce.sh) and health `hooks` rule (test-health-hygiene.sh)
   - GRD-4: worker role refusals, WORKER_SELF_REPAIR and touches (test-guards.sh), push guard (test-push-guard.sh), govern hook (test-govern.sh)
   - GRD-5: health preview-by-default (test-health-issues.sh), regression issue writes (test-regression.sh)
   - GRD-6: merge guard HEAD_MOVED (test-merge-guard.sh)
   - GRD-7: AUT-7 minutes in digest (test-automation.sh)
   - GRD-8: stalled step / silent worker (test-live-board.sh, test-board.sh), lane minutes (test-lanes.sh)
   - GRD-9: every rule has a negative control (test-health-prd.sh)
   - GRD-10: setup installs hooks and settings (test-adopt.sh / test-guard-enforce.sh)
   Exact PASS labels are read from each script's output while building; a part with no test is not given a row.
3. Add `del8-session-tokens` and `grd3-hook-bypass` as `--level draft` rows (command `false`, description names the unbuilt
   behaviour) so sync shows them and the Tests table reads not enforced; they are reported, not faked.
4. For each new passing row run `regression.py red ID --break "<cmd removing the behaviour on a copy>"`.
5. Run `docs.py render`/`audit` so the Tests tables list the rows; commit. Close #815-#824 via the pull request body.

## Tests per done line
Done line 1: `regression.py sync` lists no GAP for SET-6/7/9 or GRD-1..10; each new row has `seen_red` after `red`; the PR body
lists issues #338 #339 #341 #815-#824. Rows run in qa's lane.

## Could break
Greps on PASS labels drift if a test is reworded (rows then fail loudly). `red` runs the lane, which hangs on Windows until
win-posix-calls (#1396) merges: red runs and qa wait for that.

## Out of scope
Building the unbuilt guardrails (session token stop, time-budget step refusal, hook-bypass refusal, branch protection read,
CI cancel, token multiple flags). Editing frozen done lines.

PENDING: whether the unbuilt guardrails (session token stop, hook-bypass refusal) get their own goals
