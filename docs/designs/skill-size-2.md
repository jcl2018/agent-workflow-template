# Design: skill-size-2, four scripts back under the size warning line

Written by the idea step (idea skill, unattended, recommended answers) on 2026-11-10
Branch: loop/skill-size-2
Status: APPROVED (unattended worker run, recommended answers)
Mode: Builder
Supersedes: skill-size (PR #163, merged)

## Problem Statement

Health's size group warns when a script reaches 90% of the 20 KB limit (18,432 of 20,480 bytes). It has filed
issues 138 to 142 for five scripts. On origin/main (e145b43) the sizes are:

| Script | Bytes | Issue | State |
|---|---|---|---|
| skills/workflow-delivery/scripts/goal.py | 19,415 | 138 | warns |
| skills/workflow-docs/scripts/criteria.py | 20,356 | 139 | warns (99%) |
| skills/workflow-docs/scripts/docs.py | 15,007 | 140 | already below the line |
| skills/workflow-regression/scripts/regression.py | 20,246 | 141 | warns (98%) |
| skills/workflow-release/scripts/release.py | 18,606 | 142 | warns |

Issue 116 (two SKILL.md files over 150 lines) was fixed by the first skill-size goal (PR #163). Both files are 149
and 143 lines, and row `skill-size-116` proves it.

## Constraints

- No behaviour change. Every split is a pure move: function bodies are moved byte for byte into a new sibling
  module, and the old module imports them back under the same names. Then `goal.X`, `release.docs_trouble`,
  `criteria.tests_format` and the other names that tests and sibling scripts call (merge.py, wiki.py,
  autorelease.py, docs.py, prd.py, audit.py, counting.py, test-prd.sh, test-criteria.sh, test-docs-command.sh,
  test-summary.sh) still resolve.
- Moved code never imports its old module back. When a script runs as `__main__`, a back-import loads a second
  copy of the module with its own state. Only leaf blocks move: functions whose dependencies are the standard
  library, each other, or a tiny primitive that is copied as well (for example `git` or `run`, a few lines each,
  kept identical in both files).
- Each of the four files ends below 18,432 bytes with at least about 1 KB of headroom, so the next goal doesn't
  trip the warning straight away. Each new module is well under 18,432 bytes too.
- SET-3 ("every script self-contained and under 20 KB") holds: new modules use only the standard library and live
  next to the script they serve. Sibling imports already exist (lanes.py imports narrow, regression.py imports
  actions and lanes), and `lanes.py` follows sibling imports for affected-row selection, so new modules land in
  the right test lanes.
- Pure-move commits: one commit per file, holding just the move and the import-back line. A reviewer can then
  check with `git diff --color-moved`.
- Other goals are editing these files now: docs-format (criteria.py, docs.py), lane-control (regression.py),
  delivery-prd (goal.py, release.py). Each file's split waits until the goal editing it has merged, and is cut
  from that merged content.
- Touches: the line names skills/workflow-delivery, skills/workflow-docs, dev/toy and .loop/regression.tsv. The
  operation session is widening them to add skills/workflow-regression/scripts and skills/workflow-release/scripts.

## Premises

1. The 90% warning line is the real target. The done line says "under the 20 KB limit", which all five files
   already meet, but the issues only close when health stops warning. (Operation session agreed.)
2. A pure move with an import back is the only kind of split that is provably behaviour-free. Trimming or
   rewording code is not, so it is out of scope.
3. Issue 116 and the docs.py half of issue 140 are proved with rows that already pass, not redone.
4. The full regression suite, run once in qa, is the proof of no behaviour change, together with a new defect row
   that fails on the old sizes and passes on the new ones.

## Approaches Considered

### Approach A: Leaf-block moves into sibling modules, with names imported back (chosen)

For each file, pick a cohesive block that does not call back into the module, move it byte for byte to a new
sibling, and write `from <new> import a, b, c  # noqa` in the old file.

Likely blocks, re-checked against each file as it stands after the other goals merge:

- goal.py: the goal-file text helpers (`TEMPLATE`, `done_lines`, `done_sha`, `frozen`, `held`), or
  `flow_set`/`valid`.
- criteria.py: the tests-format and scenario-table block (`tests_format`, `scenario`, `table`, `issue_cell`,
  `RUNS`/`SEEN`).
- regression.py: the issue-sync block (`gh`, `sync_issues`, `MARK`).
- release.py: the changelog and version block (`bump`, `subjects`, `changelog_text`, `restore`), or the docs and
  criteria checks.

Effort S per file, risk low, and the moves are easy to review.

### Approach B: Trim code in place (shorter docstrings, merged helpers)

Rejected: this isn't a pure move, so behaviour might change. Each trim also buys only a little headroom, and the
files would be back at the line after the next feature.

### Approach C: Raise the warning line or the limit

Rejected: health's rule and SET-3 set the 20 KB contract, and the issues ask for the files to be split.

## Recommended Approach

Approach A. Order the work by merge: each file is split as soon as the goal editing it has merged into main, and
the branch merges main right before `goal.py pr`. Add one defect row per issue (138, 139, 141, 142), linked to its
issue. Each row checks that its file is below 18,432 bytes, is seen failing on the old code, and passes after the
split. Record each done line on the Setup PRD page as a Given/When/Then scenario under SET-3 (DOC-3). For done
lines 1 and 2, point at the existing `skill-size-116` and `skill-kept` rows, and add a docs.py size row for
issue 140.

## Open Questions

None for the owner. The touches widening is already requested from the operation session.

## Success Criteria

- `wc -c` shows goal.py, criteria.py, regression.py and release.py each below 18,432 bytes, with docs.py still
  below it too.
- `health.py check` prints no size WARN for those five files.
- The full land suite passes on the split HEAD, and the new defect rows were seen failing first.

## Dependencies

- docs-format, lane-control and delivery-prd merge first, or their in-flight edits to these files are left alone.
- The operation session widens touches to skills/workflow-regression/scripts and skills/workflow-release/scripts.

## The Assignment

After each blocking goal merges, merge main and split its file in one pure-move commit.
