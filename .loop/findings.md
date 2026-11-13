# Findings

Open findings, one line each.

- flow-qa-lane-unasked: `flow.py <slug> qa` starts the full land lane itself (role.py lane step) with no check that the operation session allowed a lane, so an in-session worker following "run flow.py" can exceed the at-most-two-lanes rule; seen in health-hygiene 2026-11-09, stopped by hand after about two minutes.

Retired (checked 2026-11-08 against each run record and `git log main`; a retired line does not start with a dash):
retired project-wiki: its run record is retired and the wiki work landed in PR #10 (project-wiki-3).
retired project-wiki-2: its run record is retired; superseded by project-wiki-3, merged as PR #10.
retired project-wiki-3: the work merged as PR #10; the judge failure it recorded did not recur.
retired operation-session: superseded by operation-session-2, merged as PR #6; its own PR #5 is also merged.
retired auto-release: the goal's PR #14 merged; its run record is done.
retired numbered-levels-2: the goal's PR #15 merged; its run record is done.
- reply-hook: reply-hook: a stale board with the right headings passes the hook; a digest token in the LIVE BOARD header, checked against board.json, would prove freshness (autoplan CEO F1)
- reply-hook: reply-hook: the live board or health should show when reply_hook is on but the hook is not installed, when it keeps failing open, and recent let-throughs (autoplan CEO F3/F4/F5, DX F2/F6); outside this goal's paths

