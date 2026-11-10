<!-- workflow-docs -->
# Setup

Milestone: https://github.com/jcl2018/agent-workflow-template/milestone/9

Review: **Unreviewed**

## Problem

Skill: `workflow-setup`. Adopts a repo into this template's format: loop config, feature pages with criteria and tests, and the regression workflow, printing what it found and would add or convert before writing on a branch. `update.py` brings the skills and the repo's generated files up to a newer template version and proposes local skill fixes back to the template, `.loop/START.md` is the generated entry point every new session reads first, setup wires the same skills into CLAUDE.md and AGENTS.md, and `design-guide.md` explains how the parts fit. `--bare` writes only the config, queue and findings. Setup takes test commands from the repo's CI workflows and scripts (a command that would run zero tests is dropped and reported), proposes feature pages from milestone or track headings or folders with code, follows the repo's version and changelog habit, reports a `.gitignore` line that would block its files with the exact exception, and exits 1 after writing when `agent_command` grants no tools, printing the line to add. Getting started is in the README. Setup writes `review_depth` (`full` by default) with its one-line explanation under `_help` in `.loop/config.json` and refuses an unknown value, and the settings reference lists it beside the private `full_markers`.

## Usage

- `/workflow-setup setup` shows what it found and would add (`--dry-run`), then writes it on a branch, including both scheduled workflows (regression and health, every 4 hours by default; health only when the workflow-health skill is in the repo, since its run needs it); `--bare` writes only the config, queue and findings.
- `/workflow-setup settings` prints every setting with its default and one-line explanation; `/workflow-setup fill-repo` adds any missing repo setting to `.loop/config.json`, such as the Automation settings `health_cron`, `judge_env`, `judge_setup` and `digest_owner`. Every setting is in `skills/workflow-setup/references/settings.md`; `cadence`, the minutes between live-board check-ins, defaults to 30; health reads `test_budget_seconds` (600) and `stale_branch_days` (14).
- `/workflow-setup reply-hook` installs the operation session's reply-format Stop hook into the repo's machine-local `.claude/settings.local.json`, which git is told to ignore (`--remove` takes it out; a second run changes nothing; a committed settings file, or a run from a goal worktree, is refused); `reply_hook: false` in `.loop/config.json` turns it off.

- `/workflow-setup update --check` shows what a newer template version brings and writes nothing (exit 1 means behind, not broken); `/workflow-setup update` applies it: the skills (a skill file edited here is kept as a LOCAL FIX, even when the new version drops it; `--take FILE` takes the package copy), then this repo's missing settings, `template_version`, `.loop/START.md` and the agent blocks, committed on branch `workflow-update-vX` cut from the base branch for you to merge; a run that fails part way leaves no branch behind, so it is safe to rerun. It reads the template's latest GitHub release (`--tag vX` pins one; `--from ZIP|DIR` reads a package instead). A sample check:

      INSTALLED: 0.21.1
      AVAILABLE: 0.22.0
      REPO: template_version 0.21.1, older than 0.22.0: run update --apply
      WHAT'S NEW:
      ## v0.22.0 - 2026-11-12
      - Updates flow both ways.
      update: workflow-setup/scripts/update.py
      LOCAL FIX: workflow-delivery/SKILL.md (kept on apply; --take workflow-delivery/SKILL.md takes the package copy, --propose sends it back)
      PREVIEW: nothing written. Ask for workflow-setup update to apply

