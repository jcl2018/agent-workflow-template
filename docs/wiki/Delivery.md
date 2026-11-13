<!-- workflow-docs -->
# Delivery

Milestone: https://github.com/jcl2018/agent-workflow-template/milestone/1

Review: **Reviewed 2026-11-13** <!-- prd P=7884b325 R=a5b21434 N=9f4c33da M=f8cd4612 U=ae139da8 -->

## Problem
- I have more changes to make than time to babysit them: I want to hand over one sentence and walk away.
- Without a loop, a change stalls at whatever step I stopped watching: no review, no tests, no release.
- I need every change to arrive the same way: reviewed, tested, documented and released, with a record of what happened.

## Requirements

### Functional
- DEL-1: **Reviewed 2026-11-08** The loop <!-- reviewed b5b65da9 -->
  - I give one sentence and its done lines; a worker runs it unattended.
  - Steps, in order: freeze, idea, plan, build, review, qa, ship, pull request, release.
  - Review is the only gate.
  - Each step maps to a skill I choose, in a private setting outside the repo.
  - It won't start without the flow set up, and stops with a reason after 3 failed tries.
- DEL-2: **Reviewed 2026-11-08** Frozen done lines <!-- reviewed c810cac8 -->
  - Done lines can't change once the goal starts; a change means a new goal.
- DEL-3: **Reviewed 2026-11-08** Decisions <!-- reviewed 48b4ed7f -->
  - A decision for me waits under Needs you, or, where the repo allows, is auto-approved and logged.
- DEL-4: **Reviewed 2026-11-08** The pull request <!-- reviewed 7cc0d031 -->
  - Carries the done lines, the plan, how to verify by hand, and each step's result.
- DEL-5: **Reviewed 2026-11-13** Release <!-- reviewed 6d02eda3 -->
  - Every goal ends with release. With auto_merge on it is fully automatic: it bumps the version, writes the release note, refuses to merge while a page is stale, runs my routines, merges, publishes the release and the wiki. With auto_merge off it makes a draft release for me to publish and merges nothing. Any failure shows under Needs you.
- DEL-6: **Reviewed 2026-11-13** Review depth fits the goal <!-- reviewed cb62ccd5 -->
  - Plan and review run at full depth by default (`review_depth: full`); a condensed plan and review happens only when `review_depth: condensed`, and I can override it per goal. Tests never shrink: every goal runs its test lane, the affected rows within the test budget (REG-7).
- DEL-10: **Reviewed 2026-11-13** A goal started on another machine can be adopted <!-- reviewed 6e9abcdb -->
  - `goal.py adopt SLUG`, run in the goal's worktree on branch `loop/SLUG`, creates this machine's run record at step qa from the pushed branch, its frozen goal file and its open pull request; idea, plan and review are recorded `done on another machine`.
  - qa, ship and the pull request are never recorded from another machine's evidence: they run again here before release.
  - A record here that is running with no pid and no recorded step (a stale, never-started one) is replaced and the replacement logged; a record with a pid, a recorded step or a finished status makes adopt refuse.
- DEL-11: **Reviewed 2026-11-13** Adopt never trusts an unpushed branch <!-- reviewed 30558ba2 -->
  - A branch that is not on origin, a worktree missing its commits, a goal with no done line or no open pull request is refused with one line, and no run record is written.

### Non-functional
- DEL-7: **Reviewed 2026-11-10** Resumable <!-- reviewed 0f9f447b -->
  - A stopped or crashed goal resumes from its last recorded step, never from the start.
- DEL-8: **Reviewed 2026-11-13** Budgeted <!-- reviewed 16c92402 -->
  - Each goal has a time and token budget, and going over shows on the board.
  - Each review and ship step has a time limit, a setting no lower than 15 minutes; a step that reaches it finishes with what it has done, records what it left, and the goal goes on instead of restarting.
  - A lane that stops at its preparation budget is recorded on the goal with the part that ran long, and the board and health list it beside the step and test budget hits.
