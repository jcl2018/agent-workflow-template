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

<!-- One or more numbered steps a person can follow, each with an Expect: line. Every release needs this. -->
