# Plan: scrub-private-prefix

Goal: `.loop/goals/scrub-private-prefix.md` (done lines and Verify by hand belong to delivery; not restated or reopened here).
Reviewed by /autoplan (unattended, CEO + Eng; no UI or developer-tool scope). Every question took the recommended answer.

## Findings from reading the repo

- The one-line edit is already on the branch: commit `bdd00da` changed `.loop/goals/defect-tests.design.md` line 84 from the private-skill wording to "Run the delivery loop on this design: ...". Only that file changed.
- A search of the working tree (excluding `.git`) for the private skill-name prefixes finds nothing, so the second done line already holds on this branch.
- The leak hook's exact prefix list is not in the repo (README, Delivery and Home only mention the "private-name leak" check). So the search can only cover the prefixes the repo names or that the hook is known to block.
- Git history still holds the old text in `f5ee2d9` and earlier. Rewriting history is out of scope; the done lines only cover the tree.

## Steps

1. Confirm line 84 of `defect-tests.design.md` reads as the done line asks and the surrounding sentence still parses.
2. Re-run the repo-wide search for the private prefixes the hook blocks (case-insensitive; take the list from the hook, do not write it into a committed file) over all tracked files, including `.loop/`, `docs/`, `skills/`, `dev/`; expect zero hits.
3. Run the repo checks and `regression.py run land` to show nothing else moved.
4. No code, no new tests: a one-line wording change in a design note has no behaviour to guard, and the repo search in step 2 is the check.

## Failure modes

| Step | Failure | Handling |
|---|---|---|
| 2 | A prefix the hook blocks that is not in the search list | Run the hook's own scan if it is installed locally; otherwise record a finding |
| 2 | Hit inside a quoted example in another note | Reword it the same way and keep the diff to the touched files |

## NOT in scope

- Rewriting git history to remove the old line from earlier commits.
- Changing the leak hook itself.

## What already exists

- The edit (`bdd00da`) and the goal file (`9c90e99`).

## Decision Audit Trail

| # | Phase | Decision | Classification | Principle | Rationale | Rejected |
|---|-------|----------|----------------|-----------|-----------|----------|
| 1 | CEO | Keep scope to the one-line scrub | Mechanical | P3 | Matches the goal's Touches line | Widening to a hook change |
| 2 | Eng | No new tests | Mechanical | P5 | Prose-only change; the search is the check | A toy test for design-note wording |
| 3 | Eng | Leave git history alone | Taste | P3 | Done lines cover the tree; a rewrite is destructive | Force-rewriting merged history |
