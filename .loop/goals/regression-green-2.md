# The template's scheduled regression on GitHub goes green: the six rows failing on every run (breaking-asks, lanes-headers, lanes-repo-narrow, one-way-to-run, prd-repo-green, toy-no-leftovers) are each traced to a test that assumes this Mac or a regression in code, and fixed where they are wrong; stale per-row regression issues for rows that now pass are closed by the workflow (owner, 2026-11-11, asking whether the template's automations are implemented); prd: Regression

- Slug: regression-green-2
- Touches: dev/toy, .loop/regression.tsv, .github/workflows/regression.yml, docs/wiki/Regression.md, docs/wiki/Tests.md, skills/workflow-regression/scripts/actions.py, docs/wiki/Automation.md, skills/workflow-docs/SKILL.md, skills/workflow-docs/references/commands.md, docs/wiki/Documentation.md

## Done lines

Frozen. A wrong done line needs a new goal.

1. a regression run on GitHub ends with those six rows passing and no new failure
2. each fix names whether the test or the code was wrong; a code regression gets a failing-then-passing row
3. open regression issues match the rows failing on the latest run

## Verify by hand

<!-- Numbered steps for a person, each with an Expect: line. A release needs this. -->

1. After the merge, open the next scheduled regression run on GitHub (Actions, regression).
   Expect: breaking-asks, lanes-headers, lanes-repo-narrow, one-way-to-run, prd-repo-green and toy-no-leftovers read
   PASS, and no row reads FAIL that passed on the run before.
2. Run `gh workflow run regression.yml -f cleanup=true`, wait for it to finish, and read its log.
   Expect: a line `CLEANUP closed <n> issues`; repeat about two hours later until it reads 0.
3. Run `gh issue list --label regression --state open`.
   Expect: one issue per row that failed on the latest run, and no issue for a row that passed or was skipped.
4. In a checkout, run `python3 skills/workflow-regression/scripts/lanes_cli.py affected skills/workflow-monitoring/scripts/batch.py | head -1`.
   Expect: `AFFECTED n of m rows` with n well under half of m (it read 515 of 515 before).
