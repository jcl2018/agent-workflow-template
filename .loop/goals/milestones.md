# Add feature milestones, a Backlog for health findings, and a Milestones row on the board

- Slug: milestones
- Level: 1
- Touches: skills/workflow-health, skills/workflow-delivery/scripts/goal.py, skills/workflow-monitoring/scripts, dev/toy, docs/wiki/Health.md, .loop

## Done lines

Frozen. A wrong done line needs a new goal.

1. milestone.py new creates one GitHub milestone per feature page in .loop/docs.tsv and a Backlog milestone, running it again creates nothing, and milestone.py attach puts a goal's pull request in the milestone of the feature its touches name, which goal.py pr runs
2. health.py run files one issue per warning or failure on the Backlog milestone, found again by a hidden marker: a repeat updates it, a fixed finding closes it, a returning one reopens it, and with no token and no --live it only prints WOULD lines
3. milestone.py move puts an issue in a feature's milestone, and a later health run updates that issue where it is instead of moving it back or opening another
4. The board has a Milestones section with each milestone's open and closed counts and the age of the Backlog's oldest open issue, with no milestone rows when gh gives no answer
5. The Health page has new criteria marked Unreviewed with regression rows, dev/toy/test-milestones.sh proves every line above with a fake gh and is in checks, and every script stays under 20 KB
6. The repo checks pass

## Verify by hand

1. Run `python3 skills/workflow-health/scripts/milestone.py new --all` in this repo.
   Expect: WOULD lines for Backlog and each feature page, and nothing created on GitHub.
2. Run `python3 skills/workflow-health/scripts/health.py run`.
   Expect: WOULD create issue lines for each warning, each naming the Backlog, and nothing created on GitHub.
3. Run `python3 skills/workflow-monitoring/scripts/board.py board` and open the board page it names.
   Expect: a Milestones section at the bottom, with no rows until real milestones exist.

<!-- Numbered steps for a person, each with an Expect: line. A release needs this. -->

## Design

A feature is a page in `.loop/docs.tsv` (not Home), so there is no new config. `milestone.py` (self-contained, gh only)
creates milestones by listing first and creating only the missing ones, attaches a goal's PR through the feature its
`Touches` line names, and moves issues. `goal.py pr` runs `attach` after the PR exists, never failing the goal.
`health.py run` reuses the check rows and files one issue per non-pass row, found again by a hidden marker in the body;
create sets the Backlog once and later runs never touch the milestone, so a moved issue stays moved. Everything dry-runs
without a token or `--live`. The board reads milestones with `gh api` and shows nothing when gh gives no answer. Risks:
a pull request whose touches match no page gets no milestone (printed, not an error); wide `Touches` pick the first
page in the map.

## Plan

1. milestone.py and health.py run, with goal.py calling attach (lines 1, 2, 3).
2. Fake gh state for milestones and issues, and dev/toy/test-milestones.sh (lines 1, 2, 3).
3. Board Milestones section and test-board.sh asserts (line 4).
4. Milestones wiki page and rows, Health page, docs.py allows the page (line 5).
5. goal.py check and judge (line 6).
