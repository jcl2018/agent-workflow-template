<!-- workflow-docs -->
# agent-workflow-template

A small agentic workflow for any repo: you state a goal and the checks that prove it, an agent builds it, a fresh agent
judges it, and you review the pull request. One session governs and the others build. To install it and run a first
goal, or to see where every file lives, read the [README](https://github.com/jcl2018/agent-workflow-template#readme).

## Features

Each feature page has a Summary, its Commands, draft Criteria for the owner to approve, and what enforces each one.

| Feature | Skill | Page |
|---|---|---|
| Goal to judged pull request | `workflow-delivery` | [Delivery](Delivery) |
| Keep the wiki in step with code | `workflow-docs` | [Documentation](Documentation) |
| Run and watch many goals | `workflow-monitoring` | [Monitoring](Monitoring) |
| Keep tests visible and enforced | `workflow-regression` | [Regression](Regression) |
| Cut a draft release or leave it | `workflow-release` | [Release](Release) |

Setting up a repo (`workflow-setup`) is covered under Getting started in the README.

## What is proven

- "A fresh judge only sees the goal file, the diff and the check output. On the first real run it failed two done lines
  for missing evidence, correctly." (FINDINGS.md)
- "`goal.py` counts a failed fresh-judge verdict as a try, the same as a failed check." (DECISIONS.md)
- "`cut` refuses in a monitored batch unless `--user` is passed; the skill says to pass it only on the human's own
  words." (DECISIONS.md)
- "`report` left out queued goals that were ready to start. It now lists them." (FINDINGS.md)
- Named toy tests: `dev/toy/test-goal.sh`, `dev/toy/test-board.sh`,
  `dev/toy/test-docs.sh`, `dev/toy/test-release.sh`, `dev/toy/test-regression.sh`.

## What is not proven

- "Real repos differ from the toy: four-number versions, changelogs with bracket headings and an intro paragraph, tests
  outside `tests/`, a wiki with pages from another tool, and a pre-push hook that takes minutes." (FINDINGS.md)
- "Several goals pushing at once can fail with a bare git error, and a plain re-push works. `goal.py pr` retries
  twice." (FINDINGS.md)
- "Scripts are close to the 20 KB limit: `goal.py` 20,474 bytes, `watch.py` 19,928. The next feature needs a new
  script." (FINDINGS.md)
- "Codex's `workspace-write` sandbox blocks writes to `.git` and outside the workspace." (FINDINGS.md)

## Gaps for the owner

- The timed check-in loop (`board.py cadence`, then `watch.py watch --once` and `board.py board` on each wait) has not
  fired on its timer. No finding or decision records a run of it, and `dev/toy/test-board.sh` uses fixtures.
- Level 2 has not run, on a toy repo or a real one (docs/ROADMAP.md).
