<!-- workflow-docs -->
# Monitoring

Milestone: https://github.com/jcl2018/agent-workflow-template/milestone/6

Review: **Reviewed 2026-11-13** <!-- prd P=41bfc9ae R=15f81fda N=9967b317 M=0fde98a8 U=03828777 -->

## Problem
- I run many goals at once, and opening each session to see which are running, stuck or waiting on me doesn't scale; without the same check-in every time, a stuck goal can sit unnoticed for hours.
- I want one session that only governs: it starts every ready goal in its own worker session, passes my answers along, and never builds anything itself.
- I want the work to finish as fast as it safely can and run unattended: re-plan the graph from real progress, run as much as possible in parallel, answer workers' routine questions with the recommended option, and only ask me for what's truly mine.

## Requirements

### Functional
- MON-1: **Reviewed 2026-11-08** Roles, start and planning. One command starts the operation session and drives the whole process the same way every time. The operation session plans queued goals as a dependency graph and gives every goal whose dependencies are met its own worker session in the app, renamed worker · <goal>, running in parallel; it never builds. A goal waits only on goals it truly depends on; sharing files is not a reason to wait. When a worker session finishes, the operation session gives it the next ready goal, renaming it again. <!-- reviewed b9787a35 -->
  - One command starts the operation session and drives the whole process the same way every time.
  - The operation session plans queued goals as a dependency graph and gives every goal whose dependencies are met its own worker session in the app, renamed worker · <goal>, running in parallel; it never builds.
  - A goal waits only on goals it truly depends on; sharing files is not a reason to wait.
  - When a worker session finishes, the operation session gives it the next ready goal, renaming it again.
- MON-2: **Reviewed 2026-11-08** Live communication. Operation and workers talk through session messages: a worker reports each change of step or status as it happens, and its result when it ends (merged, failed or waiting, with the pull request); the operation session sends a worker its answer or a follow-up. Background processes are used only when the app can't start or reach a session, and the board says so. <!-- reviewed 53b98768 -->
  - Operation and workers talk through session messages: a worker reports each change of step or status as it happens, and its result when it ends (merged, failed or waiting, with the pull request); the operation session sends a worker its answer or a follow-up.
  - Background processes are used only when the app can't start or reach a session, and the board says so.
- MON-3: **Reviewed 2026-11-13** Live board <!-- reviewed 9b9ea4c3 -->
  - Report, dashboard and the artifact show the live board in the one fixed layout MON-4 lists; this requirement owns the board, and a check-in never prints it.
- MON-4: **Reviewed 2026-11-13** Live board layout <!-- reviewed bd9028c8 -->
  - `report`, `dashboard` and "Where do things stand?" print the live board in one fixed format: Issues first (only what is open now, each with its fix in plain words); then Running goals with progress bar, time left, step flow with the current step marked and the next step; then Queued goals; then dependency arrows; then one finish time.
  - Merged work, history and totals are left out; a stuck worker stays at the top of Issues until I answer.
  - Check-ins don't print this board; MON-5 owns the check-in reply.
- MON-5: **Reviewed 2026-11-13** Cadence and reply format <!-- reviewed eeace5fb -->
  - The operation session updates the board on a set cadence, 30 minutes by default and changeable, and at once whenever a worker reports something new, and each check-in prints only its reply layout, never the board.
  - Every check-in reply has the same layout: one headline line;
  - All sessions, one table of every session across my repos with what it is for, its status, progress, time left, tokens left and latest report;
  - Dependencies, a drawn graph marking what is running, holding, queued or stuck;
  - Needs you, each question numbered with its options and a recommended answer, or Nothing needs you; and last, Coming up, the next expected events and what I will need to do.
  - A hook that setup installs blocks a reply that doesn't follow this layout, saying what is missing; it never checks worker sessions or other repos, and one setting turns it off.
- MON-6: **Reviewed 2026-11-10** Clean up after every goal <!-- reviewed deb6802e -->
  - When a goal merges, its worker session is given the next ready goal or archived, and its worktree and branch are removed.
  - A merged report always frees the session (issue 175).
- MON-10: **Reviewed 2026-11-10** Re-plan at every check-in <!-- reviewed f6c13026 -->
  - At each check-in the operation session re-reads every goal's progress and re-plans the graph to finish soonest.
  - It starts every goal whose dependencies are met in a free or freed session, up to the slot limit, so no ready goal sits idle.
  - It merges goals that do the same thing or touch the same files for the same PRD, splits a goal that blocks others when part of it is ready, and reorders the merge line so the critical path goes first.
  - It never stops or restarts a running goal to re-plan, and every change is logged with its reason and shown in the check-in.
- MON-11: **Reviewed 2026-11-13** Full auto mode <!-- reviewed e3b3cf48 -->
  - A setting, on by default. When it is on, the operation session applies each routine recommendation without asking, logs the question, the answer and why, and lists them in the next check-in; only the decisions in the next bullet and those that need my own words wait under Needs you.
  - It never auto-answers a decision that is destructive (deletes data, a page, a repo or a deployment), that contradicts something I said, that spends money, or that changes a security or access setting; those wait under Needs you.
  - When a decision needs my words, I answer in the operation session, which records my message verbatim with the IDs it covers (sessions.py owner-words) for the workers to use.
  - Turning it off takes effect at the next decision.

