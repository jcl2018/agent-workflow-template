<!-- workflow-docs -->
# Milestones

## Summary

Skill: `workflow-health`. One GitHub milestone for each feature, named for its wiki page, and a `Backlog` for findings
nobody has placed yet. Goals and their pull requests go in their feature's milestone, health findings go on the
Backlog, and you move one to a feature when you decide. The board shows the counts. The scripts refuse rather than wait when no terminal is attached.

Delivery's `pr` puts the pull request in its milestone before any merge, so a pull request the release step merges with
`auto_merge` on keeps its milestone.

Commands, flows and how-tos: `skills/workflow-health/references/milestones.md`.

## Criteria

- MIL-1: **Unreviewed** Creating milestones makes one per feature page and one Backlog, and running it again creates nothing.
- MIL-2: **Unreviewed** A goal's pull request is put in the milestone of the feature its touched files belong to.
- MIL-3: **Unreviewed** Health findings go on the Backlog by default, and nothing is written to GitHub without a token or the live flag.
- MIL-4: **Unreviewed** An issue moved to a feature's milestone stays there when health updates it.
- MIL-5: **Unreviewed** The board shows each milestone's open and closed counts and how old the Backlog's oldest open issue is.

## Tests

| Criterion | Test | Last run |
|---|---|---|
| MIL-1 | [MIL-1](../../.loop/regression.tsv) | PASS 2026-11-07 |
| MIL-2 | [MIL-2](../../.loop/regression.tsv) | PASS 2026-11-07 |
| MIL-3 | [MIL-3](../../.loop/regression.tsv) | PASS 2026-11-07 |
| MIL-4 | [MIL-4](../../.loop/regression.tsv) | PASS 2026-11-07 |
| MIL-5 | [MIL-5](../../.loop/regression.tsv) | PASS 2026-11-07 |
