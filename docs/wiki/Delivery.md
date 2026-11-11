<!-- workflow-docs -->
# Delivery

Milestone: https://github.com/jcl2018/agent-workflow-template/milestone/1

Review: **Unreviewed**

## Problem
- I have more changes to make than time to babysit them: I want to hand over one sentence and walk away.
- Without a loop, a change stalls at whatever step I stopped watching: no review, no tests, no release.
- I need every change to arrive the same way: reviewed, tested, documented and released, with a record of what happened.

## Usage
- `goal.py new "GOAL" --done "LINE" [--done "LINE" ...] [--here]` — Freezes a goal and its done lines. Prints `FROZEN slug`. Refuses with no done line (exit 2, `REFUSED: a goal needs at least one done line`) or with no skill flow set up (exit 2).
- `flow.py SLUG STEP` — Runs one step (idea, plan, review, qa, ship); a review or ship step stops at `step_budget_minutes` (default 30, never under 15), is recorded done with what it left and the goal goes on. In a worker session prints `IN SESSION` and the skill to run. Prints `RUNNING` until it ends.
- `goal.py record SLUG STEP --in-session` — Records a finished step. Refuses a reply with no `DEPTH:` line, and a qa step with no passing lane on HEAD (`LANE_MISSING`).
- `goal.py pr SLUG` — Merges the latest main, reruns the affected tests within `test_budget_minutes` (default 15, never under 15; rows past it are left to the scheduled full suite and listed), pushes and opens the pull request. Prints the PR link. Never merges.
- `merge.py SLUG` — The release step: docs check, merge (where auto_merge is on), version bump, changelog, GitHub release, wiki publish. Prints `MERGED <pr> into main`, `RELEASED vX.Y.Z <release link> (<bump> bump)` and `PUBLISHED <wiki link>`. Refuses while a page is stale.

## Requirements

### Functional
- DEL-1: **Reviewed 2026-11-08** The loop <!-- reviewed b5b65da9 -->
  - I give one sentence and its done lines; a worker runs it unattended.
  - Steps, in order: freeze, idea, plan, build, review, qa, ship, pull request, release.
  - Review is the only gate.
  - Each step maps to a skill I choose, in a private setting outside the repo.
  - It won't start without the flow set up, and stops with a reason after 3 failed tries.
- DEL-3: **Reviewed 2026-11-08** Decisions <!-- reviewed 48b4ed7f -->
  - A decision for me waits under Needs you, or, where the repo allows, is auto-approved and logged.
- DEL-4: **Reviewed 2026-11-08** The pull request <!-- reviewed 7cc0d031 -->
  - Carries the done lines, the plan, how to verify by hand, and each step's result.
- DEL-5: **Reviewed 2026-11-10** Release <!-- reviewed 17f0ff96 -->
  - Every goal ends with release, fully automatic, with no draft step.
  - It bumps the version, writes the release note, and refuses to merge while a page is stale.
  - The bump is patch by default; minor or major only when the goal says so.
  - It runs my routines, merges where allowed and publishes the wiki.
  - Any failure shows under Needs you.
- DEL-6: **Reviewed 2026-11-10** Review depth fits the goal <!-- reviewed e7ac89a1 -->
  - Small goals (up to 3 done lines, one skill) run a condensed plan and review.
  - Larger goals run full depth; I can override it per goal.
  - Tests never shrink: every goal runs its full test lane.

### Non-functional
- DEL-2: **Reviewed 2026-11-08** Frozen done lines <!-- reviewed c810cac8 -->
  - Done lines can't change once the goal starts; a change means a new goal.
- DEL-7: **Reviewed 2026-11-10** Resumable <!-- reviewed 0f9f447b -->
  - A stopped or crashed goal resumes from its last recorded step, never from the start.
- DEL-8: **Unreviewed** Budgeted
  - Each goal has a time and token budget, and going over shows on the board.
  - Each review and ship step has a time limit, a setting no lower than 15 minutes; a step that reaches it finishes with what it has done, records what it left, and the goal goes on instead of restarting.
  - A lane that stops at its preparation budget is recorded on the goal with the part that ran long, and the board and health list it beside the step and test budget hits.
- DEL-9: **Reviewed 2026-11-10** Nothing private ships <!-- reviewed ad7ed0f0 -->
  - Every commit and pull request passes the private-name scan before it is pushed.

## Non-goals
- It doesn't decide what to build.
- It never changes a done line once started.
- It doesn't run several goals at once (Monitoring does).

## Success metrics
- Every merged pull request carries its done lines, plan, verify steps and step results.
- A goal that fails three tries stops and says why.
- No goal merges while a wiki page is stale.

## Tests

