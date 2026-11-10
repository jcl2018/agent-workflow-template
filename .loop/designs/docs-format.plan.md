# Plan: docs-format

## Implementation plan

Goal: make the documentation format enforceable and apply it (design: `.loop/designs/docs-format.md`; done lines in
`.loop/goals/docs-format.md`). Owner on the cap: "for the documentation, I want you to make that cap as like a config
as well, and probably do that as 10 as default."

1. Make room in `criteria.py`, which is at 20356 of 20480 bytes.
   - Move the Tests rendering (`scenario()` and `table()`, plus their helpers) into a new
     `skills/workflow-docs/scripts/pageformat.py`.
   - `criteria.py` keeps thin calls to it, so `criteria.py render` still works.
   - `criteria_of()` treats an indented `  - ` line under Requirements as the requirement's sub-bullet, not a
     CRITERION. The requirement line's hash (group 4 of `LINE`) is unchanged, so reviewed stamps don't trip.
   - The PRD `R=` fingerprint covers the whole Requirements section, so sub-bullets count there. That is fine,
     because no PRD on main is Reviewed.
   - Audit `counting.py`, `audit.py`, `prd.py` (convert/new) and `tests.py` for readers of requirement lines, and
     make each skip sub-bullets.
2. Raise the cap default from 6 to 10.
   - `criteria.py` fallback (one constant).
   - `skills/workflow-setup/scripts/settings.py` default and `_help`.
   - `skills/workflow-setup/references/settings.md`.
   - `skills/workflow-docs/references/template.md` (default 10).
   - This repo's `.loop/config.json` (`criteria_max: 10`).
   - The commit quotes the owner.
3. Add format checks to `pageformat.py`, called from `docs.py contract`. Each refusal reads
   `FORMAT <Page>: <Section>: DOC-n <what>. Fix: <how>`.
   - **DOC-4, Home.** Only the marker, `# title`, `## Features` and one table with the header
     `| Feature | Description | Page | How to use | Milestone |`.
     - One row per feature page in `docs.tsv`, Tests.md excluded.
     - Page cell `[X](X)` must name an existing page.
     - How-to-use cell links `README#how-to-use-<slug>` (an anchor that exists in README).
     - Milestone cell is a milestone URL.
   - **DOC-5, README front door.** `## How to use` has one `### <Feature>` per feature page.
     - Each section has at least one `- "<phrase>" — <what happens>` bullet.
     - No backtick code, and no line starting with `/`, `python` or `bash`.
   - **DOC-6, Usage API.** Usage holds only `### `/skill verb ...`` entries.
     - Each entry has `- Syntax:`, `- Prints:` and `- Refuses:` bullets (`- Arguments:` optional), and nothing else
       but blank lines.
     - The existing USAGE rules stay: no script names, and each verb must be in the Command map.
   - **DOC-7, Requirements.** Each requirement has at least one sub-bullet.
     - Each sub-bullet is one sentence of at most 30 words.
     - An Unreviewed requirement line is at most 20 words. A Reviewed line is exempt: its words are locked by DOC-2.
   - **DOC-8, Problem.** No backticks, no path or extension token (`/x`, `.py`, `.json`, `.tsv`, `.md`), and no word
     from the template sheet's new `problem_banned` rules key.
   - **DOC-9, Tests.** The section must equal the rendered table (the existing TESTS staleness check, now on the
     table).
     - Every requirement has a row (`not enforced` when none passes), and every defect row is present.
     - The template sheet's rules block and its Layout and Example text are updated to the new shapes. The sheet stays
       the one definition.
4. Render the Tests table and the full Tests page (DOC-9, DOC-10).
   - The per-page Tests section becomes one table:
     `| Test | Kind | Guards | Checks | Last result | Report |`.
     - Report is `[report](Tests#t-<row>)`.
     - Defect rows are in the same table, with the kind `defect` and guards set to the issue link and state.
   - `render` also writes `docs/wiki/Tests.md` (marker, `# Tests`, then one `## <Feature>` per page). Each section
     has a table `| Test | Kind | Guards | Result | Date | Run | Seen failing |`, and each first cell is
     `<a id="t-<row>"></a>` plus the row id.
   - `docs.py check` reports `STALE Tests: ...` when Tests.md differs from a fresh render.
     - Tests.md is listed in `.loop/docs.tsv` as generated, with paths `.loop/regression.tsv,.loop/regression-runs.tsv`.
     - It is excluded from the PRD contract and from the Home table.
   - **Run link.** `regression.py run` (not `--reuse`) writes a fourth column `run`. In CI it holds
     `$GITHUB_SERVER_URL/$GITHUB_REPOSITORY/actions/runs/$GITHUB_RUN_ID`; otherwise it is empty and shown as `local`.
     Readers accept 3- and 4-column files.
