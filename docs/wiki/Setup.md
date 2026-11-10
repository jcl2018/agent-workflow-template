<!-- workflow-docs -->
# Setup

Milestone: https://github.com/jcl2018/agent-workflow-template/milestone/9

Review: **Reviewed 2026-11-10** <!-- prd P=7f1b1066 R=a1dcdd47 N=9c385754 M=471a58c6 U=93e20628 -->

## Problem
- I want this toolset to be a workspace I can drop into any repo, for any agent: one install gives Claude Code, Codex or any agent that reads skills the same loop, docs, monitoring and settings, in the right format for each.
- Adopting a repo should never block: it should look at what is there, borrow what fits, learn from a repo I've already set up, and list what doesn't fit instead of refusing.
- Any new session should see the design logic, the docs and every command at once, and an improvement in one repo, or in the template, should reach the others.

## Usage

- `/workflow-setup setup [--dry-run] [--bare]` — Surveys the repo and commits its adoption on a `workflow-setup` branch (`--dry-run` previews it, `--bare` writes only the config, queue and findings); with a check command it writes the scheduled `regression.yml`, and when the workflow-health skill is in the repo also `health.yml` and the by-hand `mail-test.yml`. Prints `FOUND: <new|existing> repo, base <base>, ...`, then `WROTE the adoption on branch <branch> at <sha>` and `NEXT: review the branch, then merge it into <base>; ...`, or `DRY RUN: nothing written`, or `NO CHANGE: nothing to add or convert`. Refuses (exit 1) `REFUSED: git <args>: <error>`, `REFUSED to call this done: agent_command <cmd> grants no tools, ...` and `REFUSED: nothing written. Fix .gitignore, then run setup again.`
- `/workflow-setup reply-hook [--remove]` — Adds the operation session's reply-format Stop hook to the repo's machine-local Claude settings (`--remove` takes it out). Prints `HOOK: <added|updated|removed|already installed|not installed>`, plus `NOTE: start a new Claude Code session ... to load it; ...` after an install. Refuses (exit 1) `REFUSED: <script> is missing. Fix: install the workflow-monitoring skill beside workflow-setup`, `REFUSED: the hook's path <script> holds a single quote. ...`, `REFUSED: the hook (<script>) or the repo is inside a goal's worktree, ...`, `REFUSED: .claude/settings.local.json is committed, ...`, `REFUSED: <path> is not valid JSON (<error>); nothing was written. ...` and `REFUSED: <path> has hooks in a shape this can't edit safely; nothing was written. ...`
- `/workflow-setup settings` — Shows the settings reference: every setting with its home, default and meaning. Prints the reference as a Markdown table, one `| <setting> | <home> | <default> | <meaning> |` row per setting. Refuses nothing.
- `/workflow-setup fill-repo` — Adds every missing repo setting to the repo's loop config with its default, never overwriting one already there. Prints `FILLED <repo>/.loop/config.json: <settings added, or "nothing missing">`. Refuses (exit 1) `REFUSED: criteria_max is <value> in <path>. Fix: a whole number from 1 to 50 (default 10).` and `REFUSED: review_depth is <value> in <path>. Fix: full or condensed.`
- `/workflow-setup update --check [--from ZIP|DIR] [--tag vX] [--template OWNER/NAME]` — Shows what a newer template version brings and writes nothing. Prints `INSTALLED: <v>`, `AVAILABLE: <v>`, `REPO: template_version <v>` (or `..., older than <v>: run update --apply`), the changelog under `WHAT'S NEW:`, an `add:`, `update:` or `remove:` line per skill file, a `LOCAL FIX: <file>` line per skill file edited here, and ends with `UP TO DATE` (exit 0) or `PREVIEW: nothing written. Ask for workflow-setup update to apply` (exit 1, behind). Refuses (exit 2) `REFUSED: no template repo is known (UPDATE_NO_TEMPLATE)`, `REFUSED: gh can't read <repo> releases: <why> (UPDATE_GH)`, `REFUSED: ... (UPDATE_TEMPLATE_MISMATCH)` and `REFUSED: can't read a package at <source>: <why> (UPDATE_BAD_ARCHIVE)`, each with its fix.
- `/workflow-setup update [--take FILE] [--from ZIP|DIR] [--tag vX]` — Applies it: writes the new skills (a local fix is kept and printed `KEPT: <file>`; `--take FILE` takes the package copy), then this repo's missing settings, `template_version`, the entry point and the agent blocks on branch `workflow-update-v<v>` cut from the base branch. Prints `UPDATED skills to <v>`, `WROTE the repo half on branch workflow-update-v<v> at <sha>: <files>` and `NEXT: merge workflow-update-v<v> into <base> ...` (exit 0), or `PENDING: workflow-update-v<v> is not merged into <base>; merge it` (exit 1). Refuses (exit 2) with `UPDATE_SKIPPED_REPO`, `UPDATE_BRANCH_MERGED`, `UPDATE_PARTIAL` or `UPDATE_LOCKED` and the fix; against a checkout it prints `SKILLS: <folder> is a checkout; update it with git pull (UPDATE_CHECKOUT)` and still writes the repo half.
- `/workflow-setup update --propose [--file-issue]` — Previews one issue proposing each local fix back to the template: prints `TITLE: Fix from an adopted repo: <files> (<hash>)`, the diff and `PREVIEW: nothing filed` (exit 0); `--file-issue` files it and prints `FILED: <url>` (exit 0) or `ALREADY FILED: <url>` (exit 1). Prints `NOTHING TO PROPOSE ... (PROPOSE_NONE)` when no skill file differs. Refuses (exit 2) `REFUSED: the proposal holds <kind of match> (PROPOSE_SCRUB)` when it names the repo, its owner, the user or a private pattern, and `REFUSED: gh couldn't file the issue (PROPOSE_GH)`, each saving the draft with the fix.
- `/workflow-setup agents [--dry-run]` — Writes the same workflow-loop block into each file `agent_files` names (CLAUDE.md and AGENTS.md by default), replacing only the block. Prints `WIRED <file>` (or `WOULD WIRE <file>`) per file, or `NO CHANGE: every agent file holds the current block` (exit 0). Refuses (exit 2) `REFUSED: <file> has one workflow-loop marker without the other (AGENTS_MARKER)` and `REFUSED: <file> resolves outside the repo (AGENTS_OUTSIDE)`, each with its fix.

