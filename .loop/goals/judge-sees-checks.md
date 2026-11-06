# Show the judge every check's exit code so long output cannot hide one

- Slug: judge-sees-checks
- Level: standard
- Touches: skills/workflow-delivery/scripts/goal.py, dev/toy/test-goal.sh

## Done lines

Frozen. A wrong done line needs a new goal.

1. goal.py check writes one summary line per check with its command and exit code at the top of the check results, so the judge's evidence always includes every check even when the output is cut
2. dev/toy/test-goal.sh proves a check whose long output would be cut still appears in the summary, and goal.py stays under 20 KB
3. The repo checks pass

## Verify by hand

<!-- One or more numbered steps a person can follow, each with an Expect: line. Every release needs this. -->

## Design

## Plan
