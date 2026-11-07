# Roadmap

## How it runs

One session governs, and the others build. Start every goal with `/workflow-monitoring go`, then run
`/workflow-monitoring watch`. Each goal gets its own worktree and background agent, at every level.

## First batch: built

Delivery, monitoring, documentation and release are built.

Together these give the whole path: start work, watch it run in parallel, document it, and ship the result.

agent-workflow-template is a pack of six focused skills, so an agent loads only the one it needs.

| Skill | Commands | What it does |
|---|---|---|
| `workflow-setup` | `setup` | Surveys a repo and writes its config, on a branch |
| `workflow-delivery` | `poc`, `go`, and the goal steps `new` to `show` | Takes a sentence to a pull request, judged at levels 1 and 2 |
| `workflow-monitoring` | `go`, `watch`, `report`, `dashboard`, `resume`, `board`, `cadence`, `repos`, `note`, `session`, `retire`, `handoff`, and the batch commands `add`, `start`, `status`, `promote` | One session governs; the others build |
| `workflow-regression` | `seed`, `add`, `sync`, `criteria`, `red`, `run`, `workflow` | Keeps tests visible and enforced |
| `workflow-docs` | `init`, `survey`, `add`, `check`, `criteria`, `publish`, `restore` | Keeps wiki pages in the repo and finds stale ones |
| `workflow-release` | `ask`, `cut`, `leave`, `show` | Versions the repo and writes a draft GitHub release |

### Delivery

`poc` answers a question, writes nothing, and ends with one `go` line. `go` freezes the done lines and runs at a level:

| Level | Steps | Fresh judge | Use it for |
|---|---|---|---|
| `0` | Design, plan, build, checks | No | The default: most work |
| `1` | Adds a judge | One, after the build | Work worth a second look |
| `2` | Adds a design review before the build | One, plus the review | Risky or large changes |

- Any change to CI, auth or data is level `1` at least.
- The judge sees only the diff, the goal file and the check results.
- After 3 failed tries, the run files a finding and stops.
- The pull request is your review. The loop never merges.

### Monitoring

One session starts and watches the others.

- `go` queues a goal and starts it. `watch` takes goals from `.loop/queue.md` and gives each its own worktree and
  background agent, 3 at a time by default.
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

### Release

For any repo using agent-workflow-template:

- Once a goal's checks hold, it shows the docs that changed and the verify steps, then asks `cut` or `leave`.
- Every goal has a `Verify by hand` section of numbered steps, each with what to expect. `cut` refuses without it.
- `cut` refuses if a wiki page is stale or missing, or a criterion's regression row is missing, a draft or failing. It
  then moves the version, writes the changelog and creates a draft GitHub
  release carrying the verify steps and docs. You publish it.
- After a cut, the wiki is published with `workflow-docs`.
- `leave` keeps the work unreleased. A monitored batch can answer `leave` by itself. It never cuts, unless
  `"release_auto": true` lets it cut a draft from what its diff shows. A breaking change always waits for the owner.

For agent-workflow-template's own Agensi release, `dev/package.sh` builds the ZIP and refuses it if any published rule fails:

| Rule | Check |
|---|---|
| Frontmatter | Every `SKILL.md` has `name` and `description`; `name` matches its folder |
| Listing fields | `summary` is 300 characters at most; 10 tags, 10 keywords, 8 use cases at most |
| Files | Text only; no executables, bundled dependencies, `.git` or caches |
| Size | Under 100 files and 5 MB, so upload from an agent also works |
| Scripts | Each under 20 KB, and each runs alone with its data embedded |
| Safety | No secrets, obfuscation, encoded text, or instructions aimed at the agent |
| Disclosure | The listing states every command, file write and network host |

### Agensi rules that shape the design

- **Scripts run alone.** The agent writes each to a temporary file, runs it and deletes it, so a script can't read
  another package file.
- **Skill content stays out of repos.** Agents are told not to save it to project folders. `.loop/` therefore holds only
  the repo's own data: config, goals, queue, findings. The instructions stay in the skill.
- **The skill must stay available.** On Agensi, each background agent needs the connector too. Installing from this
  GitHub repo needs no connector.

### Done means

1. On a toy repo, level 0 and level 1 goals each end in a pull request.
2. The judge fails a planted bug, and the run fixes it or files a finding.
3. `watch` runs 3 goals in parallel; one fails and the other two finish.
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

- `watch.py go --session`, `board.py` (`board`, `cadence`, `repos`, `note`, `session`, `retire`, `handoff`),
  `board_page.py` (the board's pages and dependency map) and the check-in loop in
  `skills/workflow-monitoring/references/operation.md`.
- `batch.py` (`add`, `start`, `status`, `promote`): the operation session governs only, and each POC or goal line runs
  in its own background process or session.

## Criteria and charts: built

- The wiki as five feature pages plus Home. Criteria are for the owner and tests for the machine. `cut` refuses while
  any test of a criterion is missing, a draft or failing.
- `release_auto`: a monitored batch goal decides from its diff, and only ever cuts a draft.
- A stage chart and status line for every command, with `docs.py check` failing a missing chart or a script file name.

## What is left

1. **The Agensi listing:** list the package on Agensi. The wiki is published; republish it with `workflow-docs` when
   the pages change.
2. **Other agents:** Kimi, Qwen and OpenCode support.
3. **Level 2:** it has run on a toy repo, unattended. The design skill ran every phase when run alone, but not in the
   goal run. It has not run on a real repo.
4. **Real proof still missing:** `release_auto`, `restore`, a batch with a real agent, the regression workflow's first run on GitHub, the check-in loop firing on
   its timer, and today's level 0 on a real repo. The wiki's status lines list each one.

Merging, a project board and milestones stay with you.
