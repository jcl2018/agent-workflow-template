# review-sitting plan

Build steps (done in order, all on the wiki pages and DECISIONS.md):
1. SET-13 pool bullet, SET-13 worker-model bullet and REG-10 "(Linux or macOS, in CI or a session)" edited while Unreviewed (commit c08fea59).
2. criteria.py unreview REG-5 AUT-5 DEL-5 DEL-6 DOC-1 MON-3 MON-4 MON-5 --user, then the nine wordings applied as written in DECISIONS.md (Monitoring Non-goals too); DECISIONS.md section renamed "Applied 2026-11-12 (owner sitting)".
3. MON-5's title shortened to meet DOC-7 (a requirement line is at most 20 words); its detail was already in its sub-bullets.
4. criteria.py review on every Unreviewed requirement id of Automation, Delivery, Documentation, Guardrails, Health, Regression, Setup, Monitoring, and criteria.py review on each of the eight pages, with the owner's typed sentence as LOOP_OWNER_WORDS.

Tests per done line: docs.py check prints DOCS OK with no CHANGED, LOCKED or FORMAT line (done line 3); grep of the pages finds no Unreviewed requirement (line 1); the nine wordings read as in DECISIONS.md (line 2). No regression row: no code changes.

Risks: a page review made before a later requirement edit goes LOCKED; review last, as the plan orders.
