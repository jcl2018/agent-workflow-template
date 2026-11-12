# Plan: setup-adopt-2

Goal file: `.loop/goals/setup-adopt-2.md` (frozen done lines 1 to 8). Design file: `.loop/goals/setup-adopt-2.design.md` (Approach B, approved). This plan meets the done lines as written and does not change them. Nothing here is approved by the owner, merged or pushed.

Privacy note: this file was scrubbed before commit; local absolute paths became repo-relative paths, and tool and owner names were left out.

Hard limits carried into every part: every script under 20,480 bytes (health warns at 18,432); `skills/*/SKILL.md` under 150 lines; `python3 skills/workflow-docs/scripts/docs.py check` prints DOCS OK; no private names, paths or emails in any commit or the PR body; milestones are free form (setup makes and asks for none); Reviewed lines of `docs/wiki/Setup.md` (SET-2, 3, 4, 5, 6, 7, 8, 9, 10) are not edited, SET-1 stays Unreviewed text and is not reworded; only Usage, Tests and Unreviewed text change there; the ci-minutes-template goal edits the same setup files next, so touches stay inside `skills/workflow-setup`, `skills/workflow-health`, `dev/toy`, `.loop/regression.tsv`, `docs/wiki/Setup.md`.

## Implementation plan

### 0. Package file count and sizes (decided first, it shapes every part)

Measured on main: `git ls-files skills | wc -l` is 96. The package check allows under 100 files (99 at most), so at most 3 new files under `skills/`. The design named six new scripts and one reference file; this plan folds them. The plan adds exactly 3 new tracked files under `skills/` (total 99); the new toy scripts live in `dev/toy` and are not packaged.

| Design module | Where it goes | New file? |
|---|---|---|
| `adopt.py` (transaction, rollback, verdict, filing, private-value guard) | `skills/workflow-setup/scripts/adopt.py` | new 1 |
| `borrow.py` (`--from`) | `skills/workflow-setup/scripts/borrow.py` | new 2 |
| `homewrite.py` (Home and README writer) | `skills/workflow-setup/scripts/homewrite.py` | new 3 |
| `hooks.py` (pure move of `reply_hook()` and `HOOKS`, 4,892 bytes) | folded into `skills/workflow-setup/scripts/agents.py` (8,023 to about 12,900 bytes; it already owns the agent-side wiring) | no |
| `layers.py` (resolver and `show`) | folded into `skills/workflow-setup/scripts/settings.py` as `resolve()` and a `show` subcommand (14,833 to about 17,000 bytes) | no |
| `adoptrules.py` (rules `no-fit`, `agent-tools`) | folded into `skills/workflow-health/scripts/report.py` (14,309 to about 15,900), registered from `rules.py`'s table; their negative controls in `controls.py` (12,641 to about 13,800) | no |
| `references/adoption.md` | folded into `skills/workflow-setup/SKILL.md` (86 lines, plus about 30) and a new "Layers" section in the existing `references/settings.md` | no |

Size gates: step zero (below) moves `reply_hook()` out of `setup.py` first (17,243 to about 12,350 bytes); the wiring budget in `setup.py` is 2,500 bytes (ends near 14,900), leaving about 3,500 bytes for ci-minutes-template. If any folded file measures above 18,432 after the change, the overflow moves into `adopt.py` or `borrow.py` (never into a fourth file). The `scripts` and `size` health rules and `python3 dev/package.py` are the proof; a closing step in part 14 re-counts `git ls-files skills | wc -l` and must print 99 or fewer. If the count would reach 100, `homewrite.py` folds into `seed.py` after moving `git_hooks()` and its three helpers into `agents.py`.

### 1. Step zero: pure move for size (no behavior change)

Move `HOOKS` and `reply_hook()` from `setup.py` into `agents.py` (names kept; `setup.py` imports it and keeps the `--reply-hook` and `--govern-hook` dispatch and the shared `refuse()`). Run the existing reply-hook and size rows before and after; the output of `setup.py --reply-hook` on a toy repo must be identical. Commit this move alone so a later regression bisects cleanly.

