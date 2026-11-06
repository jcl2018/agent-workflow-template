# agent-workflow-template

A small agentic workflow you can add to any repo. You state a goal and the checks that prove it's done. An agent plans
and builds it, a fresh agent that didn't do the work judges it, and you review the pull request. One session can run and
watch many goals at once.

**Status: early. Install by copying the `skills/` folders; no listing yet.** See the [roadmap](docs/ROADMAP.md).

## What it aims to be

- **Light:** Markdown instructions and a few small scripts, with no engine to run.
- **Adjustable:** each goal runs at a level, from `quick` to `full`, so small changes skip the heavy steps.
- **Parallel:** one session starts the others, shows what's waiting on you, and keeps a dashboard.
- **Not tied to one agent:** built for Claude Code and Codex first, then other agents that read `SKILL.md`.

## Commands

All of these have run on a toy repo, except the `full` level and `cut` against a real GitHub repo, which are untested. They may change while the first version settles. The examples use Claude Code. In other agents, you
can ask in plain words, such as "start a goal to add result caching".

Set up a repo once:

```text
/workflow-setup
```

Try an idea, then build it. `poc` writes nothing and ends with a `go` line you can paste:

```text
/workflow-delivery poc "should we cache search results?"
/workflow-delivery go "add result caching" --level quick
```

The level sets how much process a goal gets:

| Level | Steps | Use it for |
|---|---|---|
| `quick` | Plan, build, checks | Small, low-risk changes |
| `standard` | Short design, plan, build, checks, one fresh judge | Most work |
| `full` | Adds a design review before the build | Risky or large changes |

Run and watch many goals from one session:

```text
/workflow-monitoring start
/workflow-monitoring report
/workflow-monitoring dashboard
/workflow-monitoring resume
```

Release the work, or leave it unreleased for now:

```text
/workflow-release cut
/workflow-release leave
```

`cut` creates a draft GitHub release for you to publish. Nothing merges or publishes without you.
