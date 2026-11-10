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

### the review runner run log (run plan review-run-20261110101659, session_kind unattended, status gate_pending)

Host: the review runner. Scope: UI no (4 matches); DX yes (9 term matches, developer tool). Phase order: ceo → dx → eng.
Deviation: plan review guard: not enforced by this host; publication order is unverified (GUARD_NOT_INSTALLED)

#### ceo: closed 2026-11-10T10:20:09.514Z; snapshot 313db0318a3d211cb73908951eed4c9636836ca9c2c65d064beb1a291abe65a2

- native completed (model claude-opus-5-5, provider host-subagent, 12 findings, sha256 7fee60111e11)
- outside completed (model gpt-6-astra, provider host-subagent, 8 findings, sha256 9b60a6d769e6)

```
CEO DUAL VOICES — CONSENSUS TABLE:
  Severity        claude-opus-5-5(native)      gpt-6-astra(host-subagent)
  Critical        0                            1
  High            4                            5
  Medium          6                            2
  Low             2                            0
  Informational   0                            0
  Findings        12                           8
CONFIRMED 0 · SAME LOCATION, UNVERIFIED 0 · DISAGREE 0 · NEW (outside only) 8 · native only 12. Both completed.

Reconciliation (each outside finding against the native result):
| outside | native | disposition | resolution |
|---|---|---|---|
| plan review-run-20261110101659-ceo-outside-1 Acceptance criteria do not establish reduced coordination cost or better delivery | — | new | not raised by the native voice |
| plan review-run-20261110101659-ceo-outside-2 Default automatic answers let workers authorize their own recommendations | — | new | not raised by the native voice |
| plan review-run-20261110101659-ceo-outside-3 Command filtering does not enforce coordinator merge authority | — | new | not raised by the native voice |
| plan review-run-20261110101659-ceo-outside-4 Session reuse depends on an unproven host lifecycle | — | new | not raised by the native voice |
| plan review-run-20261110101659-ceo-outside-5 Pool inventory is disconnected from throughput and aggregate spend control | — | new | not raised by the native voice |
| plan review-run-20261110101659-ceo-outside-6 Untagged reports bypass the proposed stale-attempt protection | — | new | not raised by the native voice |
| plan review-run-20261110101659-ceo-outside-7 Replanning heuristics lack reliable inputs and evidence of decision value | — | new | not raised by the native voice |
| plan review-run-20261110101659-ceo-outside-8 Bundled rollout obscures value and compounds operational risk | — | new | not raised by the native voice |
| — | plan review-run-20261110101659-ceo-native-1 MON-6..MON-12 have no requirement text and MON-4/MON-5 text contradicts the new behaviour, yet the plan puts requirement text out of scope | native_only | not raised by the outside voice |
| — | plan review-run-20261110101659-ceo-native-2 MON-10 merge/split proposals are inert: the queue has no prd: or parts: fields and nothing adds them | native_only | not raised by the outside voice |
| — | plan review-run-20261110101659-ceo-native-3 full_auto (default on) trusts the worker's self-declared kind and a whole-word denylist that misses inflections, synonyms and risky_paths | native_only | not raised by the outside voice |
| — | plan review-run-20261110101659-ceo-native-4 One goal bundles 8 requirements, 10 issues, 8 modules and 17 rows into one PR, the owner's only gate, against a 120-min/3M budget and two concurrent goals on the same files | native_only | not raised by the outside voice |
| — | plan review-run-20261110101659-ceo-native-5 Pool first fill asks the owner to create pool_size (20) sessions regardless of how many goals are ready | native_only | not raised by the outside voice |
| — | plan review-run-20261110101659-ceo-native-6 Health on the board will almost always read 'unknown': the 10-minute freshness window vs health_cron every 4 hours | native_only | not raised by the outside voice |
| — | plan review-run-20261110101659-ceo-native-7 Govern hook identity is last-claim-wins with silent fail-open; a second claim or stale operation.id silently ungoverns a session | native_only | not raised by the outside voice |
| — | plan review-run-20261110101659-ceo-native-8 MON-8's 30-minute silence conflicts with the existing session-quiet row (an hour) and will flood Needs you during long test steps at 10-20 parallel workers | native_only | not raised by the outside voice |
| — | plan review-run-20261110101659-ceo-native-9 No outcome metric: owner interruptions per merged goal and auto-answer reversals are not measured, so full_auto and pool defaults can't be judged | native_only | not raised by the outside voice |
| — | plan review-run-20261110101659-ceo-native-10 Owner-contradiction check matches only an identical normalized question key; paraphrased questions bypass it and there is no undo or veto window | native_only | not raised by the outside voice |
| — | plan review-run-20261110101659-ceo-native-11 The 20 KB rule, not design, decides module placement (watch.py +0.3 KB budget); Approach C was dismissed for timing only, with no follow-up | native_only | not raised by the outside voice |
| — | plan review-run-20261110101659-ceo-native-12 Pool/session lifecycle depends on desktop-app tools that may be superseded by native multi-session features | native_only | not raised by the outside voice |
```

