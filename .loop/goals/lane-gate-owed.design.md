# lane-gate-owed design

Problem: REG-10 lets qa and ship wait (no failed try) when the lane fails only on rows skipped here and unproven, but goal.py pr's lane gate failed a try on the same state (#2865).

Approaches:
1. Make pr wait like qa/ship: on a lane line carrying LANE_OWED print the pending message, spend no try, and rerun cleanly once the proof is committed (lane reruns on the new HEAD and sees the seen-red date). Cost: small; risk: none for real failures, which still fail a try.
2. Let pr open the PR with owed rows. Cost: small; risk: an unproven row would ship, which the done line forbids.

Chosen: 1. The pr failure branch moves into fit.pr_fail (goal.py is at its size cap).

Done lines: proven rows pass the lane unchanged so pr opens without another proof; an unproven row still blocks (pr_fail returns 1, no PR). Both are toy-tested in test-owed.sh.

Open questions: none.
