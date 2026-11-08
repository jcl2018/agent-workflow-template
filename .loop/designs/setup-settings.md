# Design: setup-settings (office-hours, auto-recommended answers)

Mode: builder (internal tooling). Done lines in `.loop/goals/setup-settings.md` are frozen; this design meets them.

## Problem
Settings are scattered: repo ones in `.loop/config.json` with defaults hardcoded in each script (`cfg.get("parallel", 3) or 3` in board.py, monitor.py, watch.py), private ones in `~/.workflow-loop/flow.json` and nowhere documented. Setup (`setup.py`, 6.8 KB) writes `parallel: 3`. Nothing lists every setting with a default and a reason.

## Premises (accepted)
1. Two homes only: repo config (committed) and a private file outside the repo (never committed).
2. Defaults live in ONE table, not per script. Scripts read the config fresh each run (no caching across runs).
3. `parallel: 0` = unlimited; `0` must not fall through `or 3` (that bug is the main risk).
4. Private settings extend the existing `~/.workflow-loop/flow.json` / `$LOOP_FLOW`; no new private file.

## Approaches
- A (minimal): fix `parallel` 0 in the three readers, add a doc. Does not meet "Setup writes both halves".
- B (recommended): one shared `settings.py` holding a SETTINGS table (key, home, default, one-line explanation); `get(cfg, key)` for every script, `reference` prints the table, setup writes missing keys with defaults. Wiki `Settings` reference generated from the same table so docs cannot drift.
- C: JSON schema + validator. Heavier than needed.

Recommendation: B. Constraint: scripts are self-contained and under 20 KB each (skills ship separately), so a shared module must be copied/vendored per skill or imported from a path each skill already has; smallest option is a small `settings.py` in workflow-setup and a tiny inlined `DEFAULTS` read in monitoring scripts, with a toy test asserting the two tables match.

## Plan
1. `skills/workflow-setup/scripts/settings.py` (<20 KB): table of all repo settings (parallel, cadence, auto_approve, auto_merge, version/release-note switches, routines, regression schedule, time and token budgets, mend, max tries, resume_on_limit, base, wiki_dir, version_file, risky_paths) and private settings (flow file with default suite and per-step overrides, agent command, allowed tools and model per step, own health rules, followed repos); `reference`, `fill-repo`, `fill-private`.
2. `setup.py` calls fill for both halves; existing values are never overwritten; private file written 0600 outside the repo.
3. Monitoring scripts (board.py, monitor.py, watch.py, graph docs) read `parallel` via one helper: 0/unlimited -> no slot limit, default 0; board "a free slot" text handles unlimited.
4. `.loop/config.json` here: `"parallel": 0`. Update `skills/loop-files.md` and monitoring SKILL/references text ("3 at a time" -> unlimited by default).
5. Wiki: Setup.md SET-1/SET-2 rewritten exactly as in done line 1, then `criteria.py review --user` to mark Reviewed 2026-11-08; add a Settings reference page (generated).
6. Toy test `dev/toy/test-settings.sh`: sets parallel to 2 then 0 and sees the board/watch effect; asserts table lists every named key; asserts private half is written outside the repo; asserts every script < 20 KB (note: regression.py 20,093 B and release.py 20,376 B are already near/over 20,000 and must be checked or trimmed).

## Risks
- `or 3` truthiness bug when parallel=0.
- Script size limit on regression.py/release.py (touches only if they read settings).
- Duplicated defaults between skills; mitigated by the toy table-match test.

## Assignment
Build step 1 and the parallel helper first; run the toy test before touching docs.
