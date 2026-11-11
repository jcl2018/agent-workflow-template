# A new Guardrails feature page in the docs format lists every guardrail the template has or needs, each with what it protects against, where it is enforced, its setting and the health check that proves it is on, so guardrails are one visible set that health checks and adoption installs; docs only, no code

- Slug: guardrails-prd
- Touches: docs/wiki, README.md, .loop/docs.tsv, .loop/START.md

## Done lines

Frozen. A wrong done line needs a new goal.

1. A Guardrails page in the docs format (Problem, Usage, Requirements, Non-goals, Success metrics) with GRD requirements, all Unreviewed, covering the existing guardrails by reference (time and preparation budgets, the private-name scan, no hook bypass, workers cannot widen their own touches, the network confirm flag, only main writes shared state, protected main and required checks, token budgets) and the new ones (CI cost: superseded runs cancelled, heavy jobs skipped for changes with no code, an alarm on runs or minutes per day; token use far past a step's typical; long runs)
2. The page says each guardrail is checked by a Health rule group (present, working, with a negative control) and installed by setup when a repo is adopted, naming which feature owns each part, without changing those features' pages
3. Home has the Guardrails row, the README has a how-to-use section, docs.tsv has its row, docs.py check passes, and nothing on the page claims a guardrail is enforced that is not

## Verify by hand

<!-- Numbered steps for a person, each with an Expect: line. A release needs this. -->

1. Open docs/wiki/Guardrails.md (or the published wiki's Guardrails page).
   Expect: Problem, Usage, Requirements, Non-goals, Success metrics and Tests; GRD-1 to GRD-10, each **Unreviewed**, each part naming its owner feature and requirement ID or "new"; every Tests row reads not enforced.
2. Open the wiki's Home page and the README's "How to use Guardrails" section.
   Expect: a Guardrails row linking the page, the README section and milestone 11; the README table's four lines.
3. Run `python3 skills/workflow-docs/scripts/docs.py check`.
   Expect: `DOCS OK`.