Open (from board-held's ship review, 2026-11-10; non-blocking, for the health-report pass to file):
- sessions-size: skills/workflow-monitoring/scripts/sessions.py is 20443 bytes, 99% of the 20 KB rule; split it (e.g. the bind/free/report commands out of the pool code) before the next change to it.
- watch-start-lock: watch.py start_round checks taken() and freeze() makes its first save outside the session-pool lock, so an operator bind landing in between gives one goal two sessions; take sessions.locked() around the check and the first save.
- assign-unreadable-after-send: if the pool turns unreadable after assign's send succeeded, watch marks the run failed with worker background, and mend can relaunch a second worker beside the session; save the session on the run before reporting the pool problem.
- handed-leaves-queued: a HANDED assign (say an operator free during the send) leaves a freshly frozen run queued, which the live board shows nowhere and nothing starts; set it running with no worker so it shows as held.
- run-record-lock: run records are changed without the pool lock by sessions.py report, goal.py step/record, watch refresh and mend, so a concurrent write can undo a bind's session and bound_at; lock load and save in report at least.
- assign-new-sid-collision: assign writes a newly started session id into the pool without checking it is already busy for another goal, so a tool that repeats ids steals another goal's claim.
- report-attempt-identity: sessions.py report doesn't check which session sent it, so a stale or HANDED session's report can fail a goal and free its current session (deferred E7).
- assign-freed-reuse: assign can hand a goal back to a session `free` marked freed_from that goal, the reuse bind refuses without --force.
- watch-go-unreadable-pool: watch.py go treats an unreadable pool as empty when choosing a slug, so it can queue a goal under a slug a session already holds but hasn't frozen.
- automation-email: Failed 3 tries. Last: merging main conflicts in: .loop/regression.tsv, skills/workflow-setup/SKILL.md
- delivery-prd: Failed 3 tries. Last: qa failed: regression lane: LANE_TIMEOUT: past its limit of 4500s (flow file "limit", else step_limit); the lane committed and pushed nothing.

Open (from the issue-cleanup triage of the open non-regression issues, 2026-11-12; one line per piece of work, each names its issues; none starts with a closing word):
- size-split-scripts: trim or split the scripts the size check warns on before they pass the 20 KB limit: goal.py, release.py, role.py, reply_hook.py, watch.py, fit.py, flow.py, guards.py, lanekit.py, lanes.py, merge.py and lane.py (lane.py also in goal skill-size-2; sessions.py is the sessions-size finding above); the health run keeps these issues open until each passes (live_board.py too: health would reopen #353) (issues #138, #142, #352, #353, #354, #355, #356, #529, #828, #829, #830, #831, #833, #834)
- rows-for-set-grd: add a regression row, or mark covered, for each Setup requirement SET-6, SET-7 and SET-9 and Guardrails requirement GRD-1 to GRD-10 that health reports as not enforced (issues #338, #339, #341, #815, #816, #817, #818, #819, #820, #821, #822, #823, #824)
- usage-readme-gaps: the README names /workflow-docs init, /workflow-release cut and /workflow-release leave that no page's Usage names; add each to its page's Usage or drop it from the README (issues #343, #344, #345)
- findings-hygiene: retire the findings lines that landed, since the hygiene check warns while findings stay open (issue #357)
- prd-wording-fixes: from the review findings: DEL-6 says every goal runs its full test lane against REG-4 (#404), the depth rows are linked to DEL-1 (#405), Health Usage omits review and triage (#408), Monitoring Usage and Command map omit cleanup --dry-run (#409), MON-1, MON-2 and MON-5 title lines are over long (#410), duplicate adopt-set rows remain (#414)
- regression-job-timeout: the regression job allows 90 minutes against AUT-7's 45; make the job and the requirement agree (issue #403)
- runs-column-rows: re-run the runs-url and runs-partial rows and find why the lane recorded FAIL while the toy test passes locally (issue #407)
- setup-like-option: build the setup --like option SET-9 asks for (issue #411)
- setup-zero-tests: setup picks a test command that can run 0 tests (it accepts *_test.py for unittest discover); prove the chosen check runs at least one test, with a defect test (issue #119)
- setup-refused-writes: setup prints REFUSED on a bare agent_command but still writes and commits; write nothing, or do not call it a refusal, with a defect test (issue #120)
- tsv-ban-repos: the loop files are .tsv, which repos that ban tracked .tsv files reject; offer another format or a setup-written exemption (issue #127)
- criteria-user-assertion: criteria.py --user is still only an assertion that the owner said so, though the LOCKED hint is fixed and LOOP_OWNER_WORDS is needed without a terminal (issue #133)
- app-hook-worktree: the app's own edit hook still blocks a goal's worktree when the session started elsewhere; outside the repo's reach, tracked by the loop-guards design (issue #160)
- health-new-groups: add the CI, Portability and Process flow rule groups after retiring a group or raising the cap; Process flow is also in health-prd (issues #179, #180, #181)
- goal-pr-try-budget: a merge conflict from a moving main and a dead lane burn the 3-try budget, and finding text carries absolute paths; retry without spending a try, use repo-relative paths, skip the push when the remote has HEAD (issues #436, #610)
- goal-done-line-private: refuse a done line with a private name or absolute path before freezing, and give the operation a done --reword that records old, new and approver (issue #451)
- report-no-release-for-worker: sessions.py report --status waiting --pr must record the PR only unless the role is operation, and a resume must honour release ask when auto_merge is on, each with a regression row (issues #494, #812)
- reply-hook-checkin-only: reply_hook should check only check-in turns, accept Dependency graph, and have negative-control rows (issue #496)
- deployments-followups: extend the address check to every Deployments cell, fix cells() last character, prd.py convert order and the guide-page Deployments shape, one seen-failing row each (issue #519)
- lane-new-rows-first: order a goal's new and changed rows before reach rows in the qa, ship and pr lanes (issue #531)
- board-test-fix: dev/toy/test-board.sh fails three rows on main: restore the operation.md phrases "one chat line" and "6 lines" (or update the rows) and free room in watch.py (issue #607)
- release-draft-wording-no-wiki: the release skill still describes a draft when auto_merge is off while DEL-5 says there is no draft step, and the first-page wiki message does not cover a repo with no GitHub wiki (issue #129, reopened by this triage)
- lane-plan-cache-proof: add a regression row proving lane planning stays under 60 s at load 20 with an unchanged row set; the loop/lane-plan-cache goal carries it (issue #710)
- guard-enforce-red: Failed 3 tries. Last: merging main conflicts in: docs/wiki/Tests.md
- spec-decisions: Failed 3 tries. Last: merging main conflicts in: docs/wiki/Documentation.md, docs/wiki/Regression.md
- settings-render-windows: Failed 3 tries. Last: regression lane failed: LANE_DIRTY at start: .loop/regression-issues.tsv. Fix: commit or remove them; the lane committed and pushed nothing.
- govern-hook-notes: Failed 3 tries. Last: merging main conflicts in: .loop/regression-runs.tsv, docs/wiki/Tests.md
- capture-row-output: Failed 4 tries. Last: merging main conflicts in: .loop/regression-issues.tsv
- health-v1: Failed 3 tries. Last: merging main conflicts in: .loop/regression.tsv, DECISIONS.md, docs/wiki/Health.md, docs/wiki/Tests.md
- health-v1: Failed 4 tries. Last: merging main conflicts in: .loop/regression.tsv, DECISIONS.md, docs/wiki/Health.md, docs/wiki/Tests.md
