# Plan: health-repo-rules

Checked against the code in this worktree (origin/main b3049c80): the functions below exist, and `issues.feature_of`
already returns an item's own `feature`, so filing needs no change.

## Build steps

1. `skills/workflow-health/scripts/enforce.py`: pull Mine's command loop into `run_rule(root, rule, name, group)`, then add
   `repo_file(root)` (load `.loop/health-rules.json`, validate: names unique and not a default rule, a `break` on every rule,
   a known `group`, `off` reasons), `repo_rows(root)` (the rows, each with its group and `feature`; an invalid file or rule is
   UNREAD) and `off_rows(root)`.
2. `skills/workflow-health/scripts/report.py`: a `repo` heading beside Mine (not one of the twelve; `MAX_GROUPS` stays 12),
   shown before Mine, skipped as "no repo rules" when the file has none.
3. `skills/workflow-health/scripts/health.py`: `gather` adds the repo rows to their groups, leaves a turned-off rule out
   with its INFO row, `size_rows` reads `health_script_bytes`; `controls_rows` adds one control per repo rule; the
   missing-break refusal (exit 2) beside the missing-control one.
4. `skills/workflow-health/scripts/controls.py`: `repo_control(root, rule)` copies the tracked files, runs `break` then the
   command there, and returns the Controls row.
5. `skills/workflow-health/scripts/rules.py`: `skill_lines` reads `health_skill_lines`.
6. `skills/workflow-setup/scripts/settings.py`: TABLE rows `health_script_bytes` and `health_skill_lines`; `fill_repo` writes
   the empty commented `.loop/health-rules.json`; references/settings.md regenerated.
7. Docs: the Health page usage and `skills/loop-files.md` describe the file; requirements wording is worker 10's.
8. Toy `dev/toy/test-health-repo-rules.py` (Python, `# windows: ok`) with `--break`; its regression rows for the done line,
   each seen red.

## Test for the done line (health-repo-rules:1)

- repo-rules-run: pass/warn/fail/unread rules appear in the report with their group and feature.
- repo-rules-control: a working `break` fires the control; a `break` that changes nothing is reported as unable to fire;
  a rule with no `break` refuses (exit 2).
- repo-rules-off: a default turned off prints its reason; an empty reason leaves the rule on and UNREAD.
- repo-rules-thresholds: a larger `health_script_bytes` clears a script that failed at the default.
- repo-rules-setup: `fill-repo` writes the file once and keeps an edited one.

## What could break

enforce.py, health.py and rules.py are near the 20,480 byte cap, and health-v1 and backlog-milestones edit the same scripts, so
this merges after them and re-checks the sizes. Mine's behaviour must not change (the existing enforce toy covers it).

## Out of scope

The requirement wording on Health.md (worker 10), the defect/backlog filing and milestones (workers 10 and 13), a new file under skills/.
