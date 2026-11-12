# Apply the owner's 2026-11-12 decisions on the health review's spec conflicts (REG-7, MON-3/5, GRD-1/2/5, DEL-5/6, DOC-1/4/6/14/15, HLT-2/4, AUT-2/3, Monitoring non-goal): reword each requirement to match the decision, mark every changed requirement Unreviewed, and log each decision in DECISIONS.md

- Slug: spec-decisions
- Touches: docs/wiki, skills/workflow-delivery/SKILL.md, skills/workflow-monitoring/SKILL.md, DECISIONS.md

## Done lines

Frozen. A wrong done line needs a new goal.

1. each listed conflict is resolved in the wiki pages and SKILL.md files as decided, and workflow-docs check prints DOCS OK
2. DECISIONS.md has one dated entry per decision, and every changed requirement reads Unreviewed

## Verify by hand

<!-- Numbered steps for a person, each with an Expect: line. A release needs this. -->

1. Run `grep -c "^- 2026-11-12, " DECISIONS.md`.
   Expect: it prints 10, and a "Waiting on owner un-review" section lists the locked requirements' proposed wording.
2. Run `python3 skills/workflow-docs/scripts/docs.py check`.
   Expect: the only line printed is `CHANGED Monitoring: Usage edited ...` (it needs the owner's review).