- MON-12: **Reviewed 2026-11-10** Session pool <!-- reviewed 7a470c28 -->
  - The operation session keeps a pool of idle worker sessions, sized by a setting (default 20), and hands each ready goal one from the pool instead of starting a new session.
  - Because sessions can only be created from the desktop app, whenever the pool runs low the operation session asks me, at the desktop, to fill it, and it creates every missing session in one step on my word.
  - A finished goal's session goes back to the pool (MON-6), the board shows the pool as free, busy and total, and a goal that finds the pool empty waits under Needs you with the one action that fixes it.

- MON-13: **Reviewed 2026-11-12** Two layers per pod: one operation session governs every repo in its pod directly and talks to each worker, with no per-repo operation session; several pods may run concurrently and independently <!-- reviewed 7dca4de6 -->
  - A claim adds the session to every repo the pod follows and keeps the other sessions already claimed; nothing refuses or warns when a second operation session runs.

- MON-14: **Reviewed 2026-11-13** The check-in dependency map is grouped by repo first: one block per repo headed by the repo's name, cross-repo dependencies drawn between blocks <!-- reviewed eeac7ce2 -->
  - Each repo prints as `== name ==` within 60 characters, then a `Between repos` list for `repo/slug` dependencies, then the legend once.
  - The reply hook flags a check-in whose Dependencies section leaves out a goal on the board.

- MON-15: **Reviewed 2026-11-12** Pods coordinate through shared state, not messages: every goal records its owning pod and only that pod starts, answers, merges or resumes it; other pods show it read-only as owned by that pod; merges into one repo's main are serialized across pods by a short lock <!-- reviewed 9f4be548 -->
  - The pod id is `LOOP_POD_ID`, else the operation session's own id; a goal with no recorded pod belongs to no one. Another pod's attempt prints one `REFUSED: goal <slug> is owned by pod <id>. Fix: ...` line, exit 2, and changes nothing.
  - `merge.py` takes `<git common dir>/loop/merge.lock` for the whole merge step; a dead holder or one older than 30 minutes is replaced.
  - A pod's watch, auto-answers and mending skip other pods' goals, and its check-in lists their questions as read-only.

### Non-functional
- MON-7: **Reviewed 2026-11-10** Govern only <!-- reviewed da6f1852 -->
  - A check-in never edits code, commits or pushes from the operation session; only merges and the post-merge steps change the repo.
- MON-8: **Reviewed 2026-11-10** No silent worker <!-- reviewed 68d94ecf -->
  - A worker with no report for 30 minutes shows under Needs you.
- MON-9: **Reviewed 2026-11-10** Fast board <!-- reviewed 29aa63ec -->
  - The board builds in under 10 seconds.

## Non-goals
- The operation session never builds; workers do.
- It never merges unless auto_merge is on (MON-7, MON-15); the delivery loop merges and releases.
- Full auto never answers for me on destructive, money, security or owner-contradicting decisions.

## Success metrics
- Every ready goal gets its own worker session within one check-in, and no goal waits on a goal it doesn't depend on.
- The check-in prints in the same format every time, at least every 30 minutes by default.
- With full auto on, a run needs me only for decisions MON-11 excludes.

## Tests

