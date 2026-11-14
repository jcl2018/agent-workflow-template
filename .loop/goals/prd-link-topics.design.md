# Design: prd-link-topics

## Problem
A feature's PRD should be able to live outside the wiki page (a link, or a document an MCP connector serves) as the single source, and Home should group features by topic. The docs check must accept such a page and say UNREAD, never pass, when the source cannot be read.

## Approaches
1. Page-only: a `PRD: <link>` line on each page, read by the check. Cheap, but the source is only on the page and cannot be set per feature from one place.
2. A per-feature source in `.loop/docs.tsv` (third column: `page`, `url:<link>`, `mcp:<server>:<resource>`), shown on the page as `PRD: <source>`; the check reads it through one reader (`LOOP_PRD_READER` for MCP). Slightly more code; one setting, same path for check, render and the Tests rows.

## Chosen
Approach 2, with the page line kept as the visible statement and checked against the setting. Topics come from one `topics` setting; Home gets a leading Topic column only when it is set, so repos without it are unchanged. New code lives in `deployments.py` to keep every script under the size cap.

## What the done line needs
- A link-form page (title, `PRD:` line, Runbook/Deployments/Tests only) passes `docs.py check` when the source is readable, with its ids filling the Tests table.
- An unreadable source prints UNREAD and exits non-zero.
- `render` writes Home's Topic column grouped by topic; a wrong Topic cell fails the check.

## Open questions
- The review lock for a PRD at a source (the document's version or date): wording is proposed in DECISIONS.md; the code does not enforce it yet.
