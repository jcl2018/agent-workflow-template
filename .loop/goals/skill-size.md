# Fix issue 116: bring workflow-delivery and workflow-docs SKILL.md back under 150 lines

- Slug: skill-size
- Touches: skills/workflow-delivery, skills/workflow-docs, dev/toy, .loop/regression.tsv

## Done lines

Frozen. A wrong done line needs a new goal.

1. skills/workflow-delivery/SKILL.md and skills/workflow-docs/SKILL.md are each at most 150 lines with no instruction lost (detail moves to its references folder)
2. test-board passes on main again and a defect test linked to issue 116 is seen failing once
3. Per DOC-3, each done line is recorded on its PRD page as a Given/When/Then scenario

## Verify by hand

1. Run `wc -l skills/workflow-delivery/SKILL.md skills/workflow-docs/SKILL.md`.
   Expect: each is under 150 lines.
2. Run `bash dev/toy/test-board.sh | tail -1`.
   Expect: it prints ALL PASS, with no "over 150 lines" line above it.
3. Open `skills/workflow-docs/references/commands.md` and go to "Moved from SKILL.md".
   Expect: the six-item PRD page list, Review locks, Tests follow on their own and New and old pages, each in full.
