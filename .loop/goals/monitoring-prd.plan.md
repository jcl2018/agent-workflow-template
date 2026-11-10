# Plan: monitoring-prd

Goal file: .loop/goals/monitoring-prd.md (done lines frozen). Design: .loop/goals/monitoring-prd.design.md.

## Implementation plan

### Context

The owner approved Monitoring MON-4 and MON-6..MON-12 on 2026-11-10. This goal also fixes issues 94, 97, 111, 112,
113, 114, 115, 122, 123 and 175, and covers the merged-in reply-hook line (MON-5's hook already exists, with rows
reply-hook-blocks, -scope, -off). Every script stays under 20 KB, so new behaviour goes into new modules in
skills/workflow-monitoring/scripts/. Existing files get call sites only, with a byte budget per file (below).
estimate-model (live_board.py) and delivery-prd (same folder) merge around us: merge origin/main before build, before
review and before pr.

### Byte budget for existing files (now → cap after this goal)

| File | Now | Added at most | Note |
|---|---:|---:|---|
| live_board.py | 18.6 KB | +0.8 KB | Dependencies → dep_graph.render; Issues → issue_lines.shape; held/silent → goal_state; pool line |
| sessions.py | 18.5 KB | +0.9 KB | 175 fix (KEPT branch frees on merged); `--recommend`, `--kind` flags; attempt check delegated to pool.attempt_ok; pool.return_session call |
| watch.py | 19.5 KB | +0.3 KB | holds_slot via goal_state (one line); nothing else |
| board.py | 16.2 KB | +1.0 KB | collect/build use goal_state; digest counts held and freezing; pr_state via prs.state |
| monitor.py | 11.8 KB | +1.0 KB | report and plan read the pool (goal_state) and list held/freezing |
| operate.py | 5.4 KB | +2.0 KB | print checkin.py, run replan.py and auto.py each pass, `claim`, owner answers to answers.jsonl |
| board_status.py | 7.3 KB | +0.3 KB | pr_states → prs.states |
| session_bind.py | 4.8 KB | +0.6 KB | stamp attempt, keep history |
| settings.py | 11.7 KB | +0.8 KB | four keys |
| setup.py | 13.3 KB | +1.5 KB | `--govern-hook` (shares reply_hook's installer code path) |

Any file that would pass 19.5 KB moves its addition into the new module instead. The health size rule proves it at qa.

### New modules (skills/workflow-monitoring/scripts/)

1. **goal_state.py** (issues 113, 111, 112, 115; MON-8). `classify(run, taken, at, cfg)` returns one of running,
   waiting, failed, stopped, held, freezing, silent, done, merged, retired, queued, plus `held_since`, `holds_slot`,
   `silent_for`. `holds_slot(run, taken)` reads the pool when `taken` is given (issue 112: a held session goal stops
   holding a slot once its pool entry is free). `silent` = a session or background worker whose latest report (newest of
   `report.at`, `reports[-1].at`, `bound_at`, `updated`) is older than `silent_minutes` (default 30). `held_since`:
   `held_at` stamped by `stamp_held(run)` the first time a goal reads held, cleared on bind (issue 115). live_board,
   board.collect/build, monitor.report/plan, watch's exit test and board.cmd_handoff call it.
2. **dep_graph.py** (issues 94, 123). `render(items, width=60)` draws running and queued goals top to bottom: one
   level per dependency depth (status_graph.levels), each node `[>] slug` running, `[=] slug` holding or paused,
   `[ ] slug` queued, `[?] slug` waiting on you, `[!] slug` stuck; under each level a `|` / `v` connector and, for a
   goal that waits on several, a line `slug <- a, b`. Lines longer than `width` are wrapped by live_board.fit. A legend
   line closes it. An empty graph prints `- (none)`. A cycle is drawn once with `(cycle)`.
3. **issue_lines.py** (issue 97). `shape(lines, runs, at)` keeps each Issues entry ≤ 60 columns, replaces raw agent
   output with a plain cause (usage limit, permission refused, test failure, crashed, unknown), groups goals stopped by
   the same cause into one entry (`usage limit: 4 goals paused until Nov 11 16:00; they resume by themselves`), and
   `finish(runs)` returns "paused until <time>" when every live goal is paused by one cause.
4. **prs.py** (MON-9). `states(runs, root)` asks gh for each done run's PR in a thread pool (8 workers, 5 s timeout
   each) and caches results in `<common>/loop/pr-states.json`: MERGED forever, OPEN and CLOSED for 60 s; written by
   temp file + `os.replace` (atomic; last writer wins, a lost write only costs a re-ask). `state(url, root)` for one.
   Health on the board reads workflow-health's last verdict file if under 10 minutes old, else "unknown" (no health
   run inside the board build).
