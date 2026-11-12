# Design: codex-proof

Goal: `.loop/goals/codex-proof.md` (4 frozen done lines). Issue 38: prove the template runs in Codex, and that a Codex pod and a Claude Code pod run side by side without colliding.

## Approach

One harness, `dev/toy/test-codex.sh`, with five parts. It builds a clean toy repo with no private settings (HOME is a fresh folder), gives `codex exec` a plain prompt of `NAME: COMMAND` lines (setup, merge, go, board, health, regression), and reads the files the commands leave. It never trusts what Codex says about the run.

- `home`: setup with a read-only home folder, as Codex's `workspace-write` sandbox leaves it.
- `collide`: a Codex pod and a Claude pod, simulated with `LOOP_SESSION_TOOL` and `LOOP_OPERATION_SESSION`, queue goals, bind workers and run lanes at once.
- `skip`: a row that exits 77 is SKIPPED.
- `fake`: the harness against `dev/toy/fakecodex`, which runs the prompt's commands with no model.
- `live`: the real codex. It probes with one call first and skips when codex is not installed, not signed in, or cannot answer.

## Decisions

- A row that cannot run on this machine exits 77 and the runner records SKIPPED (runs.py, lanes.py, the nightly job in actions.py). A SKIPPED row is never PASS, opens no issue and is never reused. The alternative, a row that passes quietly without Codex, is what the done line forbids.
- The live row is `nightly`: a land lane would spend a model call on every push. The offline rows are `land`, so SET-3 stays enforced on every lane.
- The harness picks the model from codex's own model cache, because this machine's configured default is not supported by its account. `CODEX_MODEL` overrides it.
- SET-3 is rewritten word for word and left Unreviewed. Marking it Reviewed needs the owner's own words to this session; a relayed note is not that.

## Findings from the live run

1. Setup crashed with a traceback when the home folder is read-only. Fixed: it prints a NOTE and goes on with the repo adoption.
2. With a read-only home, `go` is refused for want of `~/.workflow-loop/flow.json`. The Codex sandbox needs that folder in `writable_roots`; the setup SKILL.md and the harness now say so.
3. The configured default Codex model is rejected for this account. The harness avoids it; it is the owner's local config, so nothing was changed.
4. Collision check, no collision found: queue and bind survive four concurrent callers, a repeated slug is refused, lane slots are one machine-wide pool in `~/.workflow-loop/lanes` so pods queue behind each other by design, run records are per branch. One thing to know: each pod needs its own `LOOP_FLOW` file if their agent commands differ, because `~/.workflow-loop/flow.json` is shared by default. Lane slot labels do not say which pod holds a slot ("repo by hand").
