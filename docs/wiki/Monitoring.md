<!-- workflow-docs -->
# Monitoring

## Summary

Skill: `workflow-monitoring`. The operation session never does work: it assigns goals in batches to workers, watches and
reports, and each worker runs its own loop and reports back. Run the commands from the main checkout, on the base branch.
Keep the skill's scripts in one folder. Each runs alone, but apart from its helpers `watch` neither mends nor resumes,
`board` refuses `note` and `retire`, and the board's pages refuse an unfinished board.

Codex has run as a monitored background agent on a toy repo. It needs `-s workspace-write`, with the git folder and the remote as writable roots.

Needs you also lists a merged goal whose wiki publish was refused, with the page and the reason. Every script refuses
rather than waits when no terminal is attached.

In this repo, `auto_merge` is on, so a goal's agent ends by running the release step's merge, which merges its pull
request. With it off, the goal stops at the pull request for you.

Commands, flows and how-tos: `skills/workflow-monitoring/references/commands.md`.

## Criteria

- MON-14: **Unreviewed** What waits on the owner comes first, including every stuck worker until it is answered, retired work leaves it, and the board reports only real changes.
- MON-15: **Unreviewed** Goals that would collide never run together, and what each waits on stays on the map.
- MON-16: **Unreviewed** One failure stops only its own goal.
- MON-17: **Unreviewed** A goal that has landed, or has no worker process, is left alone.
- MON-18: **Unreviewed** The operation session only assigns, watches and reports: every goal runs in its own worker, which reports back.
- MON-19: **Unreviewed** Every check-in prints one fixed status block, with Needs you first and each step's estimated and actual time and tokens.

## Tests

| Criterion | Test | Last run |
|---|---|---|
| MON-14 | [MON-2](../../.loop/regression.tsv) | PASS 2026-11-07 |
| MON-14 | [waits-first](../../.loop/regression.tsv) | PASS 2026-11-07 |
| MON-14 | [MON-11](../../.loop/regression.tsv) | PASS 2026-11-07 |
| MON-14 | [stuck-stays-top](../../.loop/regression.tsv) | PASS 2026-11-07 |
| MON-15 | [MON-1](../../.loop/regression.tsv) | PASS 2026-11-07 |
| MON-15 | [dependencies-on-map](../../.loop/regression.tsv) | PASS 2026-11-07 |
| MON-16 | [one-failure](../../.loop/regression.tsv) | PASS 2026-11-07 |
| MON-17 | [MON-9](../../.loop/regression.tsv) | PASS 2026-11-07 |
| MON-17 | [MON-13](../../.loop/regression.tsv) | PASS 2026-11-07 |
| MON-17 | [no-pid-left-alone](../../.loop/regression.tsv) | PASS 2026-11-07 |
| MON-18 | [MON-4](../../.loop/regression.tsv) | PASS 2026-11-07 |
| MON-18 | [MON-8](../../.loop/regression.tsv) | PASS 2026-11-07 |
| MON-18 | [worker-refuses](../../.loop/regression.tsv) | PASS 2026-11-07 |
| MON-18 | [worker-per-goal](../../.loop/regression.tsv) | PASS 2026-11-07 |
| MON-18 | [worker-reports](../../.loop/regression.tsv) | PASS 2026-11-07 |
| MON-18 | [one-way-to-run](../../.loop/regression.tsv) | PASS 2026-11-07 |
| MON-19 | [status-order](../../.loop/regression.tsv) | PASS 2026-11-07 |
| MON-19 | [needs-you-stuck](../../.loop/regression.tsv) | PASS 2026-11-07 |
| MON-19 | [estimates-shown](../../.loop/regression.tsv) | PASS 2026-11-07 |