| Test | Kind | Guards | Checks | Last result |
|---|---|---|---|---|
| [no-done-line-refused](Tests#t-no-done-line-refused) | requirement | DEL-1 | Given a goal with no done line, when it is started, then it is refused. | PASS 2026-11-11 |
| [no-flow-refused](Tests#t-no-flow-refused) | requirement | DEL-1 | Given no skill flow is set, when a goal is started, then it does not start. | PASS 2026-11-11 |
| [stop-after-3-tries](Tests#t-stop-after-3-tries) | requirement | DEL-1 | Given a goal, when three tries fail, then the goal stops and files a finding. | PASS 2026-11-09 |
| [pr-needs-flow](Tests#t-pr-needs-flow) | requirement | DEL-1 | Given a flow step not yet done, when a pull request is opened, then it is refused. | PASS 2026-11-09 |
| [starts-at-idea](Tests#t-starts-at-idea) | requirement | DEL-1 | Given a new goal, when it starts, then it starts at the idea step. | PASS 2026-11-09 |
| [steps-through-flow](Tests#t-steps-through-flow) | requirement | DEL-1 | Given a step reply, when it is recorded, then it is accepted only if the flow ran that step. | PASS 2026-11-09 |
| [no-prompts](Tests#t-no-prompts) | requirement | DEL-1 | Given any tool, when it runs, then it never waits on a terminal prompt. | PASS 2026-11-11 |
| [defect-flow-steps](Tests#t-defect-flow-steps) | requirement | DEL-1 | Given the flow, when it is checked, then it has no checks step and every step can be mapped, with a default suite and overrides. | PASS 2026-11-11 |
| [depth-condensed-refused](Tests#t-depth-condensed-refused) | requirement | DEL-1 | Given review_depth full, when a plan or review reply says it ran condensed, then it is refused with no try used. | PASS 2026-11-10 |
| [depth-auto-approve-gate](Tests#t-depth-auto-approve-gate) | requirement | DEL-1 | Given review_depth full and auto-approve on, when a condensed review leaves a gate, then it is refused, not approved. | PASS 2026-11-10 |
| [depth-markers](Tests#t-depth-markers) | requirement | DEL-1 | Given private evidence markers, when a full review reply lacks one, then it is refused with no try used, without showing the marker. | PASS 2026-11-10 |
| [depth-recorded](Tests#t-depth-recorded) | requirement | DEL-1 | Given the default setting, when a goal runs its steps, then every recorded step names the depth it ran. | PASS 2026-11-10 |
| [depth-condensed-when-set](Tests#t-depth-condensed-when-set) | requirement | DEL-1 | Given review_depth condensed on the base branch, when a review runs condensed, then it is recorded as condensed. | PASS 2026-11-10 |
| [depth-base-branch](Tests#t-depth-base-branch) | requirement | DEL-1 | Given review_depth full on the base branch, when a worker sets condensed in its own worktree, then it is still held to full. | PASS 2026-11-10 |
| [depth-loop-flow](Tests#t-depth-loop-flow) | requirement | DEL-1 | Given markers in the default flow file, when LOOP_FLOW points elsewhere, then the markers still apply. | PASS 2026-11-10 |
| [guards-extra](Tests#t-guards-extra) | requirement | DEL-1 | Given a stopped or waiting goal, when answer, record or a second reservation comes in, then answer refuses a stopped goal, a waiting goal can't advance, and two goals can't take one session. | PASS 2026-11-10 |
| [pending-waits](Tests#t-pending-waits) | requirement | DEL-3 | Given a step that leaves a decision for the owner, when it ends, then the goal stops and waits. | PASS 2026-11-11 |
| [auto-approved](Tests#t-auto-approved) | requirement | DEL-3 | Given an auto-approved step, when it ends, then it is logged and nothing waits. | PASS 2026-11-09 |
| [cut-needs-verify](Tests#t-cut-needs-verify) | requirement | DEL-4 | Given no Verify by hand steps, when a release is cut, then it is refused. | PASS 2026-11-11 |
| [pr-body-criterion](Tests#t-pr-body-criterion) | requirement | DEL-4 | Given a pull request, when its body is written, then it carries the goal, the done lines, the verify steps and each step's result. | PASS 2026-11-11 |
| [depth-in-pr-body](Tests#t-depth-in-pr-body) | requirement | DEL-4 | Given a goal whose steps are recorded, when its pull request opens, then the body lists every step with its depth. | PASS 2026-11-10 |
| [never-merges](Tests#t-never-merges) | requirement | DEL-5 | Given auto_merge is off, when goals finish, then nothing is merged. | PASS 2026-11-09 |
| [wiki-release](Tests#t-wiki-release) | requirement | DEL-5 | Given a merged goal, when the release runs, then its wiki pages are published, even when python leaves cache files behind. | PASS 2026-11-11 |
| [auto-release](Tests#t-auto-release) | requirement | DEL-5 | Given auto-release is on, when a goal merges, then it is released automatically. | PASS 2026-11-11 |
| [wiki-unmapped-stale](Tests#t-wiki-unmapped-stale) | requirement | DEL-5 | Given a page no touched path maps to, when the release step runs, then it refreshes the page and refuses to merge while it is stale. | PASS 2026-11-11 |
| - | requirement | DEL-6 | no passing test | not enforced |
| [frozen-done-lines](Tests#t-frozen-done-lines) | requirement | DEL-2 | Given a running goal, when a frozen done line is changed, then the goal stops. | PASS 2026-11-09 |
| - | requirement | DEL-7 | no passing test | not enforced |
| [del8-floor-step](Tests#t-del8-floor-step) | requirement | DEL-8 | Given step_budget_minutes under 15, when a step reads it, then it is refused with a fix line. | not run |
| [del8-step-stops](Tests#t-del8-step-stops) | requirement | DEL-8 | Given a review or ship step that reaches its limit, when it is stopped, then it is recorded done with what it left and the goal goes on without a failed try. | not run |
| [del8-step-recorded](Tests#t-del8-step-recorded) | requirement | DEL-8 | Given a step that hit its budget, when the goal's record is read, then it names the step and what it left. | not run |
| [del8-session-budget](Tests#t-del8-session-budget) | requirement | DEL-8 | Given a step run by the worker session, when it is asked for, then its instructions carry the step budget. | not run |
| [del8-session-overrun](Tests#t-del8-session-overrun) | requirement | DEL-8 | Given a session-run step that took longer than its budget, when it is recorded, then the overrun and what it left are kept. | not run |
| [del8-board](Tests#t-del8-board) | requirement | DEL-8 | Given a step or test run that hit its budget, when the monitoring report runs, then it lists the hit and what was left. | not run |
| [del8-health](Tests#t-del8-health) | requirement | DEL-8 | Given a step or test run that hit its budget, when health runs, then it lists the hit and what was left. | not run |
| - | requirement | DEL-8 | no passing test | not enforced |
| - | requirement | DEL-9 | no passing test | not enforced |
| [scripts-no-hang](Tests#t-scripts-no-hang) | defect | [#35](https://github.com/jcl2018/agent-workflow-template/issues/35) closed (2026-11-09) | Given a script with no terminal, when it needs a prompt, then it fails with an error instead of hanging. | PASS 2026-11-11 |
| [guards-rule-start](Tests#t-guards-rule-start) | defect | [#147](https://github.com/jcl2018/agent-workflow-template/issues/147) closed (2026-11-11) | Given a reply-format rule added after a step started, when that step is recorded, then the rule doesn't bind it, and a step started after it is refused naming the rule and the release that added it. | PASS 2026-11-10 |
| [guards-no-try](Tests#t-guards-no-try) | defect | [#148](https://github.com/jcl2018/agent-workflow-template/issues/148) closed (2026-11-11) | Given a record refused for format (no DEPTH or STEP line) or a wrong HEAD, when it is refused, then no try is used, the goal keeps running and the fix is printed. | PASS 2026-11-10 |
| [guards-touches-finding](Tests#t-guards-touches-finding) | defect | [#157](https://github.com/jcl2018/agent-workflow-template/issues/157) closed (2026-11-11) | Given a goal that needs more touches, or a finished goal with a finding, when the operation runs goal.py touches or finding, then touches widen with a logged reason and the finished goal is not stopped. | PASS 2026-11-10 |
| [builtin-flow](Tests#t-builtin-flow) | defect | [#47](https://github.com/jcl2018/agent-workflow-template/issues/47) closed (2026-11-11) | Given a flow file whose steps are built-in and no probe, when a goal starts and its steps run, then delivery runs its own routine for each step, and with no flow file it still refuses. | not run |
| [pr-body-no-checks](Tests#t-pr-body-no-checks) | defect | [PR 62](https://github.com/jcl2018/agent-workflow-template/pull/62) merged (2026-11-09) | Given a pull request, when its body is written, then it says nothing about checks and lists each step's result. | PASS 2026-11-11 |
| [wiki-release-pycache](Tests#t-wiki-release-pycache) | defect | [#58](https://github.com/jcl2018/agent-workflow-template/issues/58) closed (2026-11-09) | Given python leaves cache files behind, when a goal merges, then its wiki pages are still published. | PASS 2026-11-11 |
| [worker-runs-release](Tests#t-worker-runs-release) | defect | [PR 61](https://github.com/jcl2018/agent-workflow-template/pull/61) merged (2026-11-09) | Given a worker that ends with its pull request waiting, when it finishes, then it runs the release step itself. | PASS 2026-11-11 |
