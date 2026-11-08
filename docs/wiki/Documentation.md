<!-- workflow-docs -->
# Documentation

Milestone: https://github.com/jcl2018/agent-workflow-template/milestone/3

## Summary

Skill: `workflow-docs`. Keeps wiki pages in `docs/wiki/` (reviewed in pull requests; `wiki_dir` in `.loop/config.json` changes the folder) and finds stale ones. Each feature has a GitHub milestone named for its page, plus a Backlog, made by `skills/workflow-health/scripts/milestone.py`; a goal's pull request goes in its feature's milestone.

One command, `docs.py audit`, checks every page against the template sheet (`skills/workflow-docs/references/template.md`), fixes the mechanical, lists wording to rewrite and Reviewed criteria with no test, and the release step runs it on every goal. Commands, flows and how-tos: `skills/workflow-docs/references/commands.md` and `skills/workflow-health/references/milestones.md`.

The toy `gh` double (`dev/toy/fakegh`) can also merge a branch and fail a release, for the release tests.

## Criteria

- DOC-1: **Reviewed 2026-11-08** Template: one template defines every feature page: Summary (2-3 lines), Criteria (max 5, each with review status), Tests (one row per test: criterion it proves, test linked to its regression row, last result and date, "not enforced" for a criterion with no passing test); nothing else. <!-- reviewed d6bed5d8 -->
- DOC-2: **Reviewed 2026-11-08** Criteria are mine: high-level PRD-like plain lines I can check without code; Unreviewed or Reviewed with a date; only I mark Reviewed; then no one changes the wording unless I un-review it. <!-- reviewed 9db82973 -->
- DOC-3: **Reviewed 2026-11-08** Tests follow on their own: once I review a criterion, the loop writes the tests that prove it, links each to a regression row, adds it to the tests table; I never write or manage tests; a changed criterion gets its tests updated. <!-- reviewed e7ad710b -->
- DOC-4: **Reviewed 2026-11-08** One command enforces it: checks all required docs against the template, code and tests, fixes what's mechanical, lists wording to rewrite; the release step runs it on every goal before merging; I can run it myself. It never deletes a page, never overwrites a page it didn't write unless I name it, and the last publish can be undone. <!-- reviewed 72374942 -->
- DOC-5: **Reviewed 2026-11-08** Required docs: every repo keeps up to date one wiki page per feature, one GitHub milestone per feature linked from its page plus a Backlog milestone, and a release note for every release; each goal's pull request lands in its feature's milestone. <!-- reviewed f4c8ca82 -->

## Tests

| Criterion | Test | Last run |
|---|---|---|
| DOC-1 | [page-shape](../../.loop/regression.tsv) | PASS 2026-11-08 |
| DOC-1 | [criteria-no-scripts](../../.loop/regression.tsv) | PASS 2026-11-08 |
| DOC-1 | [tests-not-enforced](../../.loop/regression.tsv) | PASS 2026-11-08 |
| DOC-1 | [tests-last-run](../../.loop/regression.tsv) | PASS 2026-11-08 |
| DOC-1 | [tests-table-stale](../../.loop/regression.tsv) | PASS 2026-11-08 |
| DOC-1 | [template-sheet](../../.loop/regression.tsv) | PASS 2026-11-08 |
| DOC-2 | [review-dated](../../.loop/regression.tsv) | PASS 2026-11-08 |
| DOC-2 | [review-owner-only](../../.loop/regression.tsv) | PASS 2026-11-08 |
| DOC-2 | [reviewed-lock](../../.loop/regression.tsv) | PASS 2026-11-08 |
| DOC-2 | [unreview-lifts](../../.loop/regression.tsv) | PASS 2026-11-08 |
| DOC-2 | [lock-in-report](../../.loop/regression.tsv) | PASS 2026-11-08 |
| DOC-3 | [untested-listed](../../.loop/regression.tsv) | PASS 2026-11-08 |
| DOC-4 | [stale-found](../../.loop/regression.tsv) | PASS 2026-11-08 |
| DOC-4 | [publish-refused-stale](../../.loop/regression.tsv) | PASS 2026-11-08 |
| DOC-4 | [refuse-replace](../../.loop/regression.tsv) | PASS 2026-11-08 |
| DOC-4 | [stale-merge-order](../../.loop/regression.tsv) | PASS 2026-11-08 |
| DOC-4 | [docs-audit](../../.loop/regression.tsv) | PASS 2026-11-08 |
| DOC-4 | [release-runs-audit](../../.loop/regression.tsv) | PASS 2026-11-08 |
| DOC-5 | [milestones-once](../../.loop/regression.tsv) | PASS 2026-11-08 |
| DOC-5 | [pr-in-milestone](../../.loop/regression.tsv) | PASS 2026-11-08 |
| DOC-5 | [milestone-links](../../.loop/regression.tsv) | PASS 2026-11-08 |
| DOC-5 | [release-note-found](../../.loop/regression.tsv) | PASS 2026-11-08 |
