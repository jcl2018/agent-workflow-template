# Fix issue 98: run every goal in its own app session named after it, talking by session messages, with the owner's new MON-1 and MON-2 wording approved in chat on 2026-11-08

- Slug: session-workers
- Touches: skills/workflow-monitoring, docs/wiki/Monitoring.md, dev/toy

## Done lines

Frozen. A wrong done line needs a new goal.

1. MON-1 and MON-2 are unreviewed and rewritten word for word as follows, then marked Reviewed 2026-11-08 with criteria.py review --user: MON-1 "Roles, start and planning. One command starts the operation session and drives the whole process the same way every time. The operation session plans queued goals as a dependency graph and gives every goal whose dependencies are met its own worker session in the app, renamed worker · <goal>, running in parallel; it never builds. A goal waits only on goals it truly depends on; sharing files is not a reason to wait. When a worker session finishes, the operation session gives it the next ready goal, renaming it again." MON-2 "Live communication. Operation and workers talk through session messages: a worker reports each change of step or status as it happens, and its result when it ends (merged, failed or waiting, with the pull request); the operation session sends a worker its answer or a follow-up. Background processes are used only when the app can't start or reach a session, and the board says so."
2. operate assigns each ready goal to a worker session (reusing a free one or asking the app for a new one), renames it worker · <goal>, sends it the goal, worktree and report instructions, and records the session on the run record; it falls back to a background process only when no session can be started or reached, and the board marks that goal as background
3. Worker sessions report each step change and their result by session message, operate records those reports on the run record, and the live board shows each running goal's worker session name
4. A worker session runs each flow step inside itself by default (invoking the mapped skill directly, keeping the unattended rules: recommended answers, no push from ship) and records it with goal.py record; flow.py starts a headless agent only when there is no worker session
5. A toy test with a stand-in session tool proves assignment, renaming, the report path, reuse of a finished session for the next goal, and the background fallback
6. A defect test linked to issue 98 proves a goal worked in a session shows on the board with its session name and current step, never as a failed background worker, and issue 98 closes when this merges

## Verify by hand

<!-- Numbered steps for a person, each with an Expect: line. A release needs this. -->
