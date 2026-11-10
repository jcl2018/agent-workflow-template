# Plan: loop-guards

Source: `.loop/goals/loop-guards.design.md` (spec review: 3 rounds; the 3 round-3 blocking fixes applied and verified;
minor concerns resolved below). Done lines: `.loop/goals/loop-guards.md`. Done line 6 is read as the owner chose (a)
on 2026-11-10, relayed by the operation session ("a").

## Implementation plan

1. New `skills/workflow-delivery/scripts/guards.py`, imported by goal.py and flow.py. It keeps goal.py (18,955 bytes)
   and role.py (17,711) under 20 KB, and holds the format rules, the no-try refusal and the operation's repair commands.
   - `RULES = {"depth-line": "0.12.1", "depth-condensed": "0.12.1", "full-markers": "0.12.1"}`. The release is text for
     messages only.
   - `known()` returns `sorted(RULES)`. `stamp(state, step)` sets `state.setdefault("rules_at", {})[step] = known()`.
   - `applies(state, step, rule)`: true when the record or the step has no `rules_at` (status quo for running goals), or
     when `rule` is in `rules_at[step]`.
   - `check_depth(state, step, text, cfg, result)` returns `(stamp, refusal, skipped)`. It is role.record_depth moved
     here; the DEPTH and STEP regexes, depth_of and markers stay in role.py and are called from here (no import
     cycle). It runs each sub-check only when `applies()` holds. A refusal reads `no DEPTH line (rule depth-line, added in v0.12.1).
     Fix: ...`. `skipped` lists `rule <id> (v<release>) not applied: <step> started before it`, and record logs each.
   - Every new refusal ends with a stable code in parentheses, in the style of need_lane's `(LANE_MISSING)`:
     `FORMAT_RULE` (with the rule id), `NO_STEP_LINE`, `NOT_RUN_BY_FLOW`, `NOT_WORKER`, `WORKER_SELF_REPAIR`,
     `RESUME_STATUS`, `RESUME_NO_SESSION`, `SESSION_TAKEN`, `DONE_LINES_CHANGED`, `TOUCHES_PATH`, `CWD_OUTSIDE`.
     workflow-delivery's references list each code with its fix.
   - `refuse_no_try(state, step, why, fix, save)`:
     - Increments `state["refusals"]`. From 5 on, it sets `state["note"] = {"text": "<step>: N refused records in a
       row: <why>", "at": now}`.
     - Saves with log `refused (no try used): <why>`.
     - Prints `REFUSED (no try used): <why>` and `NEXT: <fix>`, then exits 2. tries, status, step and the ran marker
       stay as they are.
   - `clear_refusals(state)`: sets refusals to 0 and drops a refusal note (only one whose text says "refused records").
   - `revive(state, how, by, why)`: the one revival used by resume and by sessions.py bind. It sets status running,
     tries 0, refusals 0, finding "", waiting None, note None and report None, and logs `<how> by <by>: <why>` (for
     example `resumed by operation session: ...`, `revived by bind (was failed)`). goal.py answer stays as it is: it
     moves waiting to running, not a stopped goal.
   - `resume(...)`, `widen(...)`, `note_finding(...)`, `sync_touches(...)`: the bodies of the new and changed goal.py
     commands (items 3-5).
   - Operation-added data lives in a sidecar that only the operation commands write:
     `<git common dir>/loop/runs/<slug>.extra.json`, holding `{"touches": [], "findings": [], "log": []}`. Writes take
     an exclusive `fcntl.flock` on `<slug>.extra.lock`, then read, append and atomic-replace. No writer of the main run
     record (goal.py, sessions.py, role.begin, flow.py, watch, worker, mend) can erase it, because none of them writes
     it. `guards.extra(slug)` reads it, and readers merge: the board's collect, sync_touches and `goal.py show`.
2. `goal.py record` (148, 147):
   - The "wasn't run by flow.py" refusal: if a run record exists, it goes through `refuse_no_try` (message gains "(no
     try used)"); otherwise `no()` as today.
   - need_lane's refusal (qa lane not passed on this HEAD) gains "(no try used)"; it already changes no state.
   - A malformed full_markers config isn't the worker's slip. It sets status waiting with the ask "the owner fixes
     full_markers in the flow file (<the error>)" and the words `go on <slug>` / `stop <slug>`. No try is used, and the
     goal leaves the worker's hands until the owner answers.
   - DEPTH, condensed and marker refusals: `refuse_no_try` instead of `failed_try`, without `os.remove(ran)`. `ran` is
     removed only after the checks pass.
   - A session goal's reply with no STEP line (the run record's `worker == "session"`, with or without
     `--in-session`, since flow.py's session route prints `record` without the flag): `refuse_no_try("<step> reply has no STEP line", "end the reply with the
     DEPTH line and a STEP: done|skipped|pending|failed line, then record again")`. A headless reply with no STEP line
     stays `failed_try`.
   - After a successful done, skipped or auto-approved record: `clear_refusals`, then `stamp(state, next_step)`, where
     next_step is the next FLOW step not yet recorded.
   - `cmd_new` stamps `idea`. watch.py's freeze (the normal goal start) stamps it too, by running
     `python3 <delivery scripts>/guards.py known`, which prints the rule ids as JSON (a CLI contract, not a cross-skill
     import). `role.begin` (flow.py, headless and in-session first ask) stamps the step it starts,
     overwriting an earlier entry. role.py imports guards lazily inside begin to avoid an import cycle.
3. `goal.py resume SLUG --why TEXT [--by WHO]` (149), the operation's command:
   - Refuses under `LOOP_ROLE=worker`: "a worker can't resume its own goal; ask the operation session". Exit 2.
   - Refuses unless status is `failed` or `stopped` ("<slug> is <status>; only a failed or stopped goal resumes").
   - Refuses unless `worker == "session"` and a session id is recorded: "<slug> has no session. Fix: sessions.py bind
     <slug> ID (bind revives it), or watch.py resume <slug> for a background worker".
   - Checks the session pool: the recorded session must be busy with this slug, or free. If it's free, resume reserves
     it (busy, this slug) before any other change. If it's busy with another goal, resume refuses with "session <id>
     now serves goal <other>. Fix: sessions.py bind <slug> ID with a free session". Nothing is written.
   - Reads the goal file from `state["worktree"]`, not the caller's checkout. A missing worktree or goal file is
     refused (`RESUME_NO_WORKTREE`). A done-sha mismatch is refused with exit 1: "the done lines changed after they
     were frozen; a wrong done line needs a new goal" (`DONE_LINES_CHANGED`). Every check runs before the pool
     reservation, so a refusal writes nothing: no fail_stop, no finding, no pool change.
   - Otherwise it calls `revive(state, "resumed", WHO, WHY)` (WHO defaults to "operation session") and prints
     `RESUMED <slug> at <step>`.
   - When the repo has a session tool (sessions.py `tool(cfg)`), it sends the bound session `goal <slug> resumed by
     <WHO>: <WHY>. Continue at <step> in <worktree>`. A failed send prints `NOTE: send failed; tell the session
     yourself` plus the exact resend command (`python3 <abs>/sessions.py send <slug> "<text>"`), the session id and the
     tool's first stderr line. The first line reads `RESUMED <slug> at <step> (message not delivered)`. It never
     starts a process.