## Requirements

### Functional
- SET-1: **Reviewed 2026-11-10** One command adopts a repo <!-- reviewed 890df4f8 -->
  - One command sets up a new or existing repo: the loop config, PRD feature pages in the docs format, the Home table and README How to use, a milestone per feature plus Backlog, the nightly regression in GitHub Actions, the health groups, and every setting with its default.
  - It shows what it found and would change first, then applies it on a branch through the loop, adapting what is there instead of overwriting.
  - It never blocks: what doesn't fit is listed and filed as issues on the right milestone, and the rest is adopted.
  - Health is the first and last step: before adopting, a health check records where the repo starts; after adopting, the full health check (every group, Adoption included) must come back green or name each gap with its fix, and that verdict is the adoption result, because if health works, the rest works.
- SET-2: **Reviewed 2026-11-10** Layered settings <!-- reviewed 4adab145 -->
  - Settings come in three layers: the template's defaults, the repo's settings (committed and shared), and my local settings (private, outside the repo); a later layer overrides an earlier one.
  - Every setting has a default and a one-line explanation; I can see each setting's value and which layer it came from, and change any of them at any time.
- SET-4: **Reviewed 2026-11-10** Updates flow both ways <!-- reviewed 22b1453a -->
  - An adopted repo can check for a newer template version, see what's new and update, keeping its own config, pages, rules and local settings.
  - The operation session flags any governed repo running an older template version.
  - A fix made in an adopted repo that belongs in the template is proposed back to the template as an issue.
