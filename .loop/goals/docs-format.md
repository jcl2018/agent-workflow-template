# Make the documentation format enforceable and apply it: Home is one features table, each feature has a natural-language front door, API-style Usage, bulleted Requirements, a user-perspective Problem, a linked Tests table, one full Tests page, and every issue on a milestone (owner, 2026-11-09). PRD: Documentation DOC-4..DOC-11

- Slug: docs-format
- Touches: skills/workflow-docs, skills/workflow-regression, skills/workflow-health, skills/workflow-setup, docs/wiki, README.md, .loop/regression.tsv, .loop/docs.tsv, dev/toy

## Done lines

Frozen. A wrong done line needs a new goal.

1. The Documentation PRD page adds DOC-4..DOC-11 with the wording in the operation session's draft (docs-format-draft.md), Unreviewed for the owner's final review
2. docs.py check enforces each of DOC-4..DOC-9 (Home table columns and nothing else; README How-to-use sections are phrases not commands; Usage entries carry syntax, output and refusals; Requirements are bullets; Problem has no code-internals vocabulary; Tests is a table with the listed columns and links), each refusal naming the page, section and rule
3. A generated full Tests page lists every test grouped by feature with its latest result, date, run link and seen-failing mark, and each feature's Tests table links into it (DOC-10)
4. health flags an open issue with no milestone, and each feature page links its milestone (DOC-11)
5. Home, the README How-to-use sections and every feature page are rewritten to pass the new checks, keeping each requirement's meaning; meaning changes are listed in the PR for the owner
6. A toy test proves each check fails on a bad page and passes on a good one, seen failing first; docs check and health stay green
7. The PR body gives the owner one review list: each page and what changed, for a single final review

## Verify by hand

1. Open `docs/wiki/Home.md`.
   Expect: the title, `## Features` and one table with Feature, What it does, How to use and Milestone; seven rows,
   nothing else.
2. Open the README on GitHub and click a Home row's "How to use" link.
   Expect: it lands on that feature's "How to use" table of phrases you can say, with no command syntax.
3. Open `docs/wiki/Delivery.md`.
   Expect: Problem as "I ..." bullets, Usage as one `command — what it prints and refuses` bullet per command,
   Requirements under Functional and Non-functional with sub-bullets, and Tests as a table whose test names link to
   the Tests page.
4. Follow one test link into `docs/wiki/Tests.md` (on the published wiki, after release).
   Expect: it jumps to that test's row under its feature, with result, date, run link and seen-failing date.
5. Run `python3 skills/workflow-docs/scripts/docs.py check`.
   Expect: `DOCS OK: 8 pages`.
6. In a scratch copy, change a word in any page's Problem to `script`, then run the same check.
   Expect: `FORMAT <Page>:<line>: Problem: DOC-8 ...`, naming the page, line, section and rule.

## Review list for the owner (one final review)

**Documentation requirements.** The draft's DOC-4..DOC-11 map to the page as follows:

