<!-- workflow-docs -->
# agent-workflow-template

A small agentic workflow for any repo: you state a goal and the checks that prove it, an agent builds it, a fresh agent
judges it at levels 1 and 2, and you review the pull request. One session governs and the others build. To install it
and run a first goal, or to see where every file lives, read the
[README](https://github.com/jcl2018/agent-workflow-template#readme).

## Features

Each feature page has a Summary, its Commands with a stage chart for each, its Criteria with their stages and test
count, and what enforces each one. Criteria marked Unreviewed have not been reviewed by the owner.

| Feature | Skill | Page |
|---|---|---|
| Goal to pull request | `workflow-delivery` | [Delivery](Delivery) |
| Keep the wiki in step with code | `workflow-docs` | [Documentation](Documentation) |
| Check the repo's health | `workflow-health` | [Health](Health) |
| Milestones per feature, and a Backlog | `workflow-health` | [Milestones](Milestones) |
| Run and watch many goals | `workflow-monitoring` | [Monitoring](Monitoring) |
| Keep tests visible and enforced | `workflow-regression` | [Regression](Regression) |
| Cut a draft release or leave it | `workflow-release` | [Release](Release) |

Setting up a repo (`workflow-setup`) is covered under Getting started in the README.

## Reading the charts

Each chart shows a command's stages, with amber at each stop for the owner. Under it, `Status:` puts every stage in one
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
goals, including one real `cut` to a draft release. This repo has since had its own real `cut`, v0.1.1. Neither repo shows a level 2 run, a regression workflow run in CI, a
`release_auto` run, or a batch with a real agent. Records older than these goals may be gone, so "not on record" doesn't mean it never happened.

## What is proven

- "A fresh judge only sees the goal file, the diff and the check output. On the first real run it failed two done lines
  for missing evidence, correctly." (FINDINGS.md)
- A failed fresh-judge verdict counts as a try, the same as a failed check (DECISIONS.md).
- "`cut` refuses in a monitored batch unless `--user` is passed; the skill says to pass it only on the human's own
  words." (DECISIONS.md)
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
- A pull request merged just before `cut` gives an empty changelog entry (FINDINGS.md).

## Gaps for the owner

- The timed check-in loop (`cadence`, then `watch --once` and `board` on each wait) has not fired on its timer. No
  finding or decision records a run of it, and its toy test uses fixtures.
- Level 2 has run only on a toy repo, and its design skill didn't finish every phase there (docs/ROADMAP.md).