- `/workflow-setup update --propose` previews an issue proposing each LOCAL FIX back to the template (the diff and the version it was made on, never the repo's name); `--file-issue` files it once. The live board lists each governed repo whose `template_version` is older than your installed skills, with the fix.
- `/workflow-docs entry` writes `.loop/START.md` (`check` says whether it is stale); `/workflow-setup agents` writes the same workflow-loop block into CLAUDE.md and AGENTS.md (`agent_files` picks the files; `[]` turns it off). Setup does both.

## Requirements

- SET-1: **Reviewed 2026-11-08** One command adopts a repo. One command sets up a new or existing repo in this template's format, everything at once: the loop config, the feature pages with criteria and tests, a milestone per feature plus Backlog, the nightly regression in GitHub Actions and the health rules. It first shows what it found, what it would add or convert and what doesn't fit, then applies it on a branch through the usual loop. In an existing repo it adapts what is there instead of overwriting. <!-- reviewed 260ea1ed -->
- SET-2: **Reviewed 2026-11-08** Every setting in one place. Every setting lives in one of two places: repo settings in the repo's config, committed and shared, and private settings outside the repo, never committed. Setup writes each with a default and a one-line explanation, I can change any of them at any time, and the framework reads them every run. Parallel workers default to unlimited. <!-- reviewed 1008abc4 -->
- SET-3: **Reviewed 2026-11-08** Shipped as a versioned package of separate skills in the Agensi format, with a version number, working in Claude Code, Codex and other SKILL.md agents, every script self-contained and under 20 KB. <!-- reviewed 7c66e31a -->
- SET-4: **Reviewed 2026-11-10** Updates flow both ways: update --check shows what is new in a newer template version and update applies it keeping the repo's config, pages, rules and local settings; the operation board flags any governed repo on an older template version; a template-worthy fix in an adopted repo is proposed back to the template as an issue. <!-- reviewed 218072ee -->
- SET-5: **Reviewed 2026-11-10** A self-describing workspace: every adopted repo has one generated entry point, built from its PRD pages and settings, explaining how the loop, release, operation and workers, docs, regression, health and settings fit together and listing every feature and how to use it; the docs check fails when it is stale. <!-- reviewed fc2ba94a -->
- SET-10: **Reviewed 2026-11-10** The right format for every agent: setup wires the same skills into each agent's entry files (CLAUDE.md and AGENTS.md), so Claude Code and Codex run the same loop the same way. <!-- reviewed a76d3799 -->

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

- Given SET-1, when the toy adopt-and-update test runs, then it holds. — [adopt-set-1](../../.loop/regression.tsv), requirement, guards SET-1, both, PASS 2026-11-10, seen failing 2026-11-08
- Given SET-1 with suggest then apply, when the toy adopt-and-update test runs, then it holds. — [adopt-set-2](../../.loop/regression.tsv), requirement, guards SET-1, both, PASS 2026-11-10, seen failing 2026-11-08
- Given a repo, when setup runs, then it writes the repo half and, outside the repo, the private half. — [setup-both-halves](../../.loop/regression.tsv), requirement, guards SET-1, both, PASS 2026-11-09, seen failing 2026-11-09

#### SET-2

Every setting in one place. Every setting lives in one of two places: repo settings in the repo's config, committed and shared, and private settings outside the repo, never committed. Setup writes each with a default and a one-line explanation, I can change any of them at any time, and the framework reads them every run. Parallel workers default to unlimited.

- Given every repo and private setting, when the reference is read, then each is listed with its default and a one-line explanation. — [settings-reference](../../.loop/regression.tsv), requirement, guards SET-2, both, PASS 2026-11-09, seen failing 2026-11-09
- Given parallel is 0, when goals run, then it means unlimited, and it is the default. — [parallel-unlimited](../../.loop/regression.tsv), requirement, guards SET-2, both, PASS 2026-11-09, seen failing 2026-11-09
- Given a changed setting, when the next run happens, then it takes effect. — [settings-read-fresh](../../.loop/regression.tsv), requirement, guards SET-2, both, PASS 2026-11-09, seen failing 2026-11-09
- Given the repo settings, when they are read, then criteria_max is a repo setting with default 6 and a one-line explanation. — [criteria-max-setting](../../.loop/regression.tsv), requirement, guards SET-2, both, PASS 2026-11-09, seen failing 2026-11-09
- Given a new repo, when setup runs, then it writes review_depth full with a one-line explanation. — [depth-setup](../../.loop/regression.tsv), requirement, guards SET-2, both, not run, seen failing 2026-11-09
- Given the settings reference, when it is generated, then it lists review_depth with its default. — [depth-reference](../../.loop/regression.tsv), requirement, guards SET-2, both, not run, seen failing 2026-11-09
- Given a config that already has its _help explanations, when fill-repo runs, then it fills without error. — [depth-fill-repo-help](../../.loop/regression.tsv), requirement, guards SET-2, both, not run, seen failing 2026-11-09

#### SET-3

Shipped as a versioned package of separate skills in the Agensi format, with a version number, working in Claude Code, Codex and other SKILL.md agents, every script self-contained and under 20 KB.

- Given SET-3, when the toy adopt-and-update test runs, then it holds. — [adopt-set-3](../../.loop/regression.tsv), requirement, guards SET-3, both, PASS 2026-11-10, seen failing 2026-11-08
- Given detail moved out of the workflow-delivery and workflow-docs SKILL.md files, when their references are read, then every moved sentence is there word for word and SKILL.md points to it. — [skill-kept](../../.loop/regression.tsv), requirement, guards SET-3, both, PASS 2026-11-10, seen failing 2026-11-09

#### SET-4

Updates flow both ways: update --check shows what is new in a newer template version and update applies it keeping the repo's config, pages, rules and local settings; the operation board flags any governed repo on an older template version; a template-worthy fix in an adopted repo is proposed back to the template as an issue.

- Given SET-4, when the toy adopt-and-update test runs, then check shows the change, apply keeps the repo's data and lands the repo half on its branch. — [adopt-set-4](../../.loop/regression.tsv), requirement, guards SET-4, both, PASS 2026-11-10, seen failing 2026-11-08
- Given a newer template release, when update --check runs, then it shows the installed and available versions, the repo's version, what is new and each changed file, writes nothing, and never offers a downgrade. — [sync-check-preview](../../.loop/regression.tsv), requirement, guards SET-4, both, not run, seen failing 2026-11-10
- Given an adopted repo, when update applies a newer version, then the skills update, the repo half lands on workflow-update-vX with template_version stamped, and config values, pages and private settings are kept. — [sync-apply-keeps](../../.loop/regression.tsv), requirement, guards SET-4, both, not run, seen failing 2026-11-10
- Given an update from the template's release source archive, when the next default check runs, then it still finds the template through the installed stamp. — [sync-default-source](../../.loop/regression.tsv), requirement, guards SET-4, nightly, not run, seen failing 2026-11-10
- Given a committed template_repo that differs from the installed stamp's repo, when update runs, then it refuses rather than read another repo's releases. — [sync-template-redirect](../../.loop/regression.tsv), requirement, guards SET-4, nightly, not run, seen failing 2026-11-10
- Given a skill file fixed in an adopted repo, when update runs, then it shows as a local fix, is kept, and --propose --file-issue files one issue on the template with its diff and no repo name. — [sync-propose](../../.loop/regression.tsv), requirement, guards SET-4, nightly, not run, seen failing 2026-11-10
- Given a governed repo on an older template version, when the live board renders, then it lists that repo under Issues with the fix. — [sync-board-lag](../../.loop/regression.tsv), requirement, guards SET-4, both, not run, seen failing 2026-11-10

#### SET-5

A self-describing workspace: every adopted repo has one generated entry point, built from its PRD pages and settings, explaining how the loop, release, operation and workers, docs, regression, health and settings fit together and listing every feature and how to use it; the docs check fails when it is stale.

- Given SET-5, when the toy adopt test runs, then the design guide is installed and setup's .loop/START.md holds the opener and every part. — [adopt-set-5](../../.loop/regression.tsv), requirement, guards SET-5, both, PASS 2026-11-10, seen failing 2026-11-08
- Given an adopted repo, when a PRD page's Usage changes, then the entry point check and the docs check fail STALE until docs.py audit regenerates it. — [entry-stale](../../.loop/regression.tsv), requirement, guards SET-5, both, not run, seen failing 2026-11-10
- Given a repo, when setup adopts it, then .loop/START.md holds the first-five-minutes list and every part: loop, release, operation and workers, docs, regression, health, settings and features. — [entry-adopt](../../.loop/regression.tsv), requirement, guards SET-5, both, not run, seen failing 2026-11-10

#### SET-10

The right format for every agent: setup wires the same skills into each agent's entry files (CLAUDE.md and AGENTS.md), so Claude Code and Codex run the same loop the same way.

- Given a repo, when setup or agents.py wire runs, then CLAUDE.md and AGENTS.md hold the same workflow-loop block, text outside it is kept, and a second run changes nothing. — [agents-wire](../../.loop/regression.tsv), requirement, guards SET-10, both, not run, seen failing 2026-11-10
- **not enforced**: no passing test

### Defect tests

- Given the package's skills, when each SKILL.md is counted, then every one is under 150 lines, so test-board passes. — [skill-size-116](../../.loop/regression.tsv), defect, guards [#116](https://github.com/jcl2018/agent-workflow-template/issues/116) state unknown, both, PASS 2026-11-10, seen failing 2026-11-09
