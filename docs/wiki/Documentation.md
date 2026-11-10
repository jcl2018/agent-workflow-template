<!-- workflow-docs -->
# Documentation

Milestone: https://github.com/jcl2018/agent-workflow-template/milestone/3

Review: **Unreviewed**

## Problem
- I can't tell from the wiki what a feature does, how to use it, or whether its requirements are really tested.
- Pages drift from the code, and each repo writes them its own way, so reviewing them takes too long.
- I need my approved requirements to stay exactly as I wrote them, while the loop keeps tests, Usage and milestones up to date for me.

## Usage
- `/workflow-docs audit [--base REF] [--dry-run]` — Checks every page against the template, fixes the mechanical (the Tests tables) and lists wording to rewrite; on a Reviewed page it lists each requirement with no passing test as `UNTESTED ID: <why>`. Ends with `DOCS OK: N pages`, or `DOCS: N to do` and exit 1 while any is left.
- `/workflow-docs check [--base REF]` — Prints one line per problem (`STALE page: ...`, `MISSING`, `UNWRITTEN`, `UNMAPPED`, `SECTIONS`, `LOCKED`, `CHANGED` and others), then exits 1; prints `DOCS OK: N pages` when clean. With no pages mapped it prints `NO PAGES: run add first` (exit 1).
- `/workflow-docs criteria PAGE` — Prints the requirement format (`FORMAT ...`) and the next free ID (`NEXT DEL-7`). Refuses a page with no requirements (exit 1, `REFUSED: PAGE has no criteria. Fix: use a page listed in .loop/docs.tsv, not Home.`).
- `/workflow-docs review PAGE|ID [--date D]` — Only on the owner's own words. Marks the whole PRD, or one requirement, Reviewed with a date. Prints `REVIEWED PAGE Delivery` or `REVIEWED DEL-1`. Refuses, changing nothing (exit 1): without the owner's words (`REFUSED: only the owner changes a review. Fix: pass --user when their own words said to.`), a future or malformed date, an unknown ID (`REFUSED: no requirement X ... Nothing was changed.`), or a name that isn't a feature page.
- `/workflow-docs unreview PAGE|ID` — Lifts the owner's review lock. Prints `UNREVIEWED PAGE Delivery` or `UNREVIEWED DEL-1`. Same refusals as review.
- `/workflow-docs render` — Rewrites each page's Tests from the regression rows. Prints `RENDERED <page>` per page changed, or `TABLES OK`.
- `/workflow-docs prd NAME "IDEA" --paths A,B` — Drafts a new feature's PRD, Unreviewed, and maps it. Prints `DRAFTED <page>: Review **Unreviewed**, requirement XX-1`, then `NEXT` lines for what is left. Refuses (exit 1) with no --paths, no idea, a bad name, a page that already exists, or no free ID prefix.
- `/workflow-docs convert` — Turns old Summary/Criteria pages into PRD pages, keeping IDs and Reviewed stamps. A preview prints `DRY RUN: nothing written.` Refuses a page without the needed sections (`REFUSED N page(s). ...`).
- `/workflow-docs publish [--dry-run] [--adopt PAGE]` — Copies the pages to the GitHub wiki and prints `PUBLISHED <wiki link>`. Never deletes a page. Refuses (exit 1) while the check finds problems other than CHANGED (`REFUSED: fix the pages above first.`), when a page lost its marker, when the wiki has a page this tool didn't write and it isn't named with --adopt (`REFUSED: the wiki already has X, and this tool didn't write it. Nothing was published.`), or when the push fails.
- `/workflow-docs restore` — Reverts the last publish and prints `RESTORED the wiki: reverted <pages>`. Refuses (exit 1) with no publish on record (`REFUSED: no publish on record.`) or when the wiki changed since (`REFUSED: the wiki changed after the last publish, so nothing was reverted.`).
- `/workflow-docs milestones` — Makes each feature's milestone and the Backlog. Prints `CREATED <name>`, `EXISTS <name>` or `LINKED <page> to its milestone`, and `WOULD create milestone <name>` when it can't write to GitHub; running it again creates nothing. Refuses when GitHub can't be read or a milestone can't be made (exit 1, `REFUSED: could not read the milestones: ...`).

## Requirements

