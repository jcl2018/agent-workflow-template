<!-- workflow-docs -->
# agent-workflow-template

A small agentic workflow for any repo: you state a goal and the checks that prove it, an agent builds it, a fresh agent
judges it, and you review the pull request. One session governs and the others build.

## Features

| Feature | Skill | Page |
|---|---|---|
| Set up a repo | `workflow-setup` | [Getting started](Getting-started) |
| Goal to judged pull request | `workflow-delivery` | [Delivery](Delivery) |
| Run and watch many goals | `workflow-monitoring` | [Monitoring](Monitoring) |
| Keep the wiki in step with code | `workflow-docs` | [Documentation](Documentation) |
| Keep tests visible and enforced | `workflow-regression` | [Regression](Regression) |
| Cut a draft release or leave it | `workflow-release` | [Release](Release) |
| Where every file lives | all | [Files](Files) |

## What is proven

- The commands have run on a toy repo, except the `full` level (README, `dev/toy/test-*.sh`).
- `go`, `docs` and `cut` have also run on a real repo (README).
- The fresh judge failed two done lines for missing evidence on its first real run, correctly (FINDINGS.md).
- `dev/package.sh` refuses a package with one planted fault per rule (`dev/test-package.sh`).

## What is not proven

- The `full` level has not run.
- Agents other than Claude Code and Codex are untested; Kimi, Qwen and OpenCode are still to come (ROADMAP).
- There is no marketplace listing yet (README).
- Real repos differ from the toy: four-number versions, odd changelogs, tests outside `tests/`, slow pre-push hooks
  (FINDINGS.md).
- Commands may change while the first version settles (README).
