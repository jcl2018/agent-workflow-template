# Decisions

One line each, where the roadmap didn't say.

- Layout: `skills/workflow-<name>/` per skill, `skills/loop-files.md` as the shared file contract.
- Toy runs use a test double for `gh` (`dev/toy/fakegh`); only the real-repo check calls the real `gh`.
- A goal's run state lives in `<git common dir>/loop/`, so every worktree sees it and nothing extra is committed.
- `dev/package.sh` ships `skills/`, `listing.json` and `README.md` only.
- Starting goals moved from `monitor.py` to `watch.py`, so `monitor.py` only reads. `watch` replaces `start --wait`.
- `goal.py new` needs `--here`: a tool that can't run a background agent is the only reason to build in the governing session.
- A regression row never seen failing blocks `run`, and `red` proves it on a temporary copy of `HEAD`.
- The Actions workflow carries its own small runner, because skill scripts stay out of the repo.
- `mend` and `resume_on_limit` are off by default, since each spends the user's usage without asking.
- Delivery is a wrapper around the owner's own skill suite: one flow, no levels, no judge of its own. A private flow file names the skills, and a probe must prove their unattended mode before any step runs, so a ship skill never runs by a person's rules.
- Nothing a skill leaves for the owner is approved by an agent. It waits under Waiting on you, and `pr` waits for it.
- POCs are deleted: the suite's idea skill covers trying an idea. `workflow-release` stays, as the owner's place for routines before a release.
- 2026-11-12, regression time: the loop runs only the affected rows within `test_budget_minutes`; the full suite runs on the schedule, because a full suite in every goal outgrows the budget. Fixed `workflow-delivery` SKILL.md and its commands.md; REG-7 stands, DEL-6 reworded.
- 2026-11-12, one owner per artifact: MON-3 owns the live board (report, dashboard, artifact) and MON-4 holds its layout; MON-5 owns the check-in reply and never prints the board, because two layouts for one artifact drifted apart. Third layout removed in the proposed MON-3, MON-4, MON-5 wording (Reviewed, waiting on owner un-review).
- 2026-11-12, GitHub writes need `--live`: a token alone never writes; the scheduled workflows pass `--live`, because the safer default is a preview. Reworded GRD-5 and HLT-4; REG-5 and AUT-5 are Reviewed, so their wording is proposed (waiting on owner un-review); defect #2614 filed for the code, which still writes on a token alone.
- 2026-11-12, Guardrails is an index: it points to the owning ids (DEL-8, REG-7, DEL-9, SET-8, MON-7, MON-8) and restates none of their text, because two copies of a rule disagree. Reworded GRD-1 and the overlapping bullets of GRD-2, GRD-3, GRD-4, GRD-8.
- 2026-11-12, unknown tokens: a goal with no token count records "unknown" and the board shows "tokens unread", never 0, because 0 reads as an unspent budget. Reworded GRD-2; defect #2615 filed for the code.
- 2026-11-12, review depth and release: condensed review happens only when `review_depth: condensed` (the default stays full); release merges and publishes with `auto_merge` on and makes a draft without it, because DEL-6 and DEL-5 promised what the settings don't do. DEL-5 and DEL-6 are Reviewed, so their wording is proposed (waiting on owner un-review).
- 2026-11-12, generated sections and Usage: the generated Deployments, Runbook, Settings and Automation sections are allowed on their pages, the Regression metric uses REG-7's 15-minute floor, and Usage carries no module or refactor notes, because DOC-1, DOC-4, DOC-14 and DOC-15 contradicted each other and DOC-6 says Usage lists commands. Reworded DOC-4; DOC-1 is Reviewed, so its wording is proposed (waiting on owner un-review); Usage cleaned on Documentation, Regression and Monitoring.
- 2026-11-12, feature labels: `feature_labels` stays false by default, and the requirements say "when feature_labels is on", because the code tags a feature only then. Reworded HLT-4, AUT-2, AUT-3.
- 2026-11-12, one budget name: the setting is `test_budget_minutes` everywhere, because `test_budget_seconds` does not exist. Fixed workflow-health commands.md and the HLT-6 row descriptions; HLT-2 names no setting and stands.
- 2026-11-12, Monitoring non-goal: "does not merge" becomes "never merges unless auto_merge is on", because MON-7 and MON-15 let the post-merge step merge. The Monitoring page is Reviewed, so the Non-goals wording is proposed (waiting on owner un-review).
- Review findings (2026-11-12), health runs on the Mac only: Automation Usage no longer documents a health workflow, `workflow --check` or the Actions mail job; `/workflow-health workflow` reads as removed (exit 2), `mail send` runs as the last step of the Mac tick and `mail test` is run by hand, both reading the schedule's `mail.env`. `health_cron` is `off`, an every-N-hours shape or fixed hours (the form `local install` accepts), because the code refuses any other. Setup's entry no longer lists `health.yml` or `mail-test.yml`, because setup writes neither. The sentence win-posix-rest added to the removed `--check` entry (the tick code runs on native Windows) goes with that entry; the Health page's `local tick` entry is where the tick is described.
- Review findings (2026-11-12), private repos: the regression workflow entry says `NOT WRITTEN` for a private repo, because the code writes it for a public repo only. AUT-2 no longer says "no check ever blocks a private repo's merge": the pull request lane posts commit statuses for the ruleset's required checks, and a failing lane posts failure, so it holds that merge; AUT-2's affected-tests bullet points to REG-4 and AUT-1's missed-run bullet drops "regression before health", which the tick does not do for a private repo. All three are Unreviewed.
- Review findings (2026-11-12), rows name their requirement: the rows that already prove the Mac tick (`ls-private-tick`, `ls-public-tick`, `ls-missed-run`) now guard AUT-1, and the status rows (`st-pass`, `st-fail-never-success`) guard AUT-2. Guardrails rows for what is built now guard GRD-2 (`del8-step-stops`, `reg7-budget-leaves`) and GRD-3 (`del9-pr-refuses`, `del9-hooks`), because only `stop-tree-step-limit` named a GRD id; each owner keeps its other rows, and the rest of the guardrails (GRD-4 among them: today a role check, not a boundary) stay "not enforced" until built.
- Review findings (2026-11-12), GRD-4: a worker changes shared loop state for its own goal through the goal's commands (`goal.py`, `sessions.py bind` and `report`), and only the operation session changes the queue, other goals' records and the pool's other sessions, because workers run `goal.py record` and `pr` and bind themselves. Guardrails Usage points to Health for the check entry and no longer names a template version.
- Review findings (2026-11-12), DEL-2: it is on the Delivery page (the Delivery requirements were cut off in the review's prompt after DEL-5), so no requirement changes; DEL-2 moved up to follow DEL-1 so a cut-off page still shows it, with its text and review unchanged. DEL-5's draft-step wording stays the spec-decisions proposal below.
- Review findings (2026-11-12), Usage is current behaviour: the refactor history is out of the Delivery `record` and `pr` entries and the Setup and Health install entries (rollback internals, lock details, script-size notes, a repeated walk-through).
- Review findings (2026-11-12), `workflow-delivery` SKILL.md goes under 150 lines by trimming repeated prose, not rules.

## Waiting on owner un-review

Drafted by health-v1; none of it is applied until the owner un-reviews the requirement and approves the wording. Apply after merging origin/main (drop-usage and backlog-milestones touch the same page first).

- HLT-2 Hygiene: replace "no idle worker sessions" with "no idle worker sessions beyond the pool size (MON-12)".
- HLT-2 Performance: replace "the health check within its limit" with "the health round within AUT-7's budget".
- HLT-7 (Fast check): delete the requirement and its bullet ("The rule check without controls finishes in under 60 seconds."). The round is bounded by AUT-7's budget, so health needs no separate limit; its test (test-health-time.sh) and rows go with it.
- HLT-4: add a last bullet on top of backlog-milestones' HLT-4: "A drift finding that breaks a Reviewed requirement is a defect issue; any other drift finding is backlog."
- HLT-2 Traceability: no wording change needed (its bullet does not mention defect tests; REG-6 owns that rule). Built: a closed issue labelled `health` is exempt from the defect-test rule, and `backlog` too once that label exists on closed issues the listing reads; a closed bug and a closed `finding:` still need a defect row.
- HLT-9: replace the bullet with "Every review finding names its feature and cites its evidence: a file and line, or a test row. A requirement ID or an issue link may be added but never stands alone. A finding without that evidence is dropped, and nothing is filed twice."
- HLT-2 cap: replace "At most 12 groups plus Mine; adding one means retiring one or raising the cap on purpose." with "At most 12 groups plus Mine; adding one means retiring one or raising the cap on purpose. A repo's own rules (HLT-10) are not groups and do not count against the cap."
- HLT-10 (new, next free id; code is built later by health-repo-rules, not by health-v1) "Repo rules": "A repo extends health with its own rules in a committed file, `.loop/health-rules.json`. Each rule names its group (one of the twelve, or `repo`), its feature, the command that runs it (exit 0 pass, 2 warn, 1 fail; any other code is unread), its fix, and a break command that proves it can fail (the Controls group runs it). A repo may set a default rule's threshold (for example the script size cap), or turn a default rule off only with a written reason, which the report shows. Mine stays the owner's private, machine-level rules."
- HLT-8 (as built): "close a batch" also covers one finding by its number (`triage --close --issue N`).

Drafted 2026-11-13 by the automation-routines goal; nothing below is on the pages (AUT-1, AUT-2, AUT-3, AUT-4 and AUT-8 are Reviewed). The code and the Runbook-pointer prompt already work (`docs.py prompts`, health's `prompt-pointer`, the docs check for a routine in the config's `automation` list with a `page`). The owner reviews each wording and un-reviews the requirement to apply it.

- Decision: health-round and regression-round are only the first, built-in routines. Any repo adds its own (a digest, a site deploy) with one entry in the config's `automation` list (`name`, `does`, `cadence`, `runs`, `page`, optional `routine`). It gets a row in the Automation block, a required Runbook on its page, a generated one-line prompt and its output in the digest. A routine's scheduled prompt is never more than a pointer to its Runbook in the repo, because steps copied into a prompt drift between machines.
- AUT-1 (replace its first bullet): "Health and regression are the built-in routines: Health runs on my Mac for every repo, Regression in GitHub Actions for a public repo and on my Mac for a private one. A repo adds its own routines (a digest, a site deploy) with one entry in its config, and each runs where its entry says, with the same schedule, on/off and last-run treatment."
- AUT-2 (add two bullets): "Its scheduled prompt is the one-line pointer to the Regression page's regression-round Runbook (AUT-8), never the steps." and "A failing test's issue holds that test's last 40 output lines, never an empty block (REG-5)."
- AUT-3 (add one bullet): "Its scheduled prompt is the one-line pointer to the Health page's health-round Runbook (AUT-8), never the steps; the Adoption group warns when any installed routine prompt holds more than the pointer."
- AUT-4 (replace its first bullet): "After each round, one email goes to the address I set: what each routine that ran did and its results (the built-in routines and the repo's own), then the new, still-open and fixed issues grouped by feature, each with its link and the request to give the agent to fix it."
- AUT-8 (replace both bullets): "Each routine, built-in or the repo's own, is listed in the registry with the feature page that owns it (health-round on Health and regression-round on Regression in `.loop/routines.tsv`; a repo's own routine by the `page` of its `automation` entry), and that page's Runbook section says what a full run is, the one output, the forbidden shortcuts and how to check the run was real; the docs check fails a routine with no Runbook." and "A routine's scheduled prompt (a Claude scheduled task, a launch agent or an Actions job) is one line generated from the registry by `docs.py prompts`: In <repo>, fast-forward to origin/main, then read <wiki_dir>/<Page>.md's Runbook section <routine> and follow it exactly. No steps live in the prompt or the session, so any agent on any machine runs the same round; health warns when an installed prompt holds more. A scheduled run never sends a dry run, a fixture or a test mail in place of the real output."

## Applied 2026-11-12 (owner sitting)

The owner un-reviewed these requirements and approved the wording below; it is now on the pages, and the pages were reviewed again in the same sitting.

- REG-5 (decision 3): "One labeled issue per failing test, updated while it fails and closed when it passes; known failures don't block; it only previews unless `--live` is given, and the scheduled workflows pass `--live`."
- AUT-5 (decision 3): "Each routine can be turned off or rescheduled in one setting. It writes to GitHub only with `--live` (the scheduled workflows pass it), and without the secrets it needs a routine runs but writes nothing and says what is missing."
- DEL-5 (decision 6): "Every goal ends with release. With auto_merge on it is fully automatic: it bumps the version, writes the release note, refuses to merge while a page is stale, runs my routines, merges, publishes the release and the wiki. With auto_merge off it makes a draft release for me to publish and merges nothing. Any failure shows under Needs you."
- DEL-6 (decision 6): "Plan and review run at full depth by default (`review_depth: full`); a condensed plan and review happens only when `review_depth: condensed`, and I can override it per goal. Tests never shrink: every goal runs its test lane, the affected rows within the test budget (REG-7)."
- DOC-1 (decision 7): replace "Nothing else goes on the page." with "Nothing else goes on the page except the generated, optional Deployments (DOC-14) and Runbook (DOC-16) sections."
- MON-3 (decision 2): "Live board: report, dashboard and the artifact show the live board in the one fixed layout MON-4 lists; this requirement owns the board, and a check-in never prints it."
- MON-4 (decision 2): title "Live board layout"; keep its bullets, and change the last to "Check-ins don't print this board; MON-5 owns the check-in reply."
- MON-5 (decision 2): replace "and prints the full board every time" with "and each check-in prints only its reply layout, never the board"; the title and the layout list stay.
- Monitoring Non-goals (decision 10): "It never merges unless auto_merge is on (MON-7, MON-15); the delivery loop merges and releases."

## Waiting on owner un-review (2026-11-13)

Titles are locked on Reviewed requirements. #410: MON-1, MON-2, MON-13, MON-14 and MON-15 put a whole sentence in the title, against DOC-7's short-title format. Proposed: each gets a short title, and its sentence moves under it as a sub-bullet word for word. Nothing is applied until the owner un-reviews them.

- MON-1: "Roles, start and planning". Sub-bullet: the current text after the title, from "One command starts the operation session" on.
- MON-2: "Live communication". Sub-bullet: the current text after the title, from "Operation and workers talk through session messages" on.
- MON-13: "Two layers per pod". Sub-bullet: "One operation session governs every repo in its pod directly and talks to each worker, with no per-repo operation session; several pods may run concurrently and independently."
- MON-14: "Dependency map grouped by repo". Sub-bullet: "The check-in dependency map has one block per repo headed by the repo's name, with cross-repo dependencies drawn between blocks."
- MON-15: "Pods coordinate through shared state". Sub-bullet: the current text after the title, from "every goal records its owning pod" on.

## Waiting on owner un-review

Proposed wording for the backlog-milestones goal (2026-11-13, the owner approved the design in the operation session). Each Reviewed requirement below stays as it is until the owner un-reviews it and types the approval sentence. DEL-14 and SET-17 are new requirements: adding one to a Reviewed page changes its review lock (LOCKED, and Setup would pass criteria_max), so they go onto the Delivery and Setup pages in the same sitting, and until then their rows guard the goal's done line (`backlog-milestones:1`). The code in this goal already behaves as the wording below says, so it merges after the owner approves it.

- Backlog milestones (design): every filing has one home. Regression files only regression defects, as today. A defect is something broken against a Reviewed requirement; a backlog item is an improvement, idea, drift, weak test, size or saving. Defects are issues labelled `defect`; backlog items are issues labelled `backlog` on the milestone "Backlog: <Feature>" (one per feature page), or "Backlog: Other" when nothing fits. Backlog never blocks a release; an open defect with no goal and no owner OK does (that release check, the board counts and the per-feature triage counts are follow-up goals in workflow-release and workflow-monitoring, outside this goal's touches).
- DOC-10 (title): "One Tests page, every release noted, a backlog milestone per feature"
- DOC-10 (third bullet, replaces "A milestone is optional and free form, used to plan by version (for example v1.0); nothing requires a feature page, issue or pull request to have one, and no check fails or warns for lacking one."): "Every feature page has one standing milestone, "Backlog: <Feature>", and "Backlog: Other" holds what fits no feature; a version milestone such as v1.0 stays optional and free form. Nothing requires an issue or a pull request to have a milestone, and a backlog item never blocks a release."
- HLT-4 (first bullet, replaces "Each finding, from a rule or from the review, is one GitHub issue tagged with its group or kind and, when feature_labels is on (it is off by default), the feature it is about; it sits on a milestone only when I put it there."): "Each finding, from a rule or from the review, is one GitHub issue tagged with its group or kind and, when feature_labels is on (it is off by default), the feature it is about. A FAIL (except a performance one) and a review conflict is a defect, labelled `defect`, on no milestone; every other finding (a WARN, a size, performance, drift, weak-test or saving finding, a review gap, an unread rule) is a backlog item, labelled `backlog`, on its feature's milestone "Backlog: <Feature>", or on "Backlog: Other" when it fits no feature. An issue I move to another milestone stays there."
- DOC-10 (fourth bullet, new): "An existing milestone named "Backlog" is renamed "Backlog: Other", and the feature milestones that hold goals and pull requests (Delivery, Documentation, ...) are kept as they are." (`milestone.py backlog --live` does the rename once, only when "Backlog" exists and "Backlog: Other" does not.)
- DEL-14 (new, Unreviewed): "Leftover findings are filed by kind at ship". Body: "When a goal ships, each finding it did not fix is filed once. A break of a Reviewed requirement inside the goal's touches is fixed in place; outside them it is an open issue labelled `defect`. An improvement, idea or saving is an issue labelled `backlog` on its feature's milestone "Backlog: <Feature>" ("Backlog: Other" when it fits no feature). Filing writes to GitHub only with `--live`, which the goal passes after ship is recorded, and a finding already filed is not filed again."
- SET-17 (new, Unreviewed): "The Backlog milestones exist after adoption". Body: "Adoption creates one milestone "Backlog: <Feature>" for each feature page and "Backlog: Other", and creates none that already exists. Health's Adoption group warns for each one that is missing."

## Waiting on owner un-review (drop-usage)

The owner decided 2026-11-13: "remove the usage section, because you cannot say each feature has an API; we already have the README and How to use, and natural language will find the right way to run it." Feature pages lose Usage. Exact replacement text below; none is applied until the owner un-reviews each requirement and approves the wording. The wording sits alongside backlog-milestones' changes to DOC-10 and HLT-4 and touches neither.

- DOC-1, bullet 1, replace with: One template defines every feature page as a short PRD: Problem (who it's for and what it solves, two or three lines); Requirements (up to the repo's limit, each with an ID); Non-goals (what the feature deliberately won't do); Success metrics (how we know it works, one to three measurable lines); Tests (for each requirement, one or more Given/When/Then scenarios, each with its test, last result and date, and not enforced when no test passes). A page has no Usage section.
- DOC-1, bullet 2: unchanged.
- DOC-2, bullet 1, replace with: I review the PRD as a whole (Problem, Requirements, Non-goals and Success metrics) and mark it Reviewed with a date; only I can do that.
- DOC-2, bullet 3, delete (the Usage clause). Bullet 2 is unchanged.
- DOC-6, rename "Usage is an API reference" to "Each skill's commands are documented in its command reference", replace both bullets with: Each skill's SKILL.md Command map names every command, and its references/commands.md gives each command's exact syntax, what it prints on success, and each refusal with its message and exit code. Reason: the owner dropped Usage because a feature has no API, but the exact syntax, output and refusals are still promises the repo makes and tests prove (the usage-* rows move to the command reference); deleting the requirement would leave them with no owner.
- DOC-5: unchanged. The README's "How to use" tables stay the front door.
- DOC-10 and DOC-15: do not mention Usage; unchanged.
- Documentation Problem, last bullet, replace with: I need my approved requirements to stay exactly as I wrote them, while the loop keeps tests up to date for me. (It names Usage; Problem is locked, so this needs the same un-review.)
- HLT-2, Consistency bullet, replace "a command named the same in Usage and the README" with: a command named the same in its skill's command reference and the README.
- HLT-2, Docs bullet, replace "Usage matches the real commands and output" with: each skill's command reference matches the real commands and output.

## Waiting on owner un-review (stale pages: #3848, #3860, #3861)

Drafted 2026-11-13 by the drop-usage goal. Main's recent code changes left three Reviewed pages stale, and Usage edits no longer touch pages. One real, accurate sub-bullet each, none applied until the owner un-reviews the named requirement and page and approves the wording; the code and tests it describes are already on main.

- Automation (#3848, suite-shard), AUT-2, add this sub-bullet after the last one: The CI suite runs in eight shards with one combined summary: each row is given the time left, the suite-time line counts the rows skipped for time (the unrun rows), and a newer run on the same ref cancels the older.
- Guardrails (#3860, backlog-milestones' `criteria_max` 16 to 17), GRD-9, add this sub-bullet after the last one: A page's requirement cap, `criteria_max` (17 in this repo), is read by health's Size group, so a page too large to review shows as a finding.
- Monitoring (#3861, the reply hook and the check-in dependency code), MON-14, add this sub-bullet after the last one: The reply hook flags a check-in whose Dependencies section leaves out a goal on the board.

Applied 2026-11-13 on the owner's three approvals typed in the drop-usage session: AUT-2, GRD-9 and MON-14 and their pages were un-reviewed, given the sub-bullets above, and reviewed again.

## Waiting on owner un-review (machine-local)

The owner decided 2026-11-13: "some tasks in this session should only rely on things on this session, right? This machine. There are other machines proof and other things. They can be added like to do some milestones, but shouldn't be related." Built by the machine-local goal (`regression.py red ID --owed --runner R`, health WARN after 7 days, the check-in's off-machine to-do lines). Guardrails is Reviewed, so the requirement below is not applied until the owner un-reviews Guardrails and approves the wording.

- Guardrails, add after GRD-10: **GRD-11: A goal depends only on what its own machine can do.** A step only another machine can do (a red proof on another platform, a smoke cell, a Mac-only check) is filed as a to-do issue on the feature's milestone and never blocks the goal, its merge or the release.
  - A row whose red proof needs another platform is recorded owed (Regression, `red ID --owed --runner R`): it reads PENDING, opens one to-do issue labelled `other-machine` on the row's feature milestone, and its goal merges.
  - Health warns on an owed proof older than 7 days and never fails on it (Health, Tests).
  - The check-in lists owed off-machine items under Coming up, and the operation session never holds a goal for another pod or machine (Monitoring).
- Regression, REG-10, add this sub-bullet: A row whose red proof needs another machine can be recorded owed (`red ID --owed --runner R`): it reads PENDING instead of UNPROVEN, one to-do issue labelled `other-machine` opens on the row's feature milestone, and neither the goal's pr lane nor the release waits for it. A real red proof clears it.
- Health, Tests group rule on seen-red, add this sub-bullet: an owed proof (`.loop/regression-owed.tsv`) is not a seen-red failure; it warns once it is older than 7 days and never fails.
- Monitoring, MON-5 (check-in), add this sub-bullet: The check-in lists owed off-machine to-dos under Coming up, and the operation session never holds a goal for another pod or machine.
- Pages stale from this goal's code until the owner re-stamps them: Regression, Health, Monitoring (and Home, Documentation from the DECISIONS edit).

The owner types two sentences in the operation session:

1. Un-review: "Un-review the Guardrails, Regression, Health and Monitoring pages and GRD-10's neighbour GRD-11 (new), REG-10, HLT-2 and MON-5 so the machine-local wording can be added."
2. Review, after the goal has added it: "Review the Guardrails, Regression, Health and Monitoring pages, GRD-11, REG-10, HLT-2 and MON-5 again."

