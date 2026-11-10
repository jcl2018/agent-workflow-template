<!-- workflow-docs -->
# Documentation

Milestone: https://github.com/jcl2018/agent-workflow-template/milestone/3

Review: **Unreviewed**

## Problem

Skill: `workflow-docs`. Keeps wiki pages in `docs/wiki/` (reviewed in pull requests; `wiki_dir` in `.loop/config.json` changes the folder) and finds stale ones. Each feature has a GitHub milestone named for its page, plus a Backlog, made by `skills/workflow-health/scripts/milestone.py`; a goal's pull request goes in its feature's milestone. The docs check accepts any page listed in `.loop/docs.tsv`; the six built-in names keep their prefixes and any other page takes its own.

One command, `/workflow-docs audit` (the `docs.py audit` routine), checks every page against the template sheet (`skills/workflow-docs/references/template.md`), fixes the mechanical (the Tests tables, with defect tests in their own part), lists wording to rewrite (a defect test's link is shown with its issue number) and Reviewed criteria with no test, and the release step runs it on every goal and refreshes every page `docs.py check` calls stale, not only those mapped to the goal's paths. A Usage line is written as what the owner asks the agent and the check fails one that names a `.py` or `.sh` file. Commands, flows and how-tos: `skills/workflow-docs/references/commands.md` (which also keeps, word for word, the PRD page list, review locks, test rules and new-and-old-page steps that `SKILL.md` points to, so it stays under 150 lines) and `skills/workflow-health/references/milestones.md`.

The toy `gh` double (`dev/toy/fakegh`) can also merge a branch and fail a release, for the release tests, and keeps the labels an issue is created or edited with, for the health filing tests. Publishing to the wiki commits with a fallback author when git has none, as on a GitHub runner; `dev/toy/ci-env.sh` runs the toy tests that way.

## Usage

- `/workflow-docs audit` checks every page against the template, fixes the mechanical and lists the wording to rewrite; it exits 1 while any is left. In the Tests, each line carries workflow-regression's one test format after its Given/When/Then words: the row, its kind, what it guards (the requirement, or the issue link with its recorded state), when it runs, its last result and date, and when it was seen failing; a seen-failing value that is not a real date shows as `no`. If that tests.py is missing, broken or too old, the lines keep the older shape and a NOTE says so. The template sheet's example Tests line shows the same shape.
- `/workflow-docs entry` writes `.loop/START.md`, the generated entry point any new session reads first: how the loop, release, operation and workers, docs, regression, health and settings fit together, every feature with how to use it, and every repo setting. `/workflow-docs check` fails while it, or the workflow-loop block in CLAUDE.md and AGENTS.md, is stale (a repo behind the installed skills only shows LAG), and `/workflow-docs audit` rewrites both.
- `/workflow-docs check` lists missing, stale, unmapped and unwritten pages, counts the repo doesn't match (fenced and indented code, quoted code, comments, limits such as "up to 6" and parts such as "two delivery skills" are skipped, a page's tests count includes its defect tests and a stated defect tests count is checked against them, and a wrapped sentence is read whole; mark a line (the mark covers only that line) `<!-- not-a-count -->` when its number isn't one), and broken criteria; `/workflow-docs criteria PAGE` prints the format and the next free id.
- `/workflow-docs review PAGE` marks the whole PRD Reviewed, and `/workflow-docs review ID` one requirement, only on the owner's words; `/workflow-docs unreview PAGE` lifts the lock; PAGE is the exact feature page name, such as Delivery (a wrong case or a path is refused); `/workflow-docs render` rewrites the Tests.
- `/workflow-docs prd NAME "<idea>" --paths A,B` drafts a new feature's PRD, Unreviewed; `/workflow-docs convert` turns old Summary/Criteria pages into PRD pages, keeps a page's first heading when it has no title, and adds a missing Non-goals before Success metrics.
- `/workflow-docs publish` copies the pages to the GitHub wiki, and `/workflow-docs restore` undoes the last publish.
- `/workflow-docs milestones` makes each feature's milestone and the Backlog; running it again creates nothing.

## Requirements

- DOC-1: **Reviewed 2026-11-08** PRD template. One template defines every feature page as a short PRD: Problem (who it's for and what it solves, two or three lines); Usage (the commands and how to use each, left out when nothing applies); Requirements (up to the repo's limit, default 6, each with an ID); Non-goals (what the feature deliberately won't do); Success metrics (how we know it works, one to three measurable lines); Tests (for each requirement, one or more Given/When/Then scenarios, each with its test, last result and date, and not enforced when no test passes). Nothing else goes on the page. <!-- reviewed 8a8b477d -->
- DOC-2: **Reviewed 2026-11-08** The PRD is mine. I review the PRD as a whole (Problem, Usage, Requirements, Non-goals and Success metrics) and mark it Reviewed with a date; only I can do that. After it, nothing in Problem, Requirements, Non-goals or Success metrics changes unless I un-review it; Usage updates with the commands, and any change to it shows as changed since my review, under Needs you, until I review it again. <!-- reviewed e3f09268 -->
- DOC-3: **Reviewed 2026-11-08** Tests follow on their own. Once I review a PRD, the loop writes Given/When/Then scenarios and tests for each requirement, links each to a regression row, and keeps them in step when a requirement changes; I never write or manage tests. <!-- reviewed ffdc90c7 -->
- DOC-4: **Reviewed 2026-11-08** One command enforces it: checks all required docs against the template, code and tests, fixes what's mechanical, lists wording to rewrite; the release step runs it on every goal before merging; I can run it myself. It never deletes a page, never overwrites a page it didn't write unless I name it, and the last publish can be undone. <!-- reviewed 72374942 -->
- DOC-5: **Reviewed 2026-11-08** Required docs: every repo keeps up to date one wiki page per feature, one GitHub milestone per feature linked from its page plus a Backlog milestone, and a release note for every release; each goal's pull request lands in its feature's milestone. <!-- reviewed f4c8ca82 -->
- DOC-6: **Reviewed 2026-11-09** A feature page's Usage is written as what the owner asks the agent, a skill command or a plain request, and names no script file. <!-- reviewed ec0e28c5 -->

## Non-goals

- It never writes or reviews the owner's PRD for them: only the owner marks a PRD or a requirement Reviewed.
- It never deletes a wiki page, and never overwrites a wiki page it didn't write unless the owner names it.
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