4. `goal.py touches SLUG --add PATH --why TEXT` (157), the operation's command:
   - Refuses under `LOOP_ROLE=worker`. Refuses a PATH that is absolute, contains `..`, is already listed, or is not
     repo-relative.
   - Writes only the sidecar (append PATH to `touches`, log `touches +PATH: WHY`, under the lock), and prints
     `TOUCHES <slug> +PATH`. It never writes the main run record or the worker's worktree, so nothing can race it or
     erase it. board.py's collect returns run touches plus sidecar touches.
   - The worker brings the goal file's `- Touches:` line in line: goal.py record (each step) and goal.py pr call
     `guards.sync_touches`, which rewrites that line from run plus sidecar touches when they differ. goal.py pr syncs and
     commits it (path-limited `-- .loop/goals/<slug>.md`, which also takes any other pending edit of the worker's own goal
     file) right after its base merge and before the version bump and the pr lane, so the lane tests the final HEAD. Both run in the worker's own process, so nothing
     races. The goal file's Touches line isn't in the done-line hash.
5. `goal.py finding SLUG TEXT` (157): when status is `done` or `merged`, it appends `{"at", "text"}` to the sidecar's
   `findings` (under the lock), logs `finding (goal stays <status>): TEXT`, and prints `FINDING recorded on <slug> (goal
   stays <status>)`. Exit 0, nothing written to .loop/findings.md and no push. board.py's collect shows the newest
   sidecar finding in the goal's note field (`finding after <status>: TEXT`), so the operation's board shows it. Every
   other status keeps fail_stop.
5a. `goal.py answer` refuses unless status is `waiting` (`ANSWER_STATUS`), so it can't revive a stopped goal around
   resume's checks. `goal.py record` and `goal.py pr` refuse while status is `waiting`, with no try used
   (`WAITING_OWNER`: "<slug> waits for the owner: <ask>. Fix: the operation answers (goal.py answer)").
6. `role.guard(name, slug=None)` (121): goal.py passes `args.slug` and flow.py passes the slug. When
   `LOOP_ROLE != worker`:
   - If the slug's run record names a bound session: `REFUSED: <name> is worker work and LOOP_ROLE is not worker here.
     Fix: in <session name>, in <worktree>, run: LOOP_ROLE=worker python3 <absolute script path> <args, shlex-joined>. The operation
     session doesn't run goal steps.`
   - role.py lane passes argv[2] as the slug, so its refusal names the session too.
   - Otherwise: `REFUSED: <name> is worker work. Fix: start a worker for <slug> (batch.py start NAME), or bind a
     session (sessions.py bind <slug> ID) and run it there as LOOP_ROLE=worker.`
   - The REFUSE constant is replaced by these two texts. The existing check in dev/toy/test-operate.sh (exact old
     text) is updated to the new texts. resume, touches and finding stay outside the guard; resume and
     touches have their own worker refusal.
7. `sessions.py bind/assign` (121, 160):
   - bind prints `WORKER <slug>: run goal steps as LOOP_ROLE=worker python3 <abs path>/goal.py ... (and flow.py,
     role.py lane)` and `WORKTREE <slug>: <state worktree>`.
   - With a session tool, bind sends both lines to the session. A failed send prints a NOTE. The `SEND` text in assign
     gains the WORKER line (it already names the worktree).
   - bind's `--cwd DIR` (the session's folder): if `realpath(DIR)` is not the worktree or inside it, it refuses with
     exit 1 before changing the pool or the run record: `REFUSED: session folder DIR is outside the goal worktree PATH.
     Fix: start or move the session in PATH, then bind again`.
   - Without `--cwd`, under `LOOP_ROLE=worker`, it checks `os.getcwd()` the same way (a worker binding itself).
   - bind keeps reviving a failed or stopped goal (issue 98: a background goal moved into a session), now through
     `guards.revive(state, "revived by bind (was <status>)", ...)`, so bind and resume leave the same state. bind is
     the operation's command, refused under LOOP_ROLE=worker except when a worker binds itself to its own goal with
     `--cwd` inside its worktree. That self-bind only attaches the session: it never revives a failed or stopped goal,
     and prints `NEXT: ask the operation session to resume <slug>`.
   - The session pool's read-modify-write (assign, bind, resume's reservation, release) runs under an exclusive
     `fcntl.flock` on `session-pool.lock`. assign holds it from choosing a session to marking it busy, so resume can't
     reserve the same free session meanwhile. If saving the goal fails after a reservation, the reservation is undone
     under the same lock.
   - `sessions.call` keeps its contract (last stdout line or None), and also stores the tool's first stderr line in
     `sessions.LAST_ERROR` (empty on a missing executable: "cannot start <tool>"; on a timeout: "timed out after N s").
     resume's NOTE prints it. Tests cover a nonzero exit, a missing executable and a timeout.
     Otherwise it prints only the WORKTREE hint.
   - sessions.py is 14,309 bytes; this adds about 1.2 KB.
