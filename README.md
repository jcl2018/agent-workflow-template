# agent-workflow-template

A small agentic workflow you can add to any repo. You state a goal and the checks that prove it's done. An agent plans
and builds it, a fresh agent that didn't do the work judges it, and you review the pull request. One session can run and
watch many goals at once.

**Status: early. Nothing is installable yet.** See the [roadmap](docs/ROADMAP.md).

## What it aims to be

- **Light:** Markdown instructions and a few small scripts, with no engine to run.
- **Adjustable:** each goal runs at a level, from `quick` to `full`, so small changes skip the heavy steps.
- **Parallel:** one session starts the others, shows what's waiting on you, and keeps a dashboard.
- **Not tied to one agent:** built for Claude Code and Codex first, then other agents that read `SKILL.md`.
