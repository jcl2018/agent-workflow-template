# Finish operate's status block: clear stale wiki errors, know closed pull requests, show only live goals

- Slug: operate-fit-2
- Touches: skills/workflow-monitoring/scripts/operate.py, skills/workflow-monitoring/scripts/board_status.py, skills/workflow-monitoring/scripts/board_runs.py, dev/toy

## Done lines

Frozen. A wrong done line needs a new goal.

1. A goal's wiki_error leaves Needs you once a later publish succeeds or reports no change, or once the goal is merged, including goals that finished before this fix
2. A goal whose pull request is closed without merging shows as closed, never as awaiting merge
3. Goals lists done lines only for running, waiting and queued goals and for goals merged since the last check-in; older merged goals appear only in the merged line
4. A toy test with stale wiki errors, a closed pull request and old merged goals proves each line above

## Verify by hand

1. Run `bash dev/toy/test-operate-fit.sh`.
   Expect: it ends with ALL PASS, including the closed, healed and old goals section.
2. Run `python3 skills/workflow-monitoring/scripts/operate.py run --once` twice in a repo with goals.
   Expect: the first prints the block and Goals lists no old merged goals; the second prints one "Nothing changed" line.
