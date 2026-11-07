# agent-workflow-template

A small agentic workflow you can add to any repo. You state a goal and the checks that prove it's done. A background
agent takes it through your own skill suite's flow, unattended: your idea, plan, review, test and ship skills, with
frozen done lines and the repo's checks around them. You review the pull request. One session governs and the others
build.

**Delivery needs a configured skill suite.** You bring the skills; a private file outside the repo,
`~/.workflow-loop/flow.json`, names them and how to run them in their own unattended mode. With no flow file, delivery
refuses with one line saying how to set it. See [the file contract](skills/loop-files.md).

**Status: early. Copy the `skills/` folders into your agent's skills folder, or run `dev/install-local.sh` for Claude
Code. No marketplace listing yet.** See the [wiki](docs/wiki/Home.md) for the features and the
[roadmap](docs/ROADMAP.md).

## What it aims to be

- **Light:** Markdown instructions and a few small scripts, with no engine to run.
- **Yours:** delivery wraps the skill suite you already use instead of adding its own design, review or release steps.
- **Governed:** the session you talk to never builds. It starts background agents, shows what waits on you, and keeps a
  dashboard.
- **Checkable by you:** every pull request says how to verify it by hand, and your wiki stays in step with the code.
- **Not tied to one agent:** built for Claude Code and Codex first, then other agents that read `SKILL.md`.

## Commands

Each wiki page has a chart for every command, with a status line saying what's proven. Most of these have run on a toy
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

Every goal runs the same flow: freeze the done lines, then your idea skill, your plan skill, the build, the checks, your
review skill, your test skill and your ship skill, with the checks after each step that changes files, then the pull
request. Each skill runs only after a probe proves its unattended mode, takes its recommended answers, and leaves
anything only you can decide under Waiting on you. Nothing is approved for you. The ship skill never pushes in that
mode, so delivery opens the pull request itself, with each step's result in its body.

See where things stand, or pick up a failed goal:

```text
/workflow-monitoring report
/workflow-monitoring dashboard
/workflow-monitoring resume <slug>
```

`mend` and `resume_on_limit` in `.loop/config.json` let `watch` give a failed goal one fresh agent, and continue after a
usage limit. Both are off until you turn them on. Background agents need the tools you allow in `agent_command`.

Run an operation session that follows everything and keeps a progress board (see
`skills/workflow-monitoring/references/operation.md`):

```text
python3 skills/workflow-monitoring/scripts/board.py board
python3 skills/workflow-monitoring/scripts/board_page.py
python3 skills/workflow-monitoring/scripts/board.py cadence 10
python3 skills/workflow-monitoring/scripts/board.py repos add ../other-repo
python3 skills/workflow-monitoring/scripts/watch.py go "<goal>" --done "<line>" --session
```

`board.py board` writes `board.json` and prints what changed. `board_page.py` then draws `board.html` and
`board-artifact.html` from it.

An operation session only assigns and watches. It puts goals in a named batch, and each goal runs in its own
background process or session:

```text
python3 skills/workflow-monitoring/scripts/batch.py add nightly --goal "<goal>" --done "<line>"
python3 skills/workflow-monitoring/scripts/batch.py start nightly
python3 skills/workflow-monitoring/scripts/batch.py status nightly
```

Keep tests visible and enforced:

```text
/workflow-regression seed
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

With `"criteria": true` in the config, `check` also holds the wiki to a contract: the feature pages plus Home, criteria
with a stage that each have regression rows, a chart and status line for every command, and no script file names.

Every goal has a `Verify by hand` section: steps you can follow to see the change work, each with what to expect. The
pull request refuses to open without one. A release, if you want one, is your ship skill's and yours: nothing here
publishes a release or merges.

## Getting started

From install to one finished goal.

1. **Install.** Run `dev/install-local.sh`. It links each `skills/workflow-*` folder into `~/.claude/skills` (or
   `$CLAUDE_SKILLS_DIR`) and prints `LINKED <name>`. It skips a name that is already a real folder. For another agent,
   copy the `skills/` folders into its skills folder.
2. **Set up your repo.** Run `/workflow-setup`. It writes `.loop/config.json`, `.loop/queue.md` and `.loop/findings.md`
   on a branch called `workflow-setup`. Preview with `python3 scripts/setup.py --dry-run`, using the path to the skill's
   folder. Then run each command in `checks` once and fix or add commands until they prove the repo works, allow the
   tools a background agent needs in `agent_command` (for example
   `["claude", "-p", "--allowedTools=Bash,Read,Write,Edit"]`; you choose the list), and review and merge the branch
   yourself. The other skills read the config from the base branch.
3. **Start a goal.** From the main checkout, on the base branch:
   `/workflow-monitoring go "add result caching" --done "repeat searches are served from the cache"`. Done lines are
   frozen once the goal starts, so make each one provable before the pull request, by the checks or by what a person
   can see (see [Delivery](docs/wiki/Delivery.md)). Set up your skill flow first, in `~/.workflow-loop/flow.json`.
4. **Watch it.** `/workflow-monitoring watch` starts queued goals in their own worktrees, prints what changed, and ends
   with what waits on you. Use `report` for a snapshot.
5. **Answer and review.** Answer what waits on you, in the exact words `watch` prints. The goal ends at a pull request:
   review and merge it yourself; nothing here merges.

## File reference

In the repo:

| File | Holds |
|---|---|
| `.loop/config.json` | Base branch, checks, agent commands, risky paths, wiki folder |
| `.loop/queue.md` | Goals to run, one line each |
| `.loop/goals/<slug>.md` | One goal: frozen done lines, plan, verify steps |
| `.loop/findings.md` | Open findings |
| `.loop/docs.tsv` | Each wiki page and the paths it describes |
| `.loop/regression.tsv` | Test rows |
| `.loop/regression-known.tsv` | Rows expected to fail, with a reason |
| `docs/wiki/` | Wiki pages, each starting with `<!-- workflow-docs -->` |

Outside the repo, run state lives in `<git common dir>/loop/`: `runs/<slug>.json`, `logs/<slug>.log`,
`dashboard.html`, `wiki.json`, `board.json`, `board.html`, `board-artifact.html`, `cadence` (minutes between
check-ins, or `off`) and `handoff.md`. Nothing there is committed. `board.py repos add` keeps a list of repo paths in `~/.workflow-loop/repos`, and
`~/.workflow-loop/flow.json` names your skill flow.

In this template: `skills/` (the six skills; the full contract is `skills/loop-files.md`), `dev/` (install, package and
toy tests), `listing.json`, `VERSION`, `DECISIONS.md`, `FINDINGS.md`, `docs/ROADMAP.md` and `LICENSE`.

## License

MIT. See [LICENSE](LICENSE).
