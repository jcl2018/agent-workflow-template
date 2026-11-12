# Plan: migration-check

Source: `.loop/designs/migration-check.md` (Approach B). Goal: `.loop/goals/migration-check.md`, done lines 1 to 11, frozen: this plan meets them, edits none, and lists none as an owner decision.

## Implementation plan

### 0. Verified facts (grep and wc on this branch, 2026-11-12)

- Package count: `git ls-files skills` is 96; `dev/package.py` counts those plus listing.json, README.md, LICENSE against `MAX_FILES = 99`. The package is full: no new file under skills/. Toys, rows and docs live outside skills/ and do not count.
- `defects.py` exists: 7,659 bytes (12,821 free). Other sizes match the design: update 20,458, sync 20,354, setup 20,340, survey 20,207, seed 20,174, goal 19,726, render 19,882, settings 19,243, rules 18,502, agents 18,275, workflows 17,778, board_page 15,459, operate 9,440, entry 15,031, report 16,816, enforce 5,490.
- Symbols exist: `entry.installed/lagging/version_key`, `render.refresh/stale_blocks/BUILT_IN/entries`, `deployments.owed`, `workflows.key_of/slots/load`, `docs.clone/wiki_url`, `agents.entry/apply/installed_version`, `sync.base_of/base_config` (sync.py imports agents already), `board_page.template_lag`, `controls.CONTROLS` auto-imports `defects.CONTROLS`, health.py line 218 merges `defects.FUNCTIONS` (so health.py and controls.py need no edit).
- Corrections to the design, taken here: (a) `settings.py` has no `set` command (only reference, fill-repo, fill-private, show), so every fix line that said "settings.py set mac" reads "set regression_runs to mac in .loop/config.json"; (b) `entry.py` takes `render|write|check|block`: `lag` is a new choice; (c) `entry.installed()` is empty for a checkout that holds the skills, so MIG_VERSION never fires in the template's own tree (as `lagging` already does) and toys set `LOOP_INSTALLED_VERSION`; (d) `settings.py reference --write` must be re-run (references/settings.md) because TABLE gains a row, and this repo's Home and README Settings blocks go stale for the same reason; (e) only FAIL and UNREAD make health "not green", so a WARN row from the new rule never turns this repo's own verdict.
- Found while planning (not in the design): (f) the Mac tick already honours `regression_runs: mac` for any repo (`workflows.py` line 278 `private = setting == "mac"`), but line 279 then prints `DRIFT: regression_runs says mac but the repo is public; run setup` for a public repo, and `seed.py` lines 156 to 158 rewrite a public repo's `regression_runs` back to `actions` on every setup re-run (the live visibility wins over the kept value). With the owner's 2026-11-12 rule (public repos also run regression on the Mac) a migrated public repo would show a standing DRIFT line and setup would undo the migration. Both are fixed in section 4. (g) `regression.py red` takes `--break CMD` (required), so each row needs a named break command (section 5). (h) The parallel goal operator-setup has only its goal file on its branch so far, and its done lines 8 and 12 overlap this plan:
  - it registers the same `<repo>-health-regression` task, so the name and the 4-hour rule live once, in `workflows.py`, and are reused;
  - it edits README.md, Tests.md, `.loop/regression.tsv` and `docs/wiki/Setup.md`;
  - it adds its own health Adoption check, a second name in the same `report.py` tuple;
  - it allows at most one new file under skills/, but the package has no free slot (99 of 99), so whichever goal needs a file must retire one first; this plan needs none.
- Done line 4 is already half built: `sync.py` line 197 writes `template_version` on `update --apply` and `setup.py` line 171 stamps it on adoption; the new work is only that a repo with none counts as behind (MIG_VERSION, v0) and a toy assertion that a repo is no longer behind after `update --apply` (added to migration-blocks-inserted). `update.py` line 366 already calls `sync.base_config`, so the alias in `sync.py` fixes done line 7 without editing `update.py` (verified).
- Review rounds already in the design: R2-1 (MIG_VERSION reads the working tree), R2-2 and R2-4 (MIG_CHECKS and the truth table for the Mac case) are settled below; R2-3 (symbols and sizes) is the list above.

### 1. Gap rules (the contract; codes are stable)

Engine `migration_gaps(root, online=True)` in `defects.py` returns `[(code, subject, what, fix)]`; no file written, no git write, wiki clone in a temp dir removed after. Numbers in square brackets are the goal's done lines the gap serves. "No version reads v0" means a repo whose config has no `template_version` is treated as version 0.0.0, so it is behind any installed template.