5. Add the health rule `issue-milestones` (DOC-10).
   - `gh issue list --state open --limit 500 --json number,title,milestone`.
   - FAIL per issue with no milestone, fix `/workflow-docs milestones` or `gh issue edit N --milestone <Feature|Backlog>`.
   - UNREAD when gh fails or isn't authenticated.
   - New module `skills/workflow-health/scripts/issues.py`, because `health.py` is at 18403 bytes.
   - RULES gets the new name. MAX_RULES goes 12 → 13 with a comment ("13 for DOC-10"). It joins the docs family.
   - A negative control in `controls.py`, run through fakegh.
   - The feature page's Milestone line stays required (existing rule).
6. Documentation page requirements, as the operation session relayed them.
   - DOC-1..3 unchanged.
   - DOC-4..6 reworded to Home table, front door and Usage API. They go back to Unreviewed with
     `criteria.py unreview DOC-4 DOC-5 DOC-6 --user`; the commit quotes the relay.
   - DOC-7..10 added (DOC-10 merges the draft's DOC-10 and DOC-11).
   - Regression rows re-pointed:
     - old DOC-4's 14 rows → DOC-1;
     - old DOC-5's 4 rows → DOC-10;
     - `usage-no-script` stays on DOC-6;
     - `usage-agent-requests` is replaced by a `usage-api-shape` row.
7. Rewrite the pages.
   - Merge `origin/main` first.
   - Home: the features table only. Its essay (the no-gates notice, reading the charts, proven, not proven, gaps)
     moves to README sections unchanged in meaning.
   - README: a new `## How to use` with six `### <Feature>` phrase lists.
   - The six feature pages: a user-perspective Problem (the `Skill:` and code detail move to Usage), Usage as API
     entries, Requirements with sub-bullets (reviewed lines verbatim), and Tests re-rendered.
   - Keep each requirement's meaning. Record each meaning change for the PR list.
8. Tests.
   - `dev/toy/test-docs-format.sh`:
     - a bad and a good page for each of DOC-4..DOC-9, with the refusal naming page, section and rule;
     - Tests.md generated, stale and fresh;
     - the 4-column runs file and the `local` fallback;
     - health issue-milestones with fakegh (an issue without a milestone FAILs, with one passes, gh failing reads
       UNREAD);
     - the cap default of 10 from setup;
     - sub-bullets not read as criteria, and a reviewed line's stamp holding.
   - One regression row per check (level land), each made red with `regression.py red ID --break ...`.
   - Update existing toy tests that assert the old Tests bullet format or the cap of 6.
   - `docs.py check`, `criteria.py render --check` and `health.py check` green on this repo.
9. Verify by hand in the goal file:
   - open Home and see one table;
   - open README How to use;
   - open a feature page Tests table and follow a report link into Tests.md;
   - run `docs.py check`.
10. PR body review list: the DOC mapping table, each page and what changed, every meaning change, the moved Home
    content, the cap change with the owner's words, and the DOC-4..6 unreview.

## Amendments after review (CEO, DX and Eng reviewers; the outside voice was unavailable) and the owner-approved pattern

The owner approved the docs pattern in the operation session ("Yes, approve the documentation pattern."). Every page
matches it, and deviations go in the PR review list. These amendments override steps 1-10 where they differ.

11. **Pattern shapes.** Checks and rewrites follow these:
    - **Home:** `# <repo>`, `## Features` and one table `| Feature | What it does | How to use | Milestone |`.
      - Feature links to its page, and How to use is the absolute README URL with the `#how-to-use-<slug>` anchor.
      - The Milestone cell matches `/milestone/\d+` by regex only. Whether the milestone exists is left to health.
    - **README:** `## How to use`, then one `### How to use <Feature>` per feature. Under each, one line ("Say these
      to the agent:"), then a table `| You say | What happens |`.
      - Each You-say cell is a quoted phrase. No backticks, and no `/`, `python` or `bash` at a cell start.
    - **Problem:** 1 to `problem_lines` bullets, at least one in the first person (I, my, me), with no code tokens.
    - **Usage:** one `### `<syntax>`` entry per command, then `- Prints:` and `- Refuses:` bullets (`- Does:` is
      optional).
      - The heading command must be listed in that skill's `## Command map` (either column). This replaces the old
        no-script-name rule, because the pattern shows routine syntax. That is a meaning change for the owner: the old
        DOC-6 tests `usage-no-script` and `usage-agent-requests` are rewritten for the new rule.
      - The Refuses text may quote messages. The pattern's prose form becomes labeled bullets so the check can read it;
        that deviation goes on the list.
    - **Requirements:** the `- ID: **mark** text` line stays (the tools need it), with `  - ` sub-bullets that split
      the wording. Reviewed lines stay verbatim. The pattern hides the full line; ours shows it, which goes on the list.
    - **Tests:** `| Test | Kind | Guards | Checks | Last result |`.
      - Test is `[row](Tests#t-<slug>)`. Checks is the row's Given/When/Then text, kept because DOC-3 (Reviewed)
        promises scenarios; the pattern used short phrases, which goes on the list.
      - Every requirement has a row, with `not enforced` when no row passes, and every defect row is present.
12. **The grammar the checks read** (Eng F7, F8, F9), defined in the template sheet's rules block:
    - A sub-bullet is exactly `  - ` under a requirement line. An orphan sub-bullet or deeper nesting is refused.
    - Words are whitespace tokens after `[text](url)` becomes `text` and backticks are stripped. One sentence means
      no `[.!?] ` followed by a capital inside the bullet.
    - Path and extension tokens use bounded regexes (`(?<![\w/])/[\w.-]+/`, `\.(py|sh|json|tsv|md)\b`).
      Banned words are whole-word and case-insensitive, and the list is code-only: script, function, regex, json, tsv,
      stdout (CEO F10).
    - The sub-bullet seal: DOC-2's line seal covers the requirement line only. Sub-bullets are covered by the PRD
      `R=` fingerprint once the page is Reviewed. Tests cover review, unreview and rewrite on pages with sub-bullets.
13. **Refusal form** (DX F8): `FORMAT <Page>:<line>: <Section>: DOC-n <what> (got <value>). Fix: <how>`.
    - `STALE Tests:` lines carry `Fix: /workflow-docs render`.
    - `render` writes every file to a temp file, then renames it, and prints `WROTE <file>` for each.
14. **Generated pages** (Eng F3, F4, F6):
    - One `GENERATED = {"Tests"}` constant, honored by `problems()`, `contract()`, `counting.counts`, the audit and
      the DOC-4 row check.
    - Tests.md is rendered from `tests.entries()` plus anchors, never from a second format.
    - If `tests.py` changes, the embedded copy in `.github/workflows/regression.yml` is re-synced and the
      test-summary sync check stays green.
    - The release step's audit fix re-renders Tests.md together with page Tests.
15. **Run link** (Eng F1, DX F7):
    - CI doesn't write `regression-runs.tsv`; the local `regression.py run` does.
    - The fourth column `run` holds the commit the run was recorded on, rendered as a link to that commit.
    - It holds the Actions run URL only when `GITHUB_SERVER_URL`, `GITHUB_REPOSITORY` and `GITHUB_RUN_ID` are all
      set.
    - The runs read/write moves into a helper in `tests.py` (Eng F2), so `regression.py` shrinks. The header
      becomes four columns, three-column files still read, and a test proves the fourth column survives a run.
16. **Health** (DX F1, F3; Eng F10; CEO F13): the issue check joins the existing `docs-check` rule as extra rows, so
    there's no new rule and MAX_RULES stays at 12.
    - It runs `gh issue list --state open --limit 1000`.
    - If exactly 1000 come back, or gh fails, it prints one UNREAD row with the gh error and
      `Fix: gh auth login, then rerun`. UNREAD doesn't make HEALTH red (verified in the code). Offline behavior is
      stated in the Health page's Usage.
    - **Backfill before enabling:** every open issue with no milestone gets Backlog or its feature milestone. Issues
      on Backlog that clearly belong to a feature move to that feature's milestone, as the pattern shows. Each move is
      listed in the PR.
17. **The cap** (DX F9, Eng F18): one `CRITERIA_MAX_DEFAULT = 10` in `criteria.py`, used by the docstring, the default
    and the refusal. A test asserts that setup's default equals it.
18. **Portability** (DX F11, F14): a `format` key in the template sheet's rules block lists the enabled DOC rules
    (default all). Repos set up from this template get the checks through workflow-docs. Setup's adopt report lists
    FORMAT findings, and the release note documents the upgrade.
19. **Reader audit** (Eng F17): `counting.py`, `audit.py`, `prd.py`, `tests.py features()`, `judge.py` and the
    `regression.yml` copy each skip sub-bullets. A toy assertion covers each.
20. **Import shape** (Eng F12): `pageformat.py` is pure (data in, lines or findings out), and `criteria.py` imports it
    inside functions.
21. **Owner review list additions** (CEO F3, F4, F5, F11; DX F12):
    - DOC-1 still says "default 6". It is Reviewed and contradicted by the cap change, so the owner rewords it in the
      final review.
    - DEL-5 refers to "(DOC-4)", meaning the old one-command requirement, and that reference now dangles.
    - The old DOC-4 guarantees (never deletes a page, never overwrites one it didn't write, the last publish can be
      undone) move into the Documentation Non-goals, so they stay stated. Their tests guard DOC-1.
    - Reviewed lines stay long, with sub-bullets under them. A short title is proposed for each, for the owner to
      accept.
    - A `## Behavior changes` section covers: cap 6 → 10, Usage now naming routines, health reading GitHub issues, and
      the Tests format.
22. **Order** (Eng F13): each check lands in the same commit as the page rewrite that satisfies it, so every commit
    keeps `docs.py check` green. Nothing is pushed before `goal.py pr`.
23. **Concurrency** (CEO F12): after each merge of main, check that no PRD is Reviewed before relying on the `R=`
    widening. Re-render Tests after each merge.

Decisions kept as written (recommended `a` at the gate):
- d1: unreview DOC-4..6 on the owner's approval, as the operation session relayed it.
- d2/d4: Home stays hand-written and checked; the done line needs the check.
- d3: one goal; the done lines are one goal.
- d5: the run link uses the commit link plus the CI URL when set.
- d6: health is amended as in item 16.
- d7: the order is amended as in item 22.

## Review record

- Plan review: gate pending (gate_rev=1). CEO reviewer 14 findings, DX reviewer 14, Eng reviewer 18. The outside voice was unavailable in all three phases.

## Amendment: merged goals (owner, 2026-11-10)

The owner asked to regroup the work as one goal per approved PRD and to merge similar goals: "rewrite the goals ... to
like 3 goals to implement these 3 based on the PRD. If there are any conflicting goal or the similar goal, merge them."
docs-format is now the goal for the Documentation PRD (DOC-1..DOC-13), and two held goals merge into it. Their done
lines are carried here and in the PR. The goal file's done lines stay frozen.

24. **docs-count-gaps (issues 104, 105, 106, 107).** These were already fixed and merged in v0.14.0, and each defect
    row was seen failing on 2026-11-09. This branch runs each row (PASS 2026-11-10) and refreshes the issue states
    (closed), so the Tests show them run and passing.
25. **prd-stamps.** Each feature page whose text the owner approves is copied in verbatim, apart from the machine lines
    and Tests. Each requirement and the PRD are then stamped Reviewed with `criteria.py review --user`, quoting the
    owner's words in the commit. Done so far: Documentation and Delivery.
26. **Issues 125, 130, 133, 156** (added by the owner's regroup, next to 104..107). Each one gets a defect row in
    `dev/toy/test-docs-issues.sh`, seen failing on 2026-11-10 and then passing:
    - 125: guide pages;
    - 130: the milestone comes from the page's Milestone line;
    - 133: LOCKED hints never suggest review, and `--user` with no terminal needs LOOP_OWNER_WORDS;
    - 156: `--base` ignores commits that came in by merging the base. The ship skill's own gate is outside this repo.

    Issue 132 is closed as covered, and 155 as won't fix per DOC-11. The operation session handles both.