5. **pool.py** (MON-12, MON-6, issues 114, 122, 175). Commands:
   - `status` → `pool: F free, B busy, T total (target N)`; also used by board and check-in.
   - `need` → K = max(min(pool_size - total, ready - free), 0) when free < ready, else max(pool_size - total, 0) only
     on the first fill (total 0). K never pushes total above pool_size (no create-then-archive churn); ready goals
     beyond the target wait under Needs you with "pool full (N of N busy)".
   - `add ID [ID…] [--name-prefix worker]` registers new idle sessions (state free).
   - `decline K` records the declined K in `<common>/loop/pool.json`; cleared when K reaches 0 or the pool is filled.
     After a decline, the pool ask is hidden until K grows past the declined K; a ready goal with no free session still
     shows its one-line wait.
   - `return SLUG` (MON-6): frees the goal's busy sessions; if total > pool_size the session is marked `archive` (the
     check-in tells the operation session to archive it with the app) else `free`; then, only when gh says MERGED,
     `git worktree remove` (no `--force`; a dirty worktree is named in Needs you) and `git branch -D loop/SLUG`, reusing
     worker.py cleanup's branch check.
   - attempt identity (114): `attempt_ok(state, attempt)`; bind increments `run.attempt` and copies it to the pool entry;
     `sessions.py report --attempt N` older than the run's attempt is recorded in `reports` but not applied; a report
     without `--attempt` is applied as today (old workers keep working). `freed_from` is appended to the entry's
     `history` list so it survives reuse.
   - read_pool quarantine (122.3): a malformed entry is moved to `<common>/loop/session-pool.bad.json` and named under
     Issues; the rest of the pool keeps working. A file that isn't JSON still blocks (as today), since nothing in it can
     be trusted.
   - 122.1: a retired run whose session is still busy shows under Issues and `return` frees it; 122.2 = 175.
6. **replan.py** (MON-10). `plan(root, at)`, run by operate.py after watch:
   - starts: what watch started this pass (read from watch's output lines), logged with "dependencies met, slot free";
   - merge proposals: two queued (not running) goals with the same `prd:` field and overlapping `touches:` from their
     queue lines; goals without both fields are never proposed (logged once: "no prd or touches");
   - split proposals: a goal two or more others wait on, whose queue line has `parts:`; none without `parts:`;
   - merge-line order: done goals with open PRs ordered by status_graph.chain's critical path, advisory only (merge.py
     is not changed);
   - never stops or restarts a running goal. Each change is appended once to `<common>/loop/replan.log` as
     `<time> <kind> <slugs>: <reason>`; a proposal already logged with the same reason is not logged or shown again.
