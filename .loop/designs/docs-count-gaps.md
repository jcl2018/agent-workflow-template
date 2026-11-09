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

## Plan

Reviewed by autoplan, unattended (CEO and eng phases in-session; UI and DX scope: none, a check script's internals;
one independent Claude reviewer on the plan and code; Codex not used). Nothing here waits on the owner.

### CEO review
- Premise 1 REALITY: "no new module" is wrong. docs.py is 20,281 B against health's 20 KB FAIL limit (WARN from
  90%), and row prd-repo-green fails on any health FAIL. The count code (~5 KB) moves to a new
  `skills/workflow-docs/scripts/counting.py`; `docs.counts(root)` stays as a one-line wrapper because audit.py and
  dev/toy/test-prd.sh call it. Decision: accept (P2, in blast radius, one file).
- Premise 2 REALITY: holds. No README, wiki or skills/*.md line today matches the widened pattern (scanned), and the
  repo-green row checks it again in qa.
- Premise 3 REALITY: holds; partial counts stay a non-goal, noted in the PR body.
- Scope: the four issues and their tests; docs (SKILL.md COUNT row, Documentation page check bullet) say what is
  skipped now. Not in scope: a Markdown parser, partial counts, other readers of Requirements.
- Failure modes: a modifier missing from the part-word list makes a partial count read as a whole-set count (false
  COUNT, visible, fixed by a marker or rewording); deep list continuation misread as code (missed count, silent).

### Eng review
Data flow: `docs.py check|audit|publish` -> `docs.counts(root)` -> `counting.counts(root, folder, rows, on)` ->
`prose(text)` per file -> paragraph join -> `CLAIM.finditer` -> compare with skills / pages / criteria /
criterion rows + defect rows of the page's own ids.

1. CLAIM: `(\d+|WORD)[ \t]+(?:(?!STOP\b)([A-Za-z]+(?:-[A-Za-z]+)*)[ \t]+)?(NOUN)\b`, re.I|re.ASCII. The lookahead
   (not a post-filter) lets "two skills tests" still match "two skills" and makes "two other skills" match nothing.
2. prose(): per QUOTE-stripped line, `was_blank` from the previous line; tab-expanded indent; list column from a
   marker `^( {0,3})([-*+]|\d{1,9}[.)])( +|$)`; code = indent >= list column + 4 and (was_blank or in code). Code
   lines append "" so paragraphs split. Fence lines reset the code state.
3. Tests total adds `criteria.defect_rows(root)` (non-draft, goal is an id), the same rows `criteria.table()` lists
   under the page's Defect tests.
4. `alone` uses the file's own ids; the paragraph join keeps using `alone`, so a joined line skips only on its page.
5. Tests (dev/toy/test-criteria.sh, each run once on the unfixed code and seen failing):
   - "a word or extra space before the noun does not hide a count (104)": "twenty workflow-ready skills" and
     "nineteen  skills" each give a COUNT; "two other skills" gives none.
   - "an indented code block is not read as prose (105)": a count in a 4-space block after a blank line gives no
     COUNT; the same indent inside a list item is still read.
   - "a page's tests count includes its defect tests (106)": one criterion row plus one defect row, "2 tests" passes.
   - "a criterion id from another page does not hide a count (107)": on Delivery, a line naming EXT-1 with a wrong
     criteria count gives a COUNT; a line naming DEL-1 is still skipped.
   - The existing "defect rows left out" assertion changes to the new rule.
   Rows: four `defect` rows, goal DOC-4, linked to issues 104-107, Given/When/Then words; `criteria.py render`
   puts them under DOC-4's Defect tests on the Documentation page.
6. Size: counting.py well under 20 KB; docs.py drops to about 15 KB.

<!-- autoplan-accepted:ceo -->
- Move the count code to counting.py and keep docs.counts(root) as a wrapper; health shows no size FAIL for docs.py.
- SKILL.md COUNT row and the Documentation page say indented code is skipped and a criterion line is skipped only on its own page.
<!-- /autoplan-accepted:ceo -->
<!-- autoplan-accepted:eng -->
- One defect test per issue in dev/toy/test-criteria.sh, each seen failing on the unfixed code, each a defect row (goal DOC-4, issue link).
- CLAIM uses a negative lookahead for the part-word list; prose() skips indented code outside list content; tests total adds defect rows; id skip is per file.
<!-- /autoplan-accepted:eng -->

<!-- AUTONOMOUS DECISION LOG -->
## Decision Audit Trail

| # | Phase | Decision | Classification | Principle | Rationale | Rejected |
|---|-------|----------|----------------|-----------|-----------|----------|
| 1 | CEO | Approach A (patch in place) | Mechanical | P5 | smallest explicit fix per issue | B tokenizer, C markers |
| 2 | CEO | New counting.py module | Mechanical | P2 | docs.py would pass the 20 KB FAIL limit | trimming docs.py elsewhere |
| 3 | CEO | Partial counts out of scope | Taste | P3 | no done line; noted in PR | widening the goal |
| 4 | Eng | Lookahead instead of post-filter | Mechanical | P5 | keeps the no-modifier match | skip after match |
| 5 | Eng | Tests in test-criteria.sh | Mechanical | P4 | it already builds pages with criteria and rows | a new test file |
| 6 | Eng | Modifier word is an allowlist (workflow, workflow-*, installed, available, bundled, shipped, listed), not a denylist | Taste | P5 | reviewer: "two delivery skills", "3 regression tests", "Python 3 unit tests" are subsets or labels a denylist can't foresee; a false failure is worse than a miss (premise 2) | denylist |
| 7 | Eng | #107: a line naming another page's id still skips its criteria and tests counts; its skills and pages counts are checked. A line naming the file's own id is skipped whole | Taste | P1 | reviewer: "DEL-1 has 2 tests" on another page is about DEL-1, not that page | checking every count on such lines |
| 8 | Eng | "N defect tests" is checked against the page's defect rows | Mechanical | P1 | "9 tests plus 2 defect tests" must pass once the total includes defects | leaving it unmatched |
| 9 | Eng | List column: any marker below column + 4 sets it (nested lists); a heading, fence or table line at indent 0 clears it; CommonMark width (marker + 1-4 spaces, `1)` markers) | Mechanical | P1 | reviewer list gaps | indent<4 markers only |

Independent reviewer (Claude subagent, read-only): plan sound after items 6-9; no repo doc newly fails; counting.py
import is safe (no circular import, docs.tsv already maps skills/workflow-docs). Eng items 1, 4 and the 107 test
change accordingly: 107's test is "Unlike EXT-1, the toy has twenty skills." gives a COUNT, "EXT-1 alone has 3
tests." on Delivery gives none, and a line naming DEL-1 on Delivery is still skipped whole.
