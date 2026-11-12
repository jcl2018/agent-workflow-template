# Record the lessons of the 2026-11-11/12 migration (a Mac's operation session handing the template to a Windows PC, with five adopted repos) in FINDINGS.md, file an issue for each actionable lesson not yet tracked, and propose Unreviewed requirement wording on the owning pages where a lesson changes behaviour

- Slug: migration-lessons
- Touches: FINDINGS.md, docs/wiki/Monitoring.md, docs/wiki/Delivery.md

## Done lines

Frozen. A wrong done line needs a new goal.

1. FINDINGS.md has one dated entry per lesson, each naming its tracking issue or goal
2. every actionable lesson has an open issue or a merged fix, and workflow-docs check prints DOCS OK

## Verify by hand

1. Open FINDINGS.md and read the last twelve entries.
   Expect: twelve entries dated 2026-11-12, "migration, lesson 1" to "lesson 12", each ending in the issue, pull request or release that tracks it.
2. Run `gh issue list --search "migration" --limit 3` or open issues 2871 to 2877.
   Expect: seven new open issues, one per lesson that nothing tracked, each starting with "Found in the 2026-11-11/12 migration".
