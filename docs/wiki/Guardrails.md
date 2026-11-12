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
- `/workflow-setup settings` — Shows the settings reference: every setting with its home, default and meaning. Prints the reference as a Markdown table, one `| <setting> | <home> | <default> | <meaning> |` row per setting. Refuses nothing. This repo's `.loop/config.json` holds every setting the v0.27.17 template update writes, with `template_version` naming the template it came from.

## Requirements

### Functional

- GRD-1: **Unreviewed** One visible set of guardrails, each with its protection, owner, setting and health check
  - This page must list every guardrail the template has or needs, each with what it protects against, where it is enforced, the setting that controls it and the health rule that proves it is on.
  - Each part names the feature that owns it, by its requirement ID where one exists, and "new" where none does yet; the owner's requirement holds the exact wording.
  - A guardrail counts as on only when its Tests row here passes; until then it reads not enforced.
- GRD-2: **Unreviewed** Time and token budgets stop a goal or a step before it runs away
  - A review or ship step stops at `step_budget_minutes` (default 30, never under 15), finishes with what it has done and records what it left (Delivery, DEL-8).
  - An in-loop test run stops at `test_budget_minutes` (default 15, never under 15) and leaves the rest to the scheduled full suite (Regression, REG-7).
  - The work before a lane's first test row (preparing, planning and waiting for a slot) stops at `prep_budget_minutes` (default 15, never under 15; this repo sets 25); the lane says which part ran long and the goal can rerun it (Delivery, Regression).
  - A goal past `time_budget_minutes` starts no new step, and the setting is in the settings reference with its default (Delivery, new).
  - A goal past `token_budget` starts no new step, whether its steps run in a session or headless (Delivery, DEL-8 for showing it on the board; new for steps run in a session: today only headless goals are refused).
- GRD-3: **Unreviewed** Nothing private is committed, and no commit skips the hooks that check it
  - Every commit and push passes the private-name scan before it leaves the machine (Delivery, DEL-9).
  - A commit or push that skips the repo's hooks (a no-verify flag, an empty hooks path) is refused by the loop's own commands and flagged by health (Delivery, new).
  - The names the scan looks for live only in a private setting, never in the repo (Setup, SET-8; SET-2 for the private layer).
- GRD-4: **Unreviewed** A worker writes only its own goal's work, never shared loop state or its own limits
  - A worker can't widen its own goal's touches, resume itself or change its own budget; only the operation session can (Delivery, new: today a role check, not a boundary).
  - Shared loop state (run records, the session pool, the queue) is written only by the operation session or the main checkout, never from a goal's worktree (Monitoring, new).
  - The operation session never edits code, commits or pushes (Monitoring, MON-7).
- GRD-5: **Unreviewed** Nothing is written to GitHub without an explicit confirm
  - Every command that writes issues, comments, milestones or releases previews by default and writes only when told to (Health, HLT-4; Regression and Automation, new: today REG-5 and AUT-5 write whenever a token is present).
  - The page of each such command says which flag or environment token turns writing on (each owner, new).
- GRD-6: **Unreviewed** The base branch is protected and merges only with its required checks green
  - The base branch refuses direct pushes and force pushes, and a pull request merges only when the repo's required checks pass (Setup, new).
  - Where the platform can enforce it (branch rules, required status checks), the platform does, and health reads that it is set (Health, new).
- GRD-7: **Unreviewed** CI spends minutes only on runs that matter, and too many runs raise an alarm
  - A newer run of the same workflow on the same branch cancels the one it supersedes (Automation, new: the workflows queue runs today).
  - A heavy job is skipped for a change that touches no code, such as docs only (Automation, new).
  - Each round shows its Actions minutes and goes over its limit loudly (Automation, AUT-7); runs or minutes per day past a set limit raise one alarm (Automation, new).
- GRD-8: **Unreviewed** A step far past its usual tokens or time is flagged while it runs
  - A step whose tokens pass a set multiple of that step's usual is flagged on the board and in the check-in (Monitoring, new).
  - A step past three times its estimate is shown as stalled under Issues on the board (Monitoring, new; MON-4 keeps a stuck worker at the top of Issues), and a worker silent past `silent_minutes` (default 30) shows under Needs you (Monitoring, MON-8).
  - A goal's test lane past `goal_lane_minutes` (default 10) says so in its LANE line (Regression, REG-8).
- GRD-9: **Unreviewed** Health proves every guardrail is present and working, each rule with a negative control
  - Each guardrail has a health rule that reads whether it is present and working, in an existing group (Performance, Security and privacy, Hygiene or Adoption), within the cap of 12 groups (Health, HLT-2).
  - Each such rule has a negative control run against a deliberately broken copy, so it is known to fire (Health, HLT-2, Controls).
  - A guardrail its rule can't read shows as unread, never as passing (Health, HLT-3).
