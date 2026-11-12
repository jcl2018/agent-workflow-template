# Plan: routine-runbooks

Goal: `.loop/goals/routine-runbooks.md`. Design: `.loop/goals/routine-runbooks.design.md`.

1. `skills/workflow-docs/references/template.md`: rules block gains `runbook_section`, `runbook_fields` and `runbook` in `format`; layout text and a Runbook entry (DOC-16).
2. `skills/workflow-docs/scripts/deployments.py` (`rules()`), `pageformat.py` (`runbook`, `owed`, CHECKS), `criteria.py` (section order, call sites), `prd.py` and `render.py` (the optional section is not a PRD section).
3. `.loop/routines.tsv`: the registry (health-round, regression-round).
4. `docs/wiki/Health.md`, `Regression.md`: the two runbooks; `Documentation.md` DOC-16 and `Automation.md` AUT-8, Unreviewed.
5. `dev/toy/test-runbook.sh` (good, refused, registry, locked, repo) and five regression rows, each seen failing against a real break.
6. Checks: docs check, docs toy tests, package check (99 files, scripts under 20 KB), lane.

Out of scope: the README and Home Automation section (settings-table), an automation prompt in another repo, a `docs.py runbook` command.

## Review amendments (autoplan, 2026-11-11)

Items 1-6 above are built and committed. What the review found is still to do, in this order:

1. Merge origin/main first (18 commits behind; `.loop/regression.tsv` conflicts: keep both row sets, no duplicate id; a conflict in the CLAUDE.md workflow block or `.loop/START.md`: take either side, run `entry.py write`, commit). Then measure `pageformat.py` (19247 of 20480 bytes before the merge) and the package file count (99 is the cap, not 99 of 100).
2. Correct the Health runbook against `health.yml` (H1 judge also needs a `judge_command` program and runs `judge_setup`; H2 groups not run on the runner are performance, hygiene, Mine and controls (the workflow's note and the runbook omit controls); H3 a feature tag only when `feature_labels` is on; H4 say how to start the workflow, `gh workflow run health.yml`, and that `automation.py digest` run outside Actions posts for real with GH_TOKEN, GITHUB_TOKEN or `--live` and is a dry run otherwise (round cost is only read in Actions); H5 name the suite-time fetch step; H6 Check also allows MAIL_OFF, DIGEST_ALREADY, DIGEST_STALE, and the summary shows the round cost line, not job times).
3. Correct the Regression runbook against `regression.yml` (R1 `regression.py run nightly` is not the CI run: it writes `regression-runs.tsv`, files issues when a token or `--live` is set, has no 88-minute job budget and writes no suite-time artifact (it does have the 900 s row cut and the token-free row environment); R2 a row skipped for job time (exit 125) still opens or comments an issue and a run with such rows is not a full run; R3 feature label only when `feature_labels` is on; R4 totals equal land plus nightly rows; R5 the health round reads the newest suite-time artifact of the last 20 runs, written only by a nightly run).
4. `pageformat.runbook`: refuse an unknown Serves id (pass `known` from `criteria.contract`'s `seen`), a repeated field and a repeated routine heading, all inside 1233 bytes; `criteria.contract` adds the page to `books` before the section-order `continue`. Four toy cases (serves, repeat, heading, order), each seen failing first, each with a regression row; re-render the Tests tables.
5. Deferred: a gate that every `.github/workflows` file names a registered routine in `.loop/routines.tsv` (`mail-test.yml` has none), and a Runbook for the mail-test workflow.
