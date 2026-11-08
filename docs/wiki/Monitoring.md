<!-- workflow-docs -->
# Monitoring

Milestone: https://github.com/jcl2018/agent-workflow-template/milestone/6

## Summary

Skill: `workflow-monitoring`. The operation session never does work: it assigns goals in batches to workers, watches and reports, and each worker runs its own loop and reports back. Run the commands from the main checkout, on the base branch. Needs you also lists a merged goal whose wiki publish was refused, with the page and the reason. Codex has run as a monitored background agent on a toy repo; it needs `-s workspace-write`, with the git folder and the remote as writable roots.

Commands, flows and how-tos: `skills/workflow-monitoring/references/commands.md`.

A failed release is recorded as `release_error` and lists under Needs you beside `wiki_error`.

## Criteria

- MON-1: **Reviewed 2026-11-08** Roles and start: one command starts the operation session and drives the whole process deterministically (assign, start workers, watch, cadence printouts); when I start it by talking to an LLM, the LLM runs that command and does not improvise the process. The operation session creates the work and the workers do it; it assigns goals in batches, starts one worker per goal in its own worktree, and never builds; goals touching the same files never run together; a failed goal can get one fresh worker. <!-- reviewed fda9b7c7 -->
- MON-2: **Reviewed 2026-11-08** Live communication: a worker reports each change of step or status as it happens, and its result when it ends (merged, failed or waiting, with the pull request); the operation session can send a worker its answer or a follow-up. <!-- reviewed beca51fc -->
- MON-3: **Reviewed 2026-11-08** Board view: the board shows everything in one fixed template: what needs me, each running goal's progress bar and current step, what's next, roadmap progress, done lines met. <!-- reviewed b45361d0 -->
- MON-4: **Reviewed 2026-11-08** Printout: each check-in prints the same template as text: Needs you, Now, Next, Roadmap, Goals; Now shows progress bars with time and tokens per step against estimates; a stuck worker stays at the top of Needs you until answered. <!-- reviewed 7e5b6ec2 -->
- MON-5: **Reviewed 2026-11-08** Cadence: the operation session updates the board and prints the status on a set cadence (default 30 minutes, changeable), and at once whenever a worker reports something new; one line when nothing changed. <!-- reviewed d3f39d0a -->

## Tests

| Criterion | Test | Last run |
|---|---|---|
| MON-1 | [overlap-held](../../.loop/regression.tsv) | PASS 2026-11-08 |
| MON-1 | [no-line-in-governor](../../.loop/regression.tsv) | PASS 2026-11-08 |
| MON-1 | [skill-says-governs](../../.loop/regression.tsv) | PASS 2026-11-08 |
| MON-1 | [dependencies-on-map](../../.loop/regression.tsv) | PASS 2026-11-08 |
| MON-1 | [failed-waits-mender](../../.loop/regression.tsv) | PASS 2026-11-08 |
| MON-1 | [worker-refuses](../../.loop/regression.tsv) | FAIL 2026-11-08 |
| MON-1 | [worker-per-goal](../../.loop/regression.tsv) | PASS 2026-11-08 |
| MON-1 | [one-way-to-run](../../.loop/regression.tsv) | PASS 2026-11-08 |
| MON-2 | [worker-reports](../../.loop/regression.tsv) | PASS 2026-11-08 |
| MON-3 | [waits-first](../../.loop/regression.tsv) | PASS 2026-11-08 |
| MON-3 | [board-sections](../../.loop/regression.tsv) | PASS 2026-11-08 |
| MON-4 | [retired-leaves-waiting](../../.loop/regression.tsv) | PASS 2026-11-08 |
| MON-4 | [stuck-stays-top](../../.loop/regression.tsv) | PASS 2026-11-08 |
| MON-4 | [status-order](../../.loop/regression.tsv) | PASS 2026-11-08 |
| MON-4 | [needs-you-stuck](../../.loop/regression.tsv) | PASS 2026-11-08 |
| MON-4 | [estimates-shown](../../.loop/regression.tsv) | PASS 2026-11-08 |
| MON-5 | [no-change-quiet](../../.loop/regression.tsv) | PASS 2026-11-08 |
