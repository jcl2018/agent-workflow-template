<!-- workflow-docs -->
# Delivery

Milestone: https://github.com/jcl2018/agent-workflow-template/milestone/1

Review: **Reviewed 2026-11-10** <!-- prd P=7884b325 R=ed81bf41 N=9f4c33da M=f8cd4612 U=0c2c3b5a -->

## Problem
- I have more changes to make than time to babysit them: I want to hand over one sentence and walk away.
- Without a loop, a change stalls at whatever step I stopped watching: no review, no tests, no release.
- I need every change to arrive the same way: reviewed, tested, documented and released, with a record of what happened.

## Usage
- `goal.py new "GOAL" --done "LINE" [--done "LINE" ...] [--here]` — Freezes a goal and its done lines. Prints `FROZEN slug`. Refuses with no done line (exit 2, `REFUSED: a goal needs at least one done line`) or with no skill flow set up (exit 2).
- `flow.py SLUG STEP` — Runs one step (idea, plan, review, qa, ship). In a worker session prints `IN SESSION` and the skill to run. Prints `RUNNING` until it ends.
- `goal.py record SLUG STEP --in-session` — Records a finished step. Refuses a reply with no `DEPTH:` line, and a qa step with no passing lane on HEAD (`LANE_MISSING`).
- `goal.py pr SLUG` — Merges the latest main, reruns the affected tests, pushes and opens the pull request. Prints the PR link. Never merges.
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
- DEL-8: **Reviewed 2026-11-10** Budgeted <!-- reviewed a3d6e1fb -->
  - Each goal has a time and token budget, and going over shows on the board.
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
| [no-done-line-refused](Tests#t-no-done-line-refused) | requirement | DEL-1 | Given a goal with no done line, when it is started, then it is refused. | PASS 2026-11-10 |
| [no-flow-refused](Tests#t-no-flow-refused) | requirement | DEL-1 | Given no skill flow is set, when a goal is started, then it does not start. | PASS 2026-11-10 |
| [stop-after-3-tries](Tests#t-stop-after-3-tries) | requirement | DEL-1 | Given a goal, when three tries fail, then the goal stops and files a finding. | PASS 2026-11-09 |
| [pr-needs-flow](Tests#t-pr-needs-flow) | requirement | DEL-1 | Given a flow step not yet done, when a pull request is opened, then it is refused. | PASS 2026-11-09 |
| [starts-at-idea](Tests#t-starts-at-idea) | requirement | DEL-1 | Given a new goal, when it starts, then it starts at the idea step. | PASS 2026-11-09 |
| [steps-through-flow](Tests#t-steps-through-flow) | requirement | DEL-1 | Given a step reply, when it is recorded, then it is accepted only if the flow ran that step. | PASS 2026-11-09 |
| [no-prompts](Tests#t-no-prompts) | requirement | DEL-1 | Given any tool, when it runs, then it never waits on a terminal prompt. | PASS 2026-11-10 |
| [defect-flow-steps](Tests#t-defect-flow-steps) | requirement | DEL-1 | Given the flow, when it is checked, then it has no checks step and every step can be mapped, with a default suite and overrides. | PASS 2026-11-10 |
| [depth-condensed-refused](Tests#t-depth-condensed-refused) | requirement | DEL-1 | Given review_depth full, when a plan or review reply says it ran condensed, then it is refused with no try used. | PASS 2026-11-10 |
| [depth-auto-approve-gate](Tests#t-depth-auto-approve-gate) | requirement | DEL-1 | Given review_depth full and auto-approve on, when a condensed review leaves a gate, then it is refused, not approved. | PASS 2026-11-10 |
| [depth-markers](Tests#t-depth-markers) | requirement | DEL-1 | Given private evidence markers, when a full review reply lacks one, then it is refused with no try used, without showing the marker. | PASS 2026-11-10 |
| [depth-recorded](Tests#t-depth-recorded) | requirement | DEL-1 | Given the default setting, when a goal runs its steps, then every recorded step names the depth it ran. | PASS 2026-11-10 |
| [depth-condensed-when-set](Tests#t-depth-condensed-when-set) | requirement | DEL-1 | Given review_depth condensed on the base branch, when a review runs condensed, then it is recorded as condensed. | PASS 2026-11-10 |
| [depth-base-branch](Tests#t-depth-base-branch) | requirement | DEL-1 | Given review_depth full on the base branch, when a worker sets condensed in its own worktree, then it is still held to full. | PASS 2026-11-10 |
| [depth-loop-flow](Tests#t-depth-loop-flow) | requirement | DEL-1 | Given markers in the default flow file, when LOOP_FLOW points elsewhere, then the markers still apply. | PASS 2026-11-10 |
| [guards-extra](Tests#t-guards-extra) | requirement | DEL-1 | Given a stopped or waiting goal, when answer, record or a second reservation comes in, then answer refuses a stopped goal, a waiting goal can't advance, and two goals can't take one session. | PASS 2026-11-10 |
| [pending-waits](Tests#t-pending-waits) | requirement | DEL-3 | Given a step that leaves a decision for the owner, when it ends, then the goal stops and waits. | PASS 2026-11-10 |
| [auto-approved](Tests#t-auto-approved) | requirement | DEL-3 | Given an auto-approved step, when it ends, then it is logged and nothing waits. | PASS 2026-11-09 |
| [cut-needs-verify](Tests#t-cut-needs-verify) | requirement | DEL-4 | Given no Verify by hand steps, when a release is cut, then it is refused. | PASS 2026-11-10 |
| [pr-body-criterion](Tests#t-pr-body-criterion) | requirement | DEL-4 | Given a pull request, when its body is written, then it carries the goal, the done lines, the verify steps and each step's result. | PASS 2026-11-10 |
| [depth-in-pr-body](Tests#t-depth-in-pr-body) | requirement | DEL-4 | Given a goal whose steps are recorded, when its pull request opens, then the body lists every step with its depth. | PASS 2026-11-10 |
| [never-merges](Tests#t-never-merges) | requirement | DEL-5 | Given auto_merge is off, when goals finish, then nothing is merged. | PASS 2026-11-09 |
| [wiki-release](Tests#t-wiki-release) | requirement | DEL-5 | Given a merged goal, when the release runs, then its wiki pages are published, even when python leaves cache files behind. | PASS 2026-11-10 |
| [auto-release](Tests#t-auto-release) | requirement | DEL-5 | Given auto-release is on, when a goal merges, then it is released automatically. | PASS 2026-11-10 |
| [wiki-unmapped-stale](Tests#t-wiki-unmapped-stale) | requirement | DEL-5 | Given a page no touched path maps to, when the release step runs, then it refreshes the page and refuses to merge while it is stale. | PASS 2026-11-10 |
| [del5-patch-default](Tests#t-del5-patch-default) | requirement | DEL-5 | Given a goal with a code change and no bump set, when it is released, then the version bump is patch. | not run |
| [del5-bump-set](Tests#t-del5-bump-set) | requirement | DEL-5 | Given the operation recorded a minor bump with goal.py set, when the goal is released, then the bump is minor. | not run |
| [del5-release-pr](Tests#t-del5-release-pr) | requirement | DEL-5 | Given a protected main that refuses direct pushes, when a goal is released, then the version and changelog land through a release pull request. | not run |
| [del6-depth-by-size](Tests#t-del6-depth-by-size) | requirement | DEL-6 | Given review_depth condensed, when a small goal (up to 3 done lines, one area) and a larger goal run their plan and review, then the small one is told to run condensed and the larger one full. | not run |
| [del6-large-held-full](Tests#t-del6-large-held-full) | requirement | DEL-6 | Given review_depth condensed and a goal touching two areas, when its review replies condensed, then it is refused with no try used. | not run |
| [del6-owner-override](Tests#t-del6-owner-override) | requirement | DEL-6 | Given a large goal, when the owner sets its depth to condensed with goal.py set, then a condensed review is recorded; a worker can't set it. | not run |
| [del6-full-lane](Tests#t-del6-full-lane) | requirement | DEL-6 | Given a goal whose review ran condensed, when its qa step runs, then the full land regression lane still runs. | not run |
| - | requirement | DEL-6 | no passing test | not enforced |
| [frozen-done-lines](Tests#t-frozen-done-lines) | requirement | DEL-2 | Given a running goal, when a frozen done line is changed, then the goal stops. | PASS 2026-11-09 |
| [del7-kill-resume](Tests#t-del7-kill-resume) | requirement | DEL-7 | Given a goal whose review was killed mid-step, when it is resumed, then it reruns review from its recorded plan, never from the start, and moves on to qa. | not run |
| [del7-recorded-refused](Tests#t-del7-recorded-refused) | requirement | DEL-7 | Given a goal with recorded steps, when a recorded step is run again without --again, then it is refused with no try and names the step to resume from. | not run |
| - | requirement | DEL-7 | no passing test | not enforced |
| [del8-goal-budget](Tests#t-del8-goal-budget) | requirement | DEL-8 | Given a repo with a time and token budget, when a goal is frozen, then the goal carries both budgets. | not run |
| [del8-board-over](Tests#t-del8-board-over) | requirement | DEL-8 | Given a running goal past its time and token budget, when the live board prints, then the goal's budget line says OVER time and OVER tokens. | not run |
| - | requirement | DEL-8 | no passing test | not enforced |
| [del9-pr-refuses](Tests#t-del9-pr-refuses) | requirement | DEL-9 | Given a branch that adds a private name from the list, when goal.py pr runs, then nothing is pushed and the refusal names the place, never the text. | not run |
| [del9-merge-refuses](Tests#t-del9-merge-refuses) | requirement | DEL-9 | Given a pull request whose branch holds a private name, when merge.py runs, then nothing is merged. | not run |
| [del9-scan-sites](Tests#t-del9-scan-sites) | requirement | DEL-9 | Given the delivery, release and monitoring scripts, when any function pushes or writes to GitHub, then it calls the private-name scan first. | not run |
| - | requirement | DEL-9 | no passing test | not enforced |
| [scripts-no-hang](Tests#t-scripts-no-hang) | defect | [#35](https://github.com/jcl2018/agent-workflow-template/issues/35) closed (2026-11-09) | Given a script with no terminal, when it needs a prompt, then it fails with an error instead of hanging. | PASS 2026-11-10 |
| [guards-rule-start](Tests#t-guards-rule-start) | defect | [#147](https://github.com/jcl2018/agent-workflow-template/issues/147) state unknown | Given a reply-format rule added after a step started, when that step is recorded, then the rule doesn't bind it, and a step started after it is refused naming the rule and the release that added it. | PASS 2026-11-10 |
| [guards-no-try](Tests#t-guards-no-try) | defect | [#148](https://github.com/jcl2018/agent-workflow-template/issues/148) state unknown | Given a record refused for format (no DEPTH or STEP line) or a wrong HEAD, when it is refused, then no try is used, the goal keeps running and the fix is printed. | PASS 2026-11-10 |
| [guards-touches-finding](Tests#t-guards-touches-finding) | defect | [#157](https://github.com/jcl2018/agent-workflow-template/issues/157) state unknown | Given a goal that needs more touches, or a finished goal with a finding, when the operation runs goal.py touches or finding, then touches widen with a logged reason and the finished goal is not stopped. | PASS 2026-11-10 |
| [pr-body-no-checks](Tests#t-pr-body-no-checks) | defect | [PR 62](https://github.com/jcl2018/agent-workflow-template/pull/62) merged (2026-11-09) | Given a pull request, when its body is written, then it says nothing about checks and lists each step's result. | PASS 2026-11-10 |
| [issue-38-verdicts](Tests#t-issue-38-verdicts) | defect | [#38](https://github.com/jcl2018/agent-workflow-template/issues/38) state unknown | Given a step reply with VERDICT lines, when the goal opens its pull request, then each verdict is listed under its step (issue: Record the Codex judge and idea-run results). | not run |
| [wiki-release-pycache](Tests#t-wiki-release-pycache) | defect | [#58](https://github.com/jcl2018/agent-workflow-template/issues/58) closed (2026-11-09) | Given python leaves cache files behind, when a goal merges, then its wiki pages are still published. | PASS 2026-11-10 |
| [worker-runs-release](Tests#t-worker-runs-release) | defect | [PR 61](https://github.com/jcl2018/agent-workflow-template/pull/61) merged (2026-11-09) | Given a worker that ends with its pull request waiting, when it finishes, then it runs the release step itself. | PASS 2026-11-10 |
| [issue-129-docs-published](Tests#t-issue-129-docs-published) | defect | [#129](https://github.com/jcl2018/agent-workflow-template/issues/129) state unknown | Given the release skill's docs, when they describe the auto_merge path, then they say merge.py publishes the release with no draft (issue: Release skill says it cuts a draft, but merge.py publishes the release directly). | not run |
| [issue-129-wiki-first-page](Tests#t-issue-129-wiki-first-page) | defect | [#129](https://github.com/jcl2018/agent-workflow-template/issues/129) state unknown | Given a GitHub wiki with no first page, when the release publishes it, then the error names how to create the first page (issue: Release skill says it cuts a draft, but merge.py publishes the release directly). | not run |
| [issue-134-protected-release](Tests#t-issue-134-protected-release) | defect | [#134](https://github.com/jcl2018/agent-workflow-template/issues/134) state unknown | Given a PR-only ruleset on main, when a goal is released, then a release PR lands the version and exactly one GitHub release is made at its merge commit (issue: Autorelease fails on a protected base branch). | not run |
| [issue-154-release-pr-merge](Tests#t-issue-154-release-pr-merge) | defect | [#154](https://github.com/jcl2018/agent-workflow-template/issues/154) state unknown | Given a release PR the loop can't merge because review is required, when merge.py runs, then it records the owner's merge command (issue: merge.py's release push fails on a protected main). | not run |
| [issue-170-patch-on-remove](Tests#t-issue-170-patch-on-remove) | defect | [#170](https://github.com/jcl2018/agent-workflow-template/issues/170) state unknown | Given a goal that removes a file, when it is released, then the bump is patch and the removal is named in the reason (issue: autorelease turns release.py's 'ask' into a silent major bump). | not run |
| [issue-117-github-touches](Tests#t-issue-117-github-touches) | defect | [#117](https://github.com/jcl2018/agent-workflow-template/issues/117) state unknown | Given a goal touching github:wiki that deletes a file a repo script writes, when it opens its pull request, then the surface is listed and the script is warned about (issue: Goals can't name GitHub-side changes, and nothing warns when a script regenerates what a goal deletes). | not run |
