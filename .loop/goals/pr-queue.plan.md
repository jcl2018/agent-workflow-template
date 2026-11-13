# pr-queue plan

Checked against the code: goal.py cmd_pr, guards.failed_try (the LANE_DIED free reruns are the pattern), graph.merge_lock, pool.py.

## Build steps
1. pool.py: pr_turn (queue), pr_ahead (did main move), pr_moved (the separate cap). graph.py: pr_queue forwards. goal.py cmd_pr uses them.
2. Update the two toys and the docs that said a conflict costs a try: test-pr-tries.sh, test-operate.sh, SKILL.md lines, ptb-mend text.
3. dev/toy/test-pr-queue.py parts queue, moved, pr, with rows pr-queue-order, pr-moved-uncounted, pr-queue-goal, each seen red.
4. Docs: a Usage line on the Delivery and Monitoring pages; re-render the Tests tables; wiki.py prepare.

## What could break
Script sizes: graph.py 18148 (cap 18300), goal.py 19278 (18878 + 400), pool.py 15 KB. Existing toys that expect a counted conflict try (updated).
A queue file left by a killed worker is replaced after 30 minutes or when its run record is no longer running.

## Out of scope
merge.py and merge.lock; the pr lane's own length; serializing lanes other than pr.