8. `dev/toy/test-guards.sh` (new; `# reads:` header with goal.py, guards.py, role.py, flow.py and sessions.py). It uses
   make.sh, fakegh and a fake session tool (a shell script that logs `start/rename/send` to a file). Checks, one PASS
   line each:
   - g1 147: a step whose `rules_at` lacks depth-line records without a DEPTH line and logs "not applied". A step that
     has it is refused, the message names `depth-line` and `v0.12.1`, and tries stays 0.
   - g2 148: a missing DEPTH line leaves tries 0, status running and the ran marker in place, and prints NEXT. The 5th
     refusal in a row sets the note. need_lane's refusal says "(no try used)". A good record then clears refusals and the note. An in-session no-STEP reply is
     refused with no try, and a headless no-STEP reply still uses a try.
   - g3 149: a stopped session goal resumes (status running, tries 0, report cleared, the log line, the fake tool got
     the send). A failing fake tool gives "(message not delivered)" and the resend command. Run from another checkout,
     it reads the goal file from the goal's worktree. A session busy elsewhere is refused with the pool unchanged. It is
     refused under LOOP_ROLE=worker, for a running goal, for a goal with no session (naming watch.py resume), and after
     the done lines changed (exit 1, run record unchanged).
   - g4 157: touches --add writes only the sidecar (the run record and the worktree's git status are unchanged), logs
     the line, survives a worker save of the main record, and shows in board.py's collected touches. A later record rewrites the goal file's Touches line,
     and the freeze check still passes. It is refused under worker and for an absolute or `..` path. A finding on a done goal leaves it done with findings[0]. A finding on a running goal
     still stops it. The board's note shows the finished goal's finding.
   - g7 (extra guards): answer on a stopped goal is refused (ANSWER_STATUS). record and pr on a waiting goal are refused
     with no try (WAITING_OWNER), and after answer the record goes through. A malformed full_markers config sets waiting.
     A worker self-bind on a stopped goal attaches without reviving. A watch-frozen goal has rules_at for idea. Two
     concurrent reservations (two processes, the pool lock held by one) can't both take a free session.
     sessions.call's LAST_ERROR for a nonzero exit, a missing executable and a timeout.
   - g5 121: with no LOOP_ROLE, record on a bound goal names the session and prints `LOOP_ROLE=worker`. On an unbound
     goal it names batch.py start and sessions.py bind. bind prints the WORKER line.
   - g6 160: bind prints `WORKTREE <path>`. `--cwd` outside it is refused and the pool is unchanged. `--cwd` inside
     passes. No `--cwd` from the main checkout prints the hint only. assign's sent text names the worktree.
9. Existing rows whose behavior changes: the review-depth rows (depth-condensed-refused, depth-markers and the
   no-DEPTH checks in dev/toy/test-review-depth.sh, plus its malformed-full_markers check, which now expects waiting,
   tries unchanged, a refused record until answered, then recovery) now expect `REFUSED (no try used)` and tries unchanged instead of
   `TRY ... FAILED`, and their descriptions say so. The operate guard row (test-operate.sh) expects the new texts.
   Every changed existing suite (test-review-depth, test-operate, test-session-workers, test-goal) runs in build.
10. `.loop/regression.tsv`: one land row per check (g1-g6), each `--category defect --link` its issue, plus row
   `guards-all` (ALL PASS). Each row is seen red with `regression.py red --break` against the old code: the base
   branch's goal.py, role.py and sessions.py checked out into a temp copy. For 160 the row links the issue and the
   commit says "Refs #160" (it stays open).
11. The goal file gains a `## Closes` section: `Closes #147`, `Closes #148`, `Closes #149`, `Closes #157`,
    `Closes #121` (one per line) and `Refs #160`. The PR body carries the goal file, so GitHub closes them on merge,
    and defect.py owes a defect row for each.
12. Docs:
    - Delivery wiki Usage gains resume and touches as agent requests.
    - DEL-1's Given/When/Then lines are re-rendered by `criteria.py render` from the rows' descriptions.
    - workflow-delivery SKILL.md (under 150 lines) names resume, touches, and finding on a finished goal.
    - workflow-monitoring SKILL.md and references name bind's WORKER and WORKTREE lines and `--cwd`.
    - The PR body states line 6's reading and that #160 stays open.

### Known limits, stated

- The guard is a role convention: LOOP_ROLE can be set by anyone. The refusal names the form only to the bound
  session's goal.
- The folder check fires only when the folder is known (bind `--cwd`, or a worker binding itself). assign prints the
  hint only. The app's own edit guard is untouched (#160 stays open).
- Goals already running when this lands have no `rules_at`: every rule known today applies to them (status quo).
- A step's start boundary is flow.py's `begin` when the step goes through flow.py. For a direct `record --in-session`,
  it's the previous step's record. A rule landing between that record and the real start of the work still doesn't
  bind the step. This errs toward not stopping goals.
- The guarantee covers new rule ids. Owner config that an existing rule reads (full_markers strings, review_depth on
  the base branch) applies at once, as it does today. That is the owner's own setting.

## Review record

### How this review ran

`/autoplan` was invoked and its guard refused its first phase read with `init_mismatch` (artifacts didn't match the
invocation). Its stated fallback ran instead: `/plan-ceo-review`, then `/plan-devex-review`, then `/plan-eng-review`,
by hand and in that order, each at full depth with auto-decided recommended answers (unattended worker). Owner
decisions wait at the final gate below.

### CEO phase (HOLD SCOPE)

Mode: HOLD SCOPE, auto-decided (recommended): the plan fixes six filed defects and changes about 12 files (under 15),
so it is fix/refactor work, not a new capability. Approved decisions: none beyond the frozen done lines and the owner's
"a" for line 6.

**System audit.** Branch loop/loop-guards from origin/main v0.18.0, clean. No stashes of ours. goal.py's last change
on main came from the review-depth goal; nothing on main since 2026-11-09 adds resume, touches, rules_at or a no-try
refusal (already-done check below). TODOS.md: none in this repo (the loop keeps findings in .loop/findings.md).
Retrospective: review-depth (v0.12.1) introduced the DEPTH rule that caused 147/148; reply-hook and narrow-rows
touched neither goal.py nor role.py's record path.

**0A Premise.** The real problem is false stops: a stop should mean the work failed. Do nothing and every format rule
added later repeats yc-ready's stop, every in-session repair stays hand-edited JSON, and finished goals keep getting
marked stopped (this worker nearly did it to narrow-rows on 2026-11-10). The plan hits the pain directly: each guard is
on the exact code path the issue names.

**0B Existing code leverage.**

| Sub-problem | Reused code |
|---|---|
| rule checks | role.record_depth, role.markers, role.depth_of (moved or called) |
| no-try refusal | goal.save/role.report (the board sees every state change) |
| resume | mend.resume's reset fields (status, tries, finding, waiting), minus the relaunch |
| touches | goal.cmd_new's goal-file template and commit |
| finding | goal.write_finding stays for live goals; finished ones get a note |
| guard text | role.guard, sys.argv |
| bind | sessions.cmd_bind, sessions.tool/call (send), assign's SEND text |
| toy tests | dev/toy/make.sh, fakegh, the test-review-depth.sh pattern for records |

Premise table:

| premise | claim | receipt | verdict |
|---|---|---|---|
| P1 | goal.py is near the 20 KB limit | `wc -c` = 18,955 | verified |
| P2 | DEPTH slips cost a try | goal.py:301-304 (`failed_try` on `bad`) | verified |
| P3 | record removes `ran` before checks | goal.py:298 (`os.remove(ran)`) | verified |
| P4 | finding always stops | goal.py:436-438 (`fail_stop`) | verified |
| P5 | guard points at batch.py | role.py:16 (REFUSE) | verified |
| P6 | bind resets status but not tries | sessions.py:225-226 | verified |
| P7 | assign's message already names the worktree | sessions.py:168 (SEND with tree) | verified |
| P8 | flow.py begin runs for headless and in-session first ask | flow.py:166, 188 | verified |
| P9 | defect rows are owed for "fixes/closes #N" in the goal file | defect.py:21-23, 39-46 | verified |
| P10 | the edit hook is not in this repo | grep of skills/, dev/, .claude, ~/.claude/settings.json hooks: no match | verified |

unverified=0.

**0C Dream state.**
```
  CURRENT                         THIS PLAN                            12-MONTH IDEAL
  stops mix real failures   --->  format slips, rule changes,   --->   every stop is a failed run; repairs
  and bookkeeping; repair         finished findings, restarts          are commands with audit lines; the
  is hand-edited JSON             no longer stop; resume/touches       board's Stopped column is trusted
                                  are commands with log lines
```
It moves straight toward the ideal; the gap left is the app-side edit guard (#160, outside the template).

0D: no new approach decision was needed (Approach B from the design stands).

**0G HOLD SCOPE checks.**
1. Complexity: about 12 files and one new module (guards.py). That is over 8 files, but most are a few lines each
   (docs, a row file, a test script). The new module is required by the 20 KB rule, not by design taste. Fewer moving
   parts isn't possible without breaking the size limit.
2. Minimum change: every item maps to a done line. Deferrable without blocking: none. The SKILL.md and wiki lines are
   DEL-4 and doc obligations.
3. Invariants kept: done lines frozen (touches doesn't touch the hash), review_depth's guarantee (rules still apply to
   steps started after them), the worker guard still refuses everyone without LOOP_ROLE.

**0I Temporal interrogation.**
- Hour 1: role.record_depth's callers (goal.py only) and the regexes flow.py imports from role (DEPTH, STEP) must keep
  working, so role re-exports them.
- Hours 2-3: where `ran` is removed, and what "next step" means after plan (build has no record; next recorded step is
  review).
- Hours 4-5: the guard needs the slug before argparse runs for flow.py (flow.py calls guard after parsing: fine) and
  role.py lane (slug is argv[2]).
- Hour 6+: the toy test needs a fake session tool and an old-code copy for the red proofs.
Effort: human team about 2 days; CC about 2-3 hours.

**REALITY rows.**
REALITY: premise-table pass 10 claims, unverified=0 skills/workflow-delivery/scripts/goal.py:298
REALITY: already-done pass no commit on origin/main since 2026-11-09 adds resume, touches, rules_at or refuse_no_try skills/workflow-delivery/scripts/goal.py:446
REALITY: surface-check finding `goal.py resume` and `goal.py touches` don't exist yet (new commands); `watch.py resume`, `sessions.py bind --name`, `role.py lane` verified against --help skills/workflow-monitoring/scripts/watch.py:455
REALITY: binding-decisions pass none on this branch; the owner's "a" (line 6) is binding and carried skills/workflow-monitoring/scripts/sessions.py:213
REALITY: numbers pass sizes measured: goal.py 18,955, role.py 17,711, sessions.py 14,309, flow.py 14,682 [measured: wc -c] skills/workflow-delivery/scripts/goal.py:1
REALITY: deferred-asks pass 148's "or has its own small budget": the 5-in-a-row note is the budget's signal, not a stop (reason: a stop for format would recreate 148); 160's "subagents can't get around it": app-side, out of reach (owner's a) skills/workflow-delivery/scripts/goal.py:303
REALITY: pr-count pass one PR (no ship-policy file; default one per wave) .loop/config.json:1

### CEO review sections

**Section 1 Architecture.** Current scope: HOLD SCOPE, auto-decided; no scope rows beyond the done lines; line 6 per
the owner's "a".

```
  goal.py ──imports──> guards.py ──imports──> role.py (depth_of, report)
     │                    ^
     │                    └──lazy import── role.begin (flow.py's step start)
     └─imports─> role.py (guard, inbox, lane, session_reply)
  flow.py ──imports──> role.py (DEPTH/STEP re-exported from guards)
  sessions.py (bind/assign) ── tool(cfg)/call ──> session tool (send WORKER + WORKTREE)
```
Run record state additions: `rules_at{step:[ids]}`, `refusals:int`, `findings:[{at,text}]`, note text.

Record flow (148/147):
```
  reply ──> held(frozen?) ──> qa? need_lane ──> in-session? session_reply ──> reply path + ran?
     │ no ran: refuse_no_try (counter+1)                       │
     └──> STEP line? ─no─> in-session: refuse_no_try | headless: failed_try
               │yes
               └──> check_depth(applies per rules_at) ─refusal─> refuse_no_try (ran kept)
                        │ ok (skipped rules logged)
                        └──> remove ran, record, clear_refusals, stamp(next)
```
Nil path: no `rules_at` means every rule applies (status quo). Empty path: empty `rules_at[step]` (a list with no ids)
means no rule applies, which is right for a step started before any rule existed. Error path: save fails (disk), so the
OSError propagates as today.

State machine (goal status) gains two edges: stopped/failed → running via resume (operation only), and done/merged →
same status on finding. Invalid: resume of running/waiting/done (refused); finding never moves done → stopped.

Security architecture: no new endpoints. New mutations: resume and touches (operation-only by the LOOP_ROLE
convention), the bind cwd check (read-only). Rollback: revert the PR. Run records gain fields old code ignores
(json.load keeps unknown keys), so rollback is instant. Value test: no process artifact is added; every output is a
refusal message, log line or board note that a person or the operation acts on.

Finding A1 (WARNING): role.py imports guards for DEPTH/STEP, and guards imports role for depth_of. Fix: guards imports
role at module level; role imports guards lazily inside begin, and re-exports DEPTH/STEP by a lazy attribute? Simpler:
keep DEPTH/STEP and depth_of/markers in role.py (they are small), and move only record_depth's body into guards. That
avoids the cycle and moves enough bytes. Auto-decided (P5 explicit, P3 pragmatic): keep regexes, depth_of and markers in
role.py; guards.check_depth calls them. Plan item 1 amended.

**Section 2 Error & Rescue Map.**
```
  CODEPATH                  | WHAT CAN GO WRONG                      | CLASS
  record → check_depth      | reply lacks DEPTH/markers              | format refusal
  record → reply lookup     | ran marker missing / path differs      | format refusal
  resume                    | wrong status / no session / sha moved  | usage refusal
  resume → send             | tool missing, times out, fails         | OSError/timeout (call returns None)
  touches → commit          | index lock, hook, dirty file           | git CalledProcess (returncode)
  guard                     | argv contains secrets? (no: goal cmds) | n/a
  bind --cwd                | DIR missing                            | realpath of missing path
  CLASS              | RESCUED | ACTION                                   | USER SEES
  format refusal     | Y       | exit 2, counter, note at 5               | REFUSED (no try used) + NEXT
  usage refusal      | Y       | exit 1/2, nothing written                | REFUSED + Fix
  send failure       | Y       | NOTE line, resume still applied          | NOTE: send failed; tell the session
  commit failure     | Y       | checkout the goal file, exit 1           | REFUSED with git's message
  missing --cwd DIR  | Y       | treat as outside (realpath not under wt) | REFUSED with the hint
```
No catch-alls: call() already catches OSError/SubprocessError narrowly. No GAP.

**Section 3 Security.** Threats: (1) a worker resuming its own goal to reset its budget. Likelihood low, impact
medium; mitigated by the LOOP_ROLE refusal (a convention, stated). (2) touches PATH traversal (`../`, absolute):
mitigated by validation. (3) guard echoing argv: goal commands carry slugs and file paths only, no secrets. (4) a
session-tool send injecting text: the text is ours (slug, step, worktree path). No new dependency, secret or PII.
Audit trail: resume and touches log who and why in the run record's log.

**Section 4 Data flow & edge cases.**
```
  record:  reply ─> validate(STEP, DEPTH per rules_at) ─> state(flow, rules_at, refusals) ─> run record ─> board
           shadows: empty reply (no STEP → refusal/try), huge reply (read as today), stale reply (session_reply copies
           fresh), concurrent save (atomic replace, last writer wins)
  resume:  argv ─> validate(status, session, sha, role) ─> state reset ─> run record + send
  touches: argv ─> validate(path, role, lock, dirty) ─> goal file ─> commit ─> state
```
Concurrency: the operation's resume/touches and the worker's record both write the run record. Each save rereads
nothing: load → mutate → atomic replace, so a write in between is lost. Resume only acts on stopped/failed goals (the
worker isn't recording then). touches can overlap a live worker. Finding A2 (WARNING): touches should reload the run
record right before its save (load → append → save in one short window) to shrink the race; the goal-file commit is
already path-limited. Auto-decided (P1): reload before save. Plan item 4 amended.
Edge cases: touches with a PATH already present (refused), resume twice (second refused: running), finding on a
merged goal whose worktree is gone (state-only, no git), bind --cwd with a trailing slash (realpath normalizes).

**Section 5 Code quality.** Fits existing patterns (goal.py commands are thin; helpers in sibling modules, as
defect.py and role.py already are). Duplication: resume's reset fields duplicate mend.resume's four lines; acceptable
(different launch semantics). Naming: `refuse_no_try` says what it does. Complexity: cmd_record gains branches; keep
it under 5 by moving the format checks into one guards call. No over-engineering: the rule registry has three entries
and one consumer.

**Section 6 Test review.**
```
  NEW CODEPATH                       | TEST (dev/toy/test-guards.sh)        | HAPPY | FAILURE | EDGE
  rules_at gating                    | g1                                   | yes   | refusal names v0.12.1 | no rules_at = applies
  refuse_no_try + counter/note       | g2                                   | yes   | 5th sets note | headless no-STEP still a try
  resume                             | g3                                   | yes   | worker/running/no session/sha | send failure NOTE
  touches                            | g4                                   | yes   | worker/lock/dirty | staged other file untouched
  finding on done                    | g4                                   | yes   | running still stops | merged without worktree
  guard text                         | g5                                   | yes   | unbound goal text | —
  bind WORKER/WORKTREE/--cwd         | g6                                   | yes   | outside refused, pool unchanged | inside passes
```
Assertions (no_claim): g1 protects that a rule added after a step started can't fail it (no_claim=the real
review-depth upgrade path; simulated by editing rules_at). g3 no_claim=a real app session receiving the send (a fake
tool logs it). g6 no_claim=the app's own edit guard (owner's a). Missing assertion found: the "(no try used)" text on
need_lane's refusal (done line 2's "wrong HEAD"). Auto-decided (P1, in blast radius): add the text and a g2 check.
Plan items 2 and 8 amended. Flakiness: none (no time/network; fake tools).

**Section 7 Performance.** No hot paths: each command runs once per step. The guard reads one run record. No issues
found: every new path is O(1) file reads on a small JSON.

**Section 8 Observability.** Every repair leaves a log line in the run record (resumed by, touches +, refused (no try
used), rule not applied, finding (goal stays)). The board reads `note`, so the 5-in-a-row signal shows under Issues.
No dashboards needed beyond the existing board. Runbook: a goal with the refusal note means the worker can't satisfy
the format; the operation reads the note's last reason.

**Section 9 Deployment.** No migration; new fields are optional. Old and new code side by side: a worker still on old
code (worktree not yet merged with main) keeps today's behavior. That is safe. Rollback: revert. Post-merge check: run
`goal.py show` on a live goal and see no errors.

**Section 10 Long-term.** Debt: a third module in workflow-delivery; documented in SKILL.md. Reversibility 5/5.
In 12 months, adding a new format rule means adding one RULES entry and one check, and running goals are unaffected.
That is the intended path.

Section 11: SKIPPED (no UI scope).

<!-- autoplan-accepted:ceo -->
- guards.py holds RULES, check_depth (record_depth's body), refuse_no_try, clear_refusals, stamp/applies and the bodies
  of resume, touches (widen) and finding-on-finished; DEPTH/STEP regexes, depth_of and markers stay in role.py (no
  import cycle).
- need_lane's refusal says "(no try used)"; test-guards.sh g2 checks it.
- touches reloads the run record immediately before its save.
- The goal file gains a "Closes" section: one "Closes #N" line each for 147, 148, 149, 157 and 121, and "Refs #160"
  (stays open). defect.py then owes a defect row for each closed issue.
<!-- /autoplan-accepted:ceo -->

### CEO phase, outside voice

Codex (gpt-6-astra, read-only, plan-review role) completed: 7 findings (5 High, 2 Medium), verdict findings.

| # | Codex finding | Disposition |
|---|---|---|
| C1 | Line 6 as frozen is unmet by hints | Kept: the owner chose (a) on 2026-11-10, relayed by the operation, and said #160 stays open. Recorded at the gate as a cross-model disagreement with the owner's direction, not reopened. |
| C2 | resume can address a session now serving another goal | Accepted: resume checks the pool, reserves a free session and refuses one busy elsewhere (item 3). |
| C3 | bind already revives, so bind-then-resume can't work | Accepted in part: the no-session refusal now says bind revives it; bind also resets tries/refusals and logs it (item 7). bind keeps reviving (issue 98's test requires it). |
| C4 | touches' lock check gives no exclusion; the checkout can erase worker edits | Accepted: touches writes only the run record; the worker syncs the goal file's Touches line in its own process (item 4). |
| C5 | test-review-depth.sh and test-operate.sh assert the old behavior | Accepted: those rows change with the behavior (item 9). |
| C6 | rule snapshot boundary differs between flow.py and direct record | Accepted as a stated limit (Known limits): it errs toward not stopping. |
| C7 | markers/config aren't frozen by rule ids | Accepted as a stated limit: owner config applies at once (Known limits). |

CEO dual voices: native review (above) found A1 (import cycle), A2 (touches race) and one missing assertion. Codex
independently found C4 (the same race, deeper), plus C2, C3 and C5, which the native pass missed. Consensus: 2 of 7
confirmed by both (the touches race, and the rule-boundary limit as an edge). 4 were Codex-only and accepted. 1 is a
disagreement with the owner's decision (C1), carried to the gate.

<!-- autoplan-accepted:ceo -->
- resume checks the session pool first: it reserves a free session and refuses one busy with another goal; nothing is
  written on a refusal.
- touches writes only the run record (reload before save); guards.sync_touches, called by record and pr in the worker,
  rewrites the goal file's Touches line, and pr commits it path-limited.
- bind keeps reviving failed/stopped goals and now resets tries and refusals with a log line.
- The review-depth and operate rows that assert the old try/guard behavior are updated with it; test-review-depth,
  test-operate, test-session-workers and test-goal run in build.
- Known limits stated: rule start boundary for direct in-session records; owner config applies at once.
<!-- /autoplan-accepted:ceo -->

### Decision Audit Trail

| # | Phase | Decision | Classification | Principle | Rationale | Rejected |
|---|-------|----------|----------------|-----------|-----------|----------|
| 1 | CEO | Mode HOLD SCOPE | Mechanical | P3 | fix work, about 12 files | SELECTIVE EXPANSION |
| 2 | CEO | Keep regexes/depth_of/markers in role.py | Mechanical | P5 | avoids an import cycle | move all to guards |
| 3 | CEO | need_lane says "(no try used)" + g2 check | Mechanical | P1 | done line 2's wrong-HEAD case | leave text as is |
| 4 | CEO | Closes section in the goal file | Mechanical | P1 | done line 7 and defect.py | Closes only in PR text |
| 5 | CEO | resume checks/reserves the pool | Mechanical | P1 | Codex C2, real bug | trust the run record |
| 6 | CEO | touches state-only + worker-side sync | Taste | P5 | removes the race entirely | lock + commit in the worktree |
| 7 | CEO | bind resets tries on revival | Taste | P3 | one consistent revived state | change bind to not revive (breaks issue 98) |
| 8 | CEO | update old try/guard rows | Mechanical | P1 | behavior change must update its tests | leave them failing |
| 9 | CEO | C1 kept per the owner's "a" | User decision | — | owner already decided | reopen line 6 |
| 10 | DX | Mode DX POLISH, persona agent | Mechanical | P3 | enhancement to an existing tool | EXPANSION |
| 11 | DX | Target Champion (one command per recovery) | Mechanical | P1 | plan already reaches it | current trajectory |
| 12 | DX | Stable refusal codes | Mechanical | P1 | agent-ready error contract; repo already uses LANE_MISSING | prose only |
| 13 | DX | Send NOTE carries tool stderr | Mechanical | P1 | CAP6 trace gap | bare NOTE |
| 14 | DX | save() unions touches/findings | Mechanical | P1 | Codex X1, real lost update | per-field locks |
| 15 | DX | one revive() for resume and bind | Taste | P4 | DRY, same end state | separate resets |
| 16 | DX | malformed config waits for owner | Taste | P1 | not a worker slip; avoids a free loop | refuse_no_try forever |
| 17 | DX | session detection by run record | Mechanical | P1 | flow.py omits --in-session | flag only |
| 18 | Eng | original arrangement (structure gate) | Mechanical | P3 | no smaller one keeps files under 20 KB | split goal.py further |
| 19 | Eng | sessions.py keeps its own revival + parity check | Taste | P5 | no cross-skill import | import guards.py |
| 20 | Eng | check_record + code constants | Mechanical | P5 | cmd_record branches ≤5 | inline checks |
| 21 | Eng | sidecar for operation data | Taste | P1 | Codex Y1: only race-free option without touching every writer | flock every writer |
| 22 | Eng | pool flock | Mechanical | P1 | Codex Y2 | none |
| 23 | Eng | answer only from waiting; waiting gate | Mechanical | P1 | Codex Y3/Y4 | leave answer |
| 24 | Eng | freeze stamps via guards.py known | Mechanical | P5 | Codex Y5 without cross-skill import | import |

### DX phase (DX POLISH)

Product type: CLI tool whose primary users are agents (auto-confirmed: the readers are the worker session running
`goal.py record`, and the operation session running `resume`, `touches` and `bind`). Mode: DX POLISH (auto-decided,
recommended: an enhancement to an existing tool).

**Persona.**
```
TARGET DEVELOPER PERSONA
Who:       an AI coding agent running a goal in a worker session (and its peer, the operation session)
Context:   mid-goal, unattended; it hits a refusal and must act on the text alone
Tolerance: one retry per refusal; it re-reads nothing outside the message
Expects:   the exact next command, whether its work was lost, and whether a try was spent
```

**Empathy narrative (today, from the code).** I finish a full review and write my reply, but I forget the DEPTH line.
`goal.py record` prints `TRY 2 OF 3 FAILED: review failed: no DEPTH line. Fix: ...` (goal.py:303). I lost a try for a
typo, and the `.ran` marker is gone (goal.py:298), so I have to rerun flow.py to re-arm the step. When I recorded the
previous step I hadn't heard of DEPTH at all. The rule arrived when my worktree merged main. Later the operation tells
me to record a finding after merge, and `goal.py finding` marks my merged goal stopped (goal.py:436). When my goal is
stopped, there is no command to bring it back. The operation edits JSON by hand. Without LOOP_ROLE, I'm told to run
`batch.py start NAME` (role.py:16), an operation command that isn't mine.

**Benchmark (start: a goal blocked by a bookkeeping refusal; result: running again with the fix known).**

| Tool | Start → result | Time + evidence | DX choice | Source |
|---|---|---|---|---|
| today | slip → rerun step → record | 1 try plus a rerun [observed: yc-ready, 2026-11-09] | refusal = failure | goal.py:301 |
| today, stopped goal | stop → hand-edited JSON | about 10 min [reported: issue 149] | no command | issue 149 |
| this plan | slip → fix reply → record | one record, no try [estimated] | refusal ≠ failure | plan item 2 |
| this plan, stopped goal | stop → `goal.py resume` | one command [estimated] | audit-logged reset | plan item 3 |

Target: Champion (under 2 minutes, one command per recovery), auto-decided (recommended). The plan already reaches it.

**Magical moment.** The first slip after this lands prints `REFUSED (no try used): ... NEXT: <exact fix>`. The agent
fixes one line and records again, and nothing was lost. Vehicle: the refusal text itself (existing capability).

**Journey map.**
```
STAGE        | AGENT DOES                         | FRICTION                               | STATUS
Discover     | reads SKILL.md / refusal text       | resume/touches unknown today           | fixed (SKILL.md + refs)
Install      | none (package scripts)              | none                                   | ok
Hello World  | records a step                      | slip costs a try                       | fixed (item 2)
Real usage   | records every step                  | rule added mid-goal fails it           | fixed (item 1)
Debug        | reads the refusal                   | no code; wrong fix for LOOP_ROLE        | fixed (codes; item 6)
Upgrade      | worktree merges main mid-goal        | new rule binds running steps           | fixed (rules_at)
```

**Confusion report (first time, an agent after this lands).**
```
T+0:00 records review without DEPTH → REFUSED (no try used): review refused: no DEPTH line (rule depth-line, added in v0.12.1). Fix: ... (FORMAT_RULE depth-line)
T+0:20 adds the line, records again → RECORDED review done in session (depth full)
T+5:00 operation runs goal.py resume on a stopped goal → RESUMED x at qa; the session gets "Continue at qa in <worktree>"
T+6:00 an agent without LOOP_ROLE runs record → REFUSED ... run it in worker · x as: LOOP_ROLE=worker python3 ... (NOT_WORKER)
```
No confusion left that the plan doesn't answer. One gap was found: refusals had no stable code (added, see below).

**Pass 1 Getting started: 8/10.** The tool is already installed with the package. The first contact is a refusal that
names its fix. Gap to 10: SKILL.md must name resume/touches in its first screen (item 12). Accepted as routine.
**Pass 2 CLI design: 8/10.** `resume SLUG --why`, `touches SLUG --add PATH --why` follow goal.py's `verb SLUG` grammar.
`--why` is required (an audit reason), and `--by` defaults to "operation session". Gap: `touches --add` takes one path,
which is enough (repeat the command).
**Pass 3 Error messages: 7/10 → 8/10 after the codes.**
```
ERROR PATH MATRIX (agent-ready-v1)
Path                         | Class      | what | fix  | recovery          | code | context | trace | redaction | channel   | Cap
record: missing DEPTH        | validation | pass | pass | fix and retry     | pass*| pass    | N/A   | pass      | exit 2    | —
resume: busy session         | usage      | pass | pass | do X first (bind) | pass*| pass    | N/A   | pass      | exit 1    | —
touches: bad path            | usage      | pass | pass | fix and retry     | pass*| N/A     | N/A   | pass      | exit 1    | —
send failure (unexpected)    | dependency | pass | pass | tell the session  | N/A  | pass    | gap   | pass      | NOTE, exit 0 | CAP6:send:trace
```
`*` with the codes added. CAP6 on the send path: the NOTE should carry the tool's error text (call() returns None today
and swallows it). Auto-decided: the NOTE includes the first line of the tool's stderr when available. Recovery side
effects: refuse_no_try writes only the counter/note (partial, stated in the message: "no try used").
**Pass 4 Docs: 7/10.** workflow-delivery references gain a "Repairs" section: resume, touches, finding on a finished
goal, the refusal codes. The Delivery wiki Usage lines gain the agent requests (item 12).
**Pass 5 Upgrade: 8/10.** Old run records work unchanged (no rules_at → status quo). Behavior changes (no try for
format) are in the changelog via the release step.
**Pass 6 Environment: 8/10.** Non-interactive everywhere. Toy tests run offline with fake tools.
**Pass 7 Community: N/A beyond the template's issues.** The issues close by number in the PR.
**Pass 8 Measurement: 6/10.** The run record's log lines (refused, resumed, touches) are the measure. The health
check could count refusal notes later (not in scope; HOLD).

