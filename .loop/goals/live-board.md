# Replace the status block with the live board, with the owner's new MON-4 and MON-5 wording approved in chat on 2026-11-08

- Slug: live-board
- Touches: skills/workflow-monitoring, docs/wiki, dev/toy

## Done lines

Frozen. A wrong done line needs a new goal.

1. MON-4 and MON-5 are unreviewed and rewritten word for word as follows, then marked Reviewed 2026-11-08 with criteria.py review --user, since the owner approved this wording in chat: MON-4 "Live board. Each check-in prints the live board, always in the same format: Issues first (only what is open now, each with its fix in plain words); then Running goals, each with a progress bar, time left, its step flow with the current step marked, and its next step; then Queued goals; then the dependencies between running and queued goals as arrows; then one finish time. Merged work, history and totals are left out. A stuck worker stays at the top of Issues until I answer." MON-5 "Cadence. The operation session updates the board and prints the live board on a set cadence, 30 minutes by default and changeable, and at once whenever a worker reports something new. It prints the full board every time."
2. operate and board_status print the live board exactly as MON-4 says, headed LIVE BOARD with repo, local time, version and health; each running goal shows a 10-cell bar with percent and time left, its step flow idea, plan, build, review, qa, ship, pr, release with done steps ticked and the current step in brackets, and a one-line next step; dependencies between running and queued goals are drawn with arrows; fixes are in plain words with no local file paths
3. The merged and closed lists, milestone rows, duplicate total, token tables and done-line lists no longer appear on the board, and the one-line no-change mode is gone
4. The board artifact page shows the same live board
5. A toy test with running, queued and chained goals and one open issue proves the format line by line

## Verify by hand

1. Run `python3 skills/workflow-monitoring/scripts/board_status.py`.
   Expect: it prints a `LIVE BOARD` header (repo, local time, version, health), then Issues, Running goals (each with a 10-cell bar, percent, time left, a step flow with the current step in brackets, and a `next:` line), Queued goals, Dependencies (arrows like `a --> b`) and a single Finish line, with no merged list, milestones, token tables or done-line lists.
2. Run `bash dev/toy/test-live-board.sh`.
   Expect: it ends with `ALL PASS`, after checking the board line by line.
3. Run `python3 skills/workflow-monitoring/scripts/board.py cadence`.
   Expect: it prints `CADENCE 30`.
