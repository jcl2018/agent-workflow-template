# Plan: drop-usage

1. Wording: DECISIONS.md section; the owner un-reviews and reviews DOC-1, DOC-2, DOC-6, HLT-2, the Documentation PRD and the Health PRD (done, with their words).
2. Code: criteria.py, prd.py, pageformat.py, entry.py, defects.py, judge.py, counting.py (Automation links).
3. Pages: Usage removed from the 8 pages; entries moved to the command references; docs.tsv excludes SKILL.md and commands.md.
4. Tests: Python toys test-no-usage, test-command-reference, test-runbook-link (each row seen failing); the nine bash toys and 13 rows follow the pages (pending a Linux or Mac run).
Could break: a bash toy built on Usage pages; unseen until a Linux run. Out of scope: other command-reference rewrites.
