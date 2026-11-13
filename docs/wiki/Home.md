<!-- workflow-docs -->
# agent-workflow-template

## Features

| Feature | What it does | How to use | Milestone |
|---|---|---|---|
| [Delivery](Delivery) | Takes one sentence and its done lines to a merged, released pull request (a draft release you publish when auto_merge is off), unattended, through your own skills or its built-in routine, on Linux, macOS and native Windows. | [README › Delivery](https://github.com/jcl2018/agent-workflow-template#how-to-use-delivery) | [Delivery](https://github.com/jcl2018/agent-workflow-template/milestone/1) |
| [Monitoring](Monitoring) | One session governs many goals at once and shows a live board of what's running and what needs you. | [README › Monitoring](https://github.com/jcl2018/agent-workflow-template#how-to-use-monitoring) | [Monitoring](https://github.com/jcl2018/agent-workflow-template/milestone/6) |
| [Documentation](Documentation) | Keeps the wiki and README in one enforced format (feature pages are PRDs with no Usage section; the README's How to use tables and each skill's command reference cover usage), and publishes them on every release; the README's Automation rows follow the Automation requirements. | [README › Documentation](https://github.com/jcl2018/agent-workflow-template#how-to-use-documentation) | [Documentation](https://github.com/jcl2018/agent-workflow-template/milestone/3) |
| [Regression](Regression) | Keeps every requirement and defect tied to a test that runs, and shows the results, including red proof recorded from another runner. | [README › Regression](https://github.com/jcl2018/agent-workflow-template#how-to-use-regression) | [Regression](https://github.com/jcl2018/agent-workflow-template/milestone/7) |
| [Health](Health) | Checks the repo with fixed rules and a full reviewer, and files every finding as an issue tagged with its group (and its feature, when feature_labels is on), a defect or a backlog item on its feature's Backlog milestone (an old Backlog milestone becomes Backlog: Other); triage closes one finding by its issue number, and a review finding that cites no file line or test row is dropped; the roadmap's V1 section says what green on main still needs. | [README › Health](https://github.com/jcl2018/agent-workflow-template#how-to-use-health) | [Health](https://github.com/jcl2018/agent-workflow-template/milestone/4) |
| [Setup](Setup) | Turns any repo into a ready workspace for any agent without ever blocking, judged by health before and after, and keeps it in step with the template. | [README › Setup](https://github.com/jcl2018/agent-workflow-template#how-to-use-setup) | [Setup](https://github.com/jcl2018/agent-workflow-template/milestone/9) |
| [Automation](Automation) | Runs health on your Mac and regression in GitHub Actions for a public repo or on your Mac for a private one, every 4 hours by default, plus any routine a repo adds with one config entry, each with a Runbook in the repo that its one-line scheduled prompt points to; files each failure and finding as an issue tagged with its group (and its feature, when feature_labels is on), and emails you one digest per round; the CI suite runs in eight shards with one combined summary. | [README › Automation](https://github.com/jcl2018/agent-workflow-template#how-to-use-automation) | [Automation](https://github.com/jcl2018/agent-workflow-template/milestone/10) |
| [Guardrails](Guardrails) | Lists every guardrail the template has or needs, each with what it protects against, its owner, its setting and the health check that must prove it is on. | [README › Guardrails](https://github.com/jcl2018/agent-workflow-template#how-to-use-guardrails) | [Guardrails](https://github.com/jcl2018/agent-workflow-template/milestone/11) |

<!-- settings:begin -->
## Settings

Every repo setting from the template's settings reference, with this repo's value from `.loop/config.json`.

| Name | What it means | How to set it | Default | This repo |
|---|---|---|---|---|
| `base` | The branch goals start from and pull requests target. | set "base" in .loop/config.json | `main` | default |
| `agent_command` | The command that runs a goal in the background; the prompt is its last argument. | set "agent_command" in .loop/config.json | `[]` | **overridden:** `["claude", "-p", "--model=sonnet", "--allowedTools=Bash,Read,Write,Edit,Skill"]` |
| `parallel` | Workers running at once; 0 means unlimited. | set "parallel" in .loop/config.json | `0` | default |
| `cadence` | Minutes between check-ins of the operation session, 1 to 60, or off. | set "cadence" in .loop/config.json | `30` | **overridden:** `30` |
| `auto_approve` | true approves what a flow step leaves for the owner, logged as auto-approved. | set "auto_approve" in .loop/config.json | `false` | **overridden:** `true` |
| `auto_merge` | true lets the release step merge a goal's pull request and publish its release. | set "auto_merge" in .loop/config.json | `false` | **overridden:** `true` |
| `pr_bumps_version` | true moves the last number of the version file once on a goal's branch. | set "pr_bumps_version" in .loop/config.json | `false` | default |
| `version_file` | The file that holds the version; a release bumps it and writes the changelog. | set "version_file" in .loop/config.json | `VERSION` | default |
| `routines` | Commands the release step runs on the base branch before it merges. | set "routines" in .loop/config.json | `[]` | default |
| `regression_cron` | Five cron fields: when the full regression runs: in GitHub Actions for a public repo, with each Mac tick for a private one; off turns it off. | set "regression_cron" in .loop/config.json | `17 */4 * * *` | default |
| `health_cron` | Five cron fields (every N hours, or fixed hours): when health with the judge and its digest run on the Mac; off turns it off. | set "health_cron" in .loop/config.json | `47 */4 * * *` | default |
| `judge_env` | No longer read: the judge runs on the Mac with your own claude login. Kept so old configs stay valid. | set "judge_env" in .loop/config.json | `ANTHROPIC_API_KEY` | default |
| `judge_setup` | No longer read: kept so old configs stay valid. | set "judge_setup" in .loop/config.json | `(empty)` | default |
| `digest_owner` | Who the digest comment mentions; empty means the repo owner (an organisation notifies no one). | set "digest_owner" in .loop/config.json | `(empty)` | default |
| `digest_mail` | How the round's digest is mailed: cloudflare (Email Service), smtp, or off; the address and keys live only in Actions secrets. | set "digest_mail" in .loop/config.json | `cloudflare` | default |
| `smtp_host` | The SMTP server digest_mail smtp sends through (with DIGEST_SMTP_USER and DIGEST_SMTP_PASSWORD secrets). | set "smtp_host" in .loop/config.json | `smtp.gmail.com` | default |
| `smtp_port` | 465 (TLS) or 587 (STARTTLS) for digest_mail smtp. | set "smtp_port" in .loop/config.json | `465` | default |
| `review_depth` | full runs the plan and review skills' whole pipeline and refuses a condensed one; condensed allows a shorter run. | set "review_depth" in .loop/config.json | `full` | default |
| `criteria` | true makes docs check enforce the PRD page contract (Problem, Requirements, Non-goals, Success metrics, Tests). | set "criteria" in .loop/config.json | `true` | default |
| `criteria_max` | Most criteria a wiki page may hold, 1 to 50, default 10; docs check and health fail a page over it. | set "criteria_max" in .loop/config.json | `10` | **overridden:** `17` |
| `wiki_dir` | The folder of wiki pages. | set "wiki_dir" in .loop/config.json | `docs/wiki` | default |
| `risky_paths` | Regexes for paths whose goals need extra care. | set "risky_paths" in .loop/config.json | `["^\\.github/", "(^|/)auth", "(^|/)migrations?/", "(^|/)(schema|data)\\b"]` | default |
| `step_limit` | Seconds one flow step may run when the flow file sets no limit; 0 means the built-in limit. | set "step_limit" in .loop/config.json | `0` | default |
| `goal_lane_minutes` | Minutes a goal's regression lane may take before health warns and its LANE line says over. | set "goal_lane_minutes" in .loop/config.json | `10` | default |
| `goal_levels` | Row levels a goal lane plans from: land, or nightly for land and nightly rows. | set "goal_levels" in .loop/config.json | `land` | default |
| `regression_runs` | Where the full regression runs: actions (a public repo) or mac (with each Mac tick: a private repo, or a public one recorded mac); setup records it from the repo's live visibility, keeps a recorded mac, and unset means it is not known (nothing is written for GitHub). | set "regression_runs" in .loop/config.json | `(empty)` | default |
| `automation` | Routines the Automation table lists: {name, does, cadence, runs: github:FILE, mac:LABEL or claude:TASK}; setup declares the three built-in ones. | set "automation" in .loop/config.json | `[]` | default |
| `ci_levels` | Target of the scheduled and tag regression runs: nightly (every row) or land. | set "ci_levels" in .loop/config.json | `nightly` | default |
| `token_budget` | Tokens a goal may spend over all steps before no new step starts; 0 means no budget. | set "token_budget" in .loop/config.json | `0` | **overridden:** `3000000` |
| `test_budget_minutes` | Minutes one in-loop test run (qa, ship, pull request) may take, 15 or more; rows past it are left to the scheduled full suite. | set "test_budget_minutes" in .loop/config.json | `15` | default |
| `prep_budget_minutes` | Minutes a lane may spend before its first test row (preparing, planning, waiting for a slot), 15 or more; a lane past it stops and says which part ran long. | set "prep_budget_minutes" in .loop/config.json | `15` | **overridden:** `25` |
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

Health and regression, then each `automation` entry in `.loop/config.json`; to add one, add an entry.

| Routine | What it does | State | Cadence | Runs on | Last run | Owed by you |
|---|---|---|---|---|---|---|
| [health](https://github.com/jcl2018/agent-workflow-template/wiki/Health#health-round) | Checks the repo and files each finding. | on | every 4 hours | this Mac's local schedule | docs.py automation | none |
| [regression](https://github.com/jcl2018/agent-workflow-template/wiki/Regression#regression-round) | Runs every regression row, files each failure. | on | every 4 hours | GitHub Actions (regression.yml) | docs.py automation | none |
| digest email | Mails one digest per health round. | on | cron `with each health round` | this Mac's local schedule | docs.py automation | set the digest address and keys in the schedule's mail.env on the Mac (yours, outside git) |
<!-- automation:end -->
