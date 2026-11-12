# Plan: review-findings

## Build steps (all done on the branch)
1. Merge origin/loop/spec-decisions (open PR) so its wording on the same pages is kept; resolve the one Delivery.md conflict by keeping both sides.
2. Automation.md: replace the health workflow entry with the removed notice carrying the `health_cron` forms; drop `--check`; mail send/test read the Mac's `mail.env`; regression workflow entry says NOT WRITTEN for a private repo; AUT-1/AUT-2 bullets match `workflows.py` and `private.py` (checked: `tick_repo`, `pr_result`, `lanes_cli.workflow`).
3. Setup.md and Health.md: no `health.yml`/`mail-test.yml`; install entry and Delivery `record`/`pr` entries lose history.
4. Guardrails.md: GRD-4 bullet, Usage pointer, no v0.27.17.
5. Delivery.md: DEL-2 beside DEL-1.
6. regression.tsv: nine existing rows guard AUT-1, AUT-2, GRD-2 or GRD-3; two new rows for the done lines.
7. SKILL.md trimmed to 146 lines; DECISIONS.md lines; `docs.py audit` re-renders Tests and START.md.

## Tests per done line
- Done line 1: `review-findings-wording` (greps the Usage and requirement wording), seen failing by turning NOT WRITTEN into WRITTEN on a copy of HEAD; plus a rerun of `workflow-health review`.
- Done line 2: `review-findings-skill-lines` (under 150 lines and docs check clean apart from the owner's lock), seen failing by appending 200 lines.

## What could break
- Toy tests that read page text: checked `test-local-schedule.sh` (usage, messages), `test-runbook.sh`, `test-adoption-golden.sh`; none read an edited phrase. The toy tests skip on native Windows, so Linux CI is their first run.
- A retargeted row loses its old guard: each owner kept other rows.

## Out of scope
Health Runbook and `render.py` built-in routines naming `health.yml`, mail.py's "Mail test workflow" text and settings text naming Actions secrets (their tests pin the words; follow-ups), AUT-3/AUT-7 wording about health after regression for a private repo, DEL-5 (spec-decisions), clearing Monitoring's review lock (owner).

PENDING: none