| Test | Kind | Guards | Checks | Last result |
|---|---|---|---|---|
| [dependency-held](Tests#t-dependency-held) | requirement | MON-1 | Given a goal that depends on an unmerged goal, when the queue runs, then it is held until that goal merges. | PASS 2026-11-09 |
| [no-line-in-governor](Tests#t-no-line-in-governor) | requirement | MON-1 | Given the governing session, when goals run, then no goal runs inside it. | PASS 2026-11-12 |
| [skill-says-governs](Tests#t-skill-says-governs) | requirement | MON-1 | Given the delivery skill, when it is read, then it says the operation session only governs. | PASS 2026-11-12 |
| [dependencies-on-map](Tests#t-dependencies-on-map) | requirement | MON-1 | Given a goal that waits on others, when it starts, then it records what it waits on. | PASS 2026-11-09 |
| [failed-waits-mender](Tests#t-failed-waits-mender) | requirement | MON-1 | Given a failed goal, when mending is due, then it waits before a mender starts. | PASS 2026-11-09 |
| [worker-refuses](Tests#t-worker-refuses) | requirement | MON-1 | Given the governing session, when building is attempted inside it, then it is refused with one line. | PASS 2026-11-12 |
| [worker-per-goal](Tests#t-worker-per-goal) | requirement | MON-1 | Given several goals, when they run, then each runs in its own process and worktree. | PASS 2026-11-12 |
| [one-way-to-run](Tests#t-one-way-to-run) | requirement | MON-1 | Given the tools, when a goal is started, then no old way to start it remains. | PASS 2026-11-12 |
| [operate-all](Tests#t-operate-all) | requirement | MON-1 | Given the operate command's toy suite, when it runs, then the whole suite passes. | PASS 2026-11-09 |
| [session-assign](Tests#t-session-assign) | requirement | MON-1 | Given a ready goal, when it is assigned, then it gets its own worker session in the app. | PASS 2026-11-12 |
| [session-rename](Tests#t-session-rename) | requirement | MON-1 | Given a worker session, when it takes a goal, then it is renamed after that goal. | PASS 2026-11-12 |
| [session-reuse](Tests#t-session-reuse) | requirement | MON-1 | Given a finished worker session, when a goal is ready, then the session is given the next ready goal. | PASS 2026-11-12 |
| [steps-in-session](Tests#t-steps-in-session) | requirement | MON-1 | Given a worker session, when it runs steps, then it runs each step itself with no headless agent. | PASS 2026-11-12 |
| [record-in-session](Tests#t-record-in-session) | requirement | MON-1 | Given a step a worker session ran, when it is recorded, then it is recorded as in session and a goal with no session is refused. | PASS 2026-11-12 |
| [session-holds-slot](Tests#t-session-holds-slot) | requirement | MON-1 | Given a goal in a worker session, when the parallel limit is counted, then it counts against the limit. | PASS 2026-11-12 |
| [worker-reports](Tests#t-worker-reports) | requirement | MON-2 | Given a merged goal, when the board is shown, then it shows its pull request. | PASS 2026-11-12 |
| [worker-reports-live](Tests#t-worker-reports-live) | requirement | MON-2 | Given a report to a running worker, when goal.py next runs, then the report reaches its agent once. | PASS 2026-11-09 |
| [session-reports](Tests#t-session-reports) | requirement | MON-2 | Given a worker session's step report, when it arrives, then it is recorded on its goal. | PASS 2026-11-12 |
| [session-fallback](Tests#t-session-fallback) | requirement | MON-2 | Given no session can be started, when a goal runs, then it falls back to a background process and the board says so. | PASS 2026-11-12 |
| [session-answer](Tests#t-session-answer) | requirement | MON-2 | Given the owner's answer, when it is sent, then it reaches the worker session by session message. | PASS 2026-11-12 |
| [session-quiet](Tests#t-session-quiet) | requirement | MON-2 | Given a worker session silent past silent_minutes (30 by default), when the board is printed, then it shows under Issues. | PASS 2026-11-10 |
| [session-ended-waiting](Tests#t-session-ended-waiting) | requirement | MON-2 | Given a goal that ends with its pull request open, when it finishes, then it stays done and frees its session. | PASS 2026-11-10 |
| [session-tool-timeout](Tests#t-session-tool-timeout) | requirement | MON-2 | Given a hung session tool, when its timeout passes, then it is cut off and the goal falls back to a background process at once. | PASS 2026-11-10 |
| [session-tool-helper](Tests#t-session-tool-helper) | requirement | MON-2 | Given a helper process the session tool leaves running, when the call returns, then the helper never holds it up. | PASS 2026-11-10 |
| [guards-null-report-bind-mend](Tests#t-guards-null-report-bind-mend) | requirement | MON-2 | Given a failed or stopped goal restarted by a worker bind or by mend, when its record is written, then report is an empty record, never null. | not run |
| [waits-first](Tests#t-waits-first) | requirement | MON-3 | Given a live board, when the board page is opened, then it shows the live board. | PASS 2026-11-09 |
| [board-sections](Tests#t-board-sections) | requirement | MON-3 | Given a live board, when the board page is built, then it carries the live board's sections. | PASS 2026-11-09 |
| [retired-leaves-waiting](Tests#t-retired-leaves-waiting) | requirement | MON-4 | Given a retired goal, when the board is shown, then it no longer shows under Issues. | PASS 2026-11-09 |
| [stuck-stays-top](Tests#t-stuck-stays-top) | requirement | MON-4 | Given a stuck goal, when the board is shown, then it stays on top until answered. | PASS 2026-11-12 |
| [status-order](Tests#t-status-order) | requirement | MON-4 | Given the live board, when it is printed, then it lists Issues, Running goals, Queued goals, Dependencies and Finish in that order. | PASS 2026-11-12 |
| [needs-you-stuck](Tests#t-needs-you-stuck) | requirement | MON-4 | Given failed and waiting goals, when the board is printed, then Issues holds them with the exact words to type. | PASS 2026-11-12 |
| [estimates-shown](Tests#t-estimates-shown) | requirement | MON-4 | Given a running goal, when the board is printed, then it shows its time left from past runs and its step flow. | PASS 2026-11-12 |
| [status-roadmap-features](Tests#t-status-roadmap-features) | requirement | MON-4 | Given merged goals, when the live board is printed, then they do not appear. | PASS 2026-11-09 |
| [status-graph-order](Tests#t-status-graph-order) | requirement | MON-4 | Given the live board, when it is printed, then its sections come in a fixed order. | PASS 2026-11-12 |
| [status-graph-levels](Tests#t-status-graph-levels) | requirement | MON-4 | Given chained goals, when the board is printed, then they are drawn as a top-to-bottom graph between running and queued goals. | PASS 2026-11-12 |
| [status-graph-marks](Tests#t-status-graph-marks) | requirement | MON-4 | Given running and merged goals, when the board is printed, then a running goal shows a 10-cell bar and time left and merged goals are left out. | PASS 2026-11-12 |
| [status-graph-total](Tests#t-status-graph-total) | requirement | MON-4 | Given chained estimates, when the finish time is computed, then it is the longest chain of estimates, not their sum. | PASS 2026-11-12 |
| [status-graph-board](Tests#t-status-graph-board) | requirement | MON-4 | Given the live board, when the board artifact page is shown, then it shows the same live board. | PASS 2026-11-12 |
| [step-label-live](Tests#t-step-label-live) | requirement | MON-4 | Given a step, when it starts, then its label changes and a finished step is never shown as current. | PASS 2026-11-12 |
| [live-board-header](Tests#t-live-board-header) | requirement | MON-4 | Given the board, when it is printed, then it starts with a LIVE BOARD header of repo, local time, version and health. | PASS 2026-11-12 |
| [live-board-flow](Tests#t-live-board-flow) | requirement | MON-4 | Given a running goal, when the board is printed, then its step flow ticks done steps and brackets the current one. | PASS 2026-11-12 |
| [live-board-arrows](Tests#t-live-board-arrows) | requirement | MON-4 | Given dependencies between running and queued goals, when the board is printed, then they are drawn as a top-to-bottom graph. | PASS 2026-11-12 |
| [live-board-issues](Tests#t-live-board-issues) | requirement | MON-4 | Given a stuck worker, when the board is printed, then Issues puts it first with its fix in plain words. | PASS 2026-11-12 |
| [live-board-leftouts](Tests#t-live-board-leftouts) | requirement | MON-4 | Given merged work, history, totals, milestones, tokens and done lines, when the board is printed, then they are left off. | PASS 2026-11-12 |
| [depth-on-board](Tests#t-depth-on-board) | requirement | MON-4 | Given a running goal with recorded steps, when the live board prints, then it shows each step's depth and the setting. | PASS 2026-11-10 |
| [held-all](Tests#t-held-all) | requirement | MON-4 | Given the board-held toy repo, when every check runs (held, freezing, pool lock, free, bind, done is final, fail-closed watch and mend, assign races), then all pass. | PASS 2026-11-10 |
| [est-area](Tests#t-est-area) | requirement | MON-4 | Given touched paths, when a goal's size is counted, then each folds to one area: a skill folder, else its first folder, else the root file. | not run |
| [est-size](Tests#t-est-size) | requirement | MON-4 | Given a goal file and a queue line, when a goal's size is read, then the goal file's numbered done lines and touches win, and fenced or verify steps never count. | not run |
| [est-similar](Tests#t-est-similar) | requirement | MON-4 | Given five finished goals of a similar size, when a goal is estimated, then their times set it and it is not rough; with four it falls back to every finished goal and reads rough. | not run |
| [est-monotone](Tests#t-est-monotone) | requirement | MON-4 | Given goals of growing size, when they are estimated, then a goal with more done lines or touched areas always gets a longer estimate. | not run |
| [est-lift-bound](Tests#t-est-lift-bound) | requirement | MON-4 | Given a small size whose past goals were slow, when a larger goal is estimated, then it is never shorter, and the lift stays within one minute per extra unit. | not run |
| [est-range-text](Tests#t-est-range-text) | requirement | MON-4 | Given an estimate, when the board shows it, then it reads low to high left, adds rough when rough, and fits the board width. | not run |
| [est-pace](Tests#t-est-pace) | requirement | MON-4 | Given a running goal faster or slower than its estimate, when it is re-estimated, then the steps left scale by its pace, held between half and double. | not run |
| [est-overrun-range](Tests#t-est-overrun-range) | requirement | MON-4 | Given a running step before, at and past its estimate, when the goal is estimated, then its low, estimate and high stay in order. | not run |
| [est-offflow](Tests#t-est-offflow) | requirement | MON-4 | Given a goal at an off-flow step after build, when it is estimated, then it counts from build onward, never from idea. | not run |
| [est-flow-seconds](Tests#t-est-flow-seconds) | requirement | MON-4 | Given a run log with reports, checks and a pause, when step times are counted, then reports and checks count toward the step in force and the pause counts nothing. | not run |
| [est-partial](Tests#t-est-partial) | requirement | MON-4 | Given a goal whose later steps have no history, when the board is shown, then it reads rough and the finish time says at least. | not run |
| [est-unsafe-slug](Tests#t-est-unsafe-slug) | requirement | MON-4 | Given a bad slug or an unreadable goal file, when a goal is estimated, then it is unknown size and rough, and the board still renders. | not run |
| [est-big-goal](Tests#t-est-big-goal) | requirement | MON-4 | Given a goal larger than every finished one, when the board is shown, then it renders quickly and reads rough. | not run |
| [est-cache](Tests#t-est-cache) | requirement | MON-4 | Given a finished run that changes, when the board is shown again in the same process, then the estimate changes. | not run |
| [mon4-checkin-no-board](Tests#t-mon4-checkin-no-board) | requirement | MON-4 | Given running goals, when the operation session checks in, then it prints the check-in layout and not the live board, while report still prints the board. | PASS 2026-11-10 |
| [est-worktree](Tests#t-est-worktree) | requirement | MON-4 | Given a running goal whose goal file sits only in its worktree, when its size is read, then the worktree's goal file sizes it, and a worktree outside the loop worktrees folder is never read. | not run |
| [est-similar-step](Tests#t-est-similar-step) | requirement | MON-4 | Given five similar finished goals that never logged a step, when that step is estimated, then it comes from every finished goal, while steps they logged come from them. | not run |
| [est-stall-held](Tests#t-est-stall-held) | requirement | MON-4 | Given a goal far past three times its step estimate, when it has no worker and is held, then it is never shown as stalled under Issues. | not run |
| [est-backtest-best](Tests#t-est-backtest-best) | requirement | MON-4 | Given two fixture sets of 12 finished goals, one where time grows with size and one where it does not, when the board picks its estimate model, then it is the backtest's lowest score in both: the size rule in the first, step medians in the second. | not run |
| [est-backtest-loo](Tests#t-est-backtest-loo) | requirement | MON-4 | Given three finished goals, when the backtest leaves each out, then every candidate's prediction and the score equal the values worked out by hand without that goal. | not run |
| [est-accuracy-line](Tests#t-est-accuracy-line) | requirement | MON-4 | Given 12 finished goals, when the board is shown, then the line under the finish time names the model in use and its typical whole-goal error; under 10 goals it says the error is not known yet. | not run |
| [est-backtest-fails](Tests#t-est-backtest-fails) | requirement | MON-4 | Given a backtest that raises an error, when the board is shown, then it still renders with the size rule, says the backtest failed, and prints the traceback to stderr. | not run |
| [est-stall-floor](Tests#t-est-stall-floor) | requirement | MON-4 | Given a step with a 2-minute estimate, when it has run 10 minutes, then it is not stalled, and at 16 minutes it is. | not run |
| [est-held-idle](Tests#t-est-held-idle) | requirement | MON-4 | Given a held goal, or a log with a hold or free entry, when step time is counted, then held time adds nothing until the goal resumes, and its time left is the same an hour later. | not run |
| [est-module-size](Tests#t-est-module-size) | requirement | MON-4 | Given the board's estimate code split into modules, when they are loaded, then each is under 18,432 bytes and every name readers use still resolves from board_status. | not run |
| [est-backtest-speed](Tests#t-est-backtest-speed) | requirement | MON-4 | Given 100 finished goals, when the backtest runs, then it takes under 3 CPU seconds (measured 0.08), and the board over 300 finished goals renders in under 5 CPU seconds. | not run |
| [est-steps-monotone](Tests#t-est-steps-monotone) | requirement | MON-4 | Given the step medians and blend models, when a larger goal is estimated, then it gets a strictly longer estimate, even past a size with no time. | not run |
| [est-recompute](Tests#t-est-recompute) | requirement | MON-4 | Given the same finished runs, when the board is shown twice, then the backtest is reused; when one more run finishes, then it is worked out again (a running goal's change also recomputes it). | not run |
| [est-pool-unread-stall](Tests#t-est-pool-unread-stall) | requirement | MON-4 | Given the session pool can't be read and a goal's log ends in a hold entry, when the board is shown, then the goal is not listed as stalled. | not run |
| [est-time-order-mon4](Tests#t-est-time-order-mon4) | requirement | MON-4 | Given goals that finished before, exactly when, during and after a goal started, and one with inverted stamps, when the board backtests, then each goal is predicted only from goals that finished strictly before it started and never from itself. | not run |
| [no-change-quiet](Tests#t-no-change-quiet) | requirement | MON-5 | Given a board field the old board lacked or gh not answering, when boards are compared, then it counts as no change. | PASS 2026-11-09 |
| [operate-wakes-on-report](Tests#t-operate-wakes-on-report) | requirement | MON-5 | Given a worker's report, when it arrives before the cadence, then operate wakes and every pass prints the full board. | PASS 2026-11-09 |
| [live-board-no-oneline](Tests#t-live-board-no-oneline) | requirement | MON-5 | Given an unchanged pass, when the operation session checks in, then the full check-in is printed again and there is no one-line mode. | PASS 2026-11-12 |
| [live-board-cadence](Tests#t-live-board-cadence) | requirement | MON-5 | Given no cadence setting, when check-ins are scheduled, then the cadence is 30 minutes. | PASS 2026-11-12 |
| [reply-hook-blocks](Tests#t-reply-hook-blocks) | requirement | MON-5 | Given an operation-session check-in reply, when it stops without the headline, All sessions, Dependencies, Needs you and Coming up last, then the hook blocks it and says what is missing, and a reply in that layout passes. | PASS 2026-11-10 |
| [reply-hook-scope](Tests#t-reply-hook-scope) | requirement | MON-5 | Given a worker session or a session in another repo, when it stops with any reply, then the hook never checks it, and only the operation session is checked. | PASS 2026-11-10 |
| [reply-hook-off](Tests#t-reply-hook-off) | requirement | MON-5 | Given reply_hook set to false in the config, when the operation session stops without the board, then the hook lets it through. | PASS 2026-11-10 |
| [reply-hook-guard](Tests#t-reply-hook-guard) | requirement | MON-5 | Given a reply blocked twice in a row or a broken hook input, when the session stops again, then the hook lets it through and logs it instead of looping. | PASS 2026-11-10 |
| [reply-hook-install](Tests#t-reply-hook-install) | requirement | MON-5 | Given a repo, when setup --reply-hook runs, then the Stop hook is merged into its machine-local Claude settings, which git ignores, and a second run changes nothing. | PASS 2026-11-10 |
| [reply-hook-all](Tests#t-reply-hook-all) | requirement | MON-5 | Given the reply hook's toy suite, when it runs, then every check passes. | PASS 2026-11-10 |
| [reply-hook-mon5-wording](Tests#t-reply-hook-mon5-wording) | requirement | MON-5 | Given the Monitoring PRD, when MON-5 is read, then it carries the check-in reply layout the hook enforces. | PASS 2026-11-13 |
| [checkin-passes-hook](Tests#t-checkin-passes-hook) | requirement | MON-5 | Given the check-in operate.py prints, when the reply hook checks it, then it passes the layout. | PASS 2026-11-10 |
| [mon6-merged-frees](Tests#t-mon6-merged-frees) | requirement | MON-6 | Given a goal whose pull request merged, when its worker reports merged, then its session goes back to the pool (archived above pool_size) and its worktree and branch are removed. | PASS 2026-11-10 |
| [mon10-replan](Tests#t-mon10-replan) | requirement | MON-10 | Given ready, mergeable and splittable goals, when the operation session re-plans, then each start, merge and split is logged once with its reason, shown in the check-in, and no running goal is stopped. | PASS 2026-11-10 |
| [mon11-full-auto](Tests#t-mon11-full-auto) | requirement | MON-11 | Given full auto on, when a worker asks a routine question, then the recommended answer is sent and logged; destructive, unlabeled, risky-word and owner-answered questions wait; turning it off applies at the next decision. | PASS 2026-11-10 |
| [mon12-pool](Tests#t-mon12-pool) | requirement | MON-12 | Given a session pool, when it runs low, then the check-in asks to create every missing session in one step; pool.py add fills it, no pool hides the ask, and a full pool makes ready goals wait with the fix. | PASS 2026-11-10 |
| [mon13-two-layers](Tests#t-mon13-two-layers) | requirement | MON-13 | Given a second session's claim, when it claims, then the first stays an operation session and nothing refuses or warns. | PASS 2026-11-12 |
| [operation-checkout-ff](Tests#t-operation-checkout-ff) | requirement | MON-13 | Given a main checkout that is behind origin, when the operation loop runs a pass, then the checkout moves by fast-forward only, uncommitted work stays, and one line says it moved or could not. | not run |
| [mon14-repo-blocks](Tests#t-mon14-repo-blocks) | requirement | MON-14 | Given a cross-repo dependency, when the check-in prints, then it is listed between headed repo blocks. | PASS 2026-11-12 |
| [mon14-reply-repo-blocks](Tests#t-mon14-reply-repo-blocks) | requirement | MON-14 | Given a check-in reply whose Dependencies section has no == repo == block, when the reply hook checks it, then it flags the missing repo block. | not run |
| [mon14-reply-deps-whole](Tests#t-mon14-reply-deps-whole) | requirement | MON-14 | Given a check-in reply whose Dependencies section leaves out a running goal of the board, when the reply hook checks it, then it names that goal, and a reply that draws every goal passes. | not run |
| [mon15-pod-owner](Tests#t-mon15-pod-owner) | requirement | MON-15 | Given another pod's goal, when a pod acts on it, then it is refused naming the owner and shown owned by that pod. | PASS 2026-11-12 |
| [mon15-merge-lock](Tests#t-mon15-merge-lock) | requirement | MON-15 | Given two pods merging into one main, when they run together, then the lock serializes them. | PASS 2026-11-12 |
| [resume-ask-prompt](Tests#t-resume-ask-prompt) | requirement | MON-15 | Given a goal set to ask and auto_merge on, when it is resumed, then its prompt asks the owner and never tells the worker to run merge.py. | not run |
| [mon7-govern-blocks](Tests#t-mon7-govern-blocks) | requirement | MON-7 | Given the operation session, when it tries an edit, a commit or a push, then the govern hook refuses it with the fix, while workers, other sessions and the off switch pass. | PASS 2026-11-10 |
| [mon16-notes-pass](Tests#t-mon16-notes-pass) | requirement | MON-7 | Given the operation session, when it writes a file outside every followed repo, then the govern hook lets it through. | not run |
| [mon16-edit-inside-refused](Tests#t-mon16-edit-inside-refused) | requirement | MON-7 | Given the operation session, when it edits a file inside a followed repo, then the govern hook refuses it. | not run |
| [mon8-silent-30](Tests#t-mon8-silent-30) | requirement | MON-8 | Given a worker with no report for 31 minutes, when the operation session checks in, then it shows under Needs you; at 29 minutes it does not. | PASS 2026-11-10 |
| [mon8-silent-worker](Tests#t-mon8-silent-worker) | requirement | MON-8 | Given a running worker whose last report is 31 minutes old, when the check-in is built, then Needs you names it and a worker that reported 5 minutes ago is not named. | not run |
| [mon9-board-fast](Tests#t-mon9-board-fast) | requirement | MON-9 | Given 12 goals with pull requests and a slow GitHub, when the board is built, then it takes under 10 seconds. | PASS 2026-11-10 |
| [session-board-issue98](Tests#t-session-board-issue98) | defect | [#98](https://github.com/jcl2018/agent-workflow-template/issues/98) closed (2026-11-09) | Given a goal worked in a session, when the board is printed, then it shows its session name and step and never shows it as a failed background worker. | PASS 2026-11-12 |
| [report-done-final](Tests#t-report-done-final) | defect | [#108](https://github.com/jcl2018/agent-workflow-template/issues/108) closed (2026-11-10) | Given a goal whose pull request is open (done), when a session report says running or failed, then the goal stays done. | PASS 2026-11-10 |
| [guards-resume](Tests#t-guards-resume) | defect | [#149](https://github.com/jcl2018/agent-workflow-template/issues/149) closed (2026-11-11) | Given a stopped goal worked in a session, when the operation runs goal.py resume, then it runs again in that session with who and why logged, and no headless worker starts. | PASS 2026-11-12 |
| [guards-worker-role](Tests#t-guards-worker-role) | defect | [#121](https://github.com/jcl2018/agent-workflow-template/issues/121) closed (2026-11-11) | Given a goal step run without LOOP_ROLE=worker, when it is refused, then the refusal gives the exact LOOP_ROLE=worker command for the goal's bound session, and bind prints it. | PASS 2026-11-10 |
| [guards-worktree](Tests#t-guards-worktree) | defect | [#160](https://github.com/jcl2018/agent-workflow-template/issues/160) closed (2026-11-13) | Given a session bound to a goal, when it is bound or assigned, then it is told the goal worktree to work in, and a session folder outside it is refused. | PASS 2026-11-10 |
| [worker-save-159](Tests#t-worker-save-159) | defect | [#159](https://github.com/jcl2018/agent-workflow-template/issues/159) closed (2026-11-11) | Given a worker loop whose run record is merged from outside while it runs, when the loop saves, then the outside merge is kept. | not run |
| [issue-117-bind-self](Tests#t-issue-117-bind-self) | defect | [#117](https://github.com/jcl2018/agent-workflow-template/issues/117) closed (2026-11-11) | Given a worker session that doesn't know its own id, when it runs sessions.py bind SLUG self, then it is bound by its own session id (issue: Goals can't name GitHub-side changes ... a worker session cannot find its own session id). | not run |
| [stop-tree-session-tool](Tests#t-stop-tree-session-tool) | defect | [#1396](https://github.com/jcl2018/agent-workflow-template/issues/1396) closed (2026-11-12) | Given a hung session tool or a late mender, when it is stopped on any platform, then its whole process tree goes with it. | not run |
| [held-stale-next](Tests#t-held-stale-next) | defect | [#102](https://github.com/jcl2018/agent-workflow-template/issues/102) closed (2026-11-10) | Given a session goal with an old failure report and a newer session report, when the live board prints, then its next line is the newer report. | PASS 2026-11-10 |
| [held-shows-held](Tests#t-held-shows-held) | defect | [#102](https://github.com/jcl2018/agent-workflow-template/issues/102) closed (2026-11-10) | Given a running goal with no worker (session reassigned, worktree kept), when the live board prints, then it is listed as held, not running and not as a background worker. | PASS 2026-11-10 |
| [held-freezing](Tests#t-held-freezing) | defect | [#102](https://github.com/jcl2018/agent-workflow-template/issues/102) closed (2026-11-10) | Given a goal handed to a worker session before it is frozen, when the live board prints, then it shows at once under that session with step freezing. | PASS 2026-11-10 |
| [held-off-flow](Tests#t-held-off-flow) | defect | [#102](https://github.com/jcl2018/agent-workflow-template/issues/102) closed (2026-11-10) | Given a goal whose step is outside the flow, such as checks, when the live board prints, then it keeps its last known flow step, not idea 0%. | PASS 2026-11-10 |
| [est-stalled](Tests#t-est-stalled) | defect | [#37](https://github.com/jcl2018/agent-workflow-template/issues/37) closed (2026-11-11) | Given a running step past three times its estimate, when the board is shown, then the goal shows under Issues as stalled, naming the step and how long it has run. | not run |
| [est-issue-96](Tests#t-est-issue-96) | defect | [#96](https://github.com/jcl2018/agent-workflow-template/issues/96) closed (2026-11-11) | Given two queued goals of different sizes, when the board is shown, then they get different estimates, each inside the range of their similar past goals. | not run |
| [est-offflow-done](Tests#t-est-offflow-done) | defect | [#37](https://github.com/jcl2018/agent-workflow-template/issues/37) closed (2026-11-11) | Given a goal at an off-flow step after a step's done entry, when the board is shown, then it sits at the next step, that step's time counts, and it stalls past three times its estimate. | not run |
| [deps-graph-94](Tests#t-deps-graph-94) | defect | [#94](https://github.com/jcl2018/agent-workflow-template/issues/94) closed (2026-11-11) | Given chained goals, when the board is printed, then Dependencies is a top-to-bottom graph at most 60 columns wide with markers and a legend. | PASS 2026-11-10 |
| [issues-phone-97](Tests#t-issues-phone-97) | defect | [#97](https://github.com/jcl2018/agent-workflow-template/issues/97) closed (2026-11-11) | Given four goals stopped by one usage limit, when the board is printed, then Issues shows one short line with no raw agent output and the finish says paused. | PASS 2026-11-10 |
| [report-held-111](Tests#t-report-held-111) | defect | [#111](https://github.com/jcl2018/agent-workflow-template/issues/111) closed (2026-11-11) | Given a held goal and a freezing goal, when report and the board digest are printed, then both list them. | PASS 2026-11-10 |
| [state-shared-113](Tests#t-state-shared-113) | defect | [#113](https://github.com/jcl2018/agent-workflow-template/issues/113) closed (2026-11-11) | Given running, held and waiting goals, when graph and the live board judge them, then they agree and a held goal holds no slot. | PASS 2026-11-10 |
| [held-time-115](Tests#t-held-time-115) | defect | [#115](https://github.com/jcl2018/agent-workflow-template/issues/115) closed (2026-11-11) | Given a goal held for three hours, when the board is printed, then it shows the held time, not the time since its last change. | PASS 2026-11-10 |
| [reply-hook-checkin-123](Tests#t-reply-hook-checkin-123) | defect | [#123](https://github.com/jcl2018/agent-workflow-template/issues/123) closed (2026-11-10) | Given a check-in reply that lacks the one headline, the All sessions table, the Dependencies graph, numbered Needs you or Coming up last, when it is checked, then each missing piece is named, and a reply in the issue 123 layout passes. | PASS 2026-11-10 |
| [reply-checkin-321](Tests#t-reply-checkin-321) | defect | [#321](https://github.com/jcl2018/agent-workflow-template/issues/321) closed (2026-11-11) | Given a scheduled check-in prompt in the operation session and a one-line reply, when the reply hook runs, then it blocks the reply and names the missing parts. | PASS 2026-11-10 |
| [merged-frees-175](Tests#t-merged-frees-175) | defect | [#175](https://github.com/jcl2018/agent-workflow-template/issues/175) closed (2026-11-11) | Given a done goal, when its worker reports merged, then its session is freed. | PASS 2026-11-10 |
| [slot-pool-112](Tests#t-slot-pool-112) | defect | [#112](https://github.com/jcl2018/agent-workflow-template/issues/112) closed (2026-11-11) | Given a held session goal whose session was freed, when slots are counted, then it holds none and a queued goal can start. | PASS 2026-11-10 |
| [attempt-114](Tests#t-attempt-114) | defect | [#114](https://github.com/jcl2018/agent-workflow-template/issues/114) closed (2026-11-11) | Given a goal re-bound to a new session, when the old worker reports, then the report is recorded but not applied, and the freed session keeps its history. | PASS 2026-11-10 |
| [pool-edges-122](Tests#t-pool-edges-122) | defect | [#122](https://github.com/jcl2018/agent-workflow-template/issues/122) closed (2026-11-11) | Given a malformed pool entry and a retired goal with a busy session, when the pool is read, then the entry is set aside without blocking and the session is named and freed. | PASS 2026-11-10 |
| [pull-ff-only-passes](Tests#t-pull-ff-only-passes) | defect | [#495](https://github.com/jcl2018/agent-workflow-template/issues/495) closed (2026-11-11) | Given the operation session, when it runs git pull --ff-only (also with -C and a remote), then the govern hook lets it through. | PASS 2026-11-12 |
| [pull-plain-blocked](Tests#t-pull-plain-blocked) | defect | [#495](https://github.com/jcl2018/agent-workflow-template/issues/495) closed (2026-11-11) | Given the operation session, when it runs a plain git pull, -r, --rebase=merges, --no-ff, --ff-only with --rebase or --ff, a +refspec or -f, then the govern hook still refuses it (negative control). | PASS 2026-11-12 |
