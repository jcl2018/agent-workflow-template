# Make the health report formal and file findings as group-tagged issues under the owner's control, with the owner's new HLT-3 and HLT-4 wording approved in chat on 2026-11-08

- Slug: health-report
- Touches: skills/workflow-health, docs/wiki/Health.md, dev/toy

## Done lines

Frozen. A wrong done line needs a new goal.

1. HLT-3 and HLT-4 are unreviewed and rewritten word for word as follows, then marked Reviewed 2026-11-08 with criteria.py review --user, since the owner approved this wording in chat: HLT-3 "Formal report. Health prints one formal report: a header listing every rule group it ran (and any skipped), then each group in a fixed order with every rule it checked, marked pass, warn, fail or unread, each non-pass line with its fix, then one verdict. A rule that can't read its data is never shown as passing." HLT-4 "Findings become tagged issues, under my control. Each finding can be filed as one GitHub issue on the Backlog milestone, tagged with its group: health:size, health:criteria, health:docs, health:hygiene, health:performance (the Cost rule and the judge's savings), health:mine. A preview first lists exactly what would be opened, updated, closed or reopened, and nothing is written until I confirm or name the groups to file. A repeat updates its issue, a fix closes it, a return reopens it."
2. health check prints the formal report: a header naming every group run and skipped, every rule per group with its state, a fix on each non-pass line, one verdict; the Cost group is shown as performance
3. health preview lists each issue it would open, update, close or reopen with its tag, writing nothing; health file --group NAME writes only the named groups, each issue labelled with its health:group tag on the Backlog milestone
4. The Health page Usage lists the agent requests for check, preview, file by group and judge
5. A toy test with findings in several groups proves the report format, that preview writes nothing, and that filing one group touches only that group's issues with the right tag

## Verify by hand

1. Run `python3 skills/workflow-health/scripts/health.py check`.
   Expect: line 2 reads `groups run: ...; skipped: ...`, then each group with every rule and a state, the Cost group titled `performance`, and one `HEALTH:` line last.
2. Run `python3 skills/workflow-health/scripts/health.py preview`.
   Expect: `WOULD open/update/close/reopen ... [health:<group>]` lines and a `PREVIEW:` line; no issue changes on GitHub.
3. Run `python3 skills/workflow-health/scripts/health.py file`.
   Expect: `REFUSED: file needs --group ...` and nothing written.
4. Open `docs/wiki/Health.md`.
   Expect: HLT-3 and HLT-4 carry the new wording marked `Reviewed 2026-11-08`, and Usage lists the four agent requests.
