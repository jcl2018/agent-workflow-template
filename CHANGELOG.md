# Changelog

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
