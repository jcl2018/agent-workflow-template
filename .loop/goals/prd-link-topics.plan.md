# Plan: prd-link-topics

Checked against the code: `deployments.py` (rules, now the link and topic helpers), `criteria.py` (`contract`, calls `link_page`), `render.py` (Tests rewrite, `front`, `refresh`), `pageformat.py` (`home`), `counting.py` (`read_map`, `sources`, `write_map`), `docs.py` (`problems`), `workflow-regression/scripts/tests.py` (`features`) all exist.

## Build steps (done in the worker session)
1. docs.tsv third column read by `counting.sources`, kept by `write_map`.
2. `link_of` / `read_link` / `link_page` in `deployments.py`; `criteria.contract` routes a link-form page there; UNREAD when the source cannot be read.
3. `render` fills a link-form page's Tests table from the linked ids; `tests.py` reads the same ids for the Tests page.
4. `topics` setting; `pageformat.home` checks the Topic column and grouping; `render.regroup` writes it.
5. DOC-1, DOC-2, DOC-4 wording proposed in DECISIONS.md; SKILL.md paragraph.

## Tests
Done line: a link-form page passes and an unreadable link is UNREAD; Home renders a Topic column.
Regression rows (one per behaviour), each run by `dev/toy/test-docs-link.sh`, each seen failing on a copy with the change removed before it is trusted: `link-page-passes`, `link-unread-never-pass`, `link-source-setting`, `home-topic-column`.

## What could break
Home and README for repos that set no `topics` (column only when set); `write_map` dropping the new column (kept); script size caps (code moved into `deployments.py`).

## Out of scope
The review lock for a PRD at a source; migrating any page to a link; external sync.

PENDING: whether the review lock for a PRD at a source should be enforced in code next
