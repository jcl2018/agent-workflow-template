# Design: review-findings

## Problem
The 2026-11-12 `workflow-health review` of v0.27.34 found 13 places where a page promises something the code does not do, or two pages disagree, plus `workflow-delivery/SKILL.md` at the 150-line limit. The rule is that the code wins and the wording changes; a Reviewed (locked) requirement is not edited but proposed in DECISIONS.md.

## Approaches
1. Change the code to match the pages (restore a health workflow, make failure statuses non-blocking). Large, reverses decisions the owner already made (health runs on the Mac, a failing lane holds a private merge), and risky on Windows where the toy tests skip.
2. Change the wording to match the code (chosen): Usage entries, Unreviewed requirements and the regression row links. Small, reversible, and each edit is checked against the script that prints the behaviour.

## Chosen: approach 2
- Automation: the health workflow, `--check`, the Actions mail job and the Mail test tab are gone from Usage; `health_cron` forms are the ones `local install` accepts; the regression workflow entry says `NOT WRITTEN` for a private repo; AUT-2 describes the commit statuses the pr lane posts; AUT-1/AUT-2 are linked to the rows that already prove them.
- Delivery: DEL-2 is on the page (the review's prompt cut it off); it moves up beside DEL-1. Usage loses refactor history. DEL-5 stays the spec-decisions proposal.
- Guardrails: GRD-4 says what a worker may write; Usage no longer copies Health's check entry or names v0.27.17; rows for built guardrails name GRD-2 and GRD-3.
- Health: AUT-2 and AUT-3 already say "when feature_labels is on" (spec-decisions).
- Setup: the entry no longer lists `health.yml` or `mail-test.yml`.
- SKILL.md: repeated prose cut to 146 lines.

## What each done line needs
1. Every finding fixed in pages or code, or proposed in DECISIONS.md, and the review reports none: pages edited, decisions logged, row `review-findings-wording`, then a rerun of the review.
2. SKILL.md under 150 lines and docs check clean: row `review-findings-skill-lines`.

## Open questions
- Docs check prints `CHANGED Monitoring` because spec-decisions edited a Reviewed page's Usage; only the owner can clear it.
- The Health Runbook, the Home Automation block (`render.py`) and some mail.py messages still describe a health workflow; their tests pin the old words, so they are follow-ups.