7. **auto.py** (MON-11). `pass` (operate.py calls it each pass; the operation session may run it by hand):
   - for each `waiting` run with no `waiting.auto` and a new `waiting.at`: excluded when kind is missing, unknown or
     not `routine`, when there is no recommendation, when a keyword matches (whole word, case-insensitive; phrases such
     as `reset --hard`, `merge to main` matched as phrases): delete, remove, drop, rm, reset --hard, force, overwrite,
     publish, release, deploy, merge to main, push, pay, purchase, billing, cost, permission, access, token, secret,
     credential, password, license; or when `<common>/loop/answers.jsonl` holds an entry with source `owner`, the same
     goal and the same question key (lower-cased, spaces collapsed) with different words;
   - excluded: logged once per waiting report as `waits: <why>` and left under Needs you; re-evaluated only when a new
     waiting report arrives;
   - answered: send the recommended words with `operate.py send SLUG WORDS --source auto` (inbox + session message);
     the worker treats them as the owner's answer and runs `goal.py answer` itself; append
     `time | slug | question | answer | reason` to `<common>/loop/auto.log`; set `waiting.auto`;
   - `full_auto` false: nothing is sent; read fresh at each decision.
   `operate.py send` appends `{slug, key, words, source}` to answers.jsonl (source owner unless `--source auto`), the
   key from the run's current `waiting.ask`.
8. **govern_hook.py** (MON-7). A PreToolUse hook. Default on; `govern_hook: false` in config or `LOOP_GOVERN_HOOK=0`
   turns it off, read at each call. Installed with `setup.py --govern-hook` (and `--reply-hook` also installs it, so
   existing reply-hook repos get it on re-run). It acts only in the operation session: the session id is in
   `<common>/loop/operation.id` (written by `operate.py claim`, run at the start of `operate.py run` and by the
   operation session once; each claim overwrites; claim refuses with LOOP_ROLE=worker or in a goal worktree), or
   reply_hook's transcript signal says operation. It blocks Edit, Write, NotebookEdit; and each Bash segment (split on
   `&&`, `||`, `;`, `|`, newline; `env X=Y` and `bash -c`/`sh -c` bodies re-parsed once) whose git invocation (after
   `-C DIR`, `-c k=v`, `--git-dir=…`, `--work-tree=…`) is commit, push, merge, rebase, reset, cherry-pick, revert or am.
   Every segment is judged alone: `merge.py X && git push` is blocked. The listed merge and post-merge steps (merge.py,
   release.py, autorelease.py, wiki.py, pool.py return, worker.py cleanup) contain no visible git write and pass as any
   other command; the list documents what the session may run. Command substitution and shell writes (`sed -i`, `>`)
   are out of its claim. Fail open on any error with one log line in `<common>/loop/govern-hook.log`.
9. **checkin.py** (MON-4, MON-5, MON-10, MON-11, MON-12). `render(root)` prints the check-in in reply_hook's layout:
   headline; All sessions (one row a goal: session, repo, about, status, progress, left, latest, plus the pool line);
   Dependencies (dep_graph); Needs you (numbered: waiting and stuck goals with options and the recommended answer,
   auto-excluded decisions, silent workers, the pool ask, cleanup actions such as "archive session X"); Coming up;
   then `Re-plan:` and `Auto-answered:` with changes since the last check-in. It passes reply_hook.problems.

### Edits to existing behaviour

- operate.py `one_pass`: build board.json and pages as now, but print checkin.py's block instead of board.py's
  output; run `replan.py` and `auto.py pass` after watch; `claim` at run start. `monitor.py report`, `monitor.py
  dashboard`, `board.py board` asked directly still print the live board (MON-4).
- sessions.py `cmd_report`: in the KEPT branch, when `said == "merged"`, call `release(slug)` and `pool.return_session`
  (175). After any ended report, call `pool.return_session`. New flags `--recommend W`, `--kind K`, `--attempt N`.
- live_board.py: QUIET default 1800 via goal_state.silent_minutes; Issues through issue_lines.shape; Dependencies through
  dep_graph.render; pool line under Running goals; finish via issue_lines.finish.
- settings.py TABLE: `full_auto` True, `pool_size` 20 (the owner's PRD number: room for every goal of a large PRD at
  once), `silent_minutes` 30, `govern_hook` True.
