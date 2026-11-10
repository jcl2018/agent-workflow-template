<!-- workflow-docs -->
# Monitoring

Milestone: https://github.com/jcl2018/agent-workflow-template/milestone/6

Review: **Unreviewed**

## Problem

Skill: `workflow-monitoring`. The operation session never does work: `/workflow-monitoring operate` (the `operate.py run` routine) is its one command; it plans queued goals as a dependency graph (`depends:` or `depends-on:`, the same key, capped by `parallel`, where 0 is unlimited and the default), gives each ready goal its own worker session in the app, renamed `worker · <goal>` (`sessions.py`: a free session is reused, or the session tool in `session_command` starts one), watches and reports; each worker session runs every flow step inside itself and reports each change of step and its result by session message, which `sessions.py report` records (merged is checked with gh, and a goal that ended frees its session), and the session can send it an answer with `operate.py send`, which reaches the worker session itself; a session goal holds a `parallel` slot, and one silent for an hour is named under Issues. A goal falls back to a background process only when no session can be started or reached (a free session that can't be reached is skipped for a new one first; a session tool call past `LOOP_SESSION_TIMEOUT`, 30 seconds by default, is killed with its children and the tool is given up for that round), and the live board shows each running goal's worker: its session name, or `background` and why. `sessions.py bind` records a session started with the app's own tools, so a goal moved into a session never shows as a failed background worker (issue 98). Run the commands from the main checkout, on the base branch. Issues lists only what is still open, with at most one wiki line built each pass from the current `docs.py check` (today's stale or failing pages and the fix); a saved wiki error for a page the check no longer reports is dropped without waiting for a publish, and an error recorded before a goal merged (on GitHub too: the status asks `gh pr view`) is dropped. The Roadmap draws only live goals (running, queued, waiting) with arrows, stage, a 10-cell bar and time left, a flow chart of the `depends-on` links, and always ends with the longest-path total and its finish time; every time `operate.py` prints is in the local zone with its name; merged goals collapse to one `merged: #N` line. A pass where nothing changed prints one line. A worker ends by running the release step itself where `auto_merge` is on, so a goal is never left with its pull request waiting. `worker.py cleanup` deletes merged `loop/*` branches that no worktree has checked out (`git branch -d`, local only; `--dry-run` lists them). Codex has run as a monitored background agent on a toy repo; it needs `-s workspace-write`, with the git folder and the remote as writable roots. Each running or held goal on the live board also has a `depth:` line: every recorded step's depth (full or condensed) and the current `review_depth` setting.

Commands, flows and how-tos: `skills/workflow-monitoring/references/commands.md`. The live board also reads the session pool (issue 102): a goal handed to a session before it is frozen shows at once as `[freezing]`, a running goal no worker has (session reassigned, worktree kept) is listed under Queued goals marked `held`, the next line is the latest session report, a step outside the flow keeps its last flow step, a failed try shows `try N of M`, and a session report never moves a done goal back (issue 108); the session pool is changed under a lock, so an operator's bind wins over a handoff still in flight, and the session tool runs with no terminal, so a git or gh prompt fails instead of blocking; `sessions.py assign` refuses a goal that already has a worker, gives a failed goal to its new session, and leaves a goal bound during its send to that bind (HANDED), freeing the session it claimed; its Board states table gives each state's next command and messages.

A failed release is recorded as `release_error` and lists under Issues beside `wiki_error`, which leaves Issues once a later publish succeeds or the goal is merged. A pull request closed or merged on GitHub leaves the live board. Each check-in reply follows one layout (a headline, All sessions, Dependencies, Needs you and, last, Coming up), and `reply_hook.py`, a Stop hook that setup installs per repo, blocks an operation-session reply in any other layout and says what is missing; it reads only the transcript lines added since the last stop, never checks a worker (a session in a goal worktree, or one whose latest signal is a flow step), lets a reply through after three blocks in a row or on any error of its own, and `reply_hook: false` turns it off.

## Usage

