# Changelog

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
