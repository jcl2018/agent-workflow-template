# Plan: automation

Goal: `.loop/goals/automation.md` (6 frozen done lines). Design: `.loop/goals/automation.design.md` (Approach A).

## Implementation plan

### 1. Config: one setting per routine (AUT-1, AUT-5)
- `.loop/config.json`: `regression_cron` becomes `"17 */4 * * *"`; add `health_cron` `"47 */4 * * *"`, `agent_key_secret` `"ANTHROPIC_API_KEY"` and `digest` (`true`).
- `skills/workflow-setup/scripts/settings.py`: declare `health_cron`, `agent_key_secret` and `digest` with defaults and help, so setup and `fill-repo` add them to repos that lack them. Setup writes `.github/workflows/health.yml` beside `regression.yml`.
- `"off"` in a cron setting turns that routine off at run time: its workflow prints `OFF: <routine> is off in .loop/config.json` to the run summary and writes nothing. Any other value must be five cron fields, or the writer refuses. A run whose own schedule differs from the config prints `SCHEDULE: this workflow runs on X but .loop/config.json says Y; rewrite it with <command>`.

### 2. Regression workflow (AUT-2, REG-5)
- `skills/workflow-regression/scripts/actions.py`:
  - a first step `Check the routine` reads `regression_cron` from `.loop/config.json` and sets an output `on=true|false`; the row and summary steps run only when it is on, and print the OFF line otherwise;
  - failing-row issues are labeled `defect` (created with `--force`) instead of `regression`. Existing issues are still found by their marker in the body: the issue list covers `--label defect` and the old `--label regression`;
  - an issue body names the test, what it checks, the feature (wiki page) and the requirement it guards, read from `tests.py list --tsv` (already carried in the workflow). A closed issue reopens on a new failure, and the issue closes when the row passes, as today.
- `regression.py` (the local run, 19,968 bytes): the label changes to `defect` in `sync_issues`, as a net-zero edit.
- Regenerate `.github/workflows/regression.yml`.

### 3. Health workflow and digest: new `skills/workflow-health/scripts/automation.py` (AUT-1, AUT-3, AUT-4, AUT-5)
Stdlib only, under 20 KB. Commands:
- `automation.py workflow`: writes `.github/workflows/health.yml` from `health_cron`; it refuses a file it didn't write, like `actions.py`. Steps:
  1. check the routine (off → OFF line, write nothing);
  2. find the skills: `skills/workflow-health/scripts/health.py` in the checkout; if missing, print `MISSING: the skills package is not in this repo's checkout, so health ran nothing` and write nothing;
  3. `health.py check` into the run summary;
  4. `health.py file` for every group (opens, updates, closes `health:<group>` issues);
  5. the judge, only when the secret named by `agent_key_secret` is set (else `JUDGE: skipped, no <NAME> secret`);
  6. `automation.py digest`.
  The workflow has `permissions: contents: read, issues: write, actions: read`, and nothing in it pushes.
- `automation.py digest [--dry-run] [--owner LOGIN]`:
  - finds or creates the pinned issue `Automation digest` (label `automation`) and pins it;
  - reads open issues labeled `defect` or `health`, and the previous digest comment's hidden marker `<!-- automation-digest open=1,2,3 -->`;
  - posts one comment: `@owner`, a "What ran" table (regression's latest run conclusion and time via `gh run list --workflow regression.yml`; health's verdict from this run), then **New**, **Still open** and **Fixed** issue lists, and under each open issue "Ask the agent: `<request>`" (`Fix #N (<title>) end to end and open a pull request; its test must fail first and pass after.`), then the marker;
  - with digest off, or without `GH_TOKEN`, it prints the comment and writes nothing (dry run).
- `skills/workflow-health/SKILL.md` and references; `listing.json` commands `workflow` and `digest`.

### 4. Automation PRD page (done lines 1, 6)
- `prd.py` (or criteria) creates `docs/wiki/Automation.md` with Problem, Usage, Requirements, Non-goals and Success metrics; the drafts stay Unreviewed. The milestone is made with `milestone.py`.
- AUT-1..5 go in word for word as Unreviewed and are then marked Reviewed 2026-11-08 with `criteria.py review AUT-n --user --date 2026-11-08`.
- `.loop/docs.tsv`: `Automation	skills/workflow-health/scripts/automation.py,.github/workflows`.

### 5. REG-4 and REG-5 (done line 2)
`criteria.py unreview REG-4 REG-5 --user`, reword, then `review --user --date 2026-11-08`:
- REG-4: "Runs in GitHub Actions: one command runs the suite the same way for me, the loop and GitHub Actions."
- REG-5: "Failures go to GitHub: one issue per failing test, labeled defect, updated, closed on pass; known failures don't block; no token = preview only."

### 6. Tests (done line 5)
New `dev/toy/test-automation.sh`, with a stub gh that records calls and serves issues and runs from files:
- digest format: owner mention, the What ran table, new/still-open/fixed against a previous marker, one ask per open issue, the marker; it creates and pins the issue when missing;
- defect labeling: the regression workflow block run on a failing row creates the issue with `--label defect`, and its body names the feature and requirement;
- off switch: with `regression_cron` / `health_cron` `"off"`, each workflow's routine check prints OFF, and the stub gh records no write call;
- judge gating: no secret means JUDGE skipped; with the secret the judge step is selected;
- missing skills: health prints MISSING and writes nothing;
- no push: neither generated workflow contains `git push`, and their permissions don't include `contents: write`;
- committed workflows equal what the writers produce (extending the existing equality test).
One regression row per check under AUT-n / REG-n, each seen failing once with `red --break`.

### 7. Docs and checks
README (Automation in the commands and file table), the Health and Regression wiki pages' Usage, `loop-files.md`. Land lane (needs operation's go), docs check, health green, package, every script under 20 KB, SKILL.md under 150 lines.

## Review record

<!-- autoplan notes -->
