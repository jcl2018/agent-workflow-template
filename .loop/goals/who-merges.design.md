# who-merges: design

## Problem
Two PRs (#3855, #3792) merged with no session running merge.py (#3868).

## Cause
`sessions.py report SLUG --status waiting|merged --pr URL` set the goal done and, with auto_merge on and the PR still open, ran `release_step()`, which runs merge.py for that goal. A worker reporting "PR open; holding before merge.py" therefore merged it. No other code path runs `gh pr merge` (only merge.py); watch.py and auto.py only advise merge.py in prompts.

## Approaches
1. Keep the report-side release step but skip held goals: needs a hold flag nothing sets, and a report still has a side effect.
2. A report only records. Chosen: merges happen through the goal's own merge.py (run by its worker, or by worker.py when the agent exits done) or the operation's go.

## Done lines
Met by dev/toy/test-who-merges.py (two goals at pr, a report merges neither; the release step for one runs merge.py for only it; no other monitoring or delivery script starts merge.py) and its row, seen failing.

## Open questions
worker.py's exit fallback still runs merge.py for its own goal when the agent exits done; raised with the operation session.
