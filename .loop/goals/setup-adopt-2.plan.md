# Plan: setup-adopt-2

Goal file: `.loop/goals/setup-adopt-2.md` (frozen done lines 1 to 8). Design file: `.loop/goals/setup-adopt-2.design.md` (Approach B, approved). This plan meets the done lines as written and does not change them. Nothing here is approved by the owner, merged or pushed.

Privacy note: this file was scrubbed before commit: local absolute paths became repo-relative paths, review-tool names were replaced by a generic phrase, the tool's restore-point comment line was removed (the restore copy stays in the git-excluded scratch folder), and no owner name or email appears. Status: NOT APPROVED; the final approval gate is pending (decisions uc1, uc2, d1 to d4 and the plan approval).

Hard limits carried into every part: every script under 20,480 bytes (health warns at 18,432); `skills/*/SKILL.md` under 150 lines; `python3 skills/workflow-docs/scripts/docs.py check` prints DOCS OK; no private names, paths or emails in any commit or the PR body; milestones are free form (setup makes and asks for none); Reviewed lines of `docs/wiki/Setup.md` (SET-2, 3, 4, 5, 6, 7, 8, 9, 10) are not edited, SET-1 stays Unreviewed text and is not reworded; only Usage, Tests and Unreviewed text change there; the ci-minutes-template goal edits the same setup files next, so touches stay inside `skills/workflow-setup`, `skills/workflow-health`, `dev/toy`, `.loop/regression.tsv`, `docs/wiki/Setup.md`.

## Implementation plan

### 0. Package file count and sizes (decided first, it shapes every part)

Measured on main: `git ls-files skills | wc -l` is 96, and `dev/package.py` also ships `listing.json`, `README.md` and `LICENSE`, so the package holds 99 files and its limit is 99 (`MAX_FILES`, `dev/package.py` line 26). The package has no free slot: this plan adds ZERO new tracked files under `skills/`. The approved design (which names new `adopt.py`, `borrow.py`, `homewrite.py`, `hooks.py`, `layers.py`, `adoptrules.py` and `references/adoption.md`) is overridden on file placement only: this plan wins, and the design's behavior is unchanged. In every part below a design module name means the function block placed in the host file named here; the map is `adopt.py` Txn and rollback to `sync.py`, `adopt.py` guard_staged to `update.py`, `adopt.py` private-value check to `settings.py`, `adopt.py` health start and verdict to `agents.py`, `adopt.py` findings lines to `seed.py`, `adopt.py` filing to `setup.py`, `borrow.py` to `survey.py`, `homewrite.py` to `seed.py`, `hooks.py` to `agents.py`, `layers.py` to `settings.py`, `adoptrules.py` to `report.py` (rules) and `controls.py` (controls). The new toy scripts in `dev/toy` are not packaged.

Room: the seven setup scripts hold about 33,000 bytes of room up to the 18,432-byte warning line, and the design's setup-side additions are about 25,000 bytes (Txn 3.0 KB, `guard_staged` 2.0, `private_value` 0.8, health start and verdict 1.5 (`agents.py`), findings line writer 1.0 (`seed.py`), filing call 0.7 (`setup.py`), borrow 4.0, Home and README writer 2.5, `.gitignore` convert and Tests.md listing 1.5, survey proof and guards 3.5, layers 2.0, `setup.py` wiring 2.5). So the total fits but each host ends within about 6% of the line (agents.py 2.8%, update.py 3.1%, rules.py 3.7%); placement is the work. Starting allocation, with arithmetic (bytes; the audit may move a block to another host in this table, never to a new file):

| Host (existing file) | Receives | Now | Moves in/out | Adds | Target |
|---|---|---|---|---|---|
| `scripts/setup.py` | wiring, flags, filing call | 17,243 | -4,892 (`reply_hook`, `HOOKS`) | 2,500 + 700 | about 15,550 (leaves about 2,900 for the next goal, which may move a block out) |
| `scripts/agents.py` | `reply_hook`, `HOOKS`, seed's `git_hooks` cluster (`hook_state`, `hooks_dir`, `list_state`, `git_hooks`), `health()` start and verdict | 8,023 | +4,892, +3,500 | 1,500 | about 17,915 |
| `scripts/seed.py` | Home and README writer, `.gitignore` convert, Tests.md listing, findings line writer | 15,250 | -3,500 | 2,500 + 1,500 + 1,000 | about 16,750 |
| `scripts/survey.py` | 119 proof, `.tsv` guards, ignore source, borrow block | 9,968 | 0 | 3,500 + 4,000 | about 17,470 |
| `scripts/settings.py` | `resolve()`, `show`, `private_value` | 14,833 | 0 | 2,000 + 800 | about 17,630 |
| `scripts/sync.py` | `Txn`, rollback, journal and recovery | 14,412 | 0 | 4,000 | about 18,410 (at the line; the journal and recovery helpers move to `seed.py` first if measured over) |
| `scripts/update.py` | `guard_staged` | 15,870 | 0 | 2,000 | about 17,870 |
| `workflow-health/scripts/file.py` | `--open-only` (additive filing) | 13,459 | 0 | 300 | about 13,760 |
| `workflow-health/scripts/report.py`, `controls.py`, `rules.py` | `no-fit` and `agent-tools` rule functions, their controls, registration lines | 14,309 / 12,641 / 17,455 | 0 | 1,600 / 1,200 / 300 | 15,900 / 13,840 / 17,755 |
| `workflow-setup/SKILL.md` | "Adoption" paragraph and one line per new flag | 86 lines | 0 | about 30 lines | about 116 lines (under 150) |
| `workflow-setup/references/settings.md` | "Layers" section | 7,627 bytes | 0 | about 1,200 bytes | about 8,800 bytes |
| `workflow-health/references/commands.md` | rule table rows for `no-fit`, `agent-tools` | 17,820 bytes | 0 | about 400 bytes | about 18,200 bytes |

DX additions (parts 1, 2, 7, 10 and 14, about 1,300 bytes: `--strict`, exit codes, trace line, error codes, hook-output redaction, `show` masking, aliases) land in `setup.py` (to about 16,100, still leaving about 2,300 for the next goal), `settings.py` (to about 17,900) and `seed.py` (to about 16,950); the audit re-measures them.

Import graph, so no cycle appears: `settings.py` imports none of the setup scripts and holds `private_value`; `survey.py`, `sync.py`, `update.py`, `seed.py` and `setup.py` import `settings`; `setup.py` imports all of them; `seed.py` and `setup.py` import `agents` for `git_hooks` and `health`. `update.py` already imports `sync`; `guard_staged` takes the repo path and is called by `setup.py`, which imports `update` for it (a one-line import).

Order: capacity audit first, then the pure moves (part 1), then `Txn` (the largest block, built and measured first), then the rest of the behavior. Capacity audit (the first build commit, before any behavior change): run `python3 dev/package.py` and record the real file count, `wc -c` of every host above, and the table with real numbers in the commit message. Per-file rule: a host's measured result must be at or under 18,432 bytes at every commit. If a host would pass it, apply the levers in order: (1) shorten the host's own module docstring and comments (code comments and docstrings only; Usage text in `docs/wiki` and SKILL.md is not trimmed); (2) move the smallest block that brings the file under the line to another host in this table that has room, never a new file; (3) halt at the last green commit (the audit commit or a later one; every earlier commit stays and must still pass the gate list): write the failing host, its measured bytes and the file list to `.loop/goals/setup-adopt-2.halt.md` (not `.loop/findings.md`, which the `no-fit` rule reads), make the commit message start with `Capacity halt:`, report it to the owner as "the done lines do not fit the 99-file cap" and exit. The owner's options and the resume action for each: (a) free a packaged file elsewhere in the package by merging two shipped files, then resume from the halt commit; (b) accept a host above 18,432 and under 20,480 (health `size` warns), then resume; (c) cut a block from the done lines through a new goal. A resumed run finds its state by the `Capacity halt:` commit and the halt file, which it deletes in its first commit. A halt resolution amends the gate list in that same commit: under (a) the file count becomes the new measured value, under (b) the accepted host's ceiling becomes 20,479 bytes; placement stays as in this part after a resume.

Gate list (the one place the checks are stated; later parts refer to it): at every commit that touches `skills/`, `python3 dev/package.py` prints no file-count failure (99), `wc -c` of every script is under 20,480 and at or under 18,432 so the health `size` rule does not warn, and `git ls-files skills | wc -l` stays 96.

### 1. Step zero: pure move for size (no behavior change)

Move `HOOKS` and `reply_hook()` from `setup.py` into `agents.py` and move seed's `git_hooks` cluster there too (names kept; `setup.py` imports them and keeps the `--reply-hook` and `--govern-hook` dispatch and the shared `refuse()`). Run the existing reply-hook and size rows before and after; the output of `setup.py --reply-hook` on a toy repo must be identical. Each moved name stays importable from its old module as a one-line alias (`seed.git_hooks`, `setup.reply_hook`, `setup.HOOKS`), because the updater keeps a locally edited file on its own (`update.py` LOCAL FIX) and an old `setup.py` beside a new `seed.py` must still import. `setup-fit` (nightly) also runs the previous release's `setup.py` (taken from local git history, no network) against the new `seed.py` and `agents.py` and expects it to work, keeps the old `seed.decide` and `seed.apply` call signatures as a contract, and runs the new `setup.py` against a retained old `agents.py` and expects the `(SETUP_MIXED_VERSION)` refusal. Commit this move alone so a later regression bisects cleanly.

### 2. Transaction and rollback so a refusal leaves nothing written (issue 120)

