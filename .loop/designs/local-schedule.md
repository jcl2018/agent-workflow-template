# Design: local-schedule

Status: APPROVED (idea step, recommended answers taken; nothing owner-only is open except what the reply lists).
Goal: .loop/goals/local-schedule.md. Its seven done lines are frozen; this design meets them and changes none.

## Problem
Health with the judge needs the owner's own login and run records, so it cannot run in GitHub Actions. A private repo's
GitHub checks would block its merge. So the schedule moves to the owner's Mac: one user launch agent runs health (judge
included) for every repo, and the full regression for a private repo; issues and the digest are filed as before. A private
repo's merge is unblocked by the delivery pr lane posting its real result as commit statuses.

## Premises (taken as true)
1. launchd coalesces runs missed while the Mac sleeps into one run at wake: StartCalendarInterval gives "a missed run
   happens at next wake" (done line 4) with no code of ours. The report states the gap itself.
2. The judge already runs `judge_command` (`claude -p --tools ""`) as a child process; that uses the owner's login. The
   only API-key code is the workflow's secret mapping (judge_env, judge_setup), which goes away with health.yml.
3. `regression.py run <target> --live` already runs rows and files/updates/closes one issue per failing row
   (runs.sync_issues); `regression.py run --reuse` already is the REG-4 affected-rows selection. The local run reuses both.
4. Statuses posted with `POST /repos/{o}/{r}/statuses/{sha}` satisfy a required check of the same name (no app restriction).

## Size audit (the hard 100-file constraint)
- Files: 96 under skills/ plus listing.json, README, LICENSE = 99. This design adds ZERO files under skills/. New tests go
  in dev/toy (not counted).
- Script-size rule: `size_rows` in skills/workflow-health/scripts/health.py (constants LIMIT = 20*1024, WARN_AT = 90%);
  owned by workflow-health; FAIL over 20480 bytes, WARN from 18432; pinned by the toy row size-fail. We do not change it.
- Headroom today (bytes): lane.py 20286, role.py 20095, lanekit.py 20007, merge.py 19985, goal.py 19100, fit.py 18980 are
  full: nothing may be added to lane.py, role.py, lanekit.py; goal.py and merge.py take only 2-6 line call sites (trim a
  comment or dead line in the same function to pay for them).
- Room: private.py 15123 (delivery), automation.py 15791 and rounds.py 14268 and workflows.py 8586 (health),
  tiers.py 13619 (regression). workflows.py shrinks by about 6.5 KB when the health.yml text goes.
- Placement, so no file is added and none passes 18 KB:
  - Status poster + required-check reader + privacy test: `skills/workflow-delivery/scripts/private.py` (new functions
    `repo_is_private`, `required_checks`, `post_statuses`, `release_statuses`; about 3 KB).
  - Launch-agent plist text and its renderer: `skills/workflow-health/scripts/workflows.py` (replaces the health.yml text;
    plist is a Python string/plistlib dict generated in code, never a committed file).
  - Install, uninstall, status, register, tick: `skills/workflow-health/scripts/automation.py`, a new `local` command group
    (the old health `workflow` command is removed from it; keep it under 18 KB by moving nothing out and deleting the
    health.yml writing).
  - Last-run record: `skills/workflow-health/scripts/rounds.py`.

## Design

### 1. One launch agent, a registry, a tick
- `automation.py local install` (run once per repo by setup, and by hand) writes the registry entry for this repo and, if
  absent, the single launch agent `com.workflow-loop.schedule` in the user's LaunchAgents folder (user domain, no root).
  `StartCalendarInterval` fires at minutes 47 of hours 0,4,8,12,16,20 (the 4 hours of `health_cron`; the agent reads only
  that every-N-hours shape and says so for any other cron). `RunAtLoad` false. `ProcessType` Background. The plist runs
  `python3 <absolute path of this automation.py> local tick`, with PATH set to include the user's gh and claude. The path
  and every other path is generated at install time and lives only in the plist, never in a repo file.
- "One schedule per repo": each repo has its own registry entry and own state; they share the one agent. Uninstalling a repo
  removes its entry; the agent is removed when the last entry goes.
- Finding the repos: a registry file `~/.workflow-loop/schedule/repos.json` (outside any repo, owner-only mode) with one
  record per repo: absolute repo path, `origin` URL, last run. `local install` adds it, `local uninstall` removes it,
  `local status` lists it. The tick never scans the disk. A path that has vanished is reported once and skipped.
- `tick` runs each registered repo in turn, one at a time, under a per-repo mkdir lock with a stale-lock timeout, and each
  repo's work under its own wall-clock cap, so one slow repo cannot starve the rest.

