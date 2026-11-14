# merge.py never posts a failing status on a release head it didn't test, and its refusal names the failing checks instead of asking for a manual merge (#3870)

- Slug: release-head-status
- Touches: skills/workflow-release, dev/toy

## Done lines

Frozen. A wrong done line needs a new goal.

1. A release head whose commit only moves the version and changelog gets the goal's passing lane carried over, and a real failure names its rows

## Verify by hand

<!-- Numbered steps for a person, each with an Expect: line. A release needs this. -->