#### design: skipped (no UI scope detected)

#### dx: closed 2026-11-10T10:28:53.626Z; snapshot 313db0318a3d211cb73908951eed4c9636836ca9c2c65d064beb1a291abe65a2

- native completed (model claude-opus-5-5, provider host-subagent, 17 findings, sha256 e572533c2c6b)
- outside completed (model gpt-6-astra, provider host-subagent, 21 findings, sha256 86659401934f)

```
DX DUAL VOICES — CONSENSUS TABLE:
  Severity        claude-opus-5-5(native)      gpt-6-astra(host-subagent)
  Critical        1                            5
  High            7                            14
  Medium          8                            2
  Low             1                            0
  Informational   0                            0
  Findings        17                           21
CONFIRMED 0 · SAME LOCATION, UNVERIFIED 0 · DISAGREE 0 · NEW (outside only) 21 · native only 17. Both completed.

Reconciliation (each outside finding against the native result):
| outside | native | disposition | resolution |
|---|---|---|---|
| plan review-run-20261110101659-dx-outside-1 CAP4:operate.send:channel Failed session notification returns success | — | new | not raised by the native voice |
| plan review-run-20261110101659-dx-outside-2 CAP4:operate.run:channel Failed board generation becomes successful completion | — | new | not raised by the native voice |
| plan review-run-20261110101659-dx-outside-3 CAP4:watch.pool-unreadable:channel Corrupt ownership state returns exit zero | — | new | not raised by the native voice |
| plan review-run-20261110101659-dx-outside-4 CAP4:session.send:redaction Dependency stderr exposes credential text | — | new | not raised by the native voice |
| plan review-run-20261110101659-dx-outside-5 CAP4:govern-hook.error:channel Evaluation failure silently permits mutations | — | new | not raised by the native voice |
| plan review-run-20261110101659-dx-outside-6 CAP6:auto.dispatch:recovery Delivery has no idempotency or unknown-outcome reconciliation | — | new | not raised by the native voice |
| plan review-run-20261110101659-dx-outside-7 CAP6:pool.return:recovery Partial cleanup has no safe restart contract | — | new | not raised by the native voice |
| plan review-run-20261110101659-dx-outside-8 CAP6:pool.read:fix Corruption and quarantine lack authoritative repair instructions | — | new | not raised by the native voice |
| plan review-run-20261110101659-dx-outside-9 CAP6:prs.lookup:context Dependency failures collapse into unexplained uncertainty | — | new | not raised by the native voice |
| plan review-run-20261110101659-dx-outside-10 CAP6:issue-lines:recovery Automatic-resume copy contradicts actual recovery policy | — | new | not raised by the native voice |
| plan review-run-20261110101659-dx-outside-11 CAP6:cli.validation:fix New arguments and settings lack actionable rejection contracts | — | new | not raised by the native voice |
| plan review-run-20261110101659-dx-outside-12 CAP6:state.persist:recovery New state writes lack partial-outcome reconciliation | — | new | not raised by the native voice |
| plan review-run-20261110101659-dx-outside-13 CAP6:govern.block:fix Tool denials lack an authorized next action | — | new | not raised by the native voice |
| plan review-run-20261110101659-dx-outside-14 CAP6:setup.govern-hook:recovery Partial installation has no verification or repair receipt | — | new | not raised by the native voice |
| plan review-run-20261110101659-dx-outside-15 Pool capacity has no enforcement point in assignment | — | new | not raised by the native voice |
| plan review-run-20261110101659-dx-outside-16 Untagged reports bypass attempt identity after session reuse | — | new | not raised by the native voice |
| plan review-run-20261110101659-dx-outside-17 Human output and free-text logs are used as machine protocols | — | new | not raised by the native voice |
| plan review-run-20261110101659-dx-outside-18 Usage-line documentation does not establish a first successful worker workflow | — | new | not raised by the native voice |
| plan review-run-20261110101659-dx-outside-19 Per-request PR timeouts exceed the board latency target | — | new | not raised by the native voice |
| plan review-run-20261110101659-dx-outside-20 Regression rows omit native failure signals and recovery guarantees | — | new | not raised by the native voice |
| plan review-run-20261110101659-dx-outside-21 Unresolved replan proposals disappear after their first presentation | — | new | not raised by the native voice |
| — | plan review-run-20261110101659-dx-native-1 CAP4:govern_hook.py:channel - fail-open on any error reports allow with only a log line; the guard can be dead with no visible signal | native_only | not raised by the outside voice |
| — | plan review-run-20261110101659-dx-native-2 CAP6:govern_hook.py block:fix - the deny reason and channel are unspecified, so the operation-session model gets no fix or off switch | native_only | not raised by the outside voice |
| — | plan review-run-20261110101659-dx-native-3 CAP6:pool.py return:recovery - a dirty worktree or unknown PR state leaves partial side effects with no fix line or re-run rule | native_only | not raised by the outside voice |
| — | plan review-run-20261110101659-dx-native-4 CAP6:auto.py pass:recovery - send failure ordering is unspecified; waiting.auto set before a failed send loses the answer forever | native_only | not raised by the outside voice |
| — | plan review-run-20261110101659-dx-native-5 CAP6:prs.py states:context - gh timeout, missing auth or missing gh produce unspecified board output and may be cached as state | native_only | not raised by the outside voice |
| — | plan review-run-20261110101659-dx-native-6 CAP6:new CLIs:fix - refusals for operate.py claim, pool.py add/decline, sessions.py --kind/--attempt are unspecified | native_only | not raised by the outside voice |
| — | plan review-run-20261110101659-dx-native-7 First run: the pool's first fill asks for pool_size (20) sessions, and the ask doesn't say how to get the IDs for pool.py add | native_only | not raised by the outside voice |
| — | plan review-run-20261110101659-dx-native-8 Upgrade: setup.py --reply-hook silently installs a new blocking PreToolUse hook; --remove semantics for the hook pair are undefined | native_only | not raised by the outside voice |
| — | plan review-run-20261110101659-dx-native-9 The quiet threshold has two knobs: LOOP_SESSION_QUIET (3600 today) vs the new silent_minutes (30); precedence is unspecified | native_only | not raised by the outside voice |
| — | plan review-run-20261110101659-dx-native-10 sessions.py report --kind has no enumerated values and --recommend has no stated relation to --words | native_only | not raised by the outside voice |
| — | plan review-run-20261110101659-dx-native-11 replan.py and checkin.py have no CLI though Command map rows are promised, and replan scrapes watch's stdout for starts | native_only | not raised by the outside voice |
| — | plan review-run-20261110101659-dx-native-12 Auto-answer escape hatches are global only: no preview, no per-goal opt-out, fixed keyword list | native_only | not raised by the outside voice |
| — | plan review-run-20261110101659-dx-native-13 govern hook blocks aren't logged and there is no status/debug command, so false positives can't be diagnosed or measured | native_only | not raised by the outside voice |
| — | plan review-run-20261110101659-dx-native-14 Redaction: govern-hook.log, auto.log and answers.jsonl may store raw command text or answer words that contain tokens | native_only | not raised by the outside voice |
| — | plan review-run-20261110101659-dx-native-15 Docs list files to touch but give no copy-paste examples of the check-in, a pool session or a govern block | native_only | not raised by the outside voice |
| — | plan review-run-20261110101659-dx-native-16 operate.py send records every owner message as an answer keyed to waiting.ask, even a follow-up sent to a goal that isn't waiting | native_only | not raised by the outside voice |
| — | plan review-run-20261110101659-dx-native-17 No DX measurement of auto-answer reversals, govern blocks or declined pool asks | native_only | not raised by the outside voice |
```

