# Make the release step fully automatic as DEL-5 says

- Slug: release-auto
- Touches: skills/workflow-release, skills/workflow-delivery, skills/workflow-monitoring/scripts/board_status.py, .loop/config.json, CHANGELOG.md, VERSION, dev/toy

## Done lines

Frozen. A wrong done line needs a new goal.

1. Every merged goal bumps the version once and adds a release note for it to CHANGELOG.md and a GitHub release, with no draft step and no question, even for a breaking change
2. Release refuses to merge while a page the goal touches is stale, and runs the owner's own routines listed in .loop/config.json before merging, refusing if one fails
3. Any release failure, including a failed merge, is recorded on the goal and shows under Needs you
4. A pull request body no longer says checks passed when the repo runs no checks
5. A toy test proves each line above, and the repo checks pass

## Verify by hand

1. Run `bash dev/toy/test-autorelease.sh 2>&1 | tail -45`.
   Expect: every line is PASS and it ends with ALL PASS.
2. Run `grep -n "Checks:" skills/workflow-delivery/scripts/goal.py`.
   Expect: the pull request body says "none ran; this repo configures no checks" when no checks ran.
