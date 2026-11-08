# Design: operate

Status: shaped by office-hours with the recommended answer at every question. Nothing approved, merged or pushed.
The goal's done lines are frozen; this design meets them. Delivery fills in the done lines' met marks and Verify by hand.

## Problem

Monitoring is started by hand-run verbs (`batch.py`, `watch.py`, `board.py`) and holds a goal back whenever its
`touches` overlap a running goal (`watch.py` `blocker`/`overlap`). The owner wants one deterministic command, a
dependency-graph planner instead of file-overlap serialisation, workers that report as they go, and a guard so goal
steps never run in the operation session.

## Premises (taken as agreed)

1. Sharing files is not a reason to wait. Overlap becomes a merge-time concern (done line 3), not a start-time one.
2. `depends-on` in the queue is the only thing that holds a goal back, besides the `parallel` cap in `.loop/config.json`.
3. Existing pieces are reused: `worker.py` (report/met/loop), `board.py cadence`, `board_status.py` (status block, tokens), `board_map.py` (dependency map).
4. Scripts are near the 20 KB cap (`watch.py` 18.6, `goal.py` 17.9, `board.py` 16.9), so new logic goes into new small modules, not into those files.

## Approach (recommended, taken): graph planner in a new module, thin operate loop

1. **MON-1** (line 1): rewrite the MON-1 text in `docs/wiki/Monitoring.md` word for word as the goal says, then `criteria.py review --user` for MON-1 only, dated 2026-11-08. Do this first: Reviewed locks the wording by hash.
2. **Queue + planner** (line 2): `skills/workflow-monitoring/scripts/plan.py`. `parse_queue` accepts `depends-on: a, b`. `ready(queue, runs, limit)` returns goals whose dependencies are all `merged`, not started, up to `parallel` minus live workers. `watch.py` replaces `blocker` with this; overlap check is deleted. A dependency on an unknown or failed/retired goal leaves the goal waiting and shows in Needs you (never silently dropped). Cycles are refused at `add` with one line. `board_map.py` draws depends-on edges.
3. **Merge latest base** (line 3): in `worker.py`/`goal.py` before the PR step, a helper `sync_base` merges `origin/<base>`; clean merge → rerun checks, continue; conflict → counts one try (existing 3-try rule), agent fixes it. New module `sync.py` in workflow-delivery to keep `goal.py` under 20 KB.
4. **operate command** (line 4): `scripts/operate.py`, one entry that loops: `watch --once` → `board.py board` → print status block; sleep `board.py cadence` minutes (NEXT_DELAY), woken early by a worker report (poll the run-record mtimes at a short interval); prints one line when nothing changed. Deterministic: same steps, same order, no model in the loop.
5. **Refuse guard** (line 5): `goal.py` and `flow.py` check an env var the worker sets (`LOOP_WORKER=<slug>`); absent → one line `refused: run goal steps in a worker: python3 scripts/batch.py start NAME` and exit non-zero. `worker.py` exports it. Shared check in one tiny helper.
6. **Reporting + follow-ups** (line 6): worker appends a report to the run record on every step/status change (extends today's end-of-run message). Operation side: `operate.py send SLUG "text"` appends to an inbox file under the goal's loop dir; the worker reads and clears it between steps and shows it to the agent.
7. **Status block** (line 7): Next lists only queued and waiting goals; Roadmap counts merged goals per feature; the worker records tokens per step when the agent output reports them (extend the `TOKENS` regex handling in `worker.py` to key by step). Changes in `board_status.py`.
8. **Tests** (line 8): `dev/toy/test-operate.sh` with a stand-in agent (a script that sleeps, writes a file, prints "N tokens") proving each line 1-7; a size check that every script is < 20 KB.
9. **Docs**: README and `operation.md`/`commands.md`/SKILL.md describe `operate.py` as the one way; the manual `watch`/`batch` loop text is replaced.

## Alternatives considered

- **A. Minimal**: add `depends-on` to `watch.py` only. Fails lines 4-7 and busts the 20 KB cap.
- **B. Recommended** (above): new `plan.py`, `operate.py`, `sync.py`; small edits elsewhere.
- **C. Daemon**: long-running background supervisor. Rejected: harder to test, no benefit over a cadence loop the session already runs.

## Risks

- Parallel goals editing the same files will hit real conflicts; mitigated by line 3, and costs a try only on a true conflict.
- Early wake on worker report needs polling; keep it cheap (stat run records only).
- `watch.py` is 18.6 KB: removing `blocker`/`overlap` frees space, but check size after each edit.

## Order

MON-1 wording → plan.py + queue parse → watch.py swap → sync.py → guard → worker reports/inbox → operate.py → status block → toy test → docs/README. Run `docs.py check`, `criteria.py render --check`, regression suite and repo checks at the end.
