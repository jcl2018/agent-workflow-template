# Health keeps itself honest and the repo lean: negative controls, test-suite time, stale worktrees and branches

- Slug: health-hygiene
- Touches: skills/workflow-health, skills/workflow-regression, docs/wiki/Health.md, .loop/regression.tsv, dev/toy

## Done lines

Frozen. A wrong done line needs a new goal.

1. A new requirement HLT-6 is added to the Health PRD, Unreviewed, with the wording the owner reviews: Health keeps itself honest and the repo lean. Every health rule has a negative control that proves it can fire; the check flags a land test run over its time budget and names the slowest rows to move to nightly; and it flags stale worktrees and branches that exist only on this machine
2. Every health rule has a negative control, a small fixture that must make it report a finding; a rule whose control stays green is reported as a rule that cannot fire, and a new rule without a control is refused
3. Each regression run records its total time and each row's time; health reports a land lane over its time budget (a setting with a default) and names the slowest rows; the judge's performance review covers test time as well as tokens
4. Health reports worktrees with no live goal and local branches on no remote (older than a setting), each with the command that removes it, and never removes anything itself
5. A toy test proves each part fires on a bad fixture and stays quiet on a clean one
6. Per DOC-3, each done line above is recorded on its PRD page as one or more Given/When/Then scenarios under the requirement it serves, each linked to its regression row with its last result

## Verify by hand

<!-- Numbered steps for a person, each with an Expect: line. A release needs this. -->