### Functional
- DOC-1: **Reviewed 2026-11-08** PRD template <!-- reviewed 077e9a63 -->
  - One template defines every feature page as a short PRD: Problem (who it's for and what it solves, two or three lines); Usage (the commands and how to use each, left out when nothing applies); Requirements (up to the repo's limit, each with an ID); Non-goals (what the feature deliberately won't do); Success metrics (how we know it works, one to three measurable lines); Tests (for each requirement, one or more Given/When/Then scenarios, each with its test, last result and date, and not enforced when no test passes).
  - Nothing else goes on the page.
- DOC-2: **Reviewed 2026-11-08** The PRD is mine <!-- reviewed 5a698534 -->
  - I review the PRD as a whole (Problem, Usage, Requirements, Non-goals and Success metrics) and mark it Reviewed with a date; only I can do that.
  - After it, nothing in Problem, Requirements, Non-goals or Success metrics changes unless I un-review it.
  - Usage updates with the commands, and any change to it shows as changed since my review, under Needs you, until I review it again.
- DOC-3: **Reviewed 2026-11-08** Tests follow on their own <!-- reviewed 672fcb30 -->
  - Once I review a PRD, the loop writes Given/When/Then scenarios and tests for each requirement, links each to a regression row, and keeps them in step when a requirement changes.
  - I never write or manage tests.
- DOC-4: **Reviewed 2026-11-10** Home is one table <!-- reviewed 04ed0a31 -->
  - Home holds one table with four columns: Feature, What it does, How to use (a link to the README section), Milestone.
  - Nothing else is on Home.
- DOC-5: **Reviewed 2026-11-10** The front door is natural language <!-- reviewed 9ec08d2d -->
  - Every feature has a README "How to use" table: what I say to the agent, and what happens.
  - The table holds plain phrases, with no command syntax.
- DOC-6: **Reviewed 2026-11-10** Usage is an API reference <!-- reviewed 7005fe06 -->
  - Usage lists only commands, one entry each.
  - Each entry gives the exact syntax, what it prints on success, and each refusal with its message and exit code.
- DOC-7: **Reviewed 2026-11-10** Requirements are bullets <!-- reviewed faa2cc53 -->
  - Requirements are bullets, grouped under two sub-headings: Functional (what it does) and Non-functional (qualities and limits).
  - IDs never change in the regroup.
  - An empty group reads "None".
  - The docs check enforces both headings.
- DOC-8: **Reviewed 2026-11-10** Problem is the user's problem <!-- reviewed 708f4e8a -->
  - Problem is written from the user's side ("I ..."): what they can't do today and why it matters.
  - It names no code internals.
- DOC-9: **Reviewed 2026-11-10** Tests are a table <!-- reviewed 3dd400b8 -->
  - Tests is a table: Test, Kind, Guards, Checks, Last result.
  - Each test name links to its entry on the full Tests page.
  - Every requirement and every defect has at least one row.
- DOC-10: **Reviewed 2026-11-10** One Tests page, every issue on a milestone, every release noted <!-- reviewed 9ecf8f8e -->
  - One full Tests page is generated, listing every test with its latest result.
  - Every open issue is on its feature's milestone, or on Backlog only when it fits no feature.
  - Every release has a release note.

### Non-functional
- DOC-11: **Reviewed 2026-11-10** Safe publish <!-- reviewed 65b85b43 -->
  - Publishing never deletes a wiki page and never overwrites one it didn't write unless I name it.
  - The last publish can be undone.
- DOC-12: **Reviewed 2026-11-10** Fast check <!-- reviewed 66d142af -->
  - The docs check finishes in under 30 seconds on this repo.
- DOC-13: **Reviewed 2026-11-10** Same answer every time <!-- reviewed 3a988bfc -->
  - The docs check is deterministic: the same pages and rows give the same result, with no AI judgment.

## Non-goals
- It never writes or reviews the owner's PRD for them: only the owner marks a PRD or a requirement Reviewed.
- It keeps docs only in the repo's wiki folder and its GitHub wiki, nowhere else.

## Success metrics
- The docs check prints DOCS OK on the main branch after every merge.
- Every requirement shows at least one passing Given/When/Then test, or is marked not enforced.
- No reviewed PRD or requirement changes on the main branch without the owner un-reviewing it first.

## Tests

#### DOC-1

PRD template. One template defines every feature page as a short PRD: Problem (who it's for and what it solves, two or three lines); Usage (the commands and how to use each, left out when nothing applies); Requirements (up to the repo's limit, default 6, each with an ID); Non-goals (what the feature deliberately won't do); Success metrics (how we know it works, one to three measurable lines); Tests (for each requirement, one or more Given/When/Then scenarios, each with its test, last result and date, and not enforced when no test passes). Nothing else goes on the page.

- Given a wiki page with a Commands section, when the check runs, then it fails. — [page-shape](../../.loop/regression.tsv), requirement, guards DOC-1, both, PASS 2026-11-09, seen failing 2026-11-07
- Given a criterion that names a script, when the check runs, then it fails. — [criteria-no-scripts](../../.loop/regression.tsv), requirement, guards DOC-1, both, PASS 2026-11-09, seen failing 2026-11-07
- Given a criterion with no passing test, when the page is shown, then it shows as not enforced. — [tests-not-enforced](../../.loop/regression.tsv), requirement, guards DOC-1, both, PASS 2026-11-09, seen failing 2026-11-07
- Given recorded runs, when the Tests table is shown, then it shows each test's last result and date. — [tests-last-run](../../.loop/regression.tsv), requirement, guards DOC-1, both, PASS 2026-11-09, seen failing 2026-11-07
- Given a Tests table behind the last run, when the check runs, then it is reported stale. — [tests-table-stale](../../.loop/regression.tsv), requirement, guards DOC-1, both, PASS 2026-11-09, seen failing 2026-11-07
- Given a changed template sheet, when the docs check runs, then it reads the page rules from the sheet, so the check changes with it. — [template-sheet](../../.loop/regression.tsv), requirement, guards DOC-1, both, PASS 2026-11-09, seen failing 2026-11-08
- Given criteria_max in the config, when a page has more criteria than it allows, then the check fails. — [criteria-max-config](../../.loop/regression.tsv), requirement, guards DOC-1, both, PASS 2026-11-09, seen failing 2026-11-09
- Given a Usage section between Problem and Requirements, when the check runs, then it passes. — [usage-section-allowed](../../.loop/regression.tsv), requirement, guards DOC-1, both, PASS 2026-11-09, seen failing 2026-11-09
- Given a page with no commands and no Usage section, when the check runs, then it passes. — [usage-optional](../../.loop/regression.tsv), requirement, guards DOC-1, both, PASS 2026-11-09, seen failing 2026-11-09
- Given a PRD page with swapped sections, an unknown section or stray text before the first one, when the docs check runs, then it fails with SECTIONS. — [prd-section-order](../../.loop/regression.tsv), requirement, guards DOC-1, both, PASS 2026-11-09, seen failing 2026-11-09
- Given a PRD page with empty Non-goals or four Success metrics lines, when the docs check runs, then it fails naming the section. — [prd-nongoals-metrics](../../.loop/regression.tsv), requirement, guards DOC-1, both, PASS 2026-11-09, seen failing 2026-11-09
- Given a one-line idea, when prd new runs with --paths, then it drafts a mapped, Unreviewed PRD page that stays UNWRITTEN until its drafts are written. — [prd-new](../../.loop/regression.tsv), requirement, guards DOC-1, both, PASS 2026-11-09, seen failing 2026-11-09
- Given old Summary and Criteria pages, when convert runs, then they become PRD pages with the same IDs and stamps, a half-converted page is completed, and a second run changes nothing. — [prd-convert](../../.loop/regression.tsv), requirement, guards DOC-1, both, PASS 2026-11-09, seen failing 2026-11-09

#### DOC-2

The PRD is mine. I review the PRD as a whole (Problem, Usage, Requirements, Non-goals and Success metrics) and mark it Reviewed with a date; only I can do that. After it, nothing in Problem, Requirements, Non-goals or Success metrics changes unless I un-review it; Usage updates with the commands, and any change to it shows as changed since my review, under Needs you, until I review it again.

- Given a criterion, when it is reviewed, then it is marked Reviewed with the date. — [review-dated](../../.loop/regression.tsv), requirement, guards DOC-2, both, PASS 2026-11-09, seen failing 2026-11-07
- Given a criterion, when a review is attempted, then it is reviewed only with the owner's words. — [review-owner-only](../../.loop/regression.tsv), requirement, guards DOC-2, both, PASS 2026-11-09, seen failing 2026-11-07
- Given a reviewed criterion, when it is changed, then the check fails. — [reviewed-lock](../../.loop/regression.tsv), requirement, guards DOC-2, both, PASS 2026-11-09, seen failing 2026-11-07
- Given a reviewed criterion, when it is unreviewed, then its lock is lifted. — [unreview-lifts](../../.loop/regression.tsv), requirement, guards DOC-2, both, PASS 2026-11-09, seen failing 2026-11-07
- Given a reviewed criterion that changed, when the report is printed, then it names that criterion. — [lock-in-report](../../.loop/regression.tsv), requirement, guards DOC-2, both, PASS 2026-11-09, seen failing 2026-11-07
- Given a PRD the owner reviewed, when Problem, Requirements, Non-goals or Success metrics changes, then the docs check fails with LOCKED naming each changed section. — [prd-lock-four](../../.loop/regression.tsv), requirement, guards DOC-2, both, PASS 2026-11-09, seen failing 2026-11-09
- Given a PRD the owner reviewed, when only its Usage is edited, added or removed, then the docs check fails with CHANGED and the board lists the page. — [prd-usage-changed](../../.loop/regression.tsv), requirement, guards DOC-2, both, PASS 2026-11-09, seen failing 2026-11-09
- Given review or unreview with no --user, a bad ID, a bad page or a bad date, when it runs, then it refuses and changes nothing. — [prd-review-args](../../.loop/regression.tsv), requirement, guards DOC-2, both, PASS 2026-11-09, seen failing 2026-11-09
- Given a PRD the owner reviewed, when a requirement is reviewed or unreviewed, or the owner un-reviews and reviews the PRD again, then no lock trips. — [prd-stamps-free](../../.loop/regression.tsv), requirement, guards DOC-2, both, PASS 2026-11-09, seen failing 2026-11-09

#### DOC-3

Tests follow on their own. Once I review a PRD, the loop writes Given/When/Then scenarios and tests for each requirement, links each to a regression row, and keeps them in step when a requirement changes; I never write or manage tests.

- Given a Reviewed criterion with no test or a test that no longer matches, when the check runs, then it is listed. — [untested-listed](../../.loop/regression.tsv), requirement, guards DOC-3, both, PASS 2026-11-09, seen failing 2026-11-08
- Given regression rows linked to a requirement, when the Tests are rendered, then each row is a Given/When/Then scenario with its test, result and date, and a plain description is flagged. — [prd-scenarios](../../.loop/regression.tsv), requirement, guards DOC-3, both, PASS 2026-11-09, seen failing 2026-11-09
- Given a PRD the owner reviewed whose requirement has no test, when the docs audit runs, then it lists that requirement as UNTESTED. — [prd-untested](../../.loop/regression.tsv), requirement, guards DOC-3, both, PASS 2026-11-09, seen failing 2026-11-09

#### DOC-4

One command enforces it: checks all required docs against the template, code and tests, fixes what's mechanical, lists wording to rewrite; the release step runs it on every goal before merging; I can run it myself. It never deletes a page, never overwrites a page it didn't write unless I name it, and the last publish can be undone.

- Given a wiki page behind the code it covers, when the docs check runs, then the page is reported as stale. — [stale-found](../../.loop/regression.tsv), requirement, guards DOC-4, both, PASS 2026-11-09, seen failing 2026-11-07
- Given a stale wiki page, when the wiki is published, then publishing is refused. — [publish-refused-stale](../../.loop/regression.tsv), requirement, guards DOC-4, both, PASS 2026-11-09, seen failing 2026-11-07
- Given a wiki page the tool did not write, when the tool writes pages, then that page is never overwritten. — [refuse-replace](../../.loop/regression.tsv), requirement, guards DOC-4, both, PASS 2026-11-09, seen failing 2026-11-07
- Given two docs merges, when they merge in either order, then no page is left stale. — [stale-merge-order](../../.loop/regression.tsv), requirement, guards DOC-4, both, PASS 2026-11-09, seen failing 2026-11-07
- Given rewording left in the docs, when the docs command runs, then it fixes the Tests table, lists wording to rewrite and exits 1 while any is left. — [docs-audit](../../.loop/regression.tsv), requirement, guards DOC-4, both, PASS 2026-11-09, seen failing 2026-11-08
- Given trouble in the docs, when the release step runs, then it reads the docs command and sees the trouble. — [release-runs-audit](../../.loop/regression.tsv), requirement, guards DOC-4, both, PASS 2026-11-09, seen failing 2026-11-08
- Given a page stating the wrong number of skills, when the docs check runs, then it fails naming the file, the stated number and the real one. — [docs-count-mismatch](../../.loop/regression.tsv), requirement, guards DOC-4, both, PASS 2026-11-09, seen failing 2026-11-09
- Given a page whose Usage changed since the owner's review, when the docs audit, the release fixes or publish run, then none of them stops on it or changes Usage. — [prd-audit-ignores-changed](../../.loop/regression.tsv), requirement, guards DOC-4, both, PASS 2026-11-09, seen failing 2026-11-09
- Given this repo, when its docs check and health run, then nothing fails but a page whose Usage changed since the owner's review. — [prd-repo-green](../../.loop/regression.tsv), requirement, guards DOC-4, both, PASS 2026-11-10, seen failing 2026-11-10

#### DOC-5

Required docs: every repo keeps up to date one wiki page per feature, one GitHub milestone per feature linked from its page plus a Backlog milestone, and a release note for every release; each goal's pull request lands in its feature's milestone.

- Given milestones already created, when milestones runs again, then nothing new is created. — [milestones-once](../../.loop/regression.tsv), requirement, guards DOC-5, both, PASS 2026-11-09, seen failing 2026-11-07
- Given a pull request, when milestones runs, then the pull request goes into its milestone. — [pr-in-milestone](../../.loop/regression.tsv), requirement, guards DOC-5, both, PASS 2026-11-09, seen failing 2026-11-07
- Given a feature page, when the check runs, then it links to its GitHub milestone and a missing Backlog is found. — [milestone-links](../../.loop/regression.tsv), requirement, guards DOC-5, both, PASS 2026-11-09, seen failing 2026-11-08
- Given a release with no release note, when the check runs, then it is found. — [release-note-found](../../.loop/regression.tsv), requirement, guards DOC-5, both, PASS 2026-11-09, seen failing 2026-11-08

#### DOC-6

A feature page's Usage is written as what the owner asks the agent, a skill command or a plain request, and names no script file.

- Given a feature page whose Usage names a script file, when the docs check runs, then it fails. — [usage-no-script](../../.loop/regression.tsv), requirement, guards DOC-6, both, PASS 2026-11-09, seen failing 2026-11-09
- Given a Usage written as requests to the agent, when the docs check runs, then it passes. — [usage-agent-requests](../../.loop/regression.tsv), requirement, guards DOC-6, both, PASS 2026-11-09, seen failing 2026-11-09

### Defect tests

- Given counts in the docs that drift from the code, when the docs check runs, then it fails (issue 39). — [docs-counts-issue-39](../../.loop/regression.tsv), defect, guards [#39](https://github.com/jcl2018/agent-workflow-template/issues/39) closed (2026-11-09), both, PASS 2026-11-09, seen failing 2026-11-09
- Given a wrong skills count with a word such as "workflow-ready" or an extra space before the noun, when the docs check runs, then it fails, and a part such as "other" is not read. — [docs-count-word-gap-issue-104](../../.loop/regression.tsv), defect, guards [#104](https://github.com/jcl2018/agent-workflow-template/issues/104) state unknown, both, not run, seen failing 2026-11-09
- Given a count inside a 4-space indented code block, when the docs check runs, then it is skipped while the same indent inside a list item is still read. — [docs-count-indented-code-issue-105](../../.loop/regression.tsv), defect, guards [#105](https://github.com/jcl2018/agent-workflow-template/issues/105) state unknown, both, not run, seen failing 2026-11-09
- Given a page with one criterion test and one defect test, when the docs check runs, then a tests count of both passes. — [docs-count-defect-tests-issue-106](../../.loop/regression.tsv), defect, guards [#106](https://github.com/jcl2018/agent-workflow-template/issues/106) state unknown, both, not run, seen failing 2026-11-09
- Given a line naming another page's criterion, when the docs check runs, then its skills count is still checked and its tests count is not. — [docs-count-other-id-issue-107](../../.loop/regression.tsv), defect, guards [#107](https://github.com/jcl2018/agent-workflow-template/issues/107) state unknown, both, not run, seen failing 2026-11-09
