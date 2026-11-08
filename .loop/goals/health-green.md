# Clear the health warnings: token reporting, release.py size, stale findings and merged branches

- Slug: health-green
- Touches: skills/workflow-delivery, skills/workflow-monitoring/scripts/worker.py, skills/workflow-release/scripts/release.py, .loop/findings.md, dev/toy

## Done lines

Frozen. A wrong done line needs a new goal.

1. Every flow step records the tokens its agent used in the run record, taken from the agent's own output, so the Cost rule reads real numbers and the status block shows tokens per step
2. release.py is under 90% of 20 KB with no behaviour change
3. .loop/findings.md holds 5 or fewer open findings, each one still true; the rest are resolved or retired with a reason
4. Merged loop branches are deleted by a cleanup command the health fix line names, and the health check shows no merged-branch warnings

## Verify by hand

<!-- One or more numbered steps a person can follow, each with an Expect: line. Every release needs this. -->
