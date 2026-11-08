# Loop files

The six workflow skills share this contract. Skill instructions never go in the repo. A repo holds only its own data.

## In the repo: `.loop/`

| File | Holds |
|---|---|
| `.loop/config.json` | Base branch, check commands, agent commands, risky paths |
| `.loop/queue.md` | Goals to run, one line each |
| `.loop/goals/<slug>.md` | One goal: done lines, plan, log |
| `.loop/findings.md` | Open findings, one line each |
| `.loop/docs.tsv` | Each wiki page and the paths it describes |
| `.loop/config.json` key `criteria` | `true` makes `docs.py check` enforce the criteria contract on the wiki pages; each regression row links to one criterion by its goal or id; a reviewed line ends with a hash of its text, and `docs.py check` fails if the text changes; `criteria.py render` makes each page's Tests table |
| `.loop/regression.tsv` | Each test row: id, level, command, goal, date seen failing |
| `.loop/regression-runs.tsv` | Each row's last run: id, PASS or FAIL, date; written by `regression.py run`, shown in the wiki Tests tables |
| `.loop/regression-known.tsv` | Rows expected to fail, with a reason; they don't block |

Wiki pages live in `docs/wiki/`. Each starts with the line `<!-- workflow-docs -->`, which marks it as safe to update.

### `config.json`

```json
{
  "base": "main",
  "checks": ["python3 -m unittest"],
  "agent_command": ["claude", "-p"],
  "parallel": 3,
  "risky_paths": ["^\\.github/", "(^|/)auth", "(^|/)migrations?/", "(^|/)(schema|data)\\b"],
  "version_file": "VERSION",
  "wiki_dir": "docs/wiki",
  "pr_bumps_version": false,
  "mend": false,
  "resume_on_limit": false
}
```

- `agent_command` runs a goal in the background; the prompt is its last argument.
- `require_checks` (default `true`): `false` with an empty `checks` list lets a pull request open with no checks.
- `auto_approve` (default `false`): `true` approves what a flow step leaves for the owner, logged as auto-approved.
- `auto_merge` (default `false`): `true` lets the release step's `merge.py` merge a goal's pull request.
- `pr_bumps_version` moves the last number of the version file on a goal's branch, for repos whose CI needs a bump.
- `mend` and `resume_on_limit` let `watch` restart a goal. `limit_wait`, `mend_wait` and `watch_interval` are optional, in seconds.
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

`touches` lists the files the goal declares; it never holds a goal back. `depends-on: a, b` names goals that must be merged
before this one starts. `release: ask` makes a monitored goal wait
for your answer instead of answering `leave`.

## Outside the repo: your skill flow

`~/.workflow-loop/flow.json` (or the file `$LOOP_FLOW` names) is yours and is never committed. Delivery refuses without it.

```json
{
  "command": ["claude", "-p", "--allowedTools=Bash,Read,Write,Edit,Skill"],
  "env": {"YOUR_SUITE_MODE": "unattended"},
  "probe": ["/path/to/a/command/that/prints/the/mode"],
  "probe_expect": "unattended",
  "steps": {"idea": "<your idea skill>", "plan": "<your plan skill>", "review": "<your review skill>",
            "qa": "<your test skill>", "ship": "<your ship skill>"},
  "limit": 2700
}
```

- `command` runs one step; the prompt is its last argument. `env` is added to its environment.
- `probe` runs under the same environment, and its output must hold `probe_expect`, or no step starts. Use it to prove
  your skills will take their recommended answers, leave approvals pending, and never push.
- `steps` names the skill for each step. `limit` stops a step after that many seconds.

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
```

### `runs/<slug>.json`

```json
{
  "slug": "add-median", "goal": "Add median()",
  "status": "running", "step": "build", "tries": 0, "branch": "loop/add-median", "worktree": "/path",
  "touches": ["calc.py"], "pid": 123, "pr": "https://github.com/o/r/pull/1", "batch": true,
  "done_sha": "<sha256 of the done lines>", "checks": "pass", "release": "ask",
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
| `done` | Has a pull request and its checks hold; nothing is asked |
| `stopped` | Stopped itself after 3 failed tries, finding filed |
| `failed` | The agent ended without finishing |
| `retired` | Superseded, by `board.py retire` |

`step` is one of `idea`, `plan`, `build`, `checks`, `review`, `qa`, `ship`, `pr`, `release`. `flow` holds each flow
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
