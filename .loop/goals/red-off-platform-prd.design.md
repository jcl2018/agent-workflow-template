# red-off-platform-prd design

Problem: on native Windows the bash toy tests skip (exit 77), so a new row cannot be seen red there. Today `red` already refuses a break run that exits 77, but the PRD says nothing about it and the only way to record a red proven elsewhere is to hand-edit `.loop/regression.tsv`.

Approaches
1. Hand edit the row's `seen_red` after a Linux run. Cost: none. Risk: no record of who proved it; nothing stops a Windows skip being written in.
2. `regression.py red ID --off-platform --runner NAME --commit SHA`: records `seen_red` (still a pure date, since fit.py and `SEEN` read it as one) and appends runner and commit to a new `.loop/regression-red.tsv` (id, date, runner, commit). Refuses an unknown row, a runner that names Windows, a commit that is not a commit in this repo. Cost: one function plus a parser entry; regression.py is 18,455 of 20,480 bytes, so the code goes in a new small module `offred.py`.

Chosen: 2. It keeps `seen_red` a date, adds provenance, and the Windows rule is in code, not just prose. `red` itself keeps refusing a break run that exits 77, so a skip never sets seen red; a toy test proves both.

Done lines
- Line 1: a new REG-10 requirement on docs/wiki/Regression.md, Unreviewed, plus usage text; workflow-docs check prints DOCS OK.
- Line 2: `red --off-platform` with runner and commit, a refusal for a Windows runner, and a toy-test section in dev/toy/test-regression.sh (runs on Linux/Mac only; its red commands are owed).

Open questions: none for the owner.
