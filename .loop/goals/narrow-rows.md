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
   Expect: `AFFECTED 34 of 175 rows (...)`, well under half the land rows; with `LANES_WIDE=1` in front, all 175.
3. Run `python3 skills/workflow-regression/scripts/lanes_cli.py deps "bash dev/toy/test-live-board.sh 2>&1" --why skills/workflow-health/scripts/judge.py`.
   Expect: one chain of files from `dev/toy/test-live-board.sh` to `judge.py` (the live board runs health.py).
4. Delete the `# reads:` lines from `dev/toy/test-health.sh` and run step 1 again, then restore the file.
   Expect: `LANES-DECL-NONE dev/toy/test-health.sh:1: ...` and a `fix:` line, exit status 1.
