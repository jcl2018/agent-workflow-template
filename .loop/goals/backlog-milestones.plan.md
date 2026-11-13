# Plan: Backlog milestones

Built already (commit 26b8b869 and the rows commit); this plan records the order and the checks.

## Steps
1. `milestone.py` (workflow-health): `make()` shared by `new`, `backlog` and filing; `backlog` makes every missing "Backlog: <Feature>" and "Backlog: Other"; `leftovers FILE` files `FILE defect|backlog <Feature>: text` lines once (marker `loop-leftover`), at most ten, behind `--live`.
2. `file.py`: `home(item, page)` gives (label, milestone); a new issue gets `--label defect|backlog` and `--milestone`; the milestone is made first; an update adds the label only; the owner's milestone stays. `issues.py`: "Backlog: <Page>" counts as that feature; triage prints defects and backlog per feature.
3. `rules.py`, `report.py`: Adoption `milestones` rule and its negative control.
4. Setup: `setup.py` always runs the issue-filing step; `survey.file_issues` runs `milestone.py backlog --live` first.
5. Delivery: `goal.py record ship` files the reply's FILE lines with `--live`; `default-flow.md` tells the ship step the grammar. goal.py stays under 20,480 bytes by dropping a repeated flow check in `cmd_pr`.
6. Docs: Usage entries on Delivery, Documentation, Health, Setup; skill references; DECISIONS.md holds the requirement wording that needs the owner.

## Test per done line
1. `dev/toy/test-backlog.py`: milestones made, once, wired in setup. Rows backlog-milestones-made, backlog-setup-makes, backlog-adoption-warns (seen red).
2. Rows backlog-item-home, backlog-defect-home (seen red).
3. Rows backlog-leftovers-filed, backlog-leftovers-once (seen red).

## What could break
- Bash toys that assert "no milestone" for health filing (test-health-prd.sh, test-health-report.sh, test-automation-email.sh): they skip on Windows and need the Mac or Linux run.
- Setup now runs the filing step on every adoption, even with nothing to file.

## Out of scope
The release check on open defects, the board counts and the Monitoring part (workflow-release, workflow-monitoring are outside the touches); the owner's DOC-10 and HLT-4 rewording, DEL-14 and SET-17 (DECISIONS.md).
