<!-- workflow-docs -->
# Setup

Milestone: https://github.com/jcl2018/agent-workflow-template/milestone/9

Review: **Unreviewed**

## Problem

Skill: `workflow-setup`. Adopts a repo into this template's format: loop config, feature pages with criteria and tests, and the regression workflow, printing what it found and would add or convert before writing on a branch. `update.py` refreshes only the skills from a newer package, and `design-guide.md` explains how the parts fit. `--bare` writes only the config, queue and findings. Setup takes test commands from the repo's CI workflows and scripts (a command that would run zero tests is dropped and reported), proposes feature pages from milestone or track headings or folders with code, follows the repo's version and changelog habit, reports a `.gitignore` line that would block its files with the exact exception, and exits 1 after writing when `agent_command` grants no tools, printing the line to add. Getting started is in the README. Setup writes `review_depth` (`full` by default) with its one-line explanation under `_help` in `.loop/config.json` and refuses an unknown value, and the settings reference lists it beside the private `full_markers`.

## Usage

- `/workflow-setup setup` shows what it found and would add (`--dry-run`), then writes it on a branch; `--bare` writes only the config, queue and findings.
- `/workflow-setup settings` prints every setting with its default and one-line explanation; `/workflow-setup fill-repo` adds any missing repo setting to `.loop/config.json`. Every setting is in `skills/workflow-setup/references/settings.md`; `cadence`, the minutes between live-board check-ins, defaults to 30; health reads `test_budget_seconds` (600) and `stale_branch_days` (14).
- `/workflow-setup reply-hook` installs the operation session's reply-format Stop hook into the repo's machine-local `.claude/settings.local.json`, which git is told to ignore (`--remove` takes it out; a second run changes nothing; a committed settings file, or a run from a goal worktree, is refused); `reply_hook: false` in `.loop/config.json` turns it off.

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

| Test | Kind | Guards | Checks | Last result |
|---|---|---|---|---|
| [adopt-set-1](Tests#t-adopt-set-1) | requirement | SET-1 | Given SET-1, when the toy adopt-and-update test runs, then it holds. | PASS 2026-11-10 |
| [adopt-set-2](Tests#t-adopt-set-2) | requirement | SET-1 | Given SET-1 with suggest then apply, when the toy adopt-and-update test runs, then it holds. | PASS 2026-11-10 |
| [setup-both-halves](Tests#t-setup-both-halves) | requirement | SET-1 | Given a repo, when setup runs, then it writes the repo half and, outside the repo, the private half. | PASS 2026-11-09 |
| [settings-reference](Tests#t-settings-reference) | requirement | SET-2 | Given every repo and private setting, when the reference is read, then each is listed with its default and a one-line explanation. | PASS 2026-11-09 |
| [parallel-unlimited](Tests#t-parallel-unlimited) | requirement | SET-2 | Given parallel is 0, when goals run, then it means unlimited, and it is the default. | PASS 2026-11-09 |
| [settings-read-fresh](Tests#t-settings-read-fresh) | requirement | SET-2 | Given a changed setting, when the next run happens, then it takes effect. | PASS 2026-11-09 |
| [criteria-max-setting](Tests#t-criteria-max-setting) | requirement | SET-2 | Given the repo settings, when they are read, then criteria_max is a repo setting with default 10 and a one-line explanation. | PASS 2026-11-09 |
| [depth-setup](Tests#t-depth-setup) | requirement | SET-2 | Given a new repo, when setup runs, then it writes review_depth full with a one-line explanation. | not run |
| [depth-reference](Tests#t-depth-reference) | requirement | SET-2 | Given the settings reference, when it is generated, then it lists review_depth with its default. | not run |
| [depth-fill-repo-help](Tests#t-depth-fill-repo-help) | requirement | SET-2 | Given a config that already has its _help explanations, when fill-repo runs, then it fills without error. | not run |
| [adopt-set-3](Tests#t-adopt-set-3) | requirement | SET-3 | Given SET-3, when the toy adopt-and-update test runs, then it holds. | PASS 2026-11-10 |
| [skill-kept](Tests#t-skill-kept) | requirement | SET-3 | Given detail moved out of the workflow-delivery and workflow-docs SKILL.md files, when their references are read, then every moved sentence is there word for word and SKILL.md points to it. | PASS 2026-11-10 |
| [adopt-set-4](Tests#t-adopt-set-4) | requirement | SET-4 | Given SET-4, when the toy adopt-and-update test runs, then it holds. | PASS 2026-11-10 |
| [adopt-set-5](Tests#t-adopt-set-5) | requirement | SET-5 | Given SET-5, when the toy adopt-and-update test runs, then it holds. | PASS 2026-11-10 |
| [skill-size-116](Tests#t-skill-size-116) | defect | [#116](https://github.com/jcl2018/agent-workflow-template/issues/116) closed (2026-11-10) | Given the package's skills, when each SKILL.md is counted, then every one is under 150 lines, so test-board passes. | PASS 2026-11-10 |