- `/workflow-monitoring operate` is the operation session: it plans queued goals, starts a worker for each ready one and prints the live board; `/workflow-monitoring send SLUG "text"` gives a worker an answer.
- `/workflow-monitoring go "goal" --done "line"` queues and starts a goal; `/workflow-monitoring watch` keeps goals moving; `/workflow-monitoring resume SLUG` restarts one.
- `/workflow-monitoring report` and `/workflow-monitoring dashboard` show where every goal stands.
- `/workflow-monitoring met SLUG N` marks a done line met; `/workflow-monitoring cleanup` deletes merged `loop/*` branches ("list them first" previews).
- `/workflow-monitoring reply-check FILE` prints what an operation-session reply is missing; `/workflow-monitoring reply-status` says whether the reply hook (installed by `/workflow-setup reply-hook`) is installed and on in this repo.

## Requirements

- MON-1: **Reviewed 2026-11-08** Roles, start and planning. One command starts the operation session and drives the whole process the same way every time. The operation session plans queued goals as a dependency graph and gives every goal whose dependencies are met its own worker session in the app, renamed worker · <goal>, running in parallel; it never builds. A goal waits only on goals it truly depends on; sharing files is not a reason to wait. When a worker session finishes, the operation session gives it the next ready goal, renaming it again. <!-- reviewed b4d6beac -->
- MON-2: **Reviewed 2026-11-08** Live communication. Operation and workers talk through session messages: a worker reports each change of step or status as it happens, and its result when it ends (merged, failed or waiting, with the pull request); the operation session sends a worker its answer or a follow-up. Background processes are used only when the app can't start or reach a session, and the board says so. <!-- reviewed 3c99a1c2 -->
- MON-3: **Reviewed 2026-11-08** Board view: the board shows everything in one fixed template: what needs me, each running goal's progress bar and current step, what's next, roadmap progress, done lines met. <!-- reviewed b45361d0 -->
- MON-4: **Reviewed 2026-11-08** Live board. Each check-in prints the live board, always in the same format: Issues first (only what is open now, each with its fix in plain words); then Running goals, each with a progress bar, time left, its step flow with the current step marked, and its next step; then Queued goals; then the dependencies between running and queued goals as arrows; then one finish time. Merged work, history and totals are left out. A stuck worker stays at the top of Issues until I answer. <!-- reviewed e4985fe1 -->
- MON-5: **Reviewed 2026-11-09** Cadence and reply format. The operation session updates the board on a set cadence, 30 minutes by default and changeable, and at once whenever a worker reports something new, and prints the full board every time. Every check-in reply has the same layout: one headline line; All sessions, one table of every session across my repos with what it is for, its status, progress, time left, tokens left and latest report; Dependencies, a drawn graph marking what is running, holding, queued or stuck; Needs you, each question numbered with its options and a recommended answer, or Nothing needs you; and last, Coming up, the next expected events and what I will need to do. A hook that setup installs blocks a reply that doesn't follow this layout, saying what is missing; it never checks worker sessions or other repos, and one setting turns it off. <!-- reviewed ba57bf9b -->

## Non-goals

- The operation session never builds; workers do.
- It does not merge or release; the delivery loop does.
- The live board leaves out merged work, history and totals.

## Success metrics

- Every ready goal gets its own worker session, and no goal waits on a goal it doesn't depend on.
- The live board prints in the same format at every check-in, at least every 30 minutes by default.
- A stuck worker stays at the top of Issues until the owner answers.

## Tests

#### MON-1

Roles, start and planning. One command starts the operation session and drives the whole process the same way every time. The operation session plans queued goals as a dependency graph and gives every goal whose dependencies are met its own worker session in the app, renamed worker · <goal>, running in parallel; it never builds. A goal waits only on goals it truly depends on; sharing files is not a reason to wait. When a worker session finishes, the operation session gives it the next ready goal, renaming it again.

