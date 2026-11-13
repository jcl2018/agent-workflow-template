# health-fails-main design

Problem: health check on main FAILs on three draft regression rows (no command or level) and on workflow-regression/SKILL.md at 157 lines (limit under 150).

Approaches: (A) give each draft row a real command that checks the promised behavior, list it in .loop/regression-known.tsv with the reason "not built", prove it red; trim SKILL.md prose. (B) delete the rows (refused: never delete a row to silence the check). (C) mark them covered (untrue: nothing proves them elsewhere).

Chosen: A. grd1-guardrail-list checks the Guardrails page for a table; del8-session-tokens checks flow.py reads token_budget; grd3-hook-bypass checks guards.py names no-verify or hooksPath. All three fail today, so they are known failures and flip to FIXED when built. SKILL.md goes 157 to 148 lines by cutting repeated prose only; no rule changed. No scripts touched.

Open questions: none.
