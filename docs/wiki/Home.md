<!-- workflow-docs -->
# agent-workflow-template

A small agentic workflow for any repo: you state a goal and the checks that prove it, and a background agent takes it
through your own skill suite's flow, unattended, to a pull request you review. One session governs and the others build: `operate.py run` plans queued goals as a dependency graph and starts the workers. To install it
and run a first goal, or to see where every file lives, read the
[README](https://github.com/jcl2018/agent-workflow-template#readme). It's released under the MIT license. The last step of every goal, the release step (see [Delivery](Delivery)), also brings the wiki up to date and publishes it.


**This repo runs with no gates.** Its `.loop/config.json` turns off `require_checks`, with an empty `checks` list, and
turns on `auto_approve` and `auto_merge`. A pull request opens without any check passing. What the skills leave for the
owner is approved automatically and logged as auto-approved, in the goal's log and on the board. The release step then
merges the pull request into `main` by itself. The skills' own built-in refusals still apply, and the private-name leak
scan still guards every commit. The risk is plain: a broken or wrong change can reach `main` with nobody looking, and
the only check left is the regression workflow on GitHub, which reports and never blocks. A repo set up from this
template keeps every gate until its owner turns one off.

## Features

Each feature page is a Summary, its Criteria, and a Tests table of the regression rows that enforce them with their last
result and date. A criterion is Unreviewed or Reviewed with a date, and a Reviewed one's wording is locked. Command
detail and charts are in each skill's `references/` folder.

| Feature | Skill | Page |
|---|---|---|
| Goal to pull request, and release | `workflow-delivery`, `workflow-release` | [Delivery](Delivery) |
| Run and watch many goals, with the roadmap drawn as a dependency graph and a total time | `workflow-monitoring` | [Monitoring](Monitoring) |
| Keep the docs, milestones and release notes in step | `workflow-docs` | [Documentation](Documentation) |
| Keep tests visible and enforced | `workflow-regression` | [Regression](Regression) |
| Check the repo's health | `workflow-health` | [Health](Health) |
| Adopt a repo into this format | `workflow-setup` | [Setup](Setup) |

## Reading the charts

The charts in each skill's `references/` folder are read this way. Each chart shows a command's stages, with amber at each stop for the owner. Under it, `Status:` puts every stage in one
of three groups, `Stops for the owner:` names the stops, and `Proof:` says what the status rests on.

| Status | Means |
|---|---|
| Built and proven | A toy test passes on this stage, or a real run on this repo is on record |
| Built only | It exists, but no test exercises it and no real run is on record |
| Planned | Not built yet |

A toy test uses a throwaway repo and a stand-in for GitHub, so built and proven doesn't mean it has run on a real repo.
`Proof:` says when it hasn't. Real runs were read on 2026-11-06 from the run records of this repo and one other it
follows, plus their pull requests, releases and wikis. That second repo isn't named here. On this repo, eight real goals
reached a pull request, all at the level now called 1, and three publishes reached the wiki. The second repo ran ten
goals, including one real `cut` to a draft release. This repo has since had its own real `cut`, v0.1.1. Neither repo shows a regression workflow run in CI, a
or a batch with a real agent. Records older than these goals may be gone, so "not on record" doesn't mean it never happened.

## What is proven

- "`report` left out queued goals that were ready to start. It now lists them." (FINDINGS.md)
- Toy tests cover goals, the board, docs, criteria, releases and regression, each under `dev/toy/`.
- Codex ran a level 0 toy goal from design to pull request with no failed try (FINDINGS.md).
- The regression workflow passes on GitHub. Its first run failed 2 rows, and both are fixed (FINDINGS.md).

## What is not proven

- "Real repos differ from the toy: four-number versions, changelogs with bracket headings and an intro paragraph, tests
  outside `tests/`, a wiki with pages from another tool, and a pre-push hook that takes minutes." (FINDINGS.md)
- Several goals pushing at once can fail with a bare git error, and a plain re-push works; `pr` retries twice
  (FINDINGS.md).
- Some scripts are within a few hundred bytes of the 20 KB limit, so the next feature needs a new script
  (FINDINGS.md).
- "Codex's `workspace-write` sandbox blocks writes to `.git` and outside the workspace." (FINDINGS.md)

## Gaps for the owner

- The timed check-in loop (`cadence`, then `watch --once` and `board` on each wait) has not fired on its timer. No
  finding or decision records a run of it, and its toy test uses fixtures.
- The skill flow has run for real only up to the idea step, which waited for the owner as it should (docs/ROADMAP.md).
