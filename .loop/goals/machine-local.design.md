# Design: machine-local

## Problem
A goal waits on proofs only another machine can give (a red run on Mac or Linux, a smoke cell). Today such a row is UNPROVEN, the pr lane answers PENDING, and the goal, its merge and the release stall. A goal should depend only on what its own machine can do; the other-machine step is a to-do, not a block.

## Approaches
1. Weaken the gate: let UNPROVEN rows that skipped pass silently. Cheap, but the owed proof is then invisible and never followed up.
2. Record the proof as owed (`regression.py red ID --owed --runner R`): a row in `.loop/regression-owed.tsv`, one to-do issue labelled `other-machine` on the row's feature milestone, the row reads PENDING (not UNPROVEN) so the lane passes, health warns after 7 days and never fails, the check-in lists it under Coming up. A real red proof clears it. Costs a small record and a few lines in four scripts, all under the 19,000-byte cap.

## Choice
Approach 2: the proof stays visible and followed, and nothing waits on it.

## Done line
Needs: the owed record and issue (runs.py, regression.py), PENDING in sync and run, health WARN past 7 days and no FAIL (health.py), the Coming up line (checkin.py), a Python toy seen red (test-machine-local.py, row machine-local-owed).

## Open
The GRD-11 wording and the Regression, Health and Monitoring sub-bullets sit in DECISIONS.md: those pages are Reviewed, so the owner applies them.
