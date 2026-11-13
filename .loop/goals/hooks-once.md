# Setup and the hook commands install the reply and govern hooks exactly once each, however often they run (#2880, SET-13)

- Slug: hooks-once
- Touches: skills/workflow-setup/scripts, skills/workflow-monitoring/scripts, dev/toy

## Done lines

Frozen. A wrong done line needs a new goal.

1. Running setup's hook install three times leaves exactly one reply hook and one govern hook in settings.local.json

## Verify by hand

<!-- Numbered steps for a person, each with an Expect: line. A release needs this. -->
