<!-- workflow-docs -->
# Documentation

Milestone: https://github.com/jcl2018/agent-workflow-template/milestone/3

Review: **Unreviewed**

## Problem
- I can't tell from the wiki what a feature does, how to use it, or whether its requirements are really tested.
- Pages drift from the code, and each repo writes them its own way, so reviewing them takes too long.
- I need my approved requirements to stay exactly as I wrote them, while the loop keeps tests and Usage up to date for me.

## Usage
- `/workflow-docs audit [--base REF] [--dry-run]` — Checks every page against the template, fixes the mechanical (the Tests tables) and lists wording to rewrite; on a Reviewed page it lists each requirement with no passing test as `UNTESTED ID: <why>`. Ends with `DOCS OK: N pages`, or `DOCS: N to do` and exit 1 while any is left.
- `/workflow-docs check [--base REF]` — Prints one line per problem (`STALE page: ...`, `MISSING`, `UNWRITTEN`, `UNMAPPED`, `SECTIONS`, `LOCKED`, `CHANGED` and others), then exits 1; prints `DOCS OK: N pages` when clean. With no pages mapped it prints `NO PAGES: run add first` (exit 1). Its page map is read through `counting.py` and its page rules through `deployments.py`, moved there unchanged so docs.py and criteria.py stay under the size limit.
- `/workflow-docs criteria PAGE` — Prints the requirement format (`FORMAT ...`) and the next free ID (`NEXT DEL-7`). Refuses a page with no requirements (exit 1, `REFUSED: PAGE has no criteria. Fix: use a page listed in .loop/docs.tsv, not Home.`).
- `/workflow-docs review PAGE|ID [--date D]` — Only on the owner's own words. Marks the whole PRD, or one requirement, Reviewed with a date. Prints `REVIEWED PAGE Delivery` or `REVIEWED DEL-1`. Refuses, changing nothing (exit 1): without the owner's words (`REFUSED: only the owner changes a review. Fix: pass --user when their own words said to.`), a future or malformed date, an unknown ID (`REFUSED: no requirement X ... Nothing was changed.`), or a name that isn't a feature page.
- `/workflow-docs unreview PAGE|ID` — Lifts the owner's review lock. Prints `UNREVIEWED PAGE Delivery` or `UNREVIEWED DEL-1`. Same refusals as review.
- `/workflow-docs render` — Rewrites each page's Tests from the regression rows. Prints `RENDERED <page>` per page changed, or `TABLES OK`. The package folds keep the scripts the docs name under 100 files: the digest mail renderer sits in health `rounds.py`, the private rules in `enforce.py` and the issue proposal in setup `sync.py`.
- `/workflow-docs entry` — Writes the entry point, `.loop/START.md`, from the PRD pages (each feature's first Problem bullet and its Usage entries) and the loop config, and refreshes the workflow-loop block in each agent file that holds one. Prints `FIXED .loop/START.md` and `FIXED <file>` per file it rewrote, or `NO CHANGE .loop/START.md` (exit 0). `entry check` prints `STALE <path>: ... (ENTRY_STALE)` or `MISSING <path>: ... (ENTRY_MISSING)` (exit 1), `LAG <path>: installed v<v>, repo v<v>: ask for workflow-setup update (ENTRY_LAG)` (exit 0), or `ENTRY OK` (exit 0).
- `/workflow-docs prd NAME "IDEA" --paths A,B` — Drafts a new feature's PRD, Unreviewed, and maps it. Prints `DRAFTED <page>: Review **Unreviewed**, requirement XX-1`, then `NEXT` lines for what is left. Refuses (exit 1) with no --paths, no idea, a bad name, a page that already exists, or no free ID prefix.
- `/workflow-docs convert` — Turns old Summary/Criteria pages into PRD pages, keeping IDs and Reviewed stamps. A preview prints `DRY RUN: nothing written.` Refuses a page without the needed sections (`REFUSED N page(s). ...`).
- `/workflow-docs publish [--dry-run] [--adopt PAGE]` — Copies the pages to the GitHub wiki and prints `PUBLISHED <wiki link>`. Never deletes a page. Refuses (exit 1) while the check finds problems other than CHANGED (`REFUSED: fix the pages above first.`), when a page lost its marker, when the wiki has a page this tool didn't write and it isn't named with --adopt (`REFUSED: the wiki already has X, and this tool didn't write it. Nothing was published.`), or when the push fails.
- `/workflow-docs restore` — Reverts the last publish and prints `RESTORED the wiki: reverted <pages>`. Refuses (exit 1) with no publish on record (`REFUSED: no publish on record.`) or when the wiki changed since (`REFUSED: the wiki changed after the last publish, so nothing was reverted.`).
- `/workflow-docs milestone new TITLE | move ISSUE TITLE` — Optional, for planning by version: `new` makes a free-form milestone such as v1.0 and `move` puts an issue on an existing one (or `none` clears it; a title that doesn't exist is refused). Prints `CREATED <title>`, `EXISTS <title>` or `WOULD create milestone <title> (dry run; add --live)`; running it again creates nothing. Refuses (exit 1) `REFUSED: no milestone <title> (issue <n> unchanged). Fix: milestone.py new <title> --live` and `REFUSED: no GitHub token, nothing created. ...`. No check ever runs it.

## Requirements

### Functional
- DOC-1: **Reviewed 2026-11-08** PRD template <!-- reviewed 6cbab853 -->
  - One template defines every feature page as a short PRD: Problem (who it's for and what it solves, two or three lines); Usage (the commands and how to use each, left out when nothing applies); Requirements (up to the repo's limit, each with an ID); Non-goals (what the feature deliberately won't do); Success metrics (how we know it works, one to three measurable lines); Tests (for each requirement, one or more Given/When/Then scenarios, each with its test, last result and date, and not enforced when no test passes).
  - Nothing else goes on the page.
- DOC-2: **Reviewed 2026-11-08** The PRD is mine <!-- reviewed caa2882e -->
  - I review the PRD as a whole (Problem, Usage, Requirements, Non-goals and Success metrics) and mark it Reviewed with a date; only I can do that.
  - After it, nothing in Problem, Requirements, Non-goals or Success metrics changes unless I un-review it.
  - Usage updates with the commands, and any change to it shows as changed since my review, under Needs you, until I review it again.
- DOC-3: **Reviewed 2026-11-08** Tests follow on their own <!-- reviewed 2e9e1c3f -->
  - Once I review a PRD, the loop writes Given/When/Then scenarios and tests for each requirement, links each to a regression row, and keeps them in step when a requirement changes.
  - I never write or manage tests.
- DOC-4: **Unreviewed** Home is one table
  - Home holds one table with four columns: Feature, What it does, How to use (a link to the README section), Milestone (optional: empty, or a link to the free-form milestone the feature is planned on).
  - Nothing else is on Home.
- DOC-5: **Reviewed 2026-11-10** The front door is natural language <!-- reviewed 885694d1 -->
  - Every feature has a README "How to use" table: what I say to the agent, and what happens.
  - The table holds plain phrases, with no command syntax.
- DOC-6: **Reviewed 2026-11-10** Usage is an API reference <!-- reviewed 0d3ab52b -->
  - Usage lists only commands, one entry each.
  - Each entry gives the exact syntax, what it prints on success, and each refusal with its message and exit code.
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
- DOC-10: **Unreviewed** One Tests page, every release noted, milestones optional
  - One full Tests page is generated, listing every test with its latest result.
  - Every release has a release note.
  - A milestone is optional and free form, used to plan by version (for example v1.0); nothing requires a feature page, issue or pull request to have one, and no check fails or warns for lacking one.
- DOC-14: **Reviewed 2026-11-10** A feature page lists what it ships: the pages people open and the deliveries people receive <!-- reviewed 6920f546 -->
  - A feature page that ships something people can open, or a delivery people receive (for example a scheduled email), has a Deployments section; it is optional otherwise.
  - Pages: one row per public or private page, with its link, who can open it (public or sign-in), what it shows, and the live build (the sha in build.txt).
  - Deliveries: one row each, with its channel, recipients as a group (never an email address), what is sent and its status.
  - The docs check refuses a malformed Deployments table, naming the table and the column.
  - A listed public link that doesn't answer, or a live build that isn't the promoted one, fails the deploying repo's own check for now; the template takes that check over later.

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
| [criteria-max-config](Tests#t-criteria-max-config) | requirement | DOC-1 | Given criteria_max in the config, when a page has more criteria than it allows, then the check fails. | PASS 2026-11-11 |
| [usage-section-allowed](Tests#t-usage-section-allowed) | requirement | DOC-1 | Given a Usage section of API entries between Problem and Requirements, when the check runs, then it passes. | PASS 2026-11-11 |
| [usage-optional](Tests#t-usage-optional) | requirement | DOC-1 | Given a page with no commands and no Usage section, when the check runs, then it passes. | PASS 2026-11-11 |
| [docs-count-mismatch](Tests#t-docs-count-mismatch) | requirement | DOC-1 | Given a page stating the wrong number of skills, when the docs check runs, then it fails naming the file, the stated number and the real one. | PASS 2026-11-11 |
| [prd-section-order](Tests#t-prd-section-order) | requirement | DOC-1 | Given a PRD page with swapped sections, an unknown section or stray text before the first one, when the docs check runs, then it fails with SECTIONS. | PASS 2026-11-10 |
| [prd-nongoals-metrics](Tests#t-prd-nongoals-metrics) | requirement | DOC-1 | Given a PRD page with empty Non-goals or four Success metrics lines, when the docs check runs, then it fails naming the section. | PASS 2026-11-10 |
| [prd-audit-ignores-changed](Tests#t-prd-audit-ignores-changed) | requirement | DOC-1 | Given a page whose Usage changed since the owner's review, when the docs audit, the release fixes or publish run, then none of them stops on it or changes Usage. | PASS 2026-11-10 |
| [prd-new](Tests#t-prd-new) | requirement | DOC-1 | Given a one-line idea, when prd new runs with --paths, then it drafts a mapped, Unreviewed PRD page that stays UNWRITTEN until its drafts are written. | PASS 2026-11-10 |
| [prd-convert](Tests#t-prd-convert) | requirement | DOC-1 | Given old Summary and Criteria pages, when convert runs, then they become PRD pages with the same IDs and stamps, a half-converted page is completed, and a second run changes nothing. | PASS 2026-11-10 |
| [prd-repo-green](Tests#t-prd-repo-green) | requirement | DOC-1 | Given this repo, when its docs check and health run, then nothing fails but a page whose Usage changed since the owner's review. | PASS 2026-11-10 |
| [cap-default-10](Tests#t-cap-default-10) | requirement | DOC-1 | Given no criteria_max in the config, when the cap is read, then it is 10 in both the docs check and setup. | PASS 2026-11-10 |
| [format-key](Tests#t-format-key) | requirement | DOC-1 | Given a template rules block whose format key leaves out problem, when the docs check runs, then the Problem check is off. | PASS 2026-11-10 |
| [guide-marker-refused](Tests#t-guide-marker-refused) | requirement | DOC-1 | Given a page with requirement or Review lines, when it carries the guide marker, then the docs check refuses it naming the page. | PASS 2026-11-10 |
| [review-dated](Tests#t-review-dated) | requirement | DOC-2 | Given a criterion, when it is reviewed, then it is marked Reviewed with the date. | PASS 2026-11-12 |
| [review-owner-only](Tests#t-review-owner-only) | requirement | DOC-2 | Given a criterion, when a review is attempted, then it is reviewed only with the owner's words. | PASS 2026-11-12 |
| [reviewed-lock](Tests#t-reviewed-lock) | requirement | DOC-2 | Given a reviewed criterion, when it is changed, then the check fails. | PASS 2026-11-12 |
| [unreview-lifts](Tests#t-unreview-lifts) | requirement | DOC-2 | Given a reviewed criterion, when it is unreviewed, then its lock is lifted. | PASS 2026-11-12 |
| [lock-in-report](Tests#t-lock-in-report) | requirement | DOC-2 | Given a reviewed criterion that changed, when the report is printed, then it names that criterion. | PASS 2026-11-12 |
| [prd-lock-four](Tests#t-prd-lock-four) | requirement | DOC-2 | Given a PRD the owner reviewed, when Problem, Requirements, Non-goals or Success metrics changes, then the docs check fails with LOCKED naming each changed section. | PASS 2026-11-10 |
| [prd-usage-changed](Tests#t-prd-usage-changed) | requirement | DOC-2 | Given a PRD the owner reviewed, when only its Usage is edited, added or removed, then the docs check fails with CHANGED and the board lists the page. | PASS 2026-11-10 |
| [prd-review-args](Tests#t-prd-review-args) | requirement | DOC-2 | Given review or unreview with no --user, a bad ID, a bad page or a bad date, when it runs, then it refuses and changes nothing. | PASS 2026-11-10 |
| [prd-stamps-free](Tests#t-prd-stamps-free) | requirement | DOC-2 | Given a PRD the owner reviewed, when a requirement is reviewed or unreviewed, or the owner un-reviews and reviews the PRD again, then no lock trips. | PASS 2026-11-10 |
| [seal-sub-bullets](Tests#t-seal-sub-bullets) | requirement | DOC-2 | Given a reviewed requirement, when one of its sub-bullets changes, then the docs check reports LOCKED. | PASS 2026-11-10 |
| [report-sub-bullets](Tests#t-report-sub-bullets) | requirement | DOC-2 | Given a reviewed requirement whose sub-bullet changed, when the report prints, then it names it, and not once restored. | PASS 2026-11-10 |
| [untested-listed](Tests#t-untested-listed) | requirement | DOC-3 | Given a Reviewed criterion with no test or a test that no longer matches, when the check runs, then it is listed. | PASS 2026-11-12 |
| [prd-scenarios](Tests#t-prd-scenarios) | requirement | DOC-3 | Given regression rows linked to a requirement, when the Tests are rendered, then each row is a Given/When/Then scenario with its test, result and date, and a plain description is flagged. | PASS 2026-11-10 |
| [prd-untested](Tests#t-prd-untested) | requirement | DOC-3 | Given a PRD the owner reviewed whose requirement has no test, when the docs audit runs, then it lists that requirement as UNTESTED. | PASS 2026-11-10 |
| [format-home](Tests#t-format-home) | requirement | DOC-4 | Given a Home page with a line outside its Features table, when the docs check runs, then it fails naming Home, Features and DOC-4. | PASS 2026-11-10 |
| [format-frontdoor](Tests#t-format-frontdoor) | requirement | DOC-5 | Given a README How to use table with a command in You say, when the docs check runs, then it fails naming README, the section and DOC-5. | PASS 2026-11-10 |
| [usage-no-script](Tests#t-usage-no-script) | requirement | DOC-6 | Given a Usage entry whose command is not in the skill's Command map, when the docs check runs, then it fails. | PASS 2026-11-11 |
| [usage-agent-requests](Tests#t-usage-agent-requests) | requirement | DOC-6 | Given a Usage written as API entries with syntax, output and refusals, when the docs check runs, then it passes. | PASS 2026-11-11 |
| [format-usage-api](Tests#t-format-usage-api) | requirement | DOC-6 | Given a Usage entry that does not say what it prints, when the docs check runs, then it fails naming the page, Usage and DOC-6. | PASS 2026-11-10 |
| [usage-empty-backticks](Tests#t-usage-empty-backticks) | requirement | DOC-6 | Given a Usage entry whose backticks hold only spaces, when the docs check runs, then it fails without a crash. | PASS 2026-11-10 |
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
| [deploy-section-optional](Tests#t-deploy-section-optional) | requirement | DOC-14 | Given a feature page with no Deployments section, a good Page table, a good Delivery table or both, when the docs check runs, then it passes, and a Deployments section before Success metrics is refused as out of order. | PASS 2026-11-10 |
| [deploy-table-refused](Tests#t-deploy-table-refused) | requirement | DOC-14 | Given a Deployments section with prose, no table, a wrong header, two tables of a kind, no row, a wrong cell count, an empty cell, a bad link, access, build or an email address, when the docs check runs, then it refuses it naming the table and column, and never prints the address. | PASS 2026-11-10 |
| [deploy-not-locked](Tests#t-deploy-not-locked) | requirement | DOC-14 | Given a Reviewed page that gains a Deployments section, when the docs check, the owner's review and render run, then the page is neither locked nor changed, the review works and render keeps the section byte for byte. | PASS 2026-11-10 |
| [deploy-doc14-reviewed](Tests#t-deploy-doc14-reviewed) | requirement | DOC-14 | Given this repo's Documentation page, when the docs check runs, then it carries DOC-14 Reviewed with both owner messages and passes. | PASS 2026-11-10 |
| [refuse-replace](Tests#t-refuse-replace) | requirement | DOC-11 | Given a wiki page the tool did not write, when the tool writes pages, then that page is never overwritten. | PASS 2026-11-12 |
| [publish-restore](Tests#t-publish-restore) | requirement | DOC-11 | Given a publish that adopted a page someone else wrote, when restore runs, then the original page is back. | PASS 2026-11-10 |
| [docs-check-speed](Tests#t-docs-check-speed) | requirement | DOC-12 | Given this repo, when the docs check runs, then it finishes in under 30 seconds. | PASS 2026-11-10 |
| [docs-check-same](Tests#t-docs-check-same) | requirement | DOC-13 | Given the same pages and rows, when the docs check runs twice, then it prints the same result. | PASS 2026-11-10 |
| [docs-counts-issue-39](Tests#t-docs-counts-issue-39) | defect | [#39](https://github.com/jcl2018/agent-workflow-template/issues/39) closed (2026-11-09) | Given counts in the docs that drift from the code, when the docs check runs, then it fails (issue 39). | PASS 2026-11-11 |
| [docs-count-word-gap-issue-104](Tests#t-docs-count-word-gap-issue-104) | defect | [#104](https://github.com/jcl2018/agent-workflow-template/issues/104) closed (2026-11-10) | Given a wrong skills count with a word such as "workflow-ready" or an extra space before the noun, when the docs check runs, then it fails, and a part such as "other" is not read. | PASS 2026-11-10 |
| [docs-count-indented-code-issue-105](Tests#t-docs-count-indented-code-issue-105) | defect | [#105](https://github.com/jcl2018/agent-workflow-template/issues/105) closed (2026-11-10) | Given a count inside a 4-space indented code block, when the docs check runs, then it is skipped while the same indent inside a list item is still read. | PASS 2026-11-10 |
| [docs-count-defect-tests-issue-106](Tests#t-docs-count-defect-tests-issue-106) | defect | [#106](https://github.com/jcl2018/agent-workflow-template/issues/106) closed (2026-11-10) | Given a page with one criterion test and one defect test, when the docs check runs, then a tests count of both passes. | PASS 2026-11-10 |
| [docs-count-other-id-issue-107](Tests#t-docs-count-other-id-issue-107) | defect | [#107](https://github.com/jcl2018/agent-workflow-template/issues/107) closed (2026-11-10) | Given a line naming another page's criterion, when the docs check runs, then its skills count is still checked and its tests count is not. | PASS 2026-11-10 |
| [docs-guide-page-issue-125](Tests#t-docs-guide-page-issue-125) | defect | [#125](https://github.com/jcl2018/agent-workflow-template/issues/125) closed (2026-11-11) | Given a guide-marked wiki page, when docs check runs, then it passes with no PRD sections, Home row or README section. | PASS 2026-11-10 |
| [docs-merged-base-issue-156](Tests#t-docs-merged-base-issue-156) | defect | [#156](https://github.com/jcl2018/agent-workflow-template/issues/156) closed (2026-11-11) | Given a branch that merged the base branch, when docs check runs with --base, then the base's commits don't make its page stale. | PASS 2026-11-10 |
| [docs-locked-hint-issue-133](Tests#t-docs-locked-hint-issue-133) | defect | [#133](https://github.com/jcl2018/agent-workflow-template/issues/133) open (2026-11-11) | Given a reviewed requirement whose wording changed, when docs check runs, then its LOCKED hint says restore or unreview, never review. | PASS 2026-11-10 |
| [docs-milestone-line-issue-130](Tests#t-docs-milestone-line-issue-130) | defect | [#130](https://github.com/jcl2018/agent-workflow-template/issues/130) closed (2026-11-11) | Given a page whose Milestone line names a milestone with another title, when the audit runs, then it reports no missing milestone. | PASS 2026-11-10 |