### 2. Transaction and rollback so a refusal leaves nothing written (issue 120)

In `adopt.py`, `Txn(repo, plan_paths)`:
- Before any write it records HEAD, the current branch, whether the `workflow-setup` branch exists, and for every path setup will write (config, queue, findings, pages, `docs.tsv`, rows, workflows, START.md, agent files, `.gitignore`, rendered `docs/wiki/Tests.md`) its prior bytes or absence. An untracked or ignored working-tree config is read first and counted as prior bytes (it is never overwritten; this closes inventory item 4).
- Run order in `setup.py`: plan, health start, write files, stage, scans and guards, commit, then only after a successful commit: git hooks, private settings (`fill_private` moves here, so a dry run and a refusal write nothing under the home folder), issue filing, health verdict. Hooks setup installs never run on its own commit.
- `Txn.rollback()` on every refusal after the first write: unstage, restore or delete each path, switch back to the original branch, delete the setup branch if this run created it, then a `git status` sweep for any path other tools wrote (for example `criteria.py render`). If a restore step fails it keeps going and prints `REFUSED: could not restore <paths> (<error>); the adoption is half undone. Fix: git status, then git checkout -- <paths>, git switch <original branch>, git branch -D <setup branch>` and exits 2.
- Remaining refusals keep their `REFUSED:` wording and exit codes: not a git repo, a dirty agent file, a private name, a SET-8 local setting or private value, the repo's own commit hook refusing. The bare `agent_command` and the `.gitignore` conflict stop being refusals (parts 3 and 4).
- Row `setup-refusal-writes-120` triggers each remaining REFUSED path in `dev/toy/test-setup-adopt.sh` and compares a full tree hash (tracked and working file bytes, `git branch`, `git stash list`, the index tree via `git write-tree`) plus a hash of the private home folder, before and after. Seen failing by `regression.py red setup-refusal-writes-120 --break "<restore old code>"` (part 12).

### 3. Never blocks, gaps filed as issues (SET-1, done line 1)

