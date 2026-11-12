# Design: pod-layers

Done lines (frozen) are in `.loop/goals/pod-layers.md`. This goal replaces `single-operation`, whose refusal of a second
operation session is DROPPED: the owner said several operation sessions (one in Claude Code, one in Codex) run at once and
need not know each other. Nothing refuses, warns or keeps a pod record.

## Problem

1. MON-13 (two layers): one operation session governs every repo in its pod directly; no per-repo operation session.
   The hooks already read `operation.id` as a SET of ids (`govern_hook.operation_ids`, `reply_hook.claimed`), but
   `operate.py claim` and `govern_hook.claim` OVERWRITE the file ("last claim wins", `(replaced X)`). A second, independent
   session therefore un-governs the first. The set was built for several ids; the writers contradict it.
2. MON-14 (check-in): Dependencies is one flat graph; repos are not distinct and cross-repo edges never draw.

## Decisions

- **Claim adds, never replaces.** `operate.py claim` and `govern_hook.claim` append the session id to `operation.id` when it
  is absent and keep every other id. No `replaced` note, no refusal, no warning. A worker is still refused (unchanged).
  A re-claim by the same id is a no-op. A claim writes its id into its own repo and every repo the pod follows
  (`board.followed()`), so one operation session governs each repo by hook; two pods following one repo both appear there.
- **No pod record file, no liveness, no `--replace`.** A stale id is harmless (it is only a session id that never speaks).
- **Per-repo Dependencies block** (reuse of the `single-operation` working `gather()` and `grouped()` in `checkin.py`):
  `== name ==` header, the `board_lines` graph without its legend, `- (none)` for an empty repo; own repo first, then the
  `~/.workflow-loop/repos` order. Dependencies written `repo/slug` are listed under `Between repos` as
  `a/x <- b/y [mark]` (or `(unknown)`); the legend prints once; every line is wrapped to 60 columns. A followed repo that
  cannot be read never stops the check-in: one Needs you line names it. All sessions and the counts cover the pod.
- `watch.py` still holds a `repo/slug` goal as unknown; that stays out of scope (safe: it never starts early).
- Code changes only in `operate.py`, `govern_hook.py`, `checkin.py`; no new skill file.

## Why this and not more

Two layers needs no new mechanism: the hook already treats `operation.id` as a set and a worker is already excluded.
The one defect is the overwrite. A pod record or refusal would add state and a failure mode the owner said he does not
want. The check-in change is cosmetic and reversible.

## Rejected

- Refuse or warn on a second operation session (owner: sessions are independent).
- A shared pod record (needs the sessions to know each other).
- Rewriting `repo/slug` dependencies before `graph.ready` (would show ready while `watch` holds).

## Risks

- `operation.id` grows with every claiming session and is never pruned; a handful of short ids, accepted.
- A long-running pod reading a slow followed repo is serial; the guard prevents a crash, not latency.
