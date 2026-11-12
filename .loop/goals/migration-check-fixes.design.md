# Design: migration-check-fixes (#3780)

Two false gaps from the Mac's read-only run.
1. `enforce.task_gaps` reads only the launch agent's `repos.json`. Add `scheduled_task(label)`: true when a folder named `<repo>-health-regression` exists under `~/.claude/scheduled-tasks` or `~/Documents/Claude/Scheduled` (`LOOP_SCHEDULED_TASKS_DIR` replaces both, for the toy). When true, no MIG_TASK gap.
2. `enforce.checks_gaps` asks `regression.yml` for `pull_request` even for `regression_runs: mac`. AUT-2: the PR lane posts the statuses itself. Ask only when `regression_runs` is not mac.
Out of scope: reading a scheduled task's cron; the launch-agent registry path is unchanged.
