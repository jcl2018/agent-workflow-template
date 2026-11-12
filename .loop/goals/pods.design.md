# Design: pods

Done lines (frozen) are in `.loop/goals/pods.md` (six of them; the task text said seven, the file has six, so rows key `pods:1..6`).
This goal replaces `pod-layers` and `single-operation`. Carried over from `pod-layers`: the claim that ADDS its id to
`operation.id` (MON-13) and the per-repo check-in blocks (MON-14); both are already built as a patch that applies cleanly here.
The single-operation claim refusal is DROPPED: nothing refuses a second independent operation session.

## Problem

Several pods (a Claude Code operation session, a Codex one) may share a machine and a repo and do not message each other.
Today nothing says whose goal is whose, so pod B can start, answer, resume or merge pod A's goal, and two pods can run
`merge.py` into one main at the same moment. All coordination has to live in shared on-disk state.

## Decisions

1. **Pod id** = `$LOOP_POD_ID`, else the operation session's own id (`$CLAUDE_SESSION_ID`, the same id `operate.py claim`
   writes into `operation.id`); empty in a worker and when neither is set. `operate.py run` exports it so watch, auto, merge
   and send inherit it. A caller with no pod id stamps nothing, so a repo that never sets one behaves exactly as today.
2. **Ownership** is `pod` in the run record, stamped once when the operation freezes the goal (`watch.freeze`,
   `goal.py new` outside a worker, `sessions.assign`). It is never rewritten, so a worker's later saves keep it and the
   `<slug>.extra.json` sidecar (owner settings, merged by `fit.view`) is not involved. No `pod` means no owner: anyone acts.
3. **Enforcement** is one shared check, `graph.refuse(state)`: exit 2, one stderr line
   `REFUSED: goal <slug> is owned by pod <id>. Fix: act from that pod (set LOOP_POD_ID=<id>), not from here.`, before any write,
   so no try is used and the record is byte-identical. Workers are never checked (they run under the owner's goal).
   Applied at: `watch.freeze` (stamp), `watch.py resume` and `mend` (skip/refuse), `operate.py send`, `auto.py` (skip), `sessions.held`
   (assign, send, report) and `session_bind.cmd_bind`, `goal.py resume`, `merge.py`.
4. **Marks**: `board_lines.box` appends ` owned by <pod>` to a goal another pod owns; the check-in and the live board set
   `owner`. A foreign waiting question is listed under Needs you as read-only, never as a question this pod answers.
5. **Merge lock**: `<git common dir>/loop/merge.lock`, created with `O_CREAT|O_EXCL` holding the pid, taken in `merge.py`
   after the ownership check and before the first `gh` call, released by `atexit`. A holder that is dead (`kill(pid,0)`)
   or whose file is older than `LOOP_MERGE_LOCK_SECONDS` (default 1800) is replaced by one atomic `rename`, so two
   waiters never both take it. A waiter prints one WAITING line and polls. Chosen over `fcntl.flock` because flock cannot
   expire a hung but live holder; O_EXCL plus the stale rule covers both dead and stuck.
6. **Size** (the hard constraint, measured on a prototype): all shared code goes into `graph.py` (14,022 to 17,367 bytes;
   already imported by every monitoring script). `goal.py` and `merge.py` (other skills) load it with
   `sys.path.append` plus `try: import graph as pods / except ImportError: pods = None`, so a skill installed alone
   works. `goal.py` grows to about 19,700 (cap 20,480), `merge.py` is held at or under its 19,985 by trimming its docstring.
   No new script file: the package stays at 99.

## Rejected

- A pod record file or heartbeat (needs sessions to know each other; the owner said they do not).
- `flock` for the merge lock (cannot expire a live, hung holder).
- Storing `pod` in the sidecar (immutable, so the record is the right home; the sidecar is for owner settings).
- Refusing a second operation session (owner: sessions are independent).
- A takeover command for a restarted session (see Risks; left to the owner).

## Risks

- A restarted Claude session gets a new id, so its old goals read as another pod's. Mitigation: `claim` prints the id and
  `LOOP_POD_ID=<id>` restores it; `claim` is a no-op on a re-run. A takeover command is a PENDING owner decision.
- A pod id the owner mistypes leaves goals refused until corrected; the refusal line names the owner to copy.
- The merge lock serializes one repo's merges only; a hung merge blocks others up to 30 minutes, then is replaced.
- `watch.py` still holds `repo/slug` goals as unknown (unchanged).
