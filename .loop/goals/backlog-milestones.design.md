# Design: Backlog milestones

## Problem
Findings from delivery and health have no single home: health issues sit on no milestone, a goal's leftover findings are lines in `.loop/findings.md`, and nothing tells a defect from an idea. The owner approved one home per filing: nine standing milestones ("Backlog: <Feature>" per feature page, plus "Backlog: Other"), `defect` issues for what is broken, `backlog` issues on those milestones for the rest.

## Approaches
1. A new script that owns milestones and filing. Clean, but the package is at its 99-file cap and every skill script sits near 20,480 bytes, so it cannot exist.
2. Put the logic in `workflow-health/scripts/milestone.py` (4.5 KB, the only script with room) and call it: `file.py` imports it for health findings; setup calls its `backlog` command; `goal.py record ship` calls its `leftovers` command. Cost: a small, tight edit in goal.py (a duplicate flow check removed to make room), survey.py and setup.py. Risk: the wiring crosses skills by path, as goal.py already does for graph.py and criteria.py.

## Chosen: 2
- Kind: a FAIL (except a performance one) and a review conflict is a defect; everything else is backlog. Health's rules do not know which requirements are Reviewed, so a plain FAIL stands in for "broken against a Reviewed requirement".
- Home: defect = label `defect`, no milestone. Backlog = label `backlog`, milestone "Backlog: <Feature>" or "Backlog: Other". An issue the owner moved stays (the milestone is set only when the issue is opened).
- Setup: `setup.py` always calls the issue-filing step, which first runs `milestone.py backlog --live`; `--no-issues` skips both.
- Health: the Adoption group's `milestones` rule warns for each missing milestone, only on a repo with a GitHub origin; INFO when gh cannot list them. Triage prints `N defects, M backlog` per feature and treats "Backlog: <Page>" as that feature.
- Ship: the ship reply's `FILE defect|backlog <Feature>: text` lines are filed by `goal.py record ship` with `--live`, once each (a marker in the body), at most ten, never a line holding an email or the home folder.
- Writes: `milestone.py` writes only with `--live`; `file.py` is unchanged in that (it already needs the owner's confirmation); `goal.py` passes `--live` after ship is recorded.

## Each done line
1. Setup creates the 9 milestones: `milestone.py backlog --live` through setup's filing step (toy: made, once, wired, skipped by `--no-issues`).
2. Health files a FAIL as a defect and a WARN as a backlog item on its feature's milestone (toy: `home()` cases, a filed backlog item, a filed defect, a repeat).
3. A goal's leftover findings are filed the same way at ship (toy: `leftovers` dry run, `--live`, once).

## Open questions
- The Reviewed wording of DOC-10 and HLT-4, and the new DEL-14 and SET-17, wait for the owner (see DECISIONS.md, "Waiting on owner un-review"). The code merges after that.
- The release check ("an open defect with no goal and no owner OK blocks"), the board counts and the Monitoring part are outside this goal's touches (workflow-release, workflow-monitoring).
