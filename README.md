# agent-workflow-template

A small agentic workflow you can add to any repo. You state a goal and the checks that prove it's done. A background
agent takes it through your own skill suite's flow, unattended: your idea, plan, review, test and ship skills, with
frozen done lines and the repo's checks around them. You review the pull request. One session governs and the others
build.

**Delivery runs standalone, or with your own skill suite.** A private file outside the repo,
`~/.workflow-loop/flow.json`, names a skill for each step and how to run it in its own unattended mode. Setup fills it
with `built-in` steps, which run delivery's own routine for idea, plan, review, qa and ship; name your own skill for any
step and it replaces that routine. With no flow file, delivery refuses with one line saying how to set it. See
[the file contract](skills/loop-files.md).

**Status: early. Copy the `skills/` folders into your agent's skills folder, or run `dev/install-local.sh` for Claude
Code. No marketplace listing yet.** See the [wiki](docs/wiki/Home.md) for the features and the
[roadmap](docs/ROADMAP.md).

**This repo runs with no gates.** Its `.loop/config.json` turns on `auto_approve` and `auto_merge`. Review is the only gate: delivery runs no check step. What the skills leave for the
owner is approved automatically and logged as auto-approved, in the goal's log and on the board. The release step then
merges the pull request into `main` by itself, after bringing the wiki pages the goal touched up to date, and publishes the wiki once it has merged. The skills' own built-in refusals still apply, and the private-name leak
scan still guards every commit. The risk is plain: a broken or wrong change can reach `main` with nobody looking, and
the only check left is the regression workflow on GitHub, which reports and never blocks. A repo set up from this
template keeps every gate until its owner turns one off.

## How to use

Say these to the agent in the operation session. Each feature's wiki page has the exact commands.

### How to use Delivery

Say these to the agent:

| You say | What happens |
|---|---|
| "Start a goal to add caching, done when the cache test passes" | The goal is drafted with its done lines and shown back to you to confirm. |
| "Go" | The goal is frozen and a worker session starts it right away. |
| "Queue it" | The goal waits in line and starts when its dependencies merge. |
| "What needs me?" | You get the questions waiting on you, each with a recommended answer. |
| "Approve it" / "a" | The decision is recorded with your words and the goal carries on. |
| "Merge it" | A ready pull request is merged and released. |

### How to use Monitoring

Say these to the agent:

| You say | What happens |
|---|---|
| "Run the operation session" | Every ready goal gets its own worker session, and the full live board prints now and at each check-in, or sooner when a worker reports. |
| "Start a goal to add result caching, done when repeat searches are served from the cache" | The goal is queued and starts in its own worker as soon as a slot is free. |
| "Where do things stand?" | You get the live board: Issues first, then running goals with progress and time left, queued goals, dependencies and one finish time. |
| "Tell the caching worker to keep the old cache format" | Your answer reaches that worker session as a message. |
| "Resume the failed caching goal" | A failed or stopped goal gets a new worker; any other goal is refused. |
| "Clean up merged branches, list them first" | You see the merged goal branches that would go; once you say so, they are deleted locally. |

### How to use Documentation

Say these to the agent:

| You say | What happens |
|---|---|
| "Check the docs" | Every stale, missing, unmapped or unwritten page is listed with what is wrong, or you hear that the docs are clean. |
| "Audit the docs and fix what you can" | Mechanical fixes such as the Tests tables are made, and the wording left to rewrite is listed. |
| "Draft a feature page for billing: charge cards once a month" | A new Unreviewed feature page is drafted and mapped, with a list of what is left to write. |
| "I've reviewed the Delivery page" | The page is marked Reviewed with today's date, and its Problem, Requirements, Non-goals and Success metrics lock. |
| "Publish the wiki" | Pages are copied to the GitHub wiki; it refuses while a page still has problems. |
| "Undo the last publish" | The last publish is reverted, unless the wiki changed since. |

### How to use Regression

Say these to the agent:

| You say | What happens |
|---|---|
| "Run the land tests" | Every land test runs; each failing test gets one GitHub issue, and a test that passes again closes its issue. |
| "Add a test for DEL-1 that runs the delivery toy suite" | A test row is added and tied to that requirement. |
| "Prove the cache test can fail" | The test runs against deliberately broken code, and is marked seen failing or flagged as proving nothing. |
| "What's untested?" | Requirements with no test, draft tests and tests never seen failing are listed. |
| "List every test" | Every test, grouped by feature, with its kind, what it guards, what it checks and its last result. |
| "Write the GitHub workflow" | The GitHub Actions run is written, so the same tests run there on its schedule. |

