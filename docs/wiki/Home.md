<!-- workflow-docs -->
# agent-workflow-template

## Features

| Feature | What it does | How to use | Milestone |
|---|---|---|---|
| [Delivery](Delivery) | Takes one sentence and its done lines to a merged, released pull request, unattended, through your own skills or its built-in routine. | [README › Delivery](https://github.com/jcl2018/agent-workflow-template#how-to-use-delivery) | [Delivery](https://github.com/jcl2018/agent-workflow-template/milestone/1) |
| [Monitoring](Monitoring) | One session governs many goals at once and shows a live board of what's running and what needs you. | [README › Monitoring](https://github.com/jcl2018/agent-workflow-template#how-to-use-monitoring) | [Monitoring](https://github.com/jcl2018/agent-workflow-template/milestone/6) |
| [Documentation](Documentation) | Keeps the wiki and README in one enforced format, and publishes them on every release. | [README › Documentation](https://github.com/jcl2018/agent-workflow-template#how-to-use-documentation) | [Documentation](https://github.com/jcl2018/agent-workflow-template/milestone/3) |
| [Regression](Regression) | Keeps every requirement and defect tied to a test that runs, and shows the results. | [README › Regression](https://github.com/jcl2018/agent-workflow-template#how-to-use-regression) | [Regression](https://github.com/jcl2018/agent-workflow-template/milestone/7) |
| [Health](Health) | Checks the repo with fixed rules and a full reviewer, and files every finding as an issue tagged with its feature. | [README › Health](https://github.com/jcl2018/agent-workflow-template#how-to-use-health) | [Health](https://github.com/jcl2018/agent-workflow-template/milestone/4) |
| [Setup](Setup) | Turns any repo into a ready workspace for any agent, judged by health, and keeps it in step with the template. | [README › Setup](https://github.com/jcl2018/agent-workflow-template#how-to-use-setup) | [Setup](https://github.com/jcl2018/agent-workflow-template/milestone/9) |
| [Automation](Automation) | Runs regression and health on a schedule, files each failure and finding as an issue tagged with its feature, and emails you one digest per round. | [README › Automation](https://github.com/jcl2018/agent-workflow-template#how-to-use-automation) | [Automation](https://github.com/jcl2018/agent-workflow-template/milestone/10) |
| [Guardrails](Guardrails) | Lists every guardrail the template has or needs, each with what it protects against, its owner, its setting and the health check that must prove it is on. | [README › Guardrails](https://github.com/jcl2018/agent-workflow-template#how-to-use-guardrails) | [Guardrails](https://github.com/jcl2018/agent-workflow-template/milestone/11) |

<!-- settings:begin -->
## Settings

Every repo setting, from the template's settings reference and this repo's `.loop/config.json`.

| Name | What it means | How to set it | Default | This repo |
|---|---|---|---|---|
| `base` | The branch goals start from and pull requests target. | set "base" in .loop/config.json | `main` | default |
| `agent_command` | The command that runs a goal in the background; the prompt is its last argument. | set "agent_command" in .loop/config.json | `[]` | **overridden:** `["claude", "-p", "--model=sonnet", "--allowedTools=Bash,Read,Write,Edit,Skill"]` |
| `parallel` | Workers running at once; 0 means unlimited. | set "parallel" in .loop/config.json | `0` | default |
| `cadence` | Minutes between check-ins of the operation session, 1 to 60, or off. | set "cadence" in .loop/config.json | `30` | default |
| `auto_approve` | true approves what a flow step leaves for the owner, logged as auto-approved. | set "auto_approve" in .loop/config.json | `false` | **overridden:** `true` |
| `auto_merge` | true lets the release step merge a goal's pull request and publish its release. | set "auto_merge" in .loop/config.json | `false` | **overridden:** `true` |
| `pr_bumps_version` | true moves the last number of the version file once on a goal's branch. | set "pr_bumps_version" in .loop/config.json | `false` | default |
| `version_file` | The file that holds the version; a release bumps it and writes the changelog. | set "version_file" in .loop/config.json | `VERSION` | default |
| `routines` | Commands the release step runs on the base branch before it merges. | set "routines" in .loop/config.json | `[]` | default |
| `regression_cron` | Five cron fields: when the regression routine runs in GitHub Actions; off turns it off. | set "regression_cron" in .loop/config.json | `17 */4 * * *` | default |
| `health_cron` | Five cron fields: when the health routine and its digest run in GitHub Actions; off turns it off. | set "health_cron" in .loop/config.json | `47 */4 * * *` | default |
| `judge_env` | The Actions secret holding the agent key; the scheduled judge runs only when it is set. | set "judge_env" in .loop/config.json | `ANTHROPIC_API_KEY` | default |
| `judge_setup` | A command the scheduled health run uses to install judge_command's program, run only with the secret. | set "judge_setup" in .loop/config.json | `(empty)` | default |
| `digest_owner` | Who the digest comment mentions; empty means the repo owner (an organisation notifies no one). | set "digest_owner" in .loop/config.json | `(empty)` | default |
| `digest_mail` | How the round's digest is mailed: cloudflare (Email Service), smtp, or off; the address and keys live only in Actions secrets. | set "digest_mail" in .loop/config.json | `cloudflare` | default |
| `smtp_host` | The SMTP server digest_mail smtp sends through (with DIGEST_SMTP_USER and DIGEST_SMTP_PASSWORD secrets). | set "smtp_host" in .loop/config.json | `smtp.gmail.com` | default |
| `smtp_port` | 465 (TLS) or 587 (STARTTLS) for digest_mail smtp. | set "smtp_port" in .loop/config.json | `465` | default |
| `review_depth` | full runs the plan and review skills' whole pipeline and refuses a condensed one; condensed allows a shorter run. | set "review_depth" in .loop/config.json | `full` | default |
| `criteria` | true makes docs check enforce the PRD page contract (Problem, Requirements, Non-goals, Success metrics, Tests). | set "criteria" in .loop/config.json | `true` | default |
| `criteria_max` | Most criteria a wiki page may hold, 1 to 50, default 10; docs check and health fail a page over it. | set "criteria_max" in .loop/config.json | `10` | **overridden:** `15` |
| `wiki_dir` | The folder of wiki pages. | set "wiki_dir" in .loop/config.json | `docs/wiki` | default |
| `risky_paths` | Regexes for paths whose goals need extra care. | set "risky_paths" in .loop/config.json | `["^\\.github/", "(^|/)auth", "(^|/)migrations?/", "(^|/)(schema|data)\\b"]` | default |
| `step_limit` | Seconds one flow step may run when the flow file sets no limit; 0 means the built-in limit. | set "step_limit" in .loop/config.json | `0` | default |
| `goal_lane_minutes` | Minutes a goal's regression lane may take before health warns and its LANE line says over. | set "goal_lane_minutes" in .loop/config.json | `10` | default |
| `goal_levels` | Row levels a goal lane plans from: land, or nightly for land and nightly rows. | set "goal_levels" in .loop/config.json | `land` | default |
| `ci_levels` | Target of the scheduled and tag regression runs: nightly (every row) or land. | set "ci_levels" in .loop/config.json | `nightly` | default |
| `token_budget` | Tokens a goal may spend over all steps before no new step starts; 0 means no budget. | set "token_budget" in .loop/config.json | `0` | **overridden:** `3000000` |
| `test_budget_minutes` | Minutes one in-loop test run (qa, ship, pull request) may take, 15 or more; rows past it are left to the scheduled full suite. | set "test_budget_minutes" in .loop/config.json | `15` | default |
| `prep_budget_minutes` | Minutes a lane may spend before its first test row (preparing, planning, waiting for a slot), 15 or more; a lane past it stops and says which part ran long. | set "prep_budget_minutes" in .loop/config.json | `15` | default |
| `step_budget_minutes` | Minutes one review or ship step may take, 15 or more; a step at its limit finishes with what it has done and records what it left. | set "step_budget_minutes" in .loop/config.json | `30` | default |
| `stale_branch_days` | Days a local branch on no remote may sit before health lists it with its removal command. | set "stale_branch_days" in .loop/config.json | `14` | default |
| `mend` | true lets watch start a fresh agent for a failed goal. | set "mend" in .loop/config.json | `false` | **overridden:** `true` |
| `mend_wait` | Seconds a failed goal waits before a mender starts. | set "mend_wait" in .loop/config.json | `120` | default |
| `max_tries` | Failed tries a goal gets before it stops and files a finding. | set "max_tries" in .loop/config.json | `3` | default |
| `resume_on_limit` | true lets watch resume a goal that hit a usage limit. | set "resume_on_limit" in .loop/config.json | `false` | default |
| `limit_wait` | Seconds to wait after a usage limit before resuming. | set "limit_wait" in .loop/config.json | `1800` | default |
| `watch_interval` | Seconds between rounds of watch. | set "watch_interval" in .loop/config.json | `20` | default |
| `agent_files` | Agent entry files setup wires the workflow-loop block into; [] turns wiring off. | set "agent_files" in .loop/config.json | `["CLAUDE.md", "AGENTS.md"]` | default |
| `template_repo` | The template's GitHub repo (owner/name) update reads releases from, when the installed package names none. | set "template_repo" in .loop/config.json | `(empty)` | default |
| `reply_hook` | false turns off the reply-format hook (setup.py --reply-hook installs it) in the operation session. | set "reply_hook" in .loop/config.json | `true` | default |
| `govern_hook` | false turns off the govern-only hook (setup.py --govern-hook installs it): edits, commits and pushes refused in the operation session. | set "govern_hook" in .loop/config.json | `true` | default |
| `full_auto` | true lets the operation session answer a worker's routine decision with its recommended option, logged; risky ones wait. | set "full_auto" in .loop/config.json | `true` | default |
| `pool_size` | Idle worker sessions the session pool keeps; when it runs low the operation session asks you to create the missing ones. | set "pool_size" in .loop/config.json | `20` | default |
| `silent_minutes` | Minutes a worker may send nothing before it shows under Needs you; LOOP_SESSION_QUIET (seconds) overrides it. | set "silent_minutes" in .loop/config.json | `30` | default |
| `feature_labels` | true makes health file and the regression workflow tag each issue feature:<Page> for its feature, and create that label; off by default, so issues carry their group or regression label only. | set "feature_labels" in .loop/config.json | `false` | default |
<!-- settings:end -->

<!-- automation:begin -->
## Automation

Each routine, from `.loop/config.json`, the workflow files and the regression runs file.

| Routine | State | Cadence | Runs on | Last run | Owed by you |
|---|---|---|---|---|---|
| health | on | every 4 hours | GitHub Actions | unknown | none |
| regression | on | every 4 hours | GitHub Actions | 2026-11-12 | none |
| digest email | on (cloudflare) | with each health round | GitHub Actions | unknown | set the digest address and keys as Actions secrets (yours, outside git) |
<!-- automation:end -->