- DEL-9: **Reviewed 2026-11-10** Nothing private ships <!-- reviewed ad7ed0f0 -->
  - Every commit and pull request passes the private-name scan before it is pushed.
- DEL-12: **Reviewed 2026-11-13** Windows-safe on merge <!-- reviewed b8e35707 -->
  - A pull request that adds a POSIX-only call without its guard (fcntl, os.getuid, os.killpg, signal.SIGHUP, os.kill(pid, 0)) fails its lane, so main cannot break native Windows unseen.
  - A long pull request body, issue text or release notes goes to gh in a file (`--body-file`, `--notes-file`), never on the command line, so a pull request with a body over 32,000 characters opens on native Windows.
- DEL-13: **Reviewed 2026-11-13** A review hold before auto merge <!-- reviewed afd8d5c9 -->
  - Where a review hold is set, the release step merges only after the operation session records that it has read the diff, and the board shows a merge waiting on review.

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
| [no-done-line-refused](Tests#t-no-done-line-refused) | requirement | DEL-1 | Given a goal with no done line, when it is started, then it is refused. | PASS 2026-11-12 |
| [no-flow-refused](Tests#t-no-flow-refused) | requirement | DEL-1 | Given no skill flow is set, when a goal is started, then it does not start. | PASS 2026-11-12 |
| [stop-after-3-tries](Tests#t-stop-after-3-tries) | requirement | DEL-1 | Given a goal, when three tries fail, then the goal stops and files a finding. | PASS 2026-11-09 |
| [pr-needs-flow](Tests#t-pr-needs-flow) | requirement | DEL-1 | Given a flow step not yet done, when a pull request is opened, then it is refused. | PASS 2026-11-09 |
| [starts-at-idea](Tests#t-starts-at-idea) | requirement | DEL-1 | Given a new goal, when it starts, then it starts at the idea step. | PASS 2026-11-09 |
| [steps-through-flow](Tests#t-steps-through-flow) | requirement | DEL-1 | Given a step reply, when it is recorded, then it is accepted only if the flow ran that step. | PASS 2026-11-09 |
| [no-prompts](Tests#t-no-prompts) | requirement | DEL-1 | Given any tool, when it runs, then it never waits on a terminal prompt. | PASS 2026-11-12 |
| [defect-flow-steps](Tests#t-defect-flow-steps) | requirement | DEL-1 | Given the flow, when it is checked, then it has no checks step and every step can be mapped, with a default suite and overrides. | PASS 2026-11-12 |
| [depth-condensed-refused](Tests#t-depth-condensed-refused) | requirement | DEL-1 | Given review_depth full, when a plan or review reply says it ran condensed, then it is refused with no try used. | PASS 2026-11-10 |
| [depth-auto-approve-gate](Tests#t-depth-auto-approve-gate) | requirement | DEL-1 | Given review_depth full and auto-approve on, when a condensed review leaves a gate, then it is refused, not approved. | PASS 2026-11-10 |
| [depth-markers](Tests#t-depth-markers) | requirement | DEL-1 | Given private evidence markers, when a full review reply lacks one, then it is refused with no try used, without showing the marker. | PASS 2026-11-10 |
| [depth-recorded](Tests#t-depth-recorded) | requirement | DEL-1 | Given the default setting, when a goal runs its steps, then every recorded step names the depth it ran. | PASS 2026-11-10 |
| [depth-condensed-when-set](Tests#t-depth-condensed-when-set) | requirement | DEL-1 | Given review_depth condensed on the base branch, when a review runs condensed, then it is recorded as condensed. | PASS 2026-11-10 |
| [depth-base-branch](Tests#t-depth-base-branch) | requirement | DEL-1 | Given review_depth full on the base branch, when a worker sets condensed in its own worktree, then it is still held to full. | PASS 2026-11-10 |
| [depth-loop-flow](Tests#t-depth-loop-flow) | requirement | DEL-1 | Given markers in the default flow file, when LOOP_FLOW points elsewhere, then the markers still apply. | PASS 2026-11-10 |
| [guards-extra](Tests#t-guards-extra) | requirement | DEL-1 | Given a stopped or waiting goal, when answer, record or a second reservation comes in, then answer refuses a stopped goal, a waiting goal can't advance, and two goals can't take one session. | PASS 2026-11-10 |
| [ptb-mend](Tests#t-ptb-mend) | requirement | DEL-1 | Given main moved only in the regression rows or a Tests page, when goal.py pr merges it, then the merge is mended and the PR goes on with no try spent, while a code-file conflict still costs one. | PASS 2026-11-12 |
| [ptb-dead-lane](Tests#t-ptb-dead-lane) | requirement | DEL-1 | Given a lane that ended with no exit status (killed from outside), when goal.py pr or a record sees it, then it reruns without spending a try, at most 3 times, and a real failure still spends one. | PASS 2026-11-12 |
| [ptb-plain-paths](Tests#t-ptb-plain-paths) | requirement | DEL-1 | Given a finding or stop text that carries an absolute path, when goal.py writes it, then the finding, the journal and findings.md hold no absolute path and keep the row id and file name. | PASS 2026-11-12 |
| [frozen-done-lines](Tests#t-frozen-done-lines) | requirement | DEL-2 | Given a running goal, when a frozen done line is changed, then the goal stops. | PASS 2026-11-09 |
| [pending-waits](Tests#t-pending-waits) | requirement | DEL-3 | Given a step that leaves a decision for the owner, when it ends, then the goal stops and waits. | PASS 2026-11-12 |
| [auto-approved](Tests#t-auto-approved) | requirement | DEL-3 | Given an auto-approved step, when it ends, then it is logged and nothing waits. | PASS 2026-11-09 |
| [cut-needs-verify](Tests#t-cut-needs-verify) | requirement | DEL-4 | Given no Verify by hand steps, when a release is cut, then it is refused. | PASS 2026-11-12 |
| [pr-body-criterion](Tests#t-pr-body-criterion) | requirement | DEL-4 | Given a pull request, when its body is written, then it carries the goal, the done lines, the verify steps and each step's result. | PASS 2026-11-12 |
| [depth-in-pr-body](Tests#t-depth-in-pr-body) | requirement | DEL-4 | Given a goal whose steps are recorded, when its pull request opens, then the body lists every step with its depth. | PASS 2026-11-10 |
| [never-merges](Tests#t-never-merges) | requirement | DEL-5 | Given auto_merge is off, when goals finish, then nothing is merged. | PASS 2026-11-09 |
| [wiki-release](Tests#t-wiki-release) | requirement | DEL-5 | Given a merged goal, when the release runs, then its wiki pages are published, even when python leaves cache files behind. | PASS 2026-11-12 |
| [auto-release](Tests#t-auto-release) | requirement | DEL-5 | Given auto-release is on, when a goal merges, then it is released automatically. | PASS 2026-11-12 |
| [wiki-unmapped-stale](Tests#t-wiki-unmapped-stale) | requirement | DEL-5 | Given a page no touched path maps to, when the release step runs, then it refreshes the page and refuses to merge while it is stale. | PASS 2026-11-12 |
| [del5-patch-default](Tests#t-del5-patch-default) | requirement | DEL-5 | Given a goal with a code change and no bump set, when it is released, then the version bump is patch. | PASS 2026-11-12 |
| [del5-bump-set](Tests#t-del5-bump-set) | requirement | DEL-5 | Given the operation recorded a minor bump with goal.py set, when the goal is released, then the bump is minor. | PASS 2026-11-12 |
| [del5-release-pr](Tests#t-del5-release-pr) | requirement | DEL-5 | Given a protected main that refuses direct pushes, when a goal is released, then the version and changelog land through a release pull request. | PASS 2026-11-12 |
| [autorelease-no-report](Tests#t-autorelease-no-report) | requirement | DEL-5 | Given a goal state whose report is null, a string or has a non-string text, when the release fails and merge.py refuses, then it prints REFUSED with its fix on stderr, exits non-zero with no traceback, and records the failure on the goal. | PASS 2026-11-12 |
| [wiki-no-report](Tests#t-wiki-no-report) | requirement | DEL-5 | Given a goal state whose report is null or a string, when the wiki publish is refused, then it prints WIKI REFUSED with its fix, exits 1 with no traceback, and records the failure on the goal. | PASS 2026-11-12 |
| [del5-docs-bump-minor](Tests#t-del5-docs-bump-minor) | requirement | DEL-5 | Given a goal that changes only docs and the operation recorded a minor bump with goal.py set, when it is released, then the version moves by a minor. | not run |
| [del5-docs-patch-default](Tests#t-del5-docs-patch-default) | requirement | DEL-5 | Given a goal that changes only docs and no bump is recorded, when it is released, then the version moves by a patch. | not run |
| [resume-ask-worker-step](Tests#t-resume-ask-worker-step) | requirement | DEL-5 | Given a goal set to ask and auto_merge on, when its worker ends with the pull request open, then the release step does not merge it. | not run |
| [resume-unasked-merges](Tests#t-resume-unasked-merges) | requirement | DEL-5 | Given a goal with no ask and auto_merge on, when its worker ends with the pull request open, then the release step still merges it. | not run |
| [del6-depth-by-size](Tests#t-del6-depth-by-size) | requirement | DEL-6 | Given review_depth condensed, when a small goal (up to 3 done lines, one area) and a larger goal run their plan and review, then the small one is told to run condensed and the larger one full. | not run |
| [del6-large-held-full](Tests#t-del6-large-held-full) | requirement | DEL-6 | Given review_depth condensed and a goal touching two areas, when its review replies condensed, then it is refused with no try used. | not run |
| [del6-owner-override](Tests#t-del6-owner-override) | requirement | DEL-6 | Given a large goal, when the owner sets its depth to condensed with goal.py set, then a condensed review is recorded; a worker can't set it. | not run |
| [del6-full-lane](Tests#t-del6-full-lane) | requirement | DEL-6 | Given a goal whose review ran condensed, when its qa step runs, then it runs the same land regression lane as a full-depth goal, with no row dropped for depth. | not run |
| - | requirement | DEL-6 | no passing test | not enforced |
| [adopt-record-qa](Tests#t-adopt-record-qa) | requirement | DEL-10 | Given a goal pushed from another machine with an open pull request, when goal.py adopt runs on its branch, then a run record exists at step qa with the pull request, idea, plan and review done on another machine and qa, ship and pr not recorded. | not run |
| [adopt-replaces-stale](Tests#t-adopt-replaces-stale) | requirement | DEL-10 | Given a run record here that is running with no pid and no recorded step, when goal.py adopt runs, then it replaces the record and logs it; given a record with a pid, then adopt refuses and leaves it unchanged. | not run |
| - | requirement | DEL-10 | no passing test | not enforced |
| [adopt-refuses-unpushed](Tests#t-adopt-refuses-unpushed) | requirement | DEL-11 | Given a branch that is not on origin, when goal.py adopt runs, then it is refused in one line and no run record is written. | not run |
| - | requirement | DEL-11 | no passing test | not enforced |
| [del7-kill-resume](Tests#t-del7-kill-resume) | requirement | DEL-7 | Given a goal whose review was killed mid-step, when it is resumed, then it reruns review from its recorded plan, never from the start, and moves on to qa. | not run |
| [del7-recorded-refused](Tests#t-del7-recorded-refused) | requirement | DEL-7 | Given a goal with recorded steps, when a recorded step is run again without --again, then it is refused with no try and names the step to resume from. | not run |
| - | requirement | DEL-7 | no passing test | not enforced |
| [del8-floor-step](Tests#t-del8-floor-step) | requirement | DEL-8 | Given step_budget_minutes under 15, when a step reads it, then it is refused with a fix line. | not run |
| [del8-step-recorded](Tests#t-del8-step-recorded) | requirement | DEL-8 | Given a step that hit its budget, when the goal's record is read, then it names the step and what it left. | not run |
| [del8-session-budget](Tests#t-del8-session-budget) | requirement | DEL-8 | Given a step run by the worker session, when it is asked for, then its instructions carry the step budget. | not run |
| [del8-session-overrun](Tests#t-del8-session-overrun) | requirement | DEL-8 | Given a session-run step that took longer than its budget, when it is recorded, then the overrun and what it left are kept. | not run |
| [del8-board](Tests#t-del8-board) | requirement | DEL-8 | Given a step or test run that hit its budget, when the monitoring report runs, then it lists the hit and what was left. | not run |
| [del8-health](Tests#t-del8-health) | requirement | DEL-8 | Given a step or test run that hit its budget, when health runs, then it lists the hit and what was left. | not run |
| [del8-prep-board](Tests#t-del8-prep-board) | requirement | DEL-8 | Given a lane that hit the preparation budget, when the monitoring report and health run, then both list the hit and the part that ran long in the same words as budget.py. | not run |
| [del8-goal-budget](Tests#t-del8-goal-budget) | requirement | DEL-8 | Given a repo with a time and token budget, when a goal is frozen, then the goal carries both budgets. | not run |
| [del8-board-over](Tests#t-del8-board-over) | requirement | DEL-8 | Given a running goal past its time and token budget, when the live board prints, then the goal's budget line says OVER time and OVER tokens. | not run |
| - | requirement | DEL-8 | no passing test | not enforced |
| [del9-merge-refuses](Tests#t-del9-merge-refuses) | requirement | DEL-9 | Given a pull request whose branch holds a private name, when merge.py runs, then nothing is merged. | PASS 2026-11-12 |
| [del9-scan-sites](Tests#t-del9-scan-sites) | requirement | DEL-9 | Given the delivery, release and monitoring scripts, when any function pushes or writes to GitHub, then it calls the private-name scan first. | not run |
| [del9-lane-part-no-path](Tests#t-del9-lane-part-no-path) | requirement | DEL-9 | Given a lane record whose LANE line ends with a local log path, when the pull request body's lane part is built, then it keeps the LANE line, the before-rows parts and the rows and drops the log path, so the private-name scan does not refuse every pull request from a machine whose home folder is on the list. | not run |
| - | requirement | DEL-12 | no passing test | not enforced |
| - | requirement | DEL-13 | no passing test | not enforced |
| [scripts-no-hang](Tests#t-scripts-no-hang) | defect | [#35](https://github.com/jcl2018/agent-workflow-template/issues/35) closed (2026-11-09) | Given a script with no terminal, when it needs a prompt, then it fails with an error instead of hanging. | PASS 2026-11-12 |
| [guards-rule-start](Tests#t-guards-rule-start) | defect | [#147](https://github.com/jcl2018/agent-workflow-template/issues/147) closed (2026-11-11) | Given a reply-format rule added after a step started, when that step is recorded, then the rule doesn't bind it, and a step started after it is refused naming the rule and the release that added it. | PASS 2026-11-10 |
| [guards-no-try](Tests#t-guards-no-try) | defect | [#148](https://github.com/jcl2018/agent-workflow-template/issues/148) closed (2026-11-11) | Given a record refused for format (no DEPTH or STEP line) or a wrong HEAD, when it is refused, then no try is used, the goal keeps running and the fix is printed. | PASS 2026-11-12 |
| [guards-touches-finding](Tests#t-guards-touches-finding) | defect | [#157](https://github.com/jcl2018/agent-workflow-template/issues/157) closed (2026-11-11) | Given a goal that needs more touches, or a finished goal with a finding, when the operation runs goal.py touches or finding, then touches widen with a logged reason and the finished goal is not stopped. | PASS 2026-11-12 |
| [builtin-flow](Tests#t-builtin-flow) | defect | [#47](https://github.com/jcl2018/agent-workflow-template/issues/47) closed (2026-11-11) | Given a flow file whose steps are built-in and no probe, when a goal starts and its steps run, then delivery runs its own routine for each step, and with no flow file it still refuses. | PASS 2026-11-12 |
| [issue-117-github-touches](Tests#t-issue-117-github-touches) | defect | [#117](https://github.com/jcl2018/agent-workflow-template/issues/117) closed (2026-11-11) | Given a goal touching github:wiki that deletes a file a repo script writes, when it opens its pull request, then the surface is listed and the script is warned about (issue: Goals can't name GitHub-side changes, and nothing warns when a script regenerates what a goal deletes). | not run |
| [pr-body-no-checks](Tests#t-pr-body-no-checks) | defect | [PR 62](https://github.com/jcl2018/agent-workflow-template/pull/62) merged (2026-11-09) | Given a pull request, when its body is written, then it says nothing about checks and lists each step's result. | PASS 2026-11-12 |
| [issue-38-verdicts](Tests#t-issue-38-verdicts) | defect | [#38](https://github.com/jcl2018/agent-workflow-template/issues/38) closed (2026-11-11) | Given a step reply with VERDICT lines, when the goal opens its pull request, then each verdict is listed under its step (issue: Record the Codex judge and idea-run results). | not run |
| [pr-body-by-file](Tests#t-pr-body-by-file) | defect | [#1396](https://github.com/jcl2018/agent-workflow-template/issues/1396) closed (2026-11-12) | Given a lane that lists hundreds of rows, when goal.py opens the pull request, then the body goes in a file, not on the command line, which Windows caps. | not run |
| [wiki-release-pycache](Tests#t-wiki-release-pycache) | defect | [#58](https://github.com/jcl2018/agent-workflow-template/issues/58) closed (2026-11-09) | Given python leaves cache files behind, when a goal merges, then its wiki pages are still published. | PASS 2026-11-12 |
| [worker-runs-release](Tests#t-worker-runs-release) | defect | [PR 61](https://github.com/jcl2018/agent-workflow-template/pull/61) merged (2026-11-09) | Given a worker that ends with its pull request waiting, when it finishes, then it runs the release step itself. | PASS 2026-11-12 |
| [issue-129-docs-published](Tests#t-issue-129-docs-published) | defect | [#129](https://github.com/jcl2018/agent-workflow-template/issues/129) open (2026-11-11) | Given the release skill's docs, when they describe the auto_merge path, then they say merge.py publishes the release with no draft (issue: Release skill says it cuts a draft, but merge.py publishes the release directly). | failing (issue reopened) 2026-11-12 |
| [issue-129-wiki-first-page](Tests#t-issue-129-wiki-first-page) | defect | [#129](https://github.com/jcl2018/agent-workflow-template/issues/129) open (2026-11-11) | Given a GitHub wiki with no first page, when the release publishes it, then the error names how to create the first page (issue: Release skill says it cuts a draft, but merge.py publishes the release directly). | failing (issue reopened) 2026-11-12 |
| [issue-134-protected-release](Tests#t-issue-134-protected-release) | defect | [#134](https://github.com/jcl2018/agent-workflow-template/issues/134) closed (2026-11-11) | Given a PR-only ruleset on main, when a goal is released, then a release PR lands the version and exactly one GitHub release is made at its merge commit (issue: Autorelease fails on a protected base branch). | PASS 2026-11-12 |
| [issue-154-release-pr-merge](Tests#t-issue-154-release-pr-merge) | defect | [#154](https://github.com/jcl2018/agent-workflow-template/issues/154) closed (2026-11-11) | Given a release PR the loop can't merge because review is required, when merge.py runs, then it records the owner's merge command (issue: merge.py's release push fails on a protected main). | PASS 2026-11-12 |
| [issue-170-patch-on-remove](Tests#t-issue-170-patch-on-remove) | defect | [#170](https://github.com/jcl2018/agent-workflow-template/issues/170) closed (2026-11-11) | Given a goal that removes a file, when it is released, then the bump is patch and the removal is named in the reason (issue: autorelease turns release.py's 'ask' into a silent major bump). | PASS 2026-11-12 |
| [stop-takes-tree](Tests#t-stop-takes-tree) | defect | [#1396](https://github.com/jcl2018/agent-workflow-template/issues/1396) closed (2026-11-12) | Given a step or child stopped for a timeout or a mend, when it is stopped on any platform, then its whole process tree goes with it. | PASS 2026-11-12 |