### How to use Health

Say these to the agent:

| You say | What happens |
|---|---|
| "How healthy is this repo?" | You get the formal report: every rule by group, each problem with its fix, the tests, and one verdict. |
| "Check only the docs health" | The same report for that one group. |
| "What would you file?" | Each issue it would open, update, close or reopen is listed; nothing is written. |
| "File the docs findings" | Only that group's findings become issues, each tagged with its group. |
| "Judge the repo" | The report, plus suggestions on requirement wording, test strength and speed, with ranked next steps; the verdict doesn't change. |

### How to use Setup

Say these to the agent:

| You say | What happens |
|---|---|
| "Set up this repo" | It shows what it found and would add, then writes it on a setup branch for you to review and merge. |
| "Show me what setup would do first" | Every file it would add or convert is listed; nothing is written. |
| "Show me every setting" | Each repo and private setting, with its default and a one-line explanation. |
| "Fill in any missing settings" | Missing repo settings are added with their defaults; your own values are kept. |
| "Install the reply hook" | Operation-session replies that don't follow the check-in layout are blocked, saying what is missing. |
| "Is there a newer template version?" | It shows what the newest release brings and which skill files you changed here; nothing is written. |
| "Update this repo to the newest template" | The skills update, and this repo's new settings, entry point and agent files land on an update branch for you to merge; your own values and pages are kept. |
| "Send my skill fix back to the template" | It drafts one issue with the diff and no repo name, and files it once you say so. |
| "Wire the skills into CLAUDE.md and AGENTS.md" | Both files get the same block pointing every new session at `.loop/START.md`; your own text is kept. |

### How to use Automation

Say these to the agent:

| You say | What happens |
|---|---|
| "Set up the scheduled routines" | Regression and health workflows are written to run every 4 hours in GitHub Actions, for you to merge. |
| "Run health every 12 hours instead" | The schedule setting changes and the health workflow is written again to match. |
| "Turn off the scheduled health run" | Scheduled health runs write nothing and say the routine is off; you can still start one by hand. |
| "Post the automation digest" | One comment on the pinned digest issue lists what ran, the new, still-open and fixed issues, and a request per open issue. |
| "Write the scheduled regression run again" | The regression workflow is rewritten from the current config, so its schedule matches. |

### How to use Guardrails

Say these to the agent:

| You say | What happens |
|---|---|
| "Show me every guardrail" | You get the Guardrails page: each guardrail with what it protects against, the feature that owns it, its setting, and whether its Tests row says it is enforced. |
| "Which guardrail settings are there?" | The settings reference lists each setting with its home, default and meaning: token_budget, step_budget_minutes, test_budget_minutes, goal_lane_minutes and silent_minutes among them (time_budget_minutes is not listed yet). |
| "Check the budgets" | Health's performance group runs: it warns on any of the last 10 finished goals over its time or token budget, a goal's test lane over goal_lane_minutes, and a full suite over 30 minutes. |
| "Which guardrails aren't enforced yet?" | Each guardrail whose Tests row reads not enforced is listed with the feature that owns the missing part. |

## What it aims to be

- **Light:** Markdown instructions and a few small scripts, with no engine to run.
- **Yours:** delivery wraps the skill suite you already use instead of adding its own design or review steps.
- **Governed:** the session you talk to never builds. It starts background agents, shows what waits on you, and keeps a
  dashboard.
- **Checkable by you:** every pull request says how to verify it by hand, and your wiki stays in step with the code.
- **Not tied to one agent:** built for Claude Code and Codex first, then other agents that read `SKILL.md`.

## Commands

Each skill's `references/` folder has a chart for every command, with a status line saying what's proven. Most of these have run on a toy
repo, and `go` and `publish` have also run on a real repo. The skill flow has run for real only up to its first step. They may change while the first version settles. The examples use Claude Code. In other agents, you can ask
in plain words, such as "start a goal to add result caching".

Set up a repo once:

```text
/workflow-setup
```

Start a goal and watch it:

```text
/workflow-monitoring go "add result caching" --done "repeat searches are served from the cache"
/workflow-monitoring watch
```

**One session governs, and the others build.** `go` starts a background agent in its own worktree, and `watch` keeps
goals moving until nothing is left. You stay in one session and review pull requests.

Every goal runs the same flow: freeze the done lines, then your idea skill, your plan skill, the build, your review skill, your test skill and your
ship skill, then the pull request and the release. Review is the only gate; each step can be mapped to any skill in your private flow file. Each skill runs only after a probe proves its unattended mode, takes its recommended answers, and leaves
anything only you can decide under Waiting on you. Nothing is approved for you. The ship skill never pushes in that
mode, so delivery opens the pull request itself, with each step's result in its body.

