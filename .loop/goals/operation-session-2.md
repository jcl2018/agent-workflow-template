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

1. Run `bash dev/toy/test-board.sh`.
   Expect: lines "a level with no finished goals gets exactly no estimate" and "handoff Waiting on the owner holds the question, exact words and where to type" are PASS, and the last line is ALL PASS.
2. Run `python3 -c "import json;print(json.load(open('.loop/config.json'))['checks'][-1])"`.
   Expect: it prints `bash dev/toy/test-board.sh`.

## Design

Extend the existing no-history assertion to require the exact text `no estimate: no finished quick goals yet` for the quick level (no finished quick goals in the fixtures) while a standard run keeps a real estimate. Re-add the waiting goal record before the handoff (it is deleted earlier) and assert its section line holds the question, exact words and where. Move the board test to the end of checks. Risk: assertions tied to board.py wording; they fail loudly if it changes.

## Plan

1. Exact no-estimate assertion in test-board.sh (done line 1).
2. Handoff waiting-section assertion in test-board.sh (done line 2).
3. Reorder checks in .loop/config.json so the board test is last (done line 3).
4. Run goal.py check (done line 4).

