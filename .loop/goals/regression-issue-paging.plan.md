# Plan: regression-issue-paging

Checked against the code: `actions.py:133` (CI block, `--limit 200`), `actions.py:170-183` (job-time skip is code 125, `skipped`
True, then falls into the `red` branch), `runs.py:91` (`sync_issues`, `--limit 200`), `dev/toy/test-regression.sh:183-186` (expects
an issue for a skipped row), `dev/toy/fakegh/gh:43-49` (the `issue list` fake). All exist. Live repo has 1000+ regression issues,
453 distinct open titles.

## Build steps
1. `actions.py`: a constant `ISSUE_LIMIT = 5000` (inside the generated block). List with `--limit 5000`; when `len(issues) >= 5000`
   set `issues = None` and print `NOTE: issue list may be cut off at 5000, so none changed`. Same for `runs.py` `sync_issues`
   (return with the NOTE). Regenerate `.github/workflows/regression.yml` through `regression.py workflow` so the committed file
   matches (a toy row checks it).
2. `actions.py`: a skipped row is not `red`: change the elif to `not skipped and code != 77`; its SKIPPED state, results line and
   the "passing again" close stay as they are (a skip never closes an issue). Drop the now dead "was skipped"/"Skipped: out of
   job time" wording branches.
3. `dev/toy/fakegh/gh`: `FAKE_GH_ISSUE_COUNT=n` pads the `issue list` output with n unrelated marked issues (numbers 100+), the
   real one placed last; honours `--limit` (returns at most that many).
4. `dev/toy/test-regression.sh`: the job-budget case now expects rc 0, `SKIPPED`, no `issue create`, no `issue comment`; add
   cases: 250 existing issues with the row's marker last: no duplicate created, comment goes to the old one; list at the
   limit: no write and the NOTE is printed.
5. Regression rows (`regression.py add` + `red`): `issue-list-pages-all` (DEL-?), `job-skip-opens-no-issue`, `issue-list-cut-off-refused`,
   each running `bash dev/toy/test-regression.sh` with a grep on a `PASS` marker line like the existing row; each seen red by
   breaking the line it guards.
6. After qa: close live duplicates (keep lowest-numbered open per row marker; close the rest "Duplicate of #N"), and any open
   issue whose body says "was skipped" ("never ran"); list their numbers in the PR. Run only with the new code's reading proven
   by the tests. Count open defect issues before and after.

## Tests per done line
1. Over-200 and at-limit cases (steps 3-4), rows `issue-list-pages-all`, `issue-list-cut-off-refused`.
2. Job-budget case, row `job-skip-opens-no-issue`.
3. The live cleanup, checked by `gh issue list` showing at most one open issue per row marker.

## What could break
Local run's `sync_issues` loses its older 200 limit: slower on a huge repo, bounded by 5000. A skipped row no longer fails
the CI job (rc 0), so a persistent skip is only visible in the results file.

## Out of scope
Pagination via the REST API; changing exit 77; the Mac tick's own issue code; health issue filing.

VERDICT: self-review: no blocking findings
