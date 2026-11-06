# Tighten the board test so the judge can see it prove the operation session

- Slug: operation-session-2
- Level: standard
- Touches: dev/toy/test-board.sh, .loop/config.json

## Done lines

Frozen. A wrong done line needs a new goal.

1. dev/toy/test-board.sh asserts that a level with no finished goals gets exactly no estimate on the board
2. dev/toy/test-board.sh asserts that the handoff file's Waiting on the owner section contains a waiting goal's question, its exact words and where to type them
3. bash dev/toy/test-board.sh is the last entry of checks in .loop/config.json, so its ALL PASS is the last output in the goal's check results
4. The repo checks pass

## Verify by hand

<!-- One or more numbered steps a person can follow, each with an Expect: line. Every release needs this. -->

## Design

## Plan