- SET-5: **Reviewed 2026-11-10** A self-describing workspace <!-- reviewed 5cce9f58 -->
  - Every adopted repo has one entry point that any new session reads first: how the loop, release, operation and workers, docs, regression, health and settings fit together, and which features exist and how to use them.
  - It is generated from the PRD pages and settings, so it is never stale.
- SET-6: **Reviewed 2026-11-10** Adoption is proven <!-- reviewed 48224f33 -->
  - Adoption is proven on test repos shaped like real ones (existing checks, CI tests, a blocking .gitignore, a bare agent command, features that aren't folders), and every adoption defect found in a real repo adds a test repo that reproduces it.
- SET-9: **Reviewed 2026-11-10** Learn from a repo already set up <!-- reviewed c1f9b120 -->
  - Setup can take an adopted repo as its model: it borrows that repo's settings shape, flow, milestone layout and private rules (never private values) and adapts them to the new repo.
- SET-10: **Reviewed 2026-11-10** The right format for every agent <!-- reviewed 06345b05 -->
  - The same skills are wired into each agent's own entry files (for example CLAUDE.md and AGENTS.md), so Claude Code, Codex and other SKILL.md agents run the same loop the same way.

### Non-functional
- SET-3: **Reviewed 2026-11-10** Versioned, portable package <!-- reviewed c120e2e9 -->
  - Shipped as a versioned package of separate skills in the Agensi format, every script self-contained and under 20 KB. It works out of the box with a built-in default flow, and is proven to run in both Claude Code and Codex on a clean test repo with no private settings.
- SET-7: **Reviewed 2026-11-10** Safe and repeatable <!-- reviewed fb39932b -->
  - A dry run lists everything before any write; running setup twice changes nothing the second time; nothing existing is overwritten.
- SET-8: **Reviewed 2026-11-10** Private stays private <!-- reviewed 22a16ae7 -->
  - Local settings and private values are never written into the repo, and setup refuses to commit a file that holds one.

## Non-goals
- It never commits private settings or values.
- An update never overwrites a repo's own config, requirements, docs or local settings.
- It doesn't rewrite a page that has its own sections; that page is listed for a person.

## Success metrics
- One command adopts a fresh or existing repo with no blocking step, and the health check run right after it is green or names every gap with its fix.
- A new session in an adopted repo can name every feature and how to use it from the entry point alone.
- A template update reaches every governed repo without losing any repo setting or page.

## Tests

| Test | Kind | Guards | Checks | Last result |
|---|---|---|---|---|
| [adopt-set-1](Tests#t-adopt-set-1) | requirement | SET-1 | Given SET-1, when the toy adopt-and-update test runs, then it holds. | PASS 2026-11-10 |
| [adopt-set-2](Tests#t-adopt-set-2) | requirement | SET-1 | Given SET-1 with suggest then apply, when the toy adopt-and-update test runs, then it holds. | PASS 2026-11-10 |
| [setup-both-halves](Tests#t-setup-both-halves) | requirement | SET-1 | Given a repo, when setup runs, then it writes the repo half and, outside the repo, the private half. | PASS 2026-11-10 |
| [settings-reference](Tests#t-settings-reference) | requirement | SET-2 | Given every repo and private setting, when the reference is read, then each is listed with its default and a one-line explanation. | PASS 2026-11-10 |
| [parallel-unlimited](Tests#t-parallel-unlimited) | requirement | SET-2 | Given parallel is 0, when goals run, then it means unlimited, and it is the default. | PASS 2026-11-10 |
| [settings-read-fresh](Tests#t-settings-read-fresh) | requirement | SET-2 | Given a changed setting, when the next run happens, then it takes effect. | PASS 2026-11-10 |
| [criteria-max-setting](Tests#t-criteria-max-setting) | requirement | SET-2 | Given the repo settings, when they are read, then criteria_max is a repo setting with default 10 and a one-line explanation. | PASS 2026-11-10 |
| [depth-setup](Tests#t-depth-setup) | requirement | SET-2 | Given a new repo, when setup runs, then it writes review_depth full with a one-line explanation. | PASS 2026-11-10 |
| [depth-reference](Tests#t-depth-reference) | requirement | SET-2 | Given the settings reference, when it is generated, then it lists review_depth with its default. | PASS 2026-11-10 |
| [depth-fill-repo-help](Tests#t-depth-fill-repo-help) | requirement | SET-2 | Given a config that already has its _help explanations, when fill-repo runs, then it fills without error. | PASS 2026-11-10 |
| [adopt-set-4](Tests#t-adopt-set-4) | requirement | SET-4 | Given SET-4, when the toy adopt-and-update test runs, then check shows the change, apply keeps the repo's data and lands the repo half on its branch. | PASS 2026-11-10 |
| [sync-check-preview](Tests#t-sync-check-preview) | requirement | SET-4 | Given a newer template release, when update --check runs, then it shows the installed and available versions, the repo's version, what is new and each changed file, writes nothing, and never offers a downgrade. | not run |
| [sync-apply-keeps](Tests#t-sync-apply-keeps) | requirement | SET-4 | Given an adopted repo, when update applies a newer version, then the skills update, the repo half lands on workflow-update-vX with template_version stamped, and config values, pages and private settings are kept. | not run |
| [sync-default-source](Tests#t-sync-default-source) | requirement | SET-4 | Given an update from the template's release source archive, when the next default check runs, then it still finds the template through the installed stamp. | not run |
| [sync-template-redirect](Tests#t-sync-template-redirect) | requirement | SET-4 | Given a committed template_repo that differs from the installed stamp's repo, when update runs, then it refuses rather than read another repo's releases. | not run |
| [sync-propose](Tests#t-sync-propose) | requirement | SET-4 | Given a skill file fixed in an adopted repo, when update runs, then it shows as a local fix, is kept, and --propose --file-issue files one issue on the template with its diff and no repo name. | not run |
| [sync-board-lag](Tests#t-sync-board-lag) | requirement | SET-4 | Given a governed repo on an older template version, when the live board renders, then it lists that repo under Issues with the fix. | not run |
| [adopt-set-5](Tests#t-adopt-set-5) | requirement | SET-5 | Given SET-5, when the toy adopt test runs, then the design guide is installed and setup's .loop/START.md holds the opener and every part. | PASS 2026-11-10 |
| [entry-stale](Tests#t-entry-stale) | requirement | SET-5 | Given an adopted repo, when a PRD page's Usage changes, then the entry point check and the docs check fail STALE until docs.py audit regenerates it. | not run |
| [entry-adopt](Tests#t-entry-adopt) | requirement | SET-5 | Given a repo, when setup adopts it, then .loop/START.md holds the first-five-minutes list and every part: loop, release, operation and workers, docs, regression, health, settings and features. | not run |
| - | requirement | SET-6 | no passing test | not enforced |
| - | requirement | SET-9 | no passing test | not enforced |
| [agents-wire](Tests#t-agents-wire) | requirement | SET-10 | Given a repo, when setup or agents.py wire runs, then CLAUDE.md and AGENTS.md hold the same workflow-loop block, text outside it is kept, and a second run changes nothing. | not run |
| - | requirement | SET-10 | no passing test | not enforced |
| [adopt-set-3](Tests#t-adopt-set-3) | requirement | SET-3 | Given SET-3, when the toy adopt-and-update test runs, then it holds. | PASS 2026-11-10 |
| [skill-kept](Tests#t-skill-kept) | requirement | SET-3 | Given detail moved out of the workflow-delivery and workflow-docs SKILL.md files, when their references are read, then every moved sentence is there word for word and SKILL.md points to it. | PASS 2026-11-10 |
| - | requirement | SET-7 | no passing test | not enforced |
| - | requirement | SET-8 | no passing test | not enforced |
| [skill-size-116](Tests#t-skill-size-116) | defect | [#116](https://github.com/jcl2018/agent-workflow-template/issues/116) closed (2026-11-10) | Given the package's skills, when each SKILL.md is counted, then every one is under 150 lines, so test-board passes. | PASS 2026-11-10 |
