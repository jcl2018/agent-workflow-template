# Design: regression-issue-paging

## Problem
Both issue writers (the CI block in `actions.py:133` and `runs.py:91` for local runs) read `gh issue list --limit 200`.
The repo now holds more than 1000 regression issues, so an old issue falls off the list, the row looks new, and a duplicate
is opened every round (453 distinct titles are open, many duplicated). A row that was skipped for job time (code 125) also
opens a defect issue, which adds noise on every cut-short run.

## Approaches
1. Page with `gh api --paginate` on the REST issues endpoint. Complete, but the fields differ (lowercase state, PRs mixed in,
   labels shape), so both readers and the fake gh change. More code and risk.
2. Keep `gh issue list` (which pages internally) with a high `--limit` (5000), and treat a result of exactly `limit` rows as
   possibly cut off: read nothing, file nothing, print a NOTE. Small, keeps the field shape, fails closed.

## Chosen
Approach 2, in both `actions.py` and `runs.py`. A skipped row (code 125, out of job time) is handled like exit 77: state
SKIPPED, no issue opened, no comment on an existing one. A skipped row still does not close an open issue.
`dev/toy/test-regression.sh` lines 183-186 change to expect no issue for a skipped row, and gain a case where the fake gh
returns more than 200 existing issues (the marked one is the 201st): it must be found and no duplicate created; and a case
where the list reaches the limit: no write at all. The fake gh gets a `FAKE_GH_ISSUE_COUNT` knob that pads the list.
Then the duplicate and never-ran issues are closed from the live repo with a comment, only where the new code proves it:
for each failing-row marker keep the lowest-numbered open issue; close the others as duplicates; close issues whose body
says "was skipped" (never ran).

## Done lines
1. Limit raised and cut-off guard in `actions.py` (and `runs.py`).
2. Skip = 77 path; test updated; the over-200 case in the test.
3. Cleanup of live issues leaves at most one open per failing row; listed in the PR.

## Open questions
None.