Claude Code skill checklist: SKILL.md stays under 150 lines; new commands appear in references with examples;
refusals give the next command.

## DX Review Scorecard

```
| Dimension            | Score  | Prior  |
| Getting Started      | 8/10   | 5/10   |
| API/CLI              | 8/10   | 6/10   |
| Error Messages       | 8/10   | 4/10   |
| Documentation        | 7/10   | 5/10   |
| Upgrade Path         | 8/10   | 4/10   |
| Dev Environment      | 8/10   | 8/10   |
| Community            | N/A    | N/A    |
| DX Measurement       | 6/10   | 5/10   |
| TTHW (recover)       | 1 cmd  | ~10 min|
| Competitive Rank     | Champion (one command per recovery) |
| Magical Moment       | designed via the refusal text       |
| Mode                 | POLISH |
| Overall DX           | 8/10   | 5/10   |
```
DX principle coverage: zero friction, fight uncertainty, agents are users, escape hatches (LANES-style codes; --by)
covered. Learn by doing: the toy test doubles as the example.

DX Implementation Checklist: every refusal ends with its code and a NEXT/Fix line; resume and touches appear in
SKILL.md and references with one example each; the send NOTE carries the tool's error.

<!-- autoplan-accepted:dx -->
- Every new refusal ends with a stable code in parentheses (FORMAT_RULE <id>, NO_STEP_LINE, NOT_RUN_BY_FLOW,
  NOT_WORKER, WORKER_SELF_REPAIR, RESUME_STATUS, RESUME_NO_SESSION, SESSION_TAKEN, DONE_LINES_CHANGED, TOUCHES_PATH,
  CWD_OUTSIDE), listed with fixes in workflow-delivery's references.
