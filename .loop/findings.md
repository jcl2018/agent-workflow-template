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
