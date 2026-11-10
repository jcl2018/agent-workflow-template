# Narrow each regression row's file dependencies so a code change reruns only the rows that test it

- Slug: narrow-rows
- Touches: skills/workflow-regression, dev/toy, .loop/regression.tsv

## Done lines

Frozen. A wrong done line needs a new goal.

1. Each toy test script declares the files it actually exercises instead of whole folders, and lanes.py uses those to map changed files to rows
2. A one-file change in one skill reruns only that skill's rows, measured on this repo and shown in the PR
3. A row whose dependencies cannot be worked out still reruns on any change, never skipped
4. A toy test proves a narrow change reruns only its rows and a wide one reruns all
5. Per DOC-3, each done line above is recorded on its PRD page as one or more Given/When/Then scenarios under the requirement it serves, each linked to its regression row with its last result

## Verify by hand

<!-- Numbered steps for a person, each with an Expect: line. A release needs this. -->

1. In this repo, run `python3 skills/workflow-regression/scripts/lanes_cli.py check`.
   Expect: no output and exit status 0 (every test script a row names has a valid `# reads:` header).
2. Run `python3 skills/workflow-regression/scripts/lanes_cli.py affected skills/workflow-monitoring/scripts/batch.py`.
   Expect: `AFFECTED 81 of 225 rows (...)`, under half the land rows; with `LANES_WIDE=1` in front, all 225.
3. Run `python3 skills/workflow-regression/scripts/lanes_cli.py deps "bash dev/toy/test-live-board.sh 2>&1" --why skills/workflow-health/scripts/judge.py`.
   Expect: one chain of files from `dev/toy/test-live-board.sh` to `judge.py` (the live board runs health.py).
4. Delete the `# reads:` lines from `dev/toy/test-health.sh` and run step 1 again, then restore the file.
   Expect: `LANES-DECL-NONE dev/toy/test-health.sh:1: ...` and a `fix:` line, exit status 1.

## Measured on this repo

Land rows after merging main v0.17.0: 225. `lanes_cli.py affected <file>`, narrow vs `LANES_WIDE=1` (the old mapping):

| Changed file | Before (wide) | After (narrow) |
|---|---|---|
| skills/workflow-setup/scripts/update.py | 225 | 72 |
| skills/workflow-monitoring/scripts/batch.py | 225 | 81 |
| skills/workflow-health/scripts/judge.py | 225 | 93 |
| skills/workflow-monitoring/scripts/reply_hook.py | 225 | 216 |
| skills/workflow-setup/scripts/setup.py | 225 | 216 |
| skills/workflow-health/scripts/health.py | 225 | 224 |
| skills/workflow-docs/scripts/docs.py | 225 | 224 |
| skills/workflow-regression/scripts/regression.py | 225 | 224 |

- Floor: 72 rows run on any change. 39 of them run tools on the repo's own files (`cd "$here"`, `--root "$here"`;
  test-summary.sh, new from main, is 22 of those; test-defect.sh 12). The other 33 come from scripts that read every skill and declare
  `skills/`: test-adopt, test-rows, test-tree, test-reply-hook and test-health-hygiene.
- Across all 49 skill scripts: min 72, median 224, max 224. 7 files narrow below half. Leaf files narrow; hub files stay wide
  through real code chains (setup.py -> seed.py -> docs scripts; the live board -> health.py), so the median
  file still reruns nearly everything.
- Whole-PR diffs, the last 15 merges, measured before the merge (176 rows): median 176 -> 176. Two narrowed: stale-groups
  176 -> 112, operate-fit-3 -> 161.
- `affected` takes about 1-3 s. The nightly read trace (check-reads.sh) traced all 174 land commands clean before the merge.
- Limits: Python reads built at run time are caught only by the nightly trace. A `sys.executable -I` child bypasses the
  trace shim, a setsid child escapes its group kill, and a skill path behind another variable (`$OLDPWD/skills`)
  isn't seen.
- Moved, not removed: the whole-tree checks of 9 toy scripts and test-prd's repo-green section now live in
  dev/toy/test-tree.sh (rows one-way-to-run and prd-repo-green repointed, re-proved red).
