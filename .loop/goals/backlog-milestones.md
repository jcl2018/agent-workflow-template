# Each feature has a Backlog milestone; findings from delivery and health are filed as defects or backlog items by kind

- Slug: backlog-milestones
- Touches: skills/workflow-setup, skills/workflow-health, skills/workflow-delivery, docs/wiki, DECISIONS.md, dev/toy

## Done lines

Frozen. A wrong done line needs a new goal.

1. Setup creates the 9 Backlog milestones; health files a FAIL as a defect issue and a WARN as a backlog item on its feature's milestone; a goal's leftover findings are filed the same way at ship

## Verify by hand

<!-- Numbered steps for a person, each with an Expect: line. A release needs this. -->

1. Run `python3 skills/workflow-health/scripts/milestone.py backlog` in the template repo.
   Expect: nine lines, `EXISTS Backlog: <Feature>` for the eight feature pages and `EXISTS Backlog: Other`, and nothing created.
2. Run `python3 skills/workflow-health/scripts/health.py check --group adoption`.
   Expect: a `PASS adoption milestones` line; delete one Backlog milestone on GitHub and it becomes a `WARN` naming that milestone.
3. Run `python3 dev/toy/test-backlog.py`.
   Expect: every line `PASS:` and the last `PASS: every filing has one home`.
4. Write a ship reply with the line `FILE backlog Health: an idea` and run `python3 skills/workflow-health/scripts/milestone.py leftovers THAT_FILE` (no `--live`).
   Expect: `WOULD file backlog on milestone Backlog: Health: an idea (dry run; add --live)` and no issue created.