| ID | Requirement |
|---|---|
| DOC-4 | Home is one table |
| DOC-5 | Front door |
| DOC-6 | Usage API |
| DOC-7 | Requirements in bullets, grouped Functional and Non-functional |
| DOC-8 | Problem |
| DOC-9 | Tests table |
| DOC-10 | Tests page, issue milestones and release notes (the draft's DOC-10 and DOC-11) |
| DOC-11 | Safe publish (added by the owner) |
| DOC-12 | Fast check (added by the owner) |
| DOC-13 | Same answer every time (added by the owner) |

The old DOC-4..DOC-6 (one command enforces it, required docs, Usage as asks) were lifted on the owner's word and
replaced.

**Pages.** Each was copied verbatim from the owner-approved text, except the machine lines (marker, milestone URL,
review line) and Tests, then stamped Reviewed with the owner's words:

- Documentation: DOC-1..DOC-13.
- Delivery: DEL-1..DEL-9, plus the `merge.py` output sentence.
- Monitoring: MON-1..MON-12. The Problem is in three bullets. MON-1..3 and MON-5 keep their reviewed lines, split
  into sub-bullets from their own words.
- Regression: REG-1..REG-9. REG-4 runs on the Automation schedule.
- Health: HLT-1..HLT-9.
- Setup: SET-1..SET-10. The Problem says "any agent that reads skills" and "every command".
- Automation: AUT-1..AUT-7.
- Home: one features table, approved.
- README: a How to use table per feature, approved. Home's old text moved unchanged into the README's
  "About this repo".
- Tests: generated.

**Usage written by the worker, not seen word for word by the owner.** These pages' Usage was reshaped into the
approved bullet form, with real output and refusals read from the code: Monitoring (11 commands), Regression (7),
Health (4: review and triage come when built), Setup (4), Automation (3).

**Meaning changes:**

- Tests moved to a new requirement:
  - The old DOC-4 tests (stale pages, audit, counts, publish refusal) now guard DOC-1. refuse-replace guards DOC-11.
  - The old DOC-5 tests (milestones, release note) now guard DOC-10.
  - The old REG-6 tests (suite once in qa, reuse, affected runs) now guard REG-4.
  - ci-summary guards AUT-1, as on main.
- The Usage rule changed. Usage may now name routines, as the approved pattern does. The old "names no script file"
  rule is gone; a command must be in its skill's Command map.
- DOC-1 still says Problem is "two or three lines", and the cap default is now 10 (15 in this repo). Reviewed DOC-1
  says "default 6". The owner should reword DOC-1.
- DEL-5's reviewed text refers to "(DOC-4)", meaning the old one-command requirement. That reference now dangles.
- Reviewed requirement lines stay long, with sub-bullets under them. Short titles appear where the owner approved new
  text.
- The wording defect test now checks that REG-1, REG-2 and DEL-1 carry the owner's latest sealed words, not the
  2026-11-08 text.

**Checks fitted to the approved text:**

- DOC-6 needs syntax and what it prints. It can't require refusals, because the approved `render` entry lists none.
- DOC-7 dropped the 30-word, one-sentence limit on sub-bullets.

**Behavior changes:**

- criteria_max now defaults to 10, and this repo sets it to 15.
- Health reads open issues from GitHub and flags any without a milestone. An unread list never turns it red.
- Tests are tables, plus one generated Tests page. The results file has a run column holding the commit, or the
  Actions run in CI.
- `review`/`unreview --user` with no terminal needs LOOP_OWNER_WORDS (issue 133).
- Guide pages are allowed (issue 125).
- `docs.py check --base` ignores commits merged in from the base (issue 156).

**Issues.** All 53 open issues are on a feature milestone, none on Backlog; #129 and #142 went to Delivery. Fixed
here: 125, 130, 133, 156. 104..107 were already fixed in v0.14.0; their rows now run and pass here.

**Merged goals.** docs-count-gaps (issues 104..107) and prd-stamps (every approved page stamped with the owner's
words).

**Not enforced yet: owned by queued goals.** Health warns on these, and fails one only if it stays untested 7 days
past its Reviewed date (HLT-2):

| Requirements | Goal that builds the tests |
|---|---|
| AUT-6, AUT-7 | automation-email |
| DEL-6, DEL-7, DEL-8, DEL-9 | delivery-prd |
| HLT-7, HLT-8, HLT-9 | health-prd |
| MON-6, MON-7, MON-8, MON-9, MON-10, MON-11, MON-12 | monitoring-prd |
| REG-6, REG-7, REG-8, REG-9 | lane-control |
| SET-6, SET-7, SET-8, SET-9, SET-10 | setup-adopt / setup-sync |

**Added during review:**

- Health's not-enforced grace, decided in the operation session under full auto from the owner's HLT-2 and REG-1/DOC-1
  wording. It fixes #118.
- The review's three critical fixes:
  - Run cells are empty outside CI, so concurrent goals merge cleanly.
  - Toy tests are safe on CI runners.
  - A reviewed requirement's seal now covers its sub-bullets.
- Re-sealing: every stamped requirement on the seven pages was re-sealed on the same text with the owner's same words.
- Smaller fixes:
  - The health workflow reads issues with the job token.
  - Issues the template opens land on Backlog.
  - Banned words are caught in the plural.
  - The guide marker is refused on requirement pages.
  - `--base` uses origin only.

**Issues moved to milestones:**

- Before the run: 53 open issues (none left on Backlog).
- During qa: #184..#276, the regression issues main's CI opened with no milestone, moved to Regression.

**Known, not from this branch:**

- Nightly row lanes-trace fails, as it does on main (issue #173).
- Main's last three CI runs failed (v0.20.0..v0.21.1).
- A local `regression.py run` still opens issues with no milestone. regression.py is near its size limit.
- The `--user` review stamp is honour-system: LOOP_OWNER_WORDS records the quoted words but can't prove them.

Fixes #118, #125, #130, #133, #156.
