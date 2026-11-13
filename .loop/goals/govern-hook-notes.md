# The govern hook blocks the operation session's edits only inside followed repos, so its memory notes and other files outside every repo are not blocked (#2850, MON-7)

- Slug: govern-hook-notes
- Touches: skills/workflow-monitoring/scripts, dev/toy

## Done lines

Frozen. A wrong done line needs a new goal.

1. The govern hook refuses an Edit inside a followed repo and allows one to a path outside every followed repo

## Verify by hand

<!-- Numbered steps for a person, each with an Expect: line. A release needs this. -->
