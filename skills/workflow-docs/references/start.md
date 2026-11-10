# Entry point templates

`entry.py` builds `.loop/START.md` from these paragraphs, filling each `{name}` from `.loop/config.json` only (a
missing setting reads as its default). Nothing private, no count, date or machine path goes in.

## Loop
A goal is one sentence with frozen done lines. A worker takes it through idea, plan, build, review, qa, ship, pull
request and release, on branch `loop/<slug>` cut from `{base}`. Each step's skill is chosen in the private flow file,
`~/.workflow-loop/flow.json` (`built-in` runs delivery's own routine). Review is the only gate. Plan and review run at
`{review_depth}` depth; auto-approval is `{auto_approve}`; a goal stops after {max_tries} failed tries; its token
budget is {token_budget} (0 means none).

## Release
Release is a goal's last step: it brings the docs up to date, bumps `{version_file}` and writes the release note.
Auto-merge is `{auto_merge}`; a pull request bumps the version itself: `{pr_bumps_version}`. Your own routines after a
release: {routines}.

## Operation and workers
One session governs and the others build: the operation session assigns goals, watches them and answers what waits on
you, and never builds. Up to {parallel} workers run at once (0 means no limit). It checks in every {cadence} minutes;
mending a failed goal is `{mend}`, resuming after a usage limit is `{resume_on_limit}`, and watch looks again every
{watch_interval} seconds.

## Docs
Feature pages live in `{wiki_dir}`, one PRD page per feature with numbered requirements, at most {criteria_max} each.
The criteria contract is `{criteria}`. The docs command finds stale pages, and the release step rewrites them.

## Regression
Every requirement and every fixed defect has a regression row in `.loop/regression.tsv`, seen failing before its fix.
The land lane runs once per goal, in qa, within {test_budget_seconds} seconds; the scheduled run is `{regression_cron}`.

## Health
Health checks the repo with fixed rules that give the same answer every time, on the schedule `{health_cron}`; a
branch or worktree older than {stale_branch_days} days is stale. The judge's environment: {judge_env}.

## Settings
Every repo setting, its value and its one-line explanation is in the Settings table below; add any missing one with
`/workflow-setup fill-repo`. Private settings live in `~/.workflow-loop/` and never appear here.
