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

<!-- Numbered steps for a person, each with an Expect: line. A release needs this. -->

## Design

## Plan
