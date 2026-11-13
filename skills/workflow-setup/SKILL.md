---
name: workflow-setup
description: Surveys a git repo and writes its .loop/ config on a branch, so the delivery, monitoring and release skills can run there. Use when a repo has no .loop/config.json, or when asked to set up the workflow.
---

# workflow-setup

One command: `setup`. It finds the repo's base branch, the agent on this machine, then writes
`.loop/` on a branch called `workflow-setup`. Running it again changes nothing.

## Run it

Run `scripts/setup.py` from inside the repo, with `python3`. If the skill's files aren't on disk, write the script to a
temporary file, run it, and delete it.

```bash
python3 scripts/setup.py --dry-run
python3 scripts/setup.py
```

Read the dry run first and tell the user what it found.

## Adoption never blocks

Read the dry run's lines by their prefix: `HEALTH START:` is the health check before anything is written, `add:`, `convert:`,
`skip:` and `no fit:` are the plan (the README, `.gitignore` and the rendered Tests page included), `GAP:` is what setup
cannot fix (a bare `agent_command`, an ignore rule outside the repo) with the fix, `GUARD:` names a repo hook that mentions
`.tsv`, `borrow:`, `adapt:`, `skip:` and `held:` come from `--from`, `would add to <folder>` lists the private half, and
`WOULD FILE:` the issues. The run ends with `ADOPTION VERDICT:` (`GREEN`, or `GAPS` with each FAIL, WARN and UNREAD line
and its fix above it); it exits 0 whenever the adoption is on its branch, and `--strict` exits 3 on gaps.

- A refusal rolls everything back and says `nothing written`: the tree, index, branches and the private folder are as
  before. Codes: `SETUP_REPO_STATE` (merge, rebase, detached HEAD, branch checked out elsewhere), `SETUP_BRANCH_DIVERGED`, `SETUP_WIKI_DIR` (wiki_dir outside the repo),
  `SETUP_MIXED_VERSION` (run update), `SETUP_PRIVATE_NAME`, `SETUP_PRIVATE_VALUE` (a local setting or private value on a
  line the adoption adds), `SETUP_HOOK_REFUSED`, `SETUP_UNEXPECTED` (see the trace file it names), `SETUP_INTERRUPTED`,
  `SETUP_HALF_UNDONE` (exit 4: a restore could not finish, run the commands it prints), `SETUP_PLANNED_PATH_DIRTY` and
  `SETUP_AGENT_FILE_DIRTY` (exit 2: commit or stash that file). A rollback stops a running tool child first and a missing `pkill` never stops the restore; a killed run is rolled back by the next run (`SETUP_RECOVERED`). Exit 1 refuses, 130 interrupted.
- `.tsv` stays the loop's file format. If the repo's `.gitignore` blocks it, setup appends the exact exception lines under
  one comment. If a repo hook rejects tracked `.tsv` files, setup stops cleanly with that hook's output and names the
  exemption to add (`.loop/*.tsv`); it never edits the hook and never uses `--no-verify`.
- What does not fit is one `[adoption]` line per kind in `.loop/findings.md` and, with `gh` signed in and a GitHub
  remote, one issue tagged `health:adoption` (`--no-issues` or `LOOP_NO_ISSUES=1` skips; `--no-health` or
  `LOOP_NO_HEALTH=1` skips the health runs). A step after the commit (git hooks, private settings, issue filing) that
  fails is a `NOTE:` and a gap in the verdict, never a refusal.
- `--from REPO` borrows an adopted repo's portable settings, read-only; `auto_merge`, `full_auto`, `mend` and the other
  unattended or code-running ones stay `held:` until `--allow KEY[,KEY]` names them; a value holding a private value is
  never printed or written. `settings.py show [--repo DIR] [--json]` prints each setting's value, its layer (`default`,
  `repo`, `local`) and its home; a layer wins only where its home is read today (`layers` is the one place to change that).

## After it runs

1. Tell the user that `workflow-monitoring` needs them to allow tools in `agent_command`, because a background agent
   can't answer a permission prompt. For Claude Code, that looks like
   `["claude", "-p", "--allowedTools=Bash,Read,Write,Edit"]`. For Codex, it means `-s workspace-write` with the git
   folder, the remote and `~/.workflow-loop` in `sandbox_workspace_write.writable_roots` (a read-only home leaves the private settings unwritten: setup says so and goes on, and `go` is refused until they exist). They choose the list. You don't.
2. Tell the user to review the branch and merge it. The other skills read the config from the base branch.

