# agent-workflow-template

A small agentic workflow you can add to any repo. You state a goal and the checks that prove it's done. An agent plans
and builds it, a fresh agent that didn't do the work judges it, and you review the pull request. One session governs
and the others build.

**Status: early. Copy the `skills/` folders into your agent's skills folder, or run `dev/install-local.sh` for Claude
Code. No marketplace listing yet.** See the [wiki](docs/wiki/Home.md), the [roadmap](docs/ROADMAP.md) and the
[release page](../../releases).

## What it aims to be

- **Light:** Markdown instructions and a few small scripts, with no engine to run.
- **Adjustable:** each goal runs at a level, from `minimum` to `full`, so small changes skip the heavy steps.
- **Governed:** the session you talk to never builds. It starts background agents, shows what waits on you, and keeps a
  dashboard.
- **Checkable by you:** every release says how to verify it by hand, and your wiki stays in step with the code.
- **Not tied to one agent:** built for Claude Code and Codex first, then other agents that read `SKILL.md`.

## Commands

All of these have run on a toy repo, except the `full` level. `go`, `docs` and `cut` have also run on a real repo. They may change while the first version settles. The examples use Claude Code. In other agents, you
can ask in plain words, such as "start a goal to add result caching".

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
| `minimum` | Build, checks | The default: fast work, using the agent's own planning |
| `quick` | Written plan, build, checks | Small changes you want a plan on record for |
| `standard` | Short design, plan, build, checks, one fresh judge | Most work |
| `full` | Adds a design review before the build | Risky or large changes |

Changes to CI, auth or data run at `standard` at least.

See where things stand, or pick up a failed goal:

```text
/workflow-monitoring report
/workflow-monitoring dashboard
/workflow-monitoring resume
```

`mend` and `resume_on_limit` in `.loop/config.json` let `watch` give a failed goal one fresh agent, and continue after a
usage limit. Both are off until you turn them on. Background agents need the tools you allow in `agent_command`.

Run an operation session that follows everything and keeps a progress board (see
`skills/workflow-monitoring/references/operation.md`):

```text
python3 skills/workflow-monitoring/scripts/board.py board
python3 skills/workflow-monitoring/scripts/board.py cadence 10
python3 skills/workflow-monitoring/scripts/board.py repos add ../other-repo
python3 skills/workflow-monitoring/scripts/watch.py go "<goal>" --done "<line>" --session
```

Keep tests visible and enforced:

```text
/workflow-regression seed
/workflow-regression sync
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

`publish` only adds or updates pages it wrote, and never deletes one. `restore` undoes the last publish.

Release the work, or leave it unreleased for now:

```text
/workflow-release cut
/workflow-release leave
```

Every goal has a `Verify by hand` section: steps you can follow to see the change work, each with what to expect. `cut`
refuses without one, and refuses if a wiki page is stale. It then creates a draft GitHub release that carries those
steps and the docs that changed, for you to publish. Nothing merges or publishes without you.