- Given a goal that depends on an unmerged goal, when the queue runs, then it is held until that goal merges. — [dependency-held](../../.loop/regression.tsv), requirement, guards MON-1, nightly, PASS 2026-11-09, seen failing 2026-11-07
- Given the governing session, when goals run, then no goal runs inside it. — [no-line-in-governor](../../.loop/regression.tsv), requirement, guards MON-1, both, PASS 2026-11-09, seen failing 2026-11-07
- Given the delivery skill, when it is read, then it says the operation session only governs. — [skill-says-governs](../../.loop/regression.tsv), requirement, guards MON-1, both, PASS 2026-11-09, seen failing 2026-11-07
- Given a goal that waits on others, when it starts, then it records what it waits on. — [dependencies-on-map](../../.loop/regression.tsv), requirement, guards MON-1, nightly, PASS 2026-11-09, seen failing 2026-11-07
- Given a failed goal, when mending is due, then it waits before a mender starts. — [failed-waits-mender](../../.loop/regression.tsv), requirement, guards MON-1, nightly, PASS 2026-11-09, seen failing 2026-11-07
- Given the governing session, when building is attempted inside it, then it is refused with one line. — [worker-refuses](../../.loop/regression.tsv), requirement, guards MON-1, both, PASS 2026-11-09, seen failing 2026-11-07
- Given several goals, when they run, then each runs in its own process and worktree. — [worker-per-goal](../../.loop/regression.tsv), requirement, guards MON-1, both, PASS 2026-11-09, seen failing 2026-11-07
- Given the tools, when a goal is started, then no old way to start it remains. — [one-way-to-run](../../.loop/regression.tsv), requirement, guards MON-1, both, PASS 2026-11-10, seen failing 2026-11-07
- Given the operate command's toy suite, when it runs, then the whole suite passes. — [operate-all](../../.loop/regression.tsv), requirement, guards MON-1, nightly, PASS 2026-11-09, seen failing 2026-11-09
- Given a ready goal, when it is assigned, then it gets its own worker session in the app. — [session-assign](../../.loop/regression.tsv), requirement, guards MON-1, both, PASS 2026-11-09, seen failing 2026-11-09
- Given a worker session, when it takes a goal, then it is renamed after that goal. — [session-rename](../../.loop/regression.tsv), requirement, guards MON-1, both, PASS 2026-11-09, seen failing 2026-11-09
- Given a finished worker session, when a goal is ready, then the session is given the next ready goal. — [session-reuse](../../.loop/regression.tsv), requirement, guards MON-1, both, PASS 2026-11-09, seen failing 2026-11-09
- Given a worker session, when it runs steps, then it runs each step itself with no headless agent. — [steps-in-session](../../.loop/regression.tsv), requirement, guards MON-1, both, PASS 2026-11-09, seen failing 2026-11-09
- Given a step a worker session ran, when it is recorded, then it is recorded as in session and a goal with no session is refused. — [record-in-session](../../.loop/regression.tsv), requirement, guards MON-1, both, PASS 2026-11-09, seen failing 2026-11-09
- Given a goal in a worker session, when the parallel limit is counted, then it counts against the limit. — [session-holds-slot](../../.loop/regression.tsv), requirement, guards MON-1, both, PASS 2026-11-09, seen failing 2026-11-09

#### MON-2

Live communication. Operation and workers talk through session messages: a worker reports each change of step or status as it happens, and its result when it ends (merged, failed or waiting, with the pull request); the operation session sends a worker its answer or a follow-up. Background processes are used only when the app can't start or reach a session, and the board says so.