Keep to these rules:

- Don't write skill instructions into the repo. `.loop/` holds only the repo's own data. One exception, which SET-5
  and SET-10 require: the generated entry point `.loop/START.md` and the marked workflow-loop block in CLAUDE.md and
  AGENTS.md, rebuilt from the installed skills and the repo's own pages and settings, never edited by hand.
- Don't change `agent_command` to loosen permissions. The user's own settings decide what a
  background agent may do.
- Don't merge the branch. The user does.

## What it writes

| Path | Holds |
|---|---|
| `.loop/config.json` | Every repo setting with its default (`parallel` 0 is unlimited): base branch, checks, agent command, budgets, switches, risky paths, wiki folder |
| `~/.workflow-loop/flow.json`, `health.json`, `repos` | The private settings, outside the repo and never committed, each with a one-line explanation (`_help`); mode 0600 |
| `.loop/queue.md` | An empty goal queue |
| `.loop/findings.md` | An empty findings list |
| `.loop/START.md`, the workflow-loop block in `CLAUDE.md` and `AGENTS.md` | The entry point every new session reads first, and the same skills wired into each agent's entry file (`agent_files`); `template_version` records the version that wrote them |
| `.github/workflows/regression.yml`, `.github/workflows/regression-pr.yml` | A public repo's scheduled regression and its affected-rows run on a pull request or push, when a check command is found; a private repo gets neither (its regression and its health run on the Mac, through the local schedule setup registers outside the repo) |

Every setting, with its default and a one-line explanation, is in `references/settings.md`, generated by `scripts/settings.py reference --write`. You can change any of them at any time; every script reads them fresh on each run. Values already in a config are kept. See `loop-files.md` (`../` here, `shared/` in a pack) for each field.

## Command map

Asking the agent for one of these runs exactly the routine beside it, from the skill's folder. Wiki Usage lines use the left column.

| Ask | Runs |
|---|---|
| `/workflow-setup setup` | `python3 scripts/setup.py` (`--dry-run` previews, `--bare` writes only the config, queue and findings, `--from REPO [--allow KEY]` borrows settings, `--no-health`, `--no-issues`, `--strict`) |
| `/workflow-setup reply-hook` | `python3 scripts/setup.py --reply-hook` (`--remove` takes it out): the operation session's reply-format Stop hook, in the repo's machine-local `.claude/settings.local.json` |
| `/workflow-setup govern-hook` | `python3 scripts/setup.py --govern-hook` (`--remove` takes it out): the operation session's govern-only PreToolUse hook (MON-7), installed beside the reply hook too |
| `/workflow-setup git-hooks` | `python3 scripts/setup.py --git-hooks` (`--remove` takes out only the stubs setup wrote; `--check [--json]` prints the list's and each hook's state): the private-name scan as `pre-commit`, `commit-msg` and `pre-push` hooks in `.git/hooks`; a default `setup` installs them too (`--no-git-hooks` or `LOOP_NO_GIT_HOOKS=1` skips) |
| `/workflow-setup settings` | `python3 scripts/settings.py reference` (`show [--repo DIR] [--json]` gives each value with its layer) |
| `/workflow-setup fill-repo` | `python3 scripts/settings.py fill-repo` |
| `/workflow-setup update --check` | `python3 scripts/update.py --check` (exit 1 means behind) |
| `/workflow-setup update` | `python3 scripts/update.py --apply` (`--take FILE`, `--tag vX`, `--from ZIP\|DIR`, `--template OWNER/NAME`) |
| `/workflow-setup update --propose` | `python3 scripts/update.py --propose` (`--file-issue` files it) |
| `/workflow-setup agents` | `python3 scripts/agents.py wire` (`--dry-run`, `--repo DIR`) |
| `/workflow-setup migration-check` | `python3 scripts/setup.py migration-check` (`--repo DIR`, `--pr` only the gaps a pull request can close, `--offline` skips the published wiki): every gap to the current template with its fix, exit 0 only with none, 1 gaps, 2 usage, 4 could not run; writes nothing; needs workflow-health beside it |

Update's exit codes: 0 done or nothing to do, 1 behind or waiting on you, 2 refused. Every refusal names its code and
fix:

