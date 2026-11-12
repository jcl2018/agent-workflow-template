# The template's open issues come down to the real ones: every open non-regression issue (about 98: health findings, enhancements, goal bugs) is closed with evidence when already fixed or stale, folded into one issue when duplicated, or turned into a goal line the operation queues when it needs code; regression issues are left to regression-green-2's cleanup run (owner, 2026-11-11: "the open issues in the template is already 800, so I want you to fix them")

- Slug: issue-cleanup
- Touches: .loop/findings.md

## Done lines

Frozen. A wrong done line needs a new goal.

1. no open non-regression issue is a duplicate, already fixed or stale; each close carries a one-line reason with the evidence (commit, PR or check output)
2. every issue still open needs code, and each is either already covered by a queued goal or has a new goal line in .loop/findings.md naming the issue
3. closing goes through gh one issue at a time with its reason; nothing is deleted

## Verify by hand

<!-- Numbered steps for a person, each with an Expect: line. A release needs this. -->