- Version rules in one table (done lines 4 and 5): held `template_version` absent: behind (v0), never refused; unparseable (`"v1"`, `"1.2"`, null, non-string): behind with the unparseable message, never refused; parseable with a differing major: behind and, for `goal.py new` only, refused (a `migrate-` slug passes); parseable, same major, older: behind, warn; equal: no gap; newer than installed: no gap, and the CHECKED line says `repo ahead of installed`. The CHECKED line also names the source of each read (`working tree` for the repo; `update.py --check` reads `origin/<base>`, which is why the two can differ).
- MIG_VERSION [4]: working-tree `.loop/config.json` has no `template_version`, or it is older than `entry.installed()`; text that does not parse (`"v1"`) says `unparseable template_version 'v1' (read as 0.0.0)` rather than a bare "behind". Never fires when installed() is empty (a checkout that holds the skills, such as the template's own tree, has no installed version to be behind). `update.py --check` alone reads origin/base. In health the `migration` rule skips this code: the `template-version` row reports it once, its detail starting `MIG_VERSION:`.
- MIG_FILES [1]: `entry.py check` STALE or MISSING lines (START.md, CLAUDE.md and AGENTS.md block); `.github/workflows/regression.yml` must be absent while `regression_runs` is mac (a leftover is a gap) and, with regression off, is not required; leftover `health.yml` is a gap; the setup-written bookkeeping files `.loop/queue.md`, `.loop/findings.md` and `.loop/regression.tsv` must exist (a missing one is a gap whose Fix is to re-run setup, which adds it; `.loop/docs.tsv` is excluded because a repo without it has no wiki by design, and the machine-local git hooks are excluded because health's `hooks` rule already covers them and they live outside the committed tree).
- MIG_SETTINGS [1]: a config key not in the settings table (unknown) or a table key missing.
- MIG_BLOCKS [11, 1]: `render.stale_blocks(root)`: the generated Settings and Automation blocks on Home and in the README, and the README template line (the "template link" of the goal header; it is the `README line` entry). MIG_AUTOMATION checks the config's `automation` entries and the three routines' settings; MIG_BLOCKS checks the rendered block. A repo can fail either alone.
- MIG_AUTOMATION [8], MIG_TASK [8] truth table: both crons valid, `regression_runs` mac: the registry task exists at 4 hours or shorter; `regression_cron` off: that entry must be explicitly off and `regression_runs` need not be mac; `health_cron` off with `regression_cron` on: gap (one task runs both: turn health_cron on); `regression_cron` off with `health_cron` on: the task is owed for health alone (4 hours or shorter), `regression_runs` need not be mac, no regression.yml and no land-row check; both off: nothing owed; `regression_cron` on with `regression_runs` actions or unset: gap, fix "set regression_runs to mac in .loop/config.json". MIG_TASK is skipped (printed `SKIP MIG_TASK (not a Mac)`, not counted) off darwin; the engine honours `LOOP_SCHEDULE_PLATFORM` only when `LOOP_TEST=1` is also set, so a stray variable cannot hide a real gap.
- MIG_CHECKS [1], settled (R2-2); it is this plan's reading of the goal header's "required checks are reported" (files only; a gh branch-protection read is out of scope because health makes no gh call): regression on the Mac and no regression.yml: require at least one `land` row in `.loop/regression.tsv` (what the PR check runs), read with the existing `defects.table(root)` (which already returns [] for a missing or unreadable file). `regression.yml` present: it must trigger on `pull_request`. Regression off means `regression_cron` is `off`: the check is skipped. With `regression_cron` on it runs whenever `regression.yml` is present (so a repo mid-migration shows both this and the leftover-file gap). MIG_FILES, MIG_CHECKS and the truth table agree: regression.yml exists only while regression runs in Actions.
- MIG_WIKI_ORPHAN, MIG_WIKI_STALE, MIG_WIKI_UNREADABLE [9]: the check lists and never deletes (it writes nothing); the owner's ruling to delete stale and old pages at migration (2026-11-11, quoted in done line 9) is carried by the orphan gap's Fix text, which names the delete step (`git rm -- <page>.md` in the wiki clone, commit, push, run by the owner after the merge); MIG_RUNBOOK [10] (`docs.py check` Runbook lines); MIG_FORMAT (other `docs.py check` lines).
- No `--json` (decided: the health rule and the queue function call the engine as a function, so no script consumes JSON; the design's flag is dropped, about 250 bytes saved, one fewer path to test).
- Classes: PR-closable (VERSION, FILES, SETTINGS, BLOCKS, AUTOMATION, RUNBOOK, FORMAT, CHECKS) vs state (TASK, WIKI_*). `--pr` checks the PR-closable set; `--offline` skips only the three wiki codes. Output `GAP <CODE> <subject>: <what>. Fix: <fix>`, then one `NOT CHECKED:` line saying what this run did not verify (always `branch protection (no gh read)`, and for a repo recorded mac `pull-request-time regression check (none exists in mac mode)`; with `--pr` the state codes; with `--offline` the wiki codes; off a Mac the task), then one `CHECKED:` line with the facts the comparison used (template version installed, repo template_version, platform, mode `online` or `offline`, base ref), then one `DOCS:` line naming the page and section that explain every code (the Setup page's migration-check Usage table: code, cause, class, fix), which is each code's document target, then the last line `MIGRATION OK` or `MIGRATION: N gap(s) (a PR-closable, b state)`, each followed by a parenthetical when a flag skipped part of the check (`--pr`: `state codes not checked`; `--offline`: `wiki not checked`), so a script that reads only the last line cannot take a partial pass for a full one, exit 0 only when no gap is listed (NOT CHECKED items never change the exit code; they only qualify the result). The queued migrate goal's `--pr` done line is a stated deviation from the literal wording of done line 6 ("migration-check passing"), forced by feasibility: the state codes can only close after the merge, so a literal done line could never be met inside the goal; the PR description says so and the owner may overrule it in review. The qualifier keeps a green result from claiming more than files and git can show (inside the 1,900 budget of the engine's output function). No `.loop/docs.tsv`: no wiki, blocks, Runbook, format codes.

### 2. Byte budget per function and per target script (measure `wc -c` after every edit; plan at most 20,460; hard cap 20,480)

defects.py 7,659 to about 16,260 (hard stop 16,400): main/output 1,900 (output lines, CHECKED and DOCS, exit 4 and the trace file); version 700; files 800; settings 700; blocks 600; automation 1,300; task 1,300; checks 400; health wrapper and CONTROLS entry 900 (total 8,600). enforce.py 5,490 to about 8,190 (planning stop 9,000; the absolute stop is the 20,460 plan limit): the wiki half (clone, orphans, stale, 1,900) and the docs-check parse (Runbook and format, 800), moved there from the start behind a lazy `import enforce` inside `defects.main` (a byte-cap home, not a cohesion choice: a separate module would be the right home if the cap rises; setup's hard dependency on workflow-health is named in the Setup skill's SKILL.md and the Setup page) (the pattern `_c()` already uses for controls) (decided now rather than as a fallback: it keeps defects.py, the module health loads on every run, small, and enforce.py has 15,000 bytes free). Build the wiki function first and measure. Fallback if either file passes its hard stop: fold `checks` into `files`, then shorten the fix texts.

| Script | Now | Change | After | Fallback |
|---|---|---|---|---|
| agents.py | 18,275 | +1,650 (resolver 700, migration_check 450, blocks in apply 500) | 19,925 | shorten docstring; move migration_check into defects main, setup.py path-loads it |
| setup.py | 20,340 | +110 for the dispatch line and at least -120 from trimming the two long usage lines of the module docstring in the same edit | 20,330 or less (never above today's 20,340) | trim a third usage line |
| sync.py | 20,354 | -600 (base_of, base_config become agents aliases) | 19,754 | none needed |
| update.py, survey.py | full | 0 | unchanged | never touched |
| seed.py | 20,174 | net -30 or less: the one `regression_runs` line keeps a recorded `mac` and its trailing comment is shortened by more than the code grows | at most 20,174 | if it measures higher, shorten the next comment in the same function; never grow |
| settings.py | 19,243 | +850 (TABLE row 250, fill_automation 600) | 20,093 | compress fill_automation to a table of three tuples, then shorten the new row's one-line explanation |
| entry.py | 15,031 | +1,000 (lag, --new) | 16,031 | none needed |
| goal.py | 19,726 | +360 (subprocess call and the NOTE line) | 20,086 | rewrite the 9-line `_pods()` loader as a 5-line one (about 300 bytes saved) |
| rules.py | 18,502 | +600 (template_version behind row) | 19,102 | share the version read with defects |
| report.py | 16,816 | +12 | 16,828 | none |
| workflows.py | 17,778 | +150 (the `name` check, the 4-hour constant exported once, no DRIFT for a recorded mac, the tick's `LOOP_MIGRATION_ONLINE=1`) | 17,928 | none needed |
| render.py | 19,882 | +230 (`blocks` entry) | 20,112 | host the `blocks` command in docs.py (18,702, 1,778 free) calling `render.refresh` |
| board_page.py | 15,459 | +1,400 | 16,859 | split into operate.py |
| operate.py | 9,440 | +200 | 9,640 | none |

Rule: setup.py, update.py, sync.py, survey.py and seed.py end every edit at or below their current size (the owner's fold-or-trim rule); growth is allowed only in agents.py, settings.py, defects.py and the other scripts with room, and every growing script stays at or under 20,460.

### 3. Edit points and merge order with operator-setup (it also edits skills/workflow-setup and docs/wiki/Setup.md)

- setup.py: the final `if __name__` block gets one added line dispatching `migration-check` to `agents.migration_check`, and the module docstring's long usage lines are trimmed in the same edit so the file ends no larger than today. No change to argparse or `main()`.
- agents.py: new functions appended after `sibling`; `apply` edited in place; resolver functions placed next to `installed_version`.
- settings.py: one TABLE row after `regression_runs` (end of the repo group); `fill_automation` above `main()`; `fill_repo` calls it.
- SKILL.md (workflow-setup) Command map: one row appended at the end of the table; Setup.md: one Usage bullet appended after the `agents` bullet, and requirement SET-11 appended after SET-10 at the end of the Functional list. Read `main` first: if SET-11 is taken, use the next free id.
- Order: land whichever pull request is ready first. The second runs `git merge origin/main`, resolves only those appended lines (keep both), re-measures every script above, applies the named fallback if any script is over 20,460, then reruns the toy and package check. Neither goal rewrites the other's lines.
- report.py: the Adoption tuple is one line; both goals append a name to it, so the second to merge keeps both names (a conflict there is one line). `.loop/regression.tsv`: both goals append rows at the end: keep both. Tests.md, START.md, settings.md and the Home and README blocks are generated: after any merge re-run their generators, never merge them by hand.
- Shared with the parallel goal: the task name `<repo>-health-regression` and the "4 hours or shorter" rule live once in `workflows.py` (exported constant and `slots`); that goal's machine setup reuses them, this goal's MIG_TASK reads them.
- survey.py, update.py: never edited; seed.py only as the net-negative line in section 2.

### 4. Other pieces (each owned by the function that already does the job)

- Version nag and refusal [5]: `entry.py lag [--repo DIR] [--new SLUG]`; one line `this repo is at vY, the template is at vX, run the migrate goal` plus the slug hint of section 4b (no version reads v0); `--new` exits 3 with REFUSED when both majors known and differ, `migrate-` slugs exempt. `entry.installed()` honours `LOOP_INSTALLED_VERSION` only when `LOOP_TEST=1` is also set (so it cannot bypass the refusal outside a toy); version text that is not a string or not dotted numbers (`"v1"`, `"1.2"`, null) is read by `version_key` without raising, as 0.0.0. In the template's 0.x numbering the refusal cannot fire until a 1.0 release (done line 5 says major; the plan does not widen it). goal.py new calls it by subprocess. At session start the exact sentence is printed by code, not only asked of the agent: `entry.py check` already prints a never-failing LAG line and its note text becomes the same sentence as `entry.py lag` (one shared string), so every agent that runs the check or reads START.md's first-five-minutes list sees it. The agent block (agents.py) gains one bullet and `references/start.md` names it too.
- Health [6]: `rules.template_version` adds one WARN row for behind or missing version; the `migration` rule runs the engine offline by default and prints its mode (`offline` or `online`) in every row's detail, so the INFO `not checked here` rows are visible in a default `health check` (health stays deterministic and fast for people, CI and setup's own two health runs; it is the same engine with a different input, and the health toy asserts parity: with `LOOP_MIGRATION_ONLINE=1` the codes equal the CLI's full run minus MIG_VERSION plus the template-version row); the 4-hourly tick sets `LOOP_MIGRATION_ONLINE=1` for its health step (+40 bytes in `workflows.py`), so only the Mac tick and the CLI clone the wiki, and the wiki codes show as INFO `not checked here` elsewhere; MIG_TASK off a Mac is an INFO row `SKIP`, never a pass or a warn; a manual `health file` run offline would close the wiki issues (the rule counts as having run) and the next tick would reopen them, so the Health notes say to file only through the tick or with `LOOP_MIGRATION_ONLINE=1`; the wiki rows are grouped, one row per wiki code with the page names listed (at most 20, then a count), so a wiki with many orphans files one issue, while the CLI prints one GAP line per page; every WARN row of the Adoption group is filed as an issue by the existing 4-hourly `health file` step (`workflows.py` GROUPS holds adoption; `file.py` REPORT_ONLY lists neither `template-version` nor `migration`, so both are filed and no edit is needed): the toy proves it with `health.py preview --group adoption` printing `WOULD open` for the template-version row and for a MIG row; new `migration` rule in the Adoption tuple of report.py wraps the engine (state codes WARN; unreadable wiki or registry INFO); its negative control (toy repo, no template_version) is in `defects.CONTROLS`. In the template's own checkout the rule skips MIG_VERSION by construction.
- Operation session [6]: `board_page.queue_migrations(root)` reuses a new `behind(root)` that returns `(repo, held, want)` tuples and that `template_lag` now calls (`template_lag` keeps its string return, so `live_board.py` and the `lag` command need no change; the local-ref bug is fixed in `behind`: `origin/<base>` first), queues `migrate-<repo>` once (de-dup from `.loop/queue.md` and goal state by an exact match of the slug against `^migrate-<repo>(-v[0-9]+-[0-9]+-[0-9]+)?$`, so a repo named `app` never matches the line of `app-api`, with the repo name passed through `re.escape` so `app.v2` matches only itself; it queues only into a followed repo whose checkout is on its base branch with `.loop/queue.md` unmodified, else it prints an Issues line saying why nothing was queued; the check order is: exact-slug de-dup first, then the branch and clean-file guard, then the write; the write is the existing one-line append of `goal.py queue` (`fit.cmd_queue` appends and checks for an existing slug just before; no lock exists and none is invented: two concurrent passes cannot duplicate a slug because the second re-reads and skips, and a checkout that discards the uncommitted line only causes a requeue on the next pass); the queued line stays an uncommitted edit of that repo's `.loop/queue.md` (the loop's own bookkeeping file, which the loop already leaves uncommitted), so the next pass finds the slug and skips before it evaluates the guard; later ones `migrate-<repo>-v<X-Y-Z>`; a finished one for the same version with the repo still behind is an Issues line, not requeued), called once per pass from operate.py. The queued goal carries two lines: its done line `setup.py migration-check --pr` exits 0, run in the goal's worktree before the merge (the PR-closable half of "migration-check passing"), and a Verify-by-hand step that names the full check and the owner's Mac steps (the state half, closed after the merge). Together they cover done line 6's wording; the queued goal's own text states the two halves and the Verify-by-hand section repeats them, and the PR description says so.
- Blocks [11]: `render.py blocks [--repo DIR]` calls `refresh()`, prints each `file block`; `agents.apply` runs it and returns README.md and the Home page to stage; `settings.fill_automation` writes the three built-in entries (never changes one already set), named from the config's own origin: required by done lines 8 and 1, because without it MIG_AUTOMATION could not be closed by a pull request.
- `setup.py migration-check` reaches the engine through `agents.migration_check`, which loads workflow-health's `defects.py` by path with the existing `agents.sibling("workflow-health", "defects.py")` helper and, when workflow-health is not installed beside it, prints `REFUSED: workflow-health is not installed beside workflow-setup. Fix: install it` and exits 4, the code for "the check could not run" (fail soft, never a traceback; a caller that sees 4 knows no verdict was reached, unlike 1).
- Queue opt-out and de-duplication, written once as a state table (the opt-out is the existing one: a repo not in the followed list `~/.workflow-loop/repos` and not the operation session's own repo is never queued):

| What `queue_migrations` finds in that repo | Action |
|---|---|
| repo is current | nothing |
| behind, no slug matching the exact pattern above in `.loop/queue.md` and no goal state for one | queue `migrate-<repo>` (first) or `migrate-<repo>-v<X-Y-Z>` (later) |
| a slug matching the pattern queued, or a goal queued, running or waiting | skip |
| a finished one for this installed version, repo still behind | Issues line `migrate goal for vX finished, repo still behind`; not requeued |
| a finished one for an older version | queue the suffixed slug |

- A standing deliberate difference does not stream issues: `health file` keys each issue by rule and subject, so a repeated WARN is one open issue (the key logic in `file.py` and `issues.py` is read, not changed); closing it by hand reopens it on the next tick while the gap stands, which is why an ignore list is the named later step.
- Orphan and stale wiki gaps reach the owner without a person running the check: the `migration` rule's WARN rows are filed as issues by the 4-hourly health step (above), so a repo cannot sit behind silently.
- Reuse inside the engine (no second reader): `defects.pages`, `defects.wiki` and `defects.table` for wiki pages, wiki folder and regression rows; `defects.row` shapes the health rows; `entry.version_key` for versions.
- The supported interface for another skill is the in-process function `migration_gaps`; the CLI has one output format (text), and Setup.md Usage says so.
- update.py --check [7]: one resolver in agents.py (candidates: tree config base, origin/HEAD full name, main, master; `origin/<b>` before local `<b>`; first that parses wins); sync.py aliases it.
- Public repos on the Mac (owner rule, 2026-11-12, quoted in the goal header: "public or private"): `seed.py` keeps a recorded `regression_runs: mac` when the live visibility says public (it still records `mac` for private and `actions` for public when nothing is recorded); `workflows.py` prints no DRIFT line when the recorded setting is mac. `rules.scheduled` and `lanes_cli.workflow` already treat mac as "no regression.yml". Setup.md Usage wording for `regression_runs` changes to "mac for a private repo or one already recorded mac". The toy part `migration-mac-kept` proves a public toy recorded mac survives a setup re-run and a tick dry run prints no DRIFT. Intended limit, stated so no reader assumes more: a fresh public repo still records `actions` at first setup (unchanged); the owner's rule is carried by MIG_AUTOMATION and MIG_TASK telling the owner to set mac, after which setup and the tick keep it.
- Public-repo safety: the Mac tick runs regression on the base-branch tree after fetching `origin/<base>`, never on a pull-request or fork ref, so a public repo recorded mac does not execute contributed code. Accepted risk, stated in the pull request description: a public repo on the Mac has no `regression.yml`, so Actions no longer reports a regression check on its fork pull requests; MIG_CHECKS reads a land row only.
- Commits: the seed.py and workflows.py public-on-Mac fix is its own commit, so it can be reverted alone. Tick time: each followed repo's one clone has a 30 second cap inside the existing per-repo tick cap (60 minutes) and the total cap (180), so the wiki adds seconds, not minutes. `behind()` reads `origin/<base>` as last fetched; the tick fetches it each run, so staleness is bounded by the tick interval.
- This repo's own tree: run `settings.py reference --write`, the Settings and Automation block render (`docs.py audit`), `entry.py write` and `agents.py wire` so the generated pages and the agent block match the code. Its config has no `automation` and no `regression_runs`, and holds two legacy keys outside the settings table (`judge_command`, `time_budget_minutes`), so its own health run shows WARN rows for MIG_SETTINGS and MIG_AUTOMATION until the owner removes or fills them (verified by reading its config and the table); the new rows are WARN only and the Mac steps are the owner's, not this PR's. The goal's Touches line lists fewer paths than the done lines need (goal.py, board_page.py, operate.py, entry.py, render.py live in other skills); the PR description lists the real set; the goal's done lines and Touches line stay untouched (only its empty Verify by hand section is filled).

### 4b. Error and output contract (agent-ready; every line below is required behavior)

- Every GAP line is `GAP <CODE> <subject>: <what, with the actual values>. Fix: <one runnable command line (commands chained with && count as one), or one human step named as owner-only>`; the engine never prints a config value, only keys, page names and a wiki URL with any `user:password@` part removed.
- Exit codes of `migration-check` (this table covers that command only; `entry.py lag --new` exits 3 as done line 5 says): 0 only with no gap; 1 for any gap (a verdict was reached); 2 for a usage error (argparse: unknown flag, `--repo` not a git repo), printed to stderr with what and `Fix: run setup.py migration-check --help`; 4 when the check could not run (REFUSED, or an unexpected exception: the traceback goes to a private temp file and the line reads `INTERNAL ERROR (MIG_INTERNAL): see <path>; nothing was changed`). A caller must treat only 0 and 1 as a verdict. GAP lines and `MIGRATION: N gap(s)` go to stdout; REFUSED and usage errors go to stderr. `--pr` with `--offline` is allowed and means `--pr` (the wiki codes are state codes, so `--pr` already skips them). `migration-check` takes `--repo DIR` (default the current directory), as `entry.py lag` does.
- The wiki clone is the only network call and is bounded: the engine sets `GIT_TERMINAL_PROMPT=0` and `GIT_ALLOW_PROTOCOL=https:ssh:git:file` (so an `ext::` origin cannot run a command; a toy proves it) and clones with `git clone --quiet --depth 1` in its own process group with a 30-second timeout, killing the whole group on expiry and removing the temp dir only after (`start_new_session=True`, `os.killpg`), catching `subprocess.TimeoutExpired`, `OSError` and a non-zero exit. (It does not call `docs.clone`, which exits the process on failure, has no timeout and is a full clone; it does reuse `docs.wiki_url`.) MIG_WIKI_UNREADABLE says the cause (no origin, offline, auth, timeout), the redacted URL, and `Fix: check the origin and sign-in, then rerun; with no network pass --offline`; one rerun is the retry bound.
- MIG_WIKI_ORPHAN Fix names a persistent path: `git clone <redacted wiki url> && cd <repo>.wiki && git rm -- <quoted page>.md && git commit -m 'remove retired wiki page' && git push` (owner only, run after the merge; irreversible without the wiki's git history, which keeps the page; rerun the check after it, one retry); the GAP line itself says `owner only, after the merge` and `irreversible without wiki history`.
- Untrusted text: wiki page names come from a wiki any collaborator can write. A name is printed only if it matches `[A-Za-z0-9._ -]{1,80}`; any other name is shown as its sanitized form with the Fix `remove it by hand (the name has characters this check will not print)`, never inside a runnable command. Printed commands quote the name with `shlex.quote` after `--` (`git rm -- <quoted>`), a name starting with `-` or `.` or containing `..` is treated as not printable, and the commit message is the fixed text `remove retired wiki page` with no name inside it. The stderr excerpt in MIG_FORMAT and MIG_WIKI_UNREADABLE passes through the same redaction and control-character strip; one redaction function (userinfo, percent-encoded userinfo, and `token`, `access_token` or `key` query values) is applied to every string that can reach stdout, stderr, the CHECKED line or a health row.
- Definitions. Orphan: a `*.md` in the published wiki whose name is not the name of a page under the repo's wiki folder (`defects.pages(root)`, which already reads `docs/wiki/*.md`, so generated pages such as Tests and Home count as source pages) and is not `_`-prefixed (the wiki's own special pages such as `_Sidebar` and `_Footer` start with an underscore; done line 9's "no source page" is read with that exemption); with that marker on its first line its Fix is the `git rm` step, without it the Fix reads `this tool did not write it: keep it, or git rm it if it is retired` (the docs tool never overwrites a page it did not write, DOC-11). Stale: a source page whose published text differs from its `defects.pages(root)` text by the same exact comparison `docs.py publish` makes (`old != text`; publish writes the page unchanged, `docs.py` lines 293-330, so a freshly published wiki reads zero stale). The generated-by marker is the first line `docs.MARKER` that publish requires and checks.
- A repo whose wiki was never created (clone fails with not-found text) is not a gap: the run prints `NOTE no published wiki yet` and lists it on the NOT CHECKED line; auth, network and timeout failures stay MIG_WIKI_UNREADABLE.
- MIG_FORMAT when `docs.py check` fails with no output: the gap carries the exit code and the first 200 characters of stderr.
- `agents.migration_check` without workflow-health: stderr `REFUSED: workflow-health is not installed beside workflow-setup; nothing was changed. Fix: install the workflow-health skill from the same release (it ships in the package), then rerun`, exit 4.
- `goal.py new` when `entry.py` is missing: one stderr line `NOTE: entry.py not found beside workflow-delivery, so the template version was not checked. Fix: reinstall the skills from one release`, and it never blocks. `queue_migrations` when `goal.py queue` fails: the Issues line carries the stderr tail and says `nothing was queued`.
- The version line: `this repo is at vY, the template is at vX, run the migrate goal (slug migrate-<repo>)`: the frozen wording first, the slug hint after it. A refusal reads `REFUSED: this repo is at vY and the template at vX (different major). Fix: start it as a migrate-<repo> goal; nothing was changed`; there is no override variable (the refusal exists to force the migration, and the `migrate-` slug is its sanctioned exit).
- Test-only overrides (`LOOP_INSTALLED_VERSION` with `LOOP_TEST=1`, `LOOP_SCHEDULE_PLATFORM`, `LOOP_SCHEDULE_HOME`) are named as test-only in the toy header and in the Setup.md Usage bullet. `LOOP_MIGRATION_ONLINE=1` is different: it is a supported switch (the tick sets it; a person may too) and Usage lists it with the supported settings. `--help` text defines `--pr` ("only the gaps a pull request can close"), `--offline` and `--repo`. While the wiki clone runs, stderr shows `cloning the wiki (up to 30 s)`.
- Setup.md Usage carries one copy-paste example of a gap run and of a clean run (real output captured from the toy), a one-line table of the codes with their class (PR-closable or state), and says that unfollowing a repo in `~/.workflow-loop/repos` also removes it from the Issues lag lines.
- The measured time to a first useful result (the TTHW the Verify by hand steps record) is the wall seconds of one `migration-check` run on the toy, written next to those steps.
- Deliberate deviation: a repo that does not want a Mac task or a routine says so with the existing explicit off settings (`health_cron`, `regression_cron`, `digest_mail`); no per-code ignore list (deferred, see NOT in scope; trigger to revisit: the first repo that deliberately keeps a legacy key or setting). Until then a standing deliberate difference is one open issue per rule and subject (never a stream), and Setup.md Usage says so.

### 4c. Delivery shape and why detect-queue-review (not detect-and-apply)

One pull request, built as ordered commits, each passing its own toy parts: 0 the shared constants (the task name and 4-hour rule in `workflows.py`) and the two size trims (the `goal.py` `_pods()` rewrite and the compact `fill_automation` form), so the parallel goal can rebase on those lines; D the public-on-Mac fix (first, because A's Fix lines tell the owner to re-run setup and setup must not flip `regression_runs` back); B the base resolver and the blocks and automation writers (so a migrated toy can be clean); A the check (engine, enforce.py half, CLI, health rule and template-version row, lag line and refusal), whose clean fixtures are made by B; C the operation-session queue; then docs and rows. If review pushes back, cut C only: A, B and D stand without it and meet done lines 1 to 5 and 7 to 11. The design keeps detect, queue and let a reviewed goal fix, rather than detect and auto-apply, to protect one property: nothing in an adopted repo changes without a pull request someone reviews (done line 6 says a goal, and the owner's loop is review-gated). The same property is why the check never fixes the Mac or wiki steps itself.

### 5. Tests: dev/toy only, never a new file under skills/

One script `dev/toy/test-migration.sh` (house format: `# reads:` header lines naming every script it runs and the docs it reads, a `Value:` comment, `PASS:` and `FAIL:` lines, `want PART` selector, temp HOME, `LOOP_SCHEDULE_HOME`, `LOOP_SCHEDULE_PLATFORM=darwin`, `LOOP_INSTALLED_VERSION` with `LOOP_TEST=1`, `LOOP_MIGRATION_ONLINE` where a part needs the wiki, a local bare origin and bare wiki beside each toy repo). It needs no network, launchd or gh. Parts and their regression rows (`.loop/regression.tsv`, level `land`, goal SET-11, category criterion, each `bash dev/toy/test-migration.sh <part> 2>&1 | grep -q "PASS: ..."` so a row runs one part, not the whole script; every part finishes in under 60 seconds so the land lane budget holds; the script's `# reads:` header lists every file it runs so a row is not always-run):

| Row id | What the part proves |
|---|---|
| migration-clean | two clean toy repos, a private one recorded mac with its task registered and a public one recorded mac: `MIGRATION OK`, exit 0 |
| migration-gaps-pr | each PR-closable kind named by code with a Fix: no version, a settings-table key missing, `regression_cron` on with `regression_runs` actions or unset, regression off (MIG_CHECKS skipped, no regression.yml needed), behind, stale START.md, unknown setting, blocks stripped, entries missing, `health_cron` off alone, routine without Runbook, a stale PRD page (MIG_FORMAT), a config key outside the settings table (the known set is the table keys plus `_help` and `template_version`; the clean fixture is an empty config filled by `settings.fill_repo`), no pull_request trigger, mac with no land row, a leftover `health.yml` and a leftover `regression.yml` on a mac repo, a missing `.loop/queue.md`, `findings.md` or `regression.tsv` |
| migration-gaps-state | each state kind (plus a real `docs.py publish` into the bare wiki then zero stale (round trip), a hand-made unmarked page and a marked retired page as orphans with their different Fixes, a wiki-only Home counting as source because `Home.md` exists in the repo, an `ext::` origin giving MIG_WIKI_UNREADABLE with nothing run, a hostile page name such as one holding `;`, `$(x)` or a newline, and a page named `--force.md`: printed sanitized with no runnable command, `git rm --` quoting; an origin with no wiki repo prints the NOTE and no gap; an empty wiki; the task-name format string appears once under skills/): task missing, misnamed or 6-hourly; orphan and stale published page; an unreadable wiki (a gap in the CLI, an INFO row in health); off a Mac `SKIP MIG_TASK (not a Mac)` is printed and not counted; a repo with no `.loop/docs.tsv` gets no wiki, blocks, Runbook or format codes; `regression_cron` off with `health_cron` on owes the task only |
| migration-flags | `--pr` lists no state code and exits 0 when only state gaps remain; `--offline` drops exactly the three wiki codes; a missing workflow-health exits 4 and an injected exception exits 4 with a trace path; a wiki URL carrying `user:token@` never appears in stdout, stderr or a health row; the CHECKED and DOCS lines are present; `--pr --offline` equals `--pr`; the last line of a `--pr` pass carries `(--pr: state codes not checked)` and an `--offline` pass `(offline: wiki not checked)`; an unknown flag exits 2 on stderr; `--repo` runs against another directory; a clone that times out or has no origin gives MIG_WIKI_UNREADABLE with the cause and no hang (a fake unreachable origin); exit nonzero for any gap |
| migration-writes-nothing | the tree hash, index, branches, stash and home folder are identical before and after (the toy copies the five-line `state()` helper of dev/toy/test-setup-adopt.sh lines 28 to 32 rather than inventing another), the wiki clone temp is removed |
| migration-health-same | `health.py check --group adoption` prints the same codes (MIG_VERSION through the template-version row); a health WARN never turns the verdict not green; `health.py preview --group adoption` prints `WOULD open` for the template-version row and for a MIG row |
| migration-base-config | `update.py --check` reports the base config from a branch with no config, from a clone with no local main, from a repo whose default branch is neither main nor master, and with `origin/HEAD` unset |
| migration-robustness | a linked worktree (where `.git` is a file) as well as a subdirectory and a detached HEAD; an absent or malformed `.loop/config.json`, a corrupt `regression.tsv`, an unparseable `.loop/docs.tsv`, a non-UTF-8 page name, and two concurrent runs (each clone in its own private temp dir removed in a `finally`, also on SIGINT): named gaps or notes, never a traceback, no leftover temp dir |
| migration-lag-line | `entry.py lag` prints the exact line, once through the real resolver (a fake install folder holding `workflow-package.json`) and once through the test override, and MIG_VERSION is exercised through the real resolver too; the version table of section 1 (absent, `v1`, null, `1.2`, older, equal, newer, differing major); none when current; none in a tree that holds the skills (installed version empty), and MIG_VERSION never fires there |
| migration-major-refused | `goal.py new` warns, and on a differing major refuses with goal.py's own refusal exit 2 (it maps entry.py's exit 3 to that and creates no goal state), printing the recovery line, lets `migrate-` slugs through, and prints the NOTE (never blocks) when entry.py is missing |
| migration-blocks-inserted | a pre-v0.27.17 toy gets both blocks and the README line from `update --apply`, and after it carries `template_version` and is no longer behind (done line 4) |
| migration-queue | the queue function adds one `migrate-<repo>` line once, an Issues line for a finished-but-behind repo, queues nothing for a repo on another branch or with a modified queue file (and says why), with repos `app`, `app.v2` and `app-api` all behind queues all three, one case for each row of the state table (current, behind, queued, finished-same-version, finished-older), two concurrent passes queue one line, and a second pass after a queue write queues nothing more and prints no guard complaint |
| migration-mac-kept | a public toy recorded `regression_runs: mac` keeps it through a setup re-run, and a tick dry run prints no DRIFT and names only `origin/<base>` as the ref it fetches and runs (never a pull-request or fork ref) |

Break commands for `regression.py red --break` (each edits the copy of HEAD with one `sed` or `python3 -c` that targets a named function or constant, never a line number, so a moved line does not rot it, and each ends with `&& ! git diff --quiet` so a break that changed nothing exits non-zero and `red` refuses it): clean, remove the `MIGRATION OK` print in `defects.py`; gaps-pr, make the engine return no MIG_SETTINGS gaps; gaps-state, make the engine return no MIG_TASK gaps; flags, make `--pr` ignore its class filter; robustness, make the engine read the config without its OSError and ValueError guard; writes-nothing, add a file write to the engine; health-same, drop `migration` from the Adoption tuple in `report.py`; base-config, restore the local-ref lookup in `agents.py`; lag-line, change the line text in `entry.py`; major-refused, make `lag --new` exit 0; blocks-inserted, make `agents.apply` skip `render.py blocks`; queue, make `queue_migrations` return nothing; mac-kept, restore the `seen` precedence in `seed.py`.

Seen red then green: the implementer commits code and toy first (regression.py red copies HEAD), then for each row runs `regression.py red <row> --break "<command>"` which breaks a copy of HEAD and records the red date in `seen_red`; The rows, their dates and the re-rendered Tests.md go in a second commit (never an amend); if a row fails there, fix and add another commit. No row is added without a date. Size gate: the package check (`dev/test-package.sh`, which enforces the 20,480 limit) plus `wc -c` on every touched script after each edit, none above 20,460. Package check (`bash dev/test-package.sh`): 96 files under skills/. Run the full toy suite for `test-sync-update.sh`, `test-setup-adopt.sh`, `test-local-schedule.sh`, `test-docs.sh` (they cover edited code).

### 6. Docs

- docs/wiki/Setup.md: Usage bullet for `migration-check [--repo DIR] [--pr] [--offline]` (codes, classes, exits, one gap example, one clean example) and one-line changes to the `update --check` and `update` bullets (base resolver, blocks inserted, template_version stamped); a new requirement SET-11 marked Unreviewed ("a repo is judged fully migrated by one command") appended after SET-10. No Reviewed requirement wording changes.
- docs/wiki/Health.md: Usage and notes only: the `migration` rule and the changed `template-version` rule. Requirement lines (Reviewed) untouched.
- docs/wiki/Tests.md: regenerate with `criteria.py render` (never by hand). Home and README Settings blocks: regenerated by the render step.
- SKILL.md Command map rows: workflow-setup `migration-check` (113 lines now, fine). workflow-docs is at 149 of the 150-line `skill-lines` limit (150 or more is a health FAIL): `lag` goes into the existing `entry.py` row on the same line, adding no line. Generated: references/settings.md, `.loop/START.md`, the agent block in CLAUDE.md and AGENTS.md.

### 6b. NOT in scope

Deferred, with the reason (no TODOS.md exists in this repo, so the list is here; a lightweight Actions check for public repos on the Mac, such as compile and lint only, is a later owner call and is listed here too): a gh branch-protection read (health makes no gh call; the goal header's "required checks are reported" is narrowed to what MIG_CHECKS reads from files, a narrowing the NOT CHECKED line and the pull request description both state; an optional CLI-only read stays a later goal; trigger to revisit: the first time a repo passes MIGRATION OK while its branch protection lacks a required check, or when health gains a permitted gh call; owner: the repo owner); a Windows form of the task check (the parallel goal's done line 7); a per-code ignore list; per-code documentation anchors; a clone cache; telemetry for the first-run time. Rejected: `--json`; a fix-script printer; deleting orphan pages from the command (done line 3); splitting the goal; raising the package or script caps; widening the major-version refusal to 0.x minors (done line 5 says major; in 0.x the refusal can only be exercised through the test override, which the toy does).

### 7. Ordered steps (the commit order of section 4c)

1. Merge origin/main and re-measure every script in the section 2 table; confirm SET-11 is free in Setup.md. Hard gate before commit 0: measure the same scripts on a scratch merge of the parallel goal's branch (a temporary worktree, thrown away). If that branch holds no code yet, the goal that merges second repeats this gate before its own first commit. Take each named fallback now for any script whose measured size exceeds 20,460 or is within 200 bytes of it (the 'After' column above is the pre-merge plan; settings.py 20,093, goal.py 20,086 and render.py 20,112 pass today with about 350 bytes of slack each).
2. Commit 0: the shared constants in workflows.py, the goal.py `_pods()` rewrite, the compact `fill_automation` form with its TABLE row.
3. Commit D: the seed.py and workflows.py public-on-Mac fix; the mac-kept toy part.
4. Commit B: agents.py resolver and the sync.py aliases; `fill_automation` use, `render.py blocks`, `agents.apply`; the base-config and blocks-inserted toy parts.
5. Commit A: enforce.py wiki and docs-check parse first, then the defects.py engine in the function order of the budget, measuring after each function; `agents.migration_check` and the setup.py dispatch with its docstring trim; rules.py, report.py and CONTROLS; entry.py `lag`, the goal.py call, the agent block bullet; the clean, gaps-pr, gaps-state, flags, robustness, writes-nothing, health-same, lag-line and major-refused toy parts.
6. Commit C: board_page.py and operate.py; the queue toy part.
7. Docs, generated files, and the goal file's Verify by hand section (the only part of that file that is not a frozen done line): the design's four steps plus one for the owner's Mac steps, each with an Expect line.
8. Commit, then `regression.py red` per row, add rows with seen_red, re-render Tests.md, final package and size check. Stop and use the named fallback the moment any script measures over 20,460.

### 8. Accepted requirements (binding; one list, ordered by section)

1. Gap codes, classes, exit codes, `--pr`, `--offline`, `--repo`, the CHECKED, NOT CHECKED and DOCS lines and the last-line qualifiers are required as specified in sections 1 and 4b; tests: migration-clean, migration-gaps-pr, migration-gaps-state, migration-flags, migration-writes-nothing.
2. No new file under skills/; every touched script ends at or under 20,460 bytes (hard cap 20,480), measured after each edit and on a scratch merge of the parallel goal before commit 0; setup.py, update.py, sync.py, survey.py and seed.py never end larger than today; the named fallbacks apply at 20,460; workflow-docs SKILL.md stays under 150 lines.
3. Exit codes of migration-check are 0 (no gap), 1 (gaps, a verdict), 2 (usage), 4 (could not run, including an unexpected exception with a trace file path); goal.py maps entry.py's exit 3 to its own refusal exit 2 and creates no goal state; the version table of section 1 governs refusal.
4. Wiki safety: transport allowlist and process-group kill on the bounded clone, `git rm --` with rejected or sanitized names and a fixed commit message, one redaction function over every output string, stale by publish's exact comparison with a round-trip toy, a missing wiki is a note.
5. Health runs the engine offline unless `LOOP_MIGRATION_ONLINE=1` (set by the tick), prints the mode in each row, groups wiki rows, reports MIG_VERSION once through the template-version row, and treats MIG_TASK off a Mac as an INFO skip; `LOOP_INSTALLED_VERSION` and the engine's platform override are honoured only with `LOOP_TEST=1`.
6. A repo recorded `regression_runs: mac` stays mac through setup and prints no DRIFT, and the tick names only `origin/<base>` (test: migration-mac-kept); this fix is its own commit.
7. The queue matches slugs exactly (escaped repo names), writes only into a followed repo on its base branch with an unmodified queue file, keeps `template_lag`'s string return, and the queued goal states its two halves (`--pr` before the merge, the full check after); test: migration-queue.
8. Delivery: one pull request in the commit order of section 4c (0, D, B, A, C), each commit passing its own toy parts; the cut, if any, is C only; detect, queue and review, never detect and auto-apply.
9. Tests only under dev/toy: thirteen parts with named break commands that end with a no-op guard, seen-red dates from `regression.py red --break`, each row run as one part of dev/toy/test-migration.sh; the check writes nothing and no private name, path, token or email appears in any committed text.
10. Docs: Setup.md Usage (command, flags, one gap example, one clean example, the code table with class, supported and test-only settings, the unfollow side effect) plus Unreviewed SET-11; Health.md Usage and notes; Tests.md re-rendered; the goal file's Verify by hand section filled with runnable steps, an Expect line each and the measured seconds of one run; no Reviewed requirement wording changes.

## Review record

### CEO phase: Step 0

Mode: SELECTIVE EXPANSION (auto, recommended: an added capability to an existing toolchain; about 25 files changed, so the over-15 rule recommends reduction, overridden: the done lines require each of those files and the design already minimises new code).

Premise table (claim | receipt | verdict):
- The package is full | dev/package.py:26 MAX_FILES 99, 96 under skills/ plus 3 | verified
- defects.py has room for the engine | wc -c 7,659 | verified
- Re-running setup never inserts the Settings and Automation blocks | sync.py:208 `agents.apply` writes START.md and agent files only | verified
- update --check misreads the base config | sync.py:148-165 reads the local ref only | verified
- the tick honours regression_runs mac for any repo | workflows.py:278 | verified, and exposes the DRIFT and seed.py conflicts (plan 0 f)
- a public repo can reach MIGRATION OK under the owner rule | seed.py:156-158, workflows.py:279 | finding, fixed in plan section 4
- docs.py check renders Runbook lines with a recognisable kind | deployments.py:86-108 builds them via `bad(..., "Runbook", 16, ...)`; the rendered text was not run | unverified=1 (the toy proves it; fallback: match on the DOC-16 id)
- Only FAIL and UNREAD turn health not green | health.py:308 | verified
- settings.py has no set command | settings.py:266-285 | verified (design corrected)

REALITY: premise-table finding 9 premises, unverified=1 skills/workflow-docs/scripts/deployments.py:86
REALITY: already-done pass no commit on origin/main names MIG_ or migration-check; only entry.lagging exists (git grep on local refs, no network fetch) skills/workflow-docs/scripts/entry.py:218
REALITY: surface-check finding `entry.py lag`, `setup.py migration-check`, `render.py blocks` do not exist yet (new by plan); `settings.py set` does not exist (corrected) skills/workflow-setup/scripts/settings.py:266
REALITY: binding-decisions pass no branch decision log entries; the goal header decisions (public repos on the Mac, delete orphan pages after merge) are carried skills/workflow-setup/scripts/seed.py:156
REALITY: numbers pass every byte figure re-measured with wc -c [measured: wc -c on this branch] skills/workflow-health/scripts/defects.py:1
REALITY: deferred-asks pass no linked issue; the goal header's asks all map to done lines 1 to 11 .loop/goals/migration-check.md:1
REALITY: pr-count pass one pull request (no ship policy file); the parallel goal is a separate pull request .loop/goals/migration-check.md:1

Dream state: CURRENT adopted repos drift with no verdict and no nudge; THIS PLAN one read-only command, one health rule and one queued migrate goal give a testable done line and a session-start nudge; 12-MONTH IDEAL a repo cannot lag silently: the operation session migrates every repo on each release and the owner only runs the Mac steps.

Scope decisions (SELECTIVE EXPANSION cherry-picks, each auto-decided; effort S/M/L/XL):
1. Drop the design's `--json` flag (S): ACCEPTED, no script consumes JSON; health and the queue function call the engine as a function.
2. Fix the public-on-Mac conflict in seed.py and workflows.py (S): ACCEPTED, required for MIGRATION OK to be reachable (principle P1; in blast radius).
3. Print the repo's own fix plan as a script (M): SKIPPED, duplicates `update --apply` and the migrate goal (P4).
4. A branch-protection (gh) read for "required checks are reported" (M): DEFERRED, health makes no gh call; recorded under NOT in scope.
5. Delete orphan wiki pages from the command (S): SKIPPED, done line 3 and the owner's wording (the owner removes them).
6. A Windows form of MIG_TASK (M): DEFERRED to the parallel goal, whose done line 7 covers Windows; MIG_TASK prints SKIP off a Mac.
7. Run `regression.py red` evidence inside the toy (S): SKIPPED, the red proof is a commit-time step, not a toy.

Required by the done lines, so not discretionary (recorded for scope review): the major-version refusal (done line 5, goal.py), the auto-queued migrate goal (6, board_page.py and operate.py), automation entries (8, settings.py), the template-version WARN row (6, rules.py), `entry.py lag` (5), `render.py blocks` (11), the base-config resolver (7). NOT in scope (deferred, no TODOS.md exists in this repo, so the record is here): a gh branch-protection read for required checks; a Windows form of the task check (the parallel goal's done line 7).

Further accepted items (each tied to a done line, auto-decided P1): the `board_page.template_lag` local-ref fix (done line 6: the operation session must detect behind repos correctly); MIG_FILES leftover `health.yml` and `regression.yml` gaps (done line 1: every file setup writes is present and current, and none it no longer writes); versioned `migrate-<repo>-v<X-Y-Z>` queue names and the finished-but-behind Issues line (done line 6, repeat releases); the `LOOP_INSTALLED_VERSION` toy override (done lines 4 and 5 are only testable with it); the one-place 4-hour constant (done line 8); edits outside the goal's Touches line in workflow-docs, workflow-delivery and workflow-monitoring (the done lines name those behaviors; the PR description lists the real file set; the goal file's Touches line is not an owner decision).

Spec review: 3 launches (scores 6, 6, 7); the third's issues were all addressed in the plan text (issues verified: 19 of 19 applied; not re-reviewed, cap reached); two feasibility notes (tight byte margins, merge order) are accepted with the named per-edit measurement and fallbacks.

Merge-order dependency on the parallel goal operator-setup (not an owner decision): shared task name and 4-hour rule (reused from workflows.py), the report.py Adoption tuple line, README.md, Tests.md, regression.tsv and Setup.md; resolved by plan section 3.

Reviewer concerns carried: spec review launch 1 (score 6, five dimensions failed on coverage, one duplicate signal, undefined brackets, missing decision rows, no size gate): all applied below; launch 2 pending.

- Every gap code, class, exit code, `--pr` and `--offline` behaviour in plan sections 1 and 4 is required; tests: the toy parts migration-clean, migration-gaps-pr, migration-gaps-state, migration-flags, migration-writes-nothing.
- No new file under skills/; every script at or under 20,480 bytes, measured after each edit; seed.py, setup.py, sync.py, update.py, survey.py never grow; the named fallbacks apply at 20,460.
- A repo recorded `regression_runs: mac` stays mac through setup and prints no DRIFT; test: migration-mac-kept.
- New tests only under dev/toy; migration-check writes nothing (tree and .git listing identical before and after); no private name, path, token or email in any committed text.
- Docs: Setup.md Usage bullet plus Unreviewed SET-11, Health.md Usage and notes only, Tests.md re-rendered; no Reviewed requirement wording changes.


### CEO phase: dual voices and review sections

Voices: native CEO subagent completed (8 findings, INPUT hash matched its snapshot); Codex outside voice unavailable (the outside call needs network and was skipped; this is missing coverage, never a clean result). Tags: [subagent-only].

CEO DUAL VOICES - CONSENSUS TABLE:
  Dimension                              Claude  Codex  Consensus
  1. Premises valid?                      yes     N/A    N/A (voice coverage missing)
  2. Right problem to solve?              yes     N/A    N/A
  3. Scope calibration correct?           risky   N/A    N/A (native says large; done lines force it)
  4. Alternatives sufficiently explored?  partly  N/A    N/A
  5. Competitive/market risks covered?    yes     N/A    N/A
  6. 6-month trajectory sound?            risky   N/A    N/A (byte packing, rotting break commands)

Native findings and dispositions: (1) cap is structural, raise it or split first: TASTE, kept as is (the owner fixed the caps; this plan consumes no slot and ends no script larger where the owner said fold or trim; the next goal must retire a file, recorded below); (2) sequence the goals: TASTE, kept (append-only edit points, merge and re-measure; the shared task name and 4-hour constant already live once); (3) qualify what MIGRATION OK verifies: ACCEPTED (NOT CHECKED line); (4) public-repo change is scope creep: TASTE, kept (without it MIGRATION OK is unreachable for a public repo under the owner's 2026-11-12 rule; a Mac-hosted fresh repo cannot be detected, stated as the known limit); (5) break commands rot: ACCEPTED (anchor to function names), toy parts kept at twelve because each proves a distinct behavior and cutting merges unlike failures; (6) wiki orphans depend on a human: ACCEPTED in part (WARN rows are filed as issues by the existing health step, so the owner is nudged; no apply mode because done line 3 forbids writes); (7) queue opt-out: ACCEPTED (state table, opt-out is unfollowing the repo); (8) no --json: ACCEPTED (the function is the supported interface, said in Setup.md). Reframing (split into a core goal and a machine-state goal): REJECTED, the done lines are frozen and name both halves.

Section 1 Architecture. Findings: the engine lives in the module health already loads and reaches setup by a path-load, so setup and health cannot disagree; coupling added: setup to health (fail soft, REFUSED line), operation session to setup (subprocess, same pattern as goal.py to monitoring). Single points of failure: the registry read and the wiki clone (each a named gap, not a crash). Rollback: revert the pull request; the check writes nothing and the settings and block writers only add keys and blocks, so a revert leaves a repo that setup never overwrote. Value test: the check is consumed by health (rule), the queued goal's done line, and the owner's migration; it retires with the migration of the last repo.

  setup.py migration-check --> agents.migration_check --> defects.main --> enforce (wiki, docs parse)
  health.py (Adoption) -------------------------------> defects.migration rule  (skips MIG_VERSION)
  health.py (template-version row) <- rules.py (+MIG_VERSION text)
  operate.py -> board_page.queue_migrations -> goal.py queue (per behind repo) -> migrate goal -> update --apply
                                                                                      \-> agents.apply -> render.py blocks
  goal.py new --> entry.py lag --new (warn, exit 3 on a differing major)
  update.py --check --> sync.base_of/base_config (aliases of agents resolver)

Section 2 Error and Rescue. Registry below. Section 3 Security: no new input except `--repo`-less cwd and a `migrate-` slug; the wiki clone goes to a private temp dir removed in a finally block; no secret read; output never prints a config value, only keys and page names (private-name scan stays clean); LLM calls none. Section 4 Data flow: INPUT config, registry, wiki, git, shadow paths: nil config (MIG_VERSION v0 plus MIG_SETTINGS), empty registry (MIG_TASK), unreadable wiki (UNREADABLE), non-UTF-8 routines file (existing `bad` row), a repo with no docs.tsv (no wiki codes); concurrency: the check holds no lock and writes nothing, the tick's detached tree is read the same way. Section 5 Code quality: one function per gap code returning tuples, no catch-all except around the wiki clone and registry read, which name OSError and ValueError; branching under 5 per function by the per-function budget. Section 6 Tests: diagram below, twelve parts. Section 7 Performance: one shallow wiki clone per run (network only when online), no clone for `--offline` or `--pr`; health runs the engine with online=False inside the 4-hourly tick budget unless the repo has an origin (then one clone, capped 30 seconds). Section 8 Observability: each gap names code, subject and fix; health files issues; the queued goal journal says why. Section 9 Rollout: skills release then `update --apply` per repo; no migration of data; old and new code never run together on a repo because the check is read-only. Section 10 Trajectory: debt, byte-packed scripts and a package at its file cap; reversibility 4 of 5; the next goal must retire a file; the 1-year question: codes are stable and documented in Setup.md. Section 11 Design: SKIPPED (no UI scope).

Error and Rescue Registry:
  CODEPATH                    | FAILURE                    | RESCUED | ACTION                              | USER SEES
  migration_gaps wiki clone   | no origin, offline, auth   | Y       | MIG_WIKI_UNREADABLE gap / INFO row  | named gap with fix
  migration_gaps registry     | missing or unreadable file | Y       | MIG_TASK gap                        | named gap
  migration_gaps config read  | invalid JSON               | Y       | MIG_SETTINGS gap "unreadable"       | named gap
  docs.py check subprocess    | exit nonzero, no output    | Y       | MIG_FORMAT gap with the raw line    | named gap
  agents.migration_check      | workflow-health missing    | Y       | REFUSED line, exit 1                | one line with fix
  entry.py lag                | no config                  | Y       | reads v0, prints the line, exit 0   | the nag line
  goal.py new lag call        | entry.py missing           | Y       | skip silently, never block          | nothing
  agents.base_of resolver     | no candidate parses        | Y       | {} and the existing "no config" line| the existing line
  queue_migrations            | goal.py queue fails        | Y       | Issues line, no raise               | Issues line
  fill_automation             | unreadable config          | Y       | existing REFUSED path of fill_repo  | REFUSED
  CRITICAL GAPS: 0

Failure Modes Registry:
  CODEPATH               | FAILURE MODE                   | RESCUED? | TEST?               | USER SEES?      | LOGGED?
  wiki clone             | temp dir left behind           | Y        | writes-nothing      | nothing         | n/a
  engine                 | writes a file by mistake       | Y        | writes-nothing      | test fails      | n/a
  seed.py                | recorded mac flipped           | Y        | mac-kept            | no DRIFT        | n/a
  tick DRIFT             | line for a recorded mac        | Y        | mac-kept            | no DRIFT        | digest
  queue                  | requeues every pass            | Y        | queue               | one line        | queue.md
  lag --new              | refuses a migrate goal         | Y        | major-refused       | goal starts     | journal
  size cap               | script over 20,480 bytes       | Y        | package check, wc   | build fails     | n/a
  critical gaps: 0 (every row rescued, tested and visible)

Test diagram (codepath: type of test): gaps (twelve parts in dev/toy/test-migration.sh, integration on toy repos with bare origin and wiki); lag line and refusal (integration, goal.py by subprocess); resolver (integration, a clone with no local main); blocks (integration, update --apply on a pre-0.27.17 toy); queue (integration, operate pass on a toy followed repo); size and package (the existing package check). Hostile QA case: a wiki page named like a generated page, a config with an automation entry named like a built-in, a repo with an unreadable origin. Chaos case: kill the check mid-clone, then assert no temp dir and no tree change. No LLM prompt files are touched, so no eval suites apply.

NOT in scope: a gh branch-protection read for required checks (deferred, no TODOS.md exists here); a Windows form of the task check (deferred to the parallel goal's done line 7); an apply mode that deletes orphan pages or writes the Mac task (rejected, done line 3); a `--json` flag (rejected, YAGNI); splitting the goal in two (rejected, done lines frozen); raising the package caps (not this goal's call).

What already exists: `entry.py check` and `lagging` (reused for files and version), `docs.py check` (reused for format, stale pages, Runbook), `render.stale_blocks` and `refresh` (reused for blocks), `workflows.key_of/slots/load` (reused for the task), `docs.clone/wiki_url` (reused for the wiki), `board_page.template_lag` (refactored, not copied), `controls.CONTROLS` auto-import (no controls.py edit), `file.py` filing of WARN rows (no edit), `agents.sibling` (reused to path-load the engine).

TODOS.md updates: none proposed (the repo has no TODOS.md; deferred items are under NOT in scope).

Decision audit trail (auto-decided, none left for the gate except the taste rows marked T):
| # | Phase | Decision | Class | Principle | Rationale | Rejected |
|---|---|---|---|---|---|---|
| 1 | CEO | SELECTIVE EXPANSION mode | mechanical | P3 | an added capability | hold scope, reduction |
| 2 | CEO | drop --json | mechanical | P5 | no consumer | keep flag |
| 3 | CEO | public-on-Mac fix in this goal | T | P1 | MIGRATION OK unreachable otherwise | separate goal |
| 4 | CEO | wiki half in enforce.py from the start | mechanical | P3 | keeps defects.py small | fallback only |
| 5 | CEO | NOT CHECKED line | mechanical | P1 | green must not overclaim | silent OK |
| 6 | CEO | keep one goal, no split, no cap raise | T | P6 | frozen done lines, owner caps | split, raise cap |
| 7 | CEO | queued goal done line is --pr | mechanical | P5 | state gaps close only after merge | bare command |
| 8 | CEO | queue opt-out is unfollowing | mechanical | P4 | existing followed list | new setting |

Completion Summary (CEO): mode SELECTIVE EXPANSION; system audit: package full, two scripts' behaviors collide with the owner's public-on-Mac rule, a parallel goal overlaps; Section 1: 3 issues; Section 2: 10 error paths, 0 gaps; Section 3: 0 issues, 0 high; Section 4: 6 edge cases, 0 unhandled; Section 5: 0; Section 6: diagram produced, 0 gaps; Section 7: 1 note; Section 8: 0 gaps; Section 9: 0 risks; Section 10: reversibility 4/5, debt items 3; Section 11: SKIPPED. Outside voice: codex unavailable, native completed. Unresolved decisions: 0 owner-only. Reality rows: 7 of 7, unverified 1.

### DX phase (Phase 2.5): developer-facing scope detected (command, package, SKILL.md terms; the product is a CLI and skill system whose users are the owner and the agents that run it)

Product type: CLI tool plus Claude Code skill. Mode: DX POLISH (an enhancement to an existing product; auto, recommended). Phase 2 (Design) skipped: no UI scope.

Developer persona card:
  Who:       the operation session, an AI coding agent running unattended, and the owner reading its report
  Context:   an agent starts work in an adopted repo, or the owner asks whether a repo is fully migrated
  Tolerance: one command and one screen; an agent retries blindly and reads errors literally
  Expects:   a verdict it can act on without reading the source, and a fix line it can run or hand to the owner

Developer empathy narrative: I start a session in a repo adopted months ago. START.md says nothing is wrong, and setup says NO CHANGE, so I believe the repo is current. I run the new check and see a short list: the version is behind, two blocks are missing on Home and the README, and the Mac task is not registered, each with a Fix line, then a NOT CHECKED line and the count. I run the migrate goal, merge, and run the check again: only the wiki and Mac gaps remain, and each says it is the owner's step. After those, MIGRATION OK. What I fear is a green line that means less than it says; the NOT CHECKED line answers that. (Observed from the plan and the existing commands; the exact output text is predicted until the toy runs.)

Competitive DX benchmark (reference benchmarks, no web research: the call needs network and was skipped; none of these times is measured):
| Tool | Start to result | Time and evidence | DX choice |
| doctor-style checks in package managers | one command to a list of named problems | about 1 minute, reported | each problem names its fix |
| linters with a fix mode | one command to a diff of problems | about 1 minute, reported | exit code is the CI gate |
| this plan | one command to coded gaps with fixes | about 1 minute, estimated (toy-measured at implementation) | codes are stable; read-only; PR-closable versus state split |
TTHW: current none (no command exists); target Champion, under 2 minutes, for `setup.py migration-check` in an adopted repo; first useful result is the gap list. Not measured: re-measure with the Verify-by-hand steps.

Magical moment: the first run prints the exact list of what is behind with a runnable fix for each, and the second run after the migrate goal prints MIGRATION OK with a NOT CHECKED line saying what that did not prove. Vehicle (lowest effort, existing capabilities): the command's own output; no new service.

Developer journey map:
STAGE           | DEVELOPER DOES                                   | FRICTION POINTS                              | STATUS
1. Discover     | sees the line at session start or in the queue    | line had no command; now names the slug      | fixed
2. Install      | nothing: ships in the skills package              | health skill missing; REFUSED names the fix  | fixed
3. Hello World  | runs `setup.py migration-check`                   | no example output in docs                    | fixed (Setup.md example)
4. Real Usage   | runs --pr in the migrate worktree, full on the Mac| --pr versus full unclear                     | fixed (NOT CHECKED line)
5. Debug        | reads GAP lines, follows Fix                      | wiki fix pointed at a temp clone; unreadable wiki lumped | fixed (persistent path, cause)
6. Upgrade      | next release lags every repo again                | one queued migrate goal per behind repo      | ok

First-time developer confusion log (grounded in the plan and code):
  T+0:00 runs the command from a worktree of the template itself: installed version empty, MIG_VERSION never fires (documented, tested).
  T+0:30 sees MIG_TASK on a Linux CI box: SKIP line, not counted.
  T+1:00 sees MIG_WIKI_UNREADABLE offline: now says rerun with --offline.
  T+2:00 hits REFUSED for a differing major in goal.py new: now prints the migrate- slug recovery.
  T+3:00 succeeded; addressed items marked fixed above.

DX DUAL VOICES - CONSENSUS TABLE:
  Dimension                           Claude  Codex  Consensus
  1. Getting started < 5 min?          yes     N/A    N/A (voice coverage missing)
  2. API/CLI naming guessable?         mostly  N/A    N/A
  3. Error messages actionable?        gaps    N/A    N/A
  4. Docs findable & complete?         gaps    N/A    N/A
  5. Upgrade path safe?                yes     N/A    N/A
  6. Dev environment friction-free?    mostly  N/A    N/A
Voices: native DX subagent completed (INPUT hash matched, about 25 findings); Codex unavailable (network skipped; missing coverage). Tag [subagent-only].

Native findings and dispositions (auto-decided, DX POLISH): ACCEPTED, applied in plan section 4b and the tests: bounded no-prompt wiki clone with cause text; runnable Fix lines and the owner-only wiki step with a persistent path; GAP lines never print values and the URL is redacted; recovery text on REFUSED, the lag line names the slug; the silent skip in goal.py new becomes a NOTE; queue failure line carries the cause and says nothing was queued; `--repo`, `--pr --offline` and usage errors specified; docs get one gap example, one clean example, a code table and the unfollow side effect; test-only overrides named. TASTE, kept: no per-code anchors in the docs (the Fix text is the contract; a code table in the Usage bullet replaces anchors, because a new reference file would break the file cap); no override variable for the major refusal (it exists to force the migration; the migrate- slug is the exit); no per-code ignore list (explicit off settings already cover deliberate deviation; deferred).

ERROR PATH MATRIX (agent-ready-v1)
Path                         | Class      | what | fix  | recovery | code | context | trace | redaction | channel | Cap
migration-check usage        | usage      | pass | pass | N/A      | pass | N/A     | N/A   | pass      | pass    | none
MIG_WIKI_UNREADABLE          | validation | pass | pass | pass     | pass | pass    | N/A   | pass (URL)| pass    | none
migrate- refusal (lag --new) | validation | pass | pass | pass     | pass | pass    | N/A   | pass      | pass    | none
workflow-health missing      | unexpected | pass | pass | pass     | pass | pass    | N/A   | pass      | pass    | none
queue goal.py failure        | unexpected | pass | pass | pass     | pass | pass    | pass  | pass      | pass    | none
(initial plan had CAP6 findings on recovery, fix and context for four of these paths; no CAP4: no secret leak, no failure signalled as success, no terminal block once the clone is bounded and prompts are off)

Pass scores (before, after, what 10 means here):
1 Getting started 6 to 9: one command, example output in Usage, slug in the nag; 10 would be a measured under-2-minute run. 2 CLI design 7 to 8: one verb plus `lag`, flags consistent (`--repo`, `--pr`, `--offline`); the engine lives in another skill (named, fail soft). 3 Error messages 6 to 9: contract table above; trace is N/A except unexpected failures. 4 Documentation 6 to 8: example, code table, SET-11, Verify steps as commands; no per-code anchors. 5 Upgrade path 8 to 9: read-only check, additive writers, one migrate goal per release, revert is a PR revert. 6 Dev environment 7 to 8: toys need no network, launchd or gh; test-only overrides named; Windows deferred to the parallel goal. 7 Community 5 to 5: not applicable to an internal tool; no change. 8 DX measurement 5 to 7: Verify by hand re-measures TTHW; the health rule files a recurring signal; no telemetry (an independent policy, not added).
Initial DX score 6.3 (pre-fix pass scores 6, 7, 6, 6, 8, 7, 5, 5); overall after 8.0.

DX SCORECARD
| Getting Started 9 | API/CLI/SDK 8 | Error Messages 9 | Documentation 8 | Upgrade Path 9 | Dev Environment 8 | Community 5 | DX Measurement 7 | TTHW: none to under 2 min (target Champion) | Mode DX POLISH | Overall 8.0 |
Principle coverage: Zero Friction covered; Learn by Doing covered (examples); Fight Uncertainty covered (NOT CHECKED, recovery text); Opinionated plus Escape Hatches gap by design (no major override, explicit off settings only); Code in Context covered; Magical Moment covered (output vehicle); Agents Are Users covered (non-interactive, exit codes, no prompts).

DX IMPLEMENTATION CHECKLIST
[ ] migration-check runs in under 2 minutes on a toy and the number is written in the Verify steps
[ ] one command, no install beyond the package
[ ] first run prints gap lines or MIGRATION OK plus NOT CHECKED
[ ] every Fix is a runnable command or a named owner-only step
[ ] errors follow the contract table (stderr, exit 1 or 2, what and fix)
[ ] `--repo`, `--pr`, `--offline` documented; combination defined
[ ] Setup.md shows a real gap run and a clean run
[ ] upgrade path: the migrate goal and `update --apply`, no breaking change
[ ] works in CI without a prompt (GIT_TERMINAL_PROMPT=0, 30 second clone cap)

NOT in scope (DX): per-code doc anchors; a per-code ignore list; an override for the major-version refusal; telemetry for TTHW; Windows form of the task check.
What already exists: argparse usage errors, the `REFUSED:` style and `Fix:` suffix used across the skills, `GIT_TERMINAL_PROMPT=0` in docs.py, `entry.py` LAG note, the toy header format.
TODOS.md updates: none (no TODOS.md; deferred items above).
Decision audit trail (DX rows):
| 9 | DX | mode DX POLISH | mechanical | P3 | enhancement | expansion, triage |
| 10 | DX | bounded no-prompt shallow wiki clone, own helper | mechanical | P1 | docs.clone exits the process and has no timeout | reuse docs.clone |
| 11 | DX | no major-refusal override variable | T | P5 | the refusal forces migration | env override |
| 12 | DX | no per-code anchors or ignore list | T | P3 | file cap, explicit off settings | anchors, ignore list |
| 13 | DX | `--repo` on migration-check, `--pr --offline` allowed | mechanical | P5 | consistency with entry.py lag | reject the combination |

- The error and output contract in plan section 4b (GAP line shape, stderr and stdout split, exit codes 0, 1, 2, bounded no-prompt wiki clone with a 30 second cap, redacted URL, recovery text on every REFUSED and NOTE) is required; tests: migration-flags and migration-major-refused.
- The version line names the slug after the frozen wording, the refusal prints its recovery, goal.py new prints a NOTE when entry.py is missing and never blocks.
- Setup.md Usage carries one real gap example, one clean example, a code table with class, the test-only override names and the unfollow side effect; the Verify by hand steps are runnable commands with an Expect line and the measured TTHW.

### Eng phase (Phase 3)

Scope Challenge (result: scope accepted as-is; mode FULL_REVIEW). Complexity gate: about 25 changed files (21 under skills/ plus docs, toy and rows) and no new class or service, so the gate trips on files; auto-decided (principle P2, never reduce): feature cuts none (each piece is required by a done line); structure question plan-eng-review-structure: Original arrangement kept over a Smaller arrangement, because the package cap and the per-script caps already force the engine into two existing files and no arrangement with fewer files preserves the frozen done lines. Pending remedies not decided here: none. Design-twice: the engine adds no new module or boundary (a function in an existing file), so no second shape is required; red flags screened: hand-synced list (the report.py Adoption tuple and the `FUNCTIONS` and `CONTROLS` maps already exist; the new rule is added once to each), two ways to do one task (template_lag and behind: one derives from the other), split ownership (MIG_VERSION is reported once, by the template-version row), pass-through method none, information leakage (the task-name format lives once in workflows.py, asserted by a toy).

REALITY: premise-table finding 9 premises, unverified=1 skills/workflow-docs/scripts/deployments.py:86
REALITY: already-done pass no commit on origin/main adds MIG_ codes or migration-check (git grep, local refs) skills/workflow-docs/scripts/entry.py:218
REALITY: surface-check finding `regression.py red` needs --break; `settings.py set` does not exist; `entry.py` has no lag choice yet skills/workflow-regression/scripts/regression.py:331
REALITY: binding-decisions pass the goal header decisions (public or private on the Mac, delete orphans after merge) are carried; no decision log entries for this branch skills/workflow-health/scripts/workflows.py:278
REALITY: numbers pass every byte figure re-measured with wc -c [measured: wc -c on this branch] skills/workflow-health/scripts/defects.py:1
REALITY: deferred-asks pass no linked issue; the goal header asks all map to done lines 1 to 11 .loop/goals/migration-check.md:1
REALITY: pr-count pass one pull request; the parallel goal is separate and overlaps in eight shared files (plan section 3) .loop/goals/migration-check.md:4

ENG DUAL VOICES - CONSENSUS TABLE:
  Dimension                           Claude  Codex  Consensus
  1. Architecture sound?               yes     N/A    N/A (voice coverage missing)
  2. Test coverage sufficient?         gaps    N/A    N/A
  3. Perf risks + budget/bench named?  yes     N/A    N/A
  4. Security threats covered?         gaps    N/A    N/A
  5. Error paths handled?              gaps    N/A    N/A
  6. Deployment risk manageable?       mostly  N/A    N/A
Voices: native eng subagent completed (16 findings; INPUT hash matched its snapshot); Codex unavailable (network skipped; missing coverage). Tag [subagent-only].

Native findings and dispositions (confidence in brackets): 1 [CRITICAL 9/10] health became networked: ACCEPTED, offline by default, the tick sets LOOP_MIGRATION_ONLINE=1; 2 [CRITICAL 9/10] shell injection through wiki page names in printed Fix text: ACCEPTED, allowlist, shlex.quote, hostile-name toy; 3 [CRITICAL 7/10] orphan Fix deletes pages the tool did not write: ACCEPTED in part (orphan and stale defined; unmarked pages get a keep-or-remove Fix; the check never deletes); 4 [INFO 8/10] no-wiki-yet reported as unreadable: ACCEPTED, NOTE and a toy; 5 [INFO 9/10] queue prefix collision: ACCEPTED, exact slug pattern and a two-repo toy; 6 [INFO 6/10] MIG_CHECKS vacuous: ACCEPTED in part (the NOT CHECKED line stays; the code name stays stable; the public-repo PR-gate loss is an accepted risk written in the PR description); 7 [INFO 8/10] override of the refusal: ACCEPTED, `LOOP_TEST=1` pairs the override and a real-resolver toy is added; 8 [INFO 7/10] 0.x versions: TASTE, kept (done line 5 says major; version parsing hardened); 9 [INFO 7/10] settings false positives: ACCEPTED, known-key set defined, clean fixture named, and the template's own two legacy keys are expected WARN rows; 10 [INFO 6/10] public repo on the Mac runs contributed code: ACCEPTED as a stated fact (the tick runs the base-branch tree only); 11 [INFO 8/10] error paths missing in the toy matrix: ACCEPTED, migration-robustness row; 12 [INFO 7/10] byte margins: ACCEPTED, scratch merge measure and concrete fallbacks per script, docs.py as the second home for blocks; 13 [INFO 6/10] shared constant twice: ACCEPTED, a toy asserts the task-name format appears once; 14 [INFO 5/10] exit code ambiguity: TASTE, kept (REFUSED prints on stderr and no caller depends on the difference); 15 [INFO 8/10] template_lag return change: ACCEPTED, template_lag unchanged, new behind() for tuples; 16 [INFO 6/10] hidden complexity: ACCEPTED in part (the public-on-Mac fix is its own commit; regression.py red already refuses when the row still passes after the break, which catches a break that changed nothing).
Own findings (read from code): skill-lines FAIL risk [INFO 10/10 skills/workflow-health/scripts/rules.py:243] workflow-docs/SKILL.md is at 149 of 150 lines: the lag row folds into an existing row; docs.clone exits the process, is unbounded and not shallow [INFO 9/10 skills/workflow-docs/scripts/docs.py:98]: own bounded clone; rows must pass a part name so one row runs one part [INFO 8/10 dev/toy/test-local-schedule.sh:10]: applied; a queue write into a followed repo's checkout needs a base-branch and clean-file guard [INFO 7/10 skills/workflow-monitoring/scripts/board_page.py:222]: applied.

Section 1 Architecture (4 issues found, all resolved above). Diagram:

  setup.py migration-check --repo --pr --offline
        |-> agents.migration_check --path-load--> workflow-health/defects.py:main
        |        (missing health: stderr REFUSED, exit 1)        |-> engine: version files settings blocks automation task checks
        |                                                        |-> enforce.py (lazy): wiki clone (30s, no prompt), docs.py check parse
        |                                                        '-> output: GAP lines, NOT CHECKED, last line
  health.py check (Adoption) -> defects.migration rule (offline; tick sets LOOP_MIGRATION_ONLINE=1)
        '-> rules.template_version row (MIG_VERSION text) -> health file -> issues (REPORT_ONLY lists neither)
  operate.py pass -> board_page.queue_migrations -> behind() -> goal.py queue (cwd = followed repo, base branch, clean queue.md)
  goal.py new -> entry.py lag --new (NOTE if entry.py missing, never blocks, exit 3 on differing major, migrate- exempt)
  update.py --check / sync.base_config -> agents resolver (origin/<b> first)
  update --apply -> agents.apply -> render.py blocks (or docs.py blocks) ; settings.fill_automation (never overwrites)

Section 2 Code quality (3 issues found): one function per gap code returning tuples; no `except Exception`, only named OSError, ValueError, TimeoutExpired and SystemExit around docs calls; the engine does not import docs.py wholesale (wiki_url only); branching under 5 per function by budget; the template_lag and behind pair removes a duplicate. Diagrams touched: none stale (the graph.py status diagram is not edited).

Section 3 Test review: coverage diagram (plan paths; all are proposals, none runnable yet, so every row is a requirement):
CODE PATHS                                              USER FLOWS
[+] defects.py engine                                   [+] adopted repo behind
  |-- version, files, settings, blocks                    |-- [REQ ***] clean / gaps-pr / gaps-state rows
  |-- automation + task truth table (6 cases)             |-- [REQ ***] migrate goal, then --pr passes pre-merge
  |-- checks (mac, actions, off)                          '-- [REQ **]  full check after merge on the Mac
  '-- main: --pr, --offline, --repo, usage, NOT CHECKED [+] session start
[+] enforce.py wiki + docs parse                          |-- [REQ ***] lag line (real resolver and override)
  |-- clone ok / not-found / timeout / hostile name       '-- [REQ ***] goal.py new refusal, migrate- exempt, NOTE
  '-- orphan, stale, runbook, format                    [+] operation pass
[+] agents resolver, apply, migration_check               |-- [REQ ***] queue once, exact slug, branch and clean guard
[+] settings.fill_automation, TABLE row                   '-- [REQ ***] health issue filing (preview WOULD open)
[+] seed.py / workflows.py public-mac                   [+] setup re-run
[+] entry.py lag / goal.py call / rules.py / report.py    '-- [REQ ***] mac kept, no DRIFT
COVERAGE: 0 of 24 paths have a test today (new code); plan requires 13 toy parts for all 24 | all unit-at-boundary (integration on toy repos); no E2E beyond toys; no LLM or eval scope (no prompt files touched)
Test plan artifact written to the local review state folder (outside the repo, not committed). Test gaps identified: 24 requirements, 0 pending decisions. Value cards in the artifact. Tests made obsolete: none.
Hostile QA case: a wiki page named `x; rm -rf ~`. Chaos case: kill the check mid-clone, assert no temp dir and an identical tree.

Section 4 Performance (2 issues found): one shallow clone per tick per repo only; offline health adds file reads and one `docs.py check` subprocess (budget: the health toy asserts the adoption group runs in under 20 seconds on a toy repo; the unknown real-repo scale is [estimated], re-measure before the gate); the clone has a 30 second cap and runs once per pass, not per rule.

Failure modes registry (eng; new paths):
  CODEPATH                 | FAILURE                          | RESCUED | TEST        | USER SEES        | LOGGED
  wiki clone               | timeout, no origin, auth         | Y       | flags       | named gap        | issue via health file
  wiki clone               | not-found (no wiki yet)          | Y       | gaps-state  | NOTE             | n/a
  printed Fix              | hostile page name                | Y       | gaps-state  | sanitized, manual| n/a
  queue                    | dirty or off-base followed repo  | Y       | queue       | Issues line      | Issues
  queue                    | prefix collision                 | Y       | queue       | both queued      | queue.md
  health                   | network in a non-tick run        | Y       | health-same | INFO not checked | n/a
  lag --new                | malformed version text           | Y       | lag-line    | v0 line          | n/a
  size                     | script over cap on a merge       | Y       | package     | build fails      | n/a
  critical gaps: 0

NOT in scope (eng): per-code doc anchors; a TODOS.md file (none exists here and creating one is outside this plan's files; every deferral is recorded in this record); widening the major-version refusal to 0.x minors; a clone cache; telemetry for TTHW; the Windows task check; a gh branch-protection read.
What already exists (eng): docs.wiki_url, entry.lagging and version_key, render.stale_blocks, deployments.owed, workflows.key_of and slots, agents.sibling, file.py issue filing, controls auto-import, regression.py red, the `# reads:` header and `want PART` toy conventions, GIT_TERMINAL_PROMPT=0 in the docs scripts.
Worktree parallelization: Sequential implementation (one skill family, shared scripts in workflow-setup); one independent lane exists (docs and Setup.md text) that can run after step 8's code lands. Lanes: 1 sequential, 0 parallel.

Implementation Tasks (eng):
- [ ] T1 (P1, human ~1d / CC ~30min) agents.py, sync.py: resolver and aliases; Verify: migration-base-config
- [ ] T2 (P1, human ~1d / CC ~45min) enforce.py, defects.py: engine, wiki half, output and exit contract; Verify: clean, gaps-pr, gaps-state, flags, writes-nothing, robustness
- [ ] T3 (P1, human ~4h / CC ~20min) entry.py, goal.py: lag, refusal, NOTE; Verify: lag-line, major-refused
- [ ] T4 (P1, human ~4h / CC ~20min) settings.py, render.py or docs.py, agents.apply: automation entries and blocks; Verify: blocks-inserted
- [ ] T5 (P1, human ~4h / CC ~20min) rules.py, report.py, workflows.py: health rule, template-version row, tick online flag; Verify: health-same
- [ ] T6 (P1, human ~4h / CC ~20min) board_page.py, operate.py: behind, queue_migrations with guards; Verify: queue
- [ ] T7 (P1, human ~2h / CC ~10min) seed.py, workflows.py: public-on-Mac, own commit; Verify: mac-kept
- [ ] T8 (P2, human ~4h / CC ~20min) docs, SKILL.md rows, generated files, Verify-by-hand steps, regression rows with seen_red, Tests.md; Verify: docs check and package check
Assumption: task-type ratios as the skill's defaults.

Completion Summary (Eng): Step 0 scope accepted as-is; Reality rows 7 of 7, 1 unverified; Architecture 4 issues; Code quality 3; Test review diagram produced, 24 requirements; Performance 2; NOT in scope written; What already exists written; TODOS.md updates none (no file, items recorded here); Failure modes 0 critical gaps; Unresolved decisions 0; Outside voice codex unavailable, native completed; Parallelization 1 lane sequential; Lake Score N/A (no scored 10/10 questions asked).

Decision audit trail (eng rows):
| 14 | Eng | health offline by default, tick online | mechanical | P5 | determinism and speed | always online |
| 15 | Eng | sanitize and shlex-quote wiki page names | mechanical | P1 | untrusted text in agent-facing output | print raw |
| 16 | Eng | no-wiki-yet is a NOTE | mechanical | P1 | avoids a permanent false gap | gap |
| 17 | Eng | exact slug match, guarded queue write | mechanical | P1 | prefix collision, dirty checkouts | prefix match |
| 18 | Eng | keep REFUSED exit 1, keep major-only refusal | T | P5 | done line 5 wording; no caller needs a new code | exit 4, widen to minors |
| 19 | Eng | wiki half in enforce.py, blocks fallback in docs.py | mechanical | P3 | byte caps | new file |

- The engine's output, exit and untrusted-text rules in plan sections 1 and 4b (sanitized and quoted page names, redacted stderr, not-found wiki is a note, orphan and stale as defined) are required; tests: migration-gaps-state, migration-flags, migration-robustness.
- Health runs the engine offline unless `LOOP_MIGRATION_ONLINE=1` (set by the tick); MIG_TASK off a Mac is an INFO skip; MIG_VERSION is reported once by the template-version row; test: migration-health-same.
- The queue matches slugs exactly, writes only into a followed repo on its base branch with an unmodified queue file, and `template_lag` keeps its string return; test: migration-queue.
- `LOOP_INSTALLED_VERSION` is honoured only with `LOOP_TEST=1`; the lag line is also tested through the real install resolver; test: migration-lag-line.
- Every touched script ends at or under 20,460 bytes, measured on a scratch merge of the parallel goal before step 5, with the named fallbacks taken early; workflow-docs SKILL.md stays under 150 lines.
- Thirteen toy parts (clean, gaps-pr, gaps-state, flags, robustness, writes-nothing, health-same, base-config, lag-line, major-refused, blocks-inserted, queue, mac-kept) with seen-red dates from `regression.py red --break`, each row run as one part of dev/toy/test-migration.sh.

- Every gap code, class, exit code, `--pr` and `--offline` behaviour in plan sections 1 and 4 is required; tests: the toy parts migration-clean, migration-gaps-pr, migration-gaps-state, migration-flags, migration-writes-nothing.
- No new file under skills/; every script at or under 20,480 bytes, measured after each edit; seed.py, setup.py, sync.py, update.py, survey.py never grow; the named fallbacks apply at 20,460.
- A repo recorded `regression_runs: mac` stays mac through setup and prints no DRIFT; test: migration-mac-kept.
- New tests only under dev/toy; migration-check writes nothing (tree and .git listing identical before and after); no private name, path, token or email in any committed text.
- Docs: Setup.md Usage bullet plus Unreviewed SET-11, Health.md Usage and notes only, Tests.md re-rendered; no Reviewed requirement wording changes.
- Delivery shape: one pull request in ordered commits (check; resolver and writers; queue; public-on-Mac) with the stated cut order C, D, B; detect, queue and review, never detect and auto-apply.
- The queued migrate goal's own text and Verify by hand state its two halves (`--pr` before the merge, the full check after); the tick names only `origin/<base>` (asserted by mac-kept); every break command ends with a no-op guard; health rows print offline or online.

- The error and output contract in plan section 4b (GAP line shape, stderr and stdout split, exit codes 0, 1, 2, bounded no-prompt wiki clone with a 30 second cap, redacted URL, recovery text on every REFUSED and NOTE) is required; tests: migration-flags and migration-major-refused.
- The version line names the slug after the frozen wording, the refusal prints its recovery, goal.py new prints a NOTE when entry.py is missing and never blocks.
- Setup.md Usage carries one real gap example, one clean example, a code table with class, the test-only override names and the unfollow side effect; the Verify by hand steps are runnable commands with an Expect line and the measured TTHW.
- Exit codes of migration-check are 0 (no gap), 1 (gaps, a verdict), 2 (usage), 4 (could not run, including an unexpected exception with a trace file path); goal.py maps entry.py's exit 3 to its own refusal exit 2 and creates no goal state.
- Output carries CHECKED and DOCS lines and a progress line during the clone; the orphan Fix says owner only and irreversible; LOOP_MIGRATION_ONLINE is a supported switch listed in Usage; a secret-in-URL negative test exists.

- The engine's output, exit and untrusted-text rules in plan sections 1 and 4b (sanitized and quoted page names, redacted stderr, not-found wiki is a note, orphan and stale as defined) are required; tests: migration-gaps-state, migration-flags, migration-robustness.
- Health runs the engine offline unless `LOOP_MIGRATION_ONLINE=1` (set by the tick); MIG_TASK off a Mac is an INFO skip; MIG_VERSION is reported once by the template-version row; test: migration-health-same.
- The queue matches slugs exactly, writes only into a followed repo on its base branch with an unmodified queue file, and `template_lag` keeps its string return; test: migration-queue.
- `LOOP_INSTALLED_VERSION` is honoured only with `LOOP_TEST=1`; the lag line is also tested through the real install resolver; test: migration-lag-line.
- Every touched script ends at or under 20,460 bytes, measured on a scratch merge of the parallel goal before step 5, with the named fallbacks taken early; workflow-docs SKILL.md stays under 150 lines.
- Thirteen toy parts (clean, gaps-pr, gaps-state, flags, robustness, writes-nothing, health-same, base-config, lag-line, major-refused, blocks-inserted, queue, mac-kept) with seen-red dates from `regression.py red --break`, each row run as one part of dev/toy/test-migration.sh.
- Commit order 0 (constants and the two size trims), D (public-on-Mac), B (resolver, blocks, automation entries), A (the check), C (the queue), each passing its own toy parts; the cut, if any, is C only (this supersedes the earlier CEO cut order).
- Wiki safety: transport allowlist and process-group kill on the clone, printed `git rm --` with rejected or sanitized names and a fixed commit message, one redaction function over every output string, stale by publish's exact comparison with a round-trip toy, no-wiki-yet as a note.
- Version table (absent or unparseable is behind and never refused), health wiki rows grouped, manual offline `health file` documented, queue regex escaped with all five state-table rows and concurrency tested.

## Full-depth rerun (second pass over every phase; supersedes the compact first pass where they differ, keeps every decision unless a pass states a defect)

### CEO Step 0 in full

System audit (read from the repository, 2026-11-12). Recent history: v0.27.26 (local schedule) is the base; the goal commit is the only commit on this branch. No stash entries; the working tree holds only the two design and plan files and an untracked review scratch folder that this work does not touch. No TODOS.md exists, so there are no prior deferrals to reconcile; deferrals live in the plan's NOT in scope lists. The package is at its file cap (96 files under skills/ plus three counted files, limit 99), and five setup scripts sit within 300 bytes of the 20,480 script cap. A parallel goal (operator-setup) exists as a branch holding only its goal file, and its done lines 8 and 12 overlap this plan. Retrospective check: the history shows repeated "script at size cap" fixes (package-cap-3, skill-size, skill-size-2 goals), which is the recurring architectural pressure this plan answers with per-function budgets and named fallbacks rather than a new file.

Taste calibration. Good references: `deployments.owed` (a pure function returning typed rows, no I/O side effects), `render.stale_blocks` (one function shared by two callers), `file.py`'s REPORT_ONLY (one explicit list that decides filing). Patterns to avoid: `docs.clone` (exits the process, unbounded, not shallow) and `sync.base_config` (reads a local ref only, which is the done-line-7 bug).

0A Premise challenge. The real problem: an adopted repo can be many versions behind with no verdict and no nudge, so migrations are done by memory. Target outcome: one read-only command whose exit code is the migration's done test, a nudge at work start, and an automatic queue entry per behind repo. Do-nothing cost: repos stay on stale START.md, no Settings or Automation blocks, no local task, orphan wiki pages, and the owner keeps asking by hand (the goal header shows this happened twice). The plan solves the pain directly for files, settings, blocks, task and wiki; it solves only a proxy for "required checks are reported", because the real gate (branch protection) is unreadable without gh, which health forbids; the plan says so on the NOT CHECKED line instead of claiming it.

0B Existing code leverage (sub-problem, reuse, why not rebuild):
| Sub-problem | Reused code | Rebuild rejected because |
|---|---|---|
| version behind | entry.installed, lagging, version_key (skills/workflow-docs/scripts/entry.py:210-225) | lagging already encodes the template-checkout exception |
| files current | entry.py check through agents.entry | same renderer the writer uses, so check and writer cannot disagree |
| blocks stale | render.stale_blocks (render.py:401) | already what docs.py check calls |
| format, Runbook | docs.py check, deployments.owed (deployments.py:86) | the DOC-16 rule lives once |
| local task | workflows.load, key_of, slots (workflows.py:63-115) | the tick reads the same registry |
| wiki | docs.wiki_url (docs.py:88), read_map (counting.py:160) | URL and page map exist; only the clone is rebuilt (bounded) |
| filing | file.py BAD and REPORT_ONLY (file.py:40-44) | WARN rows are already filed every tick |
| controls | controls.CONTROLS auto-import (controls.py:215-219) | no controls.py edit needed |
| base config | none correct (sync.py:148-165 is the bug) | one resolver replaces two functions |
| queue | goal.py queue via fit.cmd_queue | only the detection and de-dup are new |

Reality rows: see the compact pass above (7 of 7, one unverified premise: the exact rendered kind string of a Runbook line from docs.py check; the toy proves it and the fallback is matching the DOC-16 id).

0C Dream state:
  CURRENT: repos drift silently; a person asks "is it migrated?" and re-derives the answer
     --->  THIS PLAN: one coded verdict, a health WARN that files an issue, a queued migrate goal per behind repo, a nudge at session start, and update --apply that closes the gaps it can
     --->  12-MONTH IDEAL: every release auto-migrates every followed repo through a merged PR; the owner only performs the Mac steps and the check says MIGRATION OK with branch protection read too

0D Alternatives. Three approaches for the whole plan (the independent sub-choices are decided in their own rows below):
| Commitment | Current | A (design as amended: engine in two existing files) | B (smaller: core check of version, files, settings, blocks only) | C (larger: new migrate.py with an apply mode) |
|---|---|---|---|---|
| frozen done lines 1 to 11 met | pending | all eleven | lines 1, 4, 5, 7, 11 only | all eleven plus apply |
| new file under skills/ | none | none | none | one (file 100 of 99, impossible) |
| writes anything | no | no (done line 3) | no | yes (breaks done line 3) |
| bytes | n/a | defects.py and enforce.py plus 13 scripts | fewer scripts | adds a 20 KB file |
Effort: A is L (human about 5 days, CC about 3 hours), B is M, C is XL. Risk: A medium (byte pressure), B high (cannot meet done lines 6, 8, 9, 10: rework forced), C blocked (package cap and done line 3). Auto-decision (P1 completeness, P5 explicit): A. B is the CEO reviewer's reframing; it fails five frozen done lines, so it is rejected, not deferred.

0E Mode selection. Recommendation: SELECTIVE EXPANSION, because the plan adds a capability to an existing toolchain (not a greenfield system) and its value depends on a few optional hardening choices (offline health, sanitization, guarded queue) that each need a separate approve or skip; the count rule (about 25 changed files, over 15) would recommend reduction, but every file is named by a frozen done line, so reduction would cut required behavior. Mode: SELECTIVE EXPANSION, auto-selected at the recommendation. Approved decisions governing it: 0D row A; scope rows 1 to 12 below.

0F and 0G Expansion framing (SELECTIVE). 10x check: a repo owner gets, with one command, the exact list of what stands between a repo and "fully migrated", and the operation session closes most of it by itself. Platform potential: the engine's gap list is a reusable verdict for any future "is this repo ready for X" check (it returns tuples). Delight scan (30-minute improvements): 1 print the code table in Setup.md Usage (accepted, inside docs scope); 2 an `--explain CODE` flag (skipped: Fix text already explains); 3 a one-line summary count per class on the last line (accepted: `N gap(s) (a PR-closable, b state)`, S); 4 color or glyphs (skipped, agent reader); 5 a `--since vX` filter (skipped, no consumer); 6 print the migrate goal slug in the nag (accepted earlier); 7 time the check and print seconds (skipped, health already prints its clock). Cherry-pick ceremony, each decided separately (A add, B defer, C skip):
| # | Candidate | Effort | Risk | Decision | Reason |
|---|---|---|---|---|---|
| 1 | drop the design's --json flag | S | low | A add (the drop) | no consumer, 250 bytes |
| 2 | public-on-Mac fix in seed.py and workflows.py | S | medium | A add | MIGRATION OK is unreachable otherwise; own commit |
| 3 | NOT CHECKED qualifier line | S | low | A add | a green result must not overclaim |
| 4 | class counts on the last line | S | low | A add | clearer than N gaps |
| 5 | offline-by-default health, online in the tick | S | low | A add | deterministic, fast health |
| 6 | sanitized, quoted wiki names | S | low | A add | untrusted text in agent-facing output |
| 7 | guarded queue write | S | low | A add | never dirty another checkout |
| 8 | fix script printer | M | medium | C skip | duplicates update --apply |
| 9 | gh branch-protection read | M | medium | B defer | health makes no gh call |
| 10 | delete orphans from the command | S | high | C skip | done line 3 |
| 11 | Windows task check | M | medium | B defer | parallel goal done line 7 |
| 12 | per-code ignore list | M | low | B defer | explicit off settings cover it |
All auto-decided at the recommendation; accepted rows enter scope, B rows go to NOT in scope (no TODOS.md exists), C rows are rejected.

0H Persist the CEO plan: the CEO scope summary is saved in the review scratch folder and the plan's Review record; the working plan is this file's Implementation plan. The Spec Review Loop runs below (three launches allowed, stop on PASS or repeat).

0I Temporal interrogation (what the implementer meets, with human-team and CC effort):
  HOUR 1 (foundations; human 4h, CC 15 min): which file owns what. Answer ready: defects.py engine, enforce.py wiki half, agents.py resolver and path-load, entry.py lag. Surprise avoided: sync.py aliases need `import agents` order (sync.py imports agents already).
  HOUR 2-3 (core logic; human 1.5d, CC 40 min): the truth table has six cases and the MIG_FILES/MIG_CHECKS agreement; ambiguity avoided by the written table; the Runbook line kind string is unverified (toy decides).
  HOUR 4-5 (integration; human 1d, CC 30 min): setup.py is 20,340 bytes and may not grow; the docstring trim must precede the dispatch line. The scratch merge with the parallel goal can change every byte figure. Surprise avoided: workflow-docs SKILL.md is at 149 of 150 lines.
  HOUR 6+ (polish and tests; human 2d, CC 60 min): 13 toy parts, 13 break commands, regression rows after the code commit, Tests.md re-render, package check. They will wish they had planned the fake wiki and origin fixtures first; the toy header lists them.

### CEO dual voices and Sections 1 to 11 in full (second pass)

Voices. Spec review: three launches this pass (scores 7, 7, 7; every issue applied in the plan text, see the closing line below). Native CEO voice: completed, 10 findings, INPUT hash matched its snapshot. Codex outside voice: unavailable (it needs network and was skipped; this is missing coverage, never a clean result). Tag [subagent-only].

CEO DUAL VOICES - CONSENSUS TABLE:
  Dimension                              Claude  Codex  Consensus
  1. Premises valid?                      yes     N/A    N/A (voice coverage missing)
  2. Right problem to solve?              yes     N/A    N/A
  3. Scope calibration correct?           risky   N/A    N/A (native: bundle is large; done lines force it)
  4. Alternatives sufficiently explored?  partly  N/A    N/A (native: detect-and-apply never weighed; now written, plan 4c)
  5. Competitive/market risks covered?    yes     N/A    N/A
  6. 6-month trajectory sound?            risky   N/A    N/A (byte caps, break commands, ignore path)

Disposition of the ten native findings: 1 [critical] split the bundle: TASTE, kept as one PR but built as ordered commits A to D with a stated cut order (plan 4c); 2 [high] the byte cap as unmovable: TASTE, kept (owner constraint; the plan adds no file and no script ends larger where the owner said fold or trim); 3 [high] zero-gh premise: TASTE, kept deferred, now with a named trigger and owner (plan 6b); 4 [high] the --pr done line is a deviation: kept as a stated deviation, now written in the queued goal's own text and Verify-by-hand, not only the PR body; the owner may overrule in review; 5 [high] public-on-Mac safety asserted not tested: ACCEPTED, mac-kept asserts the tick names only origin/<base>; a lightweight Actions check for public repos is listed as a later owner call; 6 [medium] shared constants need an owner: ACCEPTED, the workflows.py constants land as the first commit so the parallel goal can rebase on them; 7 [medium] online and offline disagree: ACCEPTED, the mode is printed in each health row; 8 [medium] break commands rot: ACCEPTED, each break ends with a no-op guard so red refuses a break that changed nothing; 9 [medium] no ignore path, noisy issues: ACCEPTED in part, issues are keyed by rule and subject so a standing difference is one open issue; the ignore list stays deferred; 10 [medium] detect-and-apply never weighed: ACCEPTED, plan 4c states the protected property (nothing changes without a reviewed PR). Premises raised: the template never exercises its own MIG_VERSION (true, documented, covered by the toys through the test override); the "only FAIL and UNREAD turn health not green" property is today's code (a later change would turn the WARN rows into blockers; recorded as a watch item in the failure registry).

Section 1: Architecture Review. Current scope: mode SELECTIVE EXPANSION; governing rows 1 to 23 in the scope table; accepted rows 1 to 11 and 23; deferred 13, 15, 16, 17, 21, 22; rejected 19 and 20; skipped 12, 14, 18.
System design and boundaries: the check is a pure function over files and git in the one module health already loads (defects.py), with its network half in enforce.py; callers are three thin shells (setup's migration-check, the health rule, the queue function). Coupling added and justified: setup to health (path-load, fail soft); operation session to setup (subprocess); goal.py to entry.py (subprocess, never blocking). Data flow, all four paths, for the one new flow (config and registry to gaps):
  INPUT (config.json, registry, docs.tsv, git, wiki) -> VALIDATION (names OSError, ValueError) -> TRANSFORM (rules per code) -> OUTPUT (GAP lines, NOT CHECKED, last line)
    happy: every file parses, gaps listed or MIGRATION OK
    nil: no config.json -> MIG_SETTINGS and MIG_VERSION v0, no traceback
    empty: empty registry -> MIG_TASK gap; empty wiki -> no orphan, no stale
    error: clone timeout or auth -> MIG_WIKI_UNREADABLE with cause; not-found -> NOTE; docs.py check exits non-zero -> MIG_FORMAT with exit code and stderr tail
State machines: none stored. The queue has implicit states (current, behind and unqueued, queued, running, finished-same-version, finished-older); the state table in plan section 4 is its diagram, invalid transitions (requeue while queued) are prevented by the exact-slug check running before any write.
Scaling: the check reads a handful of small files, one `docs.py check` subprocess and at most one shallow clone; at 10x repos the operation pass visits N followed repos serially (a few file reads each, no clone), at 100x the tick's per-repo clone is the cost, capped at 30 s per repo and run only in the tick.
Single points of failure: the registry file and the wiki remote (each a named gap), workflow-health being installed (fail soft). Security architecture: no new endpoint; untrusted text enters only through wiki page names and git or docs stderr; both sanitized, quoted and redacted (plan 4b). Production failure per integration: wiki timeout (bounded, one retry by the owner), a queue write into a dirty checkout (guarded), a missing entry.py in goal.py new (NOTE, never blocks).
Rollback: revert the pull request; writers only add keys and blocks and never overwrite, the check writes nothing; no data migration. Rollback time: one revert and a skills release.
Value test (artifacts about the work): the gap list is consumed by health (rule and issues), the queued migrate goal (done line) and the owner's migration; it retires with the last repo's migration; it is the smallest version that meets done lines 1 to 11.
Selective-expansion check: accepted cherry-picks 2 to 11 integrate cleanly; row 2 (public-on-Mac) is the one with coupling concern (seed.py and workflows.py), isolated in its own commit.
Required diagram (system architecture): see the Eng section's diagram in the compact pass above, extended here with the lag path:
  session start -> entry.py check (LAG line) / agent block bullet -> entry.py lag -> one line
  goal.py new -> entry.py lag --new -> warn | exit 3 (differing major) | migrate- slug passes
Findings in this section: [INFO 9/10 plan 4c] a bundle of this size needs a stated cut order (applied); [INFO 8/10 plan section 3] shared constants need a first-commit owner (applied); [INFO 7/10 plan 4b] the mode must show in health rows (applied). Decision gate: each applied by an auto-decision at the recommendation (rows 6, 7, 10 of the voice table); none pending.

Section 2: Error and Rescue Map.
  METHOD/CODEPATH             | WHAT CAN GO WRONG                | EXCEPTION CLASS
  engine config read          | missing, unreadable, bad JSON    | OSError, ValueError
  engine registry read        | missing, unreadable              | OSError, ValueError
  enforce.clone               | timeout, no origin, auth, DNS    | subprocess.TimeoutExpired, OSError, nonzero exit
  enforce.docs_check          | subprocess exits nonzero or empty| nonzero exit
  enforce.page names          | hostile or non-UTF-8 names       | UnicodeError
  agents.migration_check      | workflow-health absent           | missing path
  entry.lag                   | no config, bad version text      | OSError, ValueError
  goal.py new lag call        | entry.py missing                 | missing path, nonzero exit
  agents.resolver             | no candidate parses              | ValueError
  board_page.queue_migrations | goal.py queue fails, dirty repo  | nonzero exit
  settings.fill_automation    | unreadable config                | existing REFUSED path
  EXCEPTION CLASS            | RESCUED | RESCUE ACTION                                   | USER SEES
  OSError/ValueError (config)| Y       | MIG_SETTINGS gap "unreadable", rest of run goes | named gap
  TimeoutExpired             | Y       | MIG_WIKI_UNREADABLE cause timeout               | named gap, retry once
  clone not-found            | Y       | NOTE, no gap                                    | note
  docs check nonzero         | Y       | MIG_FORMAT with exit code and 200-char tail     | named gap
  UnicodeError (name)        | Y       | skip name, list as manual                       | manual fix line
  missing workflow-health    | Y       | stderr REFUSED, exit 1                          | one line with fix
  missing entry.py           | Y       | stderr NOTE, goal.py new proceeds               | note
  queue failure              | Y       | Issues line with stderr tail, "nothing queued"  | Issues line
  No catch-all handlers; each handler names its exception classes (the wiki clone wrapper names three). Logging: each gap names code, subject and values (never config values). LLM or prompt calls: none. CRITICAL GAPS: 0.

Section 3: Security and Threat Model. Attack surface: wiki page names (untrusted collaborator text printed into agent-facing output and issues); git and docs stderr (may carry URLs with credentials); the temp clone directory; the queue write into another checkout. Input validation: page names allowlisted to [A-Za-z0-9._ -]{1,80}, others shown sanitized with a manual Fix and never inside a command; `--repo` must be a git repo (exit 2); slugs matched by an anchored regex. Authorization: the check is read-only; the queue writes only into followed repos that are on their base branch with an unmodified queue file; no gh call, no token read. Secrets: none new; the clone URL is redacted of userinfo; config values are never printed. Dependency risk: none (standard library and existing scripts). Data classification: no PII; wiki URLs and repo names only. Injection vectors: shell (shlex.quote, allowlist), command via printed Fix (never built from raw names), prompt injection via page names into an agent (sanitized, length-capped), path traversal via page names (names are never used as file paths; the clone is read with os.listdir inside the temp dir). Audit logging: filed issues are the trail. Threat table: hostile page name, likelihood Medium (any wiki collaborator), impact High (agent copies a command): mitigated; credential in URL, Low, High: mitigated; fork-PR code execution on the Mac for a public repo recorded mac, Low, High: mitigated by running the base-branch tree only and asserted by a toy; queue write into a dirty checkout, Medium, Medium: mitigated by the guard. Findings: none open.

Section 4: Data Flow and Interaction Edge Cases. Data flow tracing (the three flows): (a) CLI: argv -> repo root -> gap tuples -> text; shadow paths: nil (no git repo: exit 2), empty (no docs.tsv: wiki and docs codes absent), wrong type (config key of the wrong JSON type: MIG_SETTINGS names the key), too long (page name over 80: sanitized), exception (clone timeout), conflict (two concurrent runs: each has its own mkdtemp), stale (published page older than the source: MIG_WIKI_STALE), partial (docs check partial output: MIG_FORMAT with tail), encoding (non-UTF-8 name: manual line). (b) health: same engine, offline; a repo with no origin is simply offline. (c) queue: followed repo list -> behind() -> state table -> goal.py queue; shadow paths: a repo path that is gone (skipped), a repo that is not git (skipped), queue.md absent (MIG_FILES says so; queue writes create it? no: it refuses and says why). Async ordering: the check holds no shared mutable state; the queue write and a running operation session in that repo could race on queue.md: the base-branch and unmodified-file guard plus the exact-slug check run immediately before the write, and goal.py queue appends one line atomically (the existing fit.cmd_queue path), so the worst case is a duplicate line that the next pass sees and skips. Interaction edge cases: double run (idempotent, no writes), run from a subdirectory (resolved to the repo root, tested), detached HEAD (base branch guard refuses the queue write, check still works), offline (named note), slow clone (30 s cap), zero or huge wiki (page list capped at 200 names with a count line), repeated release (versioned slug), repo renamed (queue slug uses the repo directory name; a rename starts a new slug, harmless). Findings: none open beyond those applied.

Section 5: Code Quality Review. Organization: one function per gap code in defects.py, wiki and docs parse in enforce.py, resolver and path-load in agents.py, lag in entry.py: each next to the code that already owns that knowledge. Duplication: template_lag and behind share one reader; the task-name format string lives once (asserted); the version parse reuses entry.version_key (hardened once). Naming: gap codes are nouns that name the check (MIG_BLOCKS), functions are verbs for what they do. Error handling patterns: see Section 2; no swallow-and-continue (every rescue yields a named gap, note or REFUSED). Missing edge cases: covered in Section 4 and the robustness part. Over-engineering: none (no cache, no json, no ignore list, no new file). Under-engineering: the output contract is explicit. Cyclomatic complexity: each gap function stays under 5 branches by the per-function byte budget (a function that needs more is split or its case moves to a table); the automation and task truth table is a table of six rows, not nested ifs. Findings: [INFO 7/10 plan section 2] the truth table should be data, not branches (recorded as an implementation rule: a six-row tuple table).

Section 6: Test Review. Diagram (every new item, type, existing test, happy, failure, edge):
  ITEM                         TYPE        EXISTING   HAPPY           FAILURE                    EDGE
  engine, 15 codes             integration none       clean           gaps-pr, gaps-state        robustness
  wiki clone and parse         integration none       gaps-state      timeout, not-found, auth   hostile name, empty wiki
  --pr/--offline/--repo/usage  integration none       flags           unknown flag exit 2        --pr with --offline
  health rule and row          integration test-docs   health-same     INFO rows offline          issue filing preview
  entry lag and refusal        integration none       lag-line        differing major exit 3     malformed version, no config
  goal.py new nag              integration test-goal   major-refused   entry.py missing NOTE      migrate- slug exempt
  resolver                     integration test-sync   base-config     no candidate               clone with no local main
  blocks and entries           integration test-sync   blocks-inserted never overwrites a set entry pre-0.27.17 repo
  queue                        integration none       queue           dirty or off-base repo     app versus app-api, second pass
  public-on-Mac                integration test-setup  mac-kept        DRIFT absent               tick names origin/<base> only
  writes nothing               integration none       writes-nothing  temp clone removed         kill mid-clone
  size                         package     package    package check   over-cap script            scratch merge
  Test ambition: the 2am Friday test is migration-writes-nothing plus gaps-pr on a copy of a real adopted repo; the hostile QA test is the hostile page name and the dirty followed repo; the chaos test is a kill during the clone. Pyramid: many cheap toy parts, no E2E beyond toys. Flakiness: no sleeps, no network, no clocks except the 30 s clone cap (tested against a fake unreachable origin that refuses immediately, so the test does not wait). Load: none needed. LLM and prompt changes: none touched, so no eval suites apply. Value cards: in the Eng test plan artifact (plan Eng section); `no_claim` states launchd, a live wiki and branch protection are not proven. Regression rule: existing behavior at risk is setup's regression_runs recording (public repos), update --check's base reading, health's rule set and goal.py new; each has a named toy row (mac-kept, base-config, health-same, major-refused). Findings: none open.

Section 7: Performance Review. N+1: none (no database); the queue visits each followed repo once per pass. Memory: page lists capped at 200; config files are tiny. Indexes and caching: none needed; the wiki clone is not cached (deferred row 21). Background jobs: the tick's one clone per repo, 30 s cap, inside the existing per-repo time cap. Slow paths: top three, with estimates marked [estimated]: shallow wiki clone (about 1 to 3 s online), `docs.py check` subprocess (about 1 to 5 s on a repo of this size, [re-measure before the gate]), the engine's own file reads (under 0.1 s). Connection pool: none. A hot path with no budget would be a finding: the adoption group in health has the budget "under 20 seconds on a toy" asserted by the health toy part.

Section 8: Observability and Debuggability. Logging: each gap line is the log (code, subject, values, fix); the queued goal's journal says why it was queued. Metrics: the verdict count line (a PR-closable, b state) is the metric; health files an issue per WARN row, which is the alert. Tracing: no cross-service flows; the subprocess calls print their own stderr tails on failure. Alerting: the tick's digest already reports DRIFT and judge state; migration WARN rows appear in its issue list. Dashboards: the Issues section of the board already shows template lag lines (unchanged strings). Debuggability three weeks later: the gap line names the code and the file or page, and the issue it filed names the same; the mode (offline or online) is printed in health rows. Admin tooling: none needed. Runbook: the Health page Runbook gains a short migration entry in the existing format (what the signal means, the owner step, how to confirm). Findings: [INFO 8/10 docs/wiki/Health.md Runbook] DOC-16 requires a Runbook subsection per registered routine; no new routine is registered, so no new subsection is required, but the Usage and notes mention is (applied in plan section 6).

Section 9: Deployment and Rollout. Migration safety: no data migration; writers only add keys and blocks. Feature flags: none needed; the nag never blocks and the refusal only fires on a differing major (0.x makes it inert today). Rollout order: ship the skills in a release, then each repo gets a queued migrate goal on the next operation pass; the order inside the plan is check first, then writers, then queue (commits A, B, C). Rollback plan, step by step: 1 revert the pull request; 2 release; 3 repos keep their `template_version` and any blocks already inserted (harmless); 4 delete queued `migrate-` lines by hand if wanted. Deploy-time risk window: old skills in one repo and new skills in another is the normal state (versions differ per repo), and the check is version-aware only through entry.installed. Environment parity: toys use temp HOME, a fake origin, a bare wiki; the real GitHub wiki is not tested (Verify by hand covers it). Post-deploy verification, first 5 minutes: run the check in the oldest adopted repo and compare with the expected gap list (the design's assignment); first hour: confirm one queued migrate goal appeared once. Smoke tests after deploy: `health.py check --group adoption` on this repo shows only the two expected WARN rows. Selective-expansion addition: the second-to-merge goal's scratch-merge gate makes shipping routine. Findings: none open.

Section 10: Long-Term Trajectory. Technical debt: code debt (byte-packed scripts near the cap; the next goal begins with a fold-or-trim negotiation), operational debt (the Mac-only task and wiki steps stay manual), testing debt (13 break commands to maintain), documentation debt (a code table in Usage, no per-code anchors). Path dependency: stable codes become an interface (health issues, queue lines); adding a code later is cheap, renaming one is not. Knowledge concentration: the truth table and class split are written once in the plan and Setup.md. Reversibility: 4 of 5 (one PR revert; filed issues and queued lines remain). Ecosystem fit: follows the repo's `REFUSED:` and `Fix:` style, `want PART` toys and the controls convention. The 1-year question: a new contributor reads the gap table and the code list in Setup.md Usage; the engine is one file plus one half-file. After this ships: phase 2 is an optional CLI gh read and a Windows task check (rows 13 and 15); the engine's tuple output supports both. Platform potential: any future readiness check can reuse `migration_gaps`-style rows. Retrospective on cherry-picks: the right ones were accepted (hardening rows are small); the rejected fix-script printer was not load-bearing for any accepted row.

Section 11: Design and UX Review. SKIPPED (no UI scope: the surfaces are terminal text and files).

Error and Rescue Registry: see Section 2 tables (8 rows, 0 critical gaps).
Failure Modes Registry:
  CODEPATH               | FAILURE MODE                      | RESCUED | TEST            | USER SEES        | LOGGED
  wiki clone             | timeout or auth                   | Y       | flags           | named gap        | issue
  wiki clone             | no wiki yet                       | Y       | gaps-state      | NOTE             | n/a
  printed Fix            | hostile page name                 | Y       | gaps-state      | sanitized        | n/a
  queue                  | dirty or off-base repo            | Y       | queue           | Issues line      | Issues
  queue                  | duplicate line from a race        | Y       | queue           | skipped next pass| queue.md
  health                 | rule property changes (WARN blocks)| Y      | health-same     | watch item       | n/a
  tick                   | runs a fork ref on a public repo  | Y       | mac-kept        | none             | n/a
  seed.py                | recorded mac flipped              | Y       | mac-kept        | no DRIFT         | n/a
  size                   | script over cap                   | Y       | package, gate   | build fails      | n/a
  CRITICAL GAPS: 0.

NOT in scope (CEO): rows 13, 15, 16, 17, 21, 22 deferred with reasons in plan 6b; rows 12, 14, 18 skipped; rows 19, 20 rejected. What already exists: see 0B in Step 0. Dream state delta: see 0C. TODOS.md updates: none proposed (no TODOS.md; items are in plan 6b). Scope proposals: 23 proposed, 15 accepted (1 to 11 and 23 and the plan-level items), 6 deferred, 3 skipped, 2 rejected (counts by row: accepted 1 to 11 and 23 = 12; deferred 13, 15, 16, 17, 21, 22 = 6; skipped 12, 14, 18 = 3; rejected 19, 20 = 2).

Decision audit trail (second pass rows):
| 20 | CEO | one PR in ordered commits A to D with a cut order | T | P6 | review is the gate; each commit stands alone | three PRs |
| 21 | CEO | gh read deferred with trigger and owner | T | P3 | health makes no gh call | implement now |
| 22 | CEO | --pr deviation written into the queued goal's text | mechanical | P5 | explicit over buried | PR body only |
| 23 | CEO | mac-kept asserts origin/<base> only | mechanical | P1 | a safety claim needs a test | assert nothing |
| 24 | CEO | break commands end with a no-op guard | mechanical | P5 | red refuses a no-op break | trust the sed |
| 25 | CEO | detect-queue-review over detect-and-apply, stated | mechanical | P5 | protects review gating | auto-apply |

Completion Summary (CEO, second pass): mode SELECTIVE EXPANSION; System audit: package full, five scripts near cap, a parallel goal overlaps, no TODOS.md; Step 0: 23 scope rows, 0D approach A; Section 1: 3 issues; Section 2: 11 error paths mapped, 0 gaps; Section 3: 0 issues, 0 high; Section 4: 11 edge cases mapped, 0 unhandled; Section 5: 1 note; Section 6: diagram produced, 0 gaps; Section 7: 0 issues (estimates labeled); Section 8: 1 note applied; Section 9: 0 risks; Section 10: reversibility 4/5, debt items 4; Section 11: SKIPPED; NOT in scope written (6 deferred); What already exists written; Dream state delta written; Error/rescue registry 8 rows, 0 critical gaps; Failure modes 9 rows, 0 critical gaps; TODOS.md updates 0; Scope proposals 23 proposed, 12 accepted, 6 deferred, 3 skipped, 2 rejected; CEO plan written (summary file and this record); Outside voice codex unavailable, native completed; Lake Score N/A (no scored 10/10 questions were asked; scope rows are kind-not-coverage); Diagrams produced: architecture, data flow, state table, error flow, test diagram, rollback steps; Stale diagrams found: none; Unresolved decisions: 0 owner-only; Reality rows: 7 of 7, unverified 1.

Spec review closing line: three launches used (cap); issues verified: 17 of 18 applied in the plan text and checked by reading it back; the 18th (the unlabeled duplicate requirement bullets the review tooling appends after step 10) is resolved in the final restructure, where they move under one heading in this record.

### DX review in full (Phase 2.5, second pass)

Applicability: developer-facing scope is present (CLI tool and Claude Code skill; users are the owner and the agents that run the loop). Product type: CLI tool plus Claude Code skill, primary CLI tool (auto-confirmed at the recommendation). Mode: DX POLISH (enhancement to an existing product; auto at the recommendation), so only touchpoints within the accepted scope are examined and no API is added to raise a score.

Step 0A Developer persona (primary: the AI agent; secondary: the owner).
  TARGET DEVELOPER PERSONA
  Who:       an unattended coding agent in the operation session or a goal worker; the owner reads its output
  Context:   starts work in an adopted repo, or is asked whether a repo is fully migrated
  Tolerance: one command, one screen, no prompt; it retries blindly and reads output literally
  Expects:   a verdict it can act on, a fix it can run or hand to the owner, exit codes it can branch on
  Evidence read: the goal header (the owner asked twice), the design's Target User, Setup.md Usage (every command prints codes and a fix), the existing REFUSED/Fix style.

Step 0B Empathy narrative. "I open a repo adopted months ago. START.md reads fine and setup says NO CHANGE, so I believe it is current. I run the migration check and get a short list: the template version is behind, the Settings and Automation blocks are missing from Home and the README, and the Mac task is not registered. Each line ends with a command or says it is the owner's step; below them a line says branch protection was not read, one line says what was compared, and one points at the code table. I run the migrate goal, it passes its PR-closable check in its own worktree, I merge, and the full check now lists only the wiki page and the Mac task, both marked owner only. After those it prints MIGRATION OK. What I cannot tolerate is a green line that means less than it says, and an exit 1 that might mean the check never ran." (Observed: the existing commands and their style; predicted: the exact output text, which the toy captures.) Confirmation: accepted as written (auto).

Step 0C Competitive DX benchmark (reference benchmarks; no web research, the call needs network and was skipped; none of the times is measured).
| Tool | Start to result | Time and evidence | DX choice | Source |
|---|---|---|---|---|
| package-manager doctor checks | one command to a list of named problems | about 1 min, reported | each problem names its fix, exit code is the gate | general practice, not cited |
| linters with a fix mode | one command to a list and optionally a diff | about 1 min, reported | machine-readable codes | general practice, not cited |
| infrastructure drift checks | plan command to a diff against desired state | a few minutes, reported | read-only plan, separate apply | general practice, not cited |
| this plan | one command to coded gaps with fixes | about 1 min, estimated (the toy time is recorded in Verify by hand) | read-only, separate apply (update --apply and the migrate goal), PR-closable versus state split | this plan |
Boundaries: persona = agent, start = the repo cloned and the skills installed, useful result = the gap list. TTHW target: Champion (under 2 minutes); the approved clock is the wall time of one run on a toy with a bounded 30 s clone; the target is auto-selected at the recommendation (A, Champion; feasibility: one command, no install beyond the package, no sign-in, blocker: the online clone on slow networks, mitigated by --offline and the progress line).

Step 0D Magical moment. The moment: the first run names exactly what stands between the repo and "migrated" with a runnable fix for each, and the second run after the merge prints MIGRATION OK with an honest qualifier. Delivery vehicles within existing capabilities: A the command's own output (chosen, recommended); B a generated checklist file in the repo (rejected, writes, breaks done line 3); C keep today's experience (rejected, evidenced gap). Out-of-scope opportunity listed separately: a hosted dashboard of migration state across repos.

Step 0E Mode: DX POLISH (recommended, taken).

Step 0F Developer journey, all six stages traced against docs and code, friction decided (A fix in plan, B alternative, C document, D accept):
| STAGE | DEVELOPER DOES | EVIDENCE | FRICTION | DECISION | STATUS |
|---|---|---|---|---|---|
| 1 Discover | sees the nag at session start or a queued goal | README and START.md say nothing about migration today; entry.py check prints a LAG line with no command | the line says "ask for workflow-setup update", not what to run | A: one shared sentence plus slug hint, printed by code | fixed |
| 2 Install | nothing; ships in the package | workflow-health must sit beside workflow-setup | missing health gives a bare traceback today for any health import | A: exit 4 REFUSED with a fix | fixed |
| 3 Hello World | runs `setup.py migration-check` | Setup.md Usage lines carry output shapes | no example output | A: one gap run and one clean run in Usage | fixed |
| 4 Real Usage | `--pr` in the worktree, full check on the Mac | design Verify steps | `--pr` unclear | A: help text, last-line qualifier | fixed |
| 5 Debug | reads GAP lines and follows Fix | orphan fix targeted a temp clone | unsafe or unclear fixes, wiki lumped errors | A: persistent path, cause, sanitized names, owner-only text | fixed |
| 6 Upgrade | next release lags every repo again | queue state table | repeat releases | A: versioned slugs, one goal per version | ok |
Updated journey map above; no stage is deferred.

Step 0G First-time developer roleplay (grounded in the plan and code):
  T+0:00 runs the command from the skill folder; sees the DOCS line and the code table pointer.
  T+0:20 sees MIG_VERSION behind and a Fix naming the migrate goal.
  T+0:40 sees MIG_TASK `SKIP (not a Mac)` on a Linux box: not counted, listed on NOT CHECKED.
  T+1:00 runs `--pr` in a worktree: exit 0, last line says state codes not checked.
  T+2:00 hits the wiki orphan: Fix says owner only, after the merge, irreversible without wiki history.
  T+3:00 succeeds, or gets exit 4 and knows no verdict was reached.
  Each confusion point has a remedy in plan 4b.

DX DUAL VOICES - CONSENSUS TABLE:
  Dimension                           Claude  Codex  Consensus
  1. Getting started < 5 min?          yes     N/A    N/A (voice coverage missing)
  2. API/CLI naming guessable?         mostly  N/A    N/A
  3. Error messages actionable?        gaps    N/A    N/A
  4. Docs findable & complete?         gaps    N/A    N/A
  5. Upgrade path safe?                yes     N/A    N/A
  6. Dev environment friction-free?    mostly  N/A    N/A
Voices: native DX subagent completed (INPUT hash matched its snapshot; 2 CAP4, 6 CAP6, 7 medium findings); Codex unavailable (network skipped; missing coverage). Tag [subagent-only].

Native findings and dispositions (DX POLISH): CAP4 REFUSED shares exit 1 with gaps: ACCEPTED, REFUSED and unexpected exceptions exit 4, only 0 and 1 are verdicts; CAP4 entry.py exit 3 unmapped in goal.py new: ACCEPTED, goal.py maps it to its own refusal exit 2 and creates no goal state (tested); CAP6 recovery text on GAP lines: ACCEPTED (owner-only and irreversible wording on the line, one retry); CAP6 no per-code anchor: TASTE, kept (shared table is the document target, the DOCS line names it; per-code headings would not fit the PRD page template and no new file may be added); CAP6 context: ACCEPTED, CHECKED line; CAP6 trace: ACCEPTED, MIG_INTERNAL with a trace file path; CAP6 NOTE has no fix: ACCEPTED; ignore escape hatch: TASTE, kept deferred with a trigger; first-run clone time: ACCEPTED, progress line and mode on CHECKED; invocation length: ACCEPTED (full command in Usage); naming of --pr: ACCEPTED in part (help text defines it; no alias, to keep one name); LOOP_ variables: ACCEPTED (LOOP_MIGRATION_ONLINE documented as supported); clean-run verbosity: kept (agents want the lines; no --quiet, deferred); version typo message: ACCEPTED; usage-error fix line: ACCEPTED; secret-leak negative test: ACCEPTED (in the flags part).

Pass 1 Getting started (before 6, after 9). Evidence recall: target Champion, vehicle output, friction at stages 1 and 3. Installation: nothing beyond the package (one command to start). First run: visible meaningful output (gap list or MIGRATION OK, always CHECKED and DOCS lines). Sandbox: the toy is the sandbox (no real repo needed). Free tier and sign-in: none (no gh, no network by default for health; the CLI clones the wiki only when online and bounded). Quick start: Setup.md Usage carries the full command and a real gap run and clean run. Auth bootstrapping: none. Magical moment delivery: the chosen vehicle is the output and is in the plan. Competitive gap: estimated within Champion; unmeasured, re-measured in Verify by hand. FIX TO 10 sequence: 1 `python3 skills/workflow-setup/scripts/setup.py migration-check` (about 1 s offline, up to 30 s online), 2 read GAP lines, 3 run the Fix or the migrate goal, 4 rerun. 4 steps with a 3-step minimum path for a clean repo (1 command). Stripe test: a persona goes from never-heard-of to a verdict in one terminal session, yes. Residual: not measured on a real repo (10 needs a measured run). Decision gate: all remedies are routine work inside approved scope; none new.

Pass 2 CLI design (before 7, after 8). Evidence recall: the agent expects `verb [flags]` with the existing REFUSED/Fix grammar. Naming: `migration-check` follows the `/workflow-setup <verb>` map; flags `--repo`, `--pr`, `--offline` are guessable; `--pr` is explained in `--help` and the last-line qualifier. Defaults: no flag runs the full check in the current repo. Consistency: `--repo DIR` matches entry.py lag; REFUSED/Fix wording matches the skills. Completeness: no drop to raw git for anything the check lists (Fix lines are commands). Discoverability: `--help`, the Command map row, Usage. Reliability and trust: bounded clone, no prompts, read-only, exit codes defined (0, 1, 2, 4). Progressive disclosure: simple case one command; classes and offline modes are flags. Persona fit: agent-friendly (non-interactive, stable codes, text only; JSON dropped by decision). Agent ergonomics observation (not scored): non-interactive yes, structured output text only, layered help one level. Good API test: an agent can use it correctly after one example, yes. Residual: engine in another skill (documented, fail soft). Decision gate: none new.

Pass 3 Error messages (before 4 capped by CAP4, after 9; the CAP4 items are closed). Evidence recall: stage 2 and 5 friction. ERROR PATH MATRIX (agent-ready-v1), channel is stderr and a distinct exit for failures, stdout for gap lines (a gap is a verdict, not a failure):
Path                          | Class      | what | fix  | recovery | code | context | trace | redaction | channel | Cap
usage error                   | usage      | pass | pass | N/A      | pass | N/A     | N/A   | pass      | pass (2)| none
workflow-health missing       | environment| pass | pass | pass     | pass | pass    | N/A   | pass      | pass (4)| none
MIG_WIKI_UNREADABLE           | dependency | pass | pass | pass     | pass | pass    | N/A   | pass(URL) | verdict (1)| none
unexpected exception          | unexpected | pass | pass | pass     | pass(MIG_INTERNAL) | pass | pass (file path) | pass | pass (4)| none
goal.py new major refusal     | validation | pass | pass | pass     | pass | pass    | N/A   | pass      | pass (2)| none
entry.py missing in goal.py   | environment| pass | pass | pass     | n/a (NOTE)| pass| N/A   | pass      | pass (stderr, never blocks)| none
queue goal.py queue failure   | partial    | pass | pass | pass     | pass | pass    | pass (tail)| pass | Issues line| none
wiki orphan Fix (owner step)  | partial-risk| pass| pass | pass (one retry, irreversible stated) | pass | pass | N/A | pass | verdict | none
The initial plan had CAP4 findings on two paths (exit-code ambiguity, unmapped exit 3) and CAP6 findings on recovery, code, context and trace; each is closed by a named line in plan 4b, with the corrected example: `REFUSED: workflow-health is not installed beside workflow-setup; nothing was changed. Fix: install the workflow-health skill from the same release (it ships in the package), then rerun` (stderr, exit 4). Permission and safety model: the check changes nothing; the only irreversible step (page removal) is owner only and says so. Verbose or debug mode: the trace file for unexpected failures; no --verbose flag (not needed, every gap states its values). Decision gate: no choice left; per-code anchors stay a recorded taste decision.

Pass 4 Documentation (before 7, after 8). Evidence recall: stage 3 friction. Information architecture: Setup.md Usage (command, flags, example, code table), the SKILL.md Command map row, START.md first five minutes (one line), Health.md Usage and notes (the rule), Tests.md (rows). Progressive disclosure: Usage gives the example first, then flags, then the table. Code examples: copy-paste complete, real output captured from the toy (not typed). Interactive elements: the toy. Versioning: docs ship with the code in the same PR, and docs.py check fails a page behind its code. Tutorials versus references: the Verify by hand steps are the tutorial, the code table the reference. Residual: no per-code anchors (recorded). Decision gate: none new.

Pass 5 Upgrade and migration path (before 8, after 9). Backward compatibility: nothing existing breaks; new TABLE row adds one setting with an empty default; `template_lag` keeps its return; no flag removed. Deprecation: none needed. Migration guide: the migrate goal is the guide and the codemod in one (`update --apply` plus blocks and entries). Versioning strategy: the template's release numbers; the refusal on differing major is the compatibility gate. Blast radius: one repo per migrate goal, behind a reviewed PR. Fear check: upgrading is boring (read-only check, additive writers, PR revert). Decision gate: none.

Pass 6 Developer environment (before 7, after 8). Editor integration: not applicable (terminal tool). CI/CD: works with no prompt and no network in `--offline` and in health; the toy needs neither. TypeScript: not applicable. Testing support: toys with fixtures, overrides named, `want PART` selector. Local development: no watch mode needed; a part runs in under 60 s. Cross-platform: macOS for MIG_TASK (explicit SKIP elsewhere); Windows deferred to the parallel goal. Reproducibility: temp HOME and bare repos make runs identical. Observability and testability: CHECKED line, mode, dry-run is the default (read-only), fixtures exist. Decision gate: none.

Pass 7 Community and ecosystem (before 5, after 5). Open source: the template is public in this ecosystem as the owner publishes it; no change. Channels: issues filed by health are the channel. Examples: runnable toy. Extension: the engine returns tuples other skills can reuse. Contributing: unchanged. Pricing: none. Score stays 5: an internal single-owner tool has no community to invest in, and inventing one would be scope creep. Decision gate: none.

Pass 8 DX measurement (before 5, after 7). Evidence recall: approved clock (agent persona, start = installed, result = gap list). TTHW tracking: Verify by hand records the wall seconds of one run on the toy; health files the signal recurringly. Journey analytics: none (no telemetry; an independent policy not added). Feedback mechanisms: issues. Friction audits: the 4-hourly health run is the periodic audit. Boomerang readiness: a later live DX review can compare the recorded seconds and the Usage example with real runs. Decision gate: no telemetry, no release gate, no recurring human process added.

Claude Code skill DX checklist (appendix, product type includes skill): AskUserQuestion design: not applicable (the command asks nothing). State storage: none written, per-run temp dir private. Progressive consent: none needed (read-only). Auto-upgrade: update --apply exists; this plan adds the nag. Skill composition: setup calls health by path with fail-soft refusal. Error recovery: partial results are never written, the gap list is whole or REFUSED. Agent-readable errors: contract above. Session continuity: the queued goal journal and issues carry state. Bounded autonomy: the operation session only queues, never edits another repo's code, and the guard limits the one write.

DX SCORECARD
| Dimension | Score | Prior pass-score | Trend |
| Getting Started | 9 | 6 | up |
| API/CLI/SDK | 8 | 7 | up |
| Error Messages | 9 | 4 | up |
| Documentation | 8 | 7 | up |
| Upgrade Path | 9 | 8 | up |
| Dev Environment | 8 | 7 | up |
| Community | 5 | 5 | flat |
| DX Measurement | 7 | 5 | up |
TTHW: none today to under 2 min target (Champion), estimated. Competitive rank: Champion by estimate, unmeasured. Magical moment: designed via the command's own output. Product type: CLI tool plus skill. Mode: DX POLISH. Overall DX 8.0 (initial 6.1). Principle coverage: Zero Friction covered; Learn by Doing covered; Fight Uncertainty covered (NOT CHECKED, CHECKED, exit 4); Opinionated plus Escape Hatches partial by decision (no override, no ignore list; explicit off settings); Code in Context covered; Magical Moments covered; Agents Are Users covered.

DX IMPLEMENTATION CHECKLIST
[ ] one wall-time measurement of a toy run is written into Verify by hand (target under 2 minutes)
[ ] installation: nothing beyond the package
[ ] first run prints gap lines or MIGRATION OK plus NOT CHECKED, CHECKED and DOCS lines
[ ] every Fix is one command line or one named owner-only step
[ ] exits: 0 ok, 1 gaps, 2 usage, 4 could not run; stderr for failures, stdout for gaps
[ ] `--repo`, `--pr`, `--offline` documented and in `--help`; LOOP_MIGRATION_ONLINE listed as supported
[ ] Setup.md shows a real gap run, a clean run, the code table with classes
[ ] upgrade path: migrate goal and update --apply, no breaking change
[ ] no prompt, bounded clone, progress line, mode shown
[ ] secret-in-URL negative test passes; hostile page name test passes

NOT in scope (DX): per-code doc anchors; per-code ignore list; override for the major refusal; --quiet; telemetry; Windows; alias names for flags; hosted dashboard. What already exists: argparse usage errors, REFUSED and Fix style, GIT_TERMINAL_PROMPT=0 in the docs scripts, the toy header format, the Command map. TODOS.md updates: none (no file; items listed here and in plan 6b).

Implementation tasks (DX): T1 (P1) defects.py and agents.py output contract (lines, exits 0, 1, 2, 4, trace file) Verify migration-flags; T2 (P1) goal.py exit mapping and NOTE Verify migration-major-refused; T3 (P2) Setup.md Usage example, table and supported settings Verify docs check; T4 (P2) Verify by hand steps with the timing Verify by hand run.

Decision audit trail (DX, second pass):
| 26 | DX | REFUSED and unexpected failures exit 4 | mechanical | P1 | a caller must tell no-verdict from gaps | exit 1 |
| 27 | DX | goal.py maps entry.py exit 3 to its refusal exit 2 | mechanical | P5 | explicit mapping | pass through |
| 28 | DX | CHECKED line, trace file, progress line | mechanical | P1 | context and trace items of the contract | omit |
| 29 | DX | per-code anchors deferred, table is the target | T | P3 | page template and file cap | per-code headings |
| 30 | DX | LOOP_MIGRATION_ONLINE is a supported switch | mechanical | P5 | explicit over hidden | test-only |

### Eng review in full (Phase 3, second pass)

Scope gate: the target is this plan (auto-selected). Review preparation: retrospective check on the paths the plan names (history only for existing paths): `git log --oneline -- skills/workflow-setup/scripts/sync.py` shows the recurring size-cap trims (skill-size, package-cap-3), reverts: none found for these paths; named future paths (the engine functions) have no history.

Scope Challenge A (assess):
- What already solves each sub-problem (cited): versions `entry.py:210-225`; stale blocks `render.py:401-406`; Runbook rule `deployments.py:86-108`; wiki url `docs.py:88-91`; wiki pages `defects.py:84-90` (`pages`), wiki folder `defects.py:75-81`, regression rows `defects.py:102-110` (`table`); registry `workflows.py:63,107,115`; filing `file.py:114-170`; dedupe `fit.py:207-224`; publish comparison `docs.py:293-330`; toy state hash `dev/toy/test-setup-adopt.sh:28-32`; controls auto-import `controls.py:215-219`; rule gather and ran-rules `health.py:257-285`.
- Minimum changes that achieve the goal: the check engine and its callers; everything else is either a done line (writers, resolver, nag, queue) or hardening. Deferrable without blocking: nothing among the done lines; the cut candidate if review pushes back is the queue (commit C).
- Complexity check (selected work counted once, estimates): about 25 changed paths (21 under skills/ plus the docs pages, one toy, rows, goal-file section) and 0 new classes or services (functions only). 8+ files, so Scope Challenge B applies.
- Search check: new patterns are a bounded subprocess clone with a process-group kill, a sanitizer allowlist and an exact-slug regex; research was unavailable (no network), so: "Search unavailable — proceeding with in-distribution knowledge only." [Layer 1] subprocess timeouts with `start_new_session` and `os.killpg` are the standard pattern; [Layer 1] `GIT_ALLOW_PROTOCOL` is git's documented control for transport restriction.
- TODOS cross-reference: no TODOS.md exists; nothing blocks, fits or needs a new TODO beyond plan 6b.
- Completeness check: full tests, edge cases and error paths are planned at toy level (13 parts); the CC cost of each is small against the human cost.
- Distribution check: no new artifact; ships in the skills package (96 files unchanged); the release carries it; `update --apply` moves repos; no CI change (the land lane runs the rows).
Reality rows:
REALITY: premise-table finding 9 premises, unverified=1 skills/workflow-docs/scripts/deployments.py:86
REALITY: already-done pass no commit on origin/main adds MIG_ codes or migration-check (git grep, local refs) skills/workflow-docs/scripts/entry.py:218
REALITY: surface-check finding `entry.py` has no lag choice yet, `regression.py red` needs --break, `docs.py publish` writes pages unchanged and the marker is its first-line check skills/workflow-docs/scripts/docs.py:313
REALITY: binding-decisions pass the goal header decisions are carried; no decision log entries for this branch skills/workflow-health/scripts/workflows.py:278
REALITY: numbers pass every byte figure re-measured with wc -c [measured: wc -c on this branch] skills/workflow-health/scripts/defects.py:1
REALITY: deferred-asks pass no linked issue; the goal header asks all map to done lines 1 to 11 .loop/goals/migration-check.md:1
REALITY: pr-count pass one pull request in ordered commits; the parallel goal is a separate pull request .loop/goals/migration-check.md:4

Scope Challenge B (complexity selectors): feature cuts proposed: none (each is required by a done line; the queue is the named cut if review pushes back, not cut now: auto-decided P2). Structure question (plan-eng-review-structure), auto-decided at the recommendation: Original arrangement (engine in defects.py with the wiki half in enforce.py, 13 other scripts edited, no new file) over a Smaller arrangement (fewer files): no smaller arrangement preserves the frozen done lines, the package cap and the per-script caps; both options keep the same feature list and contracts. Pending remedies not decided here: none. Scope record: feature answers: none cut; structure: original arrangement kept; accepted scope: the whole plan; pending remedies: none.
Scope Challenge C: findings: [INFO 9/10 skills/workflow-docs/scripts/docs.py:313] publish compares exactly, so stale must use the same exact comparison (applied); [INFO 9/10 skills/workflow-docs/scripts/docs.py:98] docs.clone exits the process, unbounded, so the engine owns a bounded clone (already planned); [INFO 8/10 skills/workflow-delivery/scripts/fit.py:213] cmd_queue has no lock, so the plan states the append semantics instead of inventing one (applied). Result: scope accepted as-is (MODE FULL_REVIEW).

Voices. Native eng voice: completed, 30 findings (4 High), INPUT hash matched its snapshot. Codex outside voice: unavailable (network skipped; missing coverage, never clean). Tag [subagent-only].
ENG DUAL VOICES - CONSENSUS TABLE:
  Dimension                           Claude  Codex  Consensus
  1. Architecture sound?               yes*    N/A    N/A (voice coverage missing; * commit order fixed)
  2. Test coverage sufficient?         gaps    N/A    N/A
  3. Perf risks + budget/bench named?  yes     N/A    N/A
  4. Security threats covered?         gaps    N/A    N/A (S1, S2, S3, S4, S5 closed)
  5. Error paths handled?              gaps    N/A    N/A
  6. Deployment risk manageable?       mostly  N/A    N/A

Disposition of the native findings (confidence in brackets, all applied to the plan text unless noted): S1 [CRITICAL 9/10] option injection in the printed git rm: ACCEPTED (`--`, reject leading dash or dot, fixed commit message, `--force.md` toy); S2 [CRITICAL 8/10] transport injection from an untrusted origin: ACCEPTED (`GIT_ALLOW_PROTOCOL`, `ext::` toy); S3 [INFO 8/10] timeout does not kill the tree: ACCEPTED (process group kill); S4 [INFO 7/10] redaction only for user:password: ACCEPTED (one function over every output string); S5 [INFO 7/10] unguarded platform override: ACCEPTED in the engine (LOOP_TEST gate); E1 [CRITICAL 8/10] stale false positives: resolved by reading publish, which writes pages unchanged (exact comparison; round-trip toy added); E2 [INFO 8/10] major ambiguity: ACCEPTED (version table in section 1); E3 [INFO 7/10] ahead of template silent: ACCEPTED (CHECKED line says so); E4 [INFO 7/10] two commands read different refs: ACCEPTED (CHECKED names the source); E5 [INFO 8/10] MIG_CHECKS vacuous in mac mode: ACCEPTED in part (the NOT CHECKED line now says no pull-request-time check exists in mac mode; no new gap code); E6 [INFO 8/10] re-running setup could undo a step: ACCEPTED (commit D precedes A); E7 [INFO 6/10] health_cron Fix text: ACCEPTED (Fix says turning it on also restores health checking); E8 [INFO 6/10] wiki-only Home: ACCEPTED (toy; `Home.md` exists in the repo, so it is a source page); A1 [INFO 7/10] layout driven by the cap: ACCEPTED as documented debt; A2 [INFO 7/10] slack: ACCEPTED in part (the two cheap trims move to commit 0; render.py keeps 350 bytes); A3 [CRITICAL 9/10] commits do not stand alone: ACCEPTED (order 0, D, B, A, C; cut C only); A4 [INFO 5/10] mode in the summary line: TASTE kept (row detail carries it); O1 [CRITICAL 7/10] concurrent queue writes: resolved by stating the existing append semantics (no lock exists; de-dup re-reads; duplicates are impossible, a discarded line requeues); O2 [INFO 8/10] offline filing closes issues: ACCEPTED as a documented rule (file through the tick or with the online switch); O3 [INFO 6/10] one issue per orphan: ACCEPTED (grouped health rows); O4 [INFO 6/10] clone time: stated (inside the existing caps); O5 [INFO 5/10] stale origin ref: stated (tick fetches); O6 [INFO 7/10] regex escaping: ACCEPTED; tests: all gaps added (worktree, round trip, injection cases, base resolver parity, real resolver for MIG_VERSION, queue table rows, concurrency, cost). Hidden complexity: kept as one PR with the C cut stated; the --pr deviation stays explicit.

Section 1 Architecture review. Components and boundaries: see the system diagram below; boundaries follow ownership (version knowledge in entry.py, block rendering in render.py, filing in file.py, the engine in the health module). Coupling: setup to health via path-load and exit-4 refusal (new, justified by done line 1 needing one command and done line 2 one engine); operation session to setup and goal.py via subprocess (existing pattern). Data flow: four paths covered in CEO Section 1. Bottlenecks and scaling: per followed repo per pass, a few file reads; per tick one clone; at 10x repos the pass is linear and the clone dominates (30 s cap per repo inside per-repo and total tick caps); nothing is O(n squared). Single points of failure: the registry file, the wiki remote, workflow-health installed. Security: threat table in CEO Section 3 plus S1 to S5 here. One realistic failure per new path: wiki hang (killed with its process group), hostile name (never in a command), dirty followed repo (guard), missing entry.py (note), missing health (exit 4). Distribution architecture: no new artifact.
  Design-twice: no new module, service or public boundary is introduced (the engine is functions in two existing files behind one in-process function), so no second shape is required; recorded in one line.
  Eight red flags screened: 1 shallow module no (one function, wide behaviour behind a small interface); 2 information leakage no (the task-name format and 4-hour rule live once; the version table once); 3 temporal decomposition no (split by knowledge: version, files, settings, blocks, automation, task, checks, wiki); 4 pass-through method none; 5 split ownership: MIG_VERSION is reported once by the template-version row, and the queue and the CLI both call `behind` and the engine rather than keeping copies; 6 two ways to do one task: `template_lag` strings and `behind` tuples, one derives from the other; 7 importable internals: the engine is private to defects.py except `migration_gaps` (supported); 8 hand-synced list: the `report.py` Adoption tuple, `FUNCTIONS` and `CONTROLS` are three lists that must agree, and `controls.py` already fails the build when a rule has no control (`controls.py:295-302`), which is the derived check.
  Architecture diagram:
  setup.py migration-check --repo --pr --offline
        |-> agents.migration_check --path-load--> workflow-health/defects.py:main (exit 4 REFUSED if absent)
        |        |-> engine: version files settings blocks automation task checks (reads files and git only)
        |        |-> enforce.py (lazy): bounded wiki clone, orphan, stale, docs.py check parse
        |        '-> output: GAP lines, NOT CHECKED, CHECKED, DOCS, last line (exit 0, 1, 2, 4)
  health.py check (Adoption) -> defects.migration rule (offline; the tick sets LOOP_MIGRATION_ONLINE=1)
        '-> rules.template_version row (MIG_VERSION) -> health file (tick) -> issues (grouped wiki rows)
  operate.py pass -> board_page.queue_migrations -> behind() -> goal.py queue (cwd = followed repo; base branch, clean queue file)
  goal.py new -> entry.py lag --new -> warn | refusal exit 2 (from entry's 3) | migrate- slug passes | NOTE if entry.py missing
  update.py --check / sync.base_config -> agents resolver (origin/<b> first)
  update --apply -> agents.apply -> render.py blocks; settings.fill_automation (adds, never overwrites)
  seed.py (keeps recorded mac) / workflows.py (no DRIFT for mac; tick online switch; task-name constant)
Findings in this section: 4 (A3, A1, A2, O1 resolved above). Dispositions: all accepted or stated.

Section 2 Code quality review. Organization: fits the existing pattern (rule functions returning row dicts in defects.py, helpers beside the code that owns the knowledge). Shared-code rubric: callers proven: (1) `defects.pages` is called by `defined`, `refs`, `usage_readme` (`defects.py:93-99,134-156`) and now by the stale and orphan checks: three verified callers; reuse, no extraction. (2) `defects.table` is called by `row_requirement` (`defects.py:121`) and `guarded` reads the same file by its own parse (`defects.py:49-51`): two readers of regression.tsv exist today; the plan reuses `table` and does not add a third; consolidating `guarded` into `table` would save about 6 lines (implementation estimate 6 removed, 2 added, 4 net saved) but touches a rule outside this goal: not taken, recorded as an option. (3) `entry.version_key` is called by `lagging` (`entry.py:224`) and by `board_page.template_lag`; the plan routes the engine and `behind` through it. Existing helpers inspected first; no new helper is extracted. Error handling gaps: none left (Section 2 of the CEO pass). Technical debt and fragility: the three-list agreement (flag 8) is guarded by an existing control; the byte-packed scripts are the debt, named. Diagram accuracy: the Health page's rule list diagram, if any, is regenerated; no ASCII diagram in a touched file becomes false (the usage text of entry.py is updated with `lag`). Findings: 2 (the truth table as data; the optional `guarded` consolidation).

Section 3 Test review (Step 1, trace). Concrete source and tests read in dedicated calls: defects.py lines 40-160 with test-health-hygiene.sh lines 1-45, and entry.py lines 282-330 with test-setup-adopt.sh lines 1-40 (the toy house patterns: `# reads:` headers, `want PART`, `ok`/`bad`, the `state()` hash). Execution traced from each entry point:
  setup.py migration-check -> argparse -> repo root -> agents.migration_check -> path-load defects -> engine -> output; branches: no workflow-health (exit 4), bad flag (exit 2), --pr, --offline, repo with/without docs.tsv, mac/actions/off, Darwin/other, wiki online/offline/not-found/timeout/auth, orphan/stale/empty.
  health check -> rules -> migration rule -> engine (offline) -> row mapping (group wiki rows) ; tick -> online env.
  entry.py lag -> config read -> installed() -> version table -> line / none; --new -> exit 3 vs migrate- slug.
  goal.py new -> subprocess entry.py lag --new -> map 3 to refusal exit 2 | NOTE.
  operate pass -> queue_migrations -> behind() -> state table -> goal.py queue.
Step 2 (flows and error states): the user flows are the migration (gap list, migrate goal, merge, full check, Mac steps), session start (nag), health filing; interaction edge cases: double run, run from a worktree, offline, no wiki, slow clone, empty repo, second pass of the queue, concurrent passes. Error states the user sees: named gaps, NOTE lines, REFUSED with fixes, exit 4 with a trace path.
Step 3 (branches against existing tests): existing coverage found: `test-setup-adopt.sh` (setup flows, no migration branches), `test-sync-update.sh` (update --check text), `test-health-hygiene.sh` (controls fire for every rule: the new rule's control is required by it at line 29, count `>= 34`), `test-local-schedule.sh` (tick and registry), `test-goal.sh` (goal new). None covers a migration branch (new code), so every branch is a requirement; the existing toys are extended only where they assert counts (the controls count rises by one; the Health page and Usage matches are checked by docs check).
Step 4, coverage diagram (24 requirements; QUALITY target all three-star):
  CODE PATHS                                              USER FLOWS
  [+] defects.py engine                                   [+] adopted repo behind
    |-- version table (8 cases)    [GAP ***] lag-line       |-- [GAP ***] clean / gaps-pr / gaps-state
    |-- files, settings, blocks    [GAP ***] gaps-pr         |-- [GAP ***] migrate goal then --pr passes pre-merge
    |-- automation + task (6 rows) [GAP ***] gaps-pr/state   '-- [GAP **]  full check after merge on the Mac
    |-- checks (mac/actions/off)   [GAP ***] gaps-pr       [+] session start
    '-- main flags, exits 0/1/2/4  [GAP ***] flags          |-- [GAP ***] lag line (real resolver and override)
  [+] enforce.py wiki + parse                               '-- [GAP ***] goal.py new refusal, NOTE, migrate- exempt
    |-- clone ok/not-found/timeout/auth/ext:: [GAP ***] gaps-state/flags  [+] operation pass
    |-- orphan, stale (round trip) [GAP ***] gaps-state       |-- [GAP ***] queue table (5 rows), concurrency, prefix names
    '-- hostile and leading-dash names [GAP ***] gaps-state  '-- [GAP ***] health issue filing (preview WOULD open)
  [+] agents resolver / migration_check / apply [GAP ***] base-config, blocks-inserted, flags (exit 4)
  [+] settings.fill_automation, TABLE row       [GAP ***] blocks-inserted (never overwrites a set entry)
  [+] seed.py / workflows.py public-on-Mac      [GAP ***] mac-kept (also asserts origin/<base> only)
  [+] entry.py lag / goal.py / rules.py / report.py [GAP ***] lag-line, major-refused, health-same
  [+] writes nothing, robustness (worktree, malformed inputs, concurrency) [GAP ***] writes-nothing, robustness
  COVERAGE: 0 of 24 tested today (all new); plan requires 13 toy parts covering 24 of 24 | E2E marks: the migrate goal path is [->E2E] (toy runs update --apply then --pr); no [->EVAL] (no prompt or LLM file is touched, CLAUDE.md names no prompt patterns for this change)
Regression rule (iron): behavior at risk without coverage today: setup's `regression_runs` recording for public repos (callers: seed.py:156-158, lanes_cli.py:198), update --check's base reading (update.py:366), health's rule set and control count (test-health-hygiene.sh:29), goal.py new; each has a dedicated approved row (mac-kept, base-config, health-same, major-refused). Intended differences: a recorded mac now survives for a public repo; unknown base resolution now tries origin first.
Test value bar and value cards: each proposed part has the four answers (observable behavior; the credible regression; why existing coverage misses it; no production seam); cards are in the test plan artifact. Tests made obsolete: none; extended existing toy assertions: the controls count in test-health-hygiene.sh (rises by one) and any Usage-line match in the docs toys.
Step 5: all test requirements are carried from approved contracts; no optional depth is pending. Test plan artifact: rewritten to the review state folder for this repo (outside the repo, not committed) with all 13 parts, value cards and no pending decisions. Findings: 6 test gaps found by the native voice, all added (worktree, round trip, injection, base parity, real resolver, queue rows); 0 pending.

Section 4 Performance review. Per-request or looped paths: the operation pass loops over followed repos (a handful; each does 2 to 4 small file reads and one `git show`); no query loops, no unbounded cache; no whole-file loads beyond config and regression.tsv (small); blocking calls all have timeouts (clone 30 s; subprocess `docs.py check` 60 s cap stated for the engine; `goal.py queue` 30 s). Scale (marked): followed repos about 5 to 20 [estimated], wiki pages about 10 to 40 [measured: docs/wiki holds 10 pages], tsv rows about 630 [measured: .loop/regression.tsv]. Slow paths ranked: clone (about 1 to 3 s online [estimated]), `docs.py check` (about 1 to 5 s [estimated, re-measure before the gate]), the toy suite (13 parts under 60 s each, total target under 8 minutes with one shared fixture build [estimated; the measured total is recorded in Verify by hand]). A hot path with no budget would be a finding: the health Adoption group budget (under 20 s on a toy) is asserted. Findings: 1 (the land-lane cost of 13 parts; mitigation: one shared fixture build per script run, rows run one part each).

Outside voice: Codex unavailable (network skipped); native review completed above (30 findings, dispositions listed); cross-model comparison skipped (no completed external review).

Failure modes registry (eng, second pass):
  CODEPATH               | FAILURE MODE                         | RESCUED | TEST            | USER SEES          | LOGGED
  wiki clone             | hang, leftover git children          | Y       | flags           | named gap          | issue
  wiki clone             | ext:: or file: origin                | Y       | gaps-state      | named gap          | issue
  printed Fix            | hostile or leading-dash page name    | Y       | gaps-state      | sanitized, manual  | n/a
  stale detection        | false stale after publish            | Y       | gaps-state      | zero stale         | n/a
  queue                  | dirty or off-base repo               | Y       | queue           | Issues line        | Issues
  queue                  | concurrent passes                    | Y       | queue           | one line           | queue.md
  queue                  | name prefix collision, dots in names | Y       | queue           | all queued         | queue.md
  health                 | manual offline file closes wiki issue| Y (documented) | health-same | documented rule  | issues
  setup re-run           | flips recorded mac (public)          | Y       | mac-kept        | no DRIFT           | digest
  commits                | a commit fails its own toy           | Y       | per-commit run  | build fails        | n/a
  size                   | script over the cap on a merge       | Y       | package, gate   | build fails        | n/a
  critical gaps: 0.

Worktree parallelization: one primary module family (workflow-setup and workflow-health), shared scripts; steps 2 to 8 touch overlapping scripts (agents.py, settings.py, entry.py): Sequential implementation, no parallelization opportunity for code. One independent lane exists for docs and the Verify-by-hand text after the code commits (Lane A: steps 2 to 8 sequential; Lane B: step 9 docs after step 8). Launch A; merge; then B.

Implementation Tasks (eng, second pass; human and CC effort, task-type ratios as the skill defaults):
- [ ] T1 (P1, human ~4h / CC ~20min) workflows.py, goal.py, settings.py: commit 0 constants and trims. Surfaced by: A2, plan 3. Files: skills/workflow-health/scripts/workflows.py, skills/workflow-delivery/scripts/goal.py, skills/workflow-setup/scripts/settings.py. Verify: wc -c under the plan limit; test-local-schedule.sh still green
- [ ] T2 (P1, human ~4h / CC ~20min) seed.py, workflows.py: commit D public-on-Mac. Surfaced by: plan 4 (f), E6. Verify: migration-mac-kept
- [ ] T3 (P1, human ~1d / CC ~40min) agents.py, sync.py, settings.py, render.py: commit B resolver, blocks, automation entries. Verify: migration-base-config, migration-blocks-inserted
- [ ] T4 (P1, human ~2d / CC ~60min) enforce.py, defects.py, agents.py, setup.py, rules.py, report.py, entry.py, goal.py: commit A the check, health rule, lag and refusal. Surfaced by: S1 to S5, E1 to E8, A1. Verify: clean, gaps-pr, gaps-state, flags, robustness, writes-nothing, health-same, lag-line, major-refused
- [ ] T5 (P1, human ~1d / CC ~30min) board_page.py, operate.py: commit C queue. Surfaced by: O1, O3, O6. Verify: migration-queue
- [ ] T6 (P2, human ~1d / CC ~30min) docs, SKILL.md rows, generated files, Verify-by-hand section, rows with seen_red, Tests.md. Verify: docs check, package check, regression.py red per row
Assumption: ratios as the skill's defaults; CC times are for the implementation, not the review.

Completion summary (Eng, second pass): Step 0 Scope Challenge: scope accepted as-is; Reality rows 7 of 7, 1 unverified premise; Architecture Review: 4 issues found; Code Quality Review: 2 issues found; Test Review: diagram produced, 24 requirements, 6 gaps identified and added; Performance Review: 1 issue found; NOT in scope: written (plan 6b and the CEO and DX lists); What already exists: written (Step 0 A and Section 2 callers); TODOS.md updates: 0 items proposed (no file; deferrals in plan 6b); Failure modes: 0 critical gaps flagged; Unresolved decisions: 0 in this review; Outside voice: codex unavailable, native completed; Parallelization: 1 lane code, 1 lane docs, sequential code; Lake Score: N/A (no scored 10/10 questions asked).

Decision audit trail (eng, second pass):
| 31 | Eng | stale uses publish's exact comparison; round-trip toy | mechanical | P1 | no false stale | whitespace-stripped compare |
| 32 | Eng | commit order 0, D, B, A, C; cut C only | mechanical | P5 | each commit passes its own toys | A before B |
| 33 | Eng | clone hardening: protocol allowlist, process-group kill | mechanical | P1 | untrusted origin | plain run with timeout |
| 34 | Eng | git rm after --, reject dash and dot names, fixed message | mechanical | P1 | option injection | shlex.quote only |
| 35 | Eng | no queue lock, state the append semantics | mechanical | P4 | fit.cmd_queue has none; do not invent | new lock |
| 36 | Eng | grouped wiki rows in health | mechanical | P3 | one issue not many | row per page |
| 37 | Eng | version table: absent or unparseable never refused | T | P5 | done line 5 says major; unknown is not a differing major | refuse unknown |
| 38 | Eng | guarded() consolidation not taken | T | P3 | outside this goal | consolidate |

