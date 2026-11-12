# The v0.27.17 Settings and Automation README/Home blocks never break a repo not yet migrated: a lane's render refreshes those blocks only where their markers already exist (setup or migration inserts them, never a lane), places them where the page format allows, and a lane render commit does not make every mapped page stale (found in steward: the lane inserted '<!-- settings:begin -->' inside How to use, DOC-5 refused README, and all six pages read STALE)

- Slug: render-readme-guard
- Touches: .loop/regression-known.tsv, skills/workflow-docs/scripts/render.py, skills/workflow-setup/scripts/seed.py, skills/workflow-docs/scripts/docs.py, dev/toy, .loop/regression.tsv, docs/wiki/Documentation.md, docs/wiki/Tests.md

## Done lines

Frozen. A wrong done line needs a new goal.

1. in a toy repo whose README has no settings markers, a lane render leaves README and Home byte-identical
2. where setup inserts the blocks, docs.py check passes the page format (no DOC-5 intro-line refusal)
3. a lane render commit that only refreshes generated blocks leaves mapped pages fresh
4. setup with criteria on (no --bare) leaves the tree clean: the README and Home blocks it seeds are part of the adoption commit, so `bash dev/toy/test-adopt.sh SET-1` (row adopt-set-1, "setup left the tree dirty") passes and no lane ends with LANE_DIRTY on README.md (found by wiki-release-fix and goal-pr-try-budget on v0.27.17)
5. rows adopt-set-1 to adopt-set-5 pass on main and their .loop/regression-known.tsv entries (added by wiki-release-fix) are removed
6. each done line has a regression row seen failing then passing, listed in the Documentation Tests table
7. no new file under skills/

## Verify by hand

<!-- Numbered steps for a person, each with an Expect: line. A release needs this. -->
