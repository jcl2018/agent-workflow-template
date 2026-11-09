# Design: docs-count-gaps

Status: APPROVED (unattended worker; recommended answers taken). Meets the frozen done lines in
.loop/goals/docs-count-gaps.md; changes none of them.

## Problem
`docs.py check` reads numbers the docs state (skills, feature pages, criteria, tests) and fails a wrong one. The
docs-counts goal (PR #103) left four gaps open, each found by its ship step:

- #104: `CLAIM` allows only an optional literal `workflow` and exactly one space between number and noun, so
  "eight workflow-ready skills" or "three  skills" hides a wrong count.
- #105: `prose()` skips fenced code only; a 4-space indented code block is read as prose and a count inside it can
  fail a correct page.
- #106: a feature page's tests count sums `criteria.test_rows()`, which drops defect rows, although the page's own
  Tests section lists them under `### Defect tests` (`criteria.table()` renders `defect_rows()` for the page's ids).
- #107: the "line about one criterion" skip (`alone`) uses every criterion id defined on any page, so a line on
  page B naming page A's id is skipped on B, and on the README and skills pages too.

## Premises
1. The fixes stay inside `counts()` and `prose()` (plus `CLAIM`); no new module, no dependency. Agreed.
2. A false failure on a correct page is worse than a missed count: every widening must leave this repo's own docs
   with no COUNT line (row `prd-repo-green` guards it). Agreed.
3. A count of part of a set ("two other skills") is out of scope: no done line covers it; it is left as a non-goal.

## Approaches
- A (minimal, recommended): patch in place. `CLAIM` takes `[ \t]+` and one optional modifier word
  (`[A-Za-z]+(?:-[A-Za-z]+)*`) that is not a part-word (`other`, `more`, `new`, `extra`, `additional`, `further`,
  `of`, `such`, `own`, `remaining`, `existing`, `different`, `separate`, `similar`, `related`, `optional`, `example`,
  `sample`, `toy`, `fake`, and the nouns themselves, as in "two skill tests"); `prose()` drops CommonMark indented code (4+ columns after a blank line, not
  inside a list item's content); the tests total adds `criteria.defect_rows()` for the page's ids; `alone` uses the
  page's own ids. Effort S, risk low. Reuses `defect_rows`, the existing paragraph join and fence state.
- B (ideal): a small Markdown block tokenizer shared by `prose()`, the Requirements reader and `criteria`. Cleaner,
  but touches every reader and the 20 KB size rule for docs.py; out of proportion to four gaps.
- C (lateral): require counts to carry a marker (`<!-- count -->`) and check only marked lines. Removes heuristics
  but every existing page needs editing and unmarked wrong counts pass silently — the opposite of the PRD.

Recommendation: A.

## Details (A)
1. #104. Modifier word sits in an optional group; a part-word there means "not a whole-set count" and the match is
   skipped. Whitespace is spaces/tabs only (paragraph joining already turns soft wraps into one space).
2. #105. In `prose()`, track `blank` (previous emitted line blank) and list context (a line starting with a list
   marker at indent < 4 sets the content column; a non-blank, non-indented, non-marker line clears it). A line whose
   expanded indent is >= content column + 4 and that follows a blank line or another code line is code: skipped,
   emitted as an empty line so paragraphs still split. Fences and comments keep precedence.
3. #106. `real["test"]` = criterion rows + defect rows of the page's ids (draft rows already excluded by both).
   The existing toy test that asserted defect rows are left out is updated to the new rule.
4. #107. `alone` uses `set(mine or [])`; a file that defines no criteria skips no id line. Criteria/tests are only
   checked on feature pages, so on other files only skills/pages counts become visible on such lines.

## Tests
One defect test per issue in `dev/toy/test-criteria.sh` (it already builds a feature page with criteria and rows),
each seen failing on the unfixed code, each a `defect` row in `.loop/regression.tsv` with goal DOC-4 and its issue
link, so it renders under DOC-4's Defect tests on the Documentation page with its last result (done line 6).

## Non-goals
- Partial counts ("two of the skills") compared with the total.
- A full Markdown parser.

## Risks
- The stoplist is heuristic: a modifier not in it ("two big skills") is read as a whole-set count. Acceptable per
  premise 2 only if this repo's docs stay green; the qa lane checks it.
- Indented-code detection can misread a deeply indented list continuation; list context guards the common case.

## The Assignment
After merge, run `python3 skills/workflow-docs/scripts/docs.py check` in a consumer repo with indented examples and
confirm no COUNT line comes from them.
