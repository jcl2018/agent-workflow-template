# Add workflow-health: a read-only, rule-based health check command

- Slug: workflow-health
- Level: 1
- Touches: skills/workflow-health, skills/workflow-docs/scripts/docs.py, dev/toy/test-health.sh, docs/wiki/Health.md, .loop

## Done lines

Frozen. A wrong done line needs a new goal.

1. health.py check prints one line per finding and one HEALTH verdict line, identical across two runs on an unchanged repo, and --json prints the same rows as records
2. A script over 20 KB is a FAIL and one from 90 percent of it is a WARN, each with a fix line, and only FAIL and UNREAD make the verdict not green
3. It composes docs.py check and regression.py sync without re-implementing them, so a stale page, a criterion with no row, or a done line with no row shows as a row
4. A rule that cannot read its data prints UNREAD and the verdict is never green, and check writes no file and makes no commit
5. docs/wiki/Health.md has the Health page with unreviewed criteria, docs.py allows the Health page, dev/toy/test-health.sh is in checks with regression rows, and health.py stays under 20 KB
6. The repo checks pass

## Verify by hand

<!-- Numbered steps for a person, each with an Expect: line. A release needs this. -->

## Design

## Plan
