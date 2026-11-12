# lanes-abs-path: plan

1. narrow.scan: skip a quoted literal starting with / in the folder branch.
2. lanes.references: skip a candidate starting with /.
3. dev/toy/test-lanes-abs-path.sh + two rows in .loop/regression.tsv (REG-4), seen red, Tests table rendered.
4. Compare the reach of every row before and after (613, 0 differ).

Out of scope: other toys that fail the header check on main (test-runbook.sh, test-settings-table.sh).

DEPTH: full
STEP: done

## Review amendments (independent review, 2026-11-12)
The review found a `..`-climbing quoted literal and shell glob still reached os.walk, and a shared spy list in the toy test. Fixed: `lanes.walk()` refuses an absolute or `..` prefix (its only os.walk), toy cases c and d added with a spy per closure, row `lanes-dotdot-not-walked` seen red. Reach of all 616 rows identical before and after (0 differ), measured with main's lanes.py and narrow.py on the same tree.
