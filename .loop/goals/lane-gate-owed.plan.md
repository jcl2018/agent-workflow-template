# lane-gate-owed plan

Checked: goal.py cmd_pr (fail branch), fit.off_reply/off_rows and lane.py finalize exist; the fail branch moves to fit.pr_fail.

1. fit.pr_fail: owed proof prints the waiting text (run pr again), no failed try; other failures keep result and try. (done)
2. goal.py pr calls fit.pr_fail. (done)
3. Rows for REG-10 in regression.tsv: pr-waits-owed and pr-real-fail-costs-try, both on test-owed.sh; seen failing by breaking pr_fail's `if wait:`.
4. REG-10 wiki bullet and Tests tables via docs.py audit.

Could break: goal.py size cap (kept under 20,480). Out of scope: changing qa/ship waiting, recording proofs.
