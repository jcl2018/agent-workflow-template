# Roadmap

## How it runs

One session governs, and the others build. Start every goal with `/workflow-monitoring go`, then run
`/workflow-monitoring watch`. Each goal gets its own worktree and background agent.

## Rescoped: delivery wraps your own skill suite

Delivery no longer has its own design, design review or judge. Every goal runs one flow through the owner's
own skill suite, unattended: idea, plan, build, review, qa and ship, with frozen done lines, the repo's checks, a 3-try
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
| `workflow-health` | `check`, `run`, and milestones | Checks the repo's health with fixed rules |
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

- Pages live in `docs/wiki/`, and `.loop/docs.tsv` maps each page to the paths it describes. The wiki is five feature
  pages (Delivery, Documentation, Monitoring, Regression, Release) plus Home; install steps and the file reference are
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
