# Align Health with HLT-2, HLT-3 and HLT-5

- Slug: health-tracker
- Touches: skills/workflow-health, dev/toy

## Done lines

Frozen. A wrong done line needs a new goal.

1. Health has a Mine group that runs the owner's own rules named in a private setting outside the repo, and prints UNREAD when one cannot run
2. Health prints one fixed template like the status block: each group, its findings with state and fix, and one verdict line
3. A separate suggestions step, marked as suggestions, lists conflicting or overlapping criteria, features missing a criterion, and ranked next steps from the warnings and failures; the rule check itself stays model-free and gives the same answer twice
4. A toy test proves each line above, and the repo checks pass

## Verify by hand

1. Write `~/.workflow-loop/health.json` as `{"rules": [{"name": "t", "command": ["false"], "fix": "fix t"}]}`, then run `python3 skills/workflow-health/scripts/health.py check`.
   Expect: it starts with `HEALTH REPORT`, ends with one `HEALTH:` line, and under `== Mine ==` shows `FAIL mine t mine: ... -> fix: fix t`. Change the command to `["nope-not-here"]` and it shows `UNREAD`. Delete the file afterwards.
2. Run `python3 skills/workflow-health/scripts/health.py suggest`.
   Expect: a first line `SUGGESTIONS (advisory, not findings...`, then criteria notes and ranked `next N:` steps.
