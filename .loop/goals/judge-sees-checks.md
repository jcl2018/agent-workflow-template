# Show the judge every check's exit code so long output cannot hide one

- Slug: judge-sees-checks
- Level: standard
- Touches: skills/workflow-delivery/scripts/goal.py, dev/toy/test-goal.sh

## Done lines

Frozen. A wrong done line needs a new goal.

1. goal.py check writes one summary line per check with its command and exit code at the top of the check results, so the judge's evidence always includes every check even when the output is cut
2. dev/toy/test-goal.sh proves a check whose long output would be cut still appears in the summary, and goal.py stays under 20 KB
3. The repo checks pass

## Verify by hand

1. In a repo with checks configured, run `python3 skills/workflow-delivery/scripts/goal.py check <slug>`, then `head -5` the `.checks.txt` file under `.git/loop/runs/`.
   Expect: the first lines read `CHECK exit 0: <command>` for each check, before any output.

## Design

`goal.py check` builds one `CHECK exit N: <command>` line per check and writes them, then a blank line, ahead of the
per-check output in the saved results. The judge pack appends that file whole, so cut-off output cannot hide a check.
Risk: the 20 KB size limit, so the docstring is trimmed with no change to behaviour.

## Plan

1. Add the summary lines in `cmd_check` and trim the docstring: proves done line 1.
2. In `dev/toy/test-goal.sh`, run a loud check plus a failing check and assert both summary lines sit at the top, and
   assert the size: proves done line 2.
3. Run `goal.py check`, which runs the repo checks: proves done line 3.
