<!-- workflow-docs -->
# Monitoring

## Summary

Skill: `workflow-monitoring`. The operation session never does work: `operate.py run` is its one command; it plans queued goals as a dependency graph (`depends-on`, capped by `parallel`), starts one worker per ready goal, watches and reports, and each worker runs its own loop and reports back. Run the commands from the main checkout, on the base branch. Needs you also lists a merged goal whose wiki publish was refused, with the page and the reason. Codex has run as a monitored background agent on a toy repo; it needs `-s workspace-write`, with the git folder and the remote as writable roots.

Commands, flows and how-tos: `skills/workflow-monitoring/references/commands.md`.

A failed release is recorded as `release_error` and lists under Needs you beside `wiki_error`.

## Criteria

- MON-1: **Reviewed 2026-11-08** Roles, start and planning. One command starts the operation session and drives the whole process the same way every time. The operation session plans queued goals as a dependency graph and runs every goal whose dependencies are met in parallel, each in its own worker and worktree, and never builds. A goal waits only on goals it truly depends on; sharing files is not a reason to wait: the later goal brings in the earlier one's merged changes and runs its checks again, and only a real conflict sends it back to fix. <!-- reviewed 83a0d431 -->
- MON-2: **Reviewed 2026-11-08** Live communication: a worker reports each change of step or status as it happens, and its result when it ends (merged, failed or waiting, with the pull request); the operation session can send a worker its answer or a follow-up. <!-- reviewed beca51fc -->
- MON-3: **Reviewed 2026-11-08** Board view: the board shows everything in one fixed template: what needs me, each running goal's progress bar and current step, what's next, roadmap progress, done lines met. <!-- reviewed b45361d0 -->
- MON-4: **Reviewed 2026-11-08** Printout: each check-in prints the same template as text: Needs you, Now, Next, Roadmap, Goals; Now shows progress bars with time and tokens per step against estimates; a stuck worker stays at the top of Needs you until answered. <!-- reviewed 7e5b6ec2 -->
- MON-5: **Reviewed 2026-11-08** Cadence: the operation session updates the board and prints the status on a set cadence (default 30 minutes, changeable), and at once whenever a worker reports something new; one line when nothing changed. <!-- reviewed d3f39d0a -->

## Tests

| Criterion | Test | Last run |
|---|---|---|
| MON-1 | [dependency-held](../../.loop/regression.tsv) | not run |
| MON-1 | [no-line-in-governor](../../.loop/regression.tsv) | PASS 2026-11-08 |
| MON-1 | [skill-says-governs](../../.loop/regression.tsv) | PASS 2026-11-08 |
| MON-1 | [dependencies-on-map](../../.loop/regression.tsv) | PASS 2026-11-08 |
| MON-1 | [failed-waits-mender](../../.loop/regression.tsv) | PASS 2026-11-08 |
| MON-1 | [worker-refuses](../../.loop/regression.tsv) | FAIL 2026-11-08 |
| MON-1 | [worker-per-goal](../../.loop/regression.tsv) | PASS 2026-11-08 |
| MON-1 | [one-way-to-run](../../.loop/regression.tsv) | PASS 2026-11-08 |
| MON-1 | [operate-all](../../.loop/regression.tsv) | not run |
| MON-2 | [worker-reports](../../.loop/regression.tsv) | PASS 2026-11-08 |
| MON-2 | [worker-reports-live](../../.loop/regression.tsv) | not run |
| MON-3 | [waits-first](../../.loop/regression.tsv) | PASS 2026-11-08 |
| MON-3 | [board-sections](../../.loop/regression.tsv) | PASS 2026-11-08 |
| MON-4 | [retired-leaves-waiting](../../.loop/regression.tsv) | PASS 2026-11-08 |
| MON-4 | [stuck-stays-top](../../.loop/regression.tsv) | PASS 2026-11-08 |
| MON-4 | [status-order](../../.loop/regression.tsv) | PASS 2026-11-08 |
| MON-4 | [needs-you-stuck](../../.loop/regression.tsv) | PASS 2026-11-08 |
| MON-4 | [estimates-shown](../../.loop/regression.tsv) | PASS 2026-11-08 |
| MON-4 | [status-roadmap-features](../../.loop/regression.tsv) | not run |
| MON-5 | [no-change-quiet](../../.loop/regression.tsv) | PASS 2026-11-08 |
| MON-5 | [operate-wakes-on-report](../../.loop/regression.tsv) | not run |