#### eng: closed 2026-11-10T10:35:49.879Z; snapshot 313db0318a3d211cb73908951eed4c9636836ca9c2c65d064beb1a291abe65a2

- native completed (model claude-opus-5-5, provider host-subagent, 17 findings, sha256 c85167af425b)
- outside completed (model gpt-6-astra, provider host-subagent, 15 findings, sha256 f925b0bd3310)

```
ENG DUAL VOICES — CONSENSUS TABLE:
  Severity        claude-opus-5-5(native)      gpt-6-astra(host-subagent)
  Critical        0                            1
  High            4                            11
  Medium          7                            3
  Low             6                            0
  Informational   0                            0
  Findings        17                           15
CONFIRMED 0 · SAME LOCATION, UNVERIFIED 0 · DISAGREE 0 · NEW (outside only) 15 · native only 17. Both completed.

Reconciliation (each outside finding against the native result):
| outside | native | disposition | resolution |
|---|---|---|---|
| plan review-run-20261110101659-eng-outside-1 Merged PR status does not prove the current local branch is safe to delete | — | new | not raised by the native voice |
| plan review-run-20261110101659-eng-outside-2 Release followed by return breaks archival and can free a replacement attempt | — | new | not raised by the native voice |
| plan review-run-20261110101659-eng-outside-3 Attempt fencing omits automatic assignment and accepts unfenced legacy reports | — | new | not raised by the native voice |
| plan review-run-20261110101659-eng-outside-4 Independent whole-record writes can overwrite newer binds and decisions | — | new | not raised by the native voice |
| plan review-run-20261110101659-eng-outside-5 Pool capacity is not enforced by the dispatch path | — | new | not raised by the native voice |
| plan review-run-20261110101659-eng-outside-6 Quarantine can erase live ownership and permit duplicate workers | — | new | not raised by the native voice |
| plan review-run-20261110101659-eng-outside-7 Default auto answers turn worker-authored recommendations into owner authority | — | new | not raised by the native voice |
| plan review-run-20261110101659-eng-outside-8 Automatic delivery lacks question identity, deduplication and acknowledgement | — | new | not raised by the native voice |
| plan review-run-20261110101659-eng-outside-9 Serial board lookups and per-request timeouts violate the latency target | — | new | not raised by the native voice |
| plan review-run-20261110101659-eng-outside-10 Operation pipeline failures can become successful completion and lost notifications | — | new | not raised by the native voice |
| plan review-run-20261110101659-eng-outside-11 Shell splitting bypasses supported quoted shell-body cases | — | new | not raised by the native voice |
| plan review-run-20261110101659-eng-outside-12 Last-claim identity and fail-open errors silently remove governance | — | new | not raised by the native voice |
| plan review-run-20261110101659-eng-outside-13 Replanning lacks validated metadata, structured starts and persistent proposal state | — | new | not raised by the native voice |
| plan review-run-20261110101659-eng-outside-14 Stale reports and administrative writes reset the silence clock | — | new | not raised by the native voice |
| plan review-run-20261110101659-eng-outside-15 Cause grouping fabricates shared reset times and automatic recovery | — | new | not raised by the native voice |
| — | plan review-run-20261110101659-eng-native-1 Merged cleanup trusts a worker's self-reported merged status and force-deletes loop/SLUG (git branch -D), contradicting the plan's 'only when gh says MERGED' and worker.py cleanup's --merged/-d check | native_only | not raised by the outside voice |
| — | plan review-run-20261110101659-eng-native-2 Govern hook splits on && ; | before quote-aware tokenizing, so bash -c "git commit && git push" passes; timeout/nohup/time/xargs/nice wrappers also pass (measured with govern_hook.py check) | native_only | not raised by the outside voice |
| — | plan review-run-20261110101659-eng-native-3 MON-9 relies on 'workflow-health's last verdict file' which no code writes; today live_board.health runs health.py check inline with a 30 s timeout, and the mon9 toy can mask it with LOOP_BOARD_HEALTH | native_only | not raised by the outside voice |
| — | plan review-run-20261110101659-eng-native-4 Bind increments run.attempt on every bind, including a same-session re-bind, so the live worker's later reports (merged included) are recorded but never applied and its session is never freed | native_only | not raised by the outside voice |
| — | plan review-run-20261110101659-eng-native-5 PR fan-out of 8 workers x 5 s cannot meet <10 s beyond 8 slow PRs (ceil(N/8)*5 s, N up to pool_size 20), and failed lookups are not cached so gh outages re-pay timeouts every pass | native_only | not raised by the outside voice |
| — | plan review-run-20261110101659-eng-native-6 replan.py is to log starts 'read from watch's output lines', but watch runs in another process whose stdout operate.py discards on success; the build logs no starts | native_only | not raised by the outside voice |
| — | plan review-run-20261110101659-eng-native-7 Byte budget table already exceeded by the build (sessions +967 B, board +1253 B, operate +2813 B vs origin/main), omits graph.py (+365 B), and leaves KB undefined against the 19.5 KB rule while estimate-model edits live_board.py concurrently | native_only | not raised by the outside voice |
| — | plan review-run-20261110101659-eng-native-8 Run records gain more unlocked writers: auto.py read-modify-writes runs/<slug>.json with os.replace while a worker's sessions.py report can land in between and be lost | native_only | not raised by the outside voice |
| — | plan review-run-20261110101659-eng-native-9 operate.py run claims the operation session only if CLAUDE_SESSION_ID is set, an env var nothing in the repo shows the harness provides; when absent, the claim is silently skipped and govern relies on the transcript fallback | native_only | not raised by the outside voice |
| — | plan review-run-20261110101659-eng-native-10 pool need is specified as two formulas and the first-fill branch asks for pool_size (20) sessions with 2 ready goals; the build uses pool_size - total whenever free < ready | native_only | not raised by the outside voice |
| — | plan review-run-20261110101659-eng-native-11 Issue 123 asks for every worker session across all repos the operation session governs; checkin.render(root) is single-repo yet the plan says 123 is covered | native_only | not raised by the outside voice |
| — | plan review-run-20261110101659-eng-native-12 held_since falls back to run.updated when held.json has no stamp (only replan.py stamps), reintroducing issue 115 for standalone monitor report or first pass | native_only | not raised by the outside voice |
| — | plan review-run-20261110101659-eng-native-13 Plan lists 'freezing' as a classify(run) result, but freezing is a pool entry with no run record; the API mixes run and pool domains | native_only | not raised by the outside voice |
| — | plan review-run-20261110101659-eng-native-14 govern-hook.log, auto.log, replan.log and answers.jsonl grow without bound and govern_hook.health reads the whole log every check-in | native_only | not raised by the outside voice |
| — | plan review-run-20261110101659-eng-native-15 Three PR-merged checks (worker.merged, sessions merged(pr), prs.state) and differing risky-word lists (plan phrase 'merge to main' vs build stem 'merg') are hand-synced | native_only | not raised by the outside voice |
| — | plan review-run-20261110101659-eng-native-16 graph.LAST_BAD module global is a side channel from read_pool to pool.quarantine, and sessions.py/pool.py import each other via __import__ | native_only | not raised by the outside voice |
| — | plan review-run-20261110101659-eng-native-17 For rows guarding new modules, 'seen failing on the old code' is satisfied trivially by a missing file and proves nothing about the guard | native_only | not raised by the outside voice |
```

