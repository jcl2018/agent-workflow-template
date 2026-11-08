# Remove a private skill-name prefix that leaked into a committed design note

- Slug: scrub-private-prefix
- Touches: .loop/goals/defect-tests.design.md

## Done lines

Frozen. A wrong done line needs a new goal.

1. .loop/goals/defect-tests.design.md line 84 no longer names any private skill; it says "run the delivery loop on this design" instead
2. A search of the whole repo for the private prefixes the leak hook blocks finds nothing

## Verify by hand

1. Run `sed -n 84p .loop/goals/defect-tests.design.md`.
   Expect: the line starts with "Run the delivery loop on this design" and names no private skill.
2. Run `git grep -n 'goal_\*'`.
   Expect: no match in the design note.
