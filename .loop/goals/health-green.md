# Clear the health warnings: token reporting, release.py size, stale findings and merged branches

- Slug: health-green
- Touches: skills/workflow-delivery, skills/workflow-monitoring/scripts/worker.py, skills/workflow-release/scripts/release.py, .loop/findings.md, dev/toy

## Done lines

Frozen. A wrong done line needs a new goal.

1. Every flow step records the tokens its agent used in the run record, taken from the agent's own output, so the Cost rule reads real numbers and the status block shows tokens per step
2. release.py is under 90% of 20 KB with no behaviour change
3. .loop/findings.md holds 5 or fewer open findings, each one still true; the rest are resolved or retired with a reason
4. Merged loop branches are deleted by a cleanup command the health fix line names, and the health check shows no merged-branch warnings

## Verify by hand

1. Run `bash dev/toy/test-tokens.sh`.
   Expect: it ends with ALL PASS, and a fake agent's step shows 175 tokens (input + output + cache-creation).
2. Run `wc -c skills/workflow-release/scripts/release.py`.
   Expect: it prints a number under 18432.
3. Run `python3 skills/workflow-health/scripts/health.py check --family hygiene`.
   Expect: no WARN line for findings or merged branches.
4. Run `bash dev/toy/test-cleanup.sh`.
   Expect: it ends with ALL PASS; `python3 skills/workflow-monitoring/scripts/worker.py cleanup --dry-run` lists merged loop branches without deleting any.
