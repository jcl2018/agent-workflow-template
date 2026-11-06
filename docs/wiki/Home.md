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

- The fresh judge failed two done lines for missing evidence on its first real run, correctly (FINDINGS.md).
- A failed fresh-judge verdict counts as a try, the same as a failed check (DECISIONS.md).
- `cut` refuses in a monitored batch unless `--user` is passed (DECISIONS.md, `dev/toy/test-release.sh`).
- The goal, monitoring, regression, docs and release scripts each have a toy-repo test (`dev/toy/test-*.sh`).
- `dev/package.sh` refuses a package with one planted fault per rule (`dev/test-package.sh`).

## What is not proven

- Real repos differ from the toy: four-number versions, odd changelogs, tests outside `tests/`, slow pre-push hooks
  (FINDINGS.md).
- Several goals pushing at once can fail with a bare git error; `goal.py pr` retries twice (FINDINGS.md).
- Scripts are close to the 20 KB limit, so the next feature needs a new script (FINDINGS.md).
- Codex needs extra sandbox setup for a goal run (FINDINGS.md, `dev/toy/run-goal.sh`).
