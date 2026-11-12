# Adoption never blocks, seeds tonight's format, is judged by health, and can learn from a repo already set up (owner, 2026-11-10: "Approve 1, 2, 3."); SET-1's milestone wording is corrected by the operation session under full auto (2026-11-11): "milestones per feature plus Backlog" and "on the right milestone" are dropped because the owner's later words make milestones free form and nothing needs one

- Slug: setup-adopt-2
- Touches: skills/workflow-setup, skills/workflow-health, dev/toy, .loop/regression.tsv, docs/wiki/Setup.md, docs/wiki/Home.md

## Done lines

Frozen. A wrong done line needs a new goal.

1. SET-1: one command adopts a new or existing repo with PRD pages in the docs format, the Home and README tables, the nightly regression, the health groups and every setting with its default; it shows what it would change first, applies on a branch, never overwrites, and never blocks: what doesn't fit is filed as issues tagged with their feature or group
2. SET-1 health first and last: a health check records the starting state before adopting, and the full health check after adopting is the adoption verdict, green or naming each gap with its fix
3. SET-2: settings resolve in three layers (template defaults, repo, local) and settings shows each value with the layer it came from
4. SET-6 (from adoption-proof): fixture repos shaped like real ones (existing config checks, CI tests with a .gitignore blocking *.tsv, a bare agent_command and no CI, features as milestones not folders) adopt cleanly in a nightly regression row; the existing-config-checks fixture reproduces pull request 83's bug, seen failing on old code and passing on the fix
5. SET-9: setup --from <adopted repo> borrows its settings shape, flow, milestone layout and private rules (never private values) and adapts them
6. SET-7 and SET-8: a dry run lists everything before any write, a second run changes nothing, and setup refuses to commit a file holding a local setting or private value
7. Each requirement above has a regression row seen failing then passing, listed in the Setup Tests table
8. Issues 119, 120 and 127 are fixed, each with a defect row seen failing then passing (owner-approved issue mapping 2026-11-10)

## Verify by hand

<!-- Numbered steps for a person, each with an Expect: line. A release needs this. -->
