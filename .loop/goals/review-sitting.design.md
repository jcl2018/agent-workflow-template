# review-sitting design

Problem: the owner's 2026-11-12 review sitting must be applied: three wording edits (SET-13 pool, SET-13 worker model, REG-10), nine DECISIONS.md proposals, and a review of eight wiki pages, so every requirement reads Reviewed and docs.py check prints no CHANGED or Unreviewed line.

Approaches: (1) edit the wording first, then un-review the nine ids and review every page and requirement in one pass, with the owner's typed sentence as LOOP_OWNER_WORDS; (2) review first and edit later, which would lock the text and need a second un-review. Chosen: (1), the lower risk.

Done lines: the pages read Reviewed (criteria.py review on pages and ids), the nine wordings are on the pages, and docs.py check prints DOCS OK.

Open questions: none.
