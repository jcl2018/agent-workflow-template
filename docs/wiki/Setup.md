<!-- workflow-docs -->
# Setup

Milestone: https://github.com/jcl2018/agent-workflow-template/milestone/9

Review: **Unreviewed**

## Problem

Skill: `workflow-setup`. Adopts a repo into this template's format: loop config, feature pages with criteria and tests, and the regression workflow, printing what it found and would add or convert before writing on a branch. `update.py` refreshes only the skills from a newer package, and `design-guide.md` explains how the parts fit. `--bare` writes only the config, queue and findings. Setup takes test commands from the repo's CI workflows and scripts (a command that would run zero tests is dropped and reported), proposes feature pages from milestone or track headings or folders with code, follows the repo's version and changelog habit, reports a `.gitignore` line that would block its files with the exact exception, and exits 1 after writing when `agent_command` grants no tools, printing the line to add. Getting started is in the README.

## Usage

- `/workflow-setup setup` shows what it found and would add (`--dry-run`), then writes it on a branch; `--bare` writes only the config, queue and findings.
- `/workflow-setup settings` prints every setting with its default and one-line explanation; `/workflow-setup fill-repo` adds any missing repo setting to `.loop/config.json`. Every setting is in `skills/workflow-setup/references/settings.md`; `cadence`, the minutes between live-board check-ins, defaults to 30.

## Requirements

- SET-1: **Reviewed 2026-11-08** One command adopts a repo. One command sets up a new or existing repo in this template's format, everything at once: the loop config, the feature pages with criteria and tests, a milestone per feature plus Backlog, the nightly regression in GitHub Actions and the health rules. It first shows what it found, what it would add or convert and what doesn't fit, then applies it on a branch through the usual loop. In an existing repo it adapts what is there instead of overwriting. <!-- reviewed 260ea1ed -->
- SET-2: **Reviewed 2026-11-08** Every setting in one place. Every setting lives in one of two places: repo settings in the repo's config, committed and shared, and private settings outside the repo, never committed. Setup writes each with a default and a one-line explanation, I can change any of them at any time, and the framework reads them every run. Parallel workers default to unlimited. <!-- reviewed 1008abc4 -->
- SET-3: **Reviewed 2026-11-08** Shipped as a versioned package of separate skills in the Agensi format, with a version number, working in Claude Code, Codex and other SKILL.md agents, every script self-contained and under 20 KB. <!-- reviewed 7c66e31a -->
- SET-4: **Reviewed 2026-11-08** Repos can update: a repo that installed it can check for a newer version, see what's new, and update to get new commands and guidance without losing its own config, criteria, docs or private settings. <!-- reviewed 3e9cf2d6 -->
- SET-5: **Reviewed 2026-11-08** Carries the design logic: the package explains how the loop and its release step, operation and workers, criteria and tests, regression and health fit together. <!-- reviewed c7963511 -->

## Non-goals

- It never commits private settings to the repo.
- An update never overwrites a repo's own config, requirements, docs or private settings.
- It does not adopt a page that has its own sections; that page is left for a person.

## Success metrics

- A single command adopts a fresh repo, and its docs check and regression rows work right away.
- An update keeps every existing repo setting and page.
- Every script in the package stays under 20 KB.

## Tests

#### SET-1

One command adopts a repo. One command sets up a new or existing repo in this template's format, everything at once: the loop config, the feature pages with criteria and tests, a milestone per feature plus Backlog, the nightly regression in GitHub Actions and the health rules. It first shows what it found, what it would add or convert and what doesn't fit, then applies it on a branch through the usual loop. In an existing repo it adapts what is there instead of overwriting.

- Given SET-1, when the toy adopt-and-update test runs, then it holds. — [adopt-set-1](../../.loop/regression.tsv), both, PASS 2026-11-09, seen failing 2026-11-08
- Given SET-1 with suggest then apply, when the toy adopt-and-update test runs, then it holds. — [adopt-set-2](../../.loop/regression.tsv), both, PASS 2026-11-09, seen failing 2026-11-08
- Given a repo, when setup runs, then it writes the repo half and, outside the repo, the private half. — [setup-both-halves](../../.loop/regression.tsv), both, PASS 2026-11-09, seen failing 2026-11-09

#### SET-2

Every setting in one place. Every setting lives in one of two places: repo settings in the repo's config, committed and shared, and private settings outside the repo, never committed. Setup writes each with a default and a one-line explanation, I can change any of them at any time, and the framework reads them every run. Parallel workers default to unlimited.

- Given every repo and private setting, when the reference is read, then each is listed with its default and a one-line explanation. — [settings-reference](../../.loop/regression.tsv), both, PASS 2026-11-09, seen failing 2026-11-09
- Given parallel is 0, when goals run, then it means unlimited, and it is the default. — [parallel-unlimited](../../.loop/regression.tsv), both, PASS 2026-11-09, seen failing 2026-11-09
- Given a changed setting, when the next run happens, then it takes effect. — [settings-read-fresh](../../.loop/regression.tsv), both, PASS 2026-11-09, seen failing 2026-11-09
- Given the repo settings, when they are read, then criteria_max is a repo setting with default 6 and a one-line explanation. — [criteria-max-setting](../../.loop/regression.tsv), both, PASS 2026-11-09, seen failing 2026-11-09

#### SET-3

Shipped as a versioned package of separate skills in the Agensi format, with a version number, working in Claude Code, Codex and other SKILL.md agents, every script self-contained and under 20 KB.

- Given SET-3, when the toy adopt-and-update test runs, then it holds. — [adopt-set-3](../../.loop/regression.tsv), both, PASS 2026-11-09, seen failing 2026-11-08

#### SET-4

Repos can update: a repo that installed it can check for a newer version, see what's new, and update to get new commands and guidance without losing its own config, criteria, docs or private settings.

- Given SET-4, when the toy adopt-and-update test runs, then it holds. — [adopt-set-4](../../.loop/regression.tsv), both, PASS 2026-11-09, seen failing 2026-11-08

#### SET-5

Carries the design logic: the package explains how the loop and its release step, operation and workers, criteria and tests, regression and health fit together.

- Given SET-5, when the toy adopt-and-update test runs, then it holds. — [adopt-set-5](../../.loop/regression.tsv), both, PASS 2026-11-09, seen failing 2026-11-08
