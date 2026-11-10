# Plan: health-hygiene

From the design in `.loop/designs/health-hygiene.md`, after the plan review (CEO, developer experience and eng
reviews, one round each). The recommended answers keep the design's direction: controls run on every check, and
`lanes.save` records the total. Every other finding that refines the design is folded in below.

## 1. Controls (`skills/workflow-health/scripts/controls.py`)

- `CONTROLS = {rule: (group, rule_id, fixture)}`, keyed by the names in health.py's `RULES` plus the three new rules.
  A control fires only when the rule under test gives a WARN or FAIL row with its own rule id, not UNREAD and not a
  sibling rule's row in the same group.
- Each fixture builds a throwaway repo in `tempfile.TemporaryDirectory()`. Git runs with GIT_DIR, GIT_WORK_TREE and
  GIT_INDEX_FILE unset, `GIT_CONFIG_GLOBAL=/dev/null`, `GIT_CONFIG_NOSYSTEM=1`, and a fixed identity
  (`-c user.name=health-control -c user.email=health-control@example.invalid`), so no hook, signing or global setting
  applies. Fixtures start from the repo's own templates where one exists, so a format change in the real files breaks
  the control.
- health.py passes its rule functions into `controls.run(rules, here)`; controls.py imports nothing from health.py.
  `LOOP_HEALTH` and other overrides go only to the child environment, never into `os.environ`.
- Rows: PASS `controls <rule> fires`; FAIL `cannot fire` with the fix "the rule <fn> no longer reports its fixture:
  run controls.py run <rule> --keep to see it"; UNREAD with the failing command, its exit code and the last stderr
  line. Rows never contain temp paths or times, so two runs print the same lines. A cleanup failure is UNREAD naming
  the leftover.
- A rule in `RULES` with no control: health.py prints `REFUSED: rule <name> has no negative control. Fix: add
  CONTROLS["<name>"] in controls.py` and exits 2 (not 1, so it reads as a broken install, not a red repo).
- `check --skip controls` skips the group; `controls.py run <rule> [--keep]` runs one control and prints the fixture
  path when kept.

## 2. Test time (`lean.py`, `lanes.py`, `judge.py`)

- `lanes.save` writes `total_seconds`. `lean.py` reads the lane record JSON directly (not `lanes.load`, which rejects
  other worktrees): the current branch's record, else the newest record under the git common folder's `loop/tests/`
  with a readable `at`. It counts only rows that are `land` rows in the current `.loop/regression.tsv`, and sums
  their seconds when `total_seconds` is missing. An unreadable record is UNREAD naming it; no record is INFO.
- Over `test_budget_seconds` (default 600): one WARN naming the setting, the total, and the five slowest rows, plus the
  slowest scripts (rows grouped by the toy script they run).
- `judge.py` adds the land total and the slowest rows to its performance facts.

## 3. Stale worktrees and branches (`lean.py`)

- Loop worktrees under the git common folder's `loop/worktrees/` only, matched by realpath. Live: a run names it with
  status running, waiting, failed or stopped, or done with a release other than `merged`, `cut` or `leave`. A retired
  run, a merged run or no run is stale. Locked or dirty worktrees are reported as such, with the note that the command
  refuses; a missing directory gets `git worktree prune`.
- Branches with no upstream, or an upstream marked gone, not checked out anywhere, not current, not merged into the
  base, older than `stale_branch_days` (default 14). N = `git rev-list --count <b> --not --remotes`; the data-loss
  warning prints only when N > 0.
- One WARN per kind with the count and the first five names and commands, then "and K more"; the full list in
  `--json`. Every command is shell-quoted.
- These rows are report-only: file.py never files `worktrees`, `local-branches` or `test-time`, because they hold
  machine-local paths and names.

## 4. Wiring, docs and tests

- health.py: the new rules in `RULES` (MAX_RULES raised, with the reason), the docstring, the `controls` group in the
  fixed order, `--skip`. report.py: the new rules in its rules table.
- Settings `test_budget_seconds` and `stale_branch_days` in the settings reference.
- Health PRD: HLT-6 Unreviewed in the done line's wording, then recorded Reviewed with the owner's quoted approval;
  Given/When/Then scenarios for each done line, linked to their rows.
- `dev/toy/test-health-hygiene.sh`: for each part a bad fixture that fires and a clean one that stays quiet, the load
  refusal, the report-only filing, and the controls group's time. Rows in `.loop/regression.tsv`, seen failing once.

Checks per done line: 1 and 6 by `docs.py check` and the PRD scenarios; 2 to 5 by the toy test rows.
