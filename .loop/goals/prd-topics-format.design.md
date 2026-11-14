# Design: prd-topics-format

Problem: v0.28.41 taught the docs check to accept Home with a Topic column and made the `topics` setting optional, but the wiki itself is still in the old format. This goal adopts it: the repo sets `topics`, Home leads with the Topic column and the settings blocks list the row.

Approaches: (1) set `topics` in `.loop/config.json` and re-render with the existing tools (small, uses code already merged); (2) edit Home by hand (risks drift from the renderer). Chosen: 1. The renderer writes Home, README and START.md, so they cannot disagree with the check.

Done line: Home's table leads with Topic, the features grouped by the default topics (Build loop: Delivery, Monitoring; Quality: Regression, Health, Guardrails; Operations: Automation, Setup; Docs: Documentation). Needs: the config key, the re-render, two rows (home-topic-live, config-holds-topics) that fail if either goes missing. No requirement wording changes; DOC-1, DOC-2 and DOC-4 proposals stay in DECISIONS.md.

Open questions: none.
