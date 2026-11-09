# Plan: stale-groups

Goal: `.loop/goals/stale-groups.md` (done lines and Verify by hand are frozen and belong to delivery; not restated or reopened here).
Design: `.loop/goals/stale-groups.design.md`. Reviewed unattended. Every question took the recommended answer (approach B).

## Implementation plan

Order: text leftovers, then regression rows, then the group-list check, then the defect test, then docs check.

1. **Text leftovers (done line 1).**
   - `skills/design-guide.md:19`: rename "Criteria and tests" to Documentation. Line 21 ("milestones per feature") and line 52 describe real milestone behaviour for features, so they stay.
   - `docs/ROADMAP.md:47`: the page list becomes Delivery, Documentation, Health, Monitoring, Regression, Setup plus Home (it also lacks Health and Setup and says "five").
   - `skills/loop-files.md` and `README.md`: no removed group name found; re-grep and edit only on a hit.
   - `.loop/docs.tsv`: all paths are real (`workflow-release` is the release step, `milestone.py` and `fakegh` exist). No change.
2. **Regression rows 13-15 (done line 2).** `REL-1..3` exist in no wiki page; the only home is `dev/toy/test-rows.sh` cases (lines 65-80). DEL-5 now says release is automatic with no draft step and no question, so `cut-needs-verify`, `cut-draft` and `batch-cut-user` assert behaviour DEL-5 retired. First run each (`bash dev/toy/test-rows.sh REL-n`). A row that still proves something true is relinked to DEL-5 (its criterion cell changes from `-`); a row that passes only because it proves the retired draft/ask flow is retired with a reason in the row's note. The unused `REL-n` cases leave `test-rows.sh`, and its header drops "and Release".
3. **Group lists (done line 1).** `milestone.py` already builds its list from `.loop/docs.tsv` (minus Home) plus Backlog (`features()`, line 45), and `board.py` has no group list. No code change unless the test in step 4 finds one; the toy check seeds `fakegh` with Release and Milestones and confirms neither appears in `features` or `new --all`.
4. **Defect test (done line 3).** `dev/toy/test-stale-groups.sh`, no model. It derives the allowed set from `.loop/docs.tsv` page names (minus Home) plus Backlog. It then fails on any removed group name (Release or Milestones as a group, "Criteria and tests") in the wiki titles and headings, `.loop/docs.tsv` pages, the `milestone.py features` output (run against `dev/toy/fakegh`), the design-guide parts table and the README/ROADMAP page lists. The step word "release" is allowed by context (skill names, `workflow-release`, `DEL-5`, "Release the work", step lists); CHANGELOG is out of scope. Add a regression row, category `defect`, linked to issue 89. Show it failing on the base commit (`git stash`-free: run the script against `git worktree` of `main`/`HEAD~1` text, or revert step 1 locally) and passing now, then record `seen_red`.
5. **Checks (done line 4).** `docs.py check`, `criteria.py render --check` and health stay green; `wc -c` on any edited script stays under 20 KB.

## Failure modes

| Step | Failure | Handling |
|---|---|---|
| 1 | Edit hits a real milestone feature mention | only the group name changes; lines 21 and 52 stay |
| 2 | Retiring a row hides an untested criterion | each retirement carries a reason; a still-true row is relinked, not retired |
| 4 | Grep flags the release step | context allowlist; test also asserts DEL-5 and `workflow-release` stay unflagged |
| 4 | Test never seen red | `seen_red` is recorded only after a real failing run on the base text |

## Review record

<!-- accepted:ceo -->
- Approach B: the test derives the allowed group set from `.loop/docs.tsv`; scope stays the named surfaces; approach C (single source of truth) is out of scope.
<!-- /accepted:ceo -->

<!-- accepted:eng -->
- Step 3 is verify-only because `milestone.py` already reads `.loop/docs.tsv`; the toy test proves it with Release and Milestones seeded in `fakegh`.
- Rows 13-15 are decided by running them, not assumed (REL criteria exist in no wiki page).
<!-- /accepted:eng -->

