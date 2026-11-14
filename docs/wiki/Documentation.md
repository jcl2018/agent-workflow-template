<!-- workflow-docs -->
# Documentation

Milestone: https://github.com/jcl2018/agent-workflow-template/milestone/3

Review: **Reviewed 2026-11-13** <!-- prd P=63d54ff2 R=d93be5bd N=81dd3484 M=4599a537 U=03828777 -->

## Problem
- I can't tell from the wiki what a feature does, how to use it, or whether its requirements are really tested.
- Pages drift from the code, and each repo writes them its own way, so reviewing them takes too long.
- I need my approved requirements to stay exactly as I wrote them, while the loop keeps tests up to date for me.

## Requirements

### Functional
- DOC-1: **Reviewed 2026-11-13** PRD template <!-- reviewed 422243c4 -->
  - One template defines every feature page as a short PRD: Problem (who it's for and what it solves, two or three lines); Requirements (up to the repo's limit, each with an ID); Non-goals (what the feature deliberately won't do); Success metrics (how we know it works, one to three measurable lines); Tests (for each requirement, one or more Given/When/Then scenarios, each with its test, last result and date, and not enforced when no test passes). A page has no Usage section.
  - Nothing else goes on the page except the generated, optional Deployments (DOC-14) and Runbook (DOC-16) sections.
- DOC-2: **Reviewed 2026-11-13** The PRD is mine <!-- reviewed 2e17a232 -->
  - I review the PRD as a whole (Problem, Requirements, Non-goals and Success metrics) and mark it Reviewed with a date; only I can do that, in my own words: typed by me, or recorded verbatim by the operation session from my own message.
  - A recorded message counts only for the requirement IDs or pages it lists, once for a review and once for an un-review, and every use is logged with its words.
  - After it, nothing in Problem, Requirements, Non-goals or Success metrics changes unless I un-review it.
- DOC-3: **Reviewed 2026-11-08** Tests follow on their own <!-- reviewed 2e9e1c3f -->
  - Once I review a PRD, the loop writes Given/When/Then scenarios and tests for each requirement, links each to a regression row, and keeps them in step when a requirement changes.
  - I never write or manage tests.
- DOC-4: **Reviewed 2026-11-13** Home is one table <!-- reviewed b837a911 -->
  - Home holds one table with four columns: Feature, What it does, How to use (a link to the README section), Milestone (optional: empty, or a link to the free-form milestone the feature is planned on).
  - Below the table Home carries only the generated Settings and Automation sections (DOC-15); nothing else is on Home.
- DOC-5: **Reviewed 2026-11-10** The front door is natural language <!-- reviewed 885694d1 -->
  - Every feature has a README "How to use" table: what I say to the agent, and what happens.
  - The table holds plain phrases, with no command syntax.
- DOC-6: **Reviewed 2026-11-13** Each skill's commands are documented in its command reference <!-- reviewed bb317f4a -->
  - Each skill's SKILL.md Command map names every command, and its references/commands.md gives each command's exact syntax, what it prints on success, and each refusal with its message and exit code.
- DOC-7: **Reviewed 2026-11-10** Requirements are bullets <!-- reviewed 7de6dae3 -->
  - Requirements are bullets, grouped under two sub-headings: Functional (what it does) and Non-functional (qualities and limits).
  - IDs never change in the regroup.
  - An empty group reads "None".
  - The docs check enforces both headings.
- DOC-8: **Reviewed 2026-11-10** Problem is the user's problem <!-- reviewed b623f09d -->
  - Problem is written from the user's side ("I ..."): what they can't do today and why it matters.
  - It names no code internals.
- DOC-9: **Reviewed 2026-11-10** Tests are a table <!-- reviewed df9c63f7 -->
  - Tests is a table: Test, Kind, Guards, Checks, Last result.
  - Each test name links to its entry on the full Tests page.
  - Every requirement and every defect has at least one row.
- DOC-10: **Reviewed 2026-11-13** One Tests page, every release noted, a backlog milestone per feature <!-- reviewed 8b00915e -->
  - One full Tests page is generated, listing every test with its latest result.
  - Every release has a release note.
  - Every feature page has one standing milestone, "Backlog: <Feature>", and "Backlog: Other" holds what fits no feature; a version milestone such as v1.0 stays optional and free form. Nothing requires an issue or a pull request to have a milestone, and a backlog item never blocks a release.
  - An existing milestone named "Backlog" is renamed "Backlog: Other", and the feature milestones that hold goals and pull requests (Delivery, Documentation and the rest) are kept as they are.
  - Release notes are passed to gh in a file (`--notes-file`), never on the command line.
- DOC-14: **Reviewed 2026-11-10** A feature page lists what it ships: the pages people open and the deliveries people receive <!-- reviewed 6920f546 -->
  - A feature page that ships something people can open, or a delivery people receive (for example a scheduled email), has a Deployments section; it is optional otherwise.
  - Pages: one row per public or private page, with its link, who can open it (public or sign-in), what it shows, and the live build (the sha in build.txt).
  - Deliveries: one row each, with its channel, recipients as a group (never an email address), what is sent and its status.
  - The docs check refuses a malformed Deployments table, naming the table and the column.
  - A listed public link that doesn't answer, or a live build that isn't the promoted one, fails the deploying repo's own check for now; the template takes that check over later.
- DOC-16: **Reviewed 2026-11-13** A feature page carries a runbook for each routine it owns <!-- reviewed afaba23b -->
  - A page that owns a scheduled or on-demand routine has an optional Runbook section, one subsection per routine, saying what an agent given only "run routine X" must read first: the requirement ids it serves, the schedule, the exact steps or command, what a full run is (live sources and real output, never a dry run or a fixture on a scheduled run), the one output and where it goes, the forbidden shortcuts, and how to tell the run was real.
  - The docs check fails a routine listed in the routine registry whose page has no runbook for it, and a runbook missing any of those fields, naming the page, the routine and the field.
  - A runbook's Serves field (continuation lines included) must name requirement ids that a page defines, and each routine and field appears once; a page whose sections are out of order is reported for that, not for its ids.
  - The runbook is not locked by the PRD review: an agent corrects it as it learns, and the owner's review of the requirements stays valid.

- DOC-15: **Reviewed 2026-11-13** Home and the README show how the repo is set up and what runs by itself. <!-- reviewed cc5849cc -->
  - Home and the README carry a Settings section: each setting's name, what it means, how to set it, its default and this repo's value, marked overridden only when it differs from the default.
  - Home and the README carry an Automation section: each routine on or off, what it does, its cadence in plain words, where it runs, its last run when known (live, from `docs.py automation`, so the page does not change with every run) and any step still owed by the owner; health and regression are built in and a repo adds a routine with one entry in its config, with no code change.
  - The README names and links the template repo the loop came from, never a local path, and the adoption entry points to all three.
  - The docs check says STALE when a setting, a workflow file or a value changes, and render or publish refreshes them.
  - The code that renders the blocks stays readable and under health's size warning: `counting.py` holds the Automation block code and `render.py` the rest, so the text a config renders is the same wherever the code sits (issue 1402).
  - Health and the digest email run on the Mac's local schedule, never in GitHub Actions, so the Automation table owes no health workflow; the digest's keys go in the schedule's mail.env on the Mac, outside git.

### Non-functional
- DOC-11: **Reviewed 2026-11-10** Safe publish <!-- reviewed f33a3310 -->
  - Publishing never deletes a wiki page and never overwrites one it didn't write unless I name it.
  - The last publish can be undone.
- DOC-12: **Reviewed 2026-11-10** Fast check <!-- reviewed f069101b -->
  - The docs check finishes in under 30 seconds on this repo.
- DOC-13: **Reviewed 2026-11-10** Same answer every time <!-- reviewed 0f4743ac -->
  - The docs check is deterministic: the same pages and rows give the same result, with no AI judgment.

## Non-goals
- It never writes or reviews the owner's PRD for them: only the owner marks a PRD or a requirement Reviewed.
- It keeps docs only in the repo's wiki folder and its GitHub wiki, nowhere else.

## Success metrics
- The docs check prints DOCS OK on the main branch after every merge.
- Every requirement shows at least one passing Given/When/Then test, or is marked not enforced.
- No reviewed PRD or requirement changes on the main branch without the owner un-reviewing it first.

## Tests

| Test | Kind | Guards | Checks | Last result |
|---|---|---|---|---|
| [stale-found](Tests#t-stale-found) | requirement | DOC-1 | Given a wiki page behind the code it covers, when the docs check runs, then the page is reported as stale. | PASS 2026-11-12 |
| [publish-refused-stale](Tests#t-publish-refused-stale) | requirement | DOC-1 | Given a stale wiki page, when the wiki is published, then publishing is refused. | PASS 2026-11-12 |
| [stale-merge-order](Tests#t-stale-merge-order) | requirement | DOC-1 | Given two docs merges, when they merge in either order, then no page is left stale. | PASS 2026-11-12 |
| [page-shape](Tests#t-page-shape) | requirement | DOC-1 | Given a wiki page with a Commands section, when the check runs, then it fails. | PASS 2026-11-12 |
| [criteria-no-scripts](Tests#t-criteria-no-scripts) | requirement | DOC-1 | Given a criterion that names a script, when the check runs, then it fails. | PASS 2026-11-12 |
| [tests-not-enforced](Tests#t-tests-not-enforced) | requirement | DOC-1 | Given a criterion with no passing test, when the page is shown, then it shows as not enforced. | PASS 2026-11-12 |
| [tests-last-run](Tests#t-tests-last-run) | requirement | DOC-1 | Given recorded runs, when the Tests table is shown, then it shows each test's last result and date. | PASS 2026-11-12 |
| [tests-table-stale](Tests#t-tests-table-stale) | requirement | DOC-1 | Given a Tests table behind the last run, when the check runs, then it is reported stale. | PASS 2026-11-12 |
| [template-sheet](Tests#t-template-sheet) | requirement | DOC-1 | Given a changed template sheet, when the docs check runs, then it reads the page rules from the sheet, so the check changes with it. | PASS 2026-11-12 |
| [docs-audit](Tests#t-docs-audit) | requirement | DOC-1 | Given rewording left in the docs, when the docs command runs, then it fixes the Tests table, lists wording to rewrite and exits 1 while any is left. | PASS 2026-11-12 |
| [release-runs-audit](Tests#t-release-runs-audit) | requirement | DOC-1 | Given trouble in the docs, when the release step runs, then it reads the docs command and sees the trouble. | PASS 2026-11-12 |
| [criteria-max-config](Tests#t-criteria-max-config) | requirement | DOC-1 | Given criteria_max in the config, when a page has more criteria than it allows, then the check fails. | PASS 2026-11-12 |
| [usage-section-refused](Tests#t-usage-section-refused) | requirement | DOC-1 | Given a Usage section of API entries between Problem and Requirements, when the check runs, then it fails with a USAGE line (the owner dropped Usage on 2026-11-13). | not run |
| [no-usage-passes](Tests#t-no-usage-passes) | requirement | DOC-1 | Given a page with no commands and no Usage section, when the check runs, then it passes. | not run |
| [docs-count-mismatch](Tests#t-docs-count-mismatch) | requirement | DOC-1 | Given a page stating the wrong number of skills, when the docs check runs, then it fails naming the file, the stated number and the real one. | PASS 2026-11-12 |
| [prd-section-order](Tests#t-prd-section-order) | requirement | DOC-1 | Given a PRD page with swapped sections, an unknown section or stray text before the first one, when the docs check runs, then it fails with SECTIONS. | PASS 2026-11-10 |
| [prd-nongoals-metrics](Tests#t-prd-nongoals-metrics) | requirement | DOC-1 | Given a PRD page with empty Non-goals or four Success metrics lines, when the docs check runs, then it fails naming the section. | PASS 2026-11-10 |
| [audit-names-usage](Tests#t-audit-names-usage) | requirement | DOC-1 | Given a reviewed PRD with a Usage section, when audit runs, then it names the USAGE page. | not run |
| [prd-new](Tests#t-prd-new) | requirement | DOC-1 | Given a one-line idea, when prd new runs with --paths, then it drafts a mapped, Unreviewed PRD page that stays UNWRITTEN until its drafts are written. | PASS 2026-11-10 |
| [prd-convert](Tests#t-prd-convert) | requirement | DOC-1 | Given old Summary and Criteria pages, when convert runs, then they become PRD pages with the same IDs and stamps, a half-converted page is completed, and a second run changes nothing. | PASS 2026-11-10 |
| [prd-repo-green](Tests#t-prd-repo-green) | requirement | DOC-1 | Given this repo, when its docs check and health run, then nothing fails but a page whose Usage changed since the owner's review. | PASS 2026-11-10 |
| [cap-default-10](Tests#t-cap-default-10) | requirement | DOC-1 | Given no criteria_max in the config, when the cap is read, then it is 10 in both the docs check and setup. | PASS 2026-11-10 |
| [format-key](Tests#t-format-key) | requirement | DOC-1 | Given a template rules block whose format key leaves out problem, when the docs check runs, then the Problem check is off. | PASS 2026-11-10 |
| [guide-marker-refused](Tests#t-guide-marker-refused) | requirement | DOC-1 | Given a page with requirement or Review lines, when it carries the guide marker, then the docs check refuses it naming the page. | PASS 2026-11-10 |
| [spec-decisions-wording](Tests#t-spec-decisions-wording) | requirement | DOC-1 | Given the owner's 2026-11-12 spec decisions, when the pages and SKILL.md files are read, then the loop runs only affected rows, GRD-5 names --live, the feature-label requirements say feature_labels, and the budget setting is test_budget_minutes. | PASS 2026-11-12 |
| [spec-decisions-log](Tests#t-spec-decisions-log) | requirement | DOC-1 | Given the owner's 2026-11-12 decisions, when DECISIONS.md is read, then it holds ten dated entries and the proposed wording of each locked requirement. | PASS 2026-11-13 |
| [link-page-passes](Tests#t-link-page-passes) | requirement | DOC-1 | Given a feature page holding a PRD line and a readable linked PRD, when the docs check runs, then it passes and the Tests table lists the linked ids without copying the PRD text. | PASS 2026-11-13 |
| [link-unread-never-pass](Tests#t-link-unread-never-pass) | requirement | DOC-1 | Given a feature page whose PRD source cannot be read, when the docs check runs, then it reports UNREAD and exits non-zero. | PASS 2026-11-13 |
| [stale-own-finding](Tests#t-stale-own-finding) | requirement | DOC-1 | Given main has a stale page the goal's diff doesn't map to, when docs.py check --own runs on the goal branch, then it prints the page as a FINDING line and passes. | not run |
| [stale-own-main-reported](Tests#t-stale-own-main-reported) | requirement | DOC-1 | Given the same stale page on main, when plain docs.py check runs on main (as health and the scheduled run do), then it still prints the STALE line, so --own hides nothing from them. | not run |
| [stale-own-goal-fails](Tests#t-stale-own-goal-fails) | requirement | DOC-1 | Given a goal whose own diff makes a mapped page stale, when docs.py check --own runs, then it still prints STALE for that page and fails. | not run |
| [stale-own-main-own-fails](Tests#t-stale-own-main-own-fails) | requirement | DOC-1 | Given a stale page on main, when docs.py check --own runs on main itself (the scheduled run's rows), then it still prints STALE and fails. | not run |
| [stale-own-block-kept](Tests#t-stale-own-block-kept) | requirement | DOC-1 | Given a Settings, Automation or README block that differs from a fresh render, when docs.py check --own runs, then its STALE line is kept, never moved to a FINDING. | not run |
| [notion-app-link-unread](Tests#t-notion-app-link-unread) | requirement | DOC-1 | Given a feature page whose PRD is an app.notion.com link and no reader, when the docs check runs, then it reports UNREAD instead of reading the sign-in page. | PASS 2026-11-13 |
| [review-dated](Tests#t-review-dated) | requirement | DOC-2 | Given a criterion, when it is reviewed, then it is marked Reviewed with the date. | PASS 2026-11-12 |
| [review-owner-only](Tests#t-review-owner-only) | requirement | DOC-2 | Given a criterion, when a review is attempted, then it is reviewed only with the owner's words. | PASS 2026-11-12 |
| [reviewed-lock](Tests#t-reviewed-lock) | requirement | DOC-2 | Given a reviewed criterion, when it is changed, then the check fails. | PASS 2026-11-12 |
| [unreview-lifts](Tests#t-unreview-lifts) | requirement | DOC-2 | Given a reviewed criterion, when it is unreviewed, then its lock is lifted. | PASS 2026-11-12 |
| [lock-in-report](Tests#t-lock-in-report) | requirement | DOC-2 | Given a reviewed criterion that changed, when the report is printed, then it names that criterion. | PASS 2026-11-12 |
| [prd-lock-four](Tests#t-prd-lock-four) | requirement | DOC-2 | Given a PRD the owner reviewed, when Problem, Requirements, Non-goals or Success metrics changes, then the docs check fails with LOCKED naming each changed section. | PASS 2026-11-10 |
| [usage-section-not-changed](Tests#t-usage-section-not-changed) | requirement | DOC-2 | Given a reviewed PRD, when a Usage section is added, then the check says USAGE, never CHANGED or LOCKED, and exits 1. | not run |
| [prd-review-args](Tests#t-prd-review-args) | requirement | DOC-2 | Given review or unreview with no --user, a bad ID, a bad page or a bad date, when it runs, then it refuses and changes nothing. | PASS 2026-11-10 |
| [prd-stamps-free](Tests#t-prd-stamps-free) | requirement | DOC-2 | Given a PRD the owner reviewed, when a requirement is reviewed or unreviewed, or the owner un-reviews and reviews the PRD again, then no lock trips. | PASS 2026-11-10 |
| [seal-sub-bullets](Tests#t-seal-sub-bullets) | requirement | DOC-2 | Given a reviewed requirement, when one of its sub-bullets changes, then the docs check reports LOCKED. | PASS 2026-11-12 |
| [report-sub-bullets](Tests#t-report-sub-bullets) | requirement | DOC-2 | Given a reviewed requirement whose sub-bullet changed, when the report prints, then it names it, and not once restored. | PASS 2026-11-12 |
| [owner-record-applies](Tests#t-owner-record-applies) | requirement | DOC-2 | Given the owner's message recorded by the operation session, when a worker reviews with --owner-record, then the requirement is Reviewed and reviews.tsv names the record and the words. | not run |
| [worker-cannot-write-owner-words](Tests#t-worker-cannot-write-owner-words) | requirement | DOC-2 | Given a worker role, when it tries to record the owner's words, then it is refused and nothing is written, while the operation role can record them. | not run |
| [owner-record-ids-only](Tests#t-owner-record-ids-only) | requirement | DOC-2 | Given a recorded owner message, when a worker names an ID it does not list or uses it twice for one command, then it is refused with nothing changed. | not run |
| [untested-listed](Tests#t-untested-listed) | requirement | DOC-3 | Given a Reviewed criterion with no test or a test that no longer matches, when the check runs, then it is listed. | PASS 2026-11-12 |
| [prd-scenarios](Tests#t-prd-scenarios) | requirement | DOC-3 | Given regression rows linked to a requirement, when the Tests are rendered, then each row is a Given/When/Then scenario with its test, result and date, and a plain description is flagged. | PASS 2026-11-10 |
| [prd-untested](Tests#t-prd-untested) | requirement | DOC-3 | Given a PRD the owner reviewed whose requirement has no test, when the docs audit runs, then it lists that requirement as UNTESTED. | PASS 2026-11-10 |
| [format-home](Tests#t-format-home) | requirement | DOC-4 | Given a Home page with a line outside its Features table, when the docs check runs, then it fails naming Home, Features and DOC-4. | PASS 2026-11-10 |
| [home-topic-column](Tests#t-home-topic-column) | requirement | DOC-4 | Given a topics setting, when Home is rendered, then it leads with a Topic column grouping the features and a wrong Topic cell fails the check. | PASS 2026-11-14 |
| [home-header-both](Tests#t-home-header-both) | requirement | DOC-4 | Given Home with or without a Topic column, when the docs check runs, then both headers are accepted, and the Topic cell is checked only when the topics setting is set. | PASS 2026-11-14 |
| [home-topic-live](Tests#t-home-topic-live) | requirement | DOC-4 | Given this repo's topics setting, when Home is read, then its table leads with a Topic column and the settings show topics held in the repo config. | PASS 2026-11-14 |
| [format-frontdoor](Tests#t-format-frontdoor) | requirement | DOC-5 | Given a README How to use table with a command in You say, when the docs check runs, then it fails naming README, the section and DOC-5. | PASS 2026-11-10 |
| [command-reference-complete](Tests#t-command-reference-complete) | requirement | DOC-6 | Given each skill's SKILL.md Command map, when the reference is read, then every verb in the map has its syntax in the skill's SKILL.md or references/commands.md. | not run |
| - | requirement | DOC-6 | no passing test | not enforced |
| [format-bullets](Tests#t-format-bullets) | requirement | DOC-7 | Given a requirement with no sub-bullet, when the docs check runs, then it fails naming the page, Requirements and DOC-7. | PASS 2026-11-10 |
| [format-orphan-bullet](Tests#t-format-orphan-bullet) | requirement | DOC-7 | Given a sub-bullet with no requirement above it, when the docs check runs, then it is refused. | PASS 2026-11-10 |
| [format-groups](Tests#t-format-groups) | requirement | DOC-7 | Given Requirements without the Functional or Non-functional heading, when the docs check runs, then it fails. | PASS 2026-11-10 |
| [format-groups-read](Tests#t-format-groups-read) | requirement | DOC-7 | Given a reviewed requirement under either group, when a sub-bullet is added, then it is still read and the check reports LOCKED. | PASS 2026-11-10 |
| [format-problem](Tests#t-format-problem) | requirement | DOC-8 | Given a Problem that names code internals, when the docs check runs, then it fails naming the page, Problem and DOC-8. | PASS 2026-11-10 |
| [problem-plural](Tests#t-problem-plural) | requirement | DOC-8 | Given a Problem with a banned word in the plural, when the docs check runs, then it fails. | PASS 2026-11-10 |
| [format-tests-table](Tests#t-format-tests-table) | requirement | DOC-9 | Given a hand-edited Tests table, when the docs check runs, then it fails naming the page, Tests and DOC-9. | PASS 2026-11-10 |
| [milestones-once](Tests#t-milestones-once) | requirement | DOC-10 | Given a free-form milestone title such as v1.0, when new runs twice, then one milestone is made and the second run says it exists. | PASS 2026-11-12 |
| [release-note-found](Tests#t-release-note-found) | requirement | DOC-10 | Given a release with no release note, when the check runs, then it is found. | PASS 2026-11-12 |
| [tests-page-stale](Tests#t-tests-page-stale) | requirement | DOC-10 | Given a full Tests page behind the runs, when the docs check runs, then it is reported stale with its first differing line. | PASS 2026-11-10 |
| [tests-page-run-link](Tests#t-tests-page-run-link) | requirement | DOC-10 | Given a runs file with a run column, when the Tests page is rendered, then each result links its Actions run, or that day's CI runs when the cell is empty. | PASS 2026-11-10 |
| [runs-sha](Tests#t-runs-sha) | requirement | DOC-10 | Given no GITHUB_* vars, when a row runs, then its run cell is empty. | PASS 2026-11-10 |
| [runs-url](Tests#t-runs-url) | requirement | DOC-10 | Given all three GITHUB_* vars, when a row runs, then its run cell is the Actions run URL. | FAIL 2026-11-10 |
| [runs-partial](Tests#t-runs-partial) | requirement | DOC-10 | Given only some GITHUB_* vars, when a row runs, then the run cell is empty. | FAIL 2026-11-10 |
| [runs-upgrade](Tests#t-runs-upgrade) | requirement | DOC-10 | Given an old 3-column runs file, when a row runs, then every row has 4 columns and old rows have an empty run. | PASS 2026-11-10 |
| [runs-keep](Tests#t-runs-keep) | requirement | DOC-10 | Given a recorded row, when only another row runs, then its run cell is unchanged. | PASS 2026-11-10 |
| [runs-same-day](Tests#t-runs-same-day) | requirement | DOC-10 | Given two branches running the same rows on one day, when each records its run, then the run files are identical. | PASS 2026-11-10 |
| [backlog-renames-old](Tests#t-backlog-renames-old) | requirement | DOC-10 | Given an old milestone named Backlog, when the Backlog milestones are made with --live, then it is renamed Backlog: Other with its number kept, none is made beside it, and a dry run only says it would. | not run |
| [deploy-section-optional](Tests#t-deploy-section-optional) | requirement | DOC-14 | Given a feature page with no Deployments section, a good Page table, a good Delivery table or both, when the docs check runs, then it passes, and a Deployments section before Success metrics is refused as out of order. | PASS 2026-11-12 |
| [deploy-table-refused](Tests#t-deploy-table-refused) | requirement | DOC-14 | Given a Deployments section with prose, no table, a wrong header, two tables of a kind, no row, a wrong cell count, an empty cell, a bad link, access, build or an email address, when the docs check runs, then it refuses it naming the table and column, and never prints the address. | PASS 2026-11-12 |
| [deploy-not-locked](Tests#t-deploy-not-locked) | requirement | DOC-14 | Given a Reviewed page that gains a Deployments section, when the docs check, the owner's review and render run, then the page is neither locked nor changed, the review works and render keeps the section byte for byte. | PASS 2026-11-12 |
| [deploy-doc14-reviewed](Tests#t-deploy-doc14-reviewed) | requirement | DOC-14 | Given this repo's Documentation page, when the docs check runs, then it carries DOC-14 Reviewed with both owner messages and passes. | PASS 2026-11-12 |
| [runbook-good](Tests#t-runbook-good) | requirement | DOC-16 | Given a feature page with a well-formed Runbook section after its Problem, when the docs check runs, then it passes, and a Runbook placed before Problem is refused as out of order. | not run |
| [runbook-refused](Tests#t-runbook-refused) | requirement | DOC-16 | Given a Runbook missing its Full run or Output field, with a field too short, an unknown field, loose prose, no routine heading or a bad routine name, when the docs check runs, then each is refused naming the page, the routine and the field. | not run |
| [runbook-registry](Tests#t-runbook-registry) | requirement | DOC-16 | Given a routine in the routine registry whose page has no runbook for it, or a registry row naming no page, when the docs check runs, then it fails; it passes once the page carries the runbook, and with no registry file. | not run |
| [runbook-not-locked](Tests#t-runbook-not-locked) | requirement | DOC-16 | Given a Reviewed feature page that gains a Runbook section, when the docs check runs, then the page is neither locked nor marked changed. | not run |
| [runbook-output-names-row](Tests#t-runbook-output-names-row) | requirement | DOC-16 | Given a Runbook whose Output names a Deployments row that does not exist, when the docs check runs, then it is refused naming the row; an existing row passes. | not run |
| [aut-routine-runbook-owed](Tests#t-aut-routine-runbook-owed) | requirement | DOC-16 | Given a routine in the config's automation list whose page has no Runbook section for it, when the docs check runs, then it reports the missing Runbook. | not run |
| - | requirement | DOC-16 | no passing test | not enforced |
| [settings-overridden](Tests#t-settings-overridden) | requirement | DOC-15 | Given a toy repo with one overridden setting, when render runs, then Home's Settings table marks exactly that one overridden with its value. | PASS 2026-11-12 |
| [settings-stale](Tests#t-settings-stale) | requirement | DOC-15 | Given a setting changed after render, when docs check runs, then it says STALE Settings. | PASS 2026-11-12 |
| [automation-cron-words](Tests#t-automation-cron-words) | requirement | DOC-15 | Given a daily cron, a workflow file and a routine added as one config entry, when render runs, then the Automation page reads the cadence in words, where it runs and the added routine. | PASS 2026-11-12 |
| [blocks-no-insert](Tests#t-blocks-no-insert) | requirement | DOC-15 | Given a repo adopted before the Settings and Automation blocks (no markers), when a lane renders, then README and Home stay byte-identical and docs check calls nothing STALE. | not run |
| [blocks-format](Tests#t-blocks-format) | requirement | DOC-15 | Given setup inserts the blocks into README and a DOC-4 Home, including a README that opens with How to use, when docs check runs, then no FORMAT line refuses them. | not run |
| [blocks-no-cascade](Tests#t-blocks-no-cascade) | requirement | DOC-15 | Given a page mapped to README, when a commit only refreshes the generated blocks, then the page stays fresh, and a real README edit still stales it. | not run |
| [blocks-setup-clean](Tests#t-blocks-setup-clean) | requirement | DOC-15 | Given setup with criteria on, when it adopts a repo, then the README and Home blocks are in the adoption commit and the tree is clean. | PASS 2026-11-12 |
| [automation-links-runbook](Tests#t-automation-links-runbook) | requirement | DOC-15 | Given routines with a Runbook, when the Automation block is generated, then each routine's name links to its page's Runbook. | not run |
| [refuse-replace](Tests#t-refuse-replace) | requirement | DOC-11 | Given a wiki page the tool did not write, when the tool writes pages, then that page is never overwritten. | PASS 2026-11-12 |
| [publish-restore](Tests#t-publish-restore) | requirement | DOC-11 | Given a publish that adopted a page someone else wrote, when restore runs, then the original page is back. | PASS 2026-11-10 |
| [publish-tables-regen](Tests#t-publish-tables-regen) | requirement | DOC-11 | Given a merged head whose generated Tests tables are stale, when the wiki publish prepares its tree, then it re-renders them and the Tests page is no longer stale. | PASS 2026-11-13 |
| [publish-tables-handwritten](Tests#t-publish-tables-handwritten) | requirement | DOC-11 | Given a stale hand-written page, when the wiki publish re-renders the generated tables, then that page is still reported stale and the publish still refuses. | PASS 2026-11-13 |
| [docs-check-speed](Tests#t-docs-check-speed) | requirement | DOC-12 | Given this repo, when the docs check runs, then it finishes in under 30 seconds. | PASS 2026-11-12 |
| [docs-check-same](Tests#t-docs-check-same) | requirement | DOC-13 | Given the same pages and rows, when the docs check runs twice, then it prints the same result. | PASS 2026-11-12 |
| [docs-counts-issue-39](Tests#t-docs-counts-issue-39) | defect | [#39](https://github.com/jcl2018/agent-workflow-template/issues/39) closed (2026-11-09) | Given counts in the docs that drift from the code, when the docs check runs, then it fails (issue 39). | PASS 2026-11-12 |
| [docs-count-word-gap-issue-104](Tests#t-docs-count-word-gap-issue-104) | defect | [#104](https://github.com/jcl2018/agent-workflow-template/issues/104) closed (2026-11-10) | Given a wrong skills count with a word such as "workflow-ready" or an extra space before the noun, when the docs check runs, then it fails, and a part such as "other" is not read. | PASS 2026-11-12 |
| [docs-count-indented-code-issue-105](Tests#t-docs-count-indented-code-issue-105) | defect | [#105](https://github.com/jcl2018/agent-workflow-template/issues/105) closed (2026-11-10) | Given a count inside a 4-space indented code block, when the docs check runs, then it is skipped while the same indent inside a list item is still read. | PASS 2026-11-12 |
| [docs-count-defect-tests-issue-106](Tests#t-docs-count-defect-tests-issue-106) | defect | [#106](https://github.com/jcl2018/agent-workflow-template/issues/106) closed (2026-11-10) | Given a page with one criterion test and one defect test, when the docs check runs, then a tests count of both passes. | PASS 2026-11-12 |
| [docs-count-other-id-issue-107](Tests#t-docs-count-other-id-issue-107) | defect | [#107](https://github.com/jcl2018/agent-workflow-template/issues/107) closed (2026-11-10) | Given a line naming another page's criterion, when the docs check runs, then its skills count is still checked and its tests count is not. | PASS 2026-11-12 |
| [docs-guide-page-issue-125](Tests#t-docs-guide-page-issue-125) | defect | [#125](https://github.com/jcl2018/agent-workflow-template/issues/125) closed (2026-11-11) | Given a guide-marked wiki page, when docs check runs, then it passes with no PRD sections, Home row or README section. | PASS 2026-11-10 |
| [docs-merged-base-issue-156](Tests#t-docs-merged-base-issue-156) | defect | [#156](https://github.com/jcl2018/agent-workflow-template/issues/156) closed (2026-11-11) | Given a branch that merged the base branch, when docs check runs with --base, then the base's commits don't make its page stale. | PASS 2026-11-10 |
| [docs-locked-hint-issue-133](Tests#t-docs-locked-hint-issue-133) | defect | [#133](https://github.com/jcl2018/agent-workflow-template/issues/133) closed (2026-11-13) | Given a reviewed requirement whose wording changed, when docs check runs, then its LOCKED hint says restore or unreview, never review. | PASS 2026-11-10 |
| [docs-milestone-line-issue-130](Tests#t-docs-milestone-line-issue-130) | defect | [#130](https://github.com/jcl2018/agent-workflow-template/issues/130) closed (2026-11-11) | Given a page whose Milestone line names a milestone with another title, when the audit runs, then it reports no missing milestone. | PASS 2026-11-10 |
