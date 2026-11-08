# Remove a private skill-name prefix that leaked into a committed design note

- Slug: scrub-private-prefix
- Touches: .loop/goals/defect-tests.design.md

## Done lines

Frozen. A wrong done line needs a new goal.

1. .loop/goals/defect-tests.design.md line 84 no longer names any private skill; it says "run the delivery loop on this design" instead
2. A search of the whole repo for the private prefixes the leak hook blocks finds nothing

## Verify by hand

<!-- One or more numbered steps a person can follow, each with an Expect: line. Every release needs this. -->