- SKILL.md, references/operation.md, references/commands.md: the board prints only for report, dashboard and "where do
  things stand"; the new commands and settings; Command map rows for pool, auto, replan, checkin.
- docs/wiki/Monitoring.md: Usage lines for the new commands; Tests section re-rendered from the rows (requirement
  text untouched: docs-format owns it).

### Tests

One new toy suite, `dev/toy/test-monitoring-prd.sh` (made-up repo, fake gh, stand-in pool; no model), with a named PASS
line per check, and regression rows in `.loop/regression.tsv`, each seen failing on the old code (`regression.py red`)
then passing:

| Row id | Category | Guards | Proves |
|---|---|---|---|
| mon4-checkin-no-board | criterion | MON-4 | operate.py --once prints the check-in layout, not `LIVE BOARD`; monitor report still prints it |
| mon6-merged-frees | criterion | MON-6 | a merged report frees the session, removes worktree and branch; total = pool_size keeps, +1 archives |
| mon7-govern-blocks | criterion | MON-7 | operation session: Edit, `git -C . commit`, `merge.py X && git push` blocked; a worker and `git status` pass; off switch |
| mon8-silent-30 | criterion | MON-8 | a worker silent 31 minutes shows under Needs you; 29 minutes does not |
| mon9-board-fast | criterion | MON-9 | 12 goals, fake gh sleeping 3 s: board builds in < 10 s |
| mon10-replan | criterion | MON-10 | starts logged with reason; merge and split proposals once; no running goal stopped |
| mon11-full-auto | criterion | MON-11 | routine answered and logged; destructive, no-kind, keyword and owner-contradicting wait; off applies at next decision; "keyboard" not excluded |
| mon12-pool | criterion | MON-12 | status line; K; fill ask; add; decline hides; empty pool waits with its fix |
| deps-graph-94 | defect | #94 | Dependencies is a top-to-bottom graph ≤ 60 columns with markers and a legend |
| issues-phone-97 | defect | #97 | four usage-limit stops make one ≤ 60-column line; no raw output; finish says paused |
| report-held-111 | defect | #111 | monitor report and board digest list held and freezing goals |
| slot-pool-112 | defect | #112 | a held goal whose session was freed holds no slot |
| state-shared-113 | defect | #113 | board, report, watch give the same state for each goal of a fixture |
| attempt-114 | defect | #114 | an old attempt's report is recorded, not applied; history keeps freed_from |
| held-time-115 | defect | #115 | the board shows time since held, not since last change |
| pool-edges-122 | defect | #122 | retired busy session shows and frees; one bad entry quarantined, others work |
| merged-frees-175 | defect | #175 | `report --status merged` on a done goal frees its session |

MON-5's merged-in line is covered by the existing reply-hook rows; the reply-hook row for checkin.py's output
(`checkin-passes-hook`) is added under MON-5. Issue 123's wanted printout is covered by mon4 + deps-graph-94.

### Order

1. Merge origin/main. goal_state.py and call sites; rows 111, 112, 113, 115, MON-8.
2. prs.py, issue_lines.py, dep_graph.py into live_board and board; rows 94, 97, MON-9.
3. pool.py, sessions.py 175 + flags, session_bind attempt; settings keys; rows 114, 122, 175, MON-6, MON-12.
4. auto.py, replan.py, checkin.py, operate.py; rows MON-4, MON-10, MON-11.
5. govern_hook.py and setup.py; row MON-7.
6. Docs (SKILL.md, references, wiki Usage and Tests), Verify by hand, health size check, full regression lane.

### Not in scope

- Creating, renaming or archiving sessions from a script (only the app can; the check-in names the action).
- Changing merge.py's order (advisory only), applying merges or splits automatically.
- Editing Monitoring.md's requirement text.

## Review record

(written by the plan step's reviewers)
