# agent-workflow-template

A small agentic workflow you can add to any repo. You state a goal and the checks that prove it's done. An agent plans
and builds it, a fresh agent that didn't do the work judges it at levels 1 and 2, and you review the pull request. One
session governs and the others build.

**Status: early. Copy the `skills/` folders into your agent's skills folder, or run `dev/install-local.sh` for Claude
Code. No marketplace listing yet.** See the [wiki](docs/wiki/Home.md) for the five features, the
[roadmap](docs/ROADMAP.md) and the [release page](../../releases).

## What it aims to be

- **Light:** Markdown instructions and a few small scripts, with no engine to run.
- **Adjustable:** each goal runs at a level, from `0` to `2`, so small changes skip the heavy steps.
- **Governed:** the session you talk to never builds. It starts background agents, shows what waits on you, and keeps a
  dashboard.
- **Checkable by you:** every release says how to verify it by hand, and your wiki stays in step with the code.
- **Not tied to one agent:** built for Claude Code and Codex first, then other agents that read `SKILL.md`.

## Commands

Each wiki page has a chart for every command, with a status line saying what's proven. Most of these have run on a toy
repo, and `go`, `publish` and `cut` have also run on a real repo. `poc` has no test, and level 2 has run only on a
toy repo. They may change while the first version settles. The examples use Claude Code. In other agents, you can ask
in plain words, such as "start a goal to add result caching".

Set up a repo once:

```text
/workflow-setup
```

Try an idea, then start it. `poc` writes nothing and ends with a `go` line and a queue line:

```text
/workflow-delivery poc "should we cache search results?"
/workflow-monitoring go "add result caching" --done "repeat searches are served from the cache"
/workflow-monitoring watch
```

**One session governs, and the others build.** `go` starts a background agent in its own worktree, at every level, and
`watch` keeps goals moving until nothing is left. You stay in one session and review pull requests.

The level sets how much process a goal gets:

| Level | Steps | Use it for |
|---|---|---|
| `0` | Design, plan, build, checks | The default: most work |
| `1` | Adds one fresh judge after the build | Work worth a second look |
| `2` | Adds a design review before the build | Risky or large changes |

Changes to CI, auth or data run at level `1` at least.

At level 2, `design.py SLUG` starts the design review. With a skill named in the private file
`~/.workflow-loop/design-skill` or the variable `LOOP_DESIGN_SKILL` (never stored in the repo), an agent with tools runs
that skill in the worktree, detached, because it needs the repo and can take many minutes. It runs `design_command` from
`.loop/config.json`, or `agent_command`, so allow what the skill needs. It is told to ask nothing and take the
recommended answer at every gate. Run `design.py` again until it prints `NEXT`, the `goal.py` line that records the
verdict. The `SKILL:` line says how much ran. With no skill, or the skill missing, `NEXT` is the built-in review, which
has no tools and reads only the goal file. `goal.py judge --design` refuses while a skill can run. The output says which
ran, and the pull request says whether the skill ran `full` or `condensed`. A condensed pass still counts as a pass.

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

An operation session only assigns and watches. It puts POCs and goals in a named batch, and each line runs in its own
background process or session:

```text
python3 skills/workflow-monitoring/scripts/batch.py add nightly --poc "<question>"
python3 skills/workflow-monitoring/scripts/batch.py add nightly --goal "<goal>" --done "<line>"
python3 skills/workflow-monitoring/scripts/batch.py start nightly
python3 skills/workflow-monitoring/scripts/batch.py status nightly
python3 skills/workflow-monitoring/scripts/batch.py promote <poc-slug>
```

A POC runs read-only and saves its answer and `go` line outside the repo. Promote one only when you say so.

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

With `"criteria": true` in the config, `check` also holds the wiki to a contract: five feature pages plus Home, criteria
with a stage that each have regression rows, a chart and status line for every command, and no script file names.

Release the work, or leave it unreleased for now:

```text
/workflow-release cut <slug>
/workflow-release leave <slug>
```

Every goal has a `Verify by hand` section: steps you can follow to see the change work, each with what to expect. `cut`
refuses without one, and refuses if a wiki page is stale or a criterion's regression row is missing or failing. It then
creates a draft GitHub release that carries those steps and the docs that changed, for you to publish. After a cut, the
agent publishes the wiki. No release is published and nothing merges without you.

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
   frozen once the goal starts, so make each one provable before the pull request, from the diff, the goal file and the
   check results (see [Delivery](docs/wiki/Delivery.md)). The level is `0` unless you add `--level`, and only levels 1
   and 2 get a fresh judge. To try an idea first, use `/workflow-delivery poc "<question>"`, which writes nothing.
4. **Watch it.** `/workflow-monitoring watch` starts queued goals in their own worktrees, prints what changed, and ends
   with what waits on you. Use `report` for a snapshot.
5. **Review.** The goal ends at a pull request. A monitored goal answers `leave` by itself, unless you started it with
   `--release ask`; then it waits for `cut <slug>` or `leave <slug>` (see [Release](docs/wiki/Release.md)). With
   `"release_auto": true`, it decides from its diff and may cut a draft instead. Answer before you merge, because `cut`
   commits on the goal's branch. Review and merge the pull request yourself; nothing here merges.

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
`dashboard.html`, `wiki.json`, `board.json`, `board.html`, `board-artifact.html`, `pocs/`, `cadence` (minutes between
check-ins, or `off`) and `handoff.md`. Nothing there is committed. `board.py repos add` keeps a list of repo paths in `~/.workflow-loop/repos`.

In this template: `skills/` (the six skills; the full contract is `skills/loop-files.md`), `dev/` (install, package and
toy tests), `listing.json`, `VERSION`, `DECISIONS.md`, `FINDINGS.md` and `docs/ROADMAP.md`.
