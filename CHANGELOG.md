# Changelog

## v0.3.0 - 2026-11-08

- MON-1: rewrite for the dependency-graph planner
- operate: dependency-graph planner, operate command, base merge, worker guard, live reports, status block
- Regression: seen red for three operate rows; tighten the message check
- Review: drop unused cycle(), take the inbox atomically
- Merge origin/main into loop/operate; guard role.py against prompts
- Release v0.1.4 (operate)
- Undo the ship step's version bump: the release step owns the version
- Wiki: update pages for operate
- Merge origin/main into operate

### How to verify

1. From the repo root, run `bash dev/toy/test-operate.sh`.
   Expect: it prints a `PASS:` line for each part (dependency start, status block, reports, follow-up, worker guard, operate loop, base merge) and ends with `ALL PASS`.
2. Run `python3 skills/workflow-monitoring/scripts/operate.py run --once` on the base branch.
   Expect: it prints the five status sections (Needs you, Now, Next, Roadmap, Goals), then `DIGEST`, `CHANGED`, `NEXT_DELAY` and the board paths.
3. Run `python3 skills/workflow-delivery/scripts/goal.py check operate` in a plain shell.
   Expect: one line, `REFUSED: check is worker work; the operation session only assigns, watches and reports. Use: batch.py start NAME`.
4. Run `grep -n "MON-1" docs/wiki/Monitoring.md`.
   Expect: the line says `Reviewed 2026-11-08` and begins `Roles, start and planning.`

## v0.2.0 - 2026-11-08

- Give Documentation its one enforcing command: docs.py audit, template sheet, milestone links, release-note check
- Release step: a failed audit refuses instead of passing
- Merge origin/main into docs-command: rules read from the template sheet, six Tests columns
- Delivery page: the release step runs the docs audit

### How to verify

1. Run `python3 skills/workflow-docs/scripts/docs.py audit --dry-run`.
   Expect: `WOULD FIX` or `REWRITE` lines for what needs work, `UNTESTED` lines for Reviewed criteria with no test, and exit 1 while anything is left.
2. Open `skills/workflow-docs/references/template.md`, then change `max_criteria` in its rules block and run `python3 skills/workflow-docs/scripts/docs.py check`.
   Expect: `CAP` lines that follow the new number. Put it back to 5 afterwards.
3. Open `docs/wiki/Documentation.md`.
   Expect: a `Milestone:` line under the title linking its GitHub milestone.
4. Run `bash dev/toy/test-docs-command.sh`.
   Expect: every line prints PASS and the last line is ALL PASS.

## v0.1.3 - 2026-11-08

- Regression: descriptions, schedule setting, wiki test fix
- Regenerate workflow and wiki tables; guard mine.py
- Merge origin/main into loop/regression-format

### How to verify

1. Open `docs/wiki/Regression.md` and look at the Tests table.
   Expect: columns Criterion, Test, What it checks, Runs, Last result and Seen failing, each row with a plain one-line description.
2. In `.loop/config.json` set `"regression_cron": "5 4 * * 1"`, run `python3 skills/workflow-regression/scripts/regression.py workflow`, then `git diff .github`.
   Expect: the schedule line reads `cron: "5 4 * * 1"`. Set it back to `17 9 * * *` and run it again to restore.
3. After this merges, open the next run of the regression workflow on GitHub.
   Expect: `wiki-release` passes and issue 58 closes with "Passing again".

## v0.1.2 - 2026-11-07

- Run the level 2 design skill through an agent with tools, and say in the pull request how much of it ran
- Add workflow-health, milestones, batches of POCs and goals, and the operation role
- Make the regression workflow pass on GitHub
- Fit the package to Agensi's published rules: a seven-skill pack with its file contract under `shared/`
- Run on Codex at level 0, directly and as a monitored background agent

### How to verify

1. Run `python3 dev/package.py --out dist/agent-workflow-template.zip`, then `unzip -l dist/agent-workflow-template.zip | grep -c SKILL.md`.
   Expect: it prints PASS with a NOTE about `shell=True`, then 7.
2. Run `unzip -l dist/agent-workflow-template.zip | grep loop-files`.
   Expect: one line, `shared/loop-files.md`.
3. Open the repo's Actions tab, pick regression, and choose Run workflow on `main`.
   Expect: the run ends green, and every row prints PASS in its log.
4. Install the ZIP's seven `skills/` folders in an agent, and start one level 0 goal on a test repo.
   Expect: it ends at a pull request.

## v0.1.1 - 2026-11-07

- Add the regression workflow; record the Codex and CI-like runs
- Say what the Codex and CI-like runs proved

### How to verify

1. Open the repo's Actions tab on GitHub, pick regression, and choose Run workflow on `main`.
   Expect: the run ends green, and every row prints PASS in its log.
