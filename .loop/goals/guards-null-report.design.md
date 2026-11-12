# guards-null-report: design

Two follow-ups from PR #1092, both small.

1. Null report: the reset paths (`guards.revive`, `session_bind` bind, `mend` resume) wrote `report=None`. They now write `{}`.
   Readers already treat a missing or empty report alike (`or {}`, `isinstance(..., dict)`), so nothing else changes.
2. Locked goal state: `goal.py save` was read-modify-write with no lock, so two writers each saving an older copy lost one
   write. It now holds an `flock` on `<slug>.json.lock`, re-reads the file, replaces only the keys this process changed since it
   loaded (a per-slug JSON snapshot taken at load and save), and merges the log lists (the file's lines first, then this
   writer's new ones). The caller's `state` is updated to the merged record.

Rejected: locking the whole load-to-save span (a caller can hold a record for minutes; the merge avoids that); moving the
save into another module (no module has room: goal.py is 20,341 bytes after the change, under the 20,480 cap).
Limits: a key one writer deletes is not removed from the file; two writers changing the same key still end last-writer-wins;
watch.py's own save is not part of this goal.
Tests: `dev/toy/test-guards-null-report.sh` (reset, writers, nofiles); rows `guards-null-report-reset|writers|nofiles`.

## After the plan review
- Done line 2 is read as the goal.py save path (the follow-up in PR #1092 names the goal state file's writer). Other writers
  keep their own whole-file writes: role.begin, flow.py (tokens), lanekit.hit, watch.refresh, mend, worker, sessions. A shared
  locked helper for them does not fit: role.py, flow.py and lanekit.py have no room under the 20,480-byte cap. Listed as the follow-up.
- A key removed by a writer now stays removed (session_bind clears held_at). Tested.
- A key set back to the value this process loaded is not written; two loads of one slug in a process share one snapshot; a repeated
  identical log line is merged once. Accepted limits.
