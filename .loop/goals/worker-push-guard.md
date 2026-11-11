# Worker sessions can push only their own goal branch, never main or another goal's branch, so only the operation session's merge step publishes (owner, 2026-11-10: "Approve 1-9")

- Slug: worker-push-guard
- Touches: skills/workflow-delivery, skills/workflow-setup, dev/toy, .loop/regression.tsv, docs/wiki/Delivery.md, docs/wiki/Tests.md

## Done lines

Frozen. A wrong done line needs a new goal.

1. a pre-push hook that setup installs refuses, for a worker session, any push whose target is main or a branch other than loop/<its goal>, naming the rule and the fix
2. the operation session's merge and release steps are unaffected
3. regression rows for an allowed own-branch push and refused pushes to main and to another goal branch, each seen failing then passing

## Verify by hand

<!-- Numbered steps for a person, each with an Expect: line. A release needs this. -->
