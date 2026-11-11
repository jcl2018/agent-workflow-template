<!-- workflow-docs -->
# Guardrails

Milestone: https://github.com/jcl2018/agent-workflow-template/milestone/11

Review: **Unreviewed**

## Problem

- My guardrails are scattered across six features, some are promised but not built, and I can't see in one place what protects me, where it is enforced and whether it is on.
- Runs can quietly cost too much: CI minutes on superseded or no-code runs, a step spending far more tokens than usual, a run going far longer than usual.
- I want one set of guardrails that the health checks prove are on and that every adopted repo gets, each one showing what it protects against, where it lives and the setting that controls it.

## Usage

- `/workflow-health check [--group NAME] [--skip controls] [--json]` — Runs the fixed rules and prints one line per finding, then the verdict. Prints `HEALTH REPORT`, then `<STATE> <group> <subject> <rule>: <detail>` per row, and last `HEALTH: green|not green (<p> pass, <w> warn, <f> fail, <u> unread)` (with `--json`, one object with green, counts, rows and verdict); exits 1 when not green. Refuses (exit 1) `REFUSED: unknown group <names>. Groups: ...` and `REFUSED: not inside a git repo.`; (exit 2) `REFUSED: --skip leaves no group to check` and `REFUSED: rule <name> has no negative control. ...`
- `/workflow-setup settings` — Shows the settings reference: every setting with its home, default and meaning. Prints the reference as a Markdown table, one `| <setting> | <home> | <default> | <meaning> |` row per setting. Refuses nothing.

## Requirements

### Functional

- GRD-1: **Unreviewed** One visible set of guardrails, each with its protection, owner, setting and health check
  - This page lists every guardrail the template has or needs, each with what it protects against, where it is enforced, the setting that controls it and the health rule that proves it is on.
  - Each part names the feature that owns it, by its requirement ID where one exists, and "new" where none does yet; this page never restates an owner's rule in different words.
  - A guardrail counts as on only when its Tests row here passes; until then it reads not enforced.
- GRD-2: **Unreviewed** Time and token budgets stop a goal or a step before it runs away
  - A review or ship step stops at `step_budget_minutes` (default 30, never under 15), finishes with what it has done and records what it left (Delivery, DEL-8).
  - An in-loop test run stops at `test_budget_minutes` (default 15, never under 15) and leaves the rest to the scheduled full suite (Regression, REG-7).
  - A goal past `time_budget_minutes` starts no new step, and the setting is in the settings reference with its default (Delivery, new).
  - A goal past `token_budget` starts no new step, whether its steps run in a session or headless (Delivery, DEL-8).
- GRD-3: **Unreviewed** Nothing private is committed, and no commit skips the hooks that check it
  - Every commit and push passes the private-name scan before it leaves the machine (Delivery, DEL-9; Setup, SET-8).
  - A commit or push that skips the repo's hooks (a no-verify flag, an empty hooks path) is refused by the loop's own commands and flagged by health (Delivery, new).
  - The names the scan looks for live only in a private setting, never in the repo (Setup, SET-2).
- GRD-4: **Unreviewed** A worker writes only its own goal's work, never shared loop state or its own limits
  - A worker can't widen its own goal's touches, resume itself or change its own budget; only the operation session can (Delivery, new: today a role check, not a boundary).
  - Shared loop state (run records, the session pool, the queue) is written only by the operation session or the main checkout, never from a goal's worktree (Monitoring, new).
  - The operation session never edits code, commits or pushes (Monitoring, MON-7).
- GRD-5: **Unreviewed** Nothing is written to GitHub without an explicit confirm
  - Every command that writes issues, comments, milestones or releases previews by default and writes only when told to (Regression, REG-5; Health, HLT-4; Automation, AUT-5).
  - The page of each such command says which flag or environment token turns writing on.
- GRD-6: **Unreviewed** The base branch is protected and merges only with its required checks green
  - The base branch refuses direct pushes and force pushes, and a pull request merges only when the repo's required checks pass (Setup, new).
  - Where the platform can enforce it (branch rules, required status checks), the platform does, and health reads that it is set (Health, new).
- GRD-7: **Unreviewed** CI spends minutes only on runs that matter, and too many runs raise an alarm
  - A newer run of the same workflow on the same branch cancels the one it supersedes (Automation, new: the workflows queue runs today).
  - A heavy job is skipped for a change that touches no code, such as docs only (Automation, new).
  - Each round shows its Actions minutes and goes over its limit loudly (Automation, AUT-7); runs or minutes per day past a set limit raise one alarm (Automation, new).
- GRD-8: **Unreviewed** A step far past its usual tokens or time is flagged while it runs
  - A step whose tokens pass a set multiple of that step's usual is flagged on the board and in the check-in (Monitoring, new).
  - A step or run far past its usual time is shown as stalled on the board (Monitoring, MON-4), and a worker silent past `silent_minutes` (default 30) shows under Needs you (Monitoring, MON-8).
  - A goal's test lane past `goal_lane_minutes` (default 10) says so in its LANE line (Regression, REG-8).
- GRD-9: **Unreviewed** Health proves every guardrail is present and working, each rule with a negative control
  - Each guardrail has a health rule that reads whether it is present and working, in a named group (Health, HLT-2).
  - Each such rule has a negative control run against a deliberately broken copy, so it is known to fire (Health, HLT-2, Controls).
  - A guardrail its rule can't read shows as unread, never as passing (Health, HLT-3).
- GRD-10: **Unreviewed** Setup installs the whole set when a repo is adopted, and health judges it
  - Adopting a repo installs every guardrail on this page with its default setting, and setup lists each one it installed (Setup, SET-1).
  - Health judges a freshly adopted repo's guardrails on the same rules as the template's (Setup, SET-6).

### Non-functional

None

## Non-goals

- No code here: each guardrail is built by its owner feature's own goal; this page only defines the set.
- This page never says a guardrail is on; the Tests table does, from passing regression rows.

## Success metrics

- Every guardrail is on this page with its owner, setting and health check, and none is described anywhere else in different words.
- Each guardrail's Tests row passes.
- A freshly adopted repo has every guardrail on with its default setting.

## Tests

| Test | Kind | Guards | Checks | Last result |
|---|---|---|---|---|
| - | requirement | GRD-1 | no passing test | not enforced |
| - | requirement | GRD-2 | no passing test | not enforced |
| - | requirement | GRD-3 | no passing test | not enforced |
| - | requirement | GRD-4 | no passing test | not enforced |
| - | requirement | GRD-5 | no passing test | not enforced |
| - | requirement | GRD-6 | no passing test | not enforced |
| - | requirement | GRD-7 | no passing test | not enforced |
| - | requirement | GRD-8 | no passing test | not enforced |
| - | requirement | GRD-9 | no passing test | not enforced |
| - | requirement | GRD-10 | no passing test | not enforced |
