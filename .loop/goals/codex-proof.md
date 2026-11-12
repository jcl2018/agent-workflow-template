# Fix issue 38: prove the template runs in Codex, with the owner's new SET-3 wording approved in chat on 2026-11-08

- Slug: codex-proof
- Touches: skills, dev/toy, .loop/regression.tsv, docs/wiki/Setup.md

## Done lines

Frozen. A wrong done line needs a new goal.

1. SET-3 is unreviewed and rewritten word for word as follows, then marked Reviewed 2026-11-08 with criteria.py review --user: SET-3 "Shipped as a versioned package. The template ships as one versioned package of separate skills in the Agensi format, every script self-contained and under 20 KB. It works out of the box with a built-in default flow, and is proven to run in both Claude Code and Codex on a clean test repo with no private settings."
2. On a clean toy repo with no private settings, the key commands (setup adopt, go, the live board, health check, regression run) run in Codex, results are recorded in the goal's report, and anything that breaks is fixed; if Codex is not installed or not signed in on this machine, the goal reports that plainly instead of passing
3. A regression row proves the Codex run keeps working where Codex is available and is marked skipped, never passed, where it is not; issue 38 closes when this merges
4. Per DOC-3, each done line above is recorded on its PRD page as one or more Given/When/Then scenarios under the requirement it serves, each linked to its regression row with its last result

## Verify by hand

<!-- Numbered steps for a person, each with an Expect: line. A release needs this. -->
