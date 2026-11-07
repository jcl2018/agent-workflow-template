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
| `.loop/config.json` key `criteria` | `true` makes `docs.py check` enforce the criteria contract on the wiki pages; each regression row links to one criterion by its goal or id; a reviewed line ends with a hash of its text, and `criteria.py sync` returns it to Unreviewed if the text changes |
| `.loop/regression.tsv` | Each test row: id, level, command, goal, date seen failing |
| `.loop/regression-known.tsv` | Rows expected to fail, with a reason; they don't block |

Wiki pages live in `docs/wiki/`. Each starts with the line `<!-- workflow-docs -->`, which marks it as safe to update.

### `config.json`

```json
{
  "base": "main",
  "checks": ["python3 -m unittest"],
  "agent_command": ["claude", "-p"],
  "judge_command": ["claude", "-p", "--tools", ""],
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
- `design_command`, optional, runs a level 2 design skill; it defaults to `agent_command`. The prompt is its last argument.
- `judge_command` reads its prompt on standard input and runs in an empty temporary folder.
- An empty `judge_command` means no headless judge: print the pack for a fresh agent instead.
- `pr_bumps_version` moves the last number of the version file on a goal's branch, for repos whose CI needs a bump.
- `mend` and `resume_on_limit` let `watch` restart a goal. `limit_wait`, `mend_wait` and `watch_interval` are optional, in seconds.
- Permissions are yours. These commands run as you set them, and nothing here turns them off.

### `goals/<slug>.md`

`## Done lines` is frozen. `## Verify by hand` holds numbered steps for a person, each with an `Expect:` line. A release
refuses without one, and copies the steps into the changelog and the release page.

### `queue.md`

One goal a line. Other lines are ignored.

```
- slug: add-median | level: 1 | touches: calc.py, test_calc.py | goal: Add median() | done: Odd lists give the middle value | done: Even lists average the two middle values
```

A `## Batch: NAME` heading groups lines for `batch.py`; `- poc: SLUG | question: Q` is a POC line, which `watch.py` ignores; `session: yes` after the slug runs it in a visible session.

`level` defaults to `0` (the old names are refused). `touches` lists the files the goal declares. `release: ask` makes a monitored goal wait
for your answer instead of answering `leave`. `session: yes` marks a goal for a visible session.

## Outside the repo: run state

Run state lives in `<git common dir>/loop/`, found with `git rev-parse --git-common-dir`. Every worktree sees it, and
nothing there can be committed.

```
loop/runs/<slug>.json     one goal's state
loop/logs/<slug>.log      a background agent's output
loop/dashboard.html       the last dashboard
loop/board.json, board.html, board-artifact.html  the last operation board
loop/sessions.json        tracked sessions that have no goal record
loop/pocs/<slug>.md, .go    a finished POC's answer and its go line
loop/waits/<slug>         the goals that held a queued goal, one a line
loop/cadence              minutes between check-ins (1 to 60), or off
loop/handoff.md           the last handoff file
loop/wiki.json            the last wiki publish, for restore
```

### `runs/<slug>.json`

```json
{
  "slug": "add-median", "goal": "Add median()", "level": "1",
  "status": "running", "step": "build", "tries": 0, "branch": "loop/add-median", "worktree": "/path",
  "touches": ["calc.py"], "pid": 123, "pr": "https://github.com/o/r/pull/1", "batch": true,
  "done_sha": "<sha256 of the done lines>", "checks": "pass", "judge": "pass", "release": "ask",
  "waiting": {"ask": "Cut a release or leave it unreleased?", "words": ["cut add-median", "leave add-median"]},
  "finding": "", "updated": "2026-01-01T00:00:00Z", "log": ["2026-01-01T00:00:00Z plan"]
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

`step` is one of `design`, `design-review`, `plan`, `build`, `checks`, `judge`, `pr`, `release`.
`release` is empty, `ask`, `cut` or `leave`.

`external: true` marks a goal run in a visible session: no `pid`, and a missing process never marks it `failed`.
`note` is `{"text", "at"}`, a session's latest message, kept as data. `waits_on` lists the goals that held this one.
`retired` is `{"reason", "at"}`. `board.py take` sets `external` on a goal a session has taken over. `board.py repos add` keeps a list of repo paths in
`~/.workflow-loop/repos`.

Writes go through a temporary file and a rename, so a reader never sees half a file.
