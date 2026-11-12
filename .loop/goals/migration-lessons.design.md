# Design: migration-lessons

## Problem

The 2026-11-11/12 migration (a Mac's operation session handing the template and five adopted repos to a Windows PC)
taught twelve lessons that live only in chat. Without a dated record and a tracker each, they get lost or re-learned.

## Approaches

1. One FINDINGS.md paragraph summarising the migration. Cheap, but nothing links a lesson to its fix.
2. One dated FINDINGS.md bullet per lesson, each naming its tracking issue, merged PR or goal; one new issue per
   actionable lesson that nothing tracks; Unreviewed requirement wording only where a lesson changes behaviour.

**Chosen: 2.** It is what the done lines ask and keeps each lesson traceable.

## Tracked already (checked on GitHub, 2026-11-12)

1 Windows: #1395 (closed), #1396 (fixed by PR 2616), #1397, #1408; no Windows-safe check on merge: new issue.
2 Workers as app sessions: #1404; held workers looking silent without a session_command: new issue.
3 Remote Control cannot start sessions: #1404 (names it), the idle session pool is the shipped workaround.
4 Private repos: merged (v0.27.26 statuses, PR 2152, AUT-1 on the Automation page).
5 Handover loses run state, unpushed branch reported pushed: #2851.
6 Govern hook blocks the operation session's own notes: #2850; the double install: new issue.
7 Un-reviewing needs the owner's own sentence: new issue.
8 Off-platform red: #2865 and REG-10 (merged: skipped-unproven rows wait, no try).
9 auto_merge before the operation session reviews the diff: new issue.
10 Two sessions ran one scheduled routine at once: new issue.
11 Connector read-only until reconnected: comment on #1410 (probe the connectors).
12 "template version unknown" until update --apply: new issue.

## Behaviour changes

Lessons 1, 7, 9 and 12 change behaviour: Unreviewed requirement wording goes on Delivery.md (9, 12 adoption stamp is
Setup's, which is at criteria_max, so it stays an issue) and Monitoring.md (1, 2). Wording is a proposal, never reviewed.

## Done lines

1 FINDINGS.md: a check that each of the 12 lessons has one dated bullet naming its issue, PR or goal.
2 Every actionable lesson has an open issue or a merged fix; `workflow-docs check` prints DOCS OK.

## Open questions

None for the owner.