- A failed session-tool send prints a NOTE carrying the tool's first stderr line when available.
- workflow-delivery SKILL.md names resume, touches and finding-on-finished; references gain a "Repairs" section with
  one example each.
<!-- /autoplan-accepted:dx -->

### DX phase, outside voice

Codex (gpt-6-astra) completed: 8 findings (3 High, 5 Medium).

| # | Codex finding | Disposition |
|---|---|---|
| X1 | a worker's stale save can drop an operation's touches | Accepted: save() rereads and keeps the union of touches and findings (item 1) |
| X2 | resume, bind and answer revive differently | Accepted: one guards.revive for resume and bind; answer stays (waiting→running, a different edge) |
| X3 | resume reads the goal file from the caller's checkout | Accepted: it reads from state worktree, and all checks run before the pool reservation (item 3) |
| X4 | the "exact command" lacks interpreter, path and worktree; lane guard has no slug | Accepted (item 6) |
| X5 | free refusals loop on unrepairable config | Accepted: malformed full_markers waits for the owner (item 2) |
| X6 | resume's failed send has no retry contract | Accepted: "(message not delivered)" plus the resend command (item 3) |
| X7 | session replies come through record without --in-session | Accepted: no-STEP handling keys on the run record's worker (item 2) |
| X8 | g4 contradicts the state-only touches | Accepted: g4 rewritten (item 8) |

