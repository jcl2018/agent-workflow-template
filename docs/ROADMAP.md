# Roadmap

## V1

V1 is done when all seven items below are checked. The phases and Gate A (the V1 format frozen, release `v0.28.0`) are in [issue #2881](https://github.com/jcl2018/agent-workflow-template/issues/2881). State is as of 2026-11-12; a goal named here is a `loop/<slug>` branch in `.loop/queue.md`.

- [ ] **1. Health is green on main.** Tracking: step 1.1 of [#2881](https://github.com/jcl2018/agent-workflow-template/issues/2881) (a read-only health and review of main, running), the health size findings [#2866](https://github.com/jcl2018/agent-workflow-template/issues/2866) and [#2867](https://github.com/jcl2018/agent-workflow-template/issues/2867), and goals `spec-decisions` (PRD conflicts, at the pull request step) and `health-docs-size` (docs consolidation, held until `spec-decisions` lands). State: not green. On v0.27.34 the check gave 60 pass, 57 warn, 14 fail. The fails are Monitoring's Usage edited after the owner's review (only the owner can clear it), `workflow-delivery/SKILL.md` at 150 lines, and 12 size fails, of which 11 are false on a Windows CRLF checkout and only `private.py` (21,767 bytes, fixed by `private-size-pc`) is really over. The review found 13 conflicts and gaps (Automation, Delivery, Documentation, Guardrails, Health, Setup), and GRD-1 to GRD-10 and SET-12 to SET-15 have no regression row.
- [ ] **2. Regression is trustworthy.** At most one issue per failing row, and the suite inside its budget on Linux CI. Tracking: `regression-issue-paging` ([PR #2852](https://github.com/jcl2018/agent-workflow-template/pull/2852), draft, awaiting Linux red proof; about 2,475 regression defect issues are open, likely duplicates), `regression-rows-set-grd` ([PR #2853](https://github.com/jcl2018/agent-workflow-template/pull/2853), draft, awaiting Linux red proof), `red-off-platform-prd` (qa waiting for Linux and Mac red proof), [#2865](https://github.com/jcl2018/agent-workflow-template/issues/2865) (the pull request lane gate reuses qa's run) and `automation-budgets` ([PR #2857](https://github.com/jcl2018/agent-workflow-template/pull/2857), merged in v0.27.34: one 30-minute budget, two shards; its first Actions run is not yet seen). State: not met.
- [ ] **3. Windows, Mac and Linux are supported, with a Windows-safe check on every merge.** Tracking: `win-posix-calls` ([PR #2616](https://github.com/jcl2018/agent-workflow-template/pull/2616), merged in v0.27.31), `win-posix-rest` ([PR #3050](https://github.com/jcl2018/agent-workflow-template/pull/3050)), `win-package` (running), `pr-body-file` ([#2879](https://github.com/jcl2018/agent-workflow-template/issues/2879), in review) and [#2871](https://github.com/jcl2018/agent-workflow-template/issues/2871) (the Windows-safe check on every merge, which `migration-lessons` carries). State: Windows lanes work; the rest is open.
- [ ] **4. Adoption is proven.** SET-11's strict replay on a second machine, and `goal adopt` across machines. Tracking: SET-11 ([PR #2868](https://github.com/jcl2018/agent-workflow-template/pull/2868), merged, requirement still Unreviewed), `goal-adopt` ([#2851](https://github.com/jcl2018/agent-workflow-template/issues/2851), at the pull request step), `migration-check` (shipping), [#2877](https://github.com/jcl2018/agent-workflow-template/issues/2877) (stamp the template version) and [#2880](https://github.com/jcl2018/agent-workflow-template/issues/2880) (hooks installed once). State: the replay on a second machine has not been run.
- [ ] **5. Every requirement is Reviewed by the owner.** Tracking: step 1.6 of [#2881](https://github.com/jcl2018/agent-workflow-template/issues/2881) (the owner reviews in one sitting, after `spec-decisions` and the docs consolidation). State: 60 of 91 requirements Reviewed and 31 Unreviewed (Guardrails 10 of 10, Automation 6 of 8, Setup 7 of 15, Documentation 4 of 16); the page-level review is open on 7 of 8 pages; plus the nine locked proposals in DECISIONS.md.
- [ ] **6. The Agensi package rules pass.** Tracking: `package-under-cap` (queued behind `win-package`), `private-size-pc` ([PR #2982]({R}/pull/2982)), [PR #1772](https://github.com/jcl2018/agent-workflow-template/pull/1772) (`dev/package.py` never hangs) and `agensi-ready` (not started). State: `dev/package.py` fails at HEAD.
- [ ] **7. Open defects are triaged.** Tracking: [#2879](https://github.com/jcl2018/agent-workflow-template/issues/2879), [#2851](https://github.com/jcl2018/agent-workflow-template/issues/2851), [#2850](https://github.com/jcl2018/agent-workflow-template/issues/2850), [#2865](https://github.com/jcl2018/agent-workflow-template/issues/2865), [#2873](https://github.com/jcl2018/agent-workflow-template/issues/2873) and [#2876](https://github.com/jcl2018/agent-workflow-template/issues/2876), plus the Mac's [PR #1766](https://github.com/jcl2018/agent-workflow-template/pull/1766) and [PR #2163](https://github.com/jcl2018/agent-workflow-template/pull/2163). State: open; each needs a fix, a decision or a close.

## How it runs

One session governs, and the others build. Start every goal with `/workflow-monitoring go`, then run
`/workflow-monitoring watch`. Each goal gets its own worktree and background agent.

## Rescoped: delivery wraps your own skill suite

Delivery no longer has its own design, design review or judge. Every goal runs one flow through the owner's
own skill suite, unattended: idea, plan, build, review, qa and ship, with frozen done lines, a 3-try
stop and `Verify by hand` around them, and delivery's own pull request at the end. A private file,
`~/.workflow-loop/flow.json`, names the skills; the repo never does. `poc` and the levels are gone, because the suite does those jobs.
`workflow-release` stays, as the place for the owner's own routines before a release.

agent-workflow-template is a pack of seven focused skills, so an agent loads only the one it needs.

| Skill | Commands | What it does |
|---|---|---|
| `workflow-setup` | `setup` | Surveys a repo and writes its config, on a branch |
| `workflow-delivery` | `go`, and the goal steps `new` to `show`, with `flow` and `record` | Runs your skill flow from a sentence to a pull request |
| `workflow-monitoring` | `go`, `watch`, `report`, `dashboard`, `resume`, `board`, `cadence`, `repos`, `note`, `session`, `retire`, `handoff`, and the batch commands `add`, `start`, `status` | Starts goals in the background and shows what waits on you |
| `workflow-regression` | `seed`, `add`, `sync`, `criteria`, `red`, `run`, `workflow` | Keeps tests visible and enforced |
| `workflow-docs` | `init`, `survey`, `add`, `check`, `criteria`, `publish`, `restore` | Keeps wiki pages in the repo, holds the criteria contract |
| `workflow-health` | `check`, `preview`, `file`, `judge`, and milestones | Checks the repo's health with fixed rules |
| `workflow-release` | `ask`, `cut`, `leave`, `show` | Versions the repo and writes a draft GitHub release |

The sections below record what earlier batches built, as history.

### Monitoring

One session starts and watches the others.

- `go` queues a goal and starts it. `watch` takes goals from `.loop/queue.md` and gives each its own worktree and
  background agent, unlimited by default (`parallel` caps it).
- Goals that declare the same files don't run together.
- Run state lives in the shared git folder, so every worktree sees it and nothing extra is committed.
- `report` shows each goal's step, its pull request, and what's waiting on you with the exact words to type.
- `dashboard` writes one self-contained HTML page. Claude users can also publish it as an Artifact.
- `resume` picks up a failed or stopped goal. A failed goal never stops the others.
- With `mend` on, `watch` gives a failed goal one fresh agent. With `resume_on_limit` on, it continues after a usage limit.
- Background agents use your own permission settings. agent-workflow-template never turns them off.

### Documentation

- Pages live in `docs/wiki/`, and `.loop/docs.tsv` maps each page to the paths it describes. The wiki is six feature
  pages (Delivery, Documentation, Health, Monitoring, Regression, Setup) plus Home; install steps and the file reference are
  in the README.
- Each feature page lists its criteria and stages: Unreviewed, Reviewed, Enforced or Proven. Tests are rows in
  `.loop/regression.tsv`, each linked to one criterion, and the page counts them.
- Each command on a feature page has a stage chart, a status line from real tests and runs, and its stops for the owner.
  Pages name no script files.
- `check` finds pages that are stale, missing, unwritten or unmapped. With `"criteria": true` it also enforces the page
  list, sections, criteria, charts and the script name rule.
- `publish` updates the GitHub wiki. It never deletes a page, and it won't replace a page it didn't write unless the
  owner names that page.
- `restore` reverts the last publish.

For agent-workflow-template's own Agensi release, `dev/package.sh` builds the ZIP and refuses it if any published rule fails:

| Rule | Check |
|---|---|
| Frontmatter | Every `SKILL.md` has `name` and `description`; `name` matches its folder |
| Pack | Two or more `SKILL.md` files make one listing; the README's title names it, and `shared/` reaches every skill |
| Listing fields | `summary` is 300 characters at most; 10 tags, 10 keywords, 8 use cases at most |
| Files | Text only; no executables, bundled dependencies, `.git` or caches |
| Size | Under 100 files and 5 MB, so upload from an agent also works; the website takes 50 MB and 1,000 files |
| Scripts | Each under 20 KB, and each runs alone with its data embedded |
| Safety | No secrets, obfuscation, encoded text, dangerous commands, or phrases the prompt injection scan fails |
| Disclosure | The listing states every command, file write and network host |

### Agensi rules that shape the design

- **Scripts run alone.** The agent writes each to a temporary file, runs it and deletes it, so a script can't read
  another package file.
- **Skill content stays out of repos.** Agents are told not to save it to project folders. `.loop/` therefore holds only
  the repo's own data: config, goals, queue, findings. The instructions stay in the skill.
- **The scan flags `shell=True`.** Check commands are the repo's own strings, so `goal.py` and `regression.py` keep it,
  and the listing says why. A failed check doesn't block approval when a reviewer finds it's a false positive.
- **The skill must stay available.** On Agensi, each background agent needs the connector too. Installing from this
  GitHub repo needs no connector.

### Done means

1. On a toy repo, level 0 and level 1 goals each end in a pull request.
2. The judge fails a planted bug, and the run fixes it or files a finding.
3. `watch` runs every ready goal in parallel; one fails and the others finish.
4. `report` and `dashboard` match the true state, including a goal waiting on you.
5. `cut` produces a draft release, and `leave` changes nothing versioned.
6. `setup` runs twice on a repo with no change the second time.
7. `dev/package.sh` passes, and refuses a package with one planted fault per rule.
8. One real level 0 goal works on a real repo, and Codex can run the toy level 0 goal.
9. `publish` updates a real wiki without touching other pages, and a real release carries verify steps and docs.

## Second batch: built

- Numbered levels 0, 1 and 2; level 0 is the default.
- One governing session: `/workflow-monitoring go` and `watch`.
- `workflow-regression`: rows, known failures, a workflow, and an issue per failing row.
- A POC's queue line, the mender, resuming after a usage limit, and optional version bumps on pull requests.

## Operation session: built

- `board.py` (`board`, `cadence`, `repos`, `note`, `retire`, `handoff`), `worker.py` and `board_status.py`,
  `board_page.py` (the board's pages and dependency map) and the check-in loop in
  `skills/workflow-monitoring/references/operation.md`.
- `batch.py` (`add`, `start`, `status`): the operation session assigns, watches and reports only, and each goal line runs
  in its own worker.

## Criteria and charts: built

- The wiki as five feature pages plus Home. Criteria are for the owner and tests for the machine. `cut` refuses while
  any test of a criterion is missing, a draft or failing.
- `release_auto`: a monitored batch goal decides from its diff, and only ever cuts a draft.
- A stage chart and status line for every command, with `docs.py check` failing a missing chart or a script file name.

## What is left

1. **The Agensi listing:** list the package on Agensi. The wiki is published; republish it with `workflow-docs` when
   the pages change.
2. **Other agents:** Kimi, Qwen and OpenCode support.
3. **The skill flow, for real:** one real goal ran the idea step unattended and waited for the owner's approval of the
   design, as it should. The plan, review, qa and ship steps haven't run for real yet, and qa needs a browser.
4. **Real proof still missing:** `restore`, a batch with a real agent, the regression workflow's first run on GitHub, the check-in loop firing on
   its timer, and today's level 0 on a real repo. The wiki's status lines list each one. Codex has run level 0 on a toy
   repo, and every row passes in a CI-like run on a Mac.

Merging, a project board and milestones stay with you.