Regression and health also run on a schedule in GitHub Actions (every 4 hours by default, `off` per routine in
`.loop/config.json`), filing failing tests as `defect` issues and health findings as tagged issues, and posting one digest comment per round on a pinned `Automation digest` issue, which is also emailed to you
once per round when the mail secrets are set (Cloudflare Email Service or SMTP). These runs use Actions minutes, and
each round's cost is shown and flagged over 45 minutes.

See where things stand, or pick up a failed goal:

```text
/workflow-monitoring report
/workflow-monitoring dashboard
/workflow-monitoring resume <slug>
```

`mend` and `resume_on_limit` in `.loop/config.json` let `watch` give a failed goal one fresh agent, and continue after a
usage limit. Both are off until you turn them on. Background agents need the tools you allow in `agent_command`.

Run the operation session with one command. It plans queued goals as a dependency graph (`depends-on` on a queue line,
at most `parallel` workers at once, no waiting for shared files), starts every goal whose dependencies are merged, watches
the workers, updates the board and prints the full live board on the cadence (30 minutes by default), or at once when a worker reports:

```text
/workflow-monitoring operate
/workflow-monitoring send <slug> "<answer or follow-up>"
```

A goal merges the latest base branch before its pull request and reruns its checks if that changed anything; only a real
conflict costs it a try. Goal steps refuse outside a worker.

The pieces it runs, if you want them by hand, are asked in plain words (see `skills/workflow-monitoring/references/operation.md`):

```text
"update the board and print what changed"
"draw the board page"
"set the check-in cadence to 30 minutes"
"follow the goals in ../other-repo"
/workflow-monitoring go "<goal>" --done "<line>"
```

Updating the board writes `board.json` and prints what changed; drawing the page then makes `board.html` and
`board-artifact.html` from it.

An operation session only assigns, watches and reports. It puts goals in a named batch, `start` begins one worker for
each goal, each worker runs its own loop to the end, and each sends its result (merged, failed or waiting, with the pull
request) back as a prompt message that the board shows. A check-in prints the live board: Issues, Running goals,
Queued goals, Dependencies, Finish:

```text
"add a goal to the nightly batch: <goal>, done when <line>"
"start the nightly batch"
"show the nightly batch status"
```

Keep tests visible and enforced:

```text
/workflow-regression sync
/workflow-regression red <id> --break "<a command that breaks the code>"
/workflow-regression run land
/workflow-regression workflow
```

A row must be seen failing once before it counts. Known failures don't block, and each other failing row gets one issue.

Keep the wiki in step with the code. Pages live in `docs/wiki/`, so they're reviewed in pull requests:

```text
/workflow-docs init
/workflow-docs check
/workflow-docs publish
/workflow-docs restore
```

`publish` only adds or updates pages it wrote, unless you name one with `--adopt`, and never deletes one. `restore`
undoes the last publish.

With `"criteria": true` in the config, `check` also holds the wiki to a contract: Home is free-form and each feature page
is a short PRD: Problem, an optional Usage, up to 6 requirements (`criteria_max`) marked Unreviewed or Reviewed with a
date, Non-goals, Success metrics, and Tests: each requirement's regression rows as Given/When/Then scenarios with their
last result. Only the owner reviews a PRD (`/workflow-docs review PAGE`); after that Problem, Requirements, Non-goals and
Success metrics are locked until the owner un-reviews it, and a Usage change shows as changed until the owner reviews it
again. `/workflow-docs prd NAME "<idea>" --paths A,B` drafts a new feature's PRD.

Upgrading a repo whose pages still have Summary and Criteria:

1. Preview: `python3 prd.py convert` (in `skills/workflow-docs/scripts`) prints one line per page and writes nothing.
2. Convert: `python3 prd.py convert --write`: Summary becomes Problem, Criteria Requirements (ids and Reviewed stamps
   kept), and each page gets `Review: **Unreviewed**` and placeholder Non-goals and Success metrics.
3. Write the drafts: replace each placeholder with what the feature deliberately won't do and one to three measurable
   lines on how you know it works.
4. Rewrite each regression row's description (column 6 of `.loop/regression.tsv`) as `Given ..., when ..., then ...`.
5. Render: `python3 criteria.py render`.
6. Check: `python3 docs.py check` prints `DOCS OK`.

Rollback is reverting that commit.

