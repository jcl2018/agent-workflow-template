# Make the board's runs tell the truth about pull requests and keep paths short

- Slug: board-truth
- Level: standard
- Touches: skills/workflow-monitoring/scripts/board.py, dev/toy/test-board.sh

## Done lines

Frozen. A wrong done line needs a new goal.

1. board.py reads each goal's pull request state with gh, shows open, merged or closed in Runs and Finished today, and shows unknown when gh cannot answer
2. Waiting on you shows the repo name and goal, not a long worktree path, and still says exactly where to type
3. dev/toy/test-board.sh proves both with a fake gh, and board.py stays under 20 KB
4. The repo checks pass

## Verify by hand

<!-- One or more numbered steps a person can follow, each with an Expect: line. Every release needs this. -->

## Design

## Plan
