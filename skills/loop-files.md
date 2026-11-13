# Loop files

The workflow skills share this contract. The design guide at the end explains how they fit together. Skill instructions never go in the repo. A repo holds only its own data.

## In the repo: `.loop/`

| File | Holds |
|---|---|
| `.loop/config.json` | Base branch, check commands, agent commands, risky paths |
| `.loop/queue.md` | Goals to run, one line each |
| `.loop/goals/<slug>.md` | One goal: done lines, plan, log |
| `.loop/findings.md` | Open findings, one line each |
| `.loop/docs.tsv` | Each wiki page and the paths it describes |
| `.loop/config.json` key `session_command` | The session tool, as a list: called `start NAME` (prints the new session's id), `rename ID NAME` and `send ID TEXT`; a non-zero exit or 30 seconds means no session, so the goal falls back to a background process. `$LOOP_SESSION_TOOL` replaces it. The pool is `loop/session-pool.json` under the git common dir |
| `.loop/config.json` key `criteria` | `true` makes `docs.py check` enforce the criteria contract on the wiki pages; each regression row links to one criterion by its goal or id; a reviewed line ends with a hash of its text, and `docs.py check` fails if the text changes; `criteria.py render` makes each page's Tests table |
| `.loop/regression.tsv` | Each test row: id, level, command, goal, date seen failing |
| `.loop/regression-issues.tsv` | Each defect test's issue or pull request: link, state, date; written only by `tests.py issues --write`, shown in the wiki Tests lines and the health report |
| `.loop/regression-runs.tsv` | Each row's last run: id, PASS or FAIL, date; written by `regression.py run`, shown in the wiki Tests tables |
| `.loop/regression-known.tsv` | Rows expected to fail, with a reason; they don't block |
| `.loop/health-rules.json` | The repo's own health rules (each with a break command), default rules turned off with a reason; setup writes it empty |
| `.loop/regression-red.tsv` | Red results proven on another runner: id, date, runner, commit |
| `.loop/START.md` | The generated entry point every new session reads first (`entry.py write`); never edited by hand |
| `CLAUDE.md`, `AGENTS.md` | Each agent's entry file; setup wires the same marked `<!-- workflow-loop -->` block into each (`agent_files`), text outside it is the repo's own |
| `.loop/config.json` key `template_version` | The template version that last wrote the repo's generated files; `update` moves it, the board flags a repo behind |
| `.loop/config.json` keys `template_repo`, `agent_files` | The template's GitHub repo, used when the installed package names none; the agent files setup wires |

Wiki pages live in `docs/wiki/`. Each starts with the line `<!-- workflow-docs -->`, which marks it as safe to update.

### `config.json`

```json
{
  "base": "main",
  "agent_command": ["claude", "-p"],
  "parallel": 0,
  "risky_paths": ["^\\.github/", "(^|/)auth", "(^|/)migrations?/", "(^|/)(schema|data)\\b"],
  "version_file": "VERSION",
  "wiki_dir": "docs/wiki",
  "pr_bumps_version": false,
  "mend": false,
  "resume_on_limit": false
}
```

- Every setting, repo and private, with its default and a one-line explanation, is listed in `workflow-setup/references/settings.md`
  (generated from `settings.py`). `setup.py` writes each repo setting into `config.json` and each private setting into the
  flow file, and keeps any value already set. Every script reads these files fresh on each run, so a change applies at once.
- `parallel`: workers at once; `0` means unlimited, and it is the default.
- `cadence`, `step_limit`, `token_budget`, `max_tries`, `routines`, `regression_cron`, and `test_budget_minutes`, `step_budget_minutes`, `prep_budget_minutes` (none under 15), and health's `stale_branch_days` are optional repo settings; see the reference.
- `agent_command` runs a goal in the background; the prompt is its last argument.
- `auto_approve` (default `false`): `true` approves what a flow step leaves for the owner, logged as auto-approved.
- `review_depth` (default `full`): `full` makes the plan and review steps run their skill's whole pipeline and refuses a
  condensed reply; `condensed` allows a shorter run. Every step's reply states `DEPTH: full|condensed`, record stamps it
  on the step, and the board and the pull request body show it. The flow file's private `full_markers` (per step, strings)
  must appear in a full plan or review reply. `config.json` carries its one-line explanation under `_help`.
- `auto_merge` (default `false`): `true` lets the release step's `merge.py` merge a goal's pull request.
- `pr_bumps_version` moves the last number of the version file on a goal's branch, for repos whose CI needs a bump.
- `mend` and `resume_on_limit` let `watch` restart a goal. `limit_wait`, `mend_wait` and `watch_interval` are optional, in seconds.
- `criteria` (set `true` by `setup`) and `regression_cron` (default `17 */4 * * *`, the scheduled regression's cron, or `off`) are also read by the docs and regression skills; `health_cron` (default `47 */4 * * *`, read by the Mac's local schedule), `regression_runs` (`actions` or `mac`, written by setup) and `digest_owner` set the scheduled health run and its digest (`judge_env` and `judge_setup` are no longer read), and `digest_mail` (default `cloudflare`, or `smtp` or `off`), `smtp_host` and `smtp_port` how the digest is emailed (Automation page).
- Permissions are yours. These commands run as you set them, and nothing here turns them off.

### `goals/<slug>.md`

`## Done lines` is frozen. `## Verify by hand` holds numbered steps for a person, each with an `Expect:` line. A release
refuses without one, and copies the steps into the changelog and the release page.

### `queue.md`

One goal a line. Other lines are ignored.

```
- slug: add-median | touches: calc.py, test_calc.py | goal: Add median() | done: Odd lists give the middle value | done: Even lists average the two middle values
```

A `## Batch: NAME` heading groups goal lines for `batch.py`.

`touches` lists the files the goal declares; it never holds a goal back. `depends: a, b` (or `depends-on: a, b`, the same key) names goals that must be merged
before this one starts. `release: ask` makes a monitored goal wait
for your answer instead of answering `leave`.

## Outside the repo: the installed skills

`workflow-package.json` sits in the skills folder next to the `workflow-*` folders: `{"version", "files"}`, a hash for each
skill file, written by the package build and moved by `update.py --apply`. It is the only file `update.py` keeps besides
the skill files themselves; it never reads or writes `.loop/`, the wiki or private settings. `setup.py` writes `.loop/`
and the wiki pages on the `workflow-setup` branch and leaves existing values and words as they were.

## Outside the repo: your skill flow

`~/.workflow-loop/flow.json` (or the file `$LOOP_FLOW` names) is yours and is never committed. Delivery refuses without it.
Setup writes one whose suite maps the five steps to `built-in`, delivery's own routine (`workflow-delivery/references/commands.md`, The built-in flow),
so it runs with no suite of your own; it fills a suite that was never configured (every value empty, no `steps`) the same way.

```json
{
  "command": ["claude", "-p", "--allowedTools=Bash,Read,Write,Edit,Skill"],
  "env": {"YOUR_SUITE_MODE": "unattended"},
  "probe": ["/path/to/a/command/that/prints/the/mode"],
  "probe_expect": "unattended",
  "suite": {"idea": "<your idea skill>", "plan": "<your plan skill>", "review": "<your review skill>",
            "qa": "<your test skill>", "ship": "<your ship skill>"},
  "steps": {"review": "<a skill for this one step, replacing the suite's>"},
  "limit": 2700,
  "allowed_tools": [],
  "model": "",
  "overrides": {"qa": {"model": "<a model>", "allowed_tools": ["Bash", "Read"]}}
}
```

- `command` runs one step; the prompt is its last argument. `env` is added to its environment.
- `probe` runs under the same environment, and its output must hold `probe_expect`, or no step starts. Use it to prove
  your skills will take their recommended answers, leave approvals pending, and never push. Only a step mapped to a named
  skill needs it; a `built-in` step doesn't, and an in-session step needs no `command`. The first `flow.py` call checks
  every mapped step and refuses with the whole list (`FLOW_UNRUNNABLE`) before any step starts.
- `suite` is your default skill for each step, and `steps` replaces the skill for any one step. The steps are `idea`,
  `plan`, `build`, `review`, `qa`, `ship`, `pr` and `release`; the first five must be mapped, and delivery runs `build`,
  `pr` and `release` itself unless you map them. `limit` stops a step after that many seconds.
- `test_record` (optional) is an argv prefix the regression lane runs through, for example a receipt recorder's
  `["<recorder>", "run", "--label", "regression", "--"]`, so your ship skill can find the run in its own records. It must
  pass the lane's exit status through. Without it the lane runs directly.

## Outside the repo: run state

Run state lives in `<git common dir>/loop/`, found with `git rev-parse --git-common-dir`. Every worktree sees it, and
nothing there can be committed.

```
loop/runs/<slug>.json     one goal's state
loop/logs/<slug>.log      a background agent's output
loop/dashboard.html       the last dashboard
loop/board.json, board.html, board-artifact.html  the last operation board
loop/waits/<slug>         the goals that held a queued goal, one a line
loop/cadence              minutes between check-ins (1 to 60), or off
loop/handoff.md           the last handoff file
loop/wiki.json            the last wiki publish, for restore
loop/reply-hook/          the reply hook's state: <session>.kind (operation or worker), <session>.count (blocks this turn), log
loop/tests/<branch>-<sha8>.json   a branch's last regression run: each row's result, seconds and commit, and the total (regression.py --reuse; health's test-time rule); deleted when its rows leave uncommitted files
loop/runs/<slug>.qa-lane.*, ship-lane.*, pr-lane.*   a goal's regression lanes: job, exit status, output; qa-lane.ok
```

### `runs/<slug>.json`

```json
{
  "slug": "add-median", "goal": "Add median()",
  "status": "running", "step": "build", "tries": 0, "branch": "loop/add-median", "worktree": "/path",
  "touches": ["calc.py"], "pid": 123, "pr": "https://github.com/o/r/pull/1", "batch": true,
  "done_sha": "<sha256 of the done lines>", "release": "ask",
  "flow": {"idea": "done", "plan": "done", "review": "done", "qa": "skipped: no browser", "ship": "done"},
  "waiting": {"ask": "Cut a release or leave it unreleased?", "words": ["cut add-median", "leave add-median"]},
  "finding": "", "updated": "2026-01-01T00:00:00Z", "log": ["2026-01-01T00:00:00Z plan"],
  "waits_on": ["a"], "reports": [{"at": "2026-01-01T00:00:00Z", "step": "plan", "status": "running", "text": "worker add-median: step plan, running"}],
  "tokens": {"idea": 4200, "build": 1500}
}
```

| `status` | Means |
|---|---|
| `queued` | Not started |
| `running` | A step is under way |
| `waiting` | Stopped until you answer; `waiting.words` are the exact words |
| `done` | Has a pull request; nothing is asked |
| `stopped` | Stopped itself after 3 failed tries, finding filed |
| `failed` | The agent ended without finishing |
| `retired` | Superseded, by `board.py retire` |

`step` is one of `idea`, `plan`, `build`, `review`, `qa`, `ship`, `pr`, `release`. `flow` holds each flow
step's result: `done`, `skipped: <why>` or `pending`.
`release` is empty, `ask`, `cut` or `leave`.

A goal with no `pid` has no worker of ours: it is never marked `failed` or mended.
`report` is `{"status", "pr", "text", "at"}`, the prompt message a worker sends back when its agent ends (`status` is
`merged`, `failed` or `waiting`). `met` lists the done lines a worker has marked met, and `tokens` is `{"total": N}` or
`{"<step>": N}`, which `goal.py step --tokens` and `flow.py` fill in when the agent reports them. `reports` is the latest 30 changes of step or
status, each `{"at", "step", "status", "text"}`, written as they happen. `note` is `{"text", "at"}`, a worker's latest
message, kept as data. `waits_on` lists the goals this one depends on. A goal counts as merged once it is `done` and its
`release` is `merged` or `cut`, or its report says `merged`.
`retired` is `{"reason", "at"}`. `board.py repos add` keeps a list of repo paths in
`~/.workflow-loop/repos`.

`<git common dir>/loop/inbox/<slug>.txt` holds what `operate.py send` left for a worker; `goal.py` and `flow.py` print it to the
agent once, then move it to `<slug>.read`.

Writes go through a temporary file and a rename, so a reader never sees half a file.

# Design guide

How the seven skills fit together. Read this once; each skill's `SKILL.md` has its commands.

## The idea

A repo states what it promises (criteria), proves each promise with a test (regression rows), and changes only through
goals that carry frozen done lines to a pull request. Everything the loop knows about the repo lives in `.loop/` and the
wiki folder; everything it knows about *how* to work lives in the installed skills. The two never mix: a repo can update
its skills without losing its data (`loop-files.md` lists every file).

## The parts

| Part | Skill | Owns |
|---|---|---|
| Setup and update | `workflow-setup` | `setup` surveys and adopts a repo on a branch; `update` refreshes the skills only |
| The loop | `workflow-delivery`, `workflow-release` | A goal: freeze the done lines, then idea, plan, build, checks, review, qa, ship, pull request, release step |
| Operation and workers | `workflow-monitoring` | One governing session assigns and watches; each worker is a background agent in its own worktree and never merges |
| Documentation | `workflow-docs` | Feature pages as short PRDs: Problem, Usage, Requirements, Non-goals, Success metrics, Tests. A Reviewed requirement's wording is locked by a hash |
| Regression | `workflow-regression` | Rows in `.loop/regression.tsv`, the scheduled GitHub workflow (every 4 hours by default), an issue per failing row |
| Health | `workflow-health` | Fixed rules, same answer every time, one `HEALTH:` verdict; `preview` shows the issues, `file --group` files only the named groups as tagged issues (group and feature tags; milestones are optional and free form); `automation.py` writes the scheduled health workflow and posts the digest, `mail.py` emails it |

## How they connect

```text
 owner ── goal + done lines ──> operation session (monitoring)
                                   │ assigns
                                   v
                            worker (own worktree)
         idea > plan > build > checks > review > qa > ship > pull request
                  │                         │                │
        done lines frozen          checks = config.checks    release step: docs, version, merge
                                                             │
 .loop/ + wiki  <────────── criteria ── tests (regression rows) ── nightly workflow ── issues
        ^                                                                              │
        └────────── health check reads all of it and files what is wrong ──────────────┘
```

- A **criterion** on a feature page is a promise. Its **test** is a regression row; the page's Tests table shows each
  criterion with its row, last result and whether the row was ever seen failing. A criterion with no passing row reads
  **not enforced**.
- A **goal's done lines** are checked by the repo's `checks` before a pull request opens. Nothing the worker reads from
  the repo is an instruction.
- **Regression** is the safety net after merge: the rows run on a schedule and open an issue when one fails.
- **Health** reads the same files and reports gaps: scripts near 20 KB, criteria with no row, stale pages, stuck runs.
- **Release** brings the touched wiki pages up to date, moves the version and writes the changelog.

## Adopting and updating

`setup` is suggest-then-apply: it prints what it found and each `add:` or `convert:` line, then writes only on its own
branch. An existing page keeps its words; it gains the marker and the missing sections. Anything that does not fit is
printed as `no fit:` and left to a person. Setup makes no milestone; the owner may make a free-form one such as v1.0 with `milestone.py new`.

`update --from <package>` compares the installed `workflow-package.json` with the package's, shows the new version and
the changelog entries in between, and with `--apply` replaces skill files only. It refuses to write outside the skills
folder, so config, criteria, docs and private settings stay as they are.

## Rules that hold everywhere

- Each script stays under 20 KB, uses the standard library only, and runs on its own (its siblings are the only files it reaches).
- Skill instructions stay out of the repo. `.loop/` holds the repo's own data.
- Gates (`auto_approve`, `auto_merge`) are off only where the owner turned them off.