| Code | Means | Fix |
|---|---|---|
| `UPDATE_NO_TEMPLATE` | no template repo known | set `template_repo`, or `--from ZIP\|DIR` |
| `UPDATE_NO_GH`, `UPDATE_GH` | gh missing, or it can't read the template's releases | install gh, `gh auth login`, check the tag |
| `UPDATE_TEMPLATE_MISMATCH` | the installed stamp's repo and `template_repo` differ | `--template OWNER/NAME` |
| `UPDATE_BAD_ARCHIVE` | a member is absolute, has `..`, is a link, is over 20 MB, or fails its hash | use a package from dev/package.py |
| `UPDATE_CHECKOUT` | the skills are a checkout: the skills half is skipped | `git pull` the checkout |
| `UPDATE_SKIPPED_REPO` | the base branch has no `.loop/config.json` | merge the setup branch first |
| `UPDATE_NO_ENTRY` | workflow-docs isn't installed beside workflow-setup | install it |
| `UPDATE_BRANCH_MERGED` | `workflow-update-vX` is merged but the base config is older | delete the branch, run again |
| `UPDATE_PARTIAL` | the skills updated, the repo half didn't | fix the cause, run again (safe) |
| `UPDATE_LOCKED` | another update holds the skills folder | run again when it ends |
| `PROPOSE_SCRUB`, `PROPOSE_GH`, `PROPOSE_NONE` | the proposal names the repo or user; gh failed; nothing to propose | edit the saved file and file it by hand |
| `AGENTS_MARKER`, `AGENTS_OUTSIDE`, `SETUP_AGENT_FILE_DIRTY`, `SETUP_PLANNED_PATH_DIRTY` | a stray block marker; an agent file outside the repo; uncommitted edits to a file setup would change | fix the file, or commit it |

## Command entries

Exact syntax, output and refusals for the asks the sections above don't spell out (moved from the Setup page's retired Usage section).