Release the work, or leave it unreleased for now:

```text
/workflow-release cut <slug>
/workflow-release leave <slug>
```

Every goal has a `Verify by hand` section: steps you can follow to see the change work, each with what to expect. `cut`
refuses without one, and refuses if a wiki page is stale or a requirement's regression row is missing or failing. It then
creates a draft GitHub release that carries those steps and the docs that changed, for you to publish. After a cut, the
agent publishes the wiki. No release is published without you. Nothing merges without you, unless the repo turns on
`auto_merge`, as this one does.

## Getting started

From install to one finished goal.

1. **Install.** Run `dev/install-local.sh`. It links each `skills/workflow-*` folder into `~/.claude/skills` (or
   `$CLAUDE_SKILLS_DIR`) and prints `LINKED <name>`. It skips a name that is already a real folder. For another agent,
   copy the `skills/` folders into its skills folder.
2. **Set up your repo.** Run `/workflow-setup`. It writes `.loop/config.json`, `.loop/queue.md` and `.loop/findings.md`
   on a branch called `workflow-setup`. Preview with `/workflow-setup setup --dry-run`, using the path to the skill's
   folder. Then allow the
   tools a background agent needs in `agent_command` (for example
   `["claude", "-p", "--allowedTools=Bash,Read,Write,Edit"]`; you choose the list), and review and merge the branch
   yourself. The other skills read the config from the base branch. Setup also writes `.loop/START.md`, the entry point
   any new session reads first, and the same workflow-loop block into `CLAUDE.md` and `AGENTS.md`, so Claude Code and
   Codex run the same loop.

   To run the loop from Codex, use `codex exec -s workspace-write` with these writable roots in
   `sandbox_workspace_write.writable_roots`: the repo's git folder, its remote, and `~/.workflow-loop` (setup and `go`
   write the private settings there; a read-only home leaves them unwritten and `go` is refused). The git folder root
   also lets a run write `.git/hooks`, which a narrower `.git/loop` root would not. The first setup run exits 1 until
   `agent_command` names the tools you allow. Pick the model yourself (`-m`): a model your account does not support is
   rejected before anything runs. `dev/toy/test-codex.sh` proves this on a clean toy repo and is skipped, never passed,
   where Codex cannot answer.
3. **Start a goal.** From the main checkout, on the base branch:
   `/workflow-monitoring go "add result caching" --done "repeat searches are served from the cache"`. Done lines are
   frozen once the goal starts, so make each one provable before the pull request, by a test or by what a person
   can see (see [Delivery](docs/wiki/Delivery.md)). Setup filled `~/.workflow-loop/flow.json` with `built-in` steps,
   so this works with no skill suite; name your own skill for any step there and it replaces that step's routine.
4. **Watch it.** `/workflow-monitoring watch` starts queued goals in their own worktrees, prints what changed, and ends
   with what waits on you. Use `report` for a snapshot.
5. **Answer what waits on you**, in the exact words `watch` prints.
6. **Review.** The goal ends at a pull request. A monitored goal answers `leave` by itself, unless you started it with
   `--release ask`; then it waits for `cut <slug>` or `leave <slug>` (see [Delivery](docs/wiki/Delivery.md)). With
   `"release_auto": true`, it decides from its diff and may cut a draft instead. Answer before you merge, because `cut`
   commits on the goal's branch. Review and merge the pull request yourself; nothing here merges unless `auto_merge` is on.
7. **Keep it current.** `/workflow-setup update --check` shows what a newer template version brings;
   `/workflow-setup update` applies it and puts this repo's generated files on a `workflow-update-vX` branch for you to
   merge. A skill you fixed here is kept, and `/workflow-setup update --propose` sends the fix back to the template.

## About this repo

This section was the wiki Home page; Home now holds only the features table.

A small agentic workflow for any repo: you state a goal and the checks that prove it, and a background agent takes it
through your own skill suite's flow, unattended, to a pull request you review. One session governs and the others build: `/workflow-monitoring operate` plans queued goals as a dependency graph and starts the workers and prints the live board (issues, running goals, queued goals, dependencies and one finish time) every 30 minutes by default. To install it
and run a first goal, or to see where every file lives, read the rest of this README. It's released under the MIT license. The last step of every goal, the release step (see the [Delivery](https://github.com/jcl2018/agent-workflow-template/wiki/Delivery) page), also brings the wiki up to date and publishes it.


