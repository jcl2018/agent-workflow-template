# Add a Usage section to feature pages and make the criteria limit a setting, with the owner's new DOC-1 wording approved in chat on 2026-11-08

- Slug: doc-usage
- Touches: skills/workflow-docs, skills/workflow-health/scripts/health.py, skills/workflow-setup, docs/wiki, .loop/config.json, .loop/regression.tsv, dev/toy

## Done lines

Frozen. A wrong done line needs a new goal.

1. DOC-1 is unreviewed and rewritten word for word as follows, then marked Reviewed 2026-11-08 with criteria.py review --user, since the owner approved this wording in chat: DOC-1 "Template. One template defines every feature page: Summary (two or three lines); Usage (when the feature has commands, the commands and how to use each one, in a line or two; left out when nothing applies); Criteria (up to the repo's criteria limit, a setting that defaults to 6, each with its review status); Tests (one row per test: the criterion it proves, the test linked to its regression row, its last result and date, and not enforced for a criterion with no passing test). Nothing else goes on the page."
2. criteria_max in .loop/config.json, default 6, is read by the docs check and health instead of a fixed number, and Setup writes it with a one-line explanation
3. Every feature page is rewritten to the template, with a Usage section listing its real commands taken from the skill files, and no Reviewed criterion's wording changes
4. Each test currently marked not enforced gets a real test seen failing once and passing now, or is listed in the goal's report with why it cannot be tested
5. A toy test proves the criteria_max setting, the Usage section, and that a page with no commands passes without one; docs check and health stay green

## Verify by hand

1. Run `python3 skills/workflow-docs/scripts/docs.py check`.
   Expect: it prints `DOCS OK: 7 pages`.
2. Set `"criteria_max": 1` in `.loop/config.json`, run the same command, then put it back to 6.
   Expect: it prints a `CAP` line for every page with more than one criterion, naming `criteria_max`.
3. Open `docs/wiki/Health.md`.
   Expect: a Usage section between Summary and Criteria listing `health.py check`, `judge` and `run`.
