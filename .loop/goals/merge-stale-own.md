# merge.py's wiki check refuses only on pages the goal's own diff makes stale, the same scope as docs.py check --own, and reports the rest as findings (#3941)

- Slug: merge-stale-own
- Touches: skills/workflow-release/scripts, dev/toy, docs/wiki/Delivery.md

## Done lines

Frozen. A wrong done line needs a new goal.

1. With a page stale from a commit the goal does not touch, merge.py's wiki check passes and prints it as a finding; with a page the goal's own diff makes stale, it still refuses

## Verify by hand

<!-- Numbered steps for a person, each with an Expect: line. A release needs this. -->
