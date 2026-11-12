# spec-decisions plan

Checked against the code: skills/workflow-delivery/SKILL.md:78 (full suite once per goal in qa) contradicts REG-7;
skills/workflow-regression/scripts/regression.py:24 (issues dry-run unless a token is set) contradicts GRD-5;
skills/workflow-delivery/scripts/fit.py `spent_tokens` and board_lines.py show 0 for no count (GRD-2);
skills/workflow-health/references/commands.md:44 names `test_budget_seconds` while lean.py reads `test_budget_minutes`;
Monitoring.md:15, Regression.md:17 and :19, Documentation.md:15 and :20 hold module/refactor notes in Usage.

## Build steps (one commit per group)
1. Un-review the Reviewed requirements I change with `criteria.py unreview ... --user` (owner words needed): REG-5, AUT-5,
   DEL-5, DEL-6, DOC-1, DOC-14 (only if touched), MON-3, MON-4, MON-5, and the Monitoring page (Non-goals line).
2. Reword, smallest change each: decisions 1-10 as in the design. SKILL.md:78 -> affected rows in the test budget; the
   full suite is the scheduled run. commands.md:44 -> `test_budget_minutes`.
3. Regression: HLT-6 row descriptions say test_budget_minutes; `criteria.py render` then `docs.py render`.
4. DECISIONS.md: one dated (2026-11-12) entry per decision: decision, why, requirement ids.
5. File two defect issues (gh): regression.py writes issues on a token alone (no --live); an unread token count shows 0.
6. Regression rows for the done lines (grep checks on pages/SKILL.md), each `red`-proved against HEAD.

## Tests
- Done line 1: row `spec-decisions-wording` (land): greps that SKILL.md:78 no longer says the lane runs the full suite,
  commands.md names `test_budget_minutes`, the Monitoring non-goal reads "unless auto_merge", MON-5 has no "full board",
  GRD-5 names `--live`; `docs.py check` clean of problems this goal caused. Red: run against the pre-change HEAD.
- Done line 2: row `spec-decisions-log` (land): DECISIONS.md has ten 2026-11-12 entries and every changed id reads Unreviewed.

## What could break
- Rewording reopens another conflict (a MON-3/4/5 mixup, a DOC page rule). Mitigation: `docs.py check` and `health.py check`.
- STALE Guardrails and CHANGED Monitoring existed on main; the former clears with the edit, the latter needs the owner's review.
- The shim is only for this session; qa, ship and the PR run on the real code after win-posix-calls merges.

## Out of scope
Fixing regression.py or the token display (defect issues only), reviewing any page, HLT-2 requirement text.

PENDING: the owner's exact words to un-review Reviewed requirements and the Monitoring page
