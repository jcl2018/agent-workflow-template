# Fix issue 100: toy tests stop every stand-in process they start

- Slug: toy-cleanup
- Touches: dev/toy, .loop/regression.tsv

## Done lines

Frozen. A wrong done line needs a new goal.

1. Every toy test stops every background process it started (stand-in agents and the watch, worker, goal and flow scripts) when it ends, whether it passes, fails or is interrupted
2. A defect test linked to issue 100 runs the toy suite and proves no stand-in process outlives its test, seen failing once on the old code and passing now, and issue 100 closes when this merges
3. The full toy suite and regression run still pass

## Verify by hand

<!-- Numbered steps for a person, each with an Expect: line. A release needs this. -->