### 2. What a tick does for one repo (offline-safe)
1. Probe: `gh auth status` and one cheap read (`gh api rate_limit`) under a short timeout. Offline or logged out: write a
   `SKIPPED (offline)` line to the log, change NO issue, leave "last ran" untouched, exit 0. The next fire retries.
2. Never touches the owner's working tree: `git fetch origin <base>`, then a detached worktree of `origin/<base>` under
   `~/.workflow-loop/schedule/<key>/` (key = hash of the origin URL), reset on each run, removed if stale. Skills and rows
   come from that checkout.
3. Health: `health.py check` (all rule groups), `file` the findings as health:<group> issues, the judge via
   `judge.py review` using `judge_command` (owner's claude login; no API key secret; `ANTHROPIC_API_KEY` is neither read nor
   passed on; a missing `claude` program or login makes the judge `skipped` and the report says so, as today).
4. Regression, private repo only: `regression.py run <ci_levels or nightly> --live` in the checkout. A public repo's full
   suite stays in GitHub Actions.
5. Digest: `automation.py digest` posts the round comment as today. Run id is the UTC start time (a local run has no Actions
   run id); rounds.py's ordering and "same run twice posts nothing" keep working on it. Mail: sent only if the owner put
   the mail settings in the private settings file; otherwise `MAIL_NOT_SET_UP` and no mail.
6. A failed read of issues changes no issue (same rule the workflows had); a failed filing is named in the digest.

### 3. Missed runs and "last ran"
- launchd runs one coalesced fire at wake. The tick records `last_run` and `last_ok` per repo in the registry.
- The digest comment and every health issue body gains one line: `Last ran: <time>, previous run <time> (<N> hours
  earlier)`, plus `MISSED: no run for <N> hours (Mac asleep or offline)` when the gap exceeds 5 hours. Edit points in
  automation.py: `regression_line`, `health_line`, `compose`; in rounds.py: `created`, `round_cost`/`line` (a local round's
  cost line reads `local run, N min, 0 Actions minutes`).

### 4. Commit statuses so a private repo merges with no click (done line 7)
- `repo_is_private`: `gh repo view --json isPrivate`. Public, or unreadable: no statuses, ever (and the output says why).
- `required_checks(base)`: union of the contexts from `gh api repos/{o}/{r}/rules/branches/<base>` (rulesets, active) and
  `gh api repos/{o}/{r}/branches/<base>/protection/required_status_checks` (classic). Unreadable: post nothing, name it.
