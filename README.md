# loopkit

A small agentic workflow you can add to any repo. You state a goal and the checks that prove it's done. An agent plans
and builds it, a fresh agent that didn't do the work judges it, and you review the pull request.

**Status: early. Nothing is installable yet.** See the [roadmap](docs/ROADMAP.md).

## What it aims to be

- **Light:** Markdown instructions and a few shell scripts, with no engine to run.
- **Cheap on tokens:** small changes skip the heavy steps, and each step loads only what it needs.
- **Yours after install:** it writes a `.loop/` folder into your repo, which keeps working without this package.
- **Not tied to one agent:** built for Claude Code and Codex first, then other agents that read `SKILL.md`.
