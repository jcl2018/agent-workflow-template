# A smoke set proves each agent and machine cell, and health reads the matrix

- Slug: matrix-smoke
- Touches: skills/workflow-regression/scripts, skills/workflow-health/scripts, .github/workflows, dev/toy, docs/wiki/Setup.md, DECISIONS.md

## Done lines

Frozen. A wrong done line needs a new goal.

1. smoke writes a dated matrix record; health warns on an unproven cell and fails on an unproven V1-required cell

## Verify by hand

1. Run `python3 dev/toy/matrix-smoke.py --agent claude-cli`.
   Expect: seven PASS lines (package, adopt, freeze, qa, health, runbook, relay), then `SMOKE ... pass` and `RECORDED .loop/matrix-runs.tsv`, whose new line holds today's date, your agent, OS, machine and commit.
2. Run `python3 skills/workflow-health/scripts/health.py check --group adoption`.
   Expect: with `.loop/matrix-runs.tsv` present, a FAIL for each V1 cell with no pass in 7 days (Claude Code on macOS, CI on Linux) and a WARN "not proven" for each other cell; none for Claude Code on Windows.
