# spec-decisions design

## Problem
The health review found requirements that contradict each other or the code. The owner decided each conflict on
2026-11-12 (the code and the safer behavior win; the wording changes). This goal rewords only the lines it must, marks
each changed requirement Unreviewed, and logs each decision in DECISIONS.md.

## Approaches
1. Rewrite every page broadly to a clean model. Costs a lot, touches Reviewed text that is fine, and buries the diff.
2. Edit only the conflicting lines, one decision at a time, un-review just those requirements, log a dated entry each.
   Small diff, easy for the owner's final review. Risk: a reworded line must not reopen a different conflict.

Chosen: 2.

## Per decision (requirement ids and what changes)
1. REG-7 (already Unreviewed) keeps "the loop never runs the full suite". Fix workflow-delivery SKILL.md:78 (the lane
   runs the affected rows within the test budget; the full suite is the scheduled run).
2. MON-3 owns the live board (report, dashboard, artifact); MON-4 keeps that board's layout and drops its own owner role;
   MON-5 owns the check-in layout and no longer says it prints the board. Remove MON-3's third layout.
3. GRD-5, REG-5, AUT-5 (HLT-4 too): GitHub writes only behind `--live`; scheduled workflows pass `--live`.
   Code gap: regression.py:24 writes whenever GH_TOKEN/GITHUB_TOKEN is set -> defect issue.
4. GRD-1 and its overlapping bullets (GRD-2/3/4/8) become an index of owning ids (DEL-8, REG-7, DEL-9, SET-8, MON-7, MON-8).
5. GRD-2 token bullet: no token count records "unknown", board shows "tokens unread", never 0.
   Code gap: fit.spent_tokens and board_lines show 0 -> defect issue.
6. DEL-6 condensed only when `review_depth: condensed` (default full); DEL-5 describes auto_merge on (merge + publish)
   and off (draft release).
7. DOC-1 allows generated Deployments (DOC-14) and Runbook (DOC-16); DOC-4 allows the generated Settings and Automation
   sections (DOC-15); Regression metric uses REG-7's 15-minute floor; drop module/refactor notes from Usage
   (Documentation, Regression, Monitoring pages) per DOC-6.
8. HLT-4, AUT-2, AUT-3 say "when feature_labels is on" (default false).
9. `test_budget_minutes` everywhere: skills/workflow-health/references/commands.md:44 and the two HLT-6 row descriptions.
10. Monitoring non-goal: "never merges unless auto_merge is on".

## What each done line needs
- Line 1: every conflict above fixed in the pages and SKILL.md/commands.md; `docs.py check` clean (render for Tests).
- Line 2: ten dated DECISIONS.md entries; each changed requirement reads Unreviewed (Reviewed ones via criteria.py unreview).

## Open questions
- Un-reviewing Reviewed ids (REG-5, AUT-5, DEL-5, DEL-6, DOC-1, DOC-6?, MON-3/4/5, and the Monitoring page for its
  non-goal) needs the owner's exact words in LOOP_OWNER_WORDS; asked the operation session.
- `docs.py check` already printed STALE Guardrails and CHANGED Monitoring (Usage) on main before this goal; DOCS OK
  needs the Guardrails page edit (clears STALE) and the owner's re-review of Monitoring (cannot be cleared by an agent).
