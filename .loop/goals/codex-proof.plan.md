# Plan: codex-proof

Goal: `.loop/goals/codex-proof.md`. Design: `.loop/goals/codex-proof.design.md`.

1. `skills/workflow-regression/scripts/runs.py`, `lanes.py`, `actions.py`: exit 77 is SKIPPED (done line 3). Reference: regression `references/commands.md` and the Regression page's Usage.
2. `skills/workflow-setup/scripts/setup.py`: an unwritable home is a NOTE, not a crash (done line 2: anything that breaks is fixed). `SKILL.md` names `~/.workflow-loop` as a Codex writable root.
3. `dev/toy/test-codex.sh` and `dev/toy/fakecodex`: the five parts (done lines 2 and 3, and the collision test the owner asked for).
4. `.loop/regression.tsv`: five rows, each seen failing (done line 3; line 4 links them to SET-3's Tests table).
5. `docs/wiki/Setup.md`: SET-3 word for word, Unreviewed (done line 1); the Tests table scenarios (done line 4).
6. Run: lanes, docs check, package check, the live Codex run; record the results in the goal file.
