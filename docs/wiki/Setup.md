<!-- workflow-docs -->
# Setup

Milestone: https://github.com/jcl2018/agent-workflow-template/milestone/9

Review: **Reviewed 2026-11-13** <!-- prd P=7f1b1066 R=003227cb N=9c385754 M=471a58c6 U=c8d71f6f -->

## Problem
- I want this toolset to be a workspace I can drop into any repo, for any agent: one install gives Claude Code, Codex or any agent that reads skills the same loop, docs, monitoring and settings, in the right format for each.
- Adopting a repo should never block: it should look at what is there, borrow what fits, learn from a repo I've already set up, and list what doesn't fit instead of refusing.
- Any new session should see the design logic, the docs and every command at once, and an improvement in one repo, or in the template, should reach the others.

## Requirements

### Functional
- SET-1: **Reviewed 2026-11-13** One command adopts a repo <!-- reviewed 8cd2a972 -->
  - One command sets up a new or existing repo: the loop config, PRD feature pages in the docs format, the Home table and README How to use, the nightly regression in GitHub Actions, the health groups, and every setting with its default.
  - It shows what it found and would change first, then applies it on a branch through the loop, adapting what is there instead of overwriting.
  - It never blocks: what doesn't fit is listed and filed as issues tagged with the right feature, and the rest is adopted.
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
- SET-11: **Reviewed 2026-11-13** Prerequisites first, then a strict replay of the first adoption <!-- reviewed 3d61b462 -->
  - Before it writes anything, setup prints one checklist of what this machine needs: git, python3, gh installed and signed in as me, real symlinks, and a supported platform (no crash on a missing POSIX call, and the qa lane runs on this platform instead of hanging). Each line that fails carries its exact fix, for example the install command, or `gh auth login` run with a device code I can enter from my phone instead of a prompt waiting at the PC.
  - Adoption then replays the first run step by step against its golden result (`dev/toy/adoption-golden.tsv`, eight steps from prerequisites to the first check-in). It stops at the first mismatch, says what differs and asks me to do the exact step that fixes it; it never accepts a looser equivalent.
  - Comes from [#1408](https://github.com/jcl2018/agent-workflow-template/issues/1408), with the Windows crashes in [#1395](https://github.com/jcl2018/agent-workflow-template/issues/1395), [#1396](https://github.com/jcl2018/agent-workflow-template/issues/1396) and [#1397](https://github.com/jcl2018/agent-workflow-template/issues/1397).
- SET-12: **Reviewed 2026-11-13** Adopt all my repos in one pass <!-- reviewed e8a784e2 -->
  - From the operation session, one flow lists my GitHub repos by last push, private ones included, lets me choose which to follow, clones them into one folder, registers each with the board and updates each to the current template version.
  - It ends with the board showing exactly the repos I chose and none of them on an unknown or older template version.
  - Comes from [#1409](https://github.com/jcl2018/agent-workflow-template/issues/1409).
- SET-13: **Reviewed 2026-11-13** Workers are app sessions I can see <!-- reviewed ea44c41d -->
  - When I've chosen app sessions, a goal never falls back to a background worker: it waits for a free session and says so, including when the app refuses to start one because my message came over Remote Control.
  - The pool is kept at `pool_size` sessions (MON-12): it asks me to fill it only when it runs low, and never starts more than that.
  - Worker and pool sessions start on the model one setting names, and the operation session sets it on every session it starts or reuses.
  - The reply and govern hooks are installed exactly once each, however many times setup or either hook command runs.
  - Comes from [#1404](https://github.com/jcl2018/agent-workflow-template/issues/1404).
- SET-14: **Reviewed 2026-11-13** The connectors each repo needs are checked <!-- reviewed c52f6df9 -->
  - For each followed repo, setup reads which connectors its PRDs need (mail accounts, a calendar, a file store, a notification channel) and probes each with a read-only call.
  - It prints each as connected, needs sign-in or missing, with the fix, and names the owner-written files a repo needs that don't exist yet. It never attaches or enables a connector itself: I do, with the narrowest access.
  - Comes from [#1410](https://github.com/jcl2018/agent-workflow-template/issues/1410).
- SET-16: **Reviewed 2026-11-13** A repo is judged fully migrated by one command <!-- reviewed 66eb89ce -->
  - One read-only command lists every gap between a repo and the current template, each with a one-line fix, and exits 0 only when none remain; it writes nothing, and health's Adoption group runs the same check.
  - A repo carries `template_version` (set by update) and one with none counts as behind; a session that starts in a repo behind the installed template is told so in one line and never blocked, except that a new goal is refused when the major version differs.

### Non-functional
- SET-3: **Reviewed 2026-11-13** Shipped as a versioned package. <!-- reviewed 4ddb26bd -->
  - The template ships as one versioned package of separate skills in the Agensi format, every script self-contained and under 20 KB. It works out of the box with a built-in default flow, and is proven to run in both Claude Code and Codex on a clean test repo with no private settings.
- SET-7: **Reviewed 2026-11-10** Safe and repeatable <!-- reviewed fb39932b -->
  - A dry run lists everything before any write; running setup twice changes nothing the second time; nothing existing is overwritten.
- SET-8: **Reviewed 2026-11-10** Private stays private <!-- reviewed 22a16ae7 -->
  - Local settings and private values are never written into the repo, and setup refuses to commit a file that holds one.
- SET-15: **Reviewed 2026-11-13** One private-name list that fits every repo <!-- reviewed 3f8e2427 -->
  - When setup seeds the private-name list, it explains that the list covers every repo on this machine, so a private repo's own name, or a contact it cites on purpose, would block that repo's own commits.
  - A pattern can be scoped, for example to public repos only or to named repos, so a private repo can hold what a public one must never show.
  - Comes from [#1411](https://github.com/jcl2018/agent-workflow-template/issues/1411).
- SET-17: **Reviewed 2026-11-13** The Backlog milestones exist after adoption <!-- reviewed e4d6023c -->
  - Adoption creates one milestone "Backlog: <Feature>" for each feature page and "Backlog: Other", and creates none that already exists. Health's Adoption group warns for each one that is missing.

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
| [adopt-set-1](Tests#t-adopt-set-1) | requirement | SET-1 | Given SET-1, when the toy adopt-and-update test runs, then it holds. | FAIL 2026-11-12 |
| [adopt-set-2](Tests#t-adopt-set-2) | requirement | SET-1 | Given SET-1 with suggest then apply, when the toy adopt-and-update test runs, then it holds. | FAIL 2026-11-12 |
| [setup-both-halves](Tests#t-setup-both-halves) | requirement | SET-1 | Given a repo, when setup runs, then it writes the repo half and, outside the repo, the private half. | PASS 2026-11-12 |
| [set1-health-bracket](Tests#t-set1-health-bracket) | requirement | SET-1 | Given an adoption, when setup runs, then HEALTH START comes before the first write line, ADOPTION VERDICT is the last line, and a verdict that is not green lists each gap with its fix. | not run |
| [set1-never-blocks](Tests#t-set1-never-blocks) | requirement | SET-1 | Given a bare agent_command and an ignored *.tsv, when setup runs, then it adopts and commits with exit 0, names each gap, writes the exception line, and a failed step after the commit is a note and a gap. | not run |
| [set1-no-fit-filed](Tests#t-set1-no-fit-filed) | requirement | SET-1 | Given two pages with their own sections, when setup runs, then one findings line lists both and one issue tagged adoption is filed through the stand-in, matching preview, and a second run files none. | not run |
| [set1-docs-format](Tests#t-set1-docs-format) | requirement | SET-1 | Given a fresh adoption, when the docs check runs, then no Home, front door, requirement or problem format gap and no broken link remains, only pages still to be written. | not run |
| [settings-reference](Tests#t-settings-reference) | requirement | SET-2 | Given every repo and private setting, when the reference is read, then each is listed with its default and a one-line explanation. | PASS 2026-11-12 |
| [parallel-unlimited](Tests#t-parallel-unlimited) | requirement | SET-2 | Given parallel is 0, when goals run, then it means unlimited, and it is the default. | PASS 2026-11-12 |
| [settings-read-fresh](Tests#t-settings-read-fresh) | requirement | SET-2 | Given a changed setting, when the next run happens, then it takes effect. | PASS 2026-11-12 |
| [criteria-max-setting](Tests#t-criteria-max-setting) | requirement | SET-2 | Given the repo settings, when they are read, then criteria_max is a repo setting with default 10 and a one-line explanation. | PASS 2026-11-12 |
| [depth-setup](Tests#t-depth-setup) | requirement | SET-2 | Given a new repo, when setup runs, then it writes review_depth full with a one-line explanation. | PASS 2026-11-10 |
| [depth-reference](Tests#t-depth-reference) | requirement | SET-2 | Given the settings reference, when it is generated, then it lists review_depth with its default. | PASS 2026-11-10 |
| [depth-fill-repo-help](Tests#t-depth-fill-repo-help) | requirement | SET-2 | Given a config that already has its _help explanations, when fill-repo runs, then it fills without error. | PASS 2026-11-10 |
| [set2-layers-show](Tests#t-set2-layers-show) | requirement | SET-2 | Given a default, a repo and a local setting, when settings show runs, then each value shows the layer it came from, a local key in the committed config is flagged, and private values are withheld. | not run |
| [adopt-set-4](Tests#t-adopt-set-4) | requirement | SET-4 | Given SET-4, when the toy adopt-and-update test runs, then check shows the change, apply keeps the repo's data and lands the repo half on its branch. | FAIL 2026-11-12 |
| [sync-check-preview](Tests#t-sync-check-preview) | requirement | SET-4 | Given a newer template release, when update --check runs, then it shows the installed and available versions, the repo's version, what is new and each changed file, writes nothing, and never offers a downgrade. | not run |
| [sync-apply-keeps](Tests#t-sync-apply-keeps) | requirement | SET-4 | Given an adopted repo, when update applies a newer version, then the skills update, the repo half lands on workflow-update-vX with template_version stamped, and config values, pages and private settings are kept. | not run |
| [sync-default-source](Tests#t-sync-default-source) | requirement | SET-4 | Given an update from the template's release source archive, when the next default check runs, then it still finds the template through the installed stamp. | not run |
| [sync-template-redirect](Tests#t-sync-template-redirect) | requirement | SET-4 | Given a committed template_repo that differs from the installed stamp's repo, when update runs, then it refuses rather than read another repo's releases. | not run |
| [sync-propose](Tests#t-sync-propose) | requirement | SET-4 | Given a skill file fixed in an adopted repo, when update runs, then it shows as a local fix, is kept, and --propose --file-issue files one issue on the template with its diff and no repo name. | not run |
| [sync-board-lag](Tests#t-sync-board-lag) | requirement | SET-4 | Given a governed repo on an older template version, when the live board renders, then it lists that repo under Issues with the fix. | not run |
| - | requirement | SET-4 | no passing test | not enforced |
| [adopt-set-5](Tests#t-adopt-set-5) | requirement | SET-5 | Given SET-5, when the toy adopt test runs, then the design guide is installed and setup's .loop/START.md holds the opener and every part. | FAIL 2026-11-12 |
| [entry-stale](Tests#t-entry-stale) | requirement | SET-5 | Given an adopted repo, when a PRD page's Problem changes, then the entry point check and the docs check fail STALE until docs.py audit regenerates it. | PASS 2026-11-12 |
| [entry-adopt](Tests#t-entry-adopt) | requirement | SET-5 | Given a repo, when setup adopts it, then .loop/START.md holds the first-five-minutes list and every part: loop, release, operation and workers, docs, regression, health, settings and features. | not run |
| [adopt-fixture-existing-checks](Tests#t-adopt-fixture-existing-checks) | requirement | SET-6 | Given a repo whose config lists its own checks (pull request 83), when setup adopts it, then the written config keeps every check and the seeded row runs all of them. | not run |
| [adopt-fixture-ci-gitignore](Tests#t-adopt-fixture-ci-gitignore) | requirement | SET-6 | Given CI tests and a .gitignore blocking *.tsv, when setup adopts the repo, then the exception lines are written, the loop files are committed and the check comes from CI. | not run |
| [adopt-fixture-bare-agent](Tests#t-adopt-fixture-bare-agent) | requirement | SET-6 | Given a bare agent_command and no CI, when setup adopts the repo, then it adopts with exit 0, names the gap with its fix and leaves the agent command alone. | not run |
| [adopt-fixture-feature-milestones](Tests#t-adopt-fixture-feature-milestones) | requirement | SET-6 | Given features that are roadmap milestones and not folders, when setup adopts the repo, then they become pages and no milestone is made or read. | not run |
| [setup-fit](Tests#t-setup-fit) | requirement | SET-6 | Given a repo with CI tests, a bare agent command, its own feature list and a blocking .gitignore, when setup adopts it, then it adopts with gaps, and an older setup.py beside the new modules still works. | not run |
| [matrix-health-rule](Tests#t-matrix-health-rule) | requirement | SET-6 | Given a record of smoke runs, when health checks, then a cell with no pass in 7 days reads not proven (WARN) and a V1-required cell with none is a FAIL. | PASS 2026-11-13 |
| [matrix-smoke-record](Tests#t-matrix-smoke-record) | requirement | SET-6 | Given a smoke run, when it ends, then it appends a dated line with agent, OS, machine, commit and result that health reads as proof of that cell. | PASS 2026-11-13 |
| [matrix-never-run-warns](Tests#t-matrix-never-run-warns) | requirement | SET-6 | Given a cell of the agent-by-machine matrix that has never run, when health checks, then it reads WARN pending: no run recorded and never FAIL; only a cell that ran and failed, or whose last run is too old, fails. | not run |
| [set9-from-borrows](Tests#t-set9-from-borrows) | requirement | SET-9 | Given an adopted repo as the model, when setup runs with --from, then it borrows the portable settings and page shape, holds auto_merge and reply_hook until --allow, keeps its own base and agent command, changes nothing on a second run and never writes to the model. | not run |
| [set9-from-no-values](Tests#t-set9-from-no-values) | requirement | SET-9 | Given a model value holding a home path or an email, when setup runs with --from, then the value is skipped and appears in no output and no written file. | not run |
| - | requirement | SET-9 | no passing test | not enforced |
| [agents-wire](Tests#t-agents-wire) | requirement | SET-10 | Given a repo, when setup or agents.py wire runs, then CLAUDE.md and AGENTS.md hold the same workflow-loop block, text outside it is kept, and a second run changes nothing. | PASS 2026-11-12 |
| [adoption-golden](Tests#t-adoption-golden) | requirement | SET-11 | Given the golden first adoption, when its fixture and SET-11 are read, then the fixture holds steps 1 to 8 in order, each with a check, golden result and fix, no machine path or account, and SET-11 names it and its first-mismatch stop. | PASS 2026-11-13 |
| - | requirement | SET-12 | no passing test | not enforced |
| - | requirement | SET-13 | no passing test | not enforced |
| - | requirement | SET-14 | no passing test | not enforced |
| [migration-clean](Tests#t-migration-clean) | requirement | SET-16 | Given a clean private repo and a clean public repo, both recorded mac with the task registered, when migration-check runs, then each prints MIGRATION OK and exits 0. | not run |
| [migration-gaps-pr](Tests#t-migration-gaps-pr) | requirement | SET-16 | Given a clean toy repo, when each kind of pull-request-closable gap is made (version, settings, entries, stale START.md, bookkeeping files, workflow files, land row, blocks, Runbook, stale page), then migration-check names it by code with a Fix line, and with regression off it names no regression gap. | not run |
| [migration-gaps-state](Tests#t-migration-gaps-state) | requirement | SET-16 | Given a clean toy repo with a bare wiki, when the task is misnamed, 6-hourly or missing, or the wiki holds an orphan, a stale page, hostile page names, no wiki, an unreadable origin or an ext:: origin, then migration-check names each state gap by code, never deletes, runs no command from a page name, and a repo with no docs.tsv gets no wiki gap. | not run |
| [migration-flags](Tests#t-migration-flags) | requirement | SET-16 | Given a repo whose only gaps are state gaps, when migration-check runs with --pr, --offline, --repo, an unknown flag, no workflow-health, an injected exception, a credential in the origin URL or a clone that hangs, then each exits as specified (0, 1, 2 or 4), the last line says what was skipped, no credential is printed and the hang ends at 30 seconds. | not run |
| [migration-writes-nothing](Tests#t-migration-writes-nothing) | requirement | SET-16 | Given a repo with gaps and a published orphan page, when migration-check runs in full, with --pr and with --offline, then the tree, index, branches, stash, git files, home folder and temp folder are identical before and after. | not run |
| [migration-health-same](Tests#t-migration-health-same) | requirement | SET-16 | Given a repo with no template_version and an unknown setting, when health check runs the Adoption group, then it prints the same gap codes through the migration rule and the template-version row, stays green, previews WOULD open for both, and the migration rule's negative control fires. | not run |
| [migration-base-config](Tests#t-migration-base-config) | requirement | SET-16 | Given an adopted repo, when update --check runs from a branch cut before setup, with no local main, from a fresh clone, with a default branch that is neither main nor master, or with a stale local main, then it reports the base branch's config and never says it has none. | not run |
| [migration-robustness](Tests#t-migration-robustness) | requirement | SET-16 | Given a linked worktree, a subdirectory, a missing or malformed config, a corrupt regression.tsv, an unparseable docs.tsv, an unprintable wiki page name and two runs at once, when migration-check runs, then each ends with a verdict line and no traceback, and no temp folder is left. | not run |
| [migration-lag-line](Tests#t-migration-lag-line) | requirement | SET-16 | Given a repo behind the installed template, when entry.py lag runs through a fake install folder and through the test override, then it prints the exact version line, nothing for a current or newer repo or a tree that holds the skills, and a differing major refuses a new goal unless its slug starts with migrate-. | not run |
| [migration-major-refused](Tests#t-migration-major-refused) | requirement | SET-16 | Given a repo behind the installed template, when goal.py new starts a goal, then it warns and goes on, refuses a differing major with exit 2 and no goal state, lets a migrate- slug through, and only notes a missing entry.py. | not run |
| [migration-blocks-inserted](Tests#t-migration-blocks-inserted) | requirement | SET-16 | Given a repo adopted before the Settings and Automation blocks existed, when update --apply runs, then its README and Home hold both blocks and the README line, its config holds template_version and the three routines, and the repo is no longer behind. | not run |
| [migration-queue](Tests#t-migration-queue) | requirement | SET-16 | Given followed repos app, app.v2 and app-api all behind the template, when the operation session's pass runs, then each gets exactly one migrate-<repo> goal line, a second or concurrent pass adds none, a finished goal for this version is an Issues line, an older one allows a version-suffixed slug, and a repo on another branch or with a modified queue file is skipped with its reason. | not run |
| [migration-mac-kept](Tests#t-migration-mac-kept) | requirement | SET-16 | Given a public repo recorded regression_runs mac, when setup re-runs and the tick runs, then mac is kept, no DRIFT line prints and only origin/<base> is fetched. | not run |
| - | requirement | SET-16 | no passing test | not enforced |
| [adopt-set-3](Tests#t-adopt-set-3) | requirement | SET-3 | Given SET-3, when the toy adopt-and-update test runs, then it holds. | FAIL 2026-11-12 |
| [skill-kept](Tests#t-skill-kept) | requirement | SET-3 | Given detail moved out of the workflow-delivery and workflow-docs SKILL.md files, when their references are read, then every moved sentence is there word for word and SKILL.md points to it. | PASS 2026-11-12 |
| [codex-ro-home](Tests#t-codex-ro-home) | requirement | SET-3 | Given a Codex sandbox that leaves the home folder read-only, when setup adopts a clean toy repo, then it says the private settings were not written and still adopts the repo, with no crash. | not run |
| [codex-pods-collide](Tests#t-codex-pods-collide) | requirement | SET-3 | Given a Codex pod and a Claude Code pod that know nothing of each other, when they queue goals, bind workers and run lanes in the same toy repos at once, then no goal or binding is lost, a repeated slug is refused, the lanes share one slot pool and take turns, and their private flow files stay apart. | not run |
| [codex-skip-77](Tests#t-codex-skip-77) | requirement | SET-3 | Given a regression row that cannot run on this machine, when it exits 77, then the run records it as SKIPPED, never PASS, opens no issue, and a later lane runs it again. | not run |
| [codex-harness](Tests#t-codex-harness) | requirement | SET-3 | Given a stand-in for codex that runs the prompt's commands, when the Codex harness runs them on a clean toy repo with no private settings, then setup adopts, go freezes the goal, the live board lists it, health check prints its verdict and regression run prints its result. | not run |
| [package-gate-head](Tests#t-package-gate-head) | requirement | SET-3 | Given the merged head of a pull request, when package.py's file and script checks run on its tracked files, then the lane fails if a script is over 20,480 bytes, the package has over 99 files, or a script is not standalone; it runs on Windows too. | not run |
| [package-caps-held](Tests#t-package-caps-held) | requirement | SET-3 | Given the shipped package, when a script reaches 20,480 bytes or a 100th file is added, then dev/package.py fails, and the real tree stays at 99 files and under the byte cap. | PASS 2026-11-14 FLAKY |
| [package-headroom-held](Tests#t-package-headroom-held) | requirement | SET-3 | Given the shipped package, when rules.py, lane.py, goal.py, actions.py or report.py passes 19,000 bytes or the package passes 98 files, then the check fails; today all five are at most 19,000 and the package has 98 files. | FAIL 2026-11-14 |
| [set7-dry-run-lists-all](Tests#t-set7-dry-run-lists-all) | requirement | SET-7 | Given a repo, when setup runs dry and then for real, then the dry run writes nothing anywhere and lists every file the real commit holds. | not run |
| [set7-second-run-nothing](Tests#t-set7-second-run-nothing) | requirement | SET-7 | Given an adopted repo with a working config nobody committed, when setup runs again, then it prints NO CHANGE, adds no commit, leaves a clean tree and keeps the config's own values. | not run |
| - | requirement | SET-7 | no passing test | not enforced |
| [set8-hooks](Tests#t-set8-hooks) | requirement | SET-8 | Given a repo with the hooks setup installs, when a staged change adds a private line, then git commit refuses naming the file and line and never the text, and nothing is committed. | PASS 2026-11-12 |
| [set8-setup-commit](Tests#t-set8-setup-commit) | requirement | SET-8 | Given an adoption whose staged file holds a private line, when setup runs, then it refuses before its own commit, naming the place, and commits nothing. | PASS 2026-11-12 |
| [set8-local-setting-refused](Tests#t-set8-local-setting-refused) | requirement | SET-8 | Given a private-home key in the config the adoption would commit, when setup runs, then it refuses naming the key and the line, never the value, and writes nothing. | not run |
| [set8-private-value-refused](Tests#t-set8-private-value-refused) | requirement | SET-8 | Given a home path or a local setting value on a line the adoption adds, when setup runs, then it refuses naming file and line and never the value, while text the repo already had, a short value and a template default pass. | not run |
| [set8-health](Tests#t-set8-health) | requirement | SET-8 | Given a repo with the private-name hooks installed or removed, when health runs its hooks rule, then the row appears in the Security and privacy group with its PASS or WARN text, and a wrong group, which prints no hooks row, fails the row. | PASS 2026-11-12 |
| - | requirement | SET-15 | no passing test | not enforced |
| [backlog-milestones-made](Tests#t-backlog-milestones-made) | requirement | SET-17 | Given a repo with feature pages Calc and Zed, when the Backlog milestones are made with --live, then Backlog: Calc, Backlog: Zed and Backlog: Other exist, a dry run writes none and a second run makes none. | not run |
| [backlog-setup-makes](Tests#t-backlog-setup-makes) | requirement | SET-17 | Given setup's issue filing, when it runs on a GitHub repo, then it makes the Backlog milestones with --live before it files health issues, and --no-issues makes none. | not run |
| [backlog-adoption-warns](Tests#t-backlog-adoption-warns) | requirement | SET-17 | Given a GitHub repo missing one standing Backlog milestone, when health checks the Adoption group, then it warns for that one and for none in a repo with no GitHub origin. | not run |
| - | requirement | SET-17 | no passing test | not enforced |
| [setup-zero-tests-119](Tests#t-setup-zero-tests-119) | defect | [#119](https://github.com/jcl2018/agent-workflow-template/issues/119) closed (2026-11-13) | Given a repo whose tests are named *_test.py, when setup picks its check, then the command finds at least one test, and with no proof it is no fit with a finding. | not run |
| [setup-refusal-writes-120](Tests#t-setup-refusal-writes-120) | defect | [#120](https://github.com/jcl2018/agent-workflow-template/issues/120) closed (2026-11-13) | Given any refusal, signal or kill during an adoption, when setup stops, then the tree, branches, index and home folder are as they were, and a killed run is recovered by the next. | not run |
| [setup-tsv-guard-127](Tests#t-setup-tsv-guard-127) | defect | [#127](https://github.com/jcl2018/agent-workflow-template/issues/127) closed (2026-11-13) | Given a .gitignore blocking *.tsv and a hook that rejects tracked .tsv files, when setup runs, then the ignore is exempted by a written line and the hook is named with its exemption and never edited. | not run |
| [set13-hooks-once](Tests#t-set13-hooks-once) | defect | [#2880](https://github.com/jcl2018/agent-workflow-template/issues/2880) closed (2026-11-12) | Given a repo where setup.py --reply-hook and --govern-hook run repeatedly, even on a Windows path or over a file already holding two govern hooks, when settings.local.json is read, then it holds exactly one reply hook and one govern hook. | not run |
| [skill-size-116](Tests#t-skill-size-116) | defect | [#116](https://github.com/jcl2018/agent-workflow-template/issues/116) closed (2026-11-10) | Given the package's skills, when each SKILL.md is counted, then every one is under 150 lines, so test-board passes. | PASS 2026-11-10 |
| [size-139](Tests#t-size-139) | defect | [#139](https://github.com/jcl2018/agent-workflow-template/issues/139) open (2026-11-13) | Given criteria.py's page rules moved into deployments.py by a pure move, when health's size rule and the split checks run, then neither file warns and every moved name resolves the same on criteria. | failing (issue reopened) 2026-11-13 |
| [size-140](Tests#t-size-140) | defect | [#140](https://github.com/jcl2018/agent-workflow-template/issues/140) open (2026-11-13) | Given docs.py's page map moved into counting.py by a pure move, when health's size rule and the split checks run, then neither file warns and every moved name resolves the same on docs. | failing (issue reopened) 2026-11-13 |
| [size-141](Tests#t-size-141) | defect | [#141](https://github.com/jcl2018/agent-workflow-template/issues/141) open (2026-11-13) | Given regression.py's row and page readers moved into runs.py by a pure move, when health's size rule and the split checks run, then neither file warns and every moved name resolves the same on regression. | failing (issue reopened) 2026-11-13 |
| [codex-key-commands](Tests#t-codex-key-commands) | defect | [#38](https://github.com/jcl2018/agent-workflow-template/issues/38) closed (2026-11-11) | Given a clean toy repo with no private settings and a Codex that is installed, signed in and able to answer, when Codex runs setup, go, the live board, health check and regression run, then each runs and leaves what it should; where Codex is not available the row exits 77 and is SKIPPED, never PASS. | not run |
