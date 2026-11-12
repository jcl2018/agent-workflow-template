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

## Codex run report

Run on 2026-11-11 with codex-cli 0.167.0, signed in with a ChatGPT account, model `gpt-6-luna` (the machine's configured default, `gpt-5.4`, is not supported by the account; the harness picks from codex's model cache). A clean toy repo, a fresh HOME with no private settings, `codex exec -s workspace-write` with the git folder, the remote and `~/.workflow-loop` as writable roots. About 10.7K tokens per run.

| Command | Result in Codex |
|---|---|
| setup (adopt) | wrote the adoption on branch workflow-setup |
| merge into main | exit 0 |
| go (`goal.py new`) | froze the goal, goal file written |
| live board (`monitor.py report`) | exit 0, lists the goal |
| health check | prints `HEALTH:` (not green on a bare toy, as on any new repo) |
| regression run | prints `RESULT` |

What broke and was fixed: setup crashed with a traceback when the sandbox left the home folder read-only (now a NOTE, adoption goes on). Collision checks between a Codex pod and a Claude pod found none. See the design's findings.
Where Codex is not available (not installed, not signed in, usage limit, unsupported model) the live row exits 77 and the run records SKIPPED, never PASS.
