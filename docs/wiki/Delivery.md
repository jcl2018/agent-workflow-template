<!-- workflow-docs -->
# Delivery

Milestone: https://github.com/jcl2018/agent-workflow-template/milestone/1

Review: **Unreviewed**

## Problem

Skill: `workflow-delivery`, with `workflow-release` as its last step. Takes one sentence to a pull request by running your own skill suite's flow unattended, with frozen done lines, a 3-try stop, review as the only gate and a manual verify section, then the release step runs the docs audit and refuses while it finds trouble (any page `docs.py check` calls stale, whether or not the goal touched its paths), runs the `routines` in `.loop/config.json`, merges where the repo allows it, bumps the version once, writes the CHANGELOG entry and a published GitHub release, and publishes the wiki. A failure is recorded as `release_error` and shows under Needs you.

Delivery needs a configured skill suite: a private file outside the repo, `~/.workflow-loop/flow.json`, names your skills and proves their unattended mode, and the repo never names them. A flow step can run with its own allowed tools and model (`overrides`), and `max_tries`, `step_limit` and `token_budget` in `.loop/config.json` set the try cap, the step time limit and a token cap, all read fresh each run (every setting is listed in `skills/workflow-setup/references/settings.md`). The ship step never pushes, so delivery's own `pr` does. A goal that fixes an issue or finding cannot open its pull request until its defect test exists, was seen failing, and passes. In an operation session `go` runs in a background agent, not in that session: goal steps (`step`, `check`, `record`, `pr`, `flow.py`) refuse outside a worker. The full regression suite runs once per goal, as the regression lane (`regression.py run land --reuse`): `flow.py qa` runs it in the background before the qa skill starts, through the flow file's optional `test_record` prefix (a receipt recorder, so your ship skill's own check can reuse the run), and `goal.py record SLUG qa` refuses until a qa lane passed on HEAD (`LANE_MISSING`). A failing or never-seen-failing row, or an unclean tree (`LANE_DIRTY`), fails the qa step before the skill runs. `flow.py ship` and `goal.py pr` run the same lane: on unchanged content it prints `REUSED` and runs no test, and after a commit or a base merge it reruns only the rows the change can affect. Before its pull request a goal merges the latest base branch and reruns the affected rows if that changed anything; only a real conflict costs it a try. A goal's step label changes when `flow.py` starts a step and moves on when `record` records it, so a finished step is never shown as current. `flow.py` runs a `claude` command with JSON output and records each step's tokens from it (input, output and cache-creation tokens, no cache reads), so the Cost rule and the status block show real numbers. Usage here is what you ask the agent, and each skill's `## Command map` names the routine behind it. Commands, flows and how-tos: `skills/workflow-delivery/references/commands.md` (which also keeps, word for word, the lane rules, step tokens (and how to report a step `flow.py` did not run), version and push retries and gate switches that `SKILL.md` points to, so it stays under 150 lines) and `skills/workflow-release/references/commands.md`. In a worker session, the default worker, `flow.py` starts no headless agent: it prints `IN SESSION` with the skill to invoke in that session and the reply path, then the `goal.py record` line once a reply written after that is there (a reply left by an earlier try is moved aside, never recorded again), and `goal.py record --in-session` records a step the goal's worker session ran, stamped "in session", refusing a goal whose run names no session; a headless agent runs a step only with no worker session. How deeply the plan and review steps run is the repo setting `review_depth`, `full` by default and read from the base branch, so a worker can't lower it: the step prompt asks for the skill's whole pipeline, every reply states `DEPTH: full` or `DEPTH: condensed` on a line of its own before its `STEP:` line, and record refuses a condensed plan or review under `full` (auto-approve included), a reply with no depth line, or a full one missing a private `full_markers` string from the flow file (the error never shows the string; a skipped step is held to neither). Each recorded step is stamped `(depth full)` or `(depth condensed)`, which the pull request body lists and the live board shows.

**This repo runs with no gates.** Its `.loop/config.json` turns on `auto_approve` and `auto_merge`. Review is the only gate: delivery runs no check step. What the skills leave for the
owner is approved automatically and logged as auto-approved, in the goal's log and on the board. The release step then
merges the pull request into `main` by itself. The skills' own built-in refusals still apply, and the private-name leak
scan still guards every commit. The risk is plain: a broken or wrong change can reach `main` with nobody looking, and
the only check left is the regression workflow on GitHub, which reports and never blocks. A repo set up from this
template keeps every gate until its owner turns one off.

## Usage

- "start a goal to add caching", or `/workflow-delivery go "goal" --done "line"`, freezes a goal and its done lines; from the operation session, `/workflow-monitoring go "goal" --done "line"` hands it to a background worker instead.
- `/workflow-delivery step SLUG STEP` runs the idea, plan, review, qa or ship step unattended until it stops printing `RUNNING`; `/workflow-delivery record SLUG STEP` then records it.
- A decision a step leaves for the owner shows under Issues on the live board until it is answered.
- `/workflow-delivery pr SLUG` merges the latest base branch, pushes and opens the pull request; it never merges. A goal that fixes an issue or finding needs a defect test with a real seen-failing date first; anything that is not a date does not count.
- `/workflow-release merge SLUG` is the release step: it brings the docs up to date, merges where `auto_merge` is on, bumps the version and writes the release note. `/workflow-release ask SLUG`, `/workflow-release cut SLUG` and `/workflow-release leave SLUG` are the manual path.

## Requirements

- DEL-1: **Reviewed 2026-11-08** The loop. I give one sentence and the done lines, and a worker runs it unattended through these steps, in order: freeze the done lines, office-hours (shape the idea), plan, build, review, qa, ship, pull request, release. Review is the only gate. Each step can be mapped to any skill or plugin I choose, in a private setting outside the repo, and my preferred skill suite is the default; each step runs that skill in its unattended mode. It won't start without the flow set up, and it stops and says why after 3 failed tries. <!-- reviewed 46d7806a -->
- DEL-2: **Reviewed 2026-11-08** The done lines are frozen once the goal starts; changing one means a new goal. <!-- reviewed 7eb4f867 -->
- DEL-3: **Reviewed 2026-11-08** A decision left for me waits under Needs you, or, where the repo allows it, is auto-approved and logged. <!-- reviewed c76ab2fe -->
- DEL-4: **Reviewed 2026-11-08** Every pull request carries the done lines, the plan, how to verify it by hand, and each step's result. <!-- reviewed 85dc7a9a -->
- DEL-5: **Reviewed 2026-11-08** Release is the last step, fully automatic: every goal ends with release, which bumps the version, writes the release note, brings the docs up to date with the docs command (DOC-4) and refuses to merge while a page is stale, runs my own routines, then merges where the repo allows it and publishes the wiki. No draft step and no question, even for a breaking change. Anything that fails shows under Needs you. <!-- reviewed c2490e55 -->

## Non-goals

- It does not decide what to build: the owner gives the sentence and the done lines.
- It never changes a done line once the goal starts; a wrong one needs a new goal.
- It does not plan or govern several goals at once; workflow-monitoring does that.

## Success metrics

- Every merged goal's pull request carries its done lines, plan, verify steps and each step's result.
- A goal that fails three tries stops and says why instead of trying again.
- No goal merges while a wiki page is stale.

## Tests

| Test | Kind | Guards | Checks | Last result |
|---|---|---|---|---|
| [no-done-line-refused](Tests#t-no-done-line-refused) | requirement | DEL-1 | Given a goal with no done line, when it is started, then it is refused. | PASS 2026-11-09 |
| [no-flow-refused](Tests#t-no-flow-refused) | requirement | DEL-1 | Given no skill flow is set, when a goal is started, then it does not start. | PASS 2026-11-09 |
| [stop-after-3-tries](Tests#t-stop-after-3-tries) | requirement | DEL-1 | Given a goal, when three tries fail, then the goal stops and files a finding. | PASS 2026-11-09 |
| [pr-needs-flow](Tests#t-pr-needs-flow) | requirement | DEL-1 | Given a flow step not yet done, when a pull request is opened, then it is refused. | PASS 2026-11-09 |
| [starts-at-idea](Tests#t-starts-at-idea) | requirement | DEL-1 | Given a new goal, when it starts, then it starts at the idea step. | PASS 2026-11-09 |
| [steps-through-flow](Tests#t-steps-through-flow) | requirement | DEL-1 | Given a step reply, when it is recorded, then it is accepted only if the flow ran that step. | PASS 2026-11-09 |
| [no-prompts](Tests#t-no-prompts) | requirement | DEL-1 | Given any tool, when it runs, then it never waits on a terminal prompt. | PASS 2026-11-10 |
| [defect-flow-steps](Tests#t-defect-flow-steps) | requirement | DEL-1 | Given the flow, when it is checked, then it has no checks step and every step can be mapped, with a default suite and overrides. | PASS 2026-11-09 |
| [depth-condensed-refused](Tests#t-depth-condensed-refused) | requirement | DEL-1 | Given review_depth full, when a plan or review reply says it ran condensed, then the try fails. | not run |
| [depth-auto-approve-gate](Tests#t-depth-auto-approve-gate) | requirement | DEL-1 | Given review_depth full and auto-approve on, when a condensed review leaves a gate, then it is refused, not approved. | not run |
| [depth-markers](Tests#t-depth-markers) | requirement | DEL-1 | Given private evidence markers, when a full review reply lacks one, then the try fails without showing the marker. | not run |
| [depth-recorded](Tests#t-depth-recorded) | requirement | DEL-1 | Given the default setting, when a goal runs its steps, then every recorded step names the depth it ran. | not run |
| [depth-condensed-when-set](Tests#t-depth-condensed-when-set) | requirement | DEL-1 | Given review_depth condensed on the base branch, when a review runs condensed, then it is recorded as condensed. | not run |
| [depth-base-branch](Tests#t-depth-base-branch) | requirement | DEL-1 | Given review_depth full on the base branch, when a worker sets condensed in its own worktree, then it is still held to full. | not run |
| [depth-loop-flow](Tests#t-depth-loop-flow) | requirement | DEL-1 | Given markers in the default flow file, when LOOP_FLOW points elsewhere, then the markers still apply. | not run |
| [frozen-done-lines](Tests#t-frozen-done-lines) | requirement | DEL-2 | Given a running goal, when a frozen done line is changed, then the goal stops. | PASS 2026-11-09 |
| [pending-waits](Tests#t-pending-waits) | requirement | DEL-3 | Given a step that leaves a decision for the owner, when it ends, then the goal stops and waits. | PASS 2026-11-09 |
| [auto-approved](Tests#t-auto-approved) | requirement | DEL-3 | Given an auto-approved step, when it ends, then it is logged and nothing waits. | PASS 2026-11-09 |
| [cut-needs-verify](Tests#t-cut-needs-verify) | requirement | DEL-4 | Given no Verify by hand steps, when a release is cut, then it is refused. | PASS 2026-11-09 |
| [pr-body-criterion](Tests#t-pr-body-criterion) | requirement | DEL-4 | Given a pull request, when its body is written, then it carries the goal, the done lines, the verify steps and each step's result. | PASS 2026-11-09 |
| [depth-in-pr-body](Tests#t-depth-in-pr-body) | requirement | DEL-4 | Given a goal whose steps are recorded, when its pull request opens, then the body lists every step with its depth. | not run |
| [never-merges](Tests#t-never-merges) | requirement | DEL-5 | Given auto_merge is off, when goals finish, then nothing is merged. | PASS 2026-11-09 |
| [wiki-release](Tests#t-wiki-release) | requirement | DEL-5 | Given a merged goal, when the release runs, then its wiki pages are published, even when python leaves cache files behind. | PASS 2026-11-09 |
| [auto-release](Tests#t-auto-release) | requirement | DEL-5 | Given auto-release is on, when a goal merges, then it is released automatically. | PASS 2026-11-09 |
| [wiki-unmapped-stale](Tests#t-wiki-unmapped-stale) | requirement | DEL-5 | Given a page no touched path maps to, when the release step runs, then it refreshes the page and refuses to merge while it is stale. | PASS 2026-11-09 |
| [scripts-no-hang](Tests#t-scripts-no-hang) | defect | [#35](https://github.com/jcl2018/agent-workflow-template/issues/35) closed (2026-11-09) | Given a script with no terminal, when it needs a prompt, then it fails with an error instead of hanging. | PASS 2026-11-10 |
| [pr-body-no-checks](Tests#t-pr-body-no-checks) | defect | [PR 62](https://github.com/jcl2018/agent-workflow-template/pull/62) merged (2026-11-09) | Given a pull request, when its body is written, then it says nothing about checks and lists each step's result. | PASS 2026-11-09 |
| [wiki-release-pycache](Tests#t-wiki-release-pycache) | defect | [#58](https://github.com/jcl2018/agent-workflow-template/issues/58) closed (2026-11-09) | Given python leaves cache files behind, when a goal merges, then its wiki pages are still published. | PASS 2026-11-09 |
| [worker-runs-release](Tests#t-worker-runs-release) | defect | [PR 61](https://github.com/jcl2018/agent-workflow-template/pull/61) merged (2026-11-09) | Given a worker that ends with its pull request waiting, when it finishes, then it runs the release step itself. | PASS 2026-11-09 |
