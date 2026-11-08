# Changelog

## v0.1.4 - 2026-11-08

- Operate: `operate.py run` plans queued goals as a dependency graph (`depends-on`, capped by `parallel`) and starts one worker per ready goal
- Workers report live, read the operation session's messages, and bring the latest base into their branch
- Status block with Needs you, Now, Next, Roadmap and Goals; a worker's report wakes operate before its cadence
- Guard `role.py` against git and gh prompts; merge in the regression-format change from main

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