- `/workflow-setup reply-hook [--remove]` — Adds the operation session's reply-format Stop hook to the repo's machine-local Claude settings (`--remove` takes it out). Prints `HOOK: <added|updated|removed|already installed|not installed>`, plus `NOTE: start a new Claude Code session ... to load it; ...` after an install. Refuses (exit 1) `REFUSED: <script> is missing. Fix: install the workflow-monitoring skill beside workflow-setup`, `REFUSED: the hook's path <script> holds a single quote. ...`, `REFUSED: the hook (<script>) or the repo is inside a goal's worktree, ...`, `REFUSED: .claude/settings.local.json is committed, ...`, `REFUSED: <path> is not valid JSON (<error>); nothing was written. ...` and `REFUSED: <path> has hooks in a shape this can't edit safely; nothing was written. ...`
- `/workflow-setup govern-hook` — Adds the operation session's govern-only PreToolUse hook (MON-7) to the repo's machine-local Claude settings; `reply-hook` adds it too, and `--remove` takes out only it. It refuses edits, commits and pushes in the operation session; `govern_hook: false` turns it off. Prints `HOOK: <added|updated|removed|already installed|not installed> (govern_hook.py)`, plus a `NOTE:` line after an install. Refuses (exit 1) as `reply-hook` does.
- `/workflow-setup git-hooks [--remove | --check [--json]]` — Installs the private-name scan as `pre-commit`, `commit-msg` and `pre-push` hooks in the repo's git hooks folder, each calling workflow-delivery's `private.py hook` by absolute path (a default `setup` run installs them too, after scanning its own staged files; `--no-git-hooks` or `LOOP_NO_GIT_HOOKS=1` skips that). Prints `HOOK <name>: written|removed|not installed|already calls the scan|kept, it is not the stub setup writes|left alone, it is not ours. Add: <call>`, then `list: PRIVATE LIST: ...` and each hook as `installed`, `stale`, `foreign` or `missing`; `--check --json` prints the same with `"version": 1`. A hook that is not ours is never overwritten. Refuses (exit 1) `REFUSED: core.hooksPath is set, ...`, `REFUSED: private.py or the repo is inside a goal's worktree, ...` and `REFUSED: a path holds a quote, newline or percent sign, ...`, each with the line or step to fix; `REFUSED: a staged adoption file holds a private name` stops `setup` before its commit. Exit codes of the hooks: `skills/workflow-delivery/references/commands.md`, "Private-name hooks".
- `/workflow-setup fill-repo` — Adds every missing repo setting to the repo's loop config with its default, never overwriting one already there. Prints `FILLED <repo>/.loop/config.json: <settings added, or "nothing missing">`. Refuses (exit 1) `REFUSED: criteria_max is <value> in <path>. Fix: a whole number from 1 to 50 (default 10).` and `REFUSED: review_depth is <value> in <path>. Fix: full or condensed.`
- `/workflow-setup agents [--dry-run]` — Writes the same workflow-loop block into each file `agent_files` names (CLAUDE.md and AGENTS.md by default), replacing only the block. Prints `WIRED <file>` (or `WOULD WIRE <file>`) per file, or `NO CHANGE: every agent file holds the current block` (exit 0). Refuses (exit 2) `REFUSED: <file> has one workflow-loop marker without the other (AGENTS_MARKER)` and `REFUSED: <file> resolves outside the repo (AGENTS_OUTSIDE)`, each with its fix.
- `/workflow-setup migration-check [--repo DIR] [--pr] [--offline]` — Judges whether a repo is fully migrated to the current template and writes nothing: the working tree's files setup writes, the settings table, the Settings and Automation blocks and README line, the `automation` routines and the one local `<repo>-health-regression` task (4 hours or sooner), a pull-request check, the PRD format and Runbooks, the `template_version`, and the published wiki. Prints one `GAP <CODE> <subject>: <what>. Fix: <one-line fix>` per gap, then `NOT CHECKED:` (always branch protection, which no gh read covers), `CHECKED:` and `DOCS:` lines, and last `MIGRATION OK` or `MIGRATION: N gap(s) (a PR-closable, b state)`, with `(--pr: state codes not checked)` or `(offline: wiki not checked)` after it when a flag skipped part. Exit 0 only with no gap, 1 for gaps, 2 for a usage error, 4 when the check could not run (workflow-health missing, or an unexpected error: the line names a private trace file). Codes, class and cause: `MIG_VERSION`, `MIG_FILES`, `MIG_SETTINGS`, `MIG_BLOCKS`, `MIG_AUTOMATION`, `MIG_RUNBOOK`, `MIG_FORMAT`, `MIG_CHECKS` are PR-closable (`--pr` checks only these, which is the migrate goal's done line); `MIG_TASK`, `MIG_WIKI_ORPHAN`, `MIG_WIKI_STALE`, `MIG_WIKI_UNREADABLE` are state codes that close on the Mac or in the wiki after the merge (`automation.py local install`, then the owner removes each orphan wiki page named and runs `docs.py publish`; the check lists and never deletes). `--offline` skips the three wiki codes; off a Mac the task check prints `SKIP MIG_TASK (not a Mac)` and is not counted. `LOOP_MIGRATION_ONLINE=1` makes health's migration rule read the wiki too (the 4-hourly run sets it); a repo that deliberately differs says so with an explicit off setting (`health_cron`, `regression_cron`, `digest_mail`), and a standing difference is one open issue, not a stream. Unfollowing a repo in `~/.workflow-loop/repos` also drops it from the Issues version lines. Test-only: `LOOP_TEST=1` with `LOOP_INSTALLED_VERSION`, `LOOP_SCHEDULE_PLATFORM` and `LOOP_SCHEDULE_HOME`. Example of a clean run: `NOT CHECKED: branch protection (no gh read)`, `CHECKED: installed v1.0.0, repo template_version 1.0.0 (working tree), platform darwin, mode online`, `MIGRATION OK`. Example of a gap: `GAP MIG_VERSION template_version: none is set (read as 0.0.0), the template is at v1.0.0. Fix: run the migrate goal (update.py --apply stamps it)`. It needs workflow-health beside workflow-setup. `entry.py lag` prints the one version line (`this repo is at vY, the template is at vX, run the migrate goal`) that `goal.py new` and the entry check show; `goal.py new` refuses only when the majors differ, and a `migrate-` slug is let through. A folder named `<repo>-health-regression` under `~/.claude/scheduled-tasks` counts as the repo's local task (no `MIG_TASK` gap), and a `regression_runs: mac` repo is never asked for `pull_request` in `regression.yml`.

## Exact command entries (as of main, 2026-11-13, when the Usage section was retired)

- `/workflow-setup settings` — Shows the settings reference: every setting with its home, default and meaning. Prints the reference as a Markdown table, one `| <setting> | <home> | <default> | <meaning> |` row per setting. Refuses nothing. This repo's `.loop/config.json` holds every setting the reference lists, with `template_version` naming the template it came from; it overrides `criteria_max` to 17 (the default is 10), because the Setup page holds 17 requirements.