- Given a merged goal, when the board is shown, then it shows its pull request. — [worker-reports](../../.loop/regression.tsv), requirement, guards MON-2, both, PASS 2026-11-09, seen failing 2026-11-07
- Given a report to a running worker, when goal.py next runs, then the report reaches its agent once. — [worker-reports-live](../../.loop/regression.tsv), requirement, guards MON-2, nightly, PASS 2026-11-09, seen failing 2026-11-08
- Given a worker session's step report, when it arrives, then it is recorded on its goal. — [session-reports](../../.loop/regression.tsv), requirement, guards MON-2, both, PASS 2026-11-09, seen failing 2026-11-09
- Given no session can be started, when a goal runs, then it falls back to a background process and the board says so. — [session-fallback](../../.loop/regression.tsv), requirement, guards MON-2, both, PASS 2026-11-09, seen failing 2026-11-09
- Given the owner's answer, when it is sent, then it reaches the worker session by session message. — [session-answer](../../.loop/regression.tsv), requirement, guards MON-2, both, PASS 2026-11-09, seen failing 2026-11-09
- Given a worker session silent for an hour, when the board is printed, then it shows under Issues. — [session-quiet](../../.loop/regression.tsv), requirement, guards MON-2, both, PASS 2026-11-09, seen failing 2026-11-09
- Given a goal that ends with its pull request open, when it finishes, then it stays done and frees its session. — [session-ended-waiting](../../.loop/regression.tsv), requirement, guards MON-2, both, PASS 2026-11-09, seen failing 2026-11-09
- Given a hung session tool, when its timeout passes, then it is cut off and the goal falls back to a background process at once. — [session-tool-timeout](../../.loop/regression.tsv), requirement, guards MON-2, both, PASS 2026-11-09, seen failing 2026-11-09
- Given a helper process the session tool leaves running, when the call returns, then the helper never holds it up. — [session-tool-helper](../../.loop/regression.tsv), requirement, guards MON-2, both, PASS 2026-11-09, seen failing 2026-11-09

#### MON-3

Board view: the board shows everything in one fixed template: what needs me, each running goal's progress bar and current step, what's next, roadmap progress, done lines met.

- Given a live board, when the board page is opened, then it shows the live board. — [waits-first](../../.loop/regression.tsv), requirement, guards MON-3, nightly, PASS 2026-11-09, seen failing 2026-11-07
- Given a live board, when the board page is built, then it carries the live board's sections. — [board-sections](../../.loop/regression.tsv), requirement, guards MON-3, nightly, PASS 2026-11-09, seen failing 2026-11-07

#### MON-4

Live board. Each check-in prints the live board, always in the same format: Issues first (only what is open now, each with its fix in plain words); then Running goals, each with a progress bar, time left, its step flow with the current step marked, and its next step; then Queued goals; then the dependencies between running and queued goals as arrows; then one finish time. Merged work, history and totals are left out. A stuck worker stays at the top of Issues until I answer.

