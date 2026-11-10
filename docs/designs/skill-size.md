# Design: skill-size, two SKILL.md files back under 150 lines

Written by the idea step on 2026-11-09
Branch: loop/skill-size
Status: APPROVED (unattended worker run, recommended answers)
Mode: Builder

## Problem Statement

`dev/toy/test-board.sh` checks that every `skills/*/SKILL.md` is under 150 lines (`-lt 150`). On main,
`skills/workflow-delivery/SKILL.md` is 160 lines (since test-lanes, v0.11.0) and `skills/workflow-docs/SKILL.md`
is 162 (since prd-format, v0.12.0). The check fails on main for every goal (issue 116). The fix must not drop
any instruction: a SKILL.md is what an agent reads first, and each skill already has a `references/` folder for
detail it reads on demand.

## Constraints

- Each file ends at 149 lines or fewer (the test is strict `-lt 150`); aim for about 140 so the next goal has room.
- No instruction lost: every moved sentence lands, word for word, in that skill's `references/` folder, and the
  SKILL.md keeps a one-line pointer naming the file and section.
- Keep in SKILL.md what tests or scripts read there: the `## Command map` table (criteria.py checks Usage verbs
  against it), the "governance only" / "never runs" lines (test-batch.sh), the step order and the gates.
- Touches only `skills/workflow-delivery`, `skills/workflow-docs`, `dev/toy` and `.loop/regression.tsv` (plus the
  Setup PRD page's generated Tests block and this design).
- Scripts stay under 20 KB; no script changes are needed.

## Premises

1. The 150-line rule stays; the fix is to the files, not the test. (Agreed: it keeps SKILL.md cheap to load.)
2. Moving whole paragraphs verbatim is safer than rewording: nothing can be lost in a paraphrase.
3. The moved paragraphs are the long, rarely needed detail: lane mechanics, token accounting, the PRD's test and
   conversion rules, the COUNT skip list. The run order, refusals and gates stay inline.

## Approaches Considered

### Approach A: Move detail paragraphs verbatim into the existing `references/commands.md` (chosen)

Each skill already ships `references/commands.md`. Append a section per moved block, word for word; the SKILL.md
keeps a short summary and a pointer. Effort S, risk low. Reuses the existing folder, so packaging and
`loop-files.md` need no change.

### Approach B: Reword and tighten the whole SKILL.md

Smaller files, but every sentence changes and "no instruction lost" becomes a judgement call. Rejected.

### Approach C: Raise the limit to 175

Hides the problem and the next goal hits it again. Rejected.

## Recommended Approach

Approach A.

- workflow-delivery: move "The regression lane" paragraph and the token-accounting sentences of step 2 into
  `references/commands.md` (new sections "The regression lane" and "Step tokens"), leaving a three-line summary
  that still names `LANE_DIRTY`, `LANE_MISSING` and `REUSED`.
- workflow-docs: move the `COUNT` skip rules, the "Tests follow on their own" and "New and old pages" paragraphs
  into `references/commands.md` (new sections), leaving a short summary with the `prd.py new` / `convert` commands.

## Tests (one per done line)

- Done line 1: `test-defect.sh skill-kept` checks both files are at most 149 lines and that a list of key phrases
  from the moved paragraphs (LANE_DIRTY, LANE_MISSING, test_record, cache-creation, `<!-- not-a-count -->`,
  `prd.py convert --write`, SCENARIO, ...) is still found in the skill's SKILL.md or `references/`. Row
  `skill-kept`, criterion, goal SET-3.
- Done line 2: `test-defect.sh skill-size` runs test-board's own rule over every SKILL.md. Row `skill-size-116`,
  category defect, link issue 116, seen failing via `regression.py red` against the old files.
- Done line 3: both rows have Given/When/Then descriptions under SET-3; `criteria.py render` writes them onto the
  Setup page's Tests.

## Plan (after review)

An independent review (one Claude subagent covering strategy, developer experience and engineering; the full
multi-phase review pipeline with a second model was not run, as out of proportion to a docs move) approved Approach A with
changes, all accepted:

- The first cut list was too small (delivery would end near 151, docs near 154). Delivery also moves the step-4
  `pr_bumps_version` and push-retry sentences and reflows step 4; docs also moves the six-item PRD list (its
  source is the template's `rules` block) and drops the COUNT move (it sits in one table row and saves nothing).
  Count lines before committing; target 145 or fewer.
- Keep inline: the Command map (all rows), "governance only" / "never runs", the run order, "Never review or
  unreview on a goal's own initiative", and a clause that row descriptions are Given/When/Then.
- `workflow-delivery/references/commands.md` must keep naming every goal.py command (test-goal.sh); appending is safe.
- `skill-kept` checks phrases only (one sentence from each moved block, verbatim, in `references/`), not line
  counts; `skill-size` is the defect's own test of the 150-line rule.
- Add both cases to `cases=` in test-defect.sh; both rows need a seen-failing date (`regression.py red` with a
  break that restores the old file); re-render the Setup page or the `categories` case fails.
- Editing the two skill folders makes the Delivery and Documentation wiki pages stale; the release step's
  `wiki.py prepare` lists them for rewriting on this branch.

## Open Questions

None blocking. Whether operate-all (issue 126) blocks the pr lane is decided at pr time.

## Success Criteria

test-board.sh prints no `over 150 lines` FAIL; the full land suite passes on HEAD; the two new rows pass and show
on the Setup page.

## Distribution Plan

Ships in the next package release through the existing release step; no new artifact.

## Next Steps

1. Move the paragraphs and add the pointers.
2. Add the two test-defect cases and rows; record `red` for the defect row.
3. Render the Setup page Tests; run the land suite.
