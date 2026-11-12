# Make the automation routines agree: one regression time budget across REG-7, AUT-7 and regression.yml with the suite sharded to fit, health triggered by workflow_run after regression instead of a fixed 30-minute offset, and the digest paging through issues or printing TRUNCATED (automation.py:101)

- Slug: automation-budgets
- Touches: skills/workflow-regression/scripts/automation.py, .github/workflows

## Done lines

Frozen. A wrong done line needs a new goal.

1. REG-7, AUT-7 and regression.yml name the same budget and the suite fits it
2. health.yml starts from workflow_run on regression, and the digest counts are never silently cut off

## Verify by hand

<!-- Numbered steps for a person, each with an Expect: line. A release needs this. -->
