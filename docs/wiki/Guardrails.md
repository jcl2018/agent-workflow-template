<!-- workflow-docs -->
# Guardrails

Milestone: https://github.com/jcl2018/agent-workflow-template/milestone/11

Review: **Unreviewed**

## Problem

- My guardrails are scattered across six features, some are promised but not built, and I can't see in one place what protects me, where it is enforced and whether it is on.
- Runs can quietly cost too much: CI minutes on superseded or no-code runs, a step spending far more tokens than usual, a run going far longer than usual.
- I want one set of guardrails that the health checks prove are on and that every adopted repo gets, each one showing what it protects against, where it lives and the setting that controls it.

## Usage

- `/workflow-health check [--group NAME] [--skip controls] [--json]` — Runs the fixed rules, among them the one per guardrail that proves it is on (GRD-9); the Health page holds the whole entry. Prints one line per finding and last `HEALTH: green|not green (<p> pass, <w> warn, <f> fail, <u> unread)`; exits 1 when not green. Refuses what the Health page lists.
- `/workflow-setup settings` — Shows the settings reference: every setting with its home, default and meaning. Prints the reference as a Markdown table, one `| <setting> | <home> | <default> | <meaning> |` row per setting. Refuses nothing. This repo's `.loop/config.json` holds every setting the reference lists, with `template_version` naming the template it came from.

## Requirements

### Functional

- GRD-1: **Unreviewed** One visible set of guardrails, each with its protection, owner, setting and health check
  - This page is an index: it lists every guardrail the template has or needs, each with what it protects against, where it is enforced, the setting that controls it and the health rule that proves it is on.
  - Each guardrail points to the requirement id that owns it (DEL-8, REG-7, DEL-9, SET-8, MON-7, MON-8) and says "new" where none does yet; the page restates none of the owner's text, which holds the exact wording.
  - A guardrail counts as on only when its Tests row here passes; until then it reads not enforced.
- GRD-2: **Unreviewed** Time and token budgets stop a goal or a step before it runs away
  - Review and ship step time limit: DEL-8.
  - In-loop test run time limit: REG-7.
  - The work before a lane's first test row (preparing, planning and waiting for a slot) stops at `prep_budget_minutes` (default 15, never under 15; this repo sets 25); the lane says which part ran long and the goal can rerun it (Delivery, Regression).
  - A goal past `time_budget_minutes` starts no new step, and the setting is in the settings reference with its default (Delivery, new).
  - A goal past `token_budget` starts no new step, whether its steps run in a session or headless (Delivery, DEL-8 for showing it on the board; new for steps run in a session: today only headless goals are refused).
  - A goal with no token count records "unknown" and the board shows "tokens unread", never 0, so an unread count is never mistaken for an unspent budget (Delivery, new).
- GRD-3: **Unreviewed** Nothing private is committed, and no commit skips the hooks that check it
  - Private-name scan on every commit and push: DEL-9.
  - A commit or push that skips the repo's hooks (a no-verify flag, an empty hooks path) is refused by the loop's own commands and flagged by health (Delivery, new).
  - Where the scanned names live: SET-8 (SET-2 for the private layer).
- GRD-4: **Unreviewed** A worker writes only its own goal's work, never shared loop state or its own limits
  - A worker can't widen its own goal's touches, resume itself or change its own budget; only the operation session can (Delivery, new: today a role check, not a boundary).
  - A worker changes shared loop state only for its own goal and only through the goal's commands (`goal.py step`, `record` and `pr`, `sessions.py bind` and `report`); the queue, other goals' run records and the session pool's other sessions are the operation session's to change (Monitoring, new: today the commands scope a worker to its own slug, and nothing stops a hand edit).
  - The operation session never edits code, commits or pushes: MON-7.
- GRD-5: **Unreviewed** Nothing is written to GitHub without an explicit `--live`
  - Every command that writes issues, comments, milestones or releases previews by default and writes only behind an explicit `--live` switch; a token in the environment does not turn writing on (Health, HLT-4, REG-5 and AUT-5 hold the wording; Regression new: today it writes whenever a token is present).
  - The scheduled workflows pass `--live`; the page of each such command says so (each owner, new).
- GRD-6: **Unreviewed** The base branch is protected and merges only with its required checks green
  - The base branch refuses direct pushes and force pushes, and a pull request merges only when the repo's required checks pass; I set those rules on the platform, and setup never edits a ruleset or branch protection (it names, as BLOCKS, a required check no commit status can satisfy: Setup, SET-1).
  - Where the platform can enforce it (branch rules, required status checks), the platform does, and health reads that it is set (Health, new).
- GRD-7: **Unreviewed** CI spends minutes only on runs that matter, and too many runs raise an alarm
  - A newer run of the same workflow on the same branch cancels the one it supersedes (Automation, new: the workflows queue runs today).
  - A heavy job is skipped for a change that touches no code, such as docs only (Automation, new).
  - Each round shows its Actions minutes and goes over its limit loudly (Automation, AUT-7); runs or minutes per day past a set limit raise one alarm (Automation, new).
- GRD-8: **Unreviewed** A step far past its usual tokens or time is flagged while it runs
  - A step whose tokens pass a set multiple of that step's usual is flagged on the board and in the check-in (Monitoring, new).
  - A step past three times its estimate is shown as stalled under Issues on the board (Monitoring, MON-4, which keeps a stuck worker at the top of Issues), and a worker silent past `silent_minutes` shows under Needs you: MON-8.
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
| [reg7-budget-leaves](Tests#t-reg7-budget-leaves) | requirement | GRD-2 | Given rows that would run past the test budget, when a loop test run happens, then it runs the rows that fit, stops at the budget and lists every row it left. | not run |
| [del8-step-stops](Tests#t-del8-step-stops) | requirement | GRD-2 | Given a review or ship step that reaches its limit, when it is stopped, then it is recorded done with what it left and the goal goes on without a failed try. | not run |
| - | requirement | GRD-2 | no passing test | not enforced |
| [del9-pr-refuses](Tests#t-del9-pr-refuses) | requirement | GRD-3 | Given a branch that adds a private name from the list, when goal.py pr runs, then nothing is pushed and the refusal names the place, never the text. | not run |
| [del9-hooks](Tests#t-del9-hooks) | requirement | GRD-3 | Given the pre-push hook and a branch whose commit holds a private line, when it is pushed, then the hook refuses naming file and line, and nothing reaches the remote. | PASS 2026-11-12 |
| - | requirement | GRD-4 | no passing test | not enforced |
| - | requirement | GRD-5 | no passing test | not enforced |
| - | requirement | GRD-6 | no passing test | not enforced |
| - | requirement | GRD-7 | no passing test | not enforced |
| - | requirement | GRD-8 | no passing test | not enforced |
| - | requirement | GRD-9 | no passing test | not enforced |
| - | requirement | GRD-10 | no passing test | not enforced |
| [stop-tree-step-limit](Tests#t-stop-tree-step-limit) | defect | [#1396](https://github.com/jcl2018/agent-workflow-template/issues/1396) closed (2026-11-12) | Given a step or lane past its time limit, when it is stopped on any platform, then its whole process tree goes with it. | not run |
