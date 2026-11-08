<!-- workflow-docs -->
# Setup

Milestone: https://github.com/jcl2018/agent-workflow-template/milestone/9

## Summary

Skill: `workflow-setup`. Adopts a repo into this template's format: loop config, feature pages with criteria and tests, and the regression workflow, printing what it found and would add or convert before writing on a branch. `update.py` refreshes only the skills from a newer package, and `design-guide.md` explains how the parts fit. `--bare` writes only the config, queue and findings. Getting started is in the README.

Commands, flows and how-tos: `skills/workflow-setup/SKILL.md`.

## Criteria

- SET-1: **Reviewed 2026-11-08** One command adopts a repo: sets up a new or existing repo in this template's format at once (loop config and checks, feature pages with criteria and tests, a milestone per feature plus Backlog, nightly regression in GitHub Actions, health rules); in an existing repo it adapts what is there instead of overwriting. <!-- reviewed 925ba216 -->
- SET-2: **Reviewed 2026-11-08** Suggest, then apply: prints what it found, what it would add or convert, and what doesn't fit; then applies on a branch that goes through the usual loop. <!-- reviewed 8e167d1d -->
- SET-3: **Reviewed 2026-11-08** Shipped as a versioned package of separate skills in the Agensi format, with a version number, working in Claude Code, Codex and other SKILL.md agents, every script self-contained and under 20 KB. <!-- reviewed 7c66e31a -->
- SET-4: **Reviewed 2026-11-08** Repos can update: a repo that installed it can check for a newer version, see what's new, and update to get new commands and guidance without losing its own config, criteria, docs or private settings. <!-- reviewed 3e9cf2d6 -->
- SET-5: **Reviewed 2026-11-08** Carries the design logic: the package explains how the loop and its release step, operation and workers, criteria and tests, regression and health fit together. <!-- reviewed c7963511 -->

## Tests

| Criterion | Test | What it checks | Runs | Last result | Seen failing |
|---|---|---|---|---|---|
| **SET-1** One command adopts a repo: sets up a new or existing repo in this template's format at once (loop config and checks, feature pages with criteria and tests, a milestone per feature plus Backlog, nightly regression in GitHub Actions, health rules); in an existing repo it adapts what is there instead of overwriting. | [adopt-set-1](../../.loop/regression.tsv) | The toy adopt-and-update test holds for SET-1. | both | PASS 2026-11-08 | 2026-11-08 |
| **SET-2** Suggest, then apply: prints what it found, what it would add or convert, and what doesn't fit; then applies on a branch that goes through the usual loop. | [adopt-set-2](../../.loop/regression.tsv) | The toy adopt-and-update test holds for SET-2. | both | PASS 2026-11-08 | 2026-11-08 |
| **SET-3** Shipped as a versioned package of separate skills in the Agensi format, with a version number, working in Claude Code, Codex and other SKILL.md agents, every script self-contained and under 20 KB. | [adopt-set-3](../../.loop/regression.tsv) | The toy adopt-and-update test holds for SET-3. | both | PASS 2026-11-08 | 2026-11-08 |
| **SET-4** Repos can update: a repo that installed it can check for a newer version, see what's new, and update to get new commands and guidance without losing its own config, criteria, docs or private settings. | [adopt-set-4](../../.loop/regression.tsv) | The toy adopt-and-update test holds for SET-4. | both | PASS 2026-11-08 | 2026-11-08 |
| **SET-5** Carries the design logic: the package explains how the loop and its release step, operation and workers, criteria and tests, regression and health fit together. | [adopt-set-5](../../.loop/regression.tsv) | The toy adopt-and-update test holds for SET-5. | both | PASS 2026-11-08 | 2026-11-08 |