- `post_statuses(head, ok, contexts, run_name)`: one `POST /repos/{o}/{r}/statuses/<head>` per context with state
  `success` only when `ok` is true, else `failure`; description names the local run ("workflow-loop pr lane, local run,
  <date>"); target_url omitted. Never `success` for a lane that did not pass.
- Hook: `goal.py cmd_pr`, right after the push and PR creation (the head must exist on the remote), calls
  `private.post_statuses` with the lane's real gate result. On a failed lane the branch is not pushed (unchanged), so a
  failure status is posted only when the head sha already exists on the remote (a rerun of the same head); otherwise
  nothing is posted and nothing can read as success. merge.py then merges normally (`gh pr merge`); no bypass, no admin.
- Release PR (protected base): merge.py `start` creates a release PR whose head also faces the required checks. Its call to
  `private.release_statuses` runs the affected-rows lane for that head (`regression.py run --reuse`) and posts that real
  result. merge.py has about 490 bytes of room: the builder must trade comment bytes for the 3-line call.
- Setup never edits rulesets or branch protection: it only reads `required_checks` and, for each name that no local lane
  will post (anything not matching the lane's contexts), prints `BLOCKS: required check <name> ... remove it from the
  ruleset`. The names are read data, never written to a repo file.

### 5. GitHub workflows
- health.yml: no repo gets one. Remove the template's `.github/workflows/health.yml` and its writing path (automation.py
  `cmd_workflow`, `wanted`, `render`; workflows.WORKFLOW). setup's `decide` stops adding it. `--check` stays only for
  regression.yml. The health "STALE_WORKFLOW" check in health.py reads health.yml: replaced by an absence check
  (a leftover health.yml is a WARN naming `git rm`).
- mail-test.yml: its mail job lived in health.yml; mail now sends from the Mac. Stop writing it and remove the template's
  copy; `mail.py test` is the by-hand test. (Judgment call, listed for the owner.)
- regression.yml, public repo: keeps `schedule` + tags; adds `pull_request` and `push` (branches) running only the REG-4
  affected rows; the full suite only on `schedule`, tag and dispatch. Done line 3.
- regression.yml, private repo: not written; if one exists and was ours, setup reports it as removable (setup-adopt-2 and
  the owner decide when to delete). Done line 2.
- `judge_env` and `judge_setup` config keys: no longer read. Left in the schema (no edit to workflow-setup's settings.py);
  Usage says they are ignored.

## Overlap map (exact edit points)
regression-green-2 edits `skills/workflow-regression/scripts/actions.py`. This goal touches there ONLY:
- the `WORKFLOW` triggers block (the `on:` section, the `@SCHEDULE@` marker area) to add `pull_request` and a branch `push`,
  plus a one-step condition that picks the narrow target on those events;
- `render()` and `write()` (visibility gate: skip, and say why, for a private repo).
Nothing else in actions.py: not row_env, not the heredoc body, not ROW_DROP. The target selection for the PR event goes in
regression.py `cmd_workflow` / a small helper there, not in the heredoc, so the heredoc stays untouched.
setup-adopt-2 edits `skills/workflow-setup`. This goal touches there ONLY:
- seed.py `decide` (lines about 211-217: stop adding health.yml and mail-test.yml; add the local-schedule act and the
  `BLOCKS:` notes) and `apply` (lines about 272-275: replace the `automation.py workflow` call with `automation.py local
  install`);
- setup.py `main`'s `paths` tuple (drop `health.yml`).
Nothing else in setup.py, survey.py, agents.py, settings.py, sync.py, update.py. The new code lives in workflow-health and
workflow-delivery, so a merge conflict can only occur at those few lines.

## Testing without launchctl (dev/toy)
Everything is a pure function of its inputs; launchctl is called only by `install`/`uninstall` through one `launchctl()`
helper that a toy test replaces with a recorder (env `LOOP_LAUNCHCTL` set to a fake script, like fakegh).
- plist: `local plist` prints it; the test checks label, interval hours, no secret, no key name, no repo path, valid
  plistlib parse, absolute program path.
- registry: install, status, uninstall add/list/remove entries in a temp HOME; the agent file is removed with the last.
- no health workflow for any repo; template has no health.yml; public repo keeps regression.yml with the affected-rows
  triggers; private repo gets none and setup names a blocking required check (fakegh serves rulesets and protection).
- offline: fakegh failing `auth status` makes tick change no issue and keep `last ran`.
- missed run: a registry with an old `last_run` makes the digest say `Last ran` and `MISSED`.
- judge: with `ANTHROPIC_API_KEY` unset the judge runs; with no `claude` program it is skipped and says so; the tick
  passes no API key variable.
- statuses: fakegh records posts. Pass: one `success` per required context. Fail lane: `failure` only, never `success`.
  Public repo: zero posts. Unreadable rules: zero posts. Rerun of a failed head posts `failure`, not `success`.
- size: a toy check that every touched script stays under 18432 bytes and skills/ file count is unchanged.
New toy file(s): dev/toy/test-local-schedule.sh and dev/toy/test-statuses.sh; rows added to .loop/regression.tsv.

## Docs and Usage (owner's one-time steps)
- docs/wiki/Automation.md is owned by goal automation-local-prd; this goal does not edit it (touches list excludes it).
- docs/wiki/Health.md Usage: `local install`, `local status`, `local stop`, `local uninstall`; Setup.md and Regression.md:
  the private/public split and the statuses. Tests.md rows for the new toy tests.
- Owner's one-time steps, in Usage: (1) `automation.py local install` (writes the agent; prints the exact load command),
  (2) `launchctl bootstrap gui/$(id -u) <the plist printed>` to load, (3) stop: `launchctl bootout gui/$(id -u)/com.workflow-loop.schedule`,
  (4) uninstall: `automation.py local uninstall`. The first run happens at the next hour slot, or by hand: `automation.py local tick`.
  `claude` must be logged in once in a normal terminal; mail settings, if wanted, go in the private settings file.
- No token, path or private name in any committed file: the plist and registry are generated on the Mac, outside the repo;
  `required_checks` names are printed, not stored.

## Alternatives considered
A. Per-repo launch agents: simplest discovery, but N agents to stop/uninstall and contradicts the one-agent constraint.
B. One agent + registry (chosen): one load/stop/uninstall, repos found from one outside-the-repo file.
C. Cron entry: no sleep catch-up; rejected.
D. Statuses via a GitHub App or bypass: rejected; plain statuses need neither.

## Risks
- The merge.py/goal.py size margins are tight; the builder must measure after every edit.
- A required check named by something other than a status context (an Actions-only check) cannot be satisfied; setup names it.
- launchd calendar fires at minute 47 in local time; DST shifts are harmless (coalesced).
- The launch agent runs in the login session: the Mac must be logged in (locked is fine) for keychain access to claude.

## The Assignment
After merge, run `automation.py local install` in one private repo, load it, run `local tick` once by hand and confirm the
digest line `Last ran` appears and a PR of that repo merges with no click.
