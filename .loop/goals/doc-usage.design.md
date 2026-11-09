# Design: doc-usage

Status: APPROVED (recommended answers taken; owner approved the DOC-1 wording in chat 2026-11-08)

## Problem

Feature pages have no place to say how to use the feature, and the criteria cap is a fixed `max_criteria: 5` in
`skills/workflow-docs/references/template.md`, read only by `criteria.py`. The owner wants a Usage section and a cap
that is a repo setting (default 6).

## Premises (accepted)

1. The template sheet stays the single definition of a page; the cap moves out of it into `.loop/config.json` as `criteria_max`.
2. Usage is optional per page: present only when the feature has commands; its absence is never a finding.
3. Usage lists real commands, taken from each feature's skill files, never invented.
4. Reviewed criterion wording is locked; only DOC-1 is reworded, by the owner's approved text.

## Approaches

- A (minimal): add `Usage` to `sections`, keep `max_criteria` in the sheet, bump to 6. Fails done line 2.
- B (recommended): `criteria_max` in config (default 6), read by `criteria.py` (so docs check) and `health.py` via one shared
  reader in `criteria.py`; sheet drops the number and says "the repo's criteria limit"; Setup's `settings.py` registers it
  with a one-line explanation so `references/settings.md` is regenerated. Usage is an optional section between Summary and Criteria.
- C (ideal): a general per-template settings layer. Over-built for one number.

Recommendation: B.

## Plan (for scaffold/implement)

1. `criteria.py`: load rule from the sheet, then override the cap from `config.json` `criteria_max` (int, default 6; bad
   value falls back to 6 with a note). Remove `max_criteria` from the sheet's rules block; add `usage` as an optional section
   (allowed after Summary, before Criteria, never required). Keep the CAP finding text. Update the sheet's Layout prose.
2. `health.py`: any criteria-cap logic goes through the same reader; no fixed number.
3. `skills/workflow-setup/scripts/settings.py`: add `criteria_max` (REPO, default 6, one-line explanation); regenerate
   `references/settings.md`; add to `.loop/config.json` as 6.
4. DOC-1 in `docs/wiki/Documentation.md`: replace with the frozen wording, marked unreviewed then reviewed via
   `criteria.py review --user` (done line 1). Regression rows for DOC-1 keep their ids; refresh rendered Tests tables.
5. Rewrite each wiki page (Delivery, Documentation, Health, Monitoring, Regression, Setup; Home is not a feature page) to the
   template, with Usage listing commands from the matching `skills/*/SKILL.md` (and `references/commands.md` for docs).
   Criterion wording untouched. Stay within the cap of 6 and the 3-line Summary.
6. Not-enforced rows today: HLT-5 has rows already in the registry; the true gaps are the ones whose Tests cell reads
   **not enforced** (HLT-5 at Health.md:41, SET-2 at Setup.md:30). Write a real test for each, seen failing then passing
   (SET-2 can ride the `criteria_max` setting test and `test-settings.sh`); if one cannot be tested, list why in the goal report.
7. Toy test `dev/toy/test-docs.sh` additions: (a) `criteria_max` set to 1 makes a 2-criterion page fail, default 6 passes;
   (b) a page with a Usage section passes; (c) a page with no commands and no Usage passes. Add regression rows (category
   criterion, goal DOC-1/SET-2), seen red before green.

## Risks

- Sheet and config disagree on the cap: resolved by removing the number from the sheet.
- `test-docs-command.sh:44` seds `max_criteria: 5` in the sheet; it must switch to setting `criteria_max` in config.
- Existing page-shape row ("a Commands section fails") must still hold: Usage is allowed, Commands is not.
- Pages already at 5 criteria need no change; none may exceed 6.

## Distribution

No new artifact; ships via the normal PR.

## The Assignment

Review the PR's rewritten Usage sections against each skill's real commands, then run the Verify-by-hand steps.

## Decisions left for the owner

None beyond reviewing the PR.
