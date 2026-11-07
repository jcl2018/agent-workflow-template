<!-- workflow-docs -->
# Documentation

## Summary

Skill: `workflow-docs`. Keeps wiki pages in `docs/wiki/` (reviewed in pull requests; `wiki_dir` in `.loop/config.json`
changes the folder) and finds stale ones. The release step now brings the pages a goal maps to up to date before the merge
and publishes them after it. Its scripts refuse rather than wait when no terminal is attached.

Commands, flows and how-tos: `skills/workflow-docs/references/commands.md`.

## Criteria

- DOC-4: **Unreviewed** A page that has fallen behind the code is caught before it reaches the wiki.
- DOC-5: **Unreviewed** Wiki pages written elsewhere stay as they are unless the owner names them.
- DOC-6: **Unreviewed** Every feature page is only a summary, its criteria and a table of their tests.
- DOC-7: **Unreviewed** Every criterion lists the tests that enforce it with their last result and date, and one with no passing test shows as not enforced.
- DOC-8: **Unreviewed** Every criterion shows whether the owner has reviewed it, and when.
- DOC-9: **Unreviewed** The wording of a reviewed criterion cannot change until the owner marks it unreviewed again.

## Tests

| Criterion | Test | Last run |
|---|---|---|
| DOC-4 | [DOC-1](../../.loop/regression.tsv) | PASS 2026-11-07 |
| DOC-4 | [DOC-2](../../.loop/regression.tsv) | PASS 2026-11-07 |
| DOC-4 | [stale-merge-order](../../.loop/regression.tsv) | PASS 2026-11-07 |
| DOC-5 | [DOC-3](../../.loop/regression.tsv) | PASS 2026-11-07 |
| DOC-6 | [page-shape](../../.loop/regression.tsv) | PASS 2026-11-07 |
| DOC-6 | [criteria-no-scripts](../../.loop/regression.tsv) | PASS 2026-11-07 |
| DOC-7 | [tests-not-enforced](../../.loop/regression.tsv) | PASS 2026-11-07 |
| DOC-7 | [tests-last-run](../../.loop/regression.tsv) | PASS 2026-11-07 |
| DOC-7 | [tests-table-stale](../../.loop/regression.tsv) | PASS 2026-11-07 |
| DOC-8 | [review-dated](../../.loop/regression.tsv) | PASS 2026-11-07 |
| DOC-8 | [review-owner-only](../../.loop/regression.tsv) | PASS 2026-11-07 |
| DOC-9 | [reviewed-lock](../../.loop/regression.tsv) | PASS 2026-11-07 |
| DOC-9 | [unreview-lifts](../../.loop/regression.tsv) | PASS 2026-11-07 |
| DOC-9 | [lock-in-report](../../.loop/regression.tsv) | PASS 2026-11-07 |
