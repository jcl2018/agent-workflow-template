# Findings

Open findings, one line each.

- flow-qa-lane-unasked: `flow.py <slug> qa` starts the full land lane itself (role.py lane step) with no check that the operation session allowed a lane, so an in-session worker following "run flow.py" can exceed the at-most-two-lanes rule; seen in health-hygiene 2026-11-09, stopped by hand after about two minutes.

Retired (checked 2026-11-08 against each run record and `git log main`; a retired line does not start with a dash):
retired project-wiki: its run record is retired and the wiki work landed in PR #10 (project-wiki-3).
retired project-wiki-2: its run record is retired; superseded by project-wiki-3, merged as PR #10.
retired project-wiki-3: the work merged as PR #10; the judge failure it recorded did not recur.
retired operation-session: superseded by operation-session-2, merged as PR #6; its own PR #5 is also merged.
retired auto-release: the goal's PR #14 merged; its run record is done.
retired numbered-levels-2: the goal's PR #15 merged; its run record is done.
- reply-hook: reply-hook: a stale board with the right headings passes the hook; a digest token in the LIVE BOARD header, checked against board.json, would prove freshness (autoplan CEO F1)
- reply-hook: reply-hook: the live board or health should show when reply_hook is on but the hook is not installed, when it keeps failing open, and recent let-throughs (autoplan CEO F3/F4/F5, DX F2/F6); outside this goal's paths

Open (from board-held's ship review, 2026-11-10; non-blocking, for the health-report pass to file):
- sessions-size: skills/workflow-monitoring/scripts/sessions.py is 20443 bytes, 99% of the 20 KB rule; split it (e.g. the bind/free/report commands out of the pool code) before the next change to it.
- watch-start-lock: watch.py start_round checks taken() and freeze() makes its first save outside the session-pool lock, so an operator bind landing in between gives one goal two sessions; take sessions.locked() around the check and the first save.
- assign-unreadable-after-send: if the pool turns unreadable after assign's send succeeded, watch marks the run failed with worker background, and mend can relaunch a second worker beside the session; save the session on the run before reporting the pool problem.
- handed-leaves-queued: a HANDED assign (say an operator free during the send) leaves a freshly frozen run queued, which the live board shows nowhere and nothing starts; set it running with no worker so it shows as held.
- run-record-lock: run records are changed without the pool lock by sessions.py report, goal.py step/record, watch refresh and mend, so a concurrent write can undo a bind's session and bound_at; lock load and save in report at least.
- assign-new-sid-collision: assign writes a newly started session id into the pool without checking it is already busy for another goal, so a tool that repeats ids steals another goal's claim.
- report-attempt-identity: sessions.py report doesn't check which session sent it, so a stale or HANDED session's report can fail a goal and free its current session (deferred E7).
- assign-freed-reuse: assign can hand a goal back to a session `free` marked freed_from that goal, the reuse bind refuses without --force.
- watch-go-unreadable-pool: watch.py go treats an unreadable pool as empty when choosing a slug, so it can queue a goal under a slug a session already holds but hasn't frozen.
