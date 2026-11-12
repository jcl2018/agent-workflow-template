# Resolve the 13 findings of the 2026-11-12 health review of v0.27.34 (Automation AUT-1/2/3 vs Usage health.yml, failure statuses, health_cron forms, private-repo workflow drift, unlinked AUT rows; Delivery DEL-2 rows citing a missing id; Documentation Usage history bloat; Guardrails GRD-4 vs workers recording, stale v0.27.17 settings copy, GRD rows not naming ids; Health feature_labels drift; Setup health.yml contradiction), plus workflow-delivery/SKILL.md at the 150-line limit: the code wins and the wording changes, locked requirements become proposals in DECISIONS.md

- Slug: review-findings
- Touches: docs/wiki, skills/workflow-delivery/SKILL.md, DECISIONS.md

## Done lines

Frozen. A wrong done line needs a new goal.

1. Each of the 13 findings is resolved in the pages or code, or listed in DECISIONS.md as a proposal awaiting the owner's un-review, and workflow-health review reports none of them
2. workflow-delivery/SKILL.md is under 150 lines and workflow-docs check prints DOCS OK

## Verify by hand

<!-- Numbered steps for a person, each with an Expect: line. A release needs this. -->

1. Run `grep -c "health.yml" docs/wiki/Automation.md docs/wiki/Setup.md` and `wc -l skills/workflow-delivery/SKILL.md`.
   Expect: Automation.md names `health.yml` once, only as the leftover file to `git rm`; Setup.md names it not at all in its setup entry; SKILL.md has under 150 lines.
2. Open `docs/wiki/Automation.md` and read AUT-1, AUT-2 and the Usage list.
   Expect: no health workflow, `--check` or Actions mail job; the regression workflow entry says a private repo gets `NOT WRITTEN`; AUT-2 says the pull request lane posts commit statuses.
3. Open `DECISIONS.md`.
   Expect: seven "Review findings (2026-11-12)" lines above the "Waiting on owner un-review" section, which still holds only the spec-decisions proposals.
