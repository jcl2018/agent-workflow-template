# Design: drop-usage

The owner (2026-11-13): "remove the usage section, because you cannot say each feature has an API; we already have the README and How to use, and natural language will find the right way to run it."

- Feature PRD pages lose Usage. `criteria.py` raises USAGE for any Usage section; `prd.py` no longer reports CHANGED; `pageformat.py` loses the Usage entry checks.
- `entry.py` builds START.md's Features "How to use" column from each page's skills' Command maps (docs.tsv -> SKILL.md).
- Health: `usage-readme` compares the README with the skills' Command maps; the judge's Usage-drift check is gone.
- The exact syntax, output and refusals stay in each skill's references/commands.md (and Setup's SKILL.md); entries that lived only in a Usage section were moved there. DOC-6 now says so.
- A skill's SKILL.md and command reference are excluded from every page's mapped paths in .loop/docs.tsv, so editing them never stales a page.
- Also approved: a Runbook's Output may name the Deployments row it produces (checked), and the Automation block links each routine to its Runbook.
Out of scope: rewriting the command references beyond the moved entries.