In `sync.py`, `Txn(repo, plan_paths)` (its `guard_staged` sits in `update.py`, `private_value` in `settings.py`; part 0):
- Before any write it records HEAD, the current branch, whether the `workflow-setup` branch exists, and for every path setup will write (config, queue, findings, pages, `docs.tsv`, rows, workflows, START.md, agent files, `.gitignore`, rendered `docs/wiki/Tests.md`) its prior bytes or absence. An untracked or ignored working-tree config is read first and counted as prior bytes (it is never overwritten; this closes inventory item 4).
- Run order in `setup.py`: plan, health start, write files, stage, scans and guards, commit, then only after a successful commit: git hooks, private settings (`fill_private` moves here, so a dry run and a refusal write nothing under the home folder), issue filing, health verdict. Hooks setup installs never run on its own commit (today's `hooked()` already runs after the commit). A failure in any step after the commit (hooks, private settings, filing, verdict) prints `NOTE: <step> failed (<reason>); the adoption is committed on the branch. Fix: <command>` and does not change the exit code (0); the verdict line still prints last and counts each failed post-commit step as one gap (`ADOPTION VERDICT: GAPS (<n> fail, <m> warn, <u> unread, <k> steps failed)`), so a missing private half or hook is never reported GREEN. Setup's own commit runs before the hooks it installs on purpose: those hooks scan staged text for private names, and setup's pre-commit scan and `guard_staged` already do that job on the same text.
- Prechecks (refuse before any write, exit 1, nothing written, each with a code): a merge, rebase or cherry-pick in progress, a detached or unborn HEAD, and a `workflow-setup` branch checked out in another worktree (`(SETUP_REPO_STATE)`); the setup branch existing with commits the current HEAD lacks (`(SETUP_BRANCH_DIVERGED)`, so the plan, the snapshot and the apply all describe one revision; Fix: switch to that branch or delete it); a planned path that already exists and has staged or unstaged changes, the same rule setup keeps today for agent files (`(SETUP_PLANNED_PATH_DIRTY)`, exit 2); the installed setup modules being mixed versions, found by checking that `agents` has `health`, `git_hooks` and `reply_hook` (`(SETUP_MIXED_VERSION)`, Fix: run update). Each has a fixture inside `setup-refusal-writes-120`.
- Write set and snapshot: before any write `Txn` snapshots every existing file under the folders setup writes into (`.loop`, the wiki folder, `.github/workflows`, the agent files, `.gitignore`, `README.md`), with bytes, mode and symlink target, because `criteria.py render` rewrites existing feature pages beyond the planned ones. After the writes, the write set is the files whose bytes changed against the snapshot; setup stages exactly those files (`git add -- <files>`, never a folder) and commits exactly those; a changed file that was dirty against HEAD before the run rolls the adoption back with `(SETUP_PLANNED_PATH_DIRTY)`. Rollback compares per-file content hashes, not status flags.
- Journal and interruption: before the first write `Txn` writes a journal in the git dir (`workflow-setup-txn.json`: branch, HEAD, whether the setup branch existed, the index tree, and a snapshot folder beside it). The next setup run finds a journal first, rolls back from it (`NOTE: recovered an interrupted adoption (SETUP_RECOVERED)`) and then continues; a hard kill (SIGKILL) therefore leaves recoverable state. A signal handler first terminates and reaps any running child (git, hooks) in its process group, then reconciles the ref: if the branch tip moved to a commit that holds the write set, the adoption counts as committed and no rollback runs; otherwise rollback runs. Row `setup-refusal-writes-120` covers a kill during a blocking hook and one after the ref update, and a SIGKILL recovered by the next run.
- Index and staging: `Txn` records the index tree (`git write-tree`) before any write. Setup stages only its plan paths (`git add -- <paths>`; today `setup.py` line 284 uses `git add -A -- <paths>` and line 290 commits the whole index) and commits only them (`git commit --allow-empty -m ... -- <paths>`; the first test proves `--allow-empty` with paths works), so the owner's other staged work is never committed. Rollback restores the index from the recorded tree (`git read-tree`) after unstaging, so a partially staged file keeps its separate HEAD, index and working versions. Fixtures in `setup-refusal-writes-120`: a pre-staged unrelated change (kept staged, never committed), a dirty planned path (refused), and a dirty unrelated file (untouched).
- `Txn.rollback()` on every refusal after the first write: unstage, restore or delete each path, switch back to the original branch, delete the setup branch if this run created it, then a sweep for any file other tools wrote (for example `criteria.py render`): the sweep compares per-file content hashes against the snapshot and restores or deletes only files that differ from it, never the owner's own dirty or untracked files outside the snapshot. The span from the first write to the commit runs inside a handler for any exception and for interrupt and terminate signals, which calls `Txn.rollback()` and re-raises with exit 130 for an interrupt. If a restore step fails it keeps going and prints `REFUSED: could not restore <paths> (<error>); the adoption is half undone. Fix: git status, then git checkout -- <paths>, git switch <original branch>, git branch -D <setup branch>` and exits 4; the message also says `Side effects: partial. Do not rerun setup until restored.`
- Errors (agent-ready): every `REFUSED:` and `NOTE:` line ends with a stable code in parentheses, the convention setup already uses (`(SETUP_AGENT_FILE_DIRTY)` at `setup.py` line 272; new ones are `(SETUP_PRIVATE_VALUE)`, `(SETUP_HOOK_REFUSED)`) that names an anchor on the Setup page, and says `nothing written` when that is true; the wording before the code is unchanged, so existing greps still match. An unexpected exception between the first write and the commit rolls back and prints `REFUSED: unexpected failure in <step> (<ExceptionName>); rolled back, nothing written. Trace: <path in the git dir>. Fix: rerun with --dry-run, then report the trace (SETUP_UNEXPECTED)`; the trace file holds the traceback with every value passed through `settings.private_value`. Hook output relayed after a refused commit (part 4) goes through the same masking, line by line (`[line withheld: holds a private value]`).
- Remaining refusals keep their `REFUSED:` wording and exit codes: not a git repo, a dirty agent file, a private name, a SET-8 local setting or private value, the repo's own commit hook refusing. The bare `agent_command` and the `.gitignore` conflict stop being refusals (parts 3 and 4).
- Also covered by row `setup-refusal-writes-120`: rollback when the `workflow-setup` branch already existed before the run (it is switched back to and never deleted).
- Row `setup-refusal-writes-120` triggers each remaining REFUSED path in `dev/toy/test-setup-adopt.sh` and also kills the process between the first write and the commit and asserts the same unchanged state; compares a full tree hash (tracked and working file bytes, `git branch`, `git stash list`, the index tree via `git write-tree`) plus a hash of the private home folder, before and after. Seen failing by `regression.py red setup-refusal-writes-120 --break "<restore old code>"` (part 12).

### 3. Never blocks, gaps filed as issues (SET-1, done line 1)

`setup.py` collects gaps in a list instead of refusing: a bare `agent_command` (`GAP: agent_command ... grants no tools. Fix: "agent_command": [...]`), pages with their own sections, unproven checks, a `.tsv` guard note, a source-ignored path. `seed.py` writes one line per kind (the kinds are fixed at four: pages with their own sections, no check command found, `.tsv` guard note, ignored path; so the file never passes the five-line limit health's findings rule warns on) to `.loop/findings.md` as `- [adoption] <kind>: <subject, subject, ...>. Fix: <fix>`; a rerun rewrites a line only when its subjects change, deletes a kind's line when its last subject is gone, and never touches a line that lacks the `[adoption]` tag; an owner marks a line fixed with the existing `[closed]` convention. Setup exits 0 whenever the adoption is on its branch.

Health side (in `report.py`, registered in `rules.py`, controls in `controls.py`, rule table in `skills/workflow-health/references/commands.md`): Adoption rule `no-fit` turns each such findings line into one WARN row naming the subjects and the fix; Adoption rule `agent-tools` WARNs on a bare agent command and names its fix line; it names every setting that holds an agent command (the repo `agent_command` and the private flow command) in its fix line, since fixing one leaves a Codex-only repo broken at delivery; it alone owns that gap: setup does not write an `agent_command` findings line and `no-fit` ignores that kind, so one gap files one issue. Each rule has a negative control (a fixture that must not fire), as every rule must. Existing `health.py file --group adoption` then files one issue per row with the group tag and, when a page owns the path, the feature (health's own longest-prefix rule; the `feature:<Page>` label only when `feature_labels` is on). Setup runs that filing itself, only for this run's own adoption findings and only to open or link (new `health.py file --open-only`, `file.py`: it never closes, reopens or updates an issue, because the plain command reconciles the whole group and could close an issue on an unmerged branch), against the repo named by `origin` (`GH_REPO` is set from the remote, so a fork never files upstream), when `gh` is signed in and the repo has a GitHub remote; every issue title and body passes `settings.private_value` and an issue that fails is skipped with a NOTE; the target repo and the labels the first filing creates (`health`, `health:adoption`) are printed before filing, and the dry run shows them in `WOULD FILE`; otherwise it prints `NOTE: N items left in .loop/findings.md; file them with workflow-health file --group adoption`. A filing that stops part way prints `NOTE: filing failed after N of M issues; run workflow-health file --group adoption --open-only to finish, marks dedupe (SETUP_FILING)` and the verdict counts it; a second setup run (`NO CHANGE`) does no GitHub write. A step's outcome is read from its output (a `FAILED` or `REFUSED` line) as well as its exit status, because `report.py` and `seed.git_hooks` return 0 on failure today. `--no-issues` or `LOOP_NO_ISSUES=1` skips; the dry run prints `WOULD FILE`. Health's marks dedupe a second run. No label, milestone or issue is created by any test except through `dev/toy/fakegh`.

Rows: `set1-never-blocks` (bare agent plus `*.tsv` ignored: exit 0, adoption committed, `GAP:` lines, findings written; also a step made to fail after the commit gives exit 0, a `NOTE: <step> failed` line, the commit kept and the verdict line last; no `gh` gives the `NOTE: N items left` line; `--no-issues` files nothing), `set1-no-fit-filed` (two pages with their own sections give one findings line listing both and one filed issue tagged `adoption` through the stand-in; the filed count equals the `WOULD` lines of `health.py preview --group adoption`; a second run files none).

### 4. The `.tsv` guard handling (issue 127)

In `survey.py`:
- `survey.ignored()` also reports where the rule came from (`git check-ignore -v`). Only a tracked ignore file of the repo (root or nested `.gitignore`) is edited: `seed.decide` plans `convert: .gitignore (adds ...)` and `seed.apply` appends, under one comment line, the exact exception lines `ignored()` computes (for example `!.loop/` then `!.loop/*.tsv`); existing words are kept. A rule from `.git/info/exclude` or the global excludes file yields `GAP: <file> ignores <path>. Fix: add <exact line> to that file`, and the adoption stages the plan's paths with `git add -f`. After the append, setup re-runs `git check-ignore` on every plan path: a path still ignored (a parent folder or `*` pattern wins, or a later nested ignore file) gets the same `git add -f` and a `GAP:`. The append keeps CRLF files CRLF, adds the missing final newline, and a rerun appends nothing.
- `survey.guards()` reads the repo's hook files (`.githooks/`, `.husky/`, `.pre-commit-config.yaml`, the git hooks folder, scripts named for a guard or hook) for `.tsv` and prints `GUARD: <file> mentions .tsv; if it refuses tracked data files, exempt .loop/*.tsv (docs, regression rows and runs)` in the dry run and the run.
- If the real commit is refused by a repo hook, setup rolls back (part 2), prints the hook's own output and the same exemption line, and exits 1 with nothing written; a rerun after the owner adds the exemption adopts. Never `--no-verify`; setup never edits a hook that rejects tracked files.
- Docs: SKILL.md gains an "Adoption" paragraph (the two halves and the exemption line).
- Row `setup-tsv-guard-127`: the `.gitignore` half is exempted by a written line; a hook that rejects `.tsv` is named with its exemption and nothing is written.

### 5. The test-command proof (issue 119)

`survey.runs_tests(repo, command)` proves statically (nothing is executed) that a command finds at least one test by the runner's real pattern: unittest discover uses `-s` dir and `-p` pattern (default `test*.py`), pytest `test_*.py` and `*_test.py` (or the file's own config), `go test` `*_test.go`, `cargo test` a `#[test]` or `tests/` file. The suffix-only case: `tests/calc_test.py` yields `python3 -m unittest discover -s tests -p '*_test.py'`. If no pattern matches, fall back to a repo runner that exists (`tests/**/run.sh`, `scripts/run-tests.sh`, `scripts/test.sh`). The runner is chosen from file content, not names: `unittest.TestCase` selects unittest, `def test_` functions with no TestCase select pytest only when it is on PATH (otherwise `no fit` and a finding, never a unittest command that finds zero tests). A check proven only by a file pattern is printed `NOTE: <cmd> inferred from file names, not run`. With no proof the check list is empty, `no fit: .loop/regression.tsv (no check command found)` stays, and a `no-fit` finding is filed. One rule: surveyed guesses and CI-derived commands must pass the proof to become checks; a check the config already holds is kept as is and noted (`NOTE: <cmd> finds no test files`) when it fails the proof.

PR 83 re-implemented on current main (not merged from the stale branch): `seed.stored(config, old)` keeps a `checks` key the config already holds, and the seeded land rows run every check joined by `&&`. Surveyed checks still become rows, not a setting.

Rows: `setup-zero-tests-119` (a `*_test.py` repo gets a check; the test runs the proposed command in the stdlib-only fixture and asserts at least one test ran; also no pattern and no runner gives an empty check list plus a `no-fit` finding, and a config-held check that fails the proof is kept with `NOTE: <cmd> finds no test files`; a pytest-style `calc_test.py` with no pytest on PATH gives `no fit`, not a unittest command), `adopt-fixture-existing-checks` (part 11).

### 6. `setup --from <adopted repo>` (SET-9)

The borrow block in `survey.py`, read-only on the model (a local path; no network). Reads the model's `.loop/config.json` and `.loop/docs.tsv`; prints `borrow:`, `adapt:`, `skip:` and `held:` lines in the plan:
- Portable allowlist whose value differs from the default becomes this repo's value: parallel, max_tries, cadence, criteria, criteria_max, review_depth, token_budget, the `*_minutes` budgets, step_limit, goal_levels, ci_levels, pool_size, digest_mail, regression_cron, health_cron, feature_labels, stale_branch_days, silent_minutes.
- Never borrowed silently, printed `held: <key> = <value> (unattended or runs code; add --allow <key> to take it)` and taken only with `--allow KEY[,KEY]`: auto_approve, auto_merge, full_auto, mend, resume_on_limit, pr_bumps_version, reply_hook, govern_hook, agent_files, routines.
- This repo keeps its own: base, agent_command, version_file, template_*, session_command, digest_owner.
- Milestones: none created or copied; `feature_labels` and the page-set shape are borrowed; a model page with no matching area here is `skip:`; an old milestone in the model gets `skip: milestone <title> (free form, none made)`.
- Private rules, never values: the model's `risky_paths` regexes are borrowed; leak patterns and local rules live in the owner's private folder, so only `NOTE: your local layer already applies here` prints and no private file is read.
- One wording, stated once (closes reviewer note R3-1): a borrowed value failing the private-value check prints `skip: <key> holds a private value`, and a held value failing it prints `held: <key> (holds a private value; not shown)`; the value is never printed and is left out even with `--allow`.
- The private-value check (`settings.private_value(text)`, shared with part 8): a home path, an email, a token-looking string, or a match in the owner's private-name list. An `--allow`ed value is screened by it and again by the SET-8 guard at staging.
- Borrowed values land through the normal config merge (the repo's own existing values win), so a second run changes nothing. Wiring in `setup.py`: `--from DIR` and `--allow`.
- Validation: borrowed values must match the settings table's type and range (an integer budget is an integer in range, an enum is one of its members); a borrowed `risky_paths` regex must compile and be at most 200 characters; `--from` resolves symlinks and refuses a model whose `config.json` leaves the model repo.
- Negative cases, asserted inside row `set9-from-borrows`: an unreadable or invalid model path prints `REFUSED: --from <path> is not an adopted repo (<reason>)` and writes nothing; `--allow` naming a key not in the held list prints `NOTE: <key> is not held; nothing to allow` and changes nothing.
- Rows `set9-from-borrows` (borrowed, kept, held, absent until allowed, second run `NO CHANGE`, the model repo byte-identical) and `set9-from-no-values` (a model value holding a home path or an email is skipped and appears nowhere in output or written files).

### 7. The three settings layers and their display (SET-2, done line 3)

In `settings.py`: `resolve(repo)` returns, for every setting in the existing table, `(value, layer, home)` with layer `default` (the template table), `repo` (set in `.loop/config.json`) or `local` (set in the flow or health file under the owner's private folder, `$LOOP_FLOW` and `$LOOP_HEALTH` honored and named). Order default, then repo, then local, a later layer winning wherever a key appears in more than one. A private-home key found in the committed config shows `repo (local setting in a committed file)`, which is what SET-8 refuses. `settings.py show [--repo DIR] [--json]` prints `| setting | value | layer | home |` per setting; `reference` and `show` read the same table. About 40 scripts read `config.json` themselves and are not rewritten; `resolve()` is the single place for a cross-home override, and Usage and `references/settings.md` say that is the next step. The `show` output ends with one line, `NOTE: scripts read repo values directly; a local value wins only where its own home is read`, so the display never claims more precedence than the code enforces. Every printed value (text and `--json`) goes through `settings.private_value`; a value that holds a private value prints `(withheld: holds a private value)`, and a setting that holds environment values prints its names only, because people paste this output into issues. The layers caveat is the first paragraph of the "Layers" section. Row `set2-layers-show` (default, repo and local values each show their layer; a local key in the committed config is flagged; the NOTE line is asserted).

### 8. Refusing to commit a local setting or private value (SET-8, done line 6)

`update.guard_staged(repo)` (part 0) runs after staging and before the commit, next to the existing `private.py hook staged` call. It reads the staged diff against HEAD and looks only at lines the adoption adds (never text the repo already had). It refuses with rollback, exit 1, naming `file:line` or the key and never the value, when an added line holds (a) a private-home key in `.loop/config.json` (`allowed_tools`, `leak_prefixes`, `full_markers`, `overrides`, `probe`, and any other key `settings.py` homes in the private folder), (b) the owner's home folder path or the git user email as an exact substring, or (c) an exact value of a local-layer string setting that holds `/`, `~` or `@`, is at least 8 characters, and is not a template default. There is no length-only rule. Values are read only to compare. These three refusals are the only content refusals and apply to what setup writes (including borrowed `--from` values). Rows `set8-local-setting-refused` and `set8-private-value-refused` (the second also asserts three non-refusals: private-looking text the repo already had, a value under 8 characters, and a template default); existing rows `set8-hooks` and `set8-setup-commit` stay and keep their `seen_red` dates.

### 9. Home and README writer, and the dry run that lists every file (SET-1, SET-7)

- The Home writer in `seed.py` writes the Home in the docs format: marker, `# <repo>`, `## Features`, one table whose header is read from workflow-docs' `pageformat.HOME`, one row per feature page linking its README section; and adds `## How to use` with one `### How to use <Feature>` section per page (intro line and the `| You say | What happens |` table with one row). The seeded Home no longer carries a `HOM-1` criterion or row. If a README exists only the missing section is added (words kept). Seeded PRD pages are shaped so the only gap left is UNWRITTEN. `docs.py check` is the oracle (no DOC-4, DOC-5, DOC-7, DOC-8 or link failure); reading the header from `pageformat` keeps the writer from drifting. Row `set1-docs-format`.
- Dry run (SET-7): `seed.decide` also plans the rendered `docs/wiki/Tests.md`, the `.gitignore` conversion, the git hooks, `borrow:` lines and `WOULD FILE` (computed from the in-memory gap list, since a dry run has no findings file; the filed-count equality with `health.py preview --group adoption` is asserted only after a real run), and always prints the private half's keys as `would add to <private folder>`. The invariant test: the files in the real run's adoption commit are a subset of the dry run's `add:` and `convert:` paths, and a dry run leaves the tree, branches and home folder byte-identical, including across the health start (the row hashes the tree around it, since health may write caches). Second run: no commit, no gh write, `NO CHANGE`, clean tree, an untracked working config survives, and the two health lines still print. Rows `set7-dry-run-lists-all`, `set7-second-run-nothing`.

### 10. Health first and last as the adoption verdict (SET-1, done line 2)

`agents.health(repo)` runs the sibling `workflow-health` `health.py check --skip mine` (the owner's private `mine` rules run the owner's own commands in the repo, so setup never runs them, not even in a dry run; the verdict is over the fixed groups). Before any write (dry run included: it is read-only and takes about 4 seconds) it prints `HEALTH START: <the check's HEALTH line>` or `HEALTH START: not measured (<reason>)` (workflow-health not beside workflow-setup, or the check errored, crashed or ran past 120 seconds). After the commit it runs the same full check on the branch and prints `ADOPTION VERDICT: GREEN` or `ADOPTION VERDICT: GAPS (<n> fail, <m> warn)` preceded by every FAIL, WARN and UNREAD line the check printed (each carries its fix) so that the verdict line is the last line, or `ADOPTION VERDICT: not measured (<reason>)`; the counts include unread rows (`GAPS (<n> fail, <m> warn, <u> unread, <k> steps failed)`). Every FAIL, WARN and UNREAD line relayed from health passes `settings.private_value` first. Setup exits 0 in every case unless `--strict` is given: with `--strict`, GAPS, `not measured` or a failed post-commit step exits 3 (the adoption is still committed), so automation has a readiness signal; the default stays 0 because adoption never blocks. Exit codes: 0 done or no change, 1 refused, 2 refused before any write for a dirty agent file (today's code at `setup.py` line 275, kept), 3 strict gaps, 4 half undone, 130 interrupted. A dry run prints `HEALTH START:` and `ADOPTION VERDICT: not run (dry run)`; a real run and a no-change run both print both lines. The start state is also the second line of the adoption commit message. `--no-health` or `LOOP_NO_HEALTH=1` skips; `dev/toy/reap.sh` exports it (existing toys unchanged); the new tests keep that opt-out and unset it only inside `set1-health-bracket` and `set1-no-fit-filed`, so no other row pays the extra health runs. Row `set1-health-bracket` (`HEALTH START:` precedes the first write line, `ADOPTION VERDICT:` is the last line, a non-green verdict lists each gap with its fix; also `--no-health` and a missing workflow-health give `not measured (<reason>)`, and a health run past the limit, shortened by an environment override in the test, does the same).

### 11. SET-6 fixture repos and nightly rows (done line 4)

New `dev/toy/test-adopt-fixtures.sh` (sources `dev/toy/reap.sh`, precise `# reads:` header) builds four fixture repos with `dev/toy/make.sh`: existing config checks (PR 83's shape), CI tests with a `.gitignore` blocking `*.tsv`, a bare `agent_command` with no CI, and features as milestones not folders (milestone data from the stand-in `fakegh`, nothing real). Nightly rows `adopt-fixture-existing-checks` (config checks kept, rows run every check; seen failing on v0.27.10), `adopt-fixture-ci-gitignore` (exception lines written, check from CI), `adopt-fixture-bare-agent` (gap named with its fix), `adopt-fixture-feature-milestones` (pages made, no milestone made). The existing `dev/toy/test-setup-fit.sh` gets its `.gitignore` and bare-agent expectations updated (they stop expecting a refusal) and a nightly row `setup-fit` (it had none). A comment in `dev/toy/test-adopt.sh` saying a bare agent command exits 1 after writing is corrected.

### 12. New tests, the 19 regression rows, and the Setup Tests table (done lines 7 and 8)

New `dev/toy/test-setup-adopt.sh` (sources `dev/toy/reap.sh`, precise `# reads:` header) holds the land rows' cases, one entry per row id, selectable by argument as `test-rows.sh` does. Order of work per row: write the case, add the row (`regression.py add ...`), commit (so `red` can break and restore), make it fail on old code (`regression.py red <id> --break "<cmd>"`; for new behavior the break is restoring the v0.27.10 skill folders into a scratch copy, for rows guarding behavior main already has such as `set7-second-run-nothing` it is a one-line mutation of the guard), then make it pass. The 19 rows: `set1-health-bracket`, `set1-never-blocks`, `set1-no-fit-filed`, `set1-docs-format`, `set2-layers-show`, `adopt-fixture-existing-checks`, `adopt-fixture-ci-gitignore`, `adopt-fixture-bare-agent`, `adopt-fixture-feature-milestones`, `setup-fit`, `set7-dry-run-lists-all`, `set7-second-run-nothing`, `set8-local-setting-refused`, `set8-private-value-refused`, `set9-from-borrows`, `set9-from-no-values`, `setup-zero-tests-119`, `setup-refusal-writes-120`, `setup-tsv-guard-127`. Levels: the four `adopt-fixture-*` rows and `setup-fit` are nightly; the other 14 rows are land. Lane budget is 15 minutes per lane; each new land case is measured so none runs past about 40 seconds (health at both ends is opted out except in the rows about it). Before the first new row is added the current lane time is measured and written in the commit message; a land row that would push a lane past the budget moves to nightly. Rows past the budget are left to the scheduled full suite. `criteria.py render` regenerates the Setup and Tests tables; the `no passing test` placeholders for SET-6, SET-7 and SET-9 disappear; the Tests table lists all 19 rows plus the existing `set8-hooks` and `set8-setup-commit`.

Done-line map: line 1 parts 3, 4, 9; line 2 part 10; line 3 part 7; line 4 part 11; line 5 part 6; line 6 parts 8, 9; line 7 this part; line 8 parts 2, 4, 5.

### 13. Files each change touches

| Change | Files |
|---|---|
| Pure moves for size | `skills/workflow-setup/scripts/setup.py`, `agents.py`, `seed.py` (sizes in part 0) |
| Transaction, refusals, private guard, working config | `sync.py` (`Txn`), `update.py` (`guard_staged`), `settings.py` (`private_value`), `setup.py` (wiring, 2,500 bytes budget); health start and verdict in `agents.py`, findings lines in `seed.py`, the filing call in `setup.py` |
| 119 proof, `.tsv` guards, ignore source | `survey.py` (sizes in part 0) |
| PR 83 keep checks, Tests.md listed, `.gitignore` convert, Home and README | `seed.py` (Home and README writer folded in) |
| `settings show` and layers | `settings.py` |
| `--from` | `survey.py` (borrow block); `setup.py` (flags) |
| Adoption rules `no-fit`, `agent-tools`, additive filing | `skills/workflow-health/scripts/report.py`, `rules.py` (registration only), `controls.py`, `file.py` (`--open-only`, 13,459 to about 13,800), `skills/workflow-health/references/commands.md` |
| Docs | `skills/workflow-setup/SKILL.md` (under 150 lines), `skills/workflow-setup/references/settings.md`, `docs/wiki/Setup.md` Usage, Tests and Unreviewed text only |
| Tests | new `dev/toy/test-setup-adopt.sh`, new `dev/toy/test-adopt-fixtures.sh`; edits to `dev/toy/test-setup-fit.sh`, a comment in `dev/toy/test-adopt.sh`, `dev/toy/reap.sh` (two exports); `.loop/regression.tsv` rows |

### 14. Docs and listing gates

- `docs/wiki/Setup.md`: Usage text gains the new output lines (`HEALTH START:`, `ADOPTION VERDICT:`, `GAP:`, `GUARD:`, `borrow:`, `held:`), `setup --from`, `settings show` and the changed refusals; the `REFUSED to call this done` and `REFUSED: nothing written. Fix .gitignore` usages are replaced. No requirement line changes. The Usage text is the one canonical page: a copy-paste quickstart (dry run, run, read the verdict, file the findings) with sample output, a legend table of output prefixes (prefix, meaning, who acts), one table of flags and environment variables (`--dry-run`, `--from`, `--allow`, `--no-health`, `--no-issues`, `--strict`, `LOOP_NO_HEALTH`, `LOOP_NO_ISSUES`), the exit codes, runnable examples of `setup --from <repo> --allow auto_merge` and `settings.py show --json`, and the error codes with anchors; SKILL.md and `references/settings.md` link to it. A `git diff` check confirms no changed line sits under a Reviewed marker.
- No new skill, so the catalog and `listing.json` are unchanged; `python3 dev/package.py` must pass (the part 0 gate list; no executable bits, no encoded blobs).
- Gates before the PR: `python3 skills/workflow-docs/scripts/docs.py check` prints DOCS OK; `python3 skills/workflow-health/scripts/health.py check` stays green on this repo (including the new Adoption rules); `lanes_cli.py check` passes; `dev/toy/test-tree.sh` passes; the pre-commit hook accepts every commit; the part 0 gate list holds; `wc -l` of every SKILL.md is under 150.

### 15. Not in scope and deferred

Deferred, recorded here (no TODOS.md exists and writing one is outside the goal's touches): a health rule that counts the packaged file against the 99 cap (P3, own row and control); routing every config reader through `layers.resolve` so a local layer can override a repo key (P3, about 40 scripts, outside this blast radius; stated as the next step in Usage). Also deferred: moving the folded blocks into their own modules when the file cap allows (cohesion debt: hooks and health in `agents.py`, `guard_staged` in `update.py`, `Txn` in `sync.py`, rules in `report.py`); `--no-hooks`; an adoption `--json` result contract; a stored-versus-effective column in `show`; one readiness check across agents; TTHW instrumentation. Design-derived, not expansions: the `setup-fit` row, the Tests.md listing and the correction of the `test-adopt.sh` comment.

### 16. Risks carried

- The Home writer must equal workflow-docs' own check (read `pageformat.HOME`; `docs.py check` is the oracle).
- Filing issues unprompted: only with a signed-in `gh` and a GitHub remote, off with `--no-issues`, deduplicated by health's marker, tested only through the stand-in.
- Rollback must restore every path including ones other tools write; `Txn` snapshots every existing file under the folders setup writes into and sweeps by content hash, and the 120 row compares full tree hashes.
- Health at both ends adds about 8 seconds to a real adoption and nothing to tests (env opt-out).
- `.gitignore` exception lines change a file the repo owns: append-only, under a comment, shown in the dry run first.
- `resolve()` meets "later layer overrides" only inside a key's own homes until other readers adopt it; recorded in Usage.
- Every host file ends within about 6% of the warning line; the capacity audit and gate list in part 0 are the stop condition.


<!-- autoplan-accepted:ceo -->
- Add no tracked file under `skills/`: the package holds 99 files (96 under `skills/` plus `listing.json`, `README.md`, `LICENSE`) and `dev/package.py` allows 99. Each design module is placed in the host named in plan part 0 (per-file byte targets and import graph there). The first build commit is a capacity audit (then the pure-moves commit) recording the real `dev/package.py` count and `wc -c` of every host; if a host would pass 18,432 bytes the levers in part 0 apply in order, and the last lever halts the build at the last green commit, writes the gap to `.loop/goals/setup-adopt-2.halt.md` (a `Capacity halt:` commit) and reports it. Verified at every commit that touches `skills/` by the part 0 gate list.
- Pure moves right after the capacity audit commit, in one commit: `reply_hook()` and `HOOKS` from `setup.py`, and seed's `git_hooks` cluster, into `agents.py` (the cluster has its own local `refuse`, so no import cycle), with `setup.py --reply-hook` output byte-identical.
- Negative cases: `--from` with an unreadable model or an `--allow` key that is not held changes nothing, and a rollback with a pre-existing `workflow-setup` branch keeps that branch.
- A failure in any step after the commit (hooks, private settings, filing, verdict) prints a `NOTE: <step> failed` line, keeps the commit and exits 0 with the verdict last, asserted in `set1-never-blocks`; an exception or interrupt between the first write and the commit rolls back, asserted in `setup-refusal-writes-120`; the rollback sweep compares per-file content hashes against the snapshot (part 2) and restores only files that differ from it.
- New tests keep the `LOOP_NO_HEALTH` opt-out and unset it only in `set1-health-bracket` and `set1-no-fit-filed`; the dry run's `WOULD FILE` list comes from the in-memory gap list.
<!-- /autoplan-accepted:ceo -->

<!-- autoplan-accepted:dx -->
- Index safety: `Txn` records the index tree, setup stages and commits only its plan paths, rollback restores the index with `git read-tree`; `setup-refusal-writes-120` includes a pre-staged unrelated change (kept staged), a dirty planned path (refused with `SETUP_PLANNED_PATH_DIRTY`) and a dirty unrelated file (untouched).
- Each moved name keeps a one-line alias in its old module, and `setup-fit` runs the previous release's `setup.py` against the new modules.
- Every `REFUSED:` and `NOTE:` line ends with a stable parenthesized code (setup's existing convention) naming a Setup-page anchor (wording before it unchanged); an unexpected exception rolls back and prints a masked trace path; relayed hook output and every `settings.py show` value (text and `--json`) pass `settings.private_value`; restore failure says `Side effects: partial`; a partial filing says `N of M filed` and names the finish command (`health.py file --group adoption --open-only`).
- The verdict line is the last line (gap lines precede it), counts unread rows and failed steps, and `--strict` exits 3 on GAPS, `not measured` or a failed post-commit step; default exit stays 0; exit codes 0, 1, 2 (dirty agent file, as today), 3, 4 (half undone), 130 are documented.
- `agent-tools` names every setting that holds an agent command; the findings kinds are fixed at four.
- The Setup page Usage carries the quickstart, the prefix legend, the flags and environment table, exit codes, runnable examples and error-code anchors.
<!-- /autoplan-accepted:dx -->

<!-- autoplan-accepted:eng -->
- Prechecks refuse before any write with codes: merge, rebase or cherry-pick in progress, detached or unborn HEAD, setup branch checked out in another worktree (`SETUP_REPO_STATE`); setup branch with commits HEAD lacks (`SETUP_BRANCH_DIVERGED`); a planned path with staged or unstaged changes (`SETUP_PLANNED_PATH_DIRTY`, exit 2); mixed-version setup modules (`SETUP_MIXED_VERSION`); each has a fixture inside `setup-refusal-writes-120`.
- `Txn` snapshots every existing file under the folders setup writes into (bytes, mode, symlink target), stages and commits exactly the files whose bytes changed, compares per-file hashes on rollback, writes a journal in the git dir before the first write, recovers an interrupted run at the next start, terminates and reaps child processes on a signal, and treats a moved branch tip that holds the write set as committed; tested with a kill during a hook, a kill after the ref update and a SIGKILL.
- Filing uses a new additive `health.py file --open-only` (never closes, reopens or updates), `GH_REPO` from `origin`, `private_value` over every issue title and body, the target and labels printed first and shown by the dry run; a second run writes nothing to GitHub; a step's outcome is read from its output as well as its exit status.
- Findings lines are owned by the `[adoption]` tag: setup rewrites, deletes an empty kind and never touches other lines.
- The test runner is chosen from file content; a pytest-style file with no pytest on PATH gives `no fit`, never a unittest command; after the `.gitignore` append every plan path is re-checked with `git check-ignore`, with `git add -f` and a GAP for any still ignored; CRLF and the final newline are kept.
- `--from` validates types, ranges, regex compile and length, and symlinks; relayed health lines are masked; the dry-run row hashes the tree around the health start.
- `setup-fit` takes the previous release from local git history and checks both mixed-version directions; the lane time is measured before new rows are added.
- The `agent-tools`, `no-fit` and other new rules and `file.py --open-only` stay inside `skills/workflow-health` (`report.py`, `controls.py`, `rules.py`, `file.py`).
<!-- /autoplan-accepted:eng -->
## Review record

<!-- autoplan-accepted:ceo -->
- Add no tracked file under `skills/`: the package holds 99 files (96 under `skills/` plus `listing.json`, `README.md`, `LICENSE`) and `dev/package.py` allows 99. Each design module is placed in the host named in plan part 0 (per-file byte targets and import graph there). The first build commit is a capacity audit (then the pure-moves commit) recording the real `dev/package.py` count and `wc -c` of every host; if a host would pass 18,432 bytes the levers in part 0 apply in order, and the last lever halts the build at the last green commit, writes the gap to `.loop/goals/setup-adopt-2.halt.md` (a `Capacity halt:` commit) and reports it. Verified at every commit that touches `skills/` by the part 0 gate list.
- Pure moves right after the capacity audit commit, in one commit: `reply_hook()` and `HOOKS` from `setup.py`, and seed's `git_hooks` cluster, into `agents.py` (the cluster has its own local `refuse`, so no import cycle), with `setup.py --reply-hook` output byte-identical.
- Negative cases: `--from` with an unreadable model or an `--allow` key that is not held changes nothing, and a rollback with a pre-existing `workflow-setup` branch keeps that branch.
- A failure in any step after the commit (hooks, private settings, filing, verdict) prints a `NOTE: <step> failed` line, keeps the commit and exits 0 with the verdict last, asserted in `set1-never-blocks`; an exception or interrupt between the first write and the commit rolls back, asserted in `setup-refusal-writes-120`; the rollback sweep compares per-file content hashes against the snapshot (part 2) and restores only files that differ from it.
- New tests keep the `LOOP_NO_HEALTH` opt-out and unset it only in `set1-health-bracket` and `set1-no-fit-filed`; the dry run's `WOULD FILE` list comes from the in-memory gap list.
<!-- /autoplan-accepted:ceo -->

<!-- autoplan-accepted:dx -->
- Index safety: `Txn` records the index tree, setup stages and commits only its plan paths, rollback restores the index with `git read-tree`; `setup-refusal-writes-120` includes a pre-staged unrelated change (kept staged), a dirty planned path (refused with `SETUP_PLANNED_PATH_DIRTY`) and a dirty unrelated file (untouched).
- Each moved name keeps a one-line alias in its old module, and `setup-fit` runs the previous release's `setup.py` against the new modules.
- Every `REFUSED:` and `NOTE:` line ends with a stable parenthesized code (setup's existing convention) naming a Setup-page anchor (wording before it unchanged); an unexpected exception rolls back and prints a masked trace path; relayed hook output and every `settings.py show` value (text and `--json`) pass `settings.private_value`; restore failure says `Side effects: partial`; a partial filing says `N of M filed` and names the finish command (`health.py file --group adoption --open-only`).
- The verdict line is the last line (gap lines precede it), counts unread rows and failed steps, and `--strict` exits 3 on GAPS, `not measured` or a failed post-commit step; default exit stays 0; exit codes 0, 1, 2 (dirty agent file, as today), 3, 4 (half undone), 130 are documented.
- `agent-tools` names every setting that holds an agent command; the findings kinds are fixed at four.
- The Setup page Usage carries the quickstart, the prefix legend, the flags and environment table, exit codes, runnable examples and error-code anchors.
<!-- /autoplan-accepted:dx -->

<!-- autoplan-accepted:eng -->
- Prechecks refuse before any write with codes: merge, rebase or cherry-pick in progress, detached or unborn HEAD, setup branch checked out in another worktree (`SETUP_REPO_STATE`); setup branch with commits HEAD lacks (`SETUP_BRANCH_DIVERGED`); a planned path with staged or unstaged changes (`SETUP_PLANNED_PATH_DIRTY`, exit 2); mixed-version setup modules (`SETUP_MIXED_VERSION`); each has a fixture inside `setup-refusal-writes-120`.
- `Txn` snapshots every existing file under the folders setup writes into (bytes, mode, symlink target), stages and commits exactly the files whose bytes changed, compares per-file hashes on rollback, writes a journal in the git dir before the first write, recovers an interrupted run at the next start, terminates and reaps child processes on a signal, and treats a moved branch tip that holds the write set as committed; tested with a kill during a hook, a kill after the ref update and a SIGKILL.
- Filing uses a new additive `health.py file --open-only` (never closes, reopens or updates), `GH_REPO` from `origin`, `private_value` over every issue title and body, the target and labels printed first and shown by the dry run; a second run writes nothing to GitHub; a step's outcome is read from its output as well as its exit status.
- Findings lines are owned by the `[adoption]` tag: setup rewrites, deletes an empty kind and never touches other lines.
- The test runner is chosen from file content; a pytest-style file with no pytest on PATH gives `no fit`, never a unittest command; after the `.gitignore` append every plan path is re-checked with `git check-ignore`, with `git add -f` and a GAP for any still ignored; CRLF and the final newline are kept.
- `--from` validates types, ranges, regex compile and length, and symlinks; relayed health lines are masked; the dry-run row hashes the tree around the health start.
- `setup-fit` takes the previous release from local git history and checks both mixed-version directions; the lane time is measured before new rows are added.
- The `agent-tools`, `no-fit` and other new rules and `file.py --open-only` stay inside `skills/workflow-health` (`report.py`, `controls.py`, `rules.py`, `file.py`).
<!-- /autoplan-accepted:eng -->

<!-- AUTONOMOUS DECISION LOG -->
## Decision Audit Trail

| # | Phase | Decision | Classification | Principle | Rationale | Rejected |
|---|-------|----------|----------------|-----------|-----------|----------|
| 1 | Intake | Skip the office-hours offer; a design doc exists in the repo | Mechanical | P6 | `.loop/goals/setup-adopt-2.design.md` is approved; unattended run | Run office-hours |
| 2 | Intake | UI scope no, DX scope yes (snapshot scope: 28 term matches, developer-facing CLI skills) | Mechanical | P1 | scope tool returned dxRequired true, uiRequired false | Skip DX |
| 3 | CEO | Mode SELECTIVE EXPANSION (auto) | Mechanical | P6 | autoplan override | HOLD SCOPE |
| 4 | CEO | Fold all design modules into existing files, zero new files under skills/ | Mechanical | P4 | package count 99 of 99 (package.py walks skills plus listing.json, README.md, LICENSE) | New adopt.py, borrow.py, homewrite.py |
| 5 | CEO | Capacity audit as first build commit with a stop condition | Mechanical | P1 | design estimate ~24 KB of setup-side code against ~15 KB room at the 90% line | Assume it fits |
| 6 | CEO | Defer a health rule for the packaged file count to TODOS (P3) | Taste | P3 | outside the done lines; would need its own row and control | Add the rule now |
| 7 | CEO | Correct the room premise: about 33 KB aggregate room vs about 25 KB needed; per-file targets with arithmetic and an import graph | Mechanical | P5 | spec reviewer recomputed; my 15 KB figure was a mis-sum | Keep the 15 KB claim |
| 8 | CEO | Capacity stop leaves the audit commit, writes the gap to findings and resumes after the owner decides | Mechanical | P1 | spec review: no resume path | Leave undefined |
| 9 | CEO | Deferrals recorded in plan part 15, not TODOS.md | Mechanical | P3 | TODOS.md absent and outside the touches | Create TODOS.md |
| 10 | CEO | Health bracket runs with `--skip mine`; setup never runs the owner's private rules | Mechanical | P1 | Mine rules run the owner's commands (enforce.py:48-53), not read-only | Run the full check |
| 11 | CEO | A failed post-commit step counts as a gap in the verdict | Mechanical | P1 | native voice: never GREEN after a failed step | NOTE only |
| 12 | CEO | `show` prints a NOTE that other readers use repo values directly | Mechanical | P5 | both voices: display must not overstate precedence | Silent display |
| 13 | CEO | Issue filing stays default-on with signed-in gh and a remote | User Challenge | n/a | both voices recommend opt-in; the done line says it is filed; kept as the original direction | Opt-in filing |
| 14 | CEO | Keep one goal with eight frozen done lines | User Challenge | n/a | both voices recommend splitting or a minimal flow; done lines are frozen | Split the goal |
| 15 | CEO | Keep snapshot and rollback transaction, not an isolated worktree | Taste | P5 | design settled it; sync.py already hosts a temporary worktree; close alternative | Worktree transaction |
| 16 | CEO | Keep the 99-file cap as a fixed limit and place code by host | Taste | P6 | the cap is the marketplace limit named for this goal; both voices ask if it can move | Raise MAX_FILES |
| 17 | CEO | Reject an `--allow-private` escape for the staged guard | Mechanical | P1 | it would defeat done line 6 | Add the escape |
| 18 | CEO | Inferred checks print `inferred from file names, not run` | Mechanical | P5 | static proof is not execution; running repo code at adoption is unsafe | Run the tests |
| 19 | DX | Add `--strict` (exit 3 on GAPS, not measured or a failed post-commit step); default exit stays 0 | Taste | P1 | both voices: exit 0 hides gaps from CI; additive and keeps never-blocks | Change the default exit |
| 20 | DX | Mask relayed hook output and every `show` value through `private_value` | Mechanical | P1 | CAP4 redaction (native) and unredacted show output (Codex) | Print as is |
| 21 | DX | Verdict line last, gap lines before it, unread rows counted | Mechanical | P5 | design said both last and followed-by; health has an UNREAD state | Leave the contradiction |
| 22 | DX | Index preservation, path-limited stage and commit, three rollback fixtures | Mechanical | P1 | Codex: porcelain baseline cannot restore a partially staged file | Snapshot bytes only |
| 23 | DX | Keep one-line aliases for moved names; run the previous release's setup.py in `setup-fit` | Mechanical | P1 | update.py keeps a locally edited file on its own (verified) | Treat as one upgrade unit |
| 24 | DX | Stable bracketed codes, trace path for unexpected failures, partial-outcome wording | Mechanical | P1 | agent-ready error contract, CAP6 findings | Free text only |
| 25 | DX | Reject `--allow-private`; defer `--no-hooks`, adoption `--json`, effective-value column, TTHW instrumentation | Taste | P3 | outside the done lines or defeats done line 6 | Add them now |
| 26 | DX | Filing opt-in joins User Challenge UC1 (third voice) | User Challenge | n/a | original direction stands | Opt-in filing |
| 27 | Eng | Structure question: keep the original arrangement (fold into existing files) | Mechanical | P5 | no smaller arrangement keeps the done lines under the 99-file cap | Smaller arrangement |
| 28 | Eng | Prechecks, dirty planned path refusal, exact write-set staging, per-file hashes | Mechanical | P1 | both voices: whole-index commit and status-only sweep break the guarantee (setup.py:284, :290) | Path-limited commit only |
| 29 | Eng | Durable journal, child reaping, ref reconciliation, SIGKILL recovery | Mechanical | P1 | both voices: hard kill leaves unrecoverable state | In-memory handler only |
| 30 | Eng | Branch diverged is a refusal so plan and apply see one revision | Mechanical | P5 | Codex: plan before switch (setup.py:235, :274) | Plan against branch tip |
| 31 | Eng | Filing is additive `--open-only`, GH_REPO from origin, private screening, printed target | Mechanical | P1 | file.py reconciles and closes (file.py:150-163) and creates labels | Plain `file --group adoption` |
| 32 | Eng | Exit code 2 kept for dirty files, half undone is exit 4; codes use the existing `(SETUP_*)` form | Mechanical | P5 | collisions with setup.py:272-275 | Brackets and exit 2 |
| 33 | Eng | Runner chosen from file content; pytest-style without pytest gives no fit | Mechanical | P1 | Codex: unittest finishes with zero tests | Name patterns only |
| 34 | Eng | Mixed-version precheck and both-direction test from local history | Mechanical | P1 | update keeps edited files individually (update.py:181-195) | Aliases only |
| 35 | Eng | Keep snapshot Txn; isolated worktree is the preferred successor | Taste | P5 | design settled; checkout semantics; both CEO and eng voices prefer the worktree | Adopt the worktree now |
| 36 | Eng | Txn built and measured first; lane time measured before new rows | Mechanical | P1 | cap margin and lane budget | Estimates only |

### CEO review (phase 1)

# CEO review (autoplan phase 1), plan setup-adopt-2, mode SELECTIVE EXPANSION (auto)

#### Step 0 premise table (premise | claim | receipt | verdict)
| premise | claim | file:line receipt | verdict |
|---|---|---|---|
| P1 | the package holds 99 files, the limit is 99 | dev/package.py:26 and dev/package.py:134 | verified, design assumed 3 free slots |
| P2 | a bare agent_command is refused today | skills/workflow-setup/scripts/setup.py:85 | verified |
| P3 | runs_tests accepts `*_test.py` that unittest discover misses | skills/workflow-setup/scripts/survey.py:64 | verified |
| P4 | an ignored `.tsv` is detected by survey.ignored | skills/workflow-setup/scripts/survey.py:155 | verified |
| P5 | the health Mine group runs the owner's own commands | skills/workflow-health/scripts/enforce.py:48-53 | verified, the design's "read-only" check was wrong for Mine |
| P6 | health `check` takes `--skip` for groups | skills/workflow-health/scripts/health.py:323 | verified |
| P7 | filing reuses health's file engine | skills/workflow-health/scripts/file.py:113 | verified |
| P8 | about 40 scripts read config.json themselves | design line 114, not re-counted | unverified=1 |

unverified=1

#### Reality rows
REALITY: premise-table finding 7 of 8 premises verified; the Mine group runs owner commands so the health bracket must skip it skills/workflow-health/scripts/enforce.py:48-53
REALITY: already-done pass `git fetch origin main` then `git log origin/main --since=2026-11-11` on skills/workflow-setup and skills/workflow-health printed no commit; base is the release commit b7bfe4e
REALITY: surface-check pass `health.py check --skip`, `--group` and `regression.py red` exist; `settings.py show`, `setup.py --from`, `--no-health`, `--no-issues` are new by design skills/workflow-health/scripts/health.py:323
REALITY: binding-decisions pass `the decision search tool --scope branch --recent 50` printed nothing; the plan carries no Binding decisions section; the frozen done lines are the binding text .loop/goals/setup-adopt-2.md:1
REALITY: numbers pass host sizes are [measured: wc -c] skills/workflow-setup/scripts/setup.py:1 and the 25 KB of additions is [estimated] and [re-measure before gate] dev/package.py:26
REALITY: deferred-asks pass the linked issues are 119, 120 and 127; the plan covers each with a row, nothing is left out .loop/goals/setup-adopt-2.design.md:49-51
REALITY: pr-count pass one pull request for the goal; no ship policy file exists, so the default one PR per wave holds, and the next goal edits the same files so a second PR is not split here .loop/goals/setup-adopt-2.md:1

#### 0A Premise challenge
The real problem: adopting a repo blocks, hides what it will do, and is never judged by health. The plan solves it directly, not through a proxy: gaps replace refusals, a transaction replaces half-written state, health brackets the run. Do-nothing cost: every adopter hits a refusal that has already written files (reproduced in the design). Correction found in this review: the premise that the package has room for new modules is false (P1); the plan was rebuilt around zero new files.

#### 0B Existing code leverage
Reused: seed.decide and apply, survey.ignored, private.py hook staged, health check and file --group, criteria.py render, regression.py add and red, dev/toy/make.sh and fakegh, sync.py's temporary-worktree machinery (the Txn lives beside it). Rebuilt on purpose: PR 83's keep-checks, re-implemented on current main because the branch is stale at v0.8.5.

#### 0C Dream state
CURRENT: adoption blocks, half-writes, never checked. THIS PLAN: adoption always ends on a branch with a verdict and named gaps. 12-MONTH IDEAL: an adopted repo whose settings resolve in three layers everywhere, the package split so modules have room, and a measured first-green-goal time.
  CURRENT STATE ---> THIS PLAN ---> 12-MONTH IDEAL
  refusals, no verdict   gaps + verdict + transaction   one resolver for all readers, room in the package

#### 0D Alternatives
A patch in place (rejected by the design: misses 4 of 8 done lines). B small modules around the flow (design choice), now B' = B placed in existing files under the 99-file cap. C rewrite as plan-to-manifest (rejected, collides with the next goal). Outside voices add: D isolated worktree transaction (both reviewers), E minimal integration instead of full conversion (Codex), F split the goal (native). Decisions below.

#### 0E Mode
SELECTIVE EXPANSION, taken automatically (autoplan override). Scope proposals considered (0F/0G): five candidates, two accepted into the plan as inside the done lines (audit commit and negative cases), two deferred, one rejected.

#### 0G Scope proposals
1. Capacity audit commit with halt protocol: ACCEPTED (M risk, S effort).
2. Negative-case coverage for --from and rollback: ACCEPTED (S).
3. Health rule for the packaged file count: DEFERRED (plan part 15).
4. Route all config readers through layers.resolve: DEFERRED (plan part 15).
5. Record each real adoption's verdict privately (native voice): SKIPPED, the design keeps private values off disk and the goal has no metrics surface.

#### Dual voices
Native subagent: 10 findings (critical: the 99-file cap treated as law; high: scope too big, layers display-only, post-commit semantics, unprompted filing, regret scenario). Codex (frontier model, completed): 7 findings (high: adopted is not usable, health is not read-only for Mine rules, layers display claims precedence, cap drives architecture, adoption assumes conversion, filing is remote administration; medium: static test proof).

CEO DUAL VOICES - CONSENSUS TABLE:
  Dimension                           Claude  Codex  Consensus
  1. Premises valid?                   NO      NO     CONFIRMED (cap premise, layers premise)
  2. Right problem to solve?           PARTLY  PARTLY CONFIRMED (core never-blocks yes; scope broad)
  3. Scope calibration correct?        NO      NO     CONFIRMED (too large / full conversion)
  4. Alternatives sufficiently explored? NO    NO     CONFIRMED (worktree transaction, minimal integration)
  5. Competitive/market risks covered? NO      NO     CONFIRMED (no adopter metric, no comparison)
  6. 6-month trajectory sound?         NO      NO     CONFIRMED (every host at 94-97% of the line)

Disposition of each finding (auto-decided, principles in the audit trail):
- Both: layers display overstates precedence -> ACCEPTED as an obligation (NOTE line in show output). Mechanical, inside done line 3.
- Both: unprompted issue filing -> USER CHALLENGE (original direction stands: done line 1 says what doesn't fit is filed as issues).
- Both: split the goal / minimal integration -> USER CHALLENGE (original direction stands: the 8 done lines are frozen).
- Both: worktree-based isolated transaction -> TASTE (design settled on snapshot and rollback; sync.py already uses a temporary worktree for update; keep the design, surface the alternative).
- Both: the 99-file cap shapes the architecture -> TASTE / owner question: the cap is the marketplace limit named in the task, not movable by this plan; the plan keeps host placement and the halt path.
- Codex: health check is not read-only for the Mine group -> ACCEPTED (verified at enforce.py:48-53): bracket runs with `--skip mine`.
- Native: a failed post-commit step must not read GREEN -> ACCEPTED: counted in the verdict.
- Native: state why hooks do not run on setup's own commit -> ACCEPTED as plan text.
- Native: `--allow-private` escape for the staged guard -> REJECTED (it would defeat done line 6).
- Codex: static test proof is not execution -> ACCEPTED in part: inferred checks print `inferred from file names, not run`; full execution proof deferred (a run is not permitted at adoption, it executes repo code).
- Codex: operational vs installed states -> REJECTED as scope (the verdict and `agent-tools` already name an unusable agent as a gap).
- Native: Reviewed-marker check as a script -> SKIPPED (docs.py check already guards Reviewed lines; manual diff stays as a gate).

#### Review sections 1-11
Section 1 Architecture: no new component; blocks live in existing hosts (plan part 0). Dependency graph (import graph in part 0) is acyclic: settings is the leaf; survey, sync, update, seed, agents import it; setup imports all. 
  setup.py -> agents.py(health, hooks) -> (subprocess) health.py
  setup.py -> seed.py(plan, Home, findings) -> survey.py(proof, ignored, guards, borrow)
  setup.py -> sync.py(Txn) ; update.py(guard_staged) ; settings.py(resolve, private_value)
Data flow, four paths for the plan-to-commit flow: happy (write, stage, guard, commit, verdict); nil (no git repo, refused before any write); empty (no pages, no checks: gaps filed, adoption still on its branch); error (commit refused by a repo hook: rollback). Single points of failure: the one commit; rollback restores from the Txn snapshot. Rollback posture: a rerun after a refusal finds nothing written. Production failure: a signed-in gh with a revoked token makes filing fail after the commit: NOTE and the verdict counts it. FINDING: the capacity cliff (hosts at 94-97% of the line) is the real architecture risk; handled by the audit commit, not hidden.
Section 2 Error and rescue: see registry below; no catch-all: each step names the exception it handles (OSError on file restore, subprocess.TimeoutExpired on health, CalledProcessError on git).
Section 3 Security: no new endpoint. Findings: (1) health Mine rules run owner commands during a dry run, fixed by `--skip mine` (High likelihood Low, impact High, mitigated). (2) the staged-diff guard compares exact private values and never echoes them (mitigated). (3) `--from` reads another local repo read-only and never reads the owner's private folder; held keys need `--allow` (mitigated). (4) filing issues is an external write: default on only with signed-in gh and a GitHub remote, off with --no-issues, previewed as WOULD FILE (User Challenge UC1 offers opt-in). No new dependency, no new secret.
Section 4 Data flow and interaction edge cases: shadow paths for plan -> write -> stage -> commit: nil (missing config), empty (no features), wrong type (config is a list), too long (hundreds of pages), conflict (setup branch exists, handled), stale (working config differs from HEAD, working copy wins), interrupt (signal handler rollback, added this review). Async ordering: not applicable, setup is sequential; health runs as a child with a 120 s limit.
Section 5 Code quality: the folds put unrelated blocks in shared files (hooks in agents.py, guard in update.py). Accepted cost, named in the map; no duplicated behavior is added (private_value is one function used by guard and borrow). Cyclomatic risk: Txn.rollback and borrow have many branches; the plan keeps them as small functions, to be checked in the audit.
Section 6 Tests: 19 rows plus negative cases. Test diagram: Txn (unit via row 120, kill mid-run), guard_staged (rows set8-*, three non-refusals), health bracket (set1-health-bracket, not-measured paths), filing (set1-no-fit-filed with fakegh), borrow (set9-*, unreadable model, unknown --allow), layers (set2-layers-show with NOTE line), 119 proof (positive, none, config-held), 127 (gitignore line, hook that rejects tsv). Hostile QA: a repo whose hook rewrites files on commit (covered by rollback and real-commit choice). Chaos: kill mid-run. Flakiness: none time-dependent except the health limit, shortened by an override. Eval suites: not applicable (no LLM prompt change).
Section 7 Performance: health at both ends is about 8 s per real adoption, opted out in tests; the slowest new codepaths are the two health runs and the 120 s ceiling; p99 bounded by that ceiling.
Section 8 Observability: setup output is the log (HEALTH START, GAP, GUARD, borrow, NOTE, ADOPTION VERDICT), the findings file holds gaps, the commit message records the start state. Debuggability after 3 weeks: the commit message plus findings plus verdict reconstruct the run. No dashboard needed.
Section 9 Deployment: ships in the skills package; other repos receive it through update, behavior applies to new setup runs only. Rollback: revert the release. Capacity halt protocol is the pre-deploy gate for size. Post-deploy: run setup --dry-run on a scratch repo.
Section 10 Long-term trajectory: debt: hosts at 94-97% of the line, `resolve()` display-only, no cap-aware health rule (deferred). Reversibility 4/5 (code only, no data migration). The 1-year question: a new engineer will not expect hooks in agents.py or the guard in update.py; the map in part 0 and module docstrings are the mitigation.
Section 11 Design: SKIPPED (no UI scope).

#### NOT in scope
Deferred: health rule counting the packaged file against the cap; routing all config readers through layers.resolve (both recorded in plan part 15, no TODOS.md).
Rejected: `--allow-private` escape for the staged guard (defeats done line 6); recording adoption outcomes privately (no metrics surface); operational-state tracking beyond the verdict.

#### What already exists
seed.decide/apply (plan and write), survey.ignored (exact exception lines), private.py hook staged (name scan), health check/file/preview (verdict and filing), criteria.py render, regression.py add/red, fakegh and make.sh, sync.py's temporary worktree. Plan reuses all; rebuilds nothing except PR 83's fix.

#### Error & Rescue Registry
| capability | what can go wrong | exception | rescued | rescue action | user sees |
|---|---|---|---|---|---|
| Txn snapshot | unreadable path | OSError | Y | refuse before any write | REFUSED line, nothing written |
| Txn rollback | restore fails | OSError | Y | continue, then name the paths | REFUSED could not restore, exit 2 |
| signal or exception mid-write | interrupt | KeyboardInterrupt, Exception | Y | rollback, re-raise, exit 130 | nothing written |
| health bracket | check crashes or times out | TimeoutExpired, CalledProcessError | Y | print not measured (reason) | HEALTH START or VERDICT not measured |
| filing | gh missing or fails | OSError, CalledProcessError | Y | NOTE, keep commit, count as gap | NOTE and GAPS (1 step failed) |
| guard_staged | match found | n/a (refusal) | Y | rollback, exit 1 | file:line or key, never the value |
| repo commit hook | hook refuses | CalledProcessError | Y | rollback, print hook output and exemption | GUARD line and REFUSED |
| borrow | model unreadable | OSError, ValueError | Y | refuse, nothing written | REFUSED --from |
| runs_tests | no pattern | none | Y | empty checks, no-fit finding | no fit line |
CRITICAL GAPS: 0.

#### Failure Modes Registry
CODEPATH | FAILURE MODE | RESCUED? | TEST? | USER SEES? | LOGGED?
Txn.rollback | restore error | Y | Y (row 120) | REFUSED + exit 2 | Y
mid-run interrupt | half write | Y | Y (kill case) | nothing written | Y
post-commit step | hook, private, filing fail | Y | Y (set1-never-blocks) | NOTE + GAPS | Y
health bracket | timeout, crash | Y | Y (set1-health-bracket) | not measured | Y
filing | gh signed out | Y | Y | NOTE N items left | Y
guard_staged | false positive | Y (three non-refusals tested) | Y | named file:line | Y
capacity | host over the line | Y (audit, halt) | Y (gate list) | Capacity halt commit | Y
CRITICAL GAPS: 0.

#### Dream state delta
This plan leaves adoption finished, verified and honest about gaps; it does not give one resolver for every reader, a package with free slots, or an adopter-facing success metric. The first two are named deferred or owner questions.

#### Diagrams produced
System architecture (section 1), data flow with shadow paths (section 4), error flow (registry), deployment sequence (audit, moves, behavior, docs), rollback flow (Txn). Stale diagram audit: no ASCII diagram exists in the touched files; 0 stale.

#### Completion Summary
  Mode selected: SELECTIVE EXPANSION | System audit: package at 99/99, health Mine runs commands, capacity room 33 KB vs 25 KB needed
  Section 1: 1 issue (capacity cliff) | 2: 9 paths, 0 gaps | 3: 4 issues, 1 High mitigated | 4: 7 shadow paths, 1 unhandled before (interrupt), now handled
  5: 2 issues | 6: diagram produced, 6 gaps closed by named cases | 7: 1 | 8: 0 gaps | 9: 1 risk | 10: reversibility 4/5, 3 debt items | 11: SKIPPED
  NOT in scope: written (5 items) | What already exists: written | Dream state: written | Error/rescue: 9 rows, 0 gaps | Failure modes: 7, 0 gaps
  Scope proposals: 5 proposed, 2 accepted | CEO plan: written (autoplan scope summary) | Outside voice: Codex completed, native completed
  Lake Score: N/A (no scored question was asked; unattended) | Diagrams: 5 | Stale diagrams: 0 | Unresolved decisions: 3 (UC1, UC2, plan approval) | Reality rows: 7/7, unverified=1

### DX review (phase 2.5), mode DX POLISH (auto)

Product type: Claude Code skill with a CLI (`setup.py`, `settings.py show`, `setup --from`). Classification taken automatically.

#### Developer persona card
Who: a solo owner (or the owner's coding agent) adopting an existing repo into the workflow loop, most often in one terminal session. Context: has a repo with tests and CI, a bare or Codex agent command, maybe a `.gitignore` that blocks `*.tsv`. Tolerance: about 5 minutes and 3 commands before giving up; will not read the page before the first run. Expects: a dry run first, nothing written when it stops, and a plain statement of what is left. The agent is the second reader of every error line.

#### Developer empathy narrative (predicted, not observed)
I ask my agent to adopt this repo. It runs `setup.py --dry-run` and I see a long list: files to add, files to convert, a GUARD line about my pre-commit hook, a HEALTH START line. I do not know yet which lines I must act on. I run it for real; about 8 seconds of health checks pass in silence, then a commit lands on a branch. The last line says ADOPTION VERDICT: GAPS with four lines above it, each with a fix. I like that. What I do not know: whether exit 0 means I am done, whether issues were filed in my tracker without my asking, and why my agent still cannot run goals (the private command is still the default). Predicted confusion, labelled as such: nothing in the plan shows me the exact output of a good first run.

#### Competitive DX benchmark (reference benchmarks, [estimated], no web research: no network is allowed in this run)
| Tool | Start to result | Time and evidence type | DX choice | Source |
|---|---|---|---|---|
| plain "copy the template and edit" | clone to first goal | about 20 min [estimated] | no verdict, no checks | reference |
| a scaffold CLI with `--dry-run` (reference class) | command to written files | 1 to 3 min [estimated] | prints plan first | reference |
| this plan (post-review) | `setup --dry-run` to verdict line | about 2 min including 2 health runs of about 4 s [estimated, re-measure before gate] | verdict is the product's own health check | plan parts 3, 10 |
Target tier: Competitive (2 to 5 min), taken automatically; Champion is not realistic while two health runs and a branch commit are in the path.

#### Magical moment
The single `ADOPTION VERDICT:` line with each gap and its fix printed above it. Delivery vehicle: the existing terminal output of `setup.py` (lowest effort, uses existing capability; a hosted report is out of scope).

#### Developer journey map
STAGE | DEVELOPER DOES | FRICTION POINTS | STATUS
1. Discover | reads the skill description, runs `setup.py --dry-run` | no copy-paste quickstart shown | fixed (docs obligation)
2. Install | copies skills beside each other | installer defaults to one agent's folder (install-local.sh:5) | deferred (outside touches)
3. Hello World | real run, reads the verdict | exit 0 hides gaps; no sample output | fixed (--strict, sample output)
4. Real Usage | files the findings, fixes gaps, starts a goal | private agent command still default; filing default-on | partly fixed (agent-tools names both; filing is User Challenge UC1)
5. Debug | reads a REFUSED or NOTE line | no codes, no trace, hook output may echo a name | fixed (codes, trace, masking)
6. Upgrade | runs update, keeps local fixes | moved functions break a kept old file | fixed (aliases, previous-release test)

#### First-time developer confusion report
T+0:00 runs `setup.py --dry-run`, sees 11 plan lines and a HEALTH START; unclear which need action (addressed: legend table).
T+0:30 runs for real; no output for 4 s while health runs (acceptable; a line `measuring health...` is a build detail).
T+1:00 sees GAP: agent_command; fixes the repo setting; later finds the private command still wrong (addressed: agent-tools names both).
T+2:00 sees NOTE items left, files them; (UC1 stays with the owner).
T+3:00 wants to know the exit code meaning in CI; (addressed: --strict, documented exit codes).

#### DX dual voices
Native subagent: 14 findings (CAP4 x2, CAP6 x4, high x1, medium x7). Codex (completed): 8 findings (high x6, medium x2).
DX DUAL VOICES - CONSENSUS TABLE:
  Dimension                           Claude  Codex  Consensus
  1. Getting started < 5 min?          gap     gap    CONFIRMED (no stated time, no sample output, unusable agent after adoption)
  2. API/CLI naming guessable?         gap     gap    CONFIRMED (large prefix vocabulary, several surfaces)
  3. Error messages actionable?        gap     gap    CONFIRMED (exit 0 channel, no codes, no trace)
  4. Docs findable & complete?         gap     gap    CONFIRMED (no copy-paste, spread over four files)
  5. Upgrade path safe?                ok      gap    DISAGREE (Codex only: moved functions break a kept old file; verified at update.py:187, accepted)
  6. Dev environment friction-free?    gap     gap    CONFIRMED (escape hatches, Codex-only default command)

Dispositions (auto-decided): accepted as obligations (see the dx accepted block): exit-code channel with `--strict`; masked relayed hook output; trace for unexpected failures; partial-outcome wording; stable codes; legend, flags table, exit codes, quickstart and examples; index preservation; aliases for moved names; `show` masking; `agent-tools` names both commands; verdict line last and unread counted. Rejected: `--allow-private` (defeats done line 6). Deferred (plan part 15 additions, TASTE): `--no-hooks`, an adoption `--json` result contract, a stored-versus-effective split in `show`, one consolidated readiness check across agents, installer defaults for other agents. Filing opt-in: joins User Challenge UC1 (now three voices).

#### Error path matrix (agent-ready-v1), after the accepted fixes
Path | Class | what | fix | recovery | code | context | trace | redaction | channel | Cap
refused (dirty agent file) | usage | pass | pass | N/A | pass | N/A | N/A | pass | pass | none
restore failed | environment | pass | pass | pass (partial, do not rerun) | pass | pass | N/A | pass | pass (exit 2) | none
unexpected exception | unexpected | pass | pass | pass | pass | pass | pass (path) | pass (masked) | pass (exit 1) | none
post-commit step failed | partial | pass | pass | pass (safe to rerun) | pass | pass | N/A | pass | pass with --strict (exit 3) | none
hook refused commit | environment | pass | pass (exemption line) | pass | pass | pass | N/A | pass (masked) | pass (exit 1) | none
Before the fixes: CAP4 on post-commit channel (exit 0) and on relayed hook output (redaction); CAP6 on trace, recovery, context.

#### DX scorecard
+====================================================================+
| Dimension            | Score  | Prior  | Trend  |
| Getting Started      | 6/10   | 5/10   | up     |  (plan states no timing; quickstart and verdict-first output added)
| API/CLI/SDK          | 7/10   | 6/10   | up     |  (legend, flags table; vocabulary stays large)
| Error Messages       | 8/10   | 4/10   | up     |  (CAP4 and CAP6 fixed in the plan; not measured in a run)
| Documentation        | 7/10   | 5/10   | up     |  (canonical page with examples)
| Upgrade Path         | 7/10   | 5/10   | up     |  (aliases, previous-release test)
| Dev Environment      | 6/10   | 5/10   | up     |  (opt-outs for health and issues; no --no-hooks)
| Community            | N/A    | N/A    |        |  (not applicable: personal skills package)
| DX Measurement       | 5/10   | 3/10   | up     |  (no TTHW instrumentation; deferred)
| TTHW                 | 2 min [estimated] | not stated | |
| Competitive Rank     | Competitive                                  |
| Magical Moment       | designed via the verdict line in terminal output |
| Product Type         | Claude Code skill and CLI                    |
| Mode                 | POLISH                                       |
| Overall DX           | 7/10   | 5/10   | up     |
+====================================================================+
DX principle coverage: Zero friction covered (dry run first); Learn by doing partial (quickstart added); Fight uncertainty covered after fixes (codes, trace, verdict); Opinionated defaults with escape hatches partial (no --no-hooks); Code in context covered (sample output); Magical moments covered; Agents are users covered after fixes (exit codes, codes).

Passes 1 to 8: 1 Getting started 6/10 (gap: no stated time or sample output; fix: quickstart); 2 CLI 7/10 (gap: prefix legend); 3 Errors 8/10 after fixes (was capped at 4/10 by CAP4:post-commit:channel and CAP4:hook-output:redaction; CAP6 on trace, filing recovery, restore recovery, NOTE context, and missing codes); 4 Docs 7/10; 5 Upgrade 7/10 (alias fix); 6 Environment 6/10 (CI exit codes added; Windows not claimed); 7 Community N/A (not a public product surface in this goal); 8 Measurement 5/10 (a TTHW measurement is deferred: it would need a newcomer run).

#### DX implementation checklist
[x] Time to first verdict under 5 minutes (estimated 2 min, re-measure at the gate)
[x] Install is the existing skills copy (unchanged)
[x] First run ends in a meaningful verdict line
[x] Magical moment delivered via the terminal verdict
[x] Every error line carries a code and a fix (parts 2, 4)
[x] Names are consistent: lowercase plan lines (add, convert, borrow, adapt, skip), uppercase outcomes (GAP, GUARD, NOTE, REFUSED, HEALTH START, ADOPTION VERDICT); legend documents the split
[ ] `--no-hooks` escape hatch (deferred)
[x] Docs have copy-paste examples (part 14)
[x] Upgrade path keeps old files importing (part 1)
[x] Works in CI with `--strict` and documented exit codes
[ ] TTHW instrumented (deferred)

#### NOT in scope (DX)
`--no-hooks`; adoption `--json` result contract; stored-versus-effective split in `show`; consolidated readiness check across agents; installer defaults for other agents; TTHW instrumentation. Each deferred to plan part 15 (no TODOS.md).

#### What already exists
Dry run, `NO CHANGE`, `fakegh`, `settings.py reference`, update's LOCAL FIX handling, health rows with fixes, `references/settings.md`.

#### Implementation tasks (DX)
- T1 (P1) exit codes and `--strict` in `setup.py`; verify: row `set1-never-blocks` asserts exit 3 with `--strict`.
- T2 (P1) code suffixes, trace file, masked hook output; verify: `setup-refusal-writes-120` and `setup-tsv-guard-127` assert the code and no private text.
- T3 (P1) index preservation in `Txn`; verify: three fixtures in `setup-refusal-writes-120`.
- T4 (P1) aliases and previous-release run; verify: `setup-fit`.
- T5 (P2) `show` masking; verify: `set2-layers-show`.
- T6 (P2) Usage page quickstart, legend, flags table, exit codes, examples; verify: `docs.py check` and a manual read.

### Eng review (phase 3)

#### Step 0 scope challenge
Premise table (premise | claim | file:line receipt | verdict):
| E1 | setup commits the whole index | skills/workflow-setup/scripts/setup.py:290 | verified |
| E2 | setup stages whole folders with add -A | skills/workflow-setup/scripts/setup.py:284 | verified |
| E3 | dirty-agent refusal exits 2 and uses (SETUP_AGENT_FILE_DIRTY) | skills/workflow-setup/scripts/setup.py:272-275 | verified |
| E4 | the plan is computed before the branch switch | skills/workflow-setup/scripts/setup.py:235 and :274 | verified |
| E5 | git hooks install after the commit today | skills/workflow-setup/scripts/setup.py:215 and :291 | verified |
| E6 | health file reconciles, closes and reopens issues | skills/workflow-health/scripts/file.py:150-163 | verified |
| E7 | file apply creates labels with --force | skills/workflow-health/scripts/file.py:209 | verified |
| E8 | health.py check has --skip | skills/workflow-health/scripts/health.py:323 | verified |
| E9 | update keeps a locally edited file on its own | skills/workflow-setup/scripts/update.py:181-195 | verified |
unverified=0

REALITY: premise-table pass 9 of 9 eng premises verified against code; two collisions found (exit code 2, code naming) skills/workflow-setup/scripts/setup.py:272-275
REALITY: already-done pass `git log origin/main` since 2026-11-11 on skills/workflow-setup and skills/workflow-health printed no commit; base is b7bfe4e
REALITY: surface-check pass `health.py check --skip`, `regression.py red` exist; `health.py file --open-only` is new and must be added to file.py skills/workflow-health/scripts/health.py:323
REALITY: binding-decisions pass no branch decision records and no Binding decisions section; the frozen done lines bind .loop/goals/setup-adopt-2.md:1
REALITY: numbers pass sizes are [measured: wc -c] skills/workflow-setup/scripts/setup.py:1 and byte additions are [estimated] and [re-measure before gate] dev/package.py:26
REALITY: deferred-asks pass issues 119, 120 and 127 each have a row and no ask is left out .loop/goals/setup-adopt-2.design.md:49-51
REALITY: pr-count pass one pull request; no ship policy file exists so the default one PR per wave holds; both outside voices suggest splitting, kept as User Challenge UC2 .loop/goals/setup-adopt-2.md:1

Complexity check: about 19 changed files (setup, agents, seed, survey, settings, sync, update, report, controls, rules, file, 4 docs and references files, regression.tsv, reap.sh, 2 existing toys edited, 2 new toys) and 1 new class (`Txn`). 8+ files trips the structure question: Original arrangement (fold into existing files because the package has no free slot) versus Smaller arrangement (none exists that keeps the done lines under the 99-file cap). Decision: Original arrangement, auto-decided (P5: the fold is already the smaller arrangement; a smaller one would drop done lines). Scope Challenge result: scope accepted as-is.

Search check: no new framework, no new infrastructure; transaction by snapshot and journal is plain git plus stdlib [Layer 1]. [Layer 3] note: an isolated git worktree makes "nothing written" true by construction (it is how update's temporary worktree works); kept as a Taste decision, not adopted, because the done lines say adoption applies on a branch in the owner's checkout and the design chose snapshot rollback.

#### Dual voices
Native subagent: 15 findings (5 High, 5 Medium, 4 Low, 1 supportive). Codex (completed): 9 findings (6 High, 3 Medium).
ENG DUAL VOICES - CONSENSUS TABLE:
  Dimension                           Claude  Codex  Consensus
  1. Architecture sound?               gap     gap    CONFIRMED (partial-staging/dirty-path commit, branch binding, cohesion debt)
  2. Test coverage sufficient?         gap     gap    CONFIRMED (hard-kill, mixed-version, pytest-style, filing cases)
  3. Perf risks + budget/bench named?  gap     ok     DISAGREE (Claude: lane time of 14 land rows; Codex silent; measure lane first, accepted)
  4. Security threats covered?         gap     gap    CONFIRMED (filing target and text, --from validation, masking)
  5. Error paths handled?              gap     gap    CONFIRMED (SIGKILL, child shutdown, post-commit outcomes)
  6. Deployment risk manageable?       gap     gap    CONFIRMED (cap margin, mixed-version upgrades)
5/6 confirmed; 1 disagreement is a taste item.

Dispositions (auto): accepted (see the eng accepted block): prechecks with codes; dirty planned path refusal; exact write-set staging with per-file hashes; durable journal, child reaping and ref reconciliation; additive `file --open-only`, `GH_REPO`, private screening and printed targets; findings ownership; content-based runner choice; ignore re-check and CRLF; `--from` validation; masking; dry-run hash around health; both-direction mixed-version test from local history; lane measurement; Txn built and measured first. Exit-code and code-name collisions with today's code fixed (parenthesized `SETUP_*` codes, exit 2 kept for dirty files, half-undone is exit 4). Rejected: none. Taste: worktree transaction (kept Txn), cohesion debt (deferred with the file cap). User Challenge: UC1 filing default and UC2 goal split stay with the original direction (now four voices).

#### Section 1 Architecture
Dependency graph (new blocks marked *):
  setup.py --> agents.py (reply_hook, HOOKS, git_hooks*, health*) --> health.py check --skip mine (subprocess)
  setup.py --> seed.py (decide, apply, Home*, findings*, convert*) --> survey.py (runs_tests*, ignored*, guards*, borrow*)
  setup.py --> sync.py (Txn* journal, rollback) ; update.py (guard_staged*) ; settings.py (resolve*, show*, private_value*)
  setup.py --> health.py file --open-only* (subprocess, GH_REPO)
No cycle: settings is the leaf. Coupling: new coupling setup -> health by subprocess only (already exists for the guard scan). Scaling: bounded by repo size (snapshot of the written-into folders, hashes) and two 120 s health runs. Single points of failure: the one commit and the journal; both guarded. Security: no endpoint; remote writes limited to additive issues to the origin repo with screened text. Rollback posture: journal-based recovery at the next run.
Design-twice (new boundary `Txn`): second shape = isolated worktree transaction (write in a temporary worktree, fast-forward on success). Depth: the worktree hides more (no snapshot, index or sweep logic) behind a smaller interface; cost: the owner's checkout would not show the adoption until merged and untracked/ignored working files must be copied in; and `update` already uses this pattern. Pick: keep snapshot Txn for this goal (done lines say applies on a branch in the checkout; design settled), record the worktree shape as the preferred successor (Taste, gate). Red flags screened: shallow module (Txn is deep: one call, large behavior); split ownership (one owner of state: Txn); two ways to do one task (aliases keep one old name per moved function, documented); hand-synced list (the host table in part 0 is generated by the audit, not hand-kept: audit commit rewrites it with measured numbers).

#### Section 2 Code quality
Findings: [INFORMATIONAL] (confidence: 8/10) skills/workflow-setup/scripts/setup.py:284 `git add -A -- paths` stages folders; replaced by exact write-set staging. [INFORMATIONAL] (confidence: 8/10) setup.py:290 commits the whole index; replaced by pathspec commit. [INFORMATIONAL] (confidence: 7/10) setup.py:255 `return code` mixes refusal and strict meaning; fixed by the exit-code table. Cohesion: moved blocks live in unrelated hosts; debt recorded in part 15 with aliases. Shared code: `private_value` is one function used by guard, borrow, show, hook-output and issue text (five callers, one definition, net savings). Diagrams in touched files: no ASCII diagram exists; the Txn state machine below should be added as a module comment in sync.py.

Txn state machine:
  CLEAN --journal--> SNAPSHOT --writes--> WRITTEN --stage+guards--> STAGED --commit--> COMMITTED --post steps--> DONE
     |                  |                     |                        |                |
     +--refusal/error/signal (before COMMITTED)--> ROLLBACK --> CLEAN or HALF_UNDONE(exit 4)
  signal after ref moved with the write set --> COMMITTED (no rollback)

#### Section 3 Test review (diagram)
CODE PATHS                                                   USER FLOWS
[+] setup.py main                                            [+] adoption run
  +-- prechecks (5)                    [GAP->planned] x5      +-- [planned] dry run, then real run, then NO CHANGE
  +-- plan against one revision        [GAP->planned]         +-- [planned] refusal leaves nothing (each path)
  +-- health start/verdict             [planned] x4           +-- [planned] strict exit 3 in CI
  +-- Txn snapshot/journal/rollback    [planned] x6           [+] settings show
  +-- filing --open-only               [planned] x5           +-- [planned] layers, withheld, NOTE
  +-- post-commit failures             [planned] x3           [+] setup --from
[+] survey.py runs_tests/ignored/guards/borrow               +-- [planned] borrow, held, skip, refuse
  +-- unittest, pytest-style, none, config-held [planned] x4
  +-- ignore re-check, CRLF            [planned] x3
[+] settings.py resolve/show/private_value [planned] x4
[+] health report.py no-fit, agent-tools [planned: negative controls] x2
COVERAGE: planned 38/38 paths have a named case inside the 19 rows (0 untested by design); executed coverage is 0 until built (no code exists).
QUALITY: every planned case is behavior plus an error or edge path; no smoke-only case. GAPS: 0 required rows added (the 19 are frozen), 20+ cases named inside existing rows. [->E2E]: rows adopt-fixture-* and setup-fit (nightly, real git); [->EVAL]: none (no LLM change).
Test plan artifact written to disk (outside the repo, in the review state folder; path in the Completion Summary). Value cards are in that file.
Hostile QA: a repo hook that rewrites files at commit; a branch checked out elsewhere; SIGKILL; fork remote; a planned path dirty. Chaos: kill during a blocking hook. Flakiness: the health time limit is shortened by an environment override; signals use fixed sleep points in the toy hook, not wall-clock races.

#### Section 4 Performance
Two health runs (about 4 s each on this repo, [estimated], unmeasured on large repos) bounded by 120 s each; snapshot cost is proportional to files in `.loop`, the wiki folder, workflows and agent files (hundreds, [estimated]); hashing is O(bytes) of those. Slowest new paths: health runs, issue filing (n gh calls), test-proof file scan (`git ls-files` once). No N+1: filing is one call per issue by design (bounded by 4 kinds). Land-lane budget: 14 land rows at about 40 s each is about 9 min [estimated, re-measure before gate]; lane time is measured first and rows move to nightly if the lane would pass 15 min.

#### NOT in scope (Eng)
Isolated worktree transaction as the adopted design (Taste); cohesion refactor of folded blocks; `--no-hooks`; adoption JSON; TTHW instrumentation; health rule for the file cap; splitting the goal (UC2).

#### What already exists
git plumbing (`write-tree`, `read-tree`, pathspec commit), `survey.ignored`, `seed.decide/apply`, `private.py hook staged`, `update`'s temporary worktree pattern (sync.py), health `check --skip`, `file.py` plan/apply, `fakegh`, `reap.sh`.

#### Failure modes registry
CODEPATH | FAILURE MODE | RESCUED? | TEST? | USER SEES? | LOGGED?
Txn.rollback | restore error | Y | Y | REFUSED exit 4, Side effects partial | Y
signal mid-write | interrupt, SIGKILL | Y (journal recovery) | Y | recovered at next run | Y
signal during commit | ref moved or not | Y (reconcile) | Y | committed or rolled back, stated | Y
dirty planned path | owner edits | Y (refusal) | Y | SETUP_PLANNED_PATH_DIRTY | Y
repo state | merge, detached, unborn | Y (precheck) | Y | SETUP_REPO_STATE | Y
branch diverged | plan and apply differ | Y (refusal) | Y | SETUP_BRANCH_DIVERGED | Y
filing | fork, gh down, partial | Y | Y | NOTE with finish command | Y
filing text | private value | Y (skip) | Y | NOTE | Y
mixed versions | old agents.py | Y (precheck) | Y | SETUP_MIXED_VERSION | Y
capacity | host over the line | Y (audit, halt) | Y (gate list) | Capacity halt commit | Y
CRITICAL GAPS: 0.

#### Parallelization strategy
| Step | Modules touched | Depends on |
| Capacity audit and pure moves | skills/workflow-setup scripts | - |
| Txn, prechecks, journal | skills/workflow-setup scripts (sync, setup, update) | pure moves |
| Health rules and file --open-only | skills/workflow-health scripts | - |
| Survey, seed, settings blocks | skills/workflow-setup scripts (survey, seed, settings) | pure moves |
| Fixtures, rows, docs | dev/toy, .loop, docs/wiki, references | all of the above |
Lane A: audit, moves, Txn, then survey/seed/settings (shared setup folder, sequential). Lane B: health rules and `file --open-only` (independent module). Launch A and B; merge both; then fixtures, rows and docs. Conflict flag: `setup.py` is shared by Txn and wiring work (sequential in lane A); the next goal edits the same files, so land this PR first.

#### Completion summary
- Step 0: Scope Challenge: scope accepted as-is | Reality rows: 7/7 applicable rows emitted (PLAN_REALITY complete), unverified=0
- Architecture Review: 4 issues found (branch binding, dirty planned path, journal, exit-code collision) | Code Quality Review: 3 issues found | Test Review: diagram produced, 0 required gaps, 20+ named cases | Performance Review: 1 issue (lane time)
- NOT in scope: written | What already exists: written | TODOS.md updates: 0 written (no TODOS.md; deferrals in plan part 15) | Failure modes: 0 critical gaps
- Unresolved decisions: 3 in this review (UC1, UC2 carried, plan approval) | Outside voice: Codex completed, native completed | Parallelization: 2 lanes, 1 parallel / 3 sequential | Lake Score: N/A

