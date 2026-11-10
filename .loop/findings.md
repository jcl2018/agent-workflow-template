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