- `/workflow-setup setup [--dry-run] [--bare] [--from REPO [--allow KEY[,KEY]]] [--no-health] [--no-issues] [--strict]` — Adopts a new or existing repo without ever blocking: it commits the adoption on a `workflow-setup` branch (never overwriting; it makes the standing `Backlog: <Feature>` and `Backlog: Other` milestones, and asks for no other; `--dry-run` previews every file first, `--bare` writes only the config, queue and findings) with PRD pages in the docs format, the Home table, the README How to use sections, the settings with their defaults and, for a public repo with a check command, the scheduled `regression.yml` and `regression-pr.yml`; health runs on the Mac and no repo gets a health workflow. `--from REPO` borrows an adopted repo's settings shape (read-only; the unattended ones such as `auto_merge` stay `held:` until `--allow` names them). Prints `FOUND: <new|existing> repo, base <base>, ...`, `HEALTH START: <the health check's verdict, or not measured (<why>)>`, one `add:`, `convert:`, `skip:` or `no fit:` line per file, `GAP: <what and its fix>` for what setup cannot fix (a bare `agent_command`, an ignore rule outside the repo), `GUARD: <file> mentions .tsv; ...` when a repo hook might refuse the loop's `.tsv` files, `borrow:`, `adapt:`, `skip:` and `held:` lines, `would add to <private folder>: <keys>`, `WOULD FILE: adoption <kind>: ...`, then `WROTE the adoption on branch <branch> at <sha>` and `NEXT: review the branch, then merge it into <base>; ...`, or `DRY RUN: nothing written`, or `NO CHANGE: nothing to add or convert`, and always ends with `ADOPTION VERDICT: GREEN`, `GAPS (<n> warn, <n> fail, <n> unread, <n> steps failed)` after each FAIL, WARN and UNREAD line of the full health check with its fix, `not measured (<why>)` or `not run (dry run)`. What does not fit is one `[adoption]` line per kind in `.loop/findings.md` and, with `gh` signed in and a GitHub remote, one issue tagged `health:adoption` (`--no-issues` or `LOOP_NO_ISSUES=1` skips; `--no-health` or `LOOP_NO_HEALTH=1` skips the health runs). Exits 0 whenever the adoption is on its branch, 3 with `--strict` when the verdict has gaps. Refuses (exit 1) `REFUSED: git <args>: <error>` and, always rolling back (a failed git call mid-adoption too) so nothing stays written, `REFUSED: ... (SETUP_REPO_STATE)`, `(SETUP_BRANCH_DIVERGED)`, `(SETUP_WIKI_DIR)` (wiki_dir is not a folder inside the repo), `(SETUP_MIXED_VERSION)`, `(SETUP_PRIVATE_NAME)`, `(SETUP_PRIVATE_VALUE)` for a local setting or private value on a line the adoption adds, `(SETUP_HOOK_REFUSED)` when the repo's own commit hook refuses (with the hook's output and the `.loop/*.tsv` exemption to add; setup never edits that hook), `--from <path> is not an adopted repo`; exit 2 for `(SETUP_PLANNED_PATH_DIRTY)` and `(SETUP_AGENT_FILE_DIRTY)`; exit 4 `(SETUP_HALF_UNDONE)` when a restore could not finish; exit 130 when interrupted. A killed run is rolled back by the next one (`SETUP_RECOVERED`). A step after the commit that fails (`git hooks`, `private settings`, `issue filing`) prints `NOTE: <step> failed; ... (SETUP_STEP)` (issue filing: `SETUP_FILING` or `SETUP_NOT_FILED`; a failure after the commit: `SETUP_COMMITTED`; an interrupted run that had committed: `SETUP_RECOVERED`) and counts in the verdict. Under Codex (`-s workspace-write`) the git folder, the remote and `~/.workflow-loop` must be writable roots: with a read-only home setup prints `PRIVATE_NOT_WRITTEN` and still adopts the repo, and `go` is refused until the private settings exist. It installs the local schedule (a launch agent file and registry entry outside the repo; you load it by hand, see the Health page) and, with a check command, writes the scheduled `regression.yml` and `regression-pr.yml` for a public repo only (a private repo's regression runs on the Mac). It records `regression_runs` (`mac` for a private repo or one already recorded `mac`, `actions` for any other public one, left unset when visibility is unreadable) and, once the repo is registered, plans nothing new for the schedule on a rerun; it names, as `BLOCKS: <name> (...)`, every required check or rule no commit status can satisfy; it never edits a ruleset or branch protection. Without `--bare` it also inserts the README's template line and the README's and Home's Settings and Automation blocks into the adoption commit; a later render only refreshes them. The design guide is the last section of `loop-files.md`, the one shared file an install puts in `skills/`.
