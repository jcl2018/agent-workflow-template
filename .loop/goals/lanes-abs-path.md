# A lane's reach analysis never walks a folder outside the repo: lanes.references() joins an absolute path found in a script's text (os.path.join(root, "/abs/dir/")) and lanes.walk() then walks it, which made one goal's planning walk all of /private/tmp (284k files) per row and blow its planning budget; references() skips absolute paths outside the repo root and caches per-file references, with no change to which rows are picked (found by local-schedule, 2026-11-12)

- Slug: lanes-abs-path
- Touches: skills/workflow-regression/scripts/lanes.py, skills/workflow-regression/scripts/narrow.py, dev/toy, .loop/regression.tsv, docs/wiki/Tests.md

## Done lines

Frozen. A wrong done line needs a new goal.

1. a script that names /private/tmp/ is not walked, in a toy row seen failing on main and passing on the fix
2. the rows picked for a sample change are identical before and after
3. no new file under skills/

## Verify by hand

<!-- Numbered steps for a person, each with an Expect: line. A release needs this. -->