- Given a retired goal, when the board is shown, then it no longer shows under Issues. — [retired-leaves-waiting](../../.loop/regression.tsv), requirement, guards MON-4, nightly, PASS 2026-11-09, seen failing 2026-11-07
- Given a stuck goal, when the board is shown, then it stays on top until answered. — [stuck-stays-top](../../.loop/regression.tsv), requirement, guards MON-4, both, PASS 2026-11-09, seen failing 2026-11-07
- Given the live board, when it is printed, then it lists Issues, Running goals, Queued goals, Dependencies and Finish in that order. — [status-order](../../.loop/regression.tsv), requirement, guards MON-4, both, PASS 2026-11-09, seen failing 2026-11-07
- Given failed and waiting goals, when the board is printed, then Issues holds them with the exact words to type. — [needs-you-stuck](../../.loop/regression.tsv), requirement, guards MON-4, both, PASS 2026-11-09, seen failing 2026-11-07
- Given a running goal, when the board is printed, then it shows its time left from past runs and its step flow. — [estimates-shown](../../.loop/regression.tsv), requirement, guards MON-4, both, PASS 2026-11-09, seen failing 2026-11-07
- Given merged goals, when the live board is printed, then they do not appear. — [status-roadmap-features](../../.loop/regression.tsv), requirement, guards MON-4, nightly, PASS 2026-11-09, seen failing 2026-11-09
- Given the live board, when it is printed, then its sections come in a fixed order. — [status-graph-order](../../.loop/regression.tsv), requirement, guards MON-4, both, PASS 2026-11-09, seen failing 2026-11-09
- Given chained goals, when the board is printed, then they are drawn as arrows between running and queued goals. — [status-graph-levels](../../.loop/regression.tsv), requirement, guards MON-4, both, PASS 2026-11-09, seen failing 2026-11-09
- Given running and merged goals, when the board is printed, then a running goal shows a 10-cell bar and time left and merged goals are left out. — [status-graph-marks](../../.loop/regression.tsv), requirement, guards MON-4, both, PASS 2026-11-09, seen failing 2026-11-09
- Given chained estimates, when the finish time is computed, then it is the longest chain of estimates, not their sum. — [status-graph-total](../../.loop/regression.tsv), requirement, guards MON-4, both, PASS 2026-11-09, seen failing 2026-11-09
- Given the live board, when the board artifact page is shown, then it shows the same live board. — [status-graph-board](../../.loop/regression.tsv), requirement, guards MON-4, both, PASS 2026-11-09, seen failing 2026-11-09
- Given a step, when it starts, then its label changes and a finished step is never shown as current. — [step-label-live](../../.loop/regression.tsv), requirement, guards MON-4, both, PASS 2026-11-09, seen failing 2026-11-09
- Given the board, when it is printed, then it starts with a LIVE BOARD header of repo, local time, version and health. — [live-board-header](../../.loop/regression.tsv), requirement, guards MON-4, both, PASS 2026-11-09, seen failing 2026-11-09
- Given a running goal, when the board is printed, then its step flow ticks done steps and brackets the current one. — [live-board-flow](../../.loop/regression.tsv), requirement, guards MON-4, both, PASS 2026-11-09, seen failing 2026-11-09
- Given dependencies between running and queued goals, when the board is printed, then they are drawn as arrows. — [live-board-arrows](../../.loop/regression.tsv), requirement, guards MON-4, both, PASS 2026-11-09, seen failing 2026-11-09
- Given a stuck worker, when the board is printed, then Issues puts it first with its fix in plain words. — [live-board-issues](../../.loop/regression.tsv), requirement, guards MON-4, both, PASS 2026-11-09, seen failing 2026-11-09
- Given merged work, history, totals, milestones, tokens and done lines, when the board is printed, then they are left off. — [live-board-leftouts](../../.loop/regression.tsv), requirement, guards MON-4, both, PASS 2026-11-09, seen failing 2026-11-09
- Given a running goal with recorded steps, when the live board prints, then it shows each step's depth and the setting. — [depth-on-board](../../.loop/regression.tsv), requirement, guards MON-4, both, not run, seen failing 2026-11-09
- Given the board-held toy repo, when every check runs (held, freezing, pool lock, free, bind, done is final, fail-closed watch and mend, assign races), then all pass. — [held-all](../../.loop/regression.tsv), requirement, guards MON-4, both, not run, seen failing 2026-11-10

#### MON-5

Cadence and reply format. The operation session updates the board on a set cadence, 30 minutes by default and changeable, and at once whenever a worker reports something new, and prints the full board every time. Every check-in reply has the same layout: one headline line; All sessions, one table of every session across my repos with what it is for, its status, progress, time left, tokens left and latest report; Dependencies, a drawn graph marking what is running, holding, queued or stuck; Needs you, each question numbered with its options and a recommended answer, or Nothing needs you; and last, Coming up, the next expected events and what I will need to do. A hook that setup installs blocks a reply that doesn't follow this layout, saying what is missing; it never checks worker sessions or other repos, and one setting turns it off.

