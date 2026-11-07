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
| DOC-4 | [DOC-1](../../.loop/regression.tsv) | not run |
| DOC-4 | [DOC-2](../../.loop/regression.tsv) | not run |
| DOC-4 | [stale-merge-order](../../.loop/regression.tsv) | not run |
| DOC-4 | **not enforced** | |
| DOC-5 | [DOC-3](../../.loop/regression.tsv) | not run |
| DOC-5 | **not enforced** | |
| DOC-6 | [four-sections](../../.loop/regression.tsv) | not run |
| DOC-6 | [flow-charts](../../.loop/regression.tsv) | not run |
| DOC-6 | **not enforced** | |
| DOC-7 | [names-enforcer](../../.loop/regression.tsv) | not run |
| DOC-7 | **not enforced** | |
| DOC-8 | [unreviewed-banner](../../.loop/regression.tsv) | not run |
| DOC-8 | **not enforced** | |
| DOC-9 | [returned-on-change](../../.loop/regression.tsv) | not run |
| DOC-9 | [returned-in-report](../../.loop/regression.tsv) | not run |
| DOC-9 | [change-not-blocked](../../.loop/regression.tsv) | not run |
| DOC-9 | **not enforced** | |