`setup.py` collects gaps in a list instead of refusing: a bare `agent_command` (`GAP: agent_command ... grants no tools. Fix: "agent_command": [...]`), pages with their own sections, unproven checks, a `.tsv` guard note, a source-ignored path. `adopt.py` writes one line per kind (at most 5 lines, so health's findings rule does not warn) to `.loop/findings.md` as `- [adoption] <kind>: <subject, subject, ...>. Fix: <fix>`; a rerun rewrites a line only when its subjects change. Setup exits 0 whenever the adoption is on its branch.

Health side (in `report.py`, registered in `rules.py`, controls in `controls.py`, rule table in `skills/workflow-health/references/commands.md`): Adoption rule `no-fit` turns each such findings line into one WARN row naming the subjects and the fix; Adoption rule `agent-tools` WARNs on a bare agent command and names its fix line. Each rule has a negative control (a fixture that must not fire), as every rule must. Existing `health.py file --group adoption` then files one issue per row with the group tag and, when a page owns the path, the feature (health's own longest-prefix rule; the `feature:<Page>` label only when `feature_labels` is on). Setup runs that filing itself when `gh` is signed in and the repo has a GitHub remote; otherwise it prints `NOTE: N items left in .loop/findings.md; file them with workflow-health file --group adoption`. `--no-issues` or `LOOP_NO_ISSUES=1` skips; the dry run prints `WOULD FILE`. Health's marks dedupe a second run. No label, milestone or issue is created by any test except through `dev/toy/fakegh`.

Rows: `set1-never-blocks` (bare agent plus `*.tsv` ignored: exit 0, adoption committed, `GAP:` lines, findings written), `set1-no-fit-filed` (two pages with their own sections give one findings line listing both and one filed issue tagged `adoption` through the stand-in; the filed count equals the `WOULD` lines of `health.py preview --group adoption`; a second run files none).

### 4. The `.tsv` guard handling (issue 127)

In `survey.py`:
- `survey.ignored()` also reports where the rule came from (`git check-ignore -v`). Only a tracked ignore file of the repo (root or nested `.gitignore`) is edited: `seed.decide` plans `convert: .gitignore (adds ...)` and `seed.apply` appends, under one comment line, the exact exception lines `ignored()` computes (for example `!.loop/` then `!.loop/*.tsv`); existing words are kept. A rule from `.git/info/exclude` or the global excludes file yields `GAP: <file> ignores <path>. Fix: add <exact line> to that file`, and the adoption stages the plan's paths with `git add -f`.
- `survey.guards()` reads the repo's hook files (`.githooks/`, `.husky/`, `.pre-commit-config.yaml`, the git hooks folder, scripts named for a guard or hook) for `.tsv` and prints `GUARD: <file> mentions .tsv; if it refuses tracked data files, exempt .loop/*.tsv (docs, regression rows and runs)` in the dry run and the run.
- If the real commit is refused by a repo hook, setup rolls back (part 2), prints the hook's own output and the same exemption line, and exits 1 with nothing written; a rerun after the owner adds the exemption adopts. Never `--no-verify`; setup never edits a hook that rejects tracked files.
- Docs: SKILL.md gains an "Adoption" paragraph (the two halves and the exemption line).
- Row `setup-tsv-guard-127`: the `.gitignore` half is exempted by a written line; a hook that rejects `.tsv` is named with its exemption and nothing is written.

### 5. The test-command proof (issue 119)

`survey.runs_tests(repo, command)` proves statically (nothing is executed) that a command finds at least one test by the runner's real pattern: unittest discover uses `-s` dir and `-p` pattern (default `test*.py`), pytest `test_*.py` and `*_test.py` (or the file's own config), `go test` `*_test.go`, `cargo test` a `#[test]` or `tests/` file. The suffix-only case: `tests/calc_test.py` yields `python3 -m unittest discover -s tests -p '*_test.py'`. If no pattern matches, fall back to a repo runner that exists (`tests/**/run.sh`, `scripts/run-tests.sh`, `scripts/test.sh`). With no proof the check list is empty, `no fit: .loop/regression.tsv (no check command found)` stays, and a `no-fit` finding is filed. One rule: surveyed guesses and CI-derived commands must pass the proof to become checks; a check the config already holds is kept as is and noted (`NOTE: <cmd> finds no test files`) when it fails the proof.

PR 83 re-implemented on current main (not merged from the stale branch): `seed.stored(config, old)` keeps a `checks` key the config already holds, and the seeded land rows run every check joined by `&&`. Surveyed checks still become rows, not a setting.

Rows: `setup-zero-tests-119` (a `*_test.py` repo gets a check; the test runs the proposed command in the stdlib-only fixture and asserts at least one test ran), `adopt-fixture-existing-checks` (part 11).

### 6. `setup --from <adopted repo>` (SET-9)

New `borrow.py`, read-only on the model (a local path; no network). Reads the model's `.loop/config.json` and `.loop/docs.tsv`; prints `borrow:`, `adapt:`, `skip:` and `held:` lines in the plan:
- Portable allowlist whose value differs from the default becomes this repo's value: parallel, max_tries, cadence, criteria, criteria_max, review_depth, token_budget, the `*_minutes` budgets, step_limit, goal_levels, ci_levels, pool_size, digest_mail, regression_cron, health_cron, feature_labels, stale_branch_days, silent_minutes.
- Never borrowed silently, printed `held: <key> = <value> (unattended or runs code; add --allow <key> to take it)` and taken only with `--allow KEY[,KEY]`: auto_approve, auto_merge, full_auto, mend, resume_on_limit, pr_bumps_version, reply_hook, govern_hook, agent_files, routines.
- This repo keeps its own: base, agent_command, version_file, template_*, session_command, digest_owner.
- Milestones: none created or copied; `feature_labels` and the page-set shape are borrowed; a model page with no matching area here is `skip:`; an old milestone in the model gets `skip: milestone <title> (free form, none made)`.
- Private rules, never values: the model's `risky_paths` regexes are borrowed; leak patterns and local rules live in the owner's private folder, so only `NOTE: your local layer already applies here` prints and no private file is read.
- One wording, stated once (closes reviewer note R3-1): a borrowed value failing the private-value check prints `skip: <key> holds a private value`, and a held value failing it prints `held: <key> (holds a private value; not shown)`; the value is never printed and is left out even with `--allow`.
- The private-value check (`adopt.private_value(text)`, shared with part 8): a home path, an email, a token-looking string, or a match in the owner's private-name list. An `--allow`ed value is screened by it and again by the SET-8 guard at staging.
- Borrowed values land through the normal config merge (the repo's own existing values win), so a second run changes nothing. Wiring in `setup.py`: `--from DIR` and `--allow`.
- Rows `set9-from-borrows` (borrowed, kept, held, absent until allowed, second run `NO CHANGE`, the model repo byte-identical) and `set9-from-no-values` (a model value holding a home path or an email is skipped and appears nowhere in output or written files).

### 7. The three settings layers and their display (SET-2, done line 3)

In `settings.py`: `resolve(repo)` returns, for every setting in the existing table, `(value, layer, home)` with layer `default` (the template table), `repo` (set in `.loop/config.json`) or `local` (set in the flow or health file under the owner's private folder, `$LOOP_FLOW` and `$LOOP_HEALTH` honored and named). Order default, then repo, then local, a later layer winning wherever a key appears in more than one. A private-home key found in the committed config shows `repo (local setting in a committed file)`, which is what SET-8 refuses. `settings.py show [--repo DIR] [--json]` prints `| setting | value | layer | home |` per setting; `reference` and `show` read the same table. About 40 scripts read `config.json` themselves and are not rewritten; `resolve()` is the single place for a cross-home override, and Usage and `references/settings.md` say that is the next step. Row `set2-layers-show` (default, repo and local values each show their layer; a local key in the committed config is flagged).

### 8. Refusing to commit a local setting or private value (SET-8, done line 6)

`adopt.guard_staged(repo)` runs after staging and before the commit, next to the existing `private.py hook staged` call. It reads the staged diff against HEAD and looks only at lines the adoption adds (never text the repo already had). It refuses with rollback, exit 1, naming `file:line` or the key and never the value, when an added line holds (a) a private-home key in `.loop/config.json` (`allowed_tools`, `leak_prefixes`, `full_markers`, `overrides`, `probe`, and any other key `settings.py` homes in the private folder), (b) the owner's home folder path or the git user email as an exact substring, or (c) an exact value of a local-layer string setting that holds `/`, `~` or `@`, is at least 8 characters, and is not a template default. There is no length-only rule. Values are read only to compare. These three refusals are the only content refusals and apply to what setup writes (including borrowed `--from` values). Rows `set8-local-setting-refused` and `set8-private-value-refused`; existing rows `set8-hooks` and `set8-setup-commit` stay and keep their `seen_red` dates.

### 9. Home and README writer, and the dry run that lists every file (SET-1, SET-7)

- `homewrite.py` writes the Home in the docs format: marker, `# <repo>`, `## Features`, one table whose header is read from workflow-docs' `pageformat.HOME`, one row per feature page linking its README section; and adds `## How to use` with one `### How to use <Feature>` section per page (intro line and the `| You say | What happens |` table with one row). The seeded Home no longer carries a `HOM-1` criterion or row. If a README exists only the missing section is added (words kept). Seeded PRD pages are shaped so the only gap left is UNWRITTEN. `docs.py check` is the oracle (no DOC-4, DOC-5, DOC-7, DOC-8 or link failure); reading the header from `pageformat` keeps the writer from drifting. Row `set1-docs-format`.
- Dry run (SET-7): `seed.decide` also plans the rendered `docs/wiki/Tests.md`, the `.gitignore` conversion, the git hooks, `borrow:` lines and `WOULD FILE`, and always prints the private half's keys as `would add to <private folder>`. The invariant test: the files in the real run's adoption commit are a subset of the dry run's `add:` and `convert:` paths, and a dry run leaves the tree, branches and home folder byte-identical. Second run: no commit, no gh write, `NO CHANGE`, clean tree, an untracked working config survives, and the two health lines still print. Rows `set7-dry-run-lists-all`, `set7-second-run-nothing`.

### 10. Health first and last as the adoption verdict (SET-1, done line 2)

`adopt.health(repo)` runs the sibling `workflow-health` `health.py check`. Before any write (dry run included: it is read-only and takes about 4 seconds) it prints `HEALTH START: <the check's HEALTH line>` or `HEALTH START: not measured (<reason>)` (workflow-health not beside workflow-setup, or the check errored, crashed or ran past 120 seconds). After the commit it runs the same full check on the branch and prints `ADOPTION VERDICT: GREEN` or `ADOPTION VERDICT: GAPS (<n> fail, <m> warn)` followed by every FAIL and WARN line the check printed (each carries its fix), or `ADOPTION VERDICT: not measured (<reason>)`. Setup exits 0 in every case. A dry run prints `HEALTH START:` and `ADOPTION VERDICT: not run (dry run)`; a real run and a no-change run both print both lines. The start state is also the second line of the adoption commit message. `--no-health` or `LOOP_NO_HEALTH=1` skips; `dev/toy/reap.sh` exports it (existing toys unchanged); the new tests unset it. Row `set1-health-bracket` (`HEALTH START:` precedes the first write line, `ADOPTION VERDICT:` is the last line, a non-green verdict lists each gap with its fix).

### 11. SET-6 fixture repos and nightly rows (done line 4)

New `dev/toy/test-adopt-fixtures.sh` (sources `dev/toy/reap.sh`, precise `# reads:` header) builds four fixture repos with `dev/toy/make.sh`: existing config checks (PR 83's shape), CI tests with a `.gitignore` blocking `*.tsv`, a bare `agent_command` with no CI, and features as milestones not folders (milestone data from the stand-in `fakegh`, nothing real). Nightly rows `adopt-fixture-existing-checks` (config checks kept, rows run every check; seen failing on v0.27.10), `adopt-fixture-ci-gitignore` (exception lines written, check from CI), `adopt-fixture-bare-agent` (gap named with its fix), `adopt-fixture-feature-milestones` (pages made, no milestone made). The existing `dev/toy/test-setup-fit.sh` gets its `.gitignore` and bare-agent expectations updated (they stop expecting a refusal) and a nightly row `setup-fit` (it had none). A comment in `dev/toy/test-adopt.sh` saying a bare agent command exits 1 after writing is corrected.

### 12. New tests, the 19 regression rows, and the Setup Tests table (done lines 7 and 8)

New `dev/toy/test-setup-adopt.sh` (sources `dev/toy/reap.sh`, precise `# reads:` header) holds the land rows' cases, one entry per row id, selectable by argument as `test-rows.sh` does. Order of work per row: write the case, add the row (`regression.py add ...`), commit (so `red` can break and restore), make it fail on old code (`regression.py red <id> --break "<cmd>"`; for new behavior the break is restoring the v0.27.10 skill folders into a scratch copy, for rows guarding behavior main already has such as `set7-second-run-nothing` it is a one-line mutation of the guard), then make it pass. The 19 rows: `set1-health-bracket`, `set1-never-blocks`, `set1-no-fit-filed`, `set1-docs-format`, `set2-layers-show`, `adopt-fixture-existing-checks`, `adopt-fixture-ci-gitignore`, `adopt-fixture-bare-agent`, `adopt-fixture-feature-milestones`, `setup-fit`, `set7-dry-run-lists-all`, `set7-second-run-nothing`, `set8-local-setting-refused`, `set8-private-value-refused`, `set9-from-borrows`, `set9-from-no-values`, `setup-zero-tests-119`, `setup-refusal-writes-120`, `setup-tsv-guard-127`. Levels as in the design (land for unit-sized, nightly for the fixtures and `setup-fit`). Lane budget is 15 minutes per lane; each new land case is measured so none runs past about 40 seconds (health at both ends is opted out except in the rows about it). Rows past the budget are left to the scheduled full suite. `criteria.py render` regenerates the Setup and Tests tables; the `no passing test` placeholders for SET-6, SET-7 and SET-9 disappear; the Tests table lists all 19 rows plus the existing `set8-hooks` and `set8-setup-commit`.

Done-line map: line 1 parts 3, 4, 9; line 2 part 10; line 3 part 7; line 4 part 11; line 5 part 6; line 6 parts 8, 9; line 7 this part; line 8 parts 2, 4, 5.

### 13. Files each change touches

| Change | Files |
|---|---|
| Pure move for size | `skills/workflow-setup/scripts/setup.py`, `agents.py` |
| Transaction, refusals, verdict, filing, private guard, working config | new `adopt.py`; `setup.py` (wiring only, 2,500 bytes budget) |
| 119 proof, `.tsv` guards, ignore source | `survey.py` (9,968 to about 13,500) |
| PR 83 keep checks, Tests.md listed, `.gitignore` convert, Home and README | `seed.py` (15,250, net change under 1,500), new `homewrite.py` |
| `settings show` and layers | `settings.py` |
| `--from` | new `borrow.py`; `setup.py` (flags) |
| Adoption rules `no-fit`, `agent-tools` | `skills/workflow-health/scripts/report.py`, `rules.py` (registration only), `controls.py`, `skills/workflow-health/references/commands.md` |
| Docs | `skills/workflow-setup/SKILL.md` (under 150 lines), `skills/workflow-setup/references/settings.md`, `docs/wiki/Setup.md` Usage, Tests and Unreviewed text only |
| Tests | new `dev/toy/test-setup-adopt.sh`, new `dev/toy/test-adopt-fixtures.sh`; edits to `dev/toy/test-setup-fit.sh`, a comment in `dev/toy/test-adopt.sh`, `dev/toy/reap.sh` (two exports); `.loop/regression.tsv` rows |

### 14. Docs and listing gates

- `docs/wiki/Setup.md`: Usage text gains the new output lines (`HEALTH START:`, `ADOPTION VERDICT:`, `GAP:`, `GUARD:`, `borrow:`, `held:`), `setup --from`, `settings show` and the changed refusals; the `REFUSED to call this done` and `REFUSED: nothing written. Fix .gitignore` usages are replaced. No requirement line changes. A `git diff` check confirms no changed line sits under a Reviewed marker.
- No new skill, so the catalog and `listing.json` are unchanged; `python3 dev/package.py` must pass (file count 99 or fewer, scripts under 20,480 bytes, no executable bits, no encoded blobs).
- Gates before the PR: `python3 skills/workflow-docs/scripts/docs.py check` prints DOCS OK; `python3 skills/workflow-health/scripts/health.py check` stays green on this repo (including the new Adoption rules); `lanes_cli.py check` passes; `dev/toy/test-tree.sh` passes; the pre-commit hook accepts every commit; `wc -c` of every changed script is under 20,480 and `wc -l` of every SKILL.md under 150; `git ls-files skills | wc -l` is at most 99.

### 15. Risks carried

- The Home writer must equal workflow-docs' own check (read `pageformat.HOME`; `docs.py check` is the oracle).
- Filing issues unprompted: only with a signed-in `gh` and a GitHub remote, off with `--no-issues`, deduplicated by health's marker, tested only through the stand-in.
- Rollback must restore every path including ones other tools write; `Txn` snapshots the plan's list plus a `git status` sweep, and the 120 row compares full tree hashes.
- Health at both ends adds about 8 seconds to a real adoption and nothing to tests (env opt-out).
- `.gitignore` exception lines change a file the repo owns: append-only, under a comment, shown in the dry run first.
- `resolve()` meets "later layer overrides" only inside a key's own homes until other readers adopt it; recorded in Usage.
- Folded modules grow `settings.py` and `report.py` near the warning line; the size row is the guard and overflow goes to `adopt.py` or `borrow.py`.

## Review record

