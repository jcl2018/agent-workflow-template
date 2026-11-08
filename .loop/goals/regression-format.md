# Align Regression with REG-2 and REG-4, and fix the failing nightly test

- Slug: regression-format
- Touches: skills/workflow-regression, .github, .loop/regression.tsv, .loop/config.json, dev/toy

## Done lines

Frozen. A wrong done line needs a new goal.

1. Every test row has a plain one-line description of what it checks, and the Tests tables show each test with the words of the criterion it proves, its description, when it runs, last result and date, and whether it was seen failing
2. The GitHub Actions schedule comes from a setting in .loop/config.json, and regression.py workflow writes it; changing the setting and rewriting the workflow changes the schedule
3. The wiki-release test passes on GitHub, and issue 58 closes by itself on the next run
4. A toy test proves each line above, and the repo checks pass

## Verify by hand

1. Open `docs/wiki/Regression.md` and look at the Tests table.
   Expect: columns Criterion, Test, What it checks, Runs, Last result and Seen failing, each row with a plain one-line description.
2. In `.loop/config.json` set `"regression_cron": "5 4 * * 1"`, run `python3 skills/workflow-regression/scripts/regression.py workflow`, then `git diff .github`.
   Expect: the schedule line reads `cron: "5 4 * * 1"`. Set it back to `17 9 * * *` and run it again to restore.
3. After this merges, open the next run of the regression workflow on GitHub.
   Expect: `wiki-release` passes and issue 58 closes with "Passing again".