Consensus: the native DX pass found the missing codes and the send trace. Codex found 8 more, all accepted (they are
agent recovery paths, so they're in scope under DX POLISH). No disagreements.

<!-- autoplan-accepted:dx -->
- save() in goal.py and sessions.py rereads the record and keeps the union of touches and findings.
- guards.revive is the single revival for resume and bind (clears status, tries, refusals, finding, waiting, note,
  report; logs how, who, why).
- resume reads the goal file from state worktree; all checks precede the pool reservation; RESUME_NO_WORKTREE code.
- The guard's fix line gives LOOP_ROLE=worker, python3, the absolute script path, args and the worktree; role.py lane
  passes its slug.
- A malformed full_markers config sets the goal waiting for the owner (no try).
- resume's failed send prints "(message not delivered)", the resend command, the session id and the tool's error.
- No-STEP handling keys on the run record's worker == "session", with or without --in-session.
- g4 tests state-only touches, the union against a stale worker save, and the later goal-file sync.
<!-- /autoplan-accepted:dx -->

### Eng phase (FULL REVIEW)

**Scope Challenge.**
- What already solves each sub-problem: see the CEO table (record_depth, mend.resume's fields, cmd_bind, call/tool,
  write_finding, the toy harness). Nothing on main already does it (already-done row).
- Minimum change: each item maps to a done line or an accepted CEO/DX obligation. Nothing is deferrable without
  failing a done line.
- Complexity: about 13 changed files (guards.py new, goal.py, role.py, flow.py, sessions.py, test-guards.sh new,
  test-review-depth.sh, test-operate.sh, regression.tsv, Delivery.md, two SKILL.md files, workflow-delivery
  references) and one new module [estimated]. That trips the gate (8+ files). Structure question
  `plan-eng-review-structure`: original arrangement (guards.py + edits) or a smaller one. No smaller arrangement keeps
  goal.py and role.py under 20 KB while adding the code, and the extra files are tests and docs the done lines require.
  Auto-decided: original arrangement (recommended). Feature answers: none cut. Accepted scope: as planned. Pending
  remedies: none.
- Search check: no new infrastructure pattern. The union-on-save is a standard append-only merge [Layer 1]; atomic
  replace is already used. Search wasn't needed.
- Scope Challenge result: scope accepted as-is.

REALITY: premise-table pass 10 CEO claims re-checked plus 3 new (board reads note: board.py:187; flow.py session route omits --in-session: flow.py:201; sessions.held doesn't check freeze: sessions.py:198), unverified=0 skills/workflow-monitoring/scripts/board.py:187
REALITY: already-done pass git log origin/main since 2026-11-09 on goal.py/role.py/sessions.py: no hit for resume/touches/rules_at skills/workflow-delivery/scripts/goal.py:446
REALITY: surface-check pass existing commands checked against their usage text (goal.py -h, sessions.py -h, watch.py resume); the new ones are new skills/workflow-delivery/scripts/goal.py:4
REALITY: binding-decisions pass owner's "a" (line 6) honored; no branch decisions log entries skills/workflow-monitoring/scripts/sessions.py:213
REALITY: numbers pass byte sizes [measured: wc -c]; file count [estimated] skills/workflow-delivery/scripts/role.py:1
REALITY: deferred-asks pass 148's separate small budget (signalled by the note instead); 160's subagent bypass (app-side) skills/workflow-delivery/scripts/goal.py:188
REALITY: pr-count pass one PR .loop/config.json:1

**1. Architecture.**
```
                     ┌──────────────── guards.py (new) ────────────────┐
  goal.py ──────────>│ RULES/known/stamp/applies  check_depth           │──> role.py (DEPTH, STEP, depth_of, markers, report)
   record/new/pr     │ refuse_no_try/clear_refusals  revive             │
   resume/touches    │ resume  widen  note_finding  sync_touches        │
   finding           └──────────────────────────────────────────────────┘
  flow.py ──> role.begin ──lazy──> guards.stamp
  sessions.py bind ──> guards.revive (imported by path from workflow-delivery, as sessions.py already reaches role.py?)
```
Finding E1 (P2, confidence 8/10): sessions.py lives in workflow-monitoring. Importing guards.py across skill folders
couples the skills. Check: sessions.py already imports nothing from workflow-delivery (it reads run records directly).
Remedy: sessions.py keeps its own five-line revival, matching guards.revive field for field, and a toy check asserts
that bind and resume leave identical fields. Auto-decided (P5 explicit, no cross-skill import). That is a hand-synced
list (red flag 8), so the toy check is the derived guard.
Design-twice: shape A is guards.py as a flat helper module (chosen). Shape B is a `Goal` class owning the run record
with methods (record, resume, widen). B hides the load/mutate/save cycle better, but rewrites goal.py's whole command
layer: a bigger diff, against the 20 KB pressure. Pick A: the helpers own the policy (rules, refusal accounting,
revival), and goal.py owns argument wiring. Red flags: (5) split ownership of the run record (goal.py save and
sessions.py save both write it), mitigated by the union-on-save for the append-only fields; (8) hand-synced revival
fields, mitigated by E1's toy check. No others.
Production failure per new path: resume's send times out (30 s limit in call()): NOTE plus resend. touches during a
worker save: union. Rule list stale in an old worktree: the old code ignores rules_at (it doesn't know it), so it
behaves as today.

**2. Code quality.** cmd_record's branch count rises. Keep it at 5 or fewer by routing all format checks through one
`guards.check_record(state, step, text, cfg, result, session)` that returns (stamp, refusal, waiting). Finding E2 (P3):
the refusal codes are strings in several places, so they become constants in guards.py. Auto-decided. Error handling:
no bare excepts; the existing narrow (OSError, ValueError) pattern holds. No shared-code extraction beyond guards.py
(two verified callers: goal.py record and flow.py begin for stamp; goal.py and sessions.py for revive, kept separate per
E1).

**3. Test review.**
```
CODE PATHS                                          USER FLOWS (agent)
[+] guards.check_depth / applies                    [+] worker records a step
  ├── [GAP→g1] rule not in rules_at → skipped+log     ├── [GAP→g2] slip → REFUSED (no try used), fix, record
  ├── [GAP→g1] rule in rules_at → refusal names it    └── [GAP→g2] 5 slips → board note; good record clears
  └── [GAP→g1] no rules_at → applies (legacy)       [+] operation repairs a goal
[+] refuse_no_try / clear_refusals                    ├── [GAP→g3] resume stopped goal (send ok / send fails)
  ├── [GAP→g2] tries unchanged, ran kept              ├── [GAP→g3] resume refused: worker, running, no session,
  └── [GAP→g2] headless no-STEP still a try           │            session busy, worktree missing, done lines changed
[+] malformed full_markers → waiting                  ├── [GAP→g4] touches add → run record only; union; sync
  └── [GAP→g2]                                        └── [GAP→g4] finding on done/merged → stays; running → stops
[+] revive (goal) vs bind revival (sessions)        [+] session binding
  └── [GAP→g3] identical fields after each            ├── [GAP→g5] guard text bound/unbound; lane guard
[+] save() union of touches/findings                  └── [GAP→g6] WORKTREE; --cwd outside refused; inside ok;
  └── [GAP→g4]                                                     no --cwd hint only; assign text
[★★ TESTED] test-review-depth.sh (changes: no-try expectations)   [★★ TESTED] test-operate.sh guard text (changes)
COVERAGE after the plan: all new paths have a planned check (g1-g6); 0 gaps left unplanned.
```
REGRESSION RULE: existing behavior at risk: (a) review_depth enforcement for new steps (test-review-depth keeps every
check, changing only try-vs-refusal expectations); (b) issue 98 bind revival (test-session-workers unchanged and run);
(c) headless no-STEP is still a try (g2). These are carried as CRITICAL regression requirements, auto-decided per the
approved behavior. Tests made obsolete: none. The TRY-FAILED expectations in test-review-depth are rewritten, not
retired.
Value cards (protects / fails_when / no_claim) go into each test-guards.sh check as `# Value:` comments, in the repo's
pattern.

**4. Performance.** All paths are single-file JSON reads and writes per command. union-on-save adds one read per save.
That is negligible (records are a few KB). No issues found.

<!-- autoplan-accepted:eng -->
- sessions.py keeps its own revival (no cross-skill import), and a toy check asserts that bind and resume leave identical
  run-record fields.
- cmd_record routes format checks through one guards.check_record(...) returning (stamp, refusal, waiting); refusal
  codes are constants in guards.py.
- Regression requirements: test-review-depth keeps every check (no-try expectations replace TRY FAILED);
  test-session-workers (issue 98) runs unchanged; a headless no-STEP reply still costs a try (g2).
- Each test-guards.sh check carries a `# Value:` comment (protects, fails_when, no_claim).
<!-- /autoplan-accepted:eng -->

### Eng phase, outside voice

Codex (gpt-6-astra) completed: 9 findings (5 High, 4 Medium).

| # | Codex finding | Disposition |
|---|---|---|
| Y1 | reread/union races, and other writers (begin, flow, watch, worker, mend) bypass it | Accepted: replaced by a sidecar (`<slug>.extra.json`, flock) that only operation commands write, so no main-record writer can erase it. This supersedes DX X1's union-on-save. |
| Y2 | pool reservation isn't exclusive against assign | Accepted: a pool flock around every read-modify-write, with undo on a failed goal save |
| Y3 | answer revives any status; worker self-bind revives | Accepted: answer only from waiting (ANSWER_STATUS); self-bind attaches without reviving |
| Y4 | waiting isn't enforced by record or pr | Accepted: record and pr refuse while waiting (WAITING_OWNER, no try) |
| Y5 | watch.freeze creates records without stamping | Accepted: freeze stamps idea through `guards.py known` (CLI, no cross-skill import) |
| Y6 | touches sync must precede the pr lane | Accepted: sync and commit right after the base merge, before bump and lane |
| Y7 | finished-goal findings invisible on the board | Accepted: board collect shows the newest sidecar finding in the note field |
| Y8 | call() discards stderr | Accepted: sessions.LAST_ERROR, same return contract, tests for three failure kinds |
| Y9 | test-review-depth's full_markers check changes too | Accepted: rewritten for waiting, tries, refusal, answer, recovery |

Cross-model: the native Eng pass found E1 (cross-skill import) and E2 (codes as constants). Codex found Y1-Y9, all in
blast radius. Y1 and Y2 are real data races that the native pass rated as mitigated, so the native pass was wrong.
Consensus 0 of 9 by both independently. Accepted: 9 of 9.

<!-- autoplan-accepted:eng -->
- Operation-added touches and finished-goal findings live in `<slug>.extra.json` under an flock, written only by
  operation commands; board collect, sync_touches and show merge it. This replaces the DX phase's union-on-save
  obligation (X1).
- The session pool is read-modified-written under a flock in assign, bind, resume and release; a failed goal save undoes
  a reservation.
- goal.py answer works only from waiting (ANSWER_STATUS); record and pr refuse while waiting (WAITING_OWNER, no try); a
  worker self-bind attaches without reviving.
- watch.py freeze stamps idea's rules_at via `guards.py known`.
- goal.py pr syncs and commits the goal file's Touches line after the base merge and before the bump and lane.
- board collect shows a finished goal's newest sidecar finding in its note.
- sessions.call records the tool's first stderr line in LAST_ERROR (nonzero exit, missing executable, timeout).
- test-review-depth's malformed-full_markers check is rewritten for waiting/answer/recovery; g7 covers the extra
  guards.
<!-- /autoplan-accepted:eng -->

### Final gate (Phase 4)

URGENT, outside this plan: None.
The review stopped at its final gate (gate_rev 1), which this worker step never approves. Decisions for the owner, each
with the default the build follows unless the owner says otherwise:
- d1 touches lives in a sidecar file that only operation commands write (default). Alternative: lock every writer of
  the run record, which touches seven scripts.
- d2 bind and resume leave identical revived state, and sessions.py keeps its own copy with a parity test (default).
  Alternative: sessions.py imports guards.py across skills.
- d3 a malformed full_markers config puts the goal in waiting for the owner, with no try (default). Alternative: it
  stays a free refusal.
- d4 five refused records in a row set a board note and the goal keeps running (default). Alternative: a separate small
  budget that stops it.
- d5 line 6 is met as the owner chose (a): bind/assign print the worktree, and bind refuses a known outside folder
  (`--cwd`, or a worker binding itself). With no folder known, assign and the operation's bind print only the hint.
  #160 stays open. Cross-model note: Codex (CEO phase) reads line 6 as unmet without the app-side change. The owner's
  word stands.
- p1 plan approval: approved 2026-11-10 by the owner in the operation session, relayed by it: "Approve it". d1-d5 take
  the defaults above.
How it ran: /autoplan's guard refused (init_mismatch), so its stated fallback ran: CEO (HOLD SCOPE), DX (POLISH) and Eng
(FULL) by hand, each with a native pass and a completed Codex outside voice (gpt-6-astra). Design was skipped (no UI
scope).

## REVIEW REPORT

| Review | Trigger | Why | Runs | Status | Findings |
|--------|---------|-----|------|--------|----------|
| CEO Review | `/plan-ceo-review` (autoplan fallback) | Scope & strategy | 1 | CLEAR (gate approved 2026-11-10) | HOLD SCOPE; 3 native findings + 7 Codex (6 accepted, 1 owner decision) |
| Outside Review | codex (gpt-6-astra), CEO/DX/Eng | Independent 2nd opinion | 3 | completed | 24 findings; 23 accepted, 1 carried to the gate (line 6) |
| Eng Review | `/plan-eng-review` (autoplan fallback) | Architecture & tests (required) | 1 | CLEAR (gate approved 2026-11-10) | 2 native + 9 Codex, all accepted; 0 critical gaps left |
| Design Review | `/plan-design-review` | UI/UX gaps | 0 | skipped (no UI scope) | — |
| DX Review | `/plan-devex-review` (autoplan fallback) | Developer experience gaps | 1 | CLEAR (gate approved 2026-11-10) | 5/10 → 8/10; recovery: one command; 8 Codex accepted |

- **OUTSIDE COVERAGE:** codex completed in CEO (7 findings), DX (8) and Eng (9); design phase skipped.
- **CROSS-MODEL:** CEO 2/7 confirmed by both (1 disagreement with the owner's line-6 choice); DX 0/8 overlap (all accepted); Eng 0/9 overlap (all accepted; Codex caught two races the native pass rated mitigated).
- **VERDICT:** gate answered 2026-11-10 (p1 approved, "Approve it"; d1-d5 as defaulted); eng review required and done.

**UNRESOLVED DECISIONS:**
- none: p1 (plan approval, gate_rev 1) approved 2026-11-10, "Approve it".