**This repo runs with no gates.** Its `.loop/config.json` turns on `auto_approve` and `auto_merge`. Review is the only gate: delivery runs no check step. What the skills leave for the
owner is approved automatically and logged as auto-approved, in the goal's log and on the board. The release step then
merges the pull request into `main` by itself. The skills' own built-in refusals still apply, and the private-name leak
scan still guards every commit. The risk is plain: a broken or wrong change can reach `main` with nobody looking, and
the only check left is the regression workflow on GitHub, which reports and never blocks. A repo set up from this
template keeps every gate until its owner turns one off.


### Reading the charts

The charts in each skill's `references/` folder are read this way. Each chart shows a command's stages, with amber at each stop for the owner. Under it, `Status:` puts every stage in one
of three groups, `Stops for the owner:` names the stops, and `Proof:` says what the status rests on.

| Status | Means |
|---|---|
| Built and proven | A toy test passes on this stage, or a real run on this repo is on record |
| Built only | It exists, but no test exercises it and no real run is on record |
| Planned | Not built yet |

A toy test uses a throwaway repo and a stand-in for GitHub, so built and proven doesn't mean it has run on a real repo.
`Proof:` says when it hasn't. Real runs were read on 2026-11-06 from the run records of this repo and one other it
follows, plus their pull requests, releases and wikis. That second repo isn't named here. On this repo, eight real goals
reached a pull request, all at the level now called 1, and three publishes reached the wiki. The second repo ran ten
goals, including one real `cut` to a draft release. This repo has since had its own real `cut`, v0.1.1. Neither repo shows a regression workflow run in CI, a
or a batch with a real agent. Records older than these goals may be gone, so "not on record" doesn't mean it never happened.

### What is proven

- "`report` left out queued goals that were ready to start. It now lists them." (FINDINGS.md)
- Toy tests cover goals, the board, docs, criteria, releases and regression, each under `dev/toy/`.
- Codex ran a level 0 toy goal from design to pull request with no failed try (FINDINGS.md).
- The regression workflow passes on GitHub. Its first run failed 2 rows, and both are fixed (FINDINGS.md).

### What is not proven

- "Real repos differ from the toy: four-number versions, changelogs with bracket headings and an intro paragraph, tests
  outside `tests/`, a wiki with pages from another tool, and a pre-push hook that takes minutes." (FINDINGS.md)
- Several goals pushing at once can fail with a bare git error, and a plain re-push works; `pr` retries twice
  (FINDINGS.md).
- Some scripts are within a few hundred bytes of the 20 KB limit, so the next feature needs a new script
  (FINDINGS.md).
- "Codex's `workspace-write` sandbox blocks writes to `.git` and outside the workspace." (FINDINGS.md)

### Gaps for the owner

- The timed check-in loop (`cadence`, then `watch --once` and `board` on each wait) has not fired on its timer. No
  finding or decision records a run of it, and its toy test uses fixtures.
- The skill flow has run for real only up to the idea step, which waited for the owner as it should (docs/ROADMAP.md).

## File reference

In the repo:

| File | Holds |
|---|---|
| `.loop/config.json` | Base branch, agent commands, risky paths, wiki folder |
| `.loop/queue.md` | Goals to run, one line each |
| `.loop/goals/<slug>.md` | One goal: frozen done lines, plan, verify steps |
| `.loop/findings.md` | Open findings |
| `.loop/docs.tsv` | Each wiki page and the paths it describes |
| `.loop/regression.tsv` | Test rows |
| `.loop/regression-known.tsv` | Rows expected to fail, with a reason |
| `.loop/regression-runs.tsv`, `.loop/regression-issues.tsv` | Each row's last result; each defect test's issue state |
| `.github/workflows/regression.yml`, `.github/workflows/health.yml` | The scheduled routines (written by setup) |
| `docs/wiki/` | Wiki pages, each starting with `<!-- workflow-docs -->` |

Outside the repo, run state lives in `<git common dir>/loop/`: `runs/<slug>.json`, `logs/<slug>.log`,
`dashboard.html`, `wiki.json`, `board.json`, `board.html`, `board-artifact.html`, `cadence` (minutes between
check-ins, or `off`) and `handoff.md`. Nothing there is committed. `board.py repos add` keeps a list of repo paths in `~/.workflow-loop/repos`, and
`~/.workflow-loop/flow.json` names your skill flow.

In this template: `skills/` (the seven skills; the full contract is `skills/loop-files.md`), `dev/` (install, package and
toy tests), `listing.json`, `VERSION`, `DECISIONS.md`, `FINDINGS.md`, `docs/ROADMAP.md` and `LICENSE`.

## License

MIT. See [LICENSE](LICENSE).