- Given a board field the old board lacked or gh not answering, when boards are compared, then it counts as no change. — [no-change-quiet](../../.loop/regression.tsv), requirement, guards MON-5, nightly, PASS 2026-11-09, seen failing 2026-11-07
- Given a worker's report, when it arrives before the cadence, then operate wakes and every pass prints the full board. — [operate-wakes-on-report](../../.loop/regression.tsv), requirement, guards MON-5, nightly, PASS 2026-11-09, seen failing 2026-11-08
- Given an unchanged pass, when the board is printed, then the full board is printed again and there is no one-line mode. — [live-board-no-oneline](../../.loop/regression.tsv), requirement, guards MON-5, both, PASS 2026-11-09, seen failing 2026-11-09
- Given no cadence setting, when check-ins are scheduled, then the cadence is 30 minutes. — [live-board-cadence](../../.loop/regression.tsv), requirement, guards MON-5, both, PASS 2026-11-09, seen failing 2026-11-09
- Given an operation-session check-in reply, when it stops without the headline, All sessions, Dependencies, Needs you and Coming up last, then the hook blocks it and says what is missing, and a reply in that layout passes. — [reply-hook-blocks](../../.loop/regression.tsv), requirement, guards MON-5, both, PASS 2026-11-09, seen failing 2026-11-09
- Given a worker session or a session in another repo, when it stops with any reply, then the hook never checks it, and only the operation session is checked. — [reply-hook-scope](../../.loop/regression.tsv), requirement, guards MON-5, both, PASS 2026-11-09, seen failing 2026-11-09
- Given reply_hook set to false in the config, when the operation session stops without the board, then the hook lets it through. — [reply-hook-off](../../.loop/regression.tsv), requirement, guards MON-5, both, PASS 2026-11-09, seen failing 2026-11-09
- Given a reply blocked twice in a row or a broken hook input, when the session stops again, then the hook lets it through and logs it instead of looping. — [reply-hook-guard](../../.loop/regression.tsv), requirement, guards MON-5, both, PASS 2026-11-09, seen failing 2026-11-09
- Given a repo, when setup --reply-hook runs, then the Stop hook is merged into its machine-local Claude settings, which git ignores, and a second run changes nothing. — [reply-hook-install](../../.loop/regression.tsv), requirement, guards MON-5, both, PASS 2026-11-09, seen failing 2026-11-09
- Given the reply hook's toy suite, when it runs, then every check passes. — [reply-hook-all](../../.loop/regression.tsv), requirement, guards MON-5, both, PASS 2026-11-09, seen failing 2026-11-09
- Given the Monitoring PRD, when MON-5 is read, then it carries the check-in reply layout the hook enforces. — [reply-hook-mon5-wording](../../.loop/regression.tsv), requirement, guards MON-5, both, PASS 2026-11-09, seen failing 2026-11-09

### Defect tests

- Given a goal worked in a session, when the board is printed, then it shows its session name and step and never shows it as a failed background worker. — [session-board-issue98](../../.loop/regression.tsv), defect, guards [#98](https://github.com/jcl2018/agent-workflow-template/issues/98) closed (2026-11-09), both, PASS 2026-11-09, seen failing 2026-11-09
- Given a goal whose pull request is open (done), when a session report says running or failed, then the goal stays done. — [report-done-final](../../.loop/regression.tsv), defect, guards [#108](https://github.com/jcl2018/agent-workflow-template/issues/108) state unknown, both, not run, seen failing 2026-11-09
- Given a session goal with an old failure report and a newer session report, when the live board prints, then its next line is the newer report. — [held-stale-next](../../.loop/regression.tsv), defect, guards [#102](https://github.com/jcl2018/agent-workflow-template/issues/102) state unknown, both, not run, seen failing 2026-11-09
- Given a running goal with no worker (session reassigned, worktree kept), when the live board prints, then it is listed as held, not running and not as a background worker. — [held-shows-held](../../.loop/regression.tsv), defect, guards [#102](https://github.com/jcl2018/agent-workflow-template/issues/102) state unknown, both, not run, seen failing 2026-11-09
- Given a goal handed to a worker session before it is frozen, when the live board prints, then it shows at once under that session with step freezing. — [held-freezing](../../.loop/regression.tsv), defect, guards [#102](https://github.com/jcl2018/agent-workflow-template/issues/102) state unknown, both, not run, seen failing 2026-11-09
- Given a goal whose step is outside the flow, such as checks, when the live board prints, then it keeps its last known flow step, not idea 0%. — [held-off-flow](../../.loop/regression.tsv), defect, guards [#102](https://github.com/jcl2018/agent-workflow-template/issues/102) state unknown, both, not run, seen failing 2026-11-09
- Given a check-in reply that lacks the one headline, the All sessions table, the Dependencies graph, numbered Needs you or Coming up last, when it is checked, then each missing piece is named, and a reply in the issue 123 layout passes. — [reply-hook-checkin-123](../../.loop/regression.tsv), defect, guards [#123](https://github.com/jcl2018/agent-workflow-template/issues/123) state unknown, both, not run, seen failing 2026-11-10
