# Give Documentation its one enforcing command and required docs, as DOC-1, DOC-3, DOC-4 and DOC-5 say

- Slug: docs-command
- Touches: skills/workflow-docs, skills/workflow-release, skills/workflow-health/scripts/milestone.py, docs/wiki, .loop/docs.tsv

## Done lines

Frozen. A wrong done line needs a new goal.

1. One template sheet in the docs skill defines the feature page and what each Tests column means, and the check reads its rules from it
2. One docs command checks all required docs against the template, code and tests, fixes what is mechanical, lists the wording to rewrite, and the release step runs it on every goal
3. It lists each Reviewed criterion with no test or with tests that no longer match, so the loop can queue a goal to write them
4. Each feature page links to its GitHub milestone, a Backlog milestone exists, and each release has a release note
5. A toy test proves each line above, and the repo checks pass

## Verify by hand

1. Run `python3 skills/workflow-docs/scripts/docs.py audit --dry-run`.
   Expect: `WOULD FIX` or `REWRITE` lines for what needs work, `UNTESTED` lines for Reviewed criteria with no test, and exit 1 while anything is left.
2. Open `skills/workflow-docs/references/template.md`, then change `max_criteria` in its rules block and run `python3 skills/workflow-docs/scripts/docs.py check`.
   Expect: `CAP` lines that follow the new number. Put it back to 5 afterwards.
3. Open `docs/wiki/Documentation.md`.
   Expect: a `Milestone:` line under the title linking its GitHub milestone.
4. Run `bash dev/toy/test-docs-command.sh`.
   Expect: every line prints PASS and the last line is ALL PASS.
