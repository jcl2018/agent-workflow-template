# Plan: migration-check-fixes

1. enforce.py: add `scheduled_task`, call it in `task_gaps` before the registry gaps (exists: `task_gaps`, `checks_gaps`).
2. enforce.py: `checks_gaps` skips the pull_request gap when `regression_runs` is mac.
3. dev/toy/test-migration.sh: part `fixes-3780`, four checks (task gap stays with no folder; folder removes it; mac repo asked nothing; actions repo still asked).
4. regression.tsv: `migration-fix-sched-task` and `migration-fix-mac-no-yml`, one per fix. Both bash rows: pending off-platform proofs (they skip on Windows).
5. Docs: Setup and Health pages name the new behaviour.
Could break: a stale empty folder hides a real missing task (accepted; the folder is what the Mac runs). Out of scope: cron of the scheduled task.
