# Changelog

## v0.27.31 - 2026-11-12

- fix: lanes, slots and step timeouts on native Windows Python (#1396)
- Seen red: port-base-windows, stop-takes-tree
- proctree: declare the Windows handle types (review)
- Lane: re-render the Tests tables
- fix: tmp_for ends at a Windows drive root instead of looping forever
- fix: dev/toy/reap.py is a no-op on Windows (no ps, uid or SIGPIPE) so toy tests keep their own status
- fix: liveness probes stop sending Ctrl+C on Windows
- fix: Windows lane results: CTRL_C_EVENT mislabel, killpg in the generated runner, toy rows that cannot run there
- Windows-only skips: three rows exit 77 on native Windows instead of being known failures everywhere
- Windows: toy tests that need the gh fake are skipped (exit 77) and the lane counts them SKIPPED through a row's pipe
- Merge origin/main into loop/win-posix-calls
- fix: tmp_for ends at a drive root again after the merge
- fix: lane-exec's signal names do not need SIGHUP on Windows
- Windows: the toy suite runs only tests marked '# windows: ok'; the rest are SKIPPED, Linux CI is their check
- Windows: the lane runs a row with bash; shorten two row descriptions over 400 characters
- Merge remote-tracking branch 'origin/main' into loop/win-posix-calls
- pr: record issue states and the lane's results
- docs: Monitoring and Guardrails name the native Windows case
- Revert "docs: Monitoring and Guardrails name the native Windows case"
- Wiki: update pages for win-posix-calls
- Fixes #1396: test stop-takes-tree, seen failing 2026-11-12, passing

### How to verify

1. On a Windows PC with native Python (no WSL), from the repo root run `cd skills/workflow-regression/scripts` and then
   `python -c "import slots; print(slots.port_base())"`.
   Expect: it prints a pair like `(3, 20000)`, not an AttributeError about getuid or O_NOFOLLOW.
2. In the same folder run `python -c "import subprocess, sys, time, proctree; p = subprocess.Popen([sys.executable, '-c', 'import subprocess, sys, time; subprocess.Popen([sys.executable, \"-c\", \"import time; time.sleep(60)\"]); time.sleep(60)']); time.sleep(2); proctree.kill(p.pid)"`
   and watch Task Manager (or `tasklist | findstr python`) while it runs.
   Expect: the two sleeping python processes it started are gone right after it returns.

## v0.27.30 - 2026-11-12

- Add red time-ordered model regression
- Select estimates by time-ordered backtest
- Lane: re-render the Tests tables
- Document time-ordered estimate selection
- Keep Monitoring review header adjacent
- Place estimate note with Monitoring tests
- Lane: re-render the Tests tables
- Record Monitoring criterion and red proof
- Revert "Lane: re-render the Tests tables"
- Refresh generated estimate regression docs
- Merge origin/main (v0.27.15) into loop/estimate-timeorder: rows kept, Tests re-rendered
- Exclude a goal from its own time-ordered past; add time_order_edges check and point mon4 at it
- Restore board_model docstring caveats; re-render Monitoring test table
- estimate-timeorder: commands.md says the time-ordered score picks the model; the board_report sample is a real run
- estimate-timeorder: Monitoring Usage names the time-ordered estimate line (CHANGED until the owner re-reviews); the goal file quotes the sentence
- Merge origin/main into loop/estimate-timeorder: rows kept, Tests re-rendered
- Merge remote-tracking branch 'origin/main' into loop/estimate-timeorder
- Merge origin/main (v0.27.18) into estimate-timeorder
- Merge remote-tracking branch 'origin/main' into loop/estimate-timeorder
- Merge origin/main (v0.27.29) into estimate-timeorder
- Remove merge markers left in the regression rows
- Merge remote-tracking branch 'origin/main' into loop/estimate-timeorder

### How to verify

1. Run `python3 skills/workflow-monitoring/scripts/board_report.py --root .` in a repo with finished goal runs.
   Expect: the table labels the selection column `time score`, labels leave-one-out under `diagnostics: loo`, and names the chosen model.
2. Run `python3 skills/workflow-monitoring/scripts/board_report.py --root . --json`.
   Expect: each candidate has a `time_ordered` score and a separate `leave_one_out` score; `chosen` names the time-ordered winner when at least ten goals are scorable.

## v0.27.29 - 2026-11-12

- Goal reset writes an empty report; goal state saved under a lock with merge of concurrent writers
- Design, plan and Delivery usage for guards-null-report
- guards-null-report: a removed key stays removed; plan review fixes
- Delivery usage: say exactly what the lock covers
- guards-null-report: a new record keeps its empty values (key-not-in-snapshot, not a shared sentinel); fresh case
- Lane: re-render the Tests tables
- Merge origin/main into loop/guards-null-report
- Delivery usage: a new record is written whole
- Tests tables and seen red for the bind and mend row
- Merge origin/main into loop/guards-null-report
- Merge origin/main into loop/guards-null-report
- Merge remote-tracking branch 'origin/main' into loop/guards-null-report
- Merge remote-tracking branch 'origin/main' into loop/guards-null-report
- Trim goal.py under the script size cap after merging main
- Wiki: update pages for guards-null-report

### How to verify

No manual steps were recorded.

## v0.27.28 - 2026-11-12

- goal.py pr: a conflict from main moving in generated files is mended, a dead lane reruns free (bounded), finding text carries no absolute path
- Docs: SKILL.md and commands.md name the mended conflict and the free dead-lane rerun
- Merge origin/main (pending-none) into loop/goal-pr-try-budget: rows unioned, Tests re-rendered
- guards.py: shorter docstrings so the file is back under its 20480-byte cap after the merge
- Review fixes: mend refuses a both-sides or deleted row, re-renders Tests.md, only for the wiki page; free reruns only for the generated lane text; dirty tree is no try; plain() covers the lane part
- Lane: re-render the Tests tables
- Lane: re-render the Tests tables
- Merge origin/main into loop/goal-pr-try-budget
- Lane: re-render the Tests tables
- Merge origin/main (v0.27.18) into loop/goal-pr-try-budget: Delivery Tests re-rendered
- Merge remote-tracking branch 'origin/main' into loop/goal-pr-try-budget
- Merge origin/main (v0.27.20) into loop/goal-pr-try-budget: rows unioned
- Merge remote-tracking branch 'origin/main' into loop/goal-pr-try-budget
- Merge remote-tracking branch 'origin/main' into loop/goal-pr-try-budget
- Merge remote-tracking branch 'origin/main' into loop/goal-pr-try-budget

### How to verify

No manual steps were recorded.

## v0.27.27 - 2026-11-12

- Only setup inserts the Settings and Automation blocks; a render refreshes them where their markers are
- Page format: blank the template line too, so a README that opens with How to use passes DOC-5
- Docs staleness: a commit that only refreshes the generated blocks stales no page
- test-adopt: build the package only for SET-3, SET-4 and SET-5, which use it
- test-docs-blocks and four rows for the render-readme-guard done lines
- Mark adopt-set-1 and adopt-set-2 seen red; drop their known entries; Tests, Documentation and Setup usage
- Guard the blocks rows on DOC-15, so they list in the Documentation Tests table
- Point adopt-set-3..5 known entries at package-cap-3; say why SET-1/2 skip the package
- Review: refresh a PRD Home's leftover blocks, render.py usage exit, real() early return, safer no-insert test
- Documentation: render usage names the Home rule
- counting.py: the no-prompt guard, since real() now runs git
- Documentation: check skips block-only commits
- size-140: move docs.py's live() unchanged into counting.py (docs.py 87% of the cap); drop its known entry; record the added done line
- Merge origin/main (v0.27.22) into loop/render-readme-guard: Tests re-rendered; render.py's cadence() moved unchanged into counting.py to keep render.py under the size limit
- Merge origin/main (v0.27.24) into loop/render-readme-guard: both sides' new rows kept; Tests re-rendered
- pr: record issue states and the lane's results
- Merge remote-tracking branch 'origin/main' into loop/render-readme-guard
- Lane: re-render the Tests tables

### How to verify

No manual steps were recorded.

## v0.27.26 - 2026-11-12

- Statuses: a private repo's pr lane posts its real result under every required check
- Local schedule: one launch agent, a registry and a tick; no health workflow; narrow PR workflow
- Local schedule: rows, Usage and the wiki pages
- Local schedule: package disclosure, setup registry check, sturdier toy assertions, seen-red dates
- Docs: re-render Tests, Setup note
- Local schedule: reject a base that is not a branch name, create the agent's log dir at install
- Row ls-nothing-in-repo: require the install and tick to have run
- Toy test: the second 'dr' repo gets its own name (two sections shared one folder, so the full run failed)
- Lane: re-render the Tests tables
- Health: build the temp-folder prefix without a literal path (the lane's reach analysis walked every file under it, 284k, cutting planning at the budget)
- Merge origin/main into loop/local-schedule (prep_budget_minutes stays 25)
- After the merge: move workflow() and its template from tiers.py to lanes_cli.py, trim merge.py comments, so every script is under 20480 bytes
- Lane: re-render the Tests tables
- README: the settings reference regenerated from settings.py (a row rewrote it during the lane)
- Merge origin/main (v0.27.22) into loop/local-schedule
- Lane: re-render the Tests tables
- Merge origin/main into loop/local-schedule; rows placed mid-file
- Merge remote-tracking branch 'origin/main' into loop/local-schedule
- Lane: re-render the Tests tables
- Merge origin/main into loop/local-schedule
- Wiki: update pages for local-schedule
- Wiki: update pages for local-schedule

### How to verify

No manual steps were recorded.

## v0.27.25 - 2026-11-12

- Fold portlock.py into one module per skill; automation in the listing; lane headers (package-cap-3)
- Portlock fallback test, package row, defect-categories copy includes .github, skill-size known entry removed (package-cap-3)
- portlock test declares skills/ (package-cap-3)
- Wiki: the lock fallback lives in the scripts, not portlock.py (package-cap-3)
- Usage notes: the lock fallback, and where audit and automation detail live (package-cap-3)
- Merge remote-tracking branch 'origin/main' into loop/package-cap-3
- test-runbook declares the docs scripts it runs, not the folder (package-cap-3)
- pr: record issue states and the lane's results
- Merge origin/main (lane-died) into loop/package-cap-3: keep lane-died's identity checks and the folded lock shim
- pr: record issue states and the lane's results
- Delivery page: a stop never signals a reused pid, every signal is logged, LANE_DIED names the signal (package-cap-3)
- pr: record issue states and the lane's results

### How to verify

No manual steps were recorded.

## v0.27.24 - 2026-11-12

- Never signal a pid that only reuses a stored one; audit every signal; name the signal that ended a lane
- Lane: re-render the Tests tables
- Merge remote-tracking branch 'origin/main' into loop/lane-died
- Merge origin/main into loop/lane-died
- pr: record issue states and the lane's results

### How to verify

No manual steps were recorded.

## v0.27.23 - 2026-11-12

- Merge remote-tracking branch 'origin/main' into loop/automation-local-prd
- Automation: routines run where they can run fully
- Automation: review fixes to AUT-1, 2, 3, 6 and Non-goals
- Merge remote-tracking branch 'origin/main' into loop/automation-local-prd
- Merge remote-tracking branch 'origin/main' into loop/automation-local-prd
- Merge remote-tracking branch 'origin/main' into loop/automation-local-prd
- Merge remote-tracking branch 'origin/main' into loop/automation-local-prd

### How to verify

No manual steps were recorded.

## v0.27.22 - 2026-11-12

- Runbook section (DOC-16): format check, routine registry, Health and Regression runbooks, toy tests
- runbook test: a Reviewed page's Runbook is not out of order either
- Re-render the Tests tables for the runbook rows
- Merge origin/main into loop/routine-runbooks; criteria_max 16 for DOC-15 and DOC-16
- Re-render Home, README and START after the merge
- Runbooks corrected against the workflows; runbook check hardened (repeats, duplicates, registry, render guard); tests extended
- Runbook check: Serves ids must exist, a misordered page is not also 'no runbook', registry read as UTF-8, template and runbook wording corrected; tests added
- Documentation DOC-16: Serves ids must exist, each routine and field once
- Runbook check: Serves reads continuation lines; no false Serves finding on a misordered page
- Merge origin/main (v0.27.18) into loop/routine-runbooks; Tests tables re-rendered
- runbook test: compare against the copy's own check output (another page may be CHANGED for its owner)
- Merge remote-tracking branch 'origin/main' into loop/routine-runbooks
- Merge origin/main (v0.27.21) into loop/routine-runbooks; Tests tables re-rendered

### How to verify

No manual steps were recorded.

## v0.27.21 - 2026-11-12

- Capacity audit for setup-adopt-2 (no code change)
- Move reply_hook and HOOKS from setup.py to agents.py (no behavior change)
- Health: Adoption rules no-fit and agent-tools, and file --open-only
- Setup: adoption never blocks, rolls back, shows health first and last
- Setup tests and 19 regression rows (rows not yet seen failing)
- Record the 19 setup rows as seen failing on v0.27.10
- Docs: Setup Usage and Tests, setup SKILL.md, Health Usage
- Merge origin/main (v0.27.16) into loop/setup-adopt-2: rows unioned, Tests re-rendered, read-only home kept in the new setup
- Setup: a failed git call mid-adoption rolls back (SystemExit was uncaught in the transaction)
- Docs: Setup Usage says a failed git call mid-adoption rolls back too
- Setup: journal dropped at the commit and ignored when HEAD moved, wiki_dir must be inside the repo, rollback checks index and branch restores, whole-line worktree branch match, CRLF kept once, post-commit SystemExit is a NOTE; drop dead on_branch and unused imports
- Docs: SETUP_WIKI_DIR in Setup Usage and the setup SKILL.md
- Setup: rollback kills and reaps a tool child still running before it restores (a stray docs.py wrote .loop/docs.tsv after a signal rollback)
- Merge origin/main (v0.27.17) into loop/setup-adopt-2: update.py keeps both the contextlib import and portlock, Setup page notes the rollback stops a running tool child
- Docs: Setup Usage says a rollback stops and reaps a running tool child
- Docs: re-render the Settings table (cadence is the string 30 in the config)
- Setup: rollback still restores when pkill or waitpid is missing (Windows); the setup toy declares sync.py and update.py
- Setup toy: a rollback with no pkill still restores (negative control: fails on the unguarded call)
- Docs: Setup Usage and the setup SKILL.md name the post-commit NOTE codes, exit 1 and 130, and that a missing pkill never stops the restore
- pr: record issue states and the lane's results
- Merge origin/main (v0.27.18) into loop/setup-adopt-2: Tests tables re-rendered, wiki-release waiver dropped
- Merge origin/main (v0.27.19) into loop/setup-adopt-2
- Home: the Setup row says adoption never blocks and health is judged before and after
- Merge origin/main (v0.27.20) into loop/setup-adopt-2: Home keeps main's Automation row and our Setup row

### How to verify

No manual steps were recorded.

## v0.27.20 - 2026-11-12

- Fix two small doc defects: count the wiki pages, and put the README's commands in Usage
- Lane: re-render the Tests tables
- Merge origin/main into loop/docs-small-fixes
- Home: say a repo adds a routine with one config entry
- Merge remote-tracking branch 'origin/main' into loop/docs-small-fixes

### How to verify

No manual steps were recorded.

## v0.27.19 - 2026-11-12

- Merge remote-tracking branch 'origin/main' into loop/issue-cleanup
- Merge remote-tracking branch 'origin/main' into loop/issue-cleanup
- Merge origin/main into loop/issue-cleanup; findings from both sides kept
- Merge remote-tracking branch 'origin/main' into loop/issue-cleanup
- pr: record issue states and the lane's results
- Merge origin/main (settings-table, pending-none) into loop/issue-cleanup; Tests page re-rendered
- Merge remote-tracking branch 'origin/main' into loop/issue-cleanup

### How to verify

No manual steps were recorded.

## v0.27.18 - 2026-11-12

- Render the Settings and Automation blocks only with criteria on
- Hold the README front door to the page format without the generated blocks
- Guard both v0.27.17 slips with regression checks
- Render the Tests page for format-frontdoor's new seen-failing date
- Documentation: render writes the generated blocks only with criteria on
- Merge remote-tracking branch 'origin/main' into loop/wiki-release-fix
- Render the settings blocks for main's cadence entry
- pr: record issue states and the lane's results
- Guardrails and Regression: note the v0.27.17 config and the portable lock
- Monitoring: note the portable lock in the operate usage
- pr: record issue states and the lane's results

### How to verify

No manual steps were recorded.

## v0.27.17 - 2026-11-12

- Show the settings table and the automation status on Home and in the README
- Lane: re-render the Tests tables
- Make Automation a routine registry: one config entry adds a routine
- Lane: re-render the Tests tables
- Keep the committed Automation block free of live times; guard render.py's processes
- Merge origin/main into loop/settings-table
- Say why the Automation block holds no live time
- Reword the Settings intro so Home is brought up to date with main
- Keep the Documentation page in step with the Settings intro
- pr: record issue states and the lane's results
- Merge origin/main into loop/settings-table

### How to verify

No manual steps were recorded.

## v0.27.16 - 2026-11-12

- Merge remote-tracking branch 'origin/main' into loop/pending-none
- A step reply's PENDING: none (or nothing, n/a, an empty PENDING line) no longer makes a goal wait (pending-none)
- Rows seen failing, Tests re-rendered (pending-none)
- Wiki: update pages for pending-none
- Review fixes: a decision under a bare PENDING heading waits; linear item trim (pending-none)
- Wiki: update pages for pending-none
- Merge origin/main into loop/pending-none: Tests re-rendered
- pr: record issue states and the lane's results
- Merge origin/main into loop/pending-none: rows unioned, Tests re-rendered
- Merge origin/main into loop/pending-none: rows unioned, Tests re-rendered
- goal.py: trim the usage docstring back under its 19,500-byte ceiling (pending-none)
- Wiki: update pages for pending-none
- pr: record issue states and the lane's results

### How to verify

No manual steps were recorded.

## v0.27.15 - 2026-11-12

- lane-plan-cache: idea design
- lane-plan-cache: plan
- lane-plan-cache: fixtures, v0.27.6 golden plans, golden and calls tests
- lane-plan-cache: memoize the per-row changed call and the folder walk
- lane-plan-cache: a per-branch closure cache keyed by HEAD, the row file, the planner and LANES_WIDE
- lane-plan-cache: seen-red dates for plan-cache-key and plan-seconds-nightly; render Tests
- lane-plan-cache: key the cache on the loop's uncommitted bookkeeping files
- Merge origin/main (v0.27.8) into loop/lane-plan-cache: Tests re-rendered
- lane-plan-cache: review fixes F1 to F11
- lane-plan-cache: test the inflate cap with a 200 MB bomb
- Merge origin/main (lane-tmpdir v0.27.9) into loop/lane-plan-cache: Regression Usage keeps both sentences, rows kept
- Merge remote-tracking branch 'origin/main' into loop/lane-plan-cache
- lane-plan-cache: tiers.py carries the no-terminal guard (the lane caught it: DEL-10 and no-hang)
- lane-plan-cache: qa fixes: sizes builds the package from the committed files, key-rows documented as rare, Regression Usage says planning asks git once per plan
- lane-plan-cache: ship fixes: locale crash, outside symlinks, doc wording
- Merge origin/main (v0.27.11) into loop/lane-plan-cache: rows kept
- Merge origin/main (v0.27.12) into loop/lane-plan-cache: Regression Usage keeps both sentences
- lane-plan-cache: after the v0.27.12 merge, tiers.py back under 18,432 and lanes.py ceiling set to main's size
- lane-plan-cache: Regression Usage names LANES_NO_CACHE
- Merge origin/main (v0.27.13) into loop/lane-plan-cache: Tests re-rendered
- pr: record issue states and the lane's results
- Merge origin/main (v0.27.14) into loop/lane-plan-cache: rows kept

### How to verify

1. Run `bash dev/toy/test-plan-cache.sh all`.
   Expect: golden, calls, identity, key and sizes all print PASS lines and the run ends with `ALL PASS`.
2. Run `bash dev/toy/test-plan-cache.sh seconds` on a quiet or busy machine.
   Expect: it prints the off, cold and warm planning seconds of a 1,500-row fixture under 20 busy loops, the cold plan under 60 seconds, the cache file under 2 MB, and ends with `ALL PASS`.
3. On a large real repo (owner, not run by the build), rerun a lane that was cut with "planning ran long" at a load average of 20 or more, then read the `planning Ns` part of its LANE line and the `PLAN_CACHE:` line of its log (the planner's first line).
   Expect: planning is under 60 s; run the same lane again at the same HEAD and the log says `PLAN_CACHE: hit (N rows)`; after a new commit it says `PLAN_CACHE: miss (key-head)`. If planning is under 60 s, lower that repo's `prep_budget_minutes` from 25 toward the default.
4. Run `LANES_NO_CACHE=1 python3 skills/workflow-regression/scripts/regression.py run land --reuse --tier goal` in a clean checkout of a feature branch.
   Expect: the first planner line (after any `SKIP <id>: draft` or `covered` lines) is `PLAN_CACHE: off (LANES_NO_CACHE=1)` and the rest of the output is what it was before the cache existed.
5. Done line 5 says "every script stays under 18 KB", but 27 scripts were already over 18,432 bytes before this goal, so it is read as: no script grows past its current size, and tiers.py and narrow.py (the two this goal edits that were under it) stay under 18,432. Run `wc -c skills/workflow-regression/scripts/tiers.py skills/workflow-regression/scripts/narrow.py skills/workflow-regression/scripts/lanes.py`.
   Expect: tiers.py and narrow.py under 18432 and lanes.py at most 19710 (its size on main at v0.27.12; this goal's own change to it is a net shrink). If you meant every script under 18 KB, that is a different goal.

## v0.27.14 - 2026-11-12

- test-guard-enforce: the health block asks the Security group for the hooks rule
- Docs: the hooks rule is in the Security group; set8-health seen failing and rendered
- Lane: re-render the Tests tables
- Merge origin/main (v0.27.11) into loop/guard-enforce-red: rows unioned, Tests re-rendered
- Merge origin/main into loop/guard-enforce-red: Tests re-rendered
- Merge origin/main into loop/guard-enforce-red: Tests re-rendered
- pr: record issue states and the lane's results

### How to verify

No manual steps were recorded.

## v0.27.13 - 2026-11-12

- Pods: one shared owner check and merge lock, claim adds sessions, per-repo check-in blocks
- Pods: regression rows and size budgets
- Pods: rows seen red, Tests tables, LOOP_POD_ID in the usage
- Pods: review fixes (atomic stale-lock takeover, free and worker send refuse, read-only others, watch skips foreign goals)
- Merge origin/main into loop/pods
- Pods: graph.py sets the no-prompt guard its git calls need
- Lane: re-render the Tests tables
- Pods: test the package from a clean export, check only the review lock
- Merge remote-tracking branch 'origin/main' into loop/pods
- Monitoring page: MON-15 names the skipped goals and the read-only questions
- Merge origin/main into loop/pods
- Merge remote-tracking branch 'origin/main' into loop/pods
- pr: record issue states and the lane's results

### How to verify

1. In one repo run `CLAUDE_SESSION_ID=pod-a python3 skills/workflow-monitoring/scripts/operate.py claim`, then the same with `pod-b`. Expect: both print `CLAIMED operation session` with no REFUSED, WARN or `replaced`; `cat .git/loop/operation.id` lists pod-a and pod-b.
2. Queue a goal as pod-a (`LOOP_POD_ID=pod-a python3 skills/workflow-monitoring/scripts/watch.py watch --once`), then `cat .git/loop/runs/<slug>.json`. Expect: `"pod": "pod-a"`.
3. As pod-b run `LOOP_POD_ID=pod-b python3 skills/workflow-monitoring/scripts/operate.py send <slug> hi`. Expect: exactly one line `REFUSED: goal <slug> is owned by pod pod-a. Fix: ...`, exit status 2, the record unchanged.
4. Run `python3 skills/workflow-monitoring/scripts/checkin.py` as pod-b. Expect: the goal reads `owned by pod-a` and no question for it is numbered under Needs you; as pod-a it has no such words.
5. In two shells run `python3 skills/workflow-release/scripts/merge.py <slug>` for two goals of one auto_merge repo at once. Expect: the second prints `WAITING: another pod is merging into this repo` and starts only after the first ends; `.git/loop/merge.lock` is gone afterwards.
6. Write a dead pid into `.git/loop/merge.lock` (`echo 999999 > ...`) and run a merge. Expect: it takes the lock at once (no WAITING).
7. Run `python3 skills/workflow-monitoring/scripts/checkin.py` with two followed repos in `~/.workflow-loop/repos`. Expect: one `== name ==` block per repo, no line over 60 characters, `Between repos` for a `repo/slug` dependency, the legend once.

## v0.27.12 - 2026-11-12

- Codex proof: a SKIPPED result for rows that cannot run, setup survives a read-only home, the Codex harness and pod-collision tests
- Codex proof: design, plan, run report, Regression page usage
- Codex proof: fixes from the plan review (SKIPPED never reused, red refuses 77, RESULT counts skips, narrower setup catch, stronger tests, Codex quickstart)
- Touch the Automation and Home pages after the runner and README changes
- settings: write through a symlinked settings file and keep its mode
- Ledger keeps a row's last PASS when a later run is SKIPPED; settings temp file is created with its final mode
- Touch the Setup page after the settings write fix
- Lane: re-render the Tests tables
- Touch the Regression page after the ledger change
- Merge origin/main into loop/codex-proof
- Re-render the Regression tests table; touch the Automation page
- Lane: re-render the Tests tables
- Merge remote-tracking branch 'origin/main' into loop/codex-proof

### How to verify

No manual steps were recorded.

## v0.27.11 - 2026-11-12

- Release refusals never crash on a goal state with no usable report (autorelease-fail-crash)
- Merge remote-tracking branch 'origin/main' into loop/autorelease-fail-crash
- pr: record issue states and the lane's results

### How to verify

No manual steps were recorded.

## v0.27.10 - 2026-11-12

- Merge remote-tracking branch 'origin/main' into loop/milestone-freeform
- Docs: milestones become optional and free form (un-review of DOC-4, DOC-10, HLT-2, HLT-4, AUT-2, AUT-3, SET-1)
- workflow-docs: the audit and Home check no longer require a milestone
- Milestones are optional: remove the checks and per-feature creation; feature tag behind feature_labels
- Tests and rows for free-form milestones; page Usage lines follow the code
- Record each milestone-freeform row seen failing on the old rule
- Merge origin/main into loop/milestone-freeform
- Merge origin/main into loop/milestone-freeform
- Merge origin/main (lane-tmpdir) into loop/milestone-freeform; both sides kept, Tests re-rendered
- Lane: re-render the Tests tables

### How to verify

1. Read Documentation DOC-10 and Health HLT-4 (and DOC-4, HLT-2, AUT-2, AUT-3, SET-1) in docs/wiki.
   Expect: each says a milestone is optional and free form (for example v1.0), none calls it required or per feature, and each of the seven lines reads `Unreviewed`.
2. Run `python3 skills/workflow-docs/scripts/docs.py check` in this repo (its pages keep their existing `Milestone:` link, shown as before); then run `bash dev/toy/test-docs-command.sh` and `bash dev/toy/test-docs-format.sh`.
   Expect: `DOCS OK: 9 pages` with no warning about a milestone; the toy runs print `PASS milestone-freeform:no-milestone-page-ok` and `PASS milestone-freeform:home-milestone-optional` (a page without a Milestone line, and a Home row with an empty Milestone cell, pass).
3. Run `bash dev/toy/test-milestones.sh` (a fixture repo with the fake gh) and read its health file/preview section.
   Expect: issues are filed labelled only `health` and `health:<group>`, with no milestone made or set and no `feature:` label call while `feature_labels` is off; with it on, a `feature:Calc` label is created first and applied; `milestone.py new v1.0 --live` and `move 1 v1.0` work; the run ends with `PASS milestone-freeform:health-file-no-milestone` and `PASS milestone-freeform:milestone-v1-free-form`.

## v0.27.9 - 2026-11-12

- Lane TMPDIR: a fresh folder under the system temp, never inside a git checkout (lane-tmpdir, #814)
- Lane reference: quote the LANE_TMPDIR message as lane.py prints it (lane-tmpdir)
- Merge remote-tracking branch 'origin/main' into loop/lane-tmpdir
- Wiki: update pages for lane-tmpdir

### How to verify

No manual steps were recorded.

## v0.27.8 - 2026-11-12

- estimate-accuracy: move the log facts to board_log.py and the estimate model to board_model.py (no behavior change)
- estimate-accuracy: hold and free entries pause step time; held goals pass the pool's word down
- estimate-accuracy: a step is never stalled before 15 minutes (STALL_FLOOR)
- estimate-accuracy: the board uses whichever candidate model backtests most accurate
- estimate-accuracy: board_report.py prints the backtest of every candidate and why the board uses one
- estimate-accuracy: board_report.py --help ends with the example command
- estimate-accuracy: the live board passes held goals to the estimates and prints the accuracy line under Finish
- estimate-accuracy: toy checks for the backtest, the accuracy line, the stall floor, held time and the module split
- estimate-accuracy: docs for the model choice, the accuracy line, held time and the stall floor
- estimate-accuracy: render the Monitoring and Tests pages with the new rows
- estimate-accuracy: board checks read the finish line after Finish; the speed check counts CPU seconds
- estimate-accuracy: render the Monitoring and Tests pages with the speed row's new text
- fix: with the session pool unreadable, a trailing hold entry no longer makes a goal read stalled
- estimate-accuracy: unreadable-pool stall row seen failing once; Tests re-rendered
- Merge origin/main (v0.23.0 and later) into loop/estimate-accuracy
- Merge origin/main (v0.27.0, with step-budget and lane-control) into loop/estimate-accuracy
- Package under 100 files again: defects.py folded into enforce.py, issues.py into milestone.py, milestones.md into the health commands reference
- Pages touched
- Lane: re-render the Tests tables
- Merge remote-tracking branch 'origin/main' into loop/estimate-accuracy
- Merge origin/main (v0.27.2) into loop/estimate-accuracy
- pr: record issue states and the lane's results
- Merge origin/main (v0.27.4) into loop/estimate-accuracy
- Merge remote-tracking branch 'origin/main' into loop/estimate-accuracy
- pr: record issue states and the lane's results
- Merge remote-tracking branch 'origin/main' into loop/estimate-accuracy
- Wiki: update pages for estimate-accuracy
- Wiki: update pages for estimate-accuracy
- Merge remote-tracking branch 'origin/main' into loop/estimate-accuracy
- Merge remote-tracking branch 'origin/main' into loop/estimate-accuracy
- pr: record issue states and the lane's results

### How to verify

1. Run `python3 skills/workflow-monitoring/scripts/live_board.py` in the repo and read the last line, under the finish time.
   Expect: `estimates: <model>, whole goal off xN.N (N goals)`, at most 60 characters, or `error not known yet (N of 10 goals)`.
2. Run `python3 skills/workflow-monitoring/scripts/board_report.py --root .`.
   Expect: one row per candidate, and the `chosen:` line names the candidate with the lowest loo score, the same model the board's last line names.
3. Look at Issues on the live board for any goal whose current step has run under 15 minutes, and for any goal marked held.
   Expect: none of them is listed as stalled.

## v0.27.7 - 2026-11-12

- Merge remote-tracking branch 'origin/main' into loop/worker-push-guard
- Worker push guard: private.py where and worker_push, toy test, commands.md
- Worker push guard: rows seen red, Tests table, verify by hand
- Worker push guard: review fixes (symlink kept inside temp dir, INTERNAL fix text)
- Wiki: update pages for worker-push-guard
- Merge origin/main into loop/worker-push-guard
- pr: record issue states and the lane's results

### How to verify

1. In a goal worktree run `python3 skills/workflow-delivery/scripts/private.py where`. Expect: `WORKER <slug>`; the same in the main checkout prints `NOT A WORKER (not a goal worktree)`.
2. In a goal worktree run `git push origin HEAD:refs/heads/main` with the hooks installed. Expect: `REFUSED: a worker session for goal <slug> may push only loop/<slug> ... (WORKER_PUSH)` and nothing on origin changes.
3. Run `git push origin HEAD:refs/heads/loop/<slug>` in the same worktree. Expect: the push goes through.
4. In the main checkout run `git push origin main`. Expect: the push goes through (the operation session is unaffected).

## v0.27.6 - 2026-11-12

- Fix issue 116: size splits of criteria.py, docs.py and regression.py (skill-size-2)
- pr: record issue states and the lane's results

### How to verify

1. Run `wc -c skills/workflow-docs/scripts/criteria.py skills/workflow-docs/scripts/docs.py skills/workflow-regression/scripts/regression.py`.
   Expect: criteria.py, docs.py and regression.py are each under 18432 bytes.
2. Run `python3 skills/workflow-health/scripts/health.py check | grep "WARN size"`.
   Expect: criteria.py, docs.py and regression.py are not listed.
3. Run `bash dev/toy/test-defect.sh size-139`, then add one line `def rules(): pass` to the end of `skills/workflow-docs/scripts/criteria.py` and run it again.
   Expect: the first run prints nothing and exits 0; the second prints a `leftovers:` line naming `rules`. Undo the edit with `git checkout -- skills/workflow-docs/scripts/criteria.py`.
4. Run `wc -l skills/workflow-delivery/SKILL.md skills/workflow-docs/SKILL.md`.
   Expect: each is under 150 lines.

## v0.27.5 - 2026-11-12

- Private-name hooks: pre-commit, commit-msg and pre-push scan through private.py, installed by setup, flagged by health (guard-enforce)
- Review fixes: commentChar=auto bypass, non-ASCII name leak, keep edited stubs (guard-enforce)
- Lane: re-render the Tests tables
- Lane: re-render the Tests tables
- Setup page: name the two other hook outcomes (guard-enforce)
- Merge main into guard-enforce
- Merge main (v0.27.4, health-prd) into guard-enforce: hooks rule registered in the Security group
- Merge remote-tracking branch 'origin/main' into loop/guard-enforce
- Merge remote-tracking branch 'origin/main' into loop/guard-enforce
- pr: record issue states and the lane's results
- Wiki: update pages for guard-enforce

### How to verify

No manual steps were recorded.

## v0.27.4 - 2026-11-12

- health-prd: cost leaves out goals with no tokens (124); the judge error names its stderr (158)
- health-prd: sync skips done lines of goals frozen before done_lines_since (124)
- health-prd: twelve groups with angles (groups.py), 21 new rules in rules_trace/rules_fresh/rules_guard, a control for every rule, gh read once (ghcache)
- health-prd: feature milestones, links, evidence hash and old-key migration (file.py, feature.py); review.py with verified evidence; triage.py; commands.py; judge cause names stdout and stderr (158); docs for twelve groups (159); test-health-prd.sh
- health-prd: tests updated for the twelve groups; a moved issue stays moved; ran-rules read the rule a row speaks for; judge measures check-time; donelines guard; automation files the runner-readable groups, health.yml regenerated (d6)
- health-prd: rows for HLT-1, 2, 4, 5, 6 and issues 124, 158, 159, each seen red; Health Tests re-rendered
- health-prd: review fixes (keys with spaces, shared unread source closes nothing, one issue per review finding, file --review files only review, finding-age report-only, reopen drops health:closed, open duplicate wins, no link on plain words, old ambiguous keys left alone, bad leak pattern UNREAD, stale labels removed, milestone list checked before writes, finding detail field, mine closes when it ran); HLT-7 timing in its own script
- health-prd: review cycle 2 (one issue per finding identity, stale labels alone update, Mine closes only rules that ran here, reopen unlabels only when labelled)
- health-prd: worker.py rereads its run record before the last save, so a merge recorded from outside is kept (159)
- health-prd: 159 row covers worker.py too, seen red
- health-prd: qa fixes (worker-save split, adopt listing, REFUSED[group], update-in-place grep)
- health-prd: re-render Tests tables for worker-save-159
- Merge origin/main (docs-format, v0.22.0) into loop/health-prd
- health-prd: HLT-7..9 rows seen red; Tests re-rendered
- health-prd: new tests source reap.sh; a page-level finding files on its page's milestone; next steps name each fix once
- health-prd: the judge is the session first, claude -p only with no session (owner's rule)
- health-prd: judge rows seen red; Tests re-rendered
- Merge origin/main (v0.27.0: automation-email, lane-control, step-budget) into loop/health-prd
- health-prd: fold the new modules into existing ones so the package stays at 99 files (Agensi limit)
- Merge origin/main (v0.27.1, guardrails-prd) into loop/health-prd
- Merge origin/main (v0.27.2, delivery-prd) into loop/health-prd: rows unioned, Tests re-rendered
- Merge origin/main (v0.27.3, prep-budget) into loop/health-prd: rows unioned, Tests re-rendered
- pr: record issue states and the lane's results
- Wiki: update pages for health-prd
- Wiki: update pages for health-prd
- pr: record issue states and the lane's results

### How to verify

1. Run `python3 skills/workflow-health/scripts/health.py check --skip controls` in this repo.
   Expect: twelve group headings, each with its angle, then Mine and one `HEALTH:` line, in under a minute, and no file changes (`git status` stays clean).
2. Run `python3 skills/workflow-health/scripts/health.py preview`.
   Expect: only `WOULD` or `SAME` lines and a `PREVIEW: N to write, nothing written` line.
3. Run `python3 skills/workflow-health/scripts/health.py triage`.
   Expect: the open health issues per feature with kind, count and age, and nothing written.
4. Run `python3 skills/workflow-health/scripts/health.py review` from a Claude session.
   Expect: a `judge: session` line, then a `JUDGE UNAVAILABLE` line naming a prompt file for an in-session subagent (with no session, as in the scheduled run, it says `judge: claude -p (no session)`).

Closes #124
Closes #158
Closes #159

## v0.27.3 - 2026-11-11

- Preparation budget: prep_budget_minutes, the lane's three timed parts, LANE_PREP_BUDGET, board and health lines, toy test
- Preparation budget toy test runs by section
- Preparation budget rows seen failing; Tests tables
- Wiki: update pages for prep-budget
- Wiki: update pages for prep-budget
- Review fixes: a test_record wrapper keeps the old rule, prep-alone cut recorded, race at the last moment, seconds with the override, steadier toy
- Fold the preparation-budget helpers into budget.py: the skill package stays at its 99-file cap
- Merge remote-tracking branch 'origin/main' into loop/prep-budget
- Wiki: update pages for prep-budget
- Wiki: update pages for prep-budget
- Wiki: update pages for prep-budget
- Wiki: update pages for prep-budget
- Merge remote-tracking branch 'origin/main' into loop/prep-budget
- Port the preparation budget onto main's layout (budget folded into lanekit.py, the pr bookkeeping and need_lane in role.py): the package stays at 99 files, every script under the cap
- Lane: re-render the Tests tables
- Wiki: update pages for prep-budget
- Wiki: update pages for prep-budget
- The pull request body's lane part drops the local log path (the private-name scan refused every body that held it); row
- Tests tables
- pr: record issue states and the lane's results

### How to verify

No manual steps were recorded.

## v0.27.2 - 2026-11-11

- delivery-prd: depth by size, set, resume and --again, goal budgets, private-name scan before pr, verdicts and GitHub touches; board budget and depth lines, mend resume step, bind self
- delivery-prd: delivery docs for depth by size, set, budgets, resume, the private-name scan and refusal codes
- delivery-prd: release bumps patch unless the goal set minor or major (170), protected base releases through a release PR (134, 154), private scan before merge, wiki and cut, wiki first-page fix and docs say published (129)
- delivery-prd: rows for DEL-5..DEL-9 and defect rows for issues 38, 117, 129, 134, 154, 170; merge-hold check
- delivery-prd: rows seen red on the old code; the scan-site control reads single-quoted calls and the scan entry points; the lane row checks the lane command
- Merge remote-tracking branch 'origin/main' into loop/delivery-prd
- delivery-prd: new toy tests source reap.sh (main's rule); Delivery Tests table rendered
- delivery-prd review: private scan masks a matching place, reads '++ ' lines and whole long lines, bounds git by the limit; plan_head and verdicts kept on an auto-approved plan; a worker's set is refused (test)
- delivery-prd review: a bump set after a refused merge binds; VERSION fixed by hand on the base releases at its tip; the merge hold counts the goal's own wiki pages; a waiting release PR shows under Issues; release shim moved to dev/toy/release-gh.py; tests for dirty restart, mismatch, existing release, late bump
- delivery-prd: merge.py scans the goal's pushed branch wherever it runs; Delivery and Monitoring pages refreshed (summary only)
- Merge origin/main (docs-format, v0.22.0) into loop/delivery-prd: both row sets kept, main's PRD pages kept, Tests re-rendered
- delivery-prd qa fixes: toy test # reads: headers declare the folders they glob; the scan-site control and size check move to test-scan-sites.sh so test-delivery-prd stays narrow; test-delivery-prd clears LOOP_ROLE; test-tree allows the release PR's merge
- Merge origin/main (monitoring-prd, v0.25.0) into loop/delivery-prd: flow.py's step_prompt carries the goal's decided depth; live_board keeps main's split and adds the depth-decided and budget lines; both row sets and both findings kept
- delivery-prd: fold modules to stay under the 99-file package cap: guards_ops.py and prbody.py into fit.py, release_pr.py into merge.py, board_budget.py into board_lag.py (two new skill files: fit.py, private.py)
- delivery-prd: keep main's Review stamps on Monitoring and Setup (a merge had restored older ones); CLAUDE.md and AGENTS.md entry block names the release skill's new first sentence (issue 129)
- delivery-prd: fold defect.py into fit.py (fit.py owed SLUG), so the goal adds one skill file net under the package cap
- Merge origin/main (deployments-format, v0.25.1) into loop/delivery-prd: both row sets kept, Tests re-rendered
- delivery-prd qa fixes: a LOOP_PRIVATE_NAMES file that doesn't exist refuses (PRIVATE_LIST) instead of passing as no list; small token budgets read 25k or 500 on the board; fit.py owed names a missing goal file (NO_GOAL_FILE)
- Merge origin/main (lane-control v0.27.0, step-budget v0.26.0) into loop/delivery-prd: defect.py's E-10 rule ported into fit.py; board_lag/board_budget lines now live in board_lines.py section 4; flow.py's --again gate and goal_state moved to role.py (flow.py under 20 KB); merge.py keeps main's HEAD_MOVED/BASE_MOVED checks, then my scan and requirement hold; both row sets kept; Tests re-rendered
- delivery-prd: lane check follows main's --tier flag; del6-full-lane description; Tests re-rendered
- delivery-prd: del6-full-lane seen red on the new lane layout; Tests re-rendered
- delivery-prd: fold budget.py into lanekit.py so the goal adds no skill file net (package stays at 99 of 99): flow, guards and lane.py use lanekit's budget functions
- Merge remote-tracking branch 'origin/main' into loop/delivery-prd
- pr: record issue states and the lane's results

### How to verify

1. Run `printf 'notes\n' > /tmp/names; LOOP_PRIVATE_NAMES=/tmp/names python3 skills/workflow-delivery/scripts/private.py check`.
   Expect: it prints `PRIVATE LIST: 1 pattern from $LOOP_PRIVATE_NAMES` and never prints the pattern itself.
2. Run `python3 skills/workflow-monitoring/scripts/live_board.py` from the main checkout while a goal is running.
   Expect: under the goal, a `budget:` line (minutes and tokens of its budget, or `budget: none set`) and a
   `depth decided:` line naming the goal's depth and why.
3. Run `bash dev/toy/test-delivery-prd.sh resume`.
   Expect: it kills a goal's review mid-step, shows `idea is already recorded ... (ALREADY_RECORDED)` when idea is
   rerun, and ends with `ALL PASS` after the review is resumed.
4. Run `bash dev/toy/test-delivery-release.sh protected`.
   Expect: every line is PASS, including the release landing through a `release/vX-<slug>` pull request with one
   GitHub release.

## v0.27.1 - 2026-11-11

- guardrails-prd: the Guardrails feature page (GRD-1..GRD-10, all Unreviewed), its Home row, README section, docs.tsv row and START.md entry
- guardrails-prd: review fixes (citations match their owners, no sentence claims a guardrail is on, README lines true today, docs.tsv sorted)
- pr: record issue states and the lane's results

### How to verify

1. Open docs/wiki/Guardrails.md (or the published wiki's Guardrails page).
   Expect: Problem, Usage, Requirements, Non-goals, Success metrics and Tests; GRD-1 to GRD-10, each **Unreviewed**, each part naming its owner feature and requirement ID or "new"; every Tests row reads not enforced.
2. Open the wiki's Home page and the README's "How to use Guardrails" section.
   Expect: a Guardrails row linking the page, the README section and milestone 11; the README table's four lines.
3. Run `python3 skills/workflow-docs/scripts/docs.py check`.
   Expect: `DOCS OK`.

## v0.27.0 - 2026-11-11

- lane-control: office-hours design (approved, spec review PASS after 3 rounds)
- lane-control: slot pool (slots.py), lane.py and tables.py out of role.py, locked row writes, ship record check
- lane-control: toy tests for the lane pool, operate waits and the load run (in progress)
- Merge origin/main (v0.20+, 144 commits) into loop/lane-control
- lane-control: a sweep stops only its own lane's toy processes; rows record pid and signal (issue 435)
- lane-control: the lane-control and load toy tests source reap.sh and register cleanup with toy_on_exit
- lane-control: a lane a poller may not signal (EPERM) counts as alive, not LANE_DIED
- lane-control: done-line rows (goal slug:N) coexist with criteria; a missing done line fails with its fix (issue 128)
- lane-control: test-lane-control passes 35/35; a hung prep commit no longer blocks the next one; the full Tests page is a prep path
- lane-control: done lines count only for goals still being built (issue 143)
- lane-control: merge.py refuses a moved PR head (exit 4) or a relevant base move (exit 2, fetch failure 3) (REG-4)
- lane-control: check-reads hooks isolated Python launches instead of flagging them (issue 173)
- lane-control: release notes and the CHANGELOG list each fixed issue with its defect test (REG-6)
- lane-control: settings lane_limit (flow file, 2), goal_lane_minutes (10), full_suite_minutes (30), goal_levels, ci_levels (REG-8)
- lane-control: test-summary and test-defect leave the repo root; regression.py reads suggests headers (issue 172, items 1 and 4)
- lane-control: lanes.py never maps a path inside .git (issue 178)
- lane-control: no-prompt guard in the new process-starting scripts; criteria-done control's goal is running; # reads: headers fixed; Tests page re-rendered
- lane-control: test-defect's repo copy carries the goals and the origin URL the Tests page needs
- Merge origin/main (owner re-review #497 and 36 more) into loop/lane-control
- lane-control: a reopened issue's defect test shows failing (issue reopened) (REG-6)
- lane-control: health warns on a goal lane over goal_lane_minutes or a full suite over full_suite_minutes (REG-7)
- lane-control: goal.py pr records issue states and the lane's row results in one bookkeeping commit before it pushes
- lane-control: prsteps writes no bytecode cache when it imports the regression modules
- lane-control: goal tier (tiers.py): a goal lane runs the rows its change reaches, never FULL but at pr or with no merge-base; ROWS summary; FULL_TIMEOUT; run --kind (REG-4)
- lane-control: Regression commands document --tier goal, its lines and --kind
- lane-control: prsteps adds a new bookkeeping file before committing it, so pr never leaves it untracked
- lane-control: each lane child gets its own TMPDIR and a leased port base (REG-8)
- lane-control: references/lanes.md: which tests run when, every lane message with its exit and fix, clocks, settings, upgrade, alternatives
- lane-control: test-lane-messages.sh: every lane message code has a row in references/lanes.md
- lane-control: the workflow test kind, tests.py list --kind, one format checked across summary, wiki and health; defect rows owed only when the branch proved them (E-10)
- lane-control: test-goal-release.sh takes a toy goal to merge and release; rows for the workflow kind, list --kind, one format and E-10
- lane-control: the workflow kind, list --kind, one format, E-10 and goal-to-release rows seen failing on the old code
- lane-control: results recorded for the workflow kind, list --kind, one format, E-10 and goal-to-release rows
- lane-control: the pr bookkeeping commit re-renders the Tests tables it changes and says when it fails
- lane-control: a local run's GitHub-issue code moves from actions.py to issues_gh.py, no behaviour change
- lane-control: the pull request body carries the pr lane's LANE line and each row with why it ran (DX-21)
- lane-control: FLAKY (REG-9): a row whose raw result flipped on one clean commit, runner and python is flagged, sticky, shown in list, wiki and health, never reused
- lane-control: the plain run nightly records its suite time in the git common dir (SUITE_TIME); health.yml fetches CI's suite-time artifact
- lane-control: regression.yml takes a checked dispatch target (BAD_TARGET), runs ci_levels on schedule and tags, and uploads its suite time
- lane-control: narrow maps the modules an importlib user loads by quoted name; check-reads counts no read of a missing file (#173)
- lane-control: rows for FLAKY, the suite time and the CI dispatch target and ci_levels
- lane-control: the FLAKY, suite-time and CI target rows seen failing on the old code
- lane-control: regression-runs.tsv writes the flaky cell only on a flagged line, so the upgrade and same-day merges change no other line
- lane-control: results recorded for the FLAKY, suite-time and CI target rows
- lane-control: issues_gh.py carries the no-prompt guard like every script that starts gh (DEL-10)
- lane-control: the pr bookkeeping carries a lane row's flaky flag into regression-runs.tsv
- release: fixes.py folds into wiki.py as fixes_lines and fixes_since
- health: timing.py folds into cost.py as timing_rows
- health: the workflow text says cost.py where it said timing.py
- regression: flaky.py folds into tiers.py as flaky_apply
- regression: issues_gh.py folds into runs.py as sync_issues
- regression: references/lanes.md becomes the Lanes section of references/commands.md
- listing: commands name fixes (tests.py) and reads (regression.py)
- delivery: tables.py and prsteps.py become lanekit.py, with copies of the slots.py pieces lane.py uses
- toy: test-tiers and test-ci-target declare the folders lanes_cli.py check says they read
- monitoring: session_tool.py folds into session_bind.py
- monitoring: board_runs.py, board_lag.py and status_graph.py fold into board_page.py
- lane-control: record checks the step order before the lane; the pr-body defect check skips the folded lane rows
- lane-control: the six rows seen failing on the old code, passing; Tests tables re-rendered
- lane-control review: merge guards fail closed, wiki-only head moves merge, row timeouts hold, goal_levels and the over-limit note land
- Merge remote-tracking branch 'origin/main' into loop/lane-control
- lane-control review pass 2: orphan claims recover, a dead lane says LANE_DIED, the wiki-only move is the base's wiki folder only
- Regression, Setup and Monitoring pages reviewed against lane-control's code commits (REG-4/7/8, SET-2 and the monitoring requirements already cover them; no wording change)
- Tests tables re-rendered
- lane-control review pass 3: wiki-only takes the trusted base and no symlinks, a status read never erases a live lane, fixes refuses without a known repo
- lane-control review pass 3: rows seen failing, passing; Tests tables
- lane-control qa: test-defect reads origin without -C $here (a root runner again), the reads headers declare the scripts folder, fixes accepts a non-GitHub origin
- Lane: re-render the Tests tables
- lane-control qa: test-lane-ports' 100-lease holder lives as long as the test, not a fixed 20 s
- lane-control qa: a lane child with no port lease leaves LOOP_LANE_PORT_BASE unset instead of inheriting an outer lane's range
- lane-control ship: merge.py refuses when a head was recorded but no base (it merged unchecked)
- Tests tables re-rendered
- Lane: re-render the Tests tables
- Merge origin/main (step-budget) into loop/lane-control
- Fit lanekit to test_budget_minutes: no FULL lane in the loop, deleted or unmapped files pick the rows that name them
- Merge remote-tracking branch 'origin/main' into loop/lane-control
- Lane: re-render the Tests tables
- pr: record issue states and the lane's results
- Fixes #435: test two-lanes-toy-435, seen failing 2026-11-10, passing
- Fixes #143: test done-lines-warning-143, seen failing 2026-11-10, passing
- Fixes #173: test lanes-trace-hook-173, seen failing 2026-11-10, passing
- Fixes #172: test narrow-root-172, seen failing 2026-11-10, passing
- Fixes #178: test repo-narrow-178, seen failing 2026-11-10, passing

### How to verify

P is the package's skills folder (for example `P=~/.claude/skills` or this repo's `skills`).

1. In an empty git repo run `python3 $P/workflow-setup/scripts/setup.py --bare`, add three land rows that can fail
   (`python3 $P/workflow-regression/scripts/regression.py add r1 --level land --command "sleep 20; test ! -e broken"`,
   r2 and r3 likewise), commit them, prove each with `regression.py red rN --break "touch broken"`, then start three
   `LOOP_LANE_LIMIT=2 python3 $P/workflow-regression/scripts/regression.py run land` at once.
   Expect: one prints `LANE_WAIT: 2 of 2 lane slots busy` naming the other two, and all three exit 0.
2. While a goal's qa lane runs, run `python3 $P/workflow-delivery/scripts/role.py lane-wait SLUG qa`.
   Expect: it blocks, then exits 0 with the `LANE qa ...` line.
3. Rerun one row by id (`regression.py run r1`), then start the goal's lane with `role.py lane SLUG qa`.
   Expect: `LANE_PREP: re-rendered the Tests tables (commit ...)`, then a passing lane.
4. After a ship lane passes, make one commit and run `goal.py record SLUG ship --file F --in-session`.
   Expect: `REFUSED (no try used): HEAD moved since the ship lane passed ...`; after `role.py lane SLUG ship`
   passes, the same record goes through.
5. On a toy goal that adds a file no row's `# reads:` header names, start its qa lane, then its pr lane.
   Expect: both print `UNMAPPED <path>: no row declares it. Note: ...` and run AFFECTED (the rows that name the
   file and the runners); neither prints `FULL`.
6. On a toy goal whose branch added a defect row linked to an issue and seen failing, run `release.py cut SLUG`.
   Expect: the CHANGELOG and the draft release notes list `Fixes #N: test <row>, seen failing <date>, passing`.
7. Write `abc\tfull\t1900\t2026-11-10` into `<git common dir>/loop/suite-times.tsv` of a toy repo and run
   `python3 $P/workflow-health/scripts/health.py check --family cost`.
   Expect: `WARN performance full-suite time: 31 min (limit 30, the full-suite limit) ...`.

## v0.26.0 - 2026-11-11

- Time budgets: tiers fit an in-loop test run, step budgets bound review and ship
- Budget rows seen failing then passing; REG-7 and DEL-8 Unreviewed; settings documented
- A rerun step starts without its earlier budget hit (review finding)
- Fold the test budget into runs.py: the package stays under 100 files; the guard against prompts
- Tests tables rendered; ledger
- Pages touched without a Usage edit, so no owner re-review is owed; header of test-budget
- Pages rendered
- Regression Usage: left rows are reused by a later lane
- Tier order: a goal's new rows run first
- Regression Usage: tier order

### How to verify

No manual steps were recorded.

## v0.25.1 - 2026-11-11

- No code changes

### How to verify

No manual steps were recorded.

## v0.25.0 - 2026-11-10

- WIP: monitoring-prd new modules (goal_state, dep_graph, issue_lines, prs, pool, replan, auto, govern_hook, checkin)
- Merge remote-tracking branch 'origin/main' into loop/monitoring-prd
- WIP: monitoring-prd call sites (live_board, sessions, session_bind, operate, board, monitor, watch, graph, settings, setup)
- monitoring-prd: toy suite, docs, review fixes (branch delete only when merged into base, quote-aware govern parse, PR prefetch)
- monitoring-prd: reviewed plan (unattended, gate pending) and review fixes
- monitoring-prd: regression rows for MON-4, MON-6..MON-12 and issues 94, 97, 111-115, 122, 175; old toy tests follow the new MON-4/MON-8 behaviour; operate.py run --board
- monitoring-prd: Verify by hand, wiki Usage lines, setup command map
- monitoring-prd: preview-auto verb
- monitoring-prd: commands reference for check-in, re-plan, full auto, pool and govern hook
- monitoring-prd: rows green; Monitoring Tests re-rendered
- review: a failed report frees its session without blocking a rebind; MON-9 timing assertion annotated
- review: cleanup runs git from the main checkout (a worker reporting from its own worktree kept the branch); only executing operate.py claims the operation session; wrappers no longer hide git writes; more risky words; malformed held.json tolerated
- review: specialist fixes (dead code, board uses its parallel PR lookup, auto.log escapes |, git pull and -c alias blocked, wrappers by basename, worker exit before git, stale health lock, offline fetch, repeated question keeps its auto decision, stronger MON-11 checks)
- review cycle 2: claim only when operate.py is executed (python flags, ./operate.py); wrapper flag values skipped; one merge check for freed_from and cleanup; repeated question matched by its words; MON-7 test checks real claims
- review final: the govern hook skips only wrappers, their flags and values, so a command that names git is never refused
- qa: no-prompt guard in the new scripts that start processes; SKILL.md back under 150 lines (new verbs as agent requests); narrow # reads: header; Setup and Documentation pages updated
- qa: govern hook sees through shell keywords; a non-number --attempt is refused; an unreadable config shows under Needs you; a bad since time is refused; pool add counts each id once
- Merge origin/main (docs-format, v0.22.0) into loop/monitoring-prd: both row sets kept, docs-format's pages kept with this goal's Usage lines added
- monitoring-prd: rows re-recorded after the merge; Monitoring and Tests pages re-rendered (MON-6..MON-12 rows now listed)
- monitoring-prd: MON-9's slow GitHub is a wrapper in its own test; the shared fake gh is back to main's
- Documentation page reviewed against this branch's fake gh commits: the fake gh is unchanged from main, no wording change needed
- Documentation page rendered (trailing blank line dropped)
- Rows re-run after the render; Tests re-rendered
- Issue 321: the reply hook checks the claimed operation session, so a one-line scheduled check-in reply is blocked and told the five missing parts
- Issue 321 row seen failing then passing; Tests re-rendered
- Merge origin/main (estimate-model, automation-email, v0.24.0) into loop/monitoring-prd: estimate ranges kept beside the graph, pool and check-in changes; both row sets kept; Tests re-rendered
- monitoring-prd: dep_graph.py, issue_lines.py and prs.py merged into board_lines.py, behaviour unchanged, so the skill package fits its 99-file cap with room (98)
- monitoring-prd: goal_state.py merged into graph.py (its state logic), behaviour unchanged; the skill package is at 99 files

### How to verify

1. In the main checkout, run `python3 skills/workflow-monitoring/scripts/operate.py run --once`.
   Expect: one headline line, then All sessions, Dependencies, Needs you and Coming up; no `LIVE BOARD` block.
2. Run `python3 skills/workflow-monitoring/scripts/monitor.py report`.
   Expect: the live board, with Dependencies drawn top to bottom (`[>]`, `[ ]`, `<-`, a `|`/`v` between bands and a legend), no line wider than 60 characters, and a HELD OR FREEZING section.
3. Run `python3 skills/workflow-monitoring/scripts/pool.py status`.
   Expect: one line `pool: F free, B busy, T total (target 20)` with this repo's counts.
4. Pipe a routine question into the full-auto check: `echo "Which helper name?" | python3 skills/workflow-monitoring/scripts/auto.py decide-text --kind routine --recommend a`, then the same with "Delete the cache?".
   Expect: `AUTO` for the first, `WAITS: it mentions delete` for the second.
5. Pipe two commands into the govern check: `echo "git -C . commit -m x" | python3 skills/workflow-monitoring/scripts/govern_hook.py check`, then `echo "git status" | ...`.
   Expect: `BLOCK: git commit`, then `PASS`.
6. Run `python3 skills/workflow-monitoring/scripts/replan.py plan` twice.
   Expect: the first run lists each running goal's start with its reason (or REPLAN: no change); the second prints `REPLAN: no change`.

## v0.24.0 - 2026-11-10

- Mail one digest per round, file issues on feature milestones, show round cost
- Rows for the round's mail, milestones and cost; Automation wiki; Verify by hand
- Keep the milestone title when milestones can't be read; settings reference; test expectations for feature placement
- Review fixes: verify SMTP TLS, find placed issues locally, keep placement on failed moves, no milestone POSTs on unreadable lists, stale reruns mail nothing
- Review pass 2: mail in its own job, keep placement on failed sets, make Backlog when missing
- Review pass 3: fix the spend's run listing, keep placement when milestones can't be read
- Disclose the mail hosts: api.cloudflare.com and the smtp_host
- QA lane: rounds.py turns prompts off; the mail test declares the files it reads
- Merge remote-tracking branch 'origin/main' into loop/automation-email
- test-automation-email.sh sources reap.sh (main's toy-cleanup rule) instead of its own trap
- test: name the held-issue key so the secret scan doesn't read it as a credential
- Rename templates.py to workflows.py: it holds the workflow texts, and a temp* name reads as scratch
- test: setup plans mail-test.yml beside health.yml (ship coverage audit)
- fix: a secret with a trailing newline neither leaks nor sticks a round; health still files when milestones can't be read
- fix: review pass 2 on the secret fixes; leave the Automation page for the owner to re-review
- fix: fix-check findings: owner local part from the trimmed address, no retry after a timeout, DONE names a closed milestone
- docs: feature milestones, the mail job and mail-test.yml across the health, regression and setup docs
- test: the mail test declares seed.py, which its setup case runs
- Merge origin/main (v0.22.0, docs-format) into loop/automation-email
- Merge remote-tracking branch 'origin/main' into loop/automation-email
- docs: Documentation Tests re-rendered for the ci-issue-backlog row
- docs: Tests re-rendered after the merges
- docs: Tests render matches the recorded runs
- Merge remote-tracking branch 'origin/main' into loop/automation-email
- Merge remote-tracking branch 'origin/main' into loop/automation-email
- Wiki: update pages for automation-email

### How to verify

1. Pick a sender and add its secrets in Settings, Secrets and variables, Actions: DIGEST_TO, DIGEST_FROM and either
   CLOUDFLARE_ACCOUNT_ID with CLOUDFLARE_EMAIL_TOKEN (a domain onboarded to Cloudflare Email Sending), or
   DIGEST_SMTP_USER with DIGEST_SMTP_PASSWORD plus `"digest_mail": "smtp"` in `.loop/config.json`. Time how long it takes.
   Expect: under five minutes once the domain or app password exists.
2. In the Actions tab, run the mail-test workflow.
   Expect: its log ends `MAIL: test sent (MAIL_SENT)`, and a mail titled "Automation digest: test from <owner/repo>"
   arrives within a minute.
3. Run the health workflow by hand.
   Expect: a new comment on the pinned Automation digest issue, grouped under milestone headings, with `round cost` and
   `email` rows; the run summary has a `## Round` line; one mail arrives with the same text as the comment.
4. Re-run that same health run (Re-run all jobs).
   Expect: no second comment and no second mail; the Email the digest step says `already sent for run ... (MAIL_ALREADY)`.
5. Open the health and regression issues on GitHub.
   Expect: each sits on its feature's milestone (Backlog only when no feature fits). Move one to Backlog by hand, run the
   health workflow again, and it stays on Backlog.
6. Search the run logs, the digest comment and the issues for your address.
   Expect: it appears nowhere.

## v0.23.0 - 2026-11-10

- Merge remote-tracking branch 'origin/main' into loop/setup-sync
- Built-in default flow: steps mapped to built-in run delivery's own routine (issue 47)
- Entry point (entry.py, START.md) and agent files (agents.py), wired by setup; agent_files and template_repo settings
- update both ways: --check, the release source archive, the repo half (sync.py) on workflow-update-vX, local fixes and propose (propose.py); fake gh serves archives and issues
- Board lag line for governed repos on an older template; test-sync parts for entry, agents, update, propose, board; MISSING only for stamped repos; no-hang guards
- Rows for SET-4, SET-5 and SET-10
- Docs: Setup SET-4, SET-5, SET-10 (approved wording, reviewed 2026-11-10), Usage with a sample; Monitoring, Documentation, Home, README, loop-files, skill pages; this repo's START.md, CLAUDE.md and AGENTS.md
- Verify by hand steps; Usage sample as an indented block
- update.py: shorter docstring
- Split test-sync: narrow builtin/entry/agents keep exact # reads:, wide update/propose/board move to test-sync-update.sh; operate-fit-3 scopes its wiki assertion
- entry.py write: splice the matched block (a stray close marker no longer multiplies the file), keep CRLF, accept a block at end of file; check reports stray markers (ENTRY_MARKER); docs check renders once
- agents.py apply: say wire's refusals and a failed entry write, stage only files inside the repo and outside .git
- update: a failed repo half no longer leaves an empty workflow-update-vX that reads as merged; a local fix matching the new copy is stamped, a dropped one is kept without holding check at behind; the repo half runs the sync.py just written; a checkout with no VERSION stamps nothing; PARTIAL whenever the skills were written
- test-adopt SET-4: the update branch changes only config, START.md and the agent files; a linked skills folder is left alone
- Docs: Setup and Documentation Usage for the review fixes (dropped local fix kept, a failed repo half safe to rerun, stray markers left for you)
- agents.py wire refuses any file without exactly one block (the rule entry.py write follows); update flushes before the repo half and runs it in-process when sync.py itself is a kept local fix
- test-sync-update: reset template_repo after the redirect check, so a full run passes
- fix(qa): ISSUE-001 — test-sync.sh update/board ran nothing and said ALL PASS; forward them to test-sync-update.sh, refuse an unknown part (exit 2)
- fix(qa): ISSUE-002 — entry.py read an indented example output's '- ' line as a Usage sub-bullet
- Docs: Documentation notes the Features table leaves an indented example block out
- test-sync.sh points update, propose and board at test-sync-update.sh instead of running it, so its rows stay narrow; Verify step 4 names that script
- builtin-flow: watch's suite check moves to test-builtin-watch.sh so test-sync.sh stays narrow
- test-sync.sh declares exact files; entry-adopt (same command as adopt-set-5) runs nightly, keeping a one-file change under half the land rows
- Merge origin/main (v0.22.0 docs-format) into loop/setup-sync: both sides' rows kept, docs-format's reviewed pages win with this goal's Usage entries re-added; entry.py reads a bullet Problem
- README front door rows for update, propose and agents; Home and Monitoring name the built-in routine and the lag line; workflow-docs SKILL.md back under 150 lines
- Documentation: entry names what it reads from each PRD page
- Merge origin/main (v0.22.1 estimate-model): both sides' rows kept, live board keeps the stall and lag lines; the lag line moves to board_lag.py so board_status.py stays under 20 KB

### How to verify

1. In this repo, open `.loop/START.md`.
   Expect: a "First five minutes" list, one part each for Loop, Release, Operation and workers, Docs, Regression, Health and Settings, a Features table naming all seven feature pages (Home is not one) with how to use each, and a Settings table with every repo setting and its value.
2. Open `CLAUDE.md` and `AGENTS.md` side by side.
   Expect: the same `` block in both, telling a session to read `.loop/START.md` first and listing the seven workflow skills.
3. Change one Usage bullet's first sentence in `docs/wiki/Setup.md`, then run `python3 skills/workflow-docs/scripts/docs.py check`.
   Expect: `STALE .loop/START.md: ... (ENTRY_STALE)` and exit 1; `python3 skills/workflow-docs/scripts/docs.py audit` rewrites it, and the check is back to `DOCS OK`. Undo the edit.
4. Run `bash dev/toy/test-sync-update.sh update` and `bash dev/toy/test-sync-update.sh board`.
   Expect: `ALL PASS (update)` (check shows what is new, apply lands `workflow-update-v1.1.0` and keeps the repo's data) and `ALL PASS (board)` (the live board lists `oldharbor runs template v1.0.0, older than v1.1.0`).
5. Run `bash dev/toy/test-sync.sh builtin`.
   Expect: `ALL PASS (builtin)`: a goal with a flow file whose steps are all `built-in` and no probe runs every step through delivery's own routine.

## v0.22.1 - 2026-11-10

- estimate-model: estimates from goal size and similar finished goals, ranges, pace, stalled goals under Issues
- estimate-model: docs name the estimate model; MON-4 scenarios rendered; rows seen failing once
- estimate-model: narrow test-estimates reads header so test-tree's one-file narrowing check passes
- test: status-graph comment matches the new step-time rule
- fix(qa): a goal at an off-flow step after a done entry sits at the next step
- docs: Monitoring Tests list est-offflow-done
- Merge remote-tracking branch 'origin/main' into loop/estimate-model
- test: estimate checks for worktree goal files, unlogged similar steps and held goals
- test: record the three new estimate rows seen failing; Monitoring Tests list
- docs: estimate rules in the Monitoring summary and monitoring references match the code
- fix: test-estimates.sh sources reap.sh like every toy test

### How to verify

No manual steps were recorded.

## v0.22.0 - 2026-11-10

- docs-format: DOC-4, DOC-5 and DOC-6 back to Unreviewed for rewording
- docs-format: enforce the documentation format (DOC-4..DOC-10), full Tests page, run links, issue milestones, cap default 10
- docs-format: Documentation page as the owner approved it (DOC-1..DOC-13), Usage and sub-bullet checks fitted to it
- docs-format: Tests rendered as tables, full Tests page generated; Documentation PRD Reviewed 2026-11-10
- docs-format: Delivery page as the owner approved it (DEL-1..DEL-9), Reviewed 2026-11-10
- docs-format: merged goals docs-count-gaps and prd-stamps into the plan; issues 104-107 rows run and passing
- docs-format: Delivery's merge.py Usage entry says what it prints, re-reviewed
- docs-format: Monitoring page as the owner approved it (MON-1..MON-11), Reviewed 2026-11-10
- docs-format: Regression page as the owner approved it (REG-1..REG-9), Reviewed 2026-11-10
- docs-format: Monitoring Problem in three bullets, as the owner approved
- docs-format: Health page as the owner approved it (HLT-1..HLT-9), Reviewed 2026-11-10
- docs-format: Setup page as the owner approved it (SET-1..SET-10), Reviewed 2026-11-10
- docs-format: Home as one features table, README How to use, Setup Problem reworded, MON-12 Session pool
- Merge origin/main (v0.20.0, automation) into loop/docs-format: approved pages kept, rows unioned, Automation on Home and README
- docs-format: Automation page as the owner approved it (AUT-1..AUT-7), REG-4 on the Automation schedule
- docs-format: fix issues 125, 130, 133 and 156 (guide pages, milestone line, LOCKED hint and owner words, merged-base staleness)
- docs-format: full land run recorded (run links), Tests re-rendered; run-link rows grep fixed strings, reg2-wording follows the owner's 2026-11-10 REG-2, Tests page is not a feature group
- Merge origin/main (v0.21.0, loop-guards) into loop/docs-format: approved pages kept, rows unioned, Tests re-rendered
- health: a requirement with no test warns as not enforced, and fails only after 7 days Reviewed (HLT-2, REG-1, DOC-1); fixes #118
- docs-format: review fixes (run cells, CI-safe tests, sealed sub-bullets, smaller fixes); stamps re-sealed
- docs-format: Tests re-rendered
- docs-format: review-fix rows seen failing (15 rows)
- health: a malformed Reviewed date fails its row instead of crashing; files closed; only a soft UNREAD row is kept from counting as a pass
- docs-format: results recorded for the 19 rows never run on this branch; Tests re-rendered
- Merge origin/main (v0.21.1, toy-cleanup) into loop/docs-format: approved Regression page kept, Tests re-rendered
- docs-format: new toy tests source reap.sh and register cleanup with toy_on_exit (toy-no-leftovers from main)

### How to verify

1. Open `docs/wiki/Home.md`.
   Expect: the title, `## Features` and one table with Feature, What it does, How to use and Milestone; seven rows,
   nothing else.
2. Open the README on GitHub and click a Home row's "How to use" link.
   Expect: it lands on that feature's "How to use" table of phrases you can say, with no command syntax.
3. Open `docs/wiki/Delivery.md`.
   Expect: Problem as "I ..." bullets, Usage as one `command — what it prints and refuses` bullet per command,
   Requirements under Functional and Non-functional with sub-bullets, and Tests as a table whose test names link to
   the Tests page.
4. Follow one test link into `docs/wiki/Tests.md` (on the published wiki, after release).
   Expect: it jumps to that test's row under its feature, with result, date, run link and seen-failing date.
5. Run `python3 skills/workflow-docs/scripts/docs.py check`.
   Expect: `DOCS OK: 8 pages`.
6. In a scratch copy, change a word in any page's Problem to `script`, then run the same check.
   Expect: `FORMAT <Page>:<line>: Problem: DOC-8 ...`, naming the page, line, section and rule.

## v0.21.1 - 2026-11-10

- Merge remote-tracking branch 'origin/main' into loop/toy-cleanup
- dev/toy: every toy test reaps the processes it started (issue 100)
- dev/toy: defect test for issue 100, no toy test leaves a process running
- regression: toy-no-leftovers seen red 2026-11-09 (reaper stubbed out)
- dev/toy: reaper judges a hidden-env process by its nearest known ancestor
- Merge origin/main (review-depth, v0.12.1) into loop/toy-cleanup: both regression rows kept, test-review-depth.sh sources reap.sh
- fix(qa): sweep stops a dead test's system-binary child; reap.py rejects bad options
- Merge origin/main (board-estimates and earlier) into loop/toy-cleanup: both rows kept, the 8 new toy tests source reap.sh, test-narrow uses toy_on_exit
- test-no-leftovers.sh declares # reads: dev/toy/ (main's lanes header rule)
- Merge remote-tracking branch 'origin/main' into loop/toy-cleanup
- Merge remote-tracking branch 'origin/main' into loop/toy-cleanup
- test-automation.sh (new on main) sources reap.sh
- Merge origin/main (loop-guards, v0.21.0) into loop/toy-cleanup: both rows kept, test-guards.sh sources reap.sh

### How to verify

No manual steps were recorded.

## v0.21.0 - 2026-11-10

- loop-guards: guards.py (rules per step start, no-try refusals, resume, touches, finished findings), worker refusal text, bind worktree/--cwd, pool lock, toy test
- loop-guards: regression rows (7, seen red), wiki Usage and Tests, Monitoring commands, goal Closes and verify steps
- loop-guards: review fixes (pool release locked, resume rechecks after reserve, exact undo, worker cwd always checked, null rules_at, marker rule gate, pr commits a synced goal file, exit 2 for no-try refusals, 10 refusals wait for the owner, touches path chars, slug check)
- loop-guards: review cycle 2 (resume reserves and saves under the pool lock; bind saves inside it; pr checks waiting first; the qa lane refusal counts as a refusal)
- loop-guards: qa fix: answer clears the refusal count after the owner wait
- loop-guards: listing declares reserve (and touches); DEL-3 row expects the waiting gate pr now checks first
- Merge remote-tracking branch 'origin/main' into loop/loop-guards
- Wiki: update pages for loop-guards

### How to verify

1. In a toy repo (`bash dev/toy/test-guards.sh /tmp/guards g2` builds one and leaves it), record a step whose reply has no
   DEPTH line: `LOOP_ROLE=worker python3 skills/workflow-delivery/scripts/goal.py record <slug> plan --file reply.txt --in-session`.
   Expect: `REFUSED (no try used): plan refused: no DEPTH line (rule depth-line, added in v0.12.1)`, exit 2, and the
   goal still running with tries 0 (`goal.py show <slug>`).
2. Mark a session goal stopped, then run `python3 skills/workflow-delivery/scripts/goal.py resume <slug> --why "check"` from the main checkout.
   Expect: `RESUMED <slug> at <step>`, status running, tries 0, and `resumed by operation session: check` in its log.
3. Run `python3 skills/workflow-delivery/scripts/goal.py record <slug> idea --file x` without LOOP_ROLE.
   Expect: a `REFUSED` line naming the goal's session, its worktree and `LOOP_ROLE=worker python3 .../goal.py record <slug> idea --file x`.
4. Run `python3 skills/workflow-monitoring/scripts/sessions.py bind <slug> <id> --cwd /tmp`.
   Expect: `REFUSED: session folder /tmp is outside the goal worktree ... (CWD_OUTSIDE)`; without `--cwd`, a `WORKTREE <slug>: <path>` line.

## v0.20.0 - 2026-11-10

- feat: scheduled health and digest (automation.py), regression routine switch and defect labels, Automation PRD page, REG-4/5 reworded
- test: Automation toy test with stub gh, rows for AUT-1..5 and REG-4/5; schedule rows move to Automation
- docs: Automation in the health and regression skills, README and wiki; new rows seen failing once, results recorded
- docs: Home lists Automation; the Setup page says setup writes both scheduled workflows
- fix: review (Backlog milestone before filing, digest state only after its comment, no hygiene on runners, off stops only the schedule, plain-cron check, no issue writes when the list fails, relabel only when needed)
- test: review rows seen failing once, results recorded
- docs: the health page says which groups the scheduled run files
- fix: review pass 2 (judge failure keeps the step green, cron fullmatch, custom secret name maps to the judge's variable, setup writes health.yml only with the skill in the repo)
- test: pass-2 rows seen failing once, results recorded
- docs: the setup page says when health.yml is written; the regression page states the cron rule
- docs: the health page says how the scheduled judge runs
- fix: pregate (the judge setting is judge_env, naming the secret without looking like one; old default cron literals in tests updated)
- docs: the health and setup pages name the Automation settings
- test: coverage for the foreign health.yml, the local dry-run digest, off on push and by hand, the regression schedule warning, local relabel and setup's health.yml choice
- test: coverage rows seen failing once, results recorded
- automation: judge_setup runs without the agent key; non-string judge_env and digest_owner refused or named; test header declares skills/
- docs: Automation and Health pages name the judge_setup key rule and the judge_env check
- workflow-regression SKILL.md back under 150 lines after merging main; Automation page: judge_setup takes trusted commands only
- docs: Regression page names the default schedule
- docs: design guide and setup skill name the scheduled workflows
- docs: Regression and Setup pages as merged with main (rebase conflict repair)

### How to verify

No manual steps were recorded.

## v0.19.1 - 2026-11-10

- No code changes

### How to verify

1. Run `bash dev/toy/test-board-estimates.sh` and read the printed board.
   Expect: the running goal shows `[build over by 30m]`, `30m left`, a finish time later than the on-time board, and no line wider than 60 characters.
2. Run `python3 skills/workflow-monitoring/scripts/board_status.py` in this repo.
   Expect: the step flow wraps at the `>` joints and no line runs past 60 characters.

Closes #93

## v0.19.0 - 2026-11-10

- Merge remote-tracking branch 'origin/main' into loop/board-held
- board-held: build in progress (graph pool reader, board held/freezing, sessions free/bind, watch fail-closed)
- Merge remote-tracking branch 'origin/main' into loop/board-held
- board-held: test-board-held.sh; watch texts back in watch.py so watch.py runs alone
- board-held: Monitoring page, commands reference (board states, handoff, messages), SKILL.md
- board-held: review fixes (assign claims a session under the lock, report saves before release, bind/free save under the lock, board crash guards, free wording) and review tests
- board-held: review cycle 2 (assign keeps an operator's bind, report says when a session wasn't freed, rebind restores a failed run, bind checks pid liveness, a merged goal keeps its evidence against late reports, board guards a malformed reports field) and tests
- board-held: review cycle 3 (assign rechecks its claim is still busy and saves onto the current run, mend refuses on an unreadable pool, commands doc names no removed flag), Monitoring page
- board-held: session_tool.py sets the no-terminal guard like every script that starts processes
- board-held: merge origin/main (review_depth); held goals show their depth line too
- board-held: Monitoring page names held goals' depth line and the session tool's no-terminal guard
- board-held: listing.json names the new free command (package disclosure rule)
- board-held: render the Setup Tests tables
- fix: pre-landing review fixes (assign gives a failed goal to its new session instead of misreading HANDED, watch still reports dead pids and questions on an unreadable pool, pool-fix and stale-freezing wording, listing names the lock file and mend)
- test: board-held coverage (mend and assign races, report saved but not freed, Finish, pool-only slot, failed-goal reassign, waiting bind, forced lock interleave), exit 1 on failure, held-all row
- test: held-all seen red on the pre-fix assign
- fix: assign treats only a failed or stopped try's session as replaceable; tests for a HANDED assign's freed claim, a bind back to the old session, and a goal running in a session
- fix: a manual assign refuses a goal that already has a worker; assign's final check sees a bind made during the send by its bound_at
- board-held: Monitoring page names assign's refusal and HANDED
- Merge remote-tracking branch 'origin/main' into loop/board-held
- board-held: # reads: header for test-board-held.sh (narrow-rows check from main)

### How to verify

1. In the main checkout after the merge, start a session with the app's own tools for a goal that isn't frozen yet, run
   `python3 skills/workflow-monitoring/scripts/sessions.py bind <new-slug> <session-id>`, then print the live board
   (`python3 skills/workflow-monitoring/scripts/board_status.py`).
   Expect: the bind prints `ASSIGNED ... not frozen yet`, and the board shows `<new-slug>` under Running goals at once,
   with `[freezing]` and `worker: session worker · <new-slug>`.
2. Look at a goal you put on hold (its session reassigned, its worktree kept) on the same board.
   Expect: it is listed under Queued goals ending in `held`, with `worker: none (held, ...)` and a `sessions.py bind`
   line naming it. It is not under Running goals and not called background.
3. Look at a session goal that failed once and was bound again, after its worker sent a new report.
   Expect: its next line is the newest report, not the old failure, and its bar line ends `try 2 of 3`.
4. After a goal's pull request opens, send `python3 skills/workflow-monitoring/scripts/sessions.py report <slug> --status running`.
   Expect: it prints `KEPT done for <slug>: ...`, and the goal still reads `next: merge the pull request` (or its merged report).

## v0.18.0 - 2026-11-10

- Merge remote-tracking branch 'origin/main' into loop/narrow-rows
- narrow-rows: # reads: headers, narrow closure (narrow.py), lanes_cli.py, check-reads.sh, test-tree.sh; REG-6 rows
- narrow-rows: the LANES_WIDE parity check compares a path where wide and narrow differ
- narrow-rows: real-repo header checks live in test-tree.sh; headers only in shell files; docs for # reads:
- narrow-rows: repo-level docs/health checks move to test-tree.sh; split /skills/ paths seen; lanes_cli.py prompt guard; trace fixes
- narrow-rows: rows seen red and run; REG-6 scenarios rendered
- narrow-rows: a table edit reruns its own rows and the rows that read this repo's table, not every row reaching regression.py
- narrow-rows: check-reads resolves the real interpreter (nested traces); Tests re-rendered
- narrow-rows review fixes: root-running scripts always; recursive reads need the folder; import lists; table readers through wrappers; deletions anywhere; check-reads per-pid hooks, pyc and copy mapping, group-killing timeout; narrow tests in test-narrow.sh
- narrow-rows: toy broad row declares skills/k/
- narrow-rows: lanes-table toy row that reaches regression.py without reading the table
- narrow-rows: a skill folder read as a whole (literally or via a variable) needs the folder declared; MD deletions; trace fixtures use run-time Python reads
- narrow-rows: whole-folder reads decided per command (cd/mkdir/PYTHONPATH/sys.path name only), cd-then-list, $d/sub, folder variables from sourced files; docs
- Merge remote-tracking branch 'origin/main' into loop/narrow-rows
- narrow-rows: # reads: headers for the scripts main added; workflow-regression SKILL.md back under 150 lines
- Wiki: update pages for narrow-rows
- Wiki: update pages for narrow-rows

### How to verify

1. In this repo, run `python3 skills/workflow-regression/scripts/lanes_cli.py check`.
   Expect: no output and exit status 0 (every test script a row names has a valid `# reads:` header).
2. Run `python3 skills/workflow-regression/scripts/lanes_cli.py affected skills/workflow-monitoring/scripts/batch.py`.
   Expect: `AFFECTED 81 of 225 rows (...)`, under half the land rows; with `LANES_WIDE=1` in front, all 225.
3. Run `python3 skills/workflow-regression/scripts/lanes_cli.py deps "bash dev/toy/test-live-board.sh 2>&1" --why skills/workflow-health/scripts/judge.py`.
   Expect: one chain of files from `dev/toy/test-live-board.sh` to `judge.py` (the live board runs health.py).
4. Delete the `# reads:` lines from `dev/toy/test-health.sh` and run step 1 again, then restore the file.
   Expect: `LANES-DECL-NONE dev/toy/test-health.sh:1: ...` and a `fix:` line, exit status 1.

## v0.17.0 - 2026-11-10

- Health keeps itself honest and the repo lean (HLT-6)
- HLT-6 on the Health page, Unreviewed; settings, skill and reference docs for test time, stale worktrees and controls
- HLT-6 Reviewed 2026-11-09 by the owner
- Toy test and regression rows for HLT-6
- HLT-6 rows seen failing; Tests tables; verify by hand
- docs: test times on the Regression page, the two health settings on the Setup page; importlib in health.py
- Health page summary for HLT-6; existing health tests follow the controls group and the judge's test time
- health-hygiene: review fixes (queued liveness, configured base, UNREAD over crashes, exact lane record, --skip refusal)
- health-hygiene: lean.py no-prompt guard (DEL-10); finding on flow.py starting a lane unasked
- health-hygiene: re-render the Delivery Tests table
- health-hygiene: re-render the Regression Tests table
- Merge origin/main into loop/health-hygiene
- docs: Health page covers UNREAD controls, own lane record and live goals
- Merge origin/main (v0.16.0) into loop/health-hygiene
- health-hygiene: ship review fixes (prompt env restored, NaN and non-object config are UNREAD, unreadable run record blocks removals, borrowed record never warns, controls never filed, --skip keeps the tests list)
- docs: health and regression references cover controls UNREAD, queued liveness, test time and lane record seconds (ship doc audit)
- Wiki: update pages for health-hygiene

### How to verify

1. Run `python3 skills/workflow-health/scripts/health.py check --group controls`.
   Expect: a `controls` group with one `PASS ... control: fires on its fixture` line per rule (twelve), then a green verdict.
2. Run `python3 skills/workflow-health/scripts/health.py check --group hygiene`.
   Expect: a `test-time` line with the land lane's seconds against `test_budget_seconds` (and, when it is over, the slowest rows and scripts), and `worktrees` and `local-branches` lines, each stale one with the exact command that removes it; nothing is removed.
3. Run `python3 skills/workflow-health/scripts/health.py preview --group hygiene`.
   Expect: no line for test time, worktrees or local branches.

## v0.16.0 - 2026-11-10

- fix: rows never write into the real GitHub run summary (issue 92)
- feat: every test in one format grouped by feature, in the run summary, the wiki and the health report
- docs: REG-2 in the owner's approved words (2026-11-08), rows proven failing once
- test: REG-2 wording and row descriptions seen failing once
- docs: tests.py, the grouped run summary and the row environment in the regression skill and page
- test: record the new rows' results; PRD scenarios show them
- fix: pre-landing review fixes (package heading, summary step isolation, bytecode, criteria row env, issue-state churn, nan)
- test: review rows seen failing once, results recorded
- docs: the health page says the full report lists the tests before its verdict
- docs: the documentation page describes the Tests line fields
- fix: review pass 2 (issue refresh time limit, pull-requests read, issues file kept whole, raw tsv, broken tests.py falls back)
- docs: the regression page states the row environment's limit and the issue-state refresh
- docs: the documentation page says what happens without tests.py
- Merge remote-tracking branch 'origin/main' into loop/regression-summary
- fix: keep the regression SKILL.md under 150 lines; tests.py detail moves to its references (issue 116 rule)
- test: coverage for local row env, tsv, empty list, unknown result, no-row issue refresh and health fallbacks
- test: coverage rows seen failing once, results recorded
- fix: ship review (issue refresh fits the time left, started is a number, older tests.py falls back, own temp name per writer, no table escaping in wiki lines)
- Merge remote-tracking branch 'origin/main' into loop/regression-summary
- docs: the regression page says the issue refresh fits the time left
- docs: the documentation page covers a too-old tests.py
- fix: only tests.py issues --write records issue states; a live run no longer dirties the checkout (ship review pass 2)
- docs: the regression page says only the issues command records issue states
- docs: references describe the Tests line kind and guards, the health TESTS block, the issue-state rule and .loop/regression-issues.tsv
- Wiki: update pages for regression-summary

### How to verify

No manual steps were recorded.

## v0.15.0 - 2026-11-10

- reply-hook: a Stop hook keeps the operation session's reply format; setup.py --reply-hook installs it; MON-5 proposed Unreviewed
- reply-hook: MON-5 rows seen failing and passing; Tests rendered; Setup page names --reply-hook
- reply-hook: check the owner's check-in layout (issue 123); review fixes: incremental classifier, latest signal wins, stale and synthetic messages skipped, tracked settings refused
- MON-5 Reviewed 2026-11-09 by the owner ("Approve MON-5")
- reply-hook: rows re-seen red and green on the check-in layout; Tests rendered; Setup page
- reply-hook: review cycle 2: refusal is the first output line only, calls whose result lands after a stop are kept, exact subcommands, bash -c and uv run, case-insensitive headings, fenced lines never headings
- reply-hook: review cycle 3: a denied call did not run; one-line fences and clock times no longer fool the layout check
- reply-hook: the hook keeps the no-prompt guard and answers --help, so it packages and runs alone
- Merge origin/main (v0.12.1: review-depth, operate-all known failure) into loop/reply-hook
- docs/wiki: Monitoring and Setup describe the reply hook as built
- docs/wiki: Monitoring keeps its Problem to three paragraphs
- Merge origin/main (v0.14.1) into reply-hook
- reply-hook: defect row for issue 123, Closes #123 in the goal
- reply-hook: issue 123 defect row seen red
- reply-hook: keep workflow-monitoring SKILL.md under the 150-line limit
- reply-hook: wiki Tests re-rendered; Monitoring Usage names install and on

### How to verify

1. Copy the example reply from `skills/workflow-monitoring/references/operation.md` (the block under "A reply that passes")
   into a file and run `python3 skills/workflow-monitoring/scripts/reply_hook.py check FILE`.
   Expect: it prints nothing and exits 0.
2. Run `echo "all quiet" | python3 skills/workflow-monitoring/scripts/reply_hook.py check -`.
   Expect: `it is not in the check-in layout (no All sessions, Dependencies, Needs you or Coming up section)`, exit 1.
3. In a scratch clone that has `.loop/config.json`, run `python3 skills/workflow-setup/scripts/setup.py --reply-hook` twice.
   Expect: `HOOK: added` and a NOTE the first time, `HOOK: already installed` the second; `.claude/settings.local.json` holds
   one Stop hook naming reply_hook.py, and `git status` does not list it.
4. In that clone, run `python3 skills/workflow-monitoring/scripts/reply_hook.py status`, then
   `python3 skills/workflow-setup/scripts/setup.py --reply-hook --remove`.
   Expect: `REPLY HOOK: installed, setting on, script found, ...`, then `HOOK: removed`.
5. Open the Monitoring wiki page.
   Expect: MON-5 reads `**Reviewed 2026-11-09**` with the check-in layout sentence the owner approved.

## v0.14.1 - 2026-11-10

- skill-size: office-hours design
- skill-size: plan after review
- skill-size: move SKILL.md detail into references; tests for issue 116
- skill-size: red dates, Setup Tests, verify steps
- skill-size: Delivery and Documentation pages name the moved detail
- skill-size: review: the tokens pointer says when to read it
- Merge remote-tracking branch 'origin/main' into loop/skill-size
- skill-size: Delivery page names the token rule SKILL.md points to

### How to verify

1. Run `wc -l skills/workflow-delivery/SKILL.md skills/workflow-docs/SKILL.md`.
   Expect: each is under 150 lines.
2. Run `bash dev/toy/test-board.sh | tail -1`.
   Expect: it prints ALL PASS, with no "over 150 lines" line above it.
3. Open `skills/workflow-docs/references/commands.md` and go to "Moved from SKILL.md".
   Expect: the six-item PRD page list, Review locks, Tests follow on their own and New and old pages, each in full.

## v0.14.0 - 2026-11-10

- docs check: close the four count gaps (issues 104-107)
- docs-count-gaps: record the four defect tests as seen failing
- docs count review fixes: workflow-ready only, code after a heading or fence, thematic breaks, a wrong defect count fails
- Merge remote-tracking branch 'origin/main' into loop/docs-count-gaps
- Documentation: the check bullet says a stated defect tests count is checked

### How to verify

1. In a scratch copy of the repo, add the line `The repo has twenty workflow-ready skills.` to README.md and run `python3 skills/workflow-docs/scripts/docs.py check`.
   Expect: a line `COUNT README.md: says twenty workflow-ready skills, the repo has 7` (the real number of skills).
2. Replace that line with a blank line followed by `    The repo has twenty skills.` (four leading spaces) and run the check again.
   Expect: no COUNT line for README.md.
3. Run `bash dev/toy/test-criteria.sh | grep "(10[4-7])"`.
   Expect: four PASS lines, one per issue 104 to 107.

## v0.13.1 - 2026-11-10

- regression-all: record every row, move slow rows to nightly, fix two failing rows
- regression-all: review fixes for the workflow timeout, dash dates and test waits
- regression-all: the longest-chain check now compares the finish time with the chain
- regression-all: set row levels from measured suite times, and give the workflow room
- regression-all: re-record every row, and bring three wiki pages up to date
- regression-all: second review pass fixes
- regression-all: wiki pages follow the second review pass
- regression-all: third review pass fixes to the workflow runner and seen dates
- regression-all: wiki pages follow the third review pass
- Merge remote-tracking branch 'origin/main' into loop/regression-all
- Merge remote-tracking branch 'origin/main' into loop/regression-all
- regression-all: re-record every row on the code merged with v0.12.0
- fix: pre-landing review fixes
- docs: regression skill docs give the date-only seen rule and the workflow runner limits
- Merge remote-tracking branch 'origin/main' into loop/regression-all

### How to verify

1. Open `docs/wiki/Regression.md` and `docs/wiki/Documentation.md` and read the Tests tables.
   Expect: every row shows its level (`both` or `nightly`) and a last result of `PASS` with a date, and no row says `not enforced`.
2. Open `.loop/regression.tsv`.
   Expect: every row of the suites that take 20 seconds or more (for example `operate-all`, `frozen-done-lines`, `no-pid-left-alone`) is at level `nightly`, faster ones such as `auto-release` stay `land`, and none was removed.
3. On GitHub, open Actions, then the `regression` workflow, and run it on this branch with "Run workflow".
   Expect: the run finishes green and its summary table lists every row as PASS.

## v0.13.0 - 2026-11-10

- Health: formal report, preview and file by group
- Health: guard, tests table
- Health: clean group still closes its issues
- Merge origin/main into loop/health-report
- List the preview and file commands; regression run log
- Merge origin/main into loop/health-report
- Render the wiki Tests tables after the merge
- fix: pre-landing review fixes
- fix: adversarial and targeted review fixes
- docs: health preview, file and report wording after review
- fix: pre-existing test failure in every-row-described
- fix: pre-existing test failure in dev/toy/test-operate.sh
- fix: pre-existing race in dev/toy/test-operate.sh
- Merge origin/main (v0.11.0) into loop/health-report
- Merge origin/main (v0.12.0, PRD pages) into loop/health-report
- docs: the toy gh keeps issue labels (Documentation page)
- docs: Health success metric counts only the groups the owner files
- docs: design guide rows for health filing and PRD pages
- Merge origin/main (v0.12.1) into loop/health-report

### How to verify

1. Run `python3 skills/workflow-health/scripts/health.py check`.
   Expect: line 2 reads `groups run: ...; skipped: ...`, then each group with every rule and a state, the Cost group titled `performance`, and one `HEALTH:` line last.
2. Run `python3 skills/workflow-health/scripts/health.py preview`.
   Expect: `WOULD open/update/close/reopen ... [health:<group>]` lines and a `PREVIEW:` line; no issue changes on GitHub.
3. Run `python3 skills/workflow-health/scripts/health.py file`.
   Expect: `REFUSED: file needs --group ...` and nothing written.
4. Open `docs/wiki/Health.md`.
   Expect: HLT-3 and HLT-4 carry the new wording marked `Reviewed 2026-11-08`, and Usage lists the four agent requests.

## v0.12.1 - 2026-11-10

- review_depth: full by default; every step states its depth, record checks it, the board and PR show it; setup writes it
- Rows link to criteria; Monitoring and Setup pages name review_depth
- Review (full) fixes: fill-repo keeps _help, setting read from the base branch, markers from both flow files and malformed ones refuse, skips not held to full, DEPTH a line of its own, rerun clears depth, setup validates, docs
- review-depth rows seen red; Tests tables
- Merge remote-tracking branch 'origin/main' into loop/review-depth
- Merge origin/main (test-lanes, v0.11.0) into loop/review-depth: lane and depth in the step prompt, both row sets, goal.py's in-session check moved to role.py to stay under its size limit
- Merge origin/main (prd-format, v0.12.0) into loop/review-depth: main's PRD pages and Given/When/Then rows kept, depth rows and page sentences re-added, tables re-rendered

### How to verify

1. Run `python3 skills/workflow-setup/scripts/settings.py reference | grep review_depth`.
   Expect: one row, `review_depth`, default `full`, with a one-line explanation.
2. Open `.loop/config.json`.
   Expect: `"review_depth": "full"` and its explanation under `_help`.
3. On the next goal, run `python3 skills/workflow-monitoring/scripts/live_board.py` while it runs.
   Expect: under its `worker:` line, a `depth:` line listing each recorded step's depth and `(setting full)`.
4. Open that goal's pull request.
   Expect: under Result, each step ends with `(depth full)`.

## v0.12.0 - 2026-11-09

- workflow-docs: PRD page contract, review lock and prd command
- docs/wiki: every feature page is a PRD; rows are Given/When/Then scenarios
- dev/toy: test-prd.sh, PRD fixtures in the existing toy tests, new rows
- docs: PRD page, review PAGE|ID, prd and convert in the skill, commands and README
- Rows seen failing once; Tests and Home re-rendered for the PRD pages
- dev/toy: test-batch reads a row from the scenario Tests
- criteria.py: review/unreview PAGE takes only an exact feature page name
- prd.py convert: keep a title-less page's first heading; a missing Non-goals goes before Success metrics
- docs/wiki: Documentation Usage says review/unreview PAGE takes the exact page name; convert's fixes
- prd-format: DOC-1, DOC-2 and DOC-3 Reviewed 2026-11-08 by the owner ("Approve")

### How to verify

No manual steps were recorded.

## v0.11.0 - 2026-11-09

- test-lanes: regression.py run --reuse reuses a branch's last run and reruns only affected rows
- test-lanes: delivery runs the regression lane once in qa and reuses it in ship and pr; REG-6 Unreviewed
- test-lanes: lanes ignore the loop's own bookkeeping files; toy fixtures start goals clean and proven; Tests table rendered
- test-lanes: a script's own cd to the repo root doesn't make its row always run
- test-lanes: REG-6 Reviewed by the owner ("REG-6 reviewed, approved")
- test-lanes: release and loop files no row's own scripts name no longer rerun every row
- test-lanes: stopping a lane stops its whole run; stale lane jobs never hang
- test-lanes: rename lanes.py's skill-name regex so the secrets scan stops reading it as a credential
- test-lanes: only the last STEP line can skip the qa lane; a run whose rows leave files is never recorded; reused known rows count as known
- test-lanes: a PENDING qa reply never skips the lane; a run whose rows leave files drops the old record
- docs: test-lanes docs name the last-STEP qa rule, the dropped record and the --reuse usage line
- docs: Delivery page describes the regression lane (qa runs it once, ship and pr reuse it)

### How to verify

No manual steps were recorded.

## v0.10.1 - 2026-11-09

- The docs check fails on counts that drift from the code
- Rows for the count check and issue 39
- Both rows seen failing on the old check
- Review: glob at the top; say which counts need criteria on
- Review fixes: the count check reads only prose, and says why it skipped
- Mark DOC-6 Reviewed, on the owner's words
- Review pass 2 fixes: read prose the way a reader does
- Review pass 3 fixes: no crash, any repo's ids, code as Markdown renders it
- Home: a feature page has up to 6 criteria, as the README now says
- fix(qa): ISSUE-001 — describe DOC-6's two tests
- fix: pre-landing review fixes, and the coverage audit's tests
- fix: a skip covers only its own line, and the Criteria heading allows spaces
- Merge remote-tracking branch 'origin/main' into loop/docs-counts

### How to verify

1. Run `python3 skills/workflow-docs/scripts/docs.py check` in the repo.
   Expect: `DOCS OK`, because the README and design guide say seven skills and there are seven.
2. Change "the seven skills" to "the eight skills" in `skills/design-guide.md` and run the check again.
   Expect: `COUNT skills/design-guide.md: says eight skills, the repo has 7`, and exit code 1. Undo the change.

## v0.10.0 - 2026-11-09

- session-workers: plan step, in-session flow steps, sessions.py
- MON-1 and MON-2: the owner's new wording, reviewed
- Worker sessions: assign, rename, report, reuse, background fallback; steps run in the session; board shows the session
- Docs: worker sessions are the default worker
- Delivery page: steps run inside the worker session
- Delivery page: steps run inside the worker session
- Review fixes: never re-record a stale in-session reply; try a new session before falling back
- QA fixes: pool file renamed session-pool.json, MON-1 test follows the new wording, SKILL.md files under 150 lines
- sessions.py no-terminal guard; wiki pages follow the review fixes
- goal.py record --in-session: record a step the worker session ran
- record-in-session row seen red; Tests tables
- Review (full) fixes: session goals hold a slot and keep watch alive, answers reach the session, results checked and wrapped up, worktree in the goal message, quiet sessions under Issues, resume resets the worker
- listing.json discloses the sessions.py commands
- fix(qa): a hung session tool is cut off with its children at the timeout, then given up for the run
- Session tool calls: output to a file, interrupts kill the tool, the timeout is checked, a hang lasts one round
- Tests tables after the land run; Monitoring page names the session tool timeout

### How to verify

1. From the main checkout, run `python3 skills/workflow-monitoring/scripts/live_board.py`.
   Expect: each running goal has a `worker:` line under its step flow, `session worker · <goal>` for a goal in a worker
   session and `background (<why>)` for one in a background process. No goal that moved into a session shows as failed.
2. Run `python3 skills/workflow-monitoring/scripts/sessions.py list`.
   Expect: each worker session with its state (busy or free), its name `worker · <goal>` and its goal.
3. In a worker session, run `LOOP_ROLE=worker python3 skills/workflow-delivery/scripts/flow.py <slug> review` in the
   goal's worktree.
   Expect: it prints `IN SESSION review: no headless agent`, the skill to run and the reply path, and starts no process.

## v0.9.3 - 2026-11-09

- stale-groups: remove leftovers of removed groups, add defect test
- stale-groups: render Delivery tests
- Merge origin/main into loop/stale-groups
- chore: bump version and changelog (v0.9.2)

### How to verify

1. Run `bash dev/toy/test-stale-groups.sh`.
   Expect: it prints `PASS: no removed feature group comes back`.
2. Run `python3 skills/workflow-health/scripts/milestone.py features`.
   Expect: only Delivery, Documentation, Health, Monitoring, Regression and Setup are listed.
3. Open the repo's Milestones page on GitHub.
   Expect: Release and Milestones are closed; Delivery, Documentation, Health, Monitoring, Regression, Setup and Backlog are open.
4. Run `grep -n "Criteria and tests" skills/design-guide.md`.
   Expect: no output.

## v0.9.2 - 2026-11-09

- Remove every leftover of the removed feature groups (Release, Milestones, Criteria and tests) from the wiki and skill files
- Relink regression rows that pointed at removed Release criteria
- Add a defect test for issue 89 that fails if a removed group name comes back

### How to verify

1. Run `bash dev/toy/test-stale-groups.sh`.
   Expect: it prints `PASS: no removed feature group comes back`.
2. Run `grep -n "Criteria and tests" skills/design-guide.md`.
   Expect: no output.

## v0.9.1 - 2026-11-09

- Usage as agent requests: command maps, docs check, DOC-6
- Trim SKILL.md files under 150 lines after command maps
- Wiki: update pages for usage-as-skills

### How to verify

1. Open `docs/wiki/Monitoring.md`.
   Expect: every Usage line is a `/workflow-monitoring ...` command or a plain request, and no line names a `.py` file.
2. Open `skills/workflow-monitoring/SKILL.md` and find `## Command map`.
   Expect: a row `/workflow-monitoring operate` mapped to `python3 scripts/operate.py run`.
3. Put a `.py` file name in any wiki Usage line and run `python3 skills/workflow-docs/scripts/docs.py check`.
   Expect: a `USAGE` line saying it names a script, with the fix.

## v0.9.0 - 2026-11-09

- live-board: replace the status block with the live board (MON-4, MON-5)
- live-board: regression rows
- live-board: review fixes
- Wiki: update pages for live-board

### How to verify

1. Run `python3 skills/workflow-monitoring/scripts/board_status.py`.
   Expect: it prints a `LIVE BOARD` header (repo, local time, version, health), then Issues, Running goals (each with a 10-cell bar, percent, time left, a step flow with the current step in brackets, and a `next:` line), Queued goals, Dependencies (arrows like `a --> b`) and a single Finish line, with no merged list, milestones, token tables or done-line lists.
2. Run `bash dev/toy/test-live-board.sh`.
   Expect: it ends with `ALL PASS`, after checking the board line by line.
3. Run `python3 skills/workflow-monitoring/scripts/board.py cadence`.
   Expect: it prints `CADENCE 30`.

## v0.8.9 - 2026-11-09

- wiki-sync: release step refreshes every stale page, toy test, pages
- wiki-sync: release step refreshes every stale page, toy test, pages
- wiki-sync: verify steps, test row run
- Merge remote-tracking branch 'origin/main' into loop/wiki-sync
- wiki-sync: update the Needs you assertion to the current board line

### How to verify

1. Run `python3 skills/workflow-docs/scripts/docs.py check`.
   Expect: it prints `DOCS OK`.
2. Run `python3 skills/workflow-release/scripts/wiki.py prepare wiki-sync`.
   Expect: it prints `WIKI CURRENT`, the same verdict as step 1.
3. Run `bash dev/toy/test-wiki.sh`.
   Expect: every line is PASS, including `prepare lists the unmapped stale page` and `merge publishes the refreshed page`.

## v0.8.8 - 2026-11-09

- operate-fit-3: current wiki line, flow chart, local times
- Merge remote-tracking branch 'origin/main' into loop/operate-fit-3

### How to verify

1. Run `python3 skills/workflow-monitoring/scripts/board_status.py` in a repo with queued goals that have `depends-on` links.
   Expect: under Roadmap an arrow chart (`[queued] a --> [queued] b`), and the last Roadmap line starts `longest path:`.
2. Run `python3 skills/workflow-monitoring/scripts/operate.py run --once`.
   Expect: Needs you has at most one `wiki (docs check)` line, and every time it prints shows your local zone name, never UTC.

## v0.8.7 - 2026-11-09

- doc-usage: criteria_max, Usage section, pages, tests
- doc-usage: pages, tests, rows, verify steps
- Merge origin/main into loop/doc-usage

### How to verify

1. Run `python3 skills/workflow-docs/scripts/docs.py check`.
   Expect: it prints `DOCS OK: 7 pages`.
2. Set `"criteria_max": 1` in `.loop/config.json`, run the same command, then put it back to 6.
   Expect: it prints a `CAP` line for every page with more than one criterion, naming `criteria_max`.
3. Open `docs/wiki/Health.md`.
   Expect: a Usage section between Summary and Criteria listing `health.py check`, `judge` and `run`.

## v0.8.6 - 2026-11-09

- operate-fit-2: clear stale wiki errors, know closed PRs, live-only Goals
- operate-fit-2: disclose the checkin command in listing.json
- Wiki: update pages for operate-fit-2
- Wiki: update pages for operate-fit-2
- Wiki: update pages for operate-fit-2

### How to verify

1. Run `bash dev/toy/test-operate-fit.sh`.
   Expect: it ends with ALL PASS, including the closed, healed and old goals section.
2. Run `python3 skills/workflow-monitoring/scripts/operate.py run --once` twice in a repo with goals.
   Expect: the first prints the block and Goals lists no old merged goals; the second prints one "Nothing changed" line.

## v0.8.5 - 2026-11-08

- operate: live status block, GitHub-merged goals, one quiet line
- operate: keep post-merge publish errors, keep milestone bars
- Merge remote-tracking branch 'origin/main' into loop/operate-fit
- Merge remote-tracking branch 'origin/main' into loop/operate-fit
- README: the roadmap graph shows the live goals
- Wiki: update pages for operate-fit
- Wiki: update pages for operate-fit

### How to verify

1. Run `python3 skills/workflow-monitoring/scripts/board_status.py` in a repo with a merged goal that once failed to publish its wiki.
   Expect: Needs you does not list that goal; only open asks and errors remain.
2. Merge a goal's pull request on GitHub, then run `python3 skills/workflow-monitoring/scripts/operate.py run --once`.
   Expect: the goal is not drawn and its number shows on the `merged: #N` line, never as awaiting merge.
3. Read the Roadmap section of that output.
   Expect: only running, queued and waiting goals, each with a 10-cell bar and time left, `<- waits on` arrows, and a Total line ending in `finish about HH:MM`.
4. Run `operate.py run --once` again straight away.
   Expect: one line starting `Nothing changed.`

## v0.8.4 - 2026-11-08

- Design docs for setup-fit
- Setup fits real repos: CI tests, allow-list refusal, feature pages, version habit, gitignore, private leak prefixes
- Skip tracked files in the gitignore check
- Merge remote-tracking branch 'origin/main' into loop/setup-fit
- Wiki: update pages for setup-fit

### How to verify

1. In a repo whose CI runs `bash scripts/run-tests.sh` and whose `.gitignore` holds `.loop/`, run `python3 skills/workflow-setup/scripts/setup.py --dry-run`.
   Expect: it lists the CI command as the check, prints `BLOCKED by .gitignore` with `!.loop/`, and a bare `claude -p` prints `REFUSED to call this done` with the line to add.
2. Run `bash dev/toy/test-setup-fit.sh`.
   Expect: it prints a PASS line.

## v0.8.3 - 2026-11-08

- Record each flow step's tokens from the agent's JSON output
- Trim release.py under 90% of 20 KB, no behaviour change
- Add worker.py cleanup, health fix line, verify steps and docs
- Keep the first merged branch's indent in cleanup; test it
- Test cleanup on the first listed merged branch
- Add cleanup to the listing's commands so the package check passes
- Merge remote-tracking branch 'origin/main' into loop/health-green
- Wiki: update pages for health-green

### How to verify

1. Run `bash dev/toy/test-tokens.sh`.
   Expect: it ends with ALL PASS, and a fake agent's step shows 175 tokens (input + output + cache-creation).
2. Run `wc -c skills/workflow-release/scripts/release.py`.
   Expect: it prints a number under 18432.
3. Run `python3 skills/workflow-health/scripts/health.py check --family hygiene`.
   Expect: no WARN line for findings or merged branches.
4. Run `bash dev/toy/test-cleanup.sh`.
   Expect: it ends with ALL PASS; `python3 skills/workflow-monitoring/scripts/worker.py cleanup --dry-run` lists merged loop branches without deleting any.

## v0.8.2 - 2026-11-08

- Fix wiki identity and bytecode causes; criterion tests for DEL-4 and REG-3
- Render Tests tables, record runs, verify steps
- Merge remote-tracking branch 'origin/main' into loop/regression-green
- Give the wiki revert a fallback identity; run docs rows as CI does
- Wiki: update pages for regression-green

### How to verify

1. Run `dev/toy/ci-env.sh bash dev/toy/test-wiki.sh` and `dev/toy/ci-env.sh bash dev/toy/test-adopt.sh`.
   Expect: both end with every line PASS (the first prints `PASS: merge publishes the wiki`, the second `ALL PASS`), with no bytecode setting and no git identity.
2. Open the Delivery and Regression wiki pages and find DEL-4 and REG-3 in their Tests tables.
   Expect: each lists a test (`pr-body-criterion`, `workflow-same-as-run`), not "not enforced".
3. Run `python3 skills/workflow-health/scripts/health.py check`.
   Expect: no FAIL line for DEL-4 or REG-3.
4. After merge, open the next GitHub Actions regression run and the issues list.
   Expect: the run is green and issues 58, 68, 69, 70, 71, 72 and 74 are closed with "Passing again".

## v0.8.1 - 2026-11-08

- Accept both depends: and depends-on: in queue lines
- Toy: both keys together, neither key
- Wiki: update pages for queue-key

### How to verify

1. Run `bash dev/toy/test-status-graph.sh`.
   Expect: it ends with ALL PASS, including "depends: and depends-on: parse to the same waits".
2. Open `skills/loop-files.md` and find the queue-line paragraph.
   Expect: it shows `depends: a, b` (or `depends-on:`) as the dependency key.

## v0.8.0 - 2026-11-08

- Health: Cost rule, judge command, HLT-2 and HLT-5 wording
- Compare judge exit codes with the check's
- Health: docs for Cost and the judge
- Verify by hand; milestones test follows issue numbers
- Merge origin/main into health-judge-4
- Health scripts: no terminal prompt, like the others
- Merge origin/main into health-judge-4; list judge
- Merge remote-tracking branch 'origin/main' into loop/health-judge-4
- Wiki: update pages for health-judge-4

### How to verify

1. Run `python3 skills/workflow-health/scripts/health.py check --family cost`.
   Expect: a `cost` group; each goal over `time_budget_minutes` or `token_budget` is a WARN naming its slowest or costliest steps, and `UNREAD cost tokens` prints if no recent goal recorded tokens.
2. Run `python3 skills/workflow-health/scripts/health.py judge`.
   Expect: the normal report and `HEALTH:` line, then `JUDGE (suggestions, never part of the verdict)` with criteria quality, test quality, performance and tokens, `Needs you`, candidate goals and next steps (or `JUDGE UNAVAILABLE: ...` if the judge fails), with the same exit code as `check`.

## v0.7.1 - 2026-11-08

- Merge main

### How to verify

1. Run `sed -n 84p .loop/goals/defect-tests.design.md`.
   Expect: the line starts with "Run the delivery loop on this design" and names no private skill.
2. Run `git grep -n 'goal_\*'`.
   Expect: no match in the design note.

## v0.7.0 - 2026-11-08

- Settings: one table, both halves written by setup, parallel 0 unlimited
- Guard the token budget read
- Merge origin/main into loop/setup-settings
- Wiki: settings in Delivery and Monitoring

### How to verify

1. Run `python3 skills/workflow-setup/scripts/settings.py reference`.
   Expect: a table of every repo and private setting, each with its default and a one-line explanation; `parallel` shows 0, unlimited.
2. Run `grep parallel .loop/config.json`.
   Expect: it prints `"parallel": 0`.
3. Run `bash dev/toy/test-settings.sh`.
   Expect: it ends with ALL PASS, after showing parallel 2 start two goals and parallel 0 start all four.

## v0.6.0 - 2026-11-08

- Defect tests: categories, delivery gate, health rule, worker release, no checks step
- Wiki summaries, Verify by hand, defect rows seen failing, run ledger
- Review fixes: finding ref match, docstring
- Merge origin/main into defect-tests
- Ledger and rows after merging main
- Wiki: defect-test gate in Delivery, defect links in Documentation

### How to verify

1. Open `docs/wiki/Delivery.md` and look at the Tests section.
   Expect: the criteria table, then a `### Defect tests` part listing the defects for issue 35 and pull requests 61 and 62, each linked to its source.
2. Run `bash dev/toy/test-defect.sh`.
   Expect: one `PASS:` line for each of wording, flow-steps, categories, defect-owed, health-closed, worker-release, pr-body, no-hang and known-defects, then `ALL PASS`.
3. Run `python3 skills/workflow-delivery/scripts/goal.py check anything`.
   Expect: an error saying `check` is not a valid command, because the checks step is gone.
4. Run `python3 skills/workflow-health/scripts/health.py check --family criteria`.
   Expect: no `defect-tests` FAIL line, because every issue or finding a goal says it fixed has a defect test.

## v0.5.0 - 2026-11-08

- Setup adopts a repo, update command, versioned package, design guide
- Rows, wiki, verify steps
- Setup: add only paths that exist
- Setup: --bare writes only config, queue and findings; older toy tests use it
- Merge main into loop/setup-adopt
- Wiki: update pages for setup-adopt

### How to verify

1. Run `bash dev/toy/test-adopt.sh`.
   Expect: it prints `PASS SET-1 SET-2`, `PASS SET-3`, `PASS SET-4 SET-5` and `ALL PASS`.
2. In a scratch git repo with a code folder and an unmarked `docs/wiki/Home.md`, run `python3 skills/workflow-setup/scripts/setup.py --dry-run`.
   Expect: a `FOUND:` line, then `add:` and `convert:` lines, and `DRY RUN: nothing written`.
3. Run `bash dev/package.sh --out /tmp/pk.zip`, then `python3 skills/workflow-setup/scripts/update.py --from /tmp/pk.zip --skills <a copy of skills/>`.
   Expect: `PASS: ... version 0.3.0`, then `INSTALLED:`, `AVAILABLE: 0.3.0` and a preview that writes nothing.

## v0.4.0 - 2026-11-08

- Show the roadmap as a dependency graph in the status block and board
- Wiki: roadmap graph and live step label

### How to verify

1. Run `bash dev/toy/test-status-graph.sh`.
   Expect: every line starts with PASS and the last line is ALL PASS.
2. Run `python3 skills/workflow-monitoring/scripts/board_status.py`.
   Expect: four sections in this order: Needs you, Roadmap, Total, Goals. Roadmap lists every goal under `level` headings, each marked merged, awaiting merge, running or queued, with a stage, a progress bar and a time left, and `<- waits on` for a goal that waits on another.
3. Read the Total section of that output.
   Expect: one line giving the longest chain of goals (`a > b > c`) with its time, which is shorter than the sum of every goal's time.
4. Open `docs/wiki/Monitoring.md`.
   Expect: MON-4 reads "Printout. Each check-in prints the same template as text: Needs you first, then the roadmap as a dependency graph ..." and is marked Reviewed 2026-11-08.

## v0.3.0 - 2026-11-08

- MON-1: rewrite for the dependency-graph planner
- operate: dependency-graph planner, operate command, base merge, worker guard, live reports, status block
- Regression: seen red for three operate rows; tighten the message check
- Review: drop unused cycle(), take the inbox atomically
- Merge origin/main into loop/operate; guard role.py against prompts
- Release v0.1.4 (operate)
- Undo the ship step's version bump: the release step owns the version
- Wiki: update pages for operate
- Merge origin/main into operate

### How to verify

1. From the repo root, run `bash dev/toy/test-operate.sh`.
   Expect: it prints a `PASS:` line for each part (dependency start, status block, reports, follow-up, worker guard, operate loop, base merge) and ends with `ALL PASS`.
2. Run `python3 skills/workflow-monitoring/scripts/operate.py run --once` on the base branch.
   Expect: it prints the five status sections (Needs you, Now, Next, Roadmap, Goals), then `DIGEST`, `CHANGED`, `NEXT_DELAY` and the board paths.
3. Run `python3 skills/workflow-delivery/scripts/goal.py check operate` in a plain shell.
   Expect: one line, `REFUSED: check is worker work; the operation session only assigns, watches and reports. Use: batch.py start NAME`.
4. Run `grep -n "MON-1" docs/wiki/Monitoring.md`.
   Expect: the line says `Reviewed 2026-11-08` and begins `Roles, start and planning.`

## v0.2.0 - 2026-11-08

- Give Documentation its one enforcing command: docs.py audit, template sheet, milestone links, release-note check
- Release step: a failed audit refuses instead of passing
- Merge origin/main into docs-command: rules read from the template sheet, six Tests columns
- Delivery page: the release step runs the docs audit

### How to verify

1. Run `python3 skills/workflow-docs/scripts/docs.py audit --dry-run`.
   Expect: `WOULD FIX` or `REWRITE` lines for what needs work, `UNTESTED` lines for Reviewed criteria with no test, and exit 1 while anything is left.
2. Open `skills/workflow-docs/references/template.md`, then change `max_criteria` in its rules block and run `python3 skills/workflow-docs/scripts/docs.py check`.
   Expect: `CAP` lines that follow the new number. Put it back to 5 afterwards.
3. Open `docs/wiki/Documentation.md`.
   Expect: a `Milestone:` line under the title linking its GitHub milestone.
4. Run `bash dev/toy/test-docs-command.sh`.
   Expect: every line prints PASS and the last line is ALL PASS.

## v0.1.3 - 2026-11-08

- Regression: descriptions, schedule setting, wiki test fix
- Regenerate workflow and wiki tables; guard mine.py
- Merge origin/main into loop/regression-format

### How to verify

1. Open `docs/wiki/Regression.md` and look at the Tests table.
   Expect: columns Criterion, Test, What it checks, Runs, Last result and Seen failing, each row with a plain one-line description.
2. In `.loop/config.json` set `"regression_cron": "5 4 * * 1"`, run `python3 skills/workflow-regression/scripts/regression.py workflow`, then `git diff .github`.
   Expect: the schedule line reads `cron: "5 4 * * 1"`. Set it back to `17 9 * * *` and run it again to restore.
3. After this merges, open the next run of the regression workflow on GitHub.
   Expect: `wiki-release` passes and issue 58 closes with "Passing again".

## v0.1.2 - 2026-11-07

- Run the level 2 design skill through an agent with tools, and say in the pull request how much of it ran
- Add workflow-health, milestones, batches of POCs and goals, and the operation role
- Make the regression workflow pass on GitHub
- Fit the package to Agensi's published rules: a seven-skill pack with its file contract under `shared/`
- Run on Codex at level 0, directly and as a monitored background agent

### How to verify

1. Run `python3 dev/package.py --out dist/agent-workflow-template.zip`, then `unzip -l dist/agent-workflow-template.zip | grep -c SKILL.md`.
   Expect: it prints PASS with a NOTE about `shell=True`, then 7.
2. Run `unzip -l dist/agent-workflow-template.zip | grep loop-files`.
   Expect: one line, `shared/loop-files.md`.
3. Open the repo's Actions tab, pick regression, and choose Run workflow on `main`.
   Expect: the run ends green, and every row prints PASS in its log.
4. Install the ZIP's seven `skills/` folders in an agent, and start one level 0 goal on a test repo.
   Expect: it ends at a pull request.

## v0.1.1 - 2026-11-07

- Add the regression workflow; record the Codex and CI-like runs
- Say what the Codex and CI-like runs proved

### How to verify

1. Open the repo's Actions tab on GitHub, pick regression, and choose Run workflow on `main`.
   Expect: the run ends green, and every row prints PASS in its log.