Gate: gate_rev 1, 13 decisions (13 pending). Findings: 90. Tasks: 53.

### Worker's response to the findings (applied in build, before review)

- Cleanup (eng F1 both voices): the branch is deleted only when GitHub says MERGED and its tip is contained in the base
  (`git merge-base --is-ancestor`); otherwise it is kept and named. Worktree removal never forces.
- Attempts (eng native F4): a same-session re-bind no longer raises the attempt; a new session or a revived goal does.
  Untagged reports still apply (old workers keep working): decision d9/d10 kept, recommended a.
- Govern hook (DX F1/F5, eng F2/F11/F12): quote-aware shlex tokenizing with operators split outside quotes, env and
  bash -c bodies re-read; the session registers itself as operation from its own `operate.py run|claim` call (no env
  variable needed); fail-opens are counted and shown under Needs you; the deny names the fix and the off switch; logs
  hold the git verb only, never the command line.
- Full auto (CEO F3/F10, DX F4/F12/F18): whole-word stems with endings (keyboard passes, deleted waits), risky_paths,
  any owner answer on a goal sends later questions to the owner, waiting.auto set only after the send succeeds,
  `auto.py pass --dry-run`, answers.jsonl written only for a waiting question, each auto answer listed with its revert.
  Default stays on: the owner's direction (d4/d11 kept, recommended a).
- Board speed (MON-9; eng F3/F5/F9): PR states in one parallel wave (16 workers, 3 s each), failed lookups never cached,
  board.py prefetches; health never runs inline: last verdict with its age, a stale one refreshed in the background.
- Issues (DX F10, eng F15): usage-limit goals grouped per reset time; the fix line follows resume_on_limit.
- Re-plan (DX F21, eng F6): starts come from run records; open proposals show at every check-in until acted on.
- Pool: K = pool_size - total when free < ready (the owner's "creates every missing session"; never above pool_size).
- Requirement text (CEO d1): MON-6..MON-12 text belongs to docs-format; the rows guard MON-n ids already approved.
- Bundling (CEO d2, d7): kept as the owner bundled it; the operation session merges.