- GRD-10: **Unreviewed** Setup installs the whole set when a repo is adopted, and health judges it
  - Adopting a repo installs every guardrail on this page with its default setting, and setup lists each one it installed (Setup, SET-1 for installing; listing each one is new).
  - Health judges a freshly adopted repo's guardrails on the same rules as the template's (Setup, SET-1).

### Non-functional

None

## Non-goals

- No code here: each guardrail is built by its owner feature's own goal; this page only defines the set.
- This page never says a guardrail is on; the Tests table does, from passing regression rows.

## Success metrics

- Every guardrail is on this page with its owner, setting and health check, each pointing to its owner's requirement for the exact wording.
- Each guardrail's Tests row passes.
- A freshly adopted repo has every guardrail on with its default setting.

## Tests

| Test | Kind | Guards | Checks | Last result |
|---|---|---|---|---|
| - | requirement | GRD-1 | no passing test | not enforced |
| [grd2-step-budget](Tests#t-grd2-step-budget) | requirement | GRD-2 | Given a review or ship step that reaches step_budget_minutes, when it is stopped, then it records done with what it left and costs no failed try. | not run |
| [grd2-test-budget](Tests#t-grd2-test-budget) | requirement | GRD-2 | Given an in-loop test run that reaches test_budget_minutes, when it stops, then it runs rows in order until the budget and lists the rest for the scheduled full suite. | not run |
| [grd2-goal-over](Tests#t-grd2-goal-over) | requirement | GRD-2 | Given a goal past its time and token budget, when the live board prints, then it flags OVER time and OVER tokens. | not run |
| - | requirement | GRD-2 | no passing test | not enforced |
| [grd3-private-commit](Tests#t-grd3-private-commit) | requirement | GRD-3 | Given a staged line holding a private name, when git commit runs with the installed hook, then it is refused naming the file and line and the commit does not happen. | not run |
| [grd3-hooks-health](Tests#t-grd3-hooks-health) | requirement | GRD-3 | Given a repo with the private-name hooks installed, when health runs, then it passes the hooks rule. | not run |
| - | requirement | GRD-3 | no passing test | not enforced |
| [grd4-touches](Tests#t-grd4-touches) | requirement | GRD-4 | Given a worker session, when it tries to widen its goal's touches, then the command refuses. | not run |
| [grd4-resume](Tests#t-grd4-resume) | requirement | GRD-4 | Given a stopped goal, when its own worker tries to resume it, then the command refuses with WORKER_SELF_REPAIR. | not run |
| [grd4-budget](Tests#t-grd4-budget) | requirement | GRD-4 | Given a worker session, when it tries to set its own goal's budget, then the command refuses. | not run |
| [grd4-govern](Tests#t-grd4-govern) | requirement | GRD-4 | Given the operation session governing goals, when workers build, then the governing checkout gets no commit. | not run |
| - | requirement | GRD-4 | no passing test | not enforced |
| [grd5-regression-dry](Tests#t-grd5-regression-dry) | requirement | GRD-5 | Given no token, when the regression run reaches an issue write, then it is a dry run and makes no gh call. | not run |
| [grd5-health-close](Tests#t-grd5-health-close) | requirement | GRD-5 | Given open findings, when triage close runs without --yes, then it lists them and writes nothing. | not run |
| - | requirement | GRD-5 | no passing test | not enforced |
| [grd6-head-moved](Tests#t-grd6-head-moved) | requirement | GRD-6 | Given a pull request head that moved since its checks ran, when the release merges, then it is refused with HEAD_MOVED and nothing is merged. | not run |
| - | requirement | GRD-6 | no passing test | not enforced |
| [grd7-round-cost](Tests#t-grd7-round-cost) | requirement | GRD-7 | Given a scheduled round, when its digest is posted, then the round cost shows its minutes and Actions minutes. | not run |
| - | requirement | GRD-7 | no passing test | not enforced |
| [grd8-silent-worker](Tests#t-grd8-silent-worker) | requirement | GRD-8 | Given a worker silent past silent_minutes, when the board prints, then it shows under Needs you. | not run |
| - | requirement | GRD-8 | no passing test | not enforced |
| [grd9-controls](Tests#t-grd9-controls) | requirement | GRD-9 | Given every health rule, when the controls run on broken copies, then each rule fires. | not run |
| - | requirement | GRD-9 | no passing test | not enforced |
| [grd10-install-hooks](Tests#t-grd10-install-hooks) | requirement | GRD-10 | Given a repo being adopted, when setup runs by default, then it installs the three private-name hooks after its commit. | not run |
| - | requirement | GRD-10 | no passing test | not enforced |
| [stop-tree-step-limit](Tests#t-stop-tree-step-limit) | defect | [#1396](https://github.com/jcl2018/agent-workflow-template/issues/1396) open (2026-11-12) | Given a step or lane past its time limit, when it is stopped on any platform, then its whole process tree goes with it. | not run |
