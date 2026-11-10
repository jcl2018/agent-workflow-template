# Make the documentation format enforceable and apply it: Home is one features table, each feature has a natural-language front door, API-style Usage, bulleted Requirements, a user-perspective Problem, a linked Tests table, one full Tests page, and every issue on a milestone (owner, 2026-11-09). PRD: Documentation DOC-4..DOC-11

- Slug: docs-format
- Touches: skills/workflow-docs, skills/workflow-regression, skills/workflow-health, skills/workflow-setup, docs/wiki, README.md, .loop/regression.tsv, .loop/docs.tsv, dev/toy

## Done lines

Frozen. A wrong done line needs a new goal.

1. The Documentation PRD page adds DOC-4..DOC-11 with the wording in the operation session's draft (docs-format-draft.md), Unreviewed for the owner's final review
2. docs.py check enforces each of DOC-4..DOC-9 (Home table columns and nothing else; README How-to-use sections are phrases not commands; Usage entries carry syntax, output and refusals; Requirements are bullets; Problem has no code-internals vocabulary; Tests is a table with the listed columns and links), each refusal naming the page, section and rule
3. A generated full Tests page lists every test grouped by feature with its latest result, date, run link and seen-failing mark, and each feature's Tests table links into it (DOC-10)
4. health flags an open issue with no milestone, and each feature page links its milestone (DOC-11)
5. Home, the README How-to-use sections and every feature page are rewritten to pass the new checks, keeping each requirement's meaning; meaning changes are listed in the PR for the owner
6. A toy test proves each check fails on a bad page and passes on a good one, seen failing first; docs check and health stay green
7. The PR body gives the owner one review list: each page and what changed, for a single final review

## Verify by hand

<!-- Numbered steps for a person, each with an Expect: line. A release needs this. -->
