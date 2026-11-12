# Plan: milestone-freeform

Goal: `.loop/goals/milestone-freeform.md` (done lines and Verify by hand are frozen and belong to delivery; not restated or reopened here). Design: `.loop/goals/milestone-freeform.design.md` (APPROVED).

## URGENT, outside this plan

None.

## Implementation plan

Order: un-review and reword first (the commit that seals the wording), then code removals per skill, then the feature tag, then fixtures and rows (commit before `regression.py red`), then docs and gates. Every hunk touches only milestone lines; no function is moved or renamed, so the parallel estimate-accuracy work on the same health files rebases hunk by hunk.

### 1. Requirement lines: reword through the owner's un-review (done line 1)

- Reviewed lines are locked (DOC-2). Run `python3 skills/workflow-docs/scripts/criteria.py unreview DOC-4 DOC-10 HLT-2 HLT-4 AUT-2 AUT-3 SET-1 Documentation Health Automation Setup --user` with `LOOP_OWNER_WORDS` set ONLY to the owner's quoted words from the goal file's title line, verbatim (the quote inside the parentheses, nothing added). If the tool asks for anything more, the build stops and reports instead of working around it. The command checks every argument before writing, so a refusal leaves nothing half-done; on a refusal stop and report, never hand-edit a stamp.
- Then edit the lines (wording from the design, polish allowed, meaning not): DOC-10 (milestones optional, free form, planned by version such as v1.0; nothing requires a milestone and no check fails or warns for lacking one); DOC-4 (Home keeps four columns, Milestone optional: empty or a link); HLT-4 (findings are issues tagged with their group or kind and their feature; a milestone only when the owner puts one); HLT-2 (`issue to feature`; drop `every open issue on a milestone` from Docs); AUT-2 and AUT-3 plus the Automation Problem line and success metric (tagged with the feature); SET-1 (no milestone per feature, no Backlog; issues tagged with the right feature). Also the Problem, Success metrics and Usage text of Documentation, Health, Automation, Setup, the Home table text and the Regression Usage line, and `docs/wiki/design-guide.md` lines 21 and 52.
- Then `python3 skills/workflow-docs/scripts/criteria.py render` for the Tests tables. Home has no Review line and Regression is already Unreviewed, so neither needs the command. Delivery, Monitoring and Guardrails keep their text.
- The commit message quotes the owner's words. Each changed line ends as `- ID: **Unreviewed** text`, each page as `Review: **Unreviewed**`.
- Add `## Wording changes` to `.loop/goals/milestone-freeform.md` (below the frozen done lines, never touching them): before and after for each changed line, committed before `goal.py pr`, so the PR body (goal file plus Result) shows the wording. The PR body also lists each remaining `git grep -n -i "milestone\|backlog" -- docs/wiki skills` hit with its class (optional, free form, display, or owner command).

### 2. Code removals per skill (done line 2)

Paths are under `skills/<skill>/scripts` unless named. Hunks are milestone-only.

**workflow-health**
- `issues.py`: delete `rows()`, `unread()`, `on_github()`, `LIMIT`, `RULE`, `FIX_UNREAD` (the docs-check milestone rule). Keep the other helpers. Add `feature_label(page)` and `feature_group(issue)` (step 3); `feature_of`, `covering`, `open_findings`, `listing`, `close` group and filter by feature instead of milestone (Backlog default goes).
- `health.py`: `docs_check` returns `docs_rows(root)` only; `hard_unread` loses the milestone exception; docstring line.
- `report.py`: delete `SOFT` and its one use; change the `--feature` help text only.
- `controls.py`: delete `f_docs_issues` and its registration (a gone rule needs no control).
- `judge.py`: the one hunk at line 252 (a feature's open issues by `feature_group`); line 286 (milestone read as display data) stays.
- `file.py`: stop placing on a feature milestone; delete the `BACKLOG` fallback, the `doesn't exist` and `couldn't be set` NOTEs, the Backlog make step, the `move` act and the `--milestone` args; keep `placed=` parseable, written empty; the `update` act backfills the feature label on an open health issue that lacks it. An issue the owner put on a milestone is never touched.
- `automation.py`: `backlog_args` returns no milestone (digest created with none); digest groups by feature with a milestone title as a suffix when one exists; drop the unreadable-titles note. `rounds.py` is not edited (keeps its `N:M` tokens).
- `workflows.py`: delete the `milestone.py new --all --live` step, its `::warning::` and the comment.
- `milestone.py`: delete `features`, `goal_feature`, `new --all`, `new FEATURE|backlog`, `link_page`, `attach` and the not-a-feature refusal. Name-based: `new TITLE [--live]` prints `CREATED TITLE`, `EXISTS TITLE` (second run creates nothing) or, without `--live`, `WOULD create milestone TITLE`; with `--live` and no token it prints a `REFUSED: could not ...` line (exit 1). `move ISSUE TITLE|none [--live]` puts the issue on an existing title or clears it; an unknown title prints `REFUSED: no milestone TITLE. Fix: milestone.py new TITLE --live` (exit 1). Owner commands only, never run by a check, rule or setup step.
- `rules.py`, `defects.py`, `rounds.py`: untouched.

**workflow-docs**
- `audit.py`: delete `milestone_trouble`, `milestones`, `milestone_of`, `milestone_line`, their call (164-166) and docstring lines; the audit no longer calls gh for milestones and writes no `Milestone:` line.
- `pageformat.py` `home()`: delete the Milestone-cell link refusal (132-134); the four-column header, row count and README-link checks stay.
- `template.md` (26, 73-75, 138), `SKILL.md` (65-66, 77), `commands.md` (244): milestone optional, free form, no Backlog. The Usage entry `milestones` becomes `milestone new TITLE | move ISSUE TITLE`, with the SKILL.md command map updated in step so the Usage-versus-code rule passes.
- Kept unchanged: `entry.py` (START.md Milestone column, `none` when absent), `prd.py`, `criteria.py`, `render.py`.

**workflow-setup**: `seed.py` (delete the milestone note), `setup.py` (drop the NEXT clause). `survey.py` and `docs/designs/setup-fit.md` stay (roadmap headings read as feature names, not GitHub milestones).

**workflow-delivery**: `goal.py` `pr`: delete the `milestone.py attach SLUG --live` hook (392-394) and the docstring line. `fit.py` `SURFACES`, `commands.md` 420 and `test-delivery-prd.sh` 209 (`github:milestones` as a touch surface) stay.

**workflow-regression**: `actions.py` (the workflow generator): delete `place()`, the milestone make with `FILE_FAILED`, the `by_number` patch and move-on-repeat; add the `--label feature:<Page>` to the defect issue. `SKILL.md` 113 and `commands.md` 41 reworded.

### 3. The `feature:<Page>` label (done line 2: issues still tagged with feature or group)

- `issues.feature_label(page)` = `feature:` plus the page name cut to 50 characters, kept as written; one helper for writing and reading. Two page names sharing their first 50 characters collide: accepted, noted in `commands.md`.
- `issues.feature_group(issue)` compares the issue's labels with `feature_label(p)` for each page in `.loop/docs.tsv` (case-insensitive); never parses a label back. With no feature label it falls back to the issue's milestone title only when that title equals a known page name (an old feature milestone); v1.0, Backlog or no milestone gives `No feature`, so a free-form milestone never becomes a feature.
- Binding limit (coordinator): the label is CODE ONLY in this goal. No label is created and no issue is labelled on GitHub: `gh label create` and `gh issue edit` are out of scope for the build and for any run of it; only the fake gh in the toy tests exercises them. Real labelling waits for the owner's issue-triage.
- `file.py` and `actions.py` (code paths, run only against the fake gh in this goal) create the label with `gh label create --force` beside `health:<group>` and pass `--label feature:<Page>` (none when the finding fits no page). A failed write stays the existing per-issue `FAILED <action>: <error>` line.

### 4. What stays (done line 3)

Display of an existing milestone: Home cell (any text, empty, `v1.0` or a link, never validated), START.md Features column, the digest suffix, triage and judge's own-milestone display, `issues.fetch` fields. The live board is untouched (MON-4 is Reviewed, not in this goal). Version milestones like v1.0 work as before, made on GitHub or by `milestone.py new v1.0`. `milestone.py new` and `move` remain. The fake gh keeps `--milestone` support. Backlog is never made or a fallback; an existing one is read like any other.

### 5. Fixtures and fake gh

Rewrite the toy tests that assert the old rules: `test-milestones.sh`, `test-docs-issues.sh`, `test-health-issues.sh`, `test-docs-command.sh`, `test-docs-format.sh` (line 123 now expects a free-text cell to pass), `test-automation.sh`, `test-automation-email.sh`, `test-health-prd.sh` (h4), `test-regression.sh`, `test-stale-groups.sh` (drops its milestone-list leg), `test-prd.sh`. `fakegh/` keeps `--milestone` and gains label create/list for `feature:` labels if not already general. Every toy test sources `dev/toy/reap.sh` and keeps a precise `# reads:` header; `lanes_cli.py check` and `dev/toy/test-tree.sh` must pass.

### 6. Regression rows (12 new, 11 retired, 5 rewritten)

Add each with `regression.py add` (key `milestone-freeform:N`), commit, then `regression.py red <id> --break "<cmd>"`; the break is `git checkout v0.27.4 -- <file>` restoring the old rule. Because estimate-accuracy edits some of the same files, also run the toy once on the broken tree and keep only a red whose failing line is the row's own milestone assertion (the row command greps that PASS line); put the failing line in the PR.

| New row (done line) | Break restores old rule in |
|---|---|
| `no-milestone-issue-ok` (2): open issue with no milestone, health check, no docs row names it, verdict unchanged | `issues.py`, `health.py`, `report.py` |
| `no-milestone-page-ok` (2): page with no `Milestone:` line, repo with no milestones, docs audit prints no MILESTONE line and writes nothing | `audit.py` |
| `home-milestone-optional` (2): Home cells empty, `v1.0`, link; docs check reports no Home milestone refusal | `pageformat.py` |
| `pr-no-milestone` (2): `goal.py pr` on the fake gh makes no `--milestone` call | `goal.py` |
| `health-file-no-milestone` (2): `file` tags `health:<group>` and `feature:<Page>`, places none, makes no Backlog; repeat updates and backfills the feature label; fix closes, return reopens | `file.py` |
| `regression-issue-no-milestone` (2): CI block on fake gh tags the defect with its feature, no milestone read or made, no `FILE_FAILED` | `actions.py` |
| `digest-no-milestone` (2): digest groups by feature, shows a milestone title when present, created with no milestone | `automation.py` |
| `setup-no-milestone-step` (2): setup on a toy repo, no seed note, NEXT line or file mentions making milestones | `seed.py`, `setup.py` |
| `health-workflow-no-milestone` (2): written health workflow has no milestone step or warning | `workflows.py` |
| `milestone-v1-free-form` (3): `new v1.0` twice, `move N v1.0`; one milestone, issue on it, unlabeled issue on v1.0 or Backlog is `No feature`, Home, triage and digest show it | `milestone.py`, `issues.py` |
| `milestone-wording-unreviewed` (1): the four pages; the seven lines are `**Unreviewed**` and none says a milestone is required or per feature | the four pages |
| `milestone-rows-seen-red` (4): every row above has a `seen_red` date | clear one `seen_red` cell in `.loop/regression.tsv` |

Retired (assert the removed rule): `issue-no-milestone-fails`, `issue-milestone-passes`, `issue-closed-ignored`, `issue-gh-fail-unread`, `issue-truncated-unread`, `milestone-links`, `pr-in-milestone`, `aut-backlog-milestone`, `ci-issue-backlog`, `digest-backlog`, `update-in-place`. Rewritten to tag semantics (ids and dates kept only if still red on a break): `milestones-once` (now `new TITLE`), `hlt4-feature-milestones`, `aut-email-file`, `aut-email-regression`, `aut-email-digest`. `docs-milestone-line-issue-130` keeps its row and passes either way.

### 7. Docs and gates

- Wiki pages and `Tests.md` (generated by `criteria.py render`), `design-guide.md`, health `SKILL.md` 80, 98-100 and `commands.md`, regression `SKILL.md`/`commands.md`.
- Gates: `python3 skills/workflow-docs/scripts/docs.py check` prints `DOCS OK`; every changed script stays under 20,480 bytes (check `file.py`, `automation.py`, `issues.py`, `milestone.py` after the edit; the removals only shrink them but `issues.py` gains two helpers); each `skills/*/SKILL.md` under 150 lines; `lanes_cli.py check` and `dev/toy/test-tree.sh` pass; the skill listing gate (generated listing of Usage entries) is regenerated for the renamed `milestone` entry.
- Privacy: no private names, home paths or the owner's email in commits or the PR body (pre-commit hook patterns); the owner's words are quoted from the goal file only.
- Success check: `git grep -n -i "milestone\|backlog" -- docs/wiki skills` leaves only hits that say optional, free form or display, or name an owner command; the docs check and the health check show nothing about a missing milestone on a repo with none.

### 8. PR body: `## Wording changes`

The goal file's `## Wording changes` section (step 1) is the PR's wording view: before and after per line for DOC-4, DOC-10, HLT-2, HLT-4, AUT-2, AUT-3, SET-1 and the four page Review lines, each marked Unreviewed, plus the remaining-grep list and the failing line of each seen-red break.

## Failure modes

| Step | Failure | Handling |
|---|---|---|
| 1 | `criteria.py unreview` refuses (no owner words) | stop and report; no hand-edited stamps |
| 2 | Estimate-accuracy lands first and the same files move | rebase hunk by hunk; no function moved or renamed here |
| 2 | An old repo's open issues carry only a feature milestone | `feature_group` falls back to the milestone title when it equals a page name |
| 3 | Label write fails | existing per-issue `FAILED <action>: <error>` line, nothing new |
| 6 | Break goes red for an unrelated hunk | keep only a red whose failing line is the row's own assertion |
| 7 | A script passes 20,480 bytes | move helper code to a sibling module in the same skill |

## Review record

<!-- accepted:ceo -->
- BINDING LIMIT A (coordinator): the `feature:<Page>` label is CODE ONLY in this goal. The build and any run of it create no label and label no issue on GitHub: no `gh label create` and no `gh issue edit` against GitHub. The fake gh in the toy tests is the only gh that sees them. Real labelling waits for the owner's issue-triage. Verification: every toy test that reaches `file.py`, `actions.py` or `automation.py` runs with PATH resolving `gh` to `dev/toy/fakegh`, and the new rows `health-file-no-milestone` and `regression-issue-no-milestone` fail if the fake gh log is absent (proof the real gh never ran).
- BINDING LIMIT B (coordinator): `criteria.py unreview` is run with `LOOP_OWNER_WORDS` set ONLY to the owner's quoted words from the goal file's title line, verbatim (the text inside the quote marks of the parenthesis, nothing added, nothing trimmed but the outer quote marks). If the tool asks for anything more, the build stops and reports; it never works around the refusal and never hand-edits a stamp. Verification: the `reviews.tsv` entry in the git common dir shows exactly those words; `git diff` shows only `**Unreviewed**` rewrites on the named lines and pages.
- Deferred items (live backfill of feature labels on open GitHub issues, a docs check flagging two page names that share their first 50 characters) are listed in the PR body under `## Not in this goal`; no new check is added (design premise 3).
- The remaining plan stands unchanged: no check, rule, docs check, `goal.py pr` or setup step fails, warns or refuses for a missing milestone, with the row plan, wording, grep list and gates above.
- Spec-review corrections (state replacements for the Implementation plan text above): (1) the design guide is `skills/design-guide.md` (lines 21 and 52), not `docs/wiki/design-guide.md`; it is edited without un-review. (2) Row retirement: the build deletes the 11 retired lines from `.loop/regression.tsv` by hand (`regression.py` has no delete command); the 5 rewritten rows are replaced with `regression.py add`, which clears `seen_red` when the command changes, so each is seen red again with `red --break`. (3) `milestone-wording-unreviewed` covers the Review line of Documentation, Health, Automation and Setup and the seven requirement lines; Home table text, the Regression Usage line and `skills/design-guide.md` are reworded without un-review (Home has no Review line, Regression is already Unreviewed, the guide is not a PRD). (4) The ellipses inside the owner's quote stay in `LOOP_OWNER_WORDS`. (5) The generated CI workflow in `actions.py` includes a `gh label create --force` step before `gh issue create --label feature:<Page>` (code only; never run live in this goal); without it the issue create fails on a repo lacking the label. `.loop/config.json` has no milestone text and needs no edit.
- Fake gh: `dev/toy/fakegh/gh` is added to the section-5 edit list. Its routing sends `issue create` to `fake.py` only for `--label health`, `--milestone` or `--repo`; it is widened to also route `--label feature:`, and `label create` and `label list` are routed and recorded in `calls.log`. The two label rows assert on `calls.log` text and the recorded labels.
- Size gates: `skills/workflow-docs/SKILL.md` is at 149 of 150 lines, so its edits (65-66, 77, the command map) must be net zero lines or fewer; the gate is `wc -l skills/*/SKILL.md` all under 150.
- `feature_group`'s fallback (a milestone title equal to a page name still groups as that feature) is kept: it keeps old open issues on feature milestones grouped instead of turning every one into `No feature` on the day this ships. `milestone-v1-free-form` gains a leg: an issue on a milestone named like a page, with no label, groups as that page; one on v1.0 groups `No feature`.
- `milestone.py new TITLE` and `move ISSUE TITLE|none` are the smallest rewrite: today `new` takes a feature name and refuses a non-feature, which is the restriction; the REFUSED lines are the existing refusal style, not new checks (owner commands, never run by a check).
- `placed=` is written empty and a toy assertion proves `rounds.py` still parses an empty `placed=` marker field.
- Spec-review pass-two corrections (replacements for the Implementation plan text above): (1) every mention of `docs/wiki/design-guide.md` (steps 1 and 7) reads `skills/design-guide.md`. (2) Label length: GitHub caps a label name at 50 characters in total, so `feature_label(page)` is `feature:` plus the page name cut to 42 characters (whole label at most 50); the collision note in `commands.md` says two page names sharing their first 42 characters share a label (accepted, no check). (3) The `update` act's feature-label backfill on an open health issue is code that only the fake gh exercises in this goal (BINDING LIMIT A); the deferred item is the live backfill of existing GitHub issues. (4) Seen-red breaks are targeted: each `--break` reinstates only the old milestone rule (a patch built from `git diff v0.27.4 -- <file>` limited to the milestone hunk and applied with `git apply -R`), falling back to `git checkout v0.27.4 -- <file>` only where the old file still imports cleanly with the new helpers present; a red counts only when its failing line is the row's own assertion, never an ImportError or a crash. (5) `milestone-rows-seen-red` checks the other 11 rows only; its own red is clearing one `seen_red` cell. (6) The `controls.py` rule removal and the `hard_unread` exception are proven by `no-milestone-issue-ok` (a health check on a repo with an open no-milestone issue prints no docs row and the same verdict).
- Native CEO voice corrections accepted: (1) PR-body ledger: the PR body lists each of the 11 retired rows with the old rule it asserted and the row that replaces it, so the history is not silent; no `regression.py retire` command is built. (2) Sentinels: each new or rewritten toy row prints a unique sentinel line `PASS milestone-freeform:<id>` and `regression.py red` counts a break only when that sentinel is missing and the output holds no traceback or ImportError. (3) Day-one note: the PR body states that issues on Backlog, v1.0 or no milestone group as `No feature` until the owner's issue-triage labels them, with that as the expected before/after digest change; feature labels are code only until then. (4) Base: before step 1 the build merges `origin/main` (wiki-sync work landed there after v0.27.4 and touched `docs/wiki/Automation.md` and `Tests.md`), so the un-review and reseal run on the latest wiki pages, and no stamp is hand-merged.
<!-- /accepted:ceo -->

<!-- accepted:dx -->
- Owner-command messages (`milestone.py`), for the agent reader: (1) `new TITLE --live` with no token prints on stderr `REFUSED: no GitHub token, nothing created. Fix: set GH_TOKEN or run gh auth login, or drop --live to preview.` and exits 1. (2) `move ISSUE TITLE|none` with an unknown title prints `REFUSED: no milestone TITLE (issue N unchanged). Fix: milestone.py new TITLE --live` and exits 1; a gh failure on the move prints `REFUSED: could not move issue N: <error>. Fix: gh issue view N to see whether it moved before retrying` and exits 1. (3) Dry-run output is `WOULD create milestone TITLE (dry run; add --live)`; the design strings `CREATED TITLE` and `EXISTS TITLE` stay. (4) Usage errors keep argparse's own stderr message and exit 2; no custom code.
- A label write that fails in `file.py` or the generated CI step prints the existing `FAILED <action>: <error>` line naming the full label and adds the recovery clause `label feature:X may exist, issue not filed; rerun is safe (label create --force is idempotent)`.
- When `criteria.py unreview` refuses, the build's stop report names the missing input (the owner's words) and says nothing was written.
- Toy tests: the fake-gh-missing failure prints `FAIL milestone-freeform:<id>: calls.log absent, real gh may have run. Fix: put dev/toy/fakegh first on PATH`; a toy assertion proves a real label or issue write failure still surfaces as a `FAILED` line while `placed=` stays empty (empty means not placed on purpose, never a hidden failure).
- Docs: `skills/workflow-health/commands.md` gets three copy-paste owner lines with their output (`milestone.py new v1.0 --live` showing `CREATED v1.0` then `EXISTS v1.0`, `milestone.py move 42 v1.0 --live`, `milestone.py move 42 none --live`), one sentence that milestones are optional and only for planning by version, one sentence that to regroup an issue by feature the owner sets its `feature:<Page>` label (`gh issue edit N --add-label "feature:<Page>"`, an owner command never run by the build), and one sentence that a downstream repo regenerates its health workflow (`automation.py`) to drop the removed milestone step. `skills/workflow-docs/SKILL.md` carries the optional-milestone sentence by replacing a line, net zero lines.
- Removed subcommands of `milestone.py` (`new --all`, `new backlog`, `attach`, `features`): an old downstream workflow or agent that still calls one gets a one-line `REFUSED: <name> was removed, milestones are free form. Fix: drop the call.` on stderr and exit 1, never a traceback.
<!-- /accepted:dx -->

<!-- accepted:eng -->
- Generated CI workflow (`actions.py`): the page-derived label never enters script text; it is passed through an `env:` entry (`FEATURE_LABEL`) and used as `"$FEATURE_LABEL"`. `feature_label(page)` strips commas, newlines and control characters and cuts on code points (42 characters, so the whole label is at most 50). The generated workflow declares `permissions: issues: write`. Toy leg: a hostile page name (quote, backtick, `$(...)`, comma, newline, non-ASCII) yields YAML that parses and creates no file.
- Label failure never loses the report (replaces the earlier DX clause "issue not filed; rerun is safe"): in `file.py` and in the generated CI step, if the label create or the labelled issue create fails, the issue is filed again without the feature label (the `health:<group>` or regression label kept) and a `FAILED label <name>: <error>` warning prints. Toy leg asserts the issue still exists.
- `milestone.py` token rule: `backlog` is an ordinary title for `new`; the removed tokens `--all`, `attach` and `features` each print the one-line REFUSED and exit 1; one toy leg per token and one for `new backlog`. The old downstream step is `milestone.py new --all --live || echo ::warning::...` (verified in `workflows.py` lines 93-94), so the refusal does not fail the job; a toy leg runs that stale step text against the new CLI and expects exit 0 from the step.
- Binding Limit A guard: toys that reach `file.py`, `actions.py` or `automation.py` run with a PATH holding only `dev/toy/fakegh` and coreutils, with `GH_TOKEN=invalid` and `GH_HOST=localhost.invalid`; a grep guard proves no `feature:` label write (`label create` or `--add-label`) exists outside `file.py`, `actions.py` and the fake.
- Removed-name gate: `git grep -nE "issues\.(rows|unread|on_github|LIMIT|RULE|FIX_UNREAD)"` over skills and dev returns no hit (today `controls.py` line 286 and `health.py` line 207 import `rows`; both go, with the registration at `controls.py` line 194), and every touched module imports (`python3 -c "import <module>"` per touched script). Dead helpers `page_of`, `title_of` (feature refusal) and `held` in `milestone.py` go with their only callers.
- `feature_of` keeps returning the page for a finding but no longer defaults to `Backlog` (returns none); `feature_group(issue)` is the issue-side helper; two pages sharing one label make `feature_group` return `No feature`; toy cases at 42 and 43 characters. `fetch` paginates (`--paginate --slurp`), so removing `LIMIT` opens no truncation gap.
- Parser correction (replaces the `rounds.py` clause above): the `placed=` marker parsers are `file.py` (FOUND, line 37) and the marker in `actions.py`, not `rounds.py`; the toy proves old markers `placed=Backlog`, `placed=Alpha` and an empty `placed=` parse in both and that no `move` act is produced.
- Seen-red breaks are built at red time (replaces the stored-patch idea): a short Python or sed mutation of the one guarded line, or a restore of the old function with `git show v0.27.4:<file>`, whichever imports cleanly; a red counts only on the row's own sentinel and no traceback. Each row prints `PASS milestone-freeform:<id>` only after its last assertion.
- Day-one pin: a toy leg pins the before and after group counts (issues on Backlog, v1.0 or no milestone move to `No feature`; page-named milestones keep their feature), and `commands.md` says grouping is mixed until the owner's triage; `commands.md` also notes a milestone named like a page groups as that feature.
- Gates as commands: `wc -c` of every changed script is under 20480 (watch `actions.py`, 19768 now, and `file.py`, 17590), `wc -l skills/*/SKILL.md` all under 150, `python3 skills/workflow-regression/scripts/regression.py sync` lists no new gap after the hand edit of `.loop/regression.tsv`, and `criteria.py render` is re-run after the `origin/main` merge so `Tests.md` is never hand-merged.
- Test plan artifact on disk: a test plan file in the reviewer's local state folder (outside the repo; not committed).
<!-- /accepted:eng -->


### Phase 1: CEO review (SELECTIVE EXPANSION, unattended auto-decisions)

Mode: SELECTIVE EXPANSION (added capability; about 30 files across 5 skills, but every hunk is a removal; recommendation taken per the review-pipeline override). Taste calibration: good patterns, `milestone.py`'s refusal style and `health:<group>` label creation (`--force`); poor pattern to avoid, a soft note that replaces a removed check.

Landscape (Layer 1/2/3, in-distribution only; search not needed for a repo-internal rule removal): L1 GitHub milestones are a free-form planning tool; L2 nothing external requires a milestone per feature; L3 the restriction was a template invention, so deletion is the conventional answer.

REALITY rows (tier 1; receipts are repo-relative):
REALITY: premise-table pass 9 claims checked, unverified=0 (issues.py:49 rows(); report.py:80 SOFT; controls.py:118 f_docs_issues; health.py:205-212; audit.py:37-69; pageformat.py:132-134; goal.py:392; setup.py:271 and seed.py:106; workflows.py:93-94; criteria.py:328 owner words) skills/workflow-health/scripts/issues.py:49
REALITY: already-done pass `git log origin/main --since=2026-11-11` on skills/workflow-health and audit.py: no commits; main gained wiki-sync PRs touching docs/wiki only (obligation: merge origin/main first) commit 5ac593d
REALITY: surface-check pass criteria.py unreview --user, regression.py add/red, milestone.py new/move, lanes_cli.py check, docs.py check all exist; fixed one wrong path (design guide is skills/design-guide.md) skills/design-guide.md:21
REALITY: binding-decisions pass the decision search returned none for this branch; the coordinator's two limits are recorded as accepted obligations A and B .loop/goals/milestone-freeform.md:1
REALITY: numbers pass 12 new, 11 retired, 5 rewritten re-derived from the plan table and `.loop/regression.tsv` (all 17 ids present) [measured: regression.tsv] .loop/regression.tsv:1
REALITY: deferred-asks pass no linked issue; deferred items (live label backfill, label-collision check) listed for the PR body .loop/goals/milestone-freeform.md:10
REALITY: pr-count pass no ship-policy file; default one PR for the goal, no split (split rejected, see decision D3) .loop/goals/milestone-freeform.md:1

Premise table:
| premise | claim | receipt | verdict |
|---|---|---|---|
| P1 | docs-check fails every open issue with no milestone | issues.py:49, health.py:205 | verified |
| P2 | a goal's PR joins a feature milestone | goal.py:392 | verified |
| P3 | the audit auto-adds a `Milestone:` line and flags a missing Backlog | audit.py:47-69 | verified |
| P4 | Home refuses a non-link Milestone cell | pageformat.py:132-134 | verified |
| P5 | setup tells the owner to run `new --all --live` | setup.py:271 | verified |
| P6 | `--user` un-review needs owner words with no terminal | criteria.py:328-331 | verified |
| P7 | regression.py has no delete command | regression.py usage | verified |
| P8 | fake gh routes `issue create` only for health, milestone or repo | dev/toy/fakegh/gh:8 | verified |
| P9 | GitHub label names cap at 50 characters in total | external knowledge | unverified-by-repo; corrected to 42 plus prefix (conservative) |

0A Premise challenge: the real problem is a template-imposed bookkeeping rule the owner never reads; the plan solves it directly (deletes the rule and its creators), not a proxy. Do-nothing cost: every new repo gets a failing docs check and a Backlog milestone nobody wants. 0B Existing code leverage: `tag_of`, `label create --force`, `feature_of`, the digest marker, `docs.tsv` page map are all reused; nothing is rebuilt. 0C Dream state: CURRENT (milestone is the feature identity and a required field) ---> THIS PLAN (milestone is optional display, feature identity is a label with a milestone-title fallback) ---> 12-MONTH IDEAL (owner triage labels live issues, the fallback is retired, version milestones carry only planning).

Scope proposals (SELECTIVE EXPANSION): 7 proposed, 4 accepted (fake-gh assertion, name-based `milestone.py`, `feature_group` fallback with a row leg, spec-review corrections), 1 deferred (live label backfill), 2 skipped (label-collision check, release note). Native voice proposed splitting the label system into a second goal: declined (done line 2 needs issues still tagged; the label is the only replacement identity and is design-approved), logged as taste decision D3.

Native CEO voice (subagent) findings and dispositions:
- F1 high overbuild, split into two goals: declined (D3); instead the PR labels the label code as dead until triage.
- F2 high truncated-title label key: kept with 42-char cut (taste D4); a slug needs an ID pages do not have.
- F3 high live-state mismatch on day one: accepted as obligation (PR-body before/after note; feature labels code only until triage).
- F4 high history of retired rows: accepted (PR-body ledger); `regression.py retire` declined (new tooling).
- F5 medium `milestone.py` rewrite: kept minimal (done line 3).
- F6 medium alternatives (tracking issue, Project field): label wins because done line 2 says tagged, the repo already tags `health:<group>`, and a Project field needs a token scope the CI does not have; no plan change.
- F7 medium rebase risk: partly accepted (merge origin/main first; hunks stay removals).
- F8 medium silent seen-red: accepted (sentinel line per row).

CEO DUAL VOICES: outside voice UNAVAILABLE (usage limit reached; reset Nov 12th 2026 7:55 AM; outside_status unavailable). Native subagent only: tagged [subagent-only].

CEO DUAL VOICES — CONSENSUS TABLE:
  Dimension                              Claude  Outside Consensus
  1. Premises valid?                     partial N/A    N/A (P9 label cap corrected)
  2. Right problem to solve?             yes     N/A    N/A
  3. Scope calibration correct?          flagged N/A    N/A (split declined, taste D3)
  4. Alternatives sufficiently explored? flagged N/A    N/A (F6 answered in the record)
  5. Competitive/market risks covered?   n/a     N/A    N/A (internal tool)
  6. 6-month trajectory sound?           flagged N/A    N/A (retire ledger, day-one note accepted)

Section 1 Architecture: dependency graph before and after:
  BEFORE: docs.tsv page --> milestone (per page) --> issue / PR / Home cell / audit / setup / CI / goal.py pr
  AFTER:  docs.tsv page --> feature_label --> label on issue (code only) ; milestone --> display only (Home, digest suffix, triage, judge)
          feature_group(issue): label match -> else milestone title == page name -> else "No feature"
  Data flow paths: happy (label present, grouped by page); nil (no labels, no milestone: `No feature`); empty (labels list empty: same); error (gh label create or issue create fails: existing `FAILED <action>: <error>` line). Single point of failure: `feature_label` shared by write and read (one helper, intended). Rollback: revert the PR; no live state changes (Binding Limit A), minutes. Value test: no new process artifact is added; the PR-body ledger and Wording changes are the owner's requested review surface. No issues beyond the corrections recorded.
Section 2 Error and Rescue: see registry below; 4 paths mapped, 1 gap closed (label create failing in CI before `issue create`: the generated workflow creates the label first, and a failure is the existing FILE_FAILED-style line).
Section 3 Security: no new endpoint or input; label names derive from page file names (no spaces or slashes), cut to 42 characters; the owner-words path stays verbatim and logged; no new secrets. 0 High issues; one Low: a hostile page name could not inject because it is passed as one argv element.
Section 4 Data flow and edge cases: shadow paths for `feature_group`: nil issue labels, empty docs.tsv (every issue `No feature`), 42-character collision (accepted risk), case differences (compared case-insensitively), an issue on `Backlog` with a label (label wins). 5 edge cases mapped, 0 unhandled.
Section 5 Code quality: removal hunks only; no duplicated logic (`feature_label` is the one helper); `issues.py` gains two small helpers; no method branches more than 5 times. 0 issues.
Section 6 Test review: diagram produced in the Eng phase; here: every removed check has a red row, every changed surface has a green leg, fake gh proves labels. 0 gaps beyond corrections (sentinel, calls.log assertions).
Section 7 Performance: removing the docs-check gh call and the audit gh calls reduces network use; `feature_group` reads docs.tsv once per run (cache in the caller). 0 issues.
Section 8 Observability: the existing `FAILED <action>` lines and the digest stay; no new metrics needed for an owner-only rule removal; 0 gaps.
Section 9 Deployment: no migration; ships with the template release; rollback is a revert; deploy-time window: an old workflow file in a downstream repo still runs `milestone.py new --all --live` and would hit the new CLI (it refuses with a REFUSED line, exit 1, in a step that only echoes a warning, so the job continues). Risk flagged: 1, accepted; the release note names regenerating the workflow.
Section 10 Long-term: debt removed; reversibility 4/5; the fallback is a known retirement item after triage; path dependency low.
Section 11 Design: SKIPPED (no UI scope).

NOT in scope: deferred (to the PR body): live feature-label backfill on open GitHub issues (owner triage, Binding Limit A). Rejected: docs check for label collisions (design premise 3); a release note beyond the PR body; `regression.py retire`; splitting the label system into a second goal; Projects or tracking-issue grouping.
What already exists: `tag_of` and `health:<group>` labels (reused for `feature:`), `feature_of` (reworked), `docs.tsv` page map, `criteria.py unreview`, `regression.py red`, the fake gh and `reap.sh` harness, `entry.py` and `prd.py` milestone display (unchanged).
Dream state delta: the repo stops asking for milestones and tags by feature in code; the live labelling and fallback retirement are the remaining distance.

Error and Rescue Registry (capability rows):
| codepath | failure | rescued | action | user sees |
|---|---|---|---|---|
| file.py label create | gh error | Y | per-issue FAILED line, continue | `FAILED label feature:X: ...` |
| file.py issue create with feature label | label missing | Y | label made first | none |
| actions.py CI step | label create fails | Y | FILE_FAILED-style line | workflow log |
| issues.feature_group | empty docs.tsv | Y | `No feature` | grouped as No feature |
| milestone.py move | unknown title | Y | REFUSED line exit 1 | refusal with fix |
| milestone.py new --live no token | gh error | Y | REFUSED could not | refusal |
| criteria.py unreview | owner words missing | Y | stop and report | REFUSED, nothing written |
| old downstream workflow | calls removed `new --all` | Y | step only echoes a warning | warning in CI log |

Failure Modes Registry:
  CODEPATH | FAILURE MODE | RESCUED? | TEST? | USER SEES? | LOGGED?
  feature_group | page names collide at 42 chars | N (accepted) | N | wrong group (rare) | no   (accepted risk, not critical: not silent corruption)
  update backfill | label missing on old issue | Y | Y (fake gh) | FAILED line | yes
  break patch | red for wrong reason | Y | Y (sentinel) | red rejected | yes
  old workflow | removed CLI args | Y | N | CI warning | yes   (flagged, release note names regenerating)
Critical gaps: 0.

Diagrams: system architecture and data flow (above), state machine none (no new stateful object), error flow (registry), deployment sequence (merge origin/main, un-review, reword, remove, label code, rows, red), rollback (revert PR). Stale diagram audit: none of the touched files hold ASCII diagrams (0 found).

Implementation tasks (aggregated for the gate): T1 un-review and reword (P1); T2 removals per skill (P1); T3 label helpers and fake gh routing (P1); T4 rows with sentinels and targeted breaks (P1); T5 PR-body ledger, day-one note, Not-in-this-goal list (P2).

Taste decisions: D3 declined the split of the label system (done line 2 needs the tag); D4 kept truncated page names as label keys with a 42-character cut.

### Phase 2.5: DX review (DX POLISH, unattended auto-decisions)

Product type: CLI tool plus Claude Code skill docs (owner commands `milestone.py`, `criteria.py`, `regression.py`, SKILL.md and commands.md pages). Mode: DX POLISH (enhancement to an existing product). Developer-facing scope detected by terms (16 matches: command, SKILL.md, argument, action).

TARGET DEVELOPER PERSONA
Who:       the repo owner (a solo developer) and the AI coding agent that runs the template's skills unattended.
Context:   the owner wants to plan by version (v1.0) on GitHub; the agent runs health, regression and delivery steps that used to demand milestones.
Tolerance: one command, no reading of source; an agent retries blindly and reads errors literally.
Expects:   nothing is required of a feature or issue; a failed command says what was left unchanged and the next safe command.

Developer empathy narrative (first person): I open the repo wanting a v1.0 milestone. I run `milestone.py new v1.0 --live` and see `CREATED v1.0`; a second run prints `EXISTS v1.0`, so I trust it. I put an issue on it with `move 42 v1.0 --live`. I do not have to give every feature page a milestone, and the docs check stays quiet when a page has none. As the agent, when I call `move 42 v2` and v2 does not exist, I read `REFUSED: no milestone v2 (issue 42 unchanged). Fix: milestone.py new v2 --live`, run that, and retry. Predicted friction (not observed): an old workflow still calling `new --all --live` now gets a one-line REFUSED instead of milestones, which a stale CI step must tolerate.

Competitive DX benchmark (estimated, same boundary: "owner has a version milestone"):
| Tool | Start to result | Time and evidence | DX choice | Source |
|---|---|---|---|---|
| GitHub web UI | open Milestones, New milestone | about 1 min [estimated] | form, no code | in-distribution |
| `gh api` | one POST with a title | about 1 min [estimated] | raw JSON, no idempotence | in-distribution |
| this plan, `milestone.py new TITLE --live` | one command | under 1 min [estimated] | idempotent (`EXISTS`), dry run by default | plan |
Target: Champion (< 2 min), one command, [estimated; re-measure after release].

Magical moment: `milestone.py new v1.0 --live` prints `CREATED v1.0`, then Home shows the link the owner adds; delivery vehicle: the existing script (no new capability).

Developer journey map:
STAGE           | DEVELOPER DOES                         | FRICTION POINTS                 | STATUS
1. Discover     | reads commands.md Usage line           | entry renamed from `milestones` | fixed (command map updated, one sentence added)
2. Install      | none (script in the skill)             | none                            | ok
3. Hello World  | `milestone.py new v1.0 --live`         | no copy-paste example           | fixed (three examples in commands.md)
4. Real Usage   | `move N v1.0`, link on Home            | unknown title or issue          | fixed (refusal lines carry fix and state)
5. Debug        | reads a REFUSED or FAILED line         | outcome unknown after a gh error| fixed (gh issue view before retry)
6. Upgrade      | old workflow calls removed commands    | traceback or silent change      | fixed (one-line REFUSED, regenerate note)

First-time developer confusion report: T+0:00 the agent reads "milestones optional"; T+0:30 it runs `new v1.0` dry and sees `WOULD create milestone v1.0 (dry run; add --live)`; T+1:00 adds `--live`, sees `CREATED v1.0`; T+2:00 `move 42 v1.0` with no token gets the no-token REFUSED with `GH_TOKEN` fix; T+3:00 succeeded. Addressed: the missing example, the missing fix line, the dry-run hint.

Native DX voice (subagent) findings and dispositions (17 items; 0 critical, 6 CAP6-class high):
- 1 no-token line lacks fix and state: accepted. 2 unknown-title line lacks state and gh-failure path: accepted. 3 label write failure recovery: accepted. 4 unreview refusal report: accepted. 5 fake-gh-missing message: accepted. 6 usage errors: argparse default accepted, no custom code. 7 `placed=` empty vs failure: accepted as a toy assertion.
- 8 uppercase `WOULD CREATE`: declined (taste D6; the design strings are what the rows grep). 9 dry-run hint: accepted as a suffix. 10 print the truncated label: declined (taste D7; no new output, note stays in commands.md). 11 document the label as the override: accepted. 12 three copy-paste examples: accepted. 13 optional-milestone sentence in SKILL.md, net zero lines: accepted. 14 grep table: already in plan. 15 digest footer for day one: declined (taste D8; the PR body carries the day-one note, the `No feature` heading is self-describing, and a footer would be a soft note). 16 no finding. 17 documented owner label command: accepted.
- Added by the review: removed subcommands print a one-line REFUSED (upgrade path).

DX DUAL VOICES — CONSENSUS TABLE (outside reviewer unavailable: usage limit; outside_status unavailable; native subagent only [subagent-only]):
  Dimension                           Claude  Outside Consensus
  1. Getting started < 5 min?          yes     N/A    N/A
  2. API/CLI naming guessable?         mostly  N/A    N/A
  3. Error messages actionable?        gaps    N/A    N/A (fixed)
  4. Docs findable & complete?         gaps    N/A    N/A (fixed)
  5. Upgrade path safe?                gaps    N/A    N/A (fixed)
  6. Dev environment friction-free?    yes     N/A    N/A

ERROR PATH MATRIX (agent-ready-v1), after the accepted fixes:
Path                      | Class      | what | fix  | recovery | code | context | trace | redaction | channel | Cap
new --live, no token      | external   | pass | pass | pass     | N/A  | pass    | N/A   | pass      | pass    | none
move, unknown title       | usage      | pass | pass | pass     | N/A  | pass    | N/A   | pass      | pass    | none
move, gh failure          | external   | pass | pass | pass     | N/A  | pass    | N/A   | pass      | pass    | none
label write failure       | external   | pass | pass | pass     | N/A  | pass    | N/A   | pass      | pass    | none
removed subcommand        | usage      | pass | pass | N/A      | N/A  | N/A     | N/A   | pass      | pass    | none
unexpected crash          | unexpected | gap  | gap  | gap      | N/A  | gap     | gap   | pass      | pass    | accepted: owner scripts keep Python's own traceback on stderr, exit 1; no new handler (not a new codepath)
Stable code tokens (a doc-anchored code per error) are declined as taste D5: the owner commands are three; the message text is the contract.

DX Scorecard (before, after review):
| Dimension | Score | Prior | Trend |
| Getting Started | 7 -> 9 | none | first review |
| API/CLI/SDK | 6 -> 8 | none | first review |
| Error Messages | 5 -> 8 | none | first review (CAP6 fixed) |
| Documentation | 6 -> 8 | none | first review |
| Upgrade Path | 5 -> 8 | none | first review |
| Dev Environment | 8 -> 8 | none | first review |
| Community | n/a, internal template, scored 7 | none | first review |
| DX Measurement | 5 -> 7 | none | first review (re-measure after release) |
TTHW: 1 min estimated (target Champion under 2 min); Competitive rank: Champion; Magical moment: designed via the existing script; Product type: CLI tool; Mode: DX POLISH; Overall DX 6 -> 8 [estimated]. Principle coverage: Zero friction covered; Learn by doing covered (examples); Fight uncertainty covered (state and fix lines); Opinionated plus escape hatches covered (free-form milestones, `none`, label override); Code in context covered; Magical moments covered; Agents are users covered.

DX Implementation Checklist:
[ ] Time to hello world < 2 min (one command)
[ ] Installation is one command (none needed)
[ ] First run produces meaningful output (`CREATED v1.0` or the dry-run line)
[ ] Magical moment delivered via the existing script
[ ] Every error message meets the agent-ready contract (matrix above)
[ ] CLI naming guessable (`new`, `move`)
[ ] Every parameter has a default (dry run by default)
[ ] Docs have copy-paste examples (three in commands.md)
[ ] Upgrade path documented (regenerate workflow note; removed commands refuse in one line)
[ ] Works in CI without special configuration (non-interactive)
[ ] Changelog exists (release flow writes it)

NOT in scope (DX): stable doc-anchored error codes; uppercase verb grammar; printing the truncated label; a digest footer; telemetry for TTHW; a hosted playground.
What already exists: `criteria.py` refusal text with Fix (criteria.py:328-331), `milestone.py` dry-run default, `FAILED <action>: <error>` lines, the commands.md pages, argparse usage errors.

Implementation tasks: T6 refusal messages and removed-subcommand lines in `milestone.py` (P1); T7 commands.md examples and sentences, SKILL.md net-zero sentence (P1); T8 toy assertions for failure surfacing and the fake-gh message (P2).
Taste decisions: D5 no stable error codes; D6 keep design's lowercase `WOULD create`; D7 no truncated-label print; D8 no digest footer.

<!-- AUTONOMOUS DECISION LOG -->
### Phase 3: Eng review (FULL_REVIEW, unattended auto-decisions)

Scope Challenge result: scope accepted as-is (never reduce, P2). Complexity: about 30 planned changed files across 5 skills plus 11 toy tests and the fake gh; 0 new classes or services (two small helpers in `issues.py`); every hunk is a removal except the label helpers. The 8-file complexity gate trips by count, so the structure answer is auto-decided (`plan-eng-review-structure`): Original arrangement (one PR, per-skill hunks) kept, because a smaller arrangement would split the label code from the removals that feed it; both native passes raised a two-PR split, recorded as taste D3 for the gate.

REALITY rows (eng):
REALITY: premise-table pass 8 claims re-read in code, unverified=0 (issues.py:49-67 rows(); issues.py:196-224 feature_of defaults to BACKLOG; controls.py:286 second importer of issues.rows; health.py:207; file.py:35-37 marker regex parses an empty placed=; automation.py:107-112 backlog(); judge.py:252 milestone == name; fakegh/gh:8 routing) skills/workflow-health/scripts/issues.py:49
REALITY: already-done pass origin/main has no commit on the touched scripts since 2026-11-11 (wiki-sync PRs only) commit 5ac593d
REALITY: surface-check pass criteria.py unreview --user, regression.py add/red, lanes_cli.py check, dev/toy/test-tree.sh, docs.py check and milestone.py new/move exist; the removed names are verified by grep skills/workflow-regression/scripts/lanes_cli.py:1
REALITY: binding-decisions pass the decision search found none; coordinator limits A and B recorded as obligations .loop/goals/milestone-freeform.md:1
REALITY: numbers pass 12 new, 11 retired, 5 rewritten re-counted against the plan table [measured: .loop/regression.tsv:1]; issues.py is 13376 bytes [measured: wc -c skills/workflow-health/scripts/issues.py:1]; file.py is 17590 bytes [measured: wc -c skills/workflow-health/scripts/file.py:1]; actions.py is 19768 of 20480 bytes [measured: wc -c skills/workflow-regression/scripts/actions.py:1] .loop/regression.tsv:1
REALITY: deferred-asks pass no linked issue; deferred items go to the PR body .loop/goals/milestone-freeform.md:10
REALITY: pr-count pass default one PR; split proposed by both native passes and kept as one (D3), cost of a second PR is a second gate and a rebase over the first .loop/goals/milestone-freeform.md:1

Premise table: P1 `rows()` is the only docs milestone rule (issues.py:49, verified); P2 `feature_of` is the feature identity (issues.py:215-220 reads an issue's milestone, verified, must move to `feature_group`); P3 `fetch` paginates (issues.py:99 `--paginate --slurp`), so the `LIMIT` removal opens no truncation gap (verified); P4 old CI step tolerates failure (workflows.py:93-94 `|| echo ::warning::`, verified); P5 the `placed=` parser is `file.py` FOUND (file.py:37) and `actions.py`'s own marker, not `rounds.py` (corrects an earlier obligation, verified); P6 `controls.py` has two references to the removed rule (line 194 registration, line 286 lambda calling `issues.rows`, verified); P7 `judge.py:252` is the only judge hunk (verified); P8 the fake gh routes `issue create` only for health, milestone or repo flags (fakegh/gh:8, verified).

Native ENG voice (subagent) findings and dispositions (14 findings: 2 high, 7 medium, 5 low); outside voice unavailable (usage limit, outside_status unavailable) [subagent-only]:
- H1 page name spliced into the generated workflow (shell/YAML injection, comma splits `--label`): accepted; pass the label through an `env:` entry and quote it, strip commas, newlines and control characters in `feature_label`, cut on code points, add a hostile-name toy leg.
- H2 a failed label write loses the CI defect report: accepted; on any label failure the issue is still filed without the feature label (health or regression label kept) and a `FAILED label` warning prints; the generated workflow carries `permissions: issues: write` and the toy asserts it. This replaces the DX clause "issue not filed; rerun is safe".
- M3 `new backlog` vs removed tokens: accepted; `backlog` is an ordinary title; the tokens `--all`, `attach` and `features` get a one-line REFUSED; one toy leg per token and one for `new backlog`.
- M4 stale downstream workflows: verified tolerant (warning step), stated in commands.md; toy leg runs the stale step text against the new CLI.
- M5 Binding Limit A weak: accepted; toys run with a PATH holding only the fake gh and coreutils, `GH_TOKEN=invalid`, `GH_HOST=localhost.invalid`; a grep guard proves no `feature:` label write lives outside `file.py` and `actions.py`.
- M6 seen-red breaks fragile: accepted; breaks are built at red time by a short mutation of the one guarded line or a restore of the old function with `git show v0.27.4:<file>`; the sentinel and no-traceback rule is the arbiter.
- M7 dangling imports: accepted; gate `git grep -nE "issues\.(rows|unread|on_github|LIMIT|RULE|FIX_UNREAD)"` returns zero (today `controls.py:286`, `health.py:207` import `rows`) and every touched module imports.
- M8 truncation guard: verified not needed (`fetch` paginates); recorded.
- M9 mixed grouping until triage: accepted; toy pins before/after group counts; commands.md says grouping is mixed until triage.
- L10 label cap: accepted (42 plus prefix; toy cases at 42 and 43; two pages sharing a label group as `No feature`). L11 fallback surprise: accepted as a commands.md sentence. L12 sentinel printed after the last assertion: accepted. L13 explicit `wc -c` and `wc -l` gate commands: accepted. L14 `regression.py` list pass after the hand edit and `criteria.py render` after the origin/main merge: accepted.
- Hidden complexity (split into two PRs): declined as one PR (taste D3); both native passes raise it, no outside voice, so it is a gate item, not a User Challenge (done line 2 requires the tag).

ENG DUAL VOICES — CONSENSUS TABLE (outside reviewer unavailable; N/A, never CONFIRMED):
  Dimension                           Claude  Outside Consensus
  1. Architecture sound?               yes     N/A    N/A
  2. Test coverage sufficient?         gaps    N/A    N/A (fixed by obligations)
  3. Perf risks + budget/bench named?  none     N/A    N/A (removes gh calls)
  4. Security threats covered?         H1      N/A    N/A (fixed)
  5. Error paths handled?              H2      N/A    N/A (fixed)
  6. Deployment risk manageable?       yes     N/A    N/A (stale step tolerated)

Section 1 Architecture (ASCII, new and removed edges):
  docs.tsv ---> issues.features() ---> feature_label(page) --+--> file.py (write: label create --force, --label)   [fake gh only this goal]
                                                              +--> actions.py generated CI step (env FEATURE_LABEL)   [never run live this goal]
  issue labels/milestone ---> feature_group(issue) ---> triage(listing,close) / digest / covering / judge:252
  REMOVED: issues.rows ---> health.docs_check ---> report.SOFT ; controls f_docs_issues(194,286) ; audit.milestone_* ;
           pageformat.home milestone cell ; goal.pr attach ; setup NEXT ; workflows `new --all` step ; file.py placement/move/Backlog
  KEPT: milestone display (Home cell, START.md, digest suffix, judge 286, fetch fields), milestone.py new/move (owner commands)
Coupling: `feature_label` is the single writer/reader helper; one owner per piece of state. Design-twice: second shape (store the page in the issue body marker instead of a label) rejected, a body marker cannot be filtered by `gh issue list --label`, and the repo already tags by label. Red flags screened: none (no shallow module, no hand-synced list; the `feature` map has one owner `issues.features`). Security: H1 fixed; owner words path logged. Single point of failure: none new. Distribution: ships with the template release, no new artifact. Issues found: 3 (H1, H2, M7 importers).
Section 2 Code quality: DRY, `feature_label` replaces three ad-hoc page-to-name conversions; `file.py` (17590 of 20480) loses more than it gains, `issues.py` (13376) gains about 25 lines; stale diagrams: none. Naming: `feature_group` vs old `feature_of`, keep `feature_of` for page-from-finding (still used by `file.py:124`) and add `feature_group` for issues; delete the `BACKLOG` default (return None), callers `file.py:124,127,237,251` rewritten. Issues found: 2 (feature_of default, dead `page_of`/`title_of`/`held` in milestone.py to delete with their only callers).
Section 3 Test review: diagram below; the Test Plan artifact is on disk (path in the gate summary).

CODE PATHS                                              USER FLOWS
[+] issues.py                                           [+] health check, no-milestone issue
  ├── feature_label(page)                                  ├── [GAP→row] no docs row, same verdict (no-milestone-issue-ok)
  │   ├── [GAP→row] 42/43-char names, comma/control chars  └── [GAP→row] hostile page name in generated CI
  ├── feature_group(issue)                              [+] docs audit / docs check
  │   ├── [GAP→row] label match, page-named milestone,     ├── [GAP→row] no Milestone line (no-milestone-page-ok)
  │   │             v1.0/Backlog/none, label collision     └── [GAP→row] Home empty / v1.0 / link cells
  [+] file.py                                             [+] file / digest / CI
  │   ├── [GAP→row] label create + issue create + update   ├── [GAP→row] label failure still files the issue
  │   ├── [GAP→row] label failure fallback                 ├── [GAP→row] repeat run backfills; fix closes; return reopens
  │   └── [GAP→row] old placed=Backlog/Alpha/empty markers └── [GAP→row] digest groups by feature, milestone suffix
  [+] actions.py (generated workflow)                     [+] owner commands
  │   └── [GAP→row] env FEATURE_LABEL, permissions block   ├── [GAP→row] new v1.0 twice, move N v1.0 / none
  [+] milestone.py                                         └── [GAP→row] unknown title, no token, removed tokens, new backlog
  │   └── [GAP→row] each REFUSED path and exit code       [+] goal.py pr / setup / workflow text
  [+] goal.py, seed.py, setup.py, workflows.py             └── [GAP→row] pr no --milestone; setup no note; workflow no step
COVERAGE: 0/24 planned paths tested today (all are new rows)  |  after plan: 24/24 via 12 rows plus legs  |  QUALITY target ★★★ (each leg has an error path)
LLM/eval scope: none (no prompt or skill-template change; SKILL.md edits are prose).
Tests made obsolete: the 11 retired rows. Each proposed row carries a value card in the Test Plan artifact.
Issues found: 6 test gaps, all closed by accepted obligations (hostile name, label failure, removed tokens, stale step, PATH sandbox, import smoke).
Section 4 Performance: removing the docs-check `gh issue list` (one call per check) and the audit's milestone calls (gh per page) reduces network use; `feature_group` reads `docs.tsv` once per run (cache in the caller dict as `feature_of` does); no loops over issues with gh calls. 0 issues.

NOT in scope: live label backfill; two-PR split; label-collision docs check; stable error codes; digest footer; `regression.py retire`.
What already exists: `issues.features`, `tag_of`, `label create --force` pattern (issues.py:294 for `health:closed`), `fetch` pagination, FOUND marker regexes, fake gh and `reap.sh`, `criteria.py unreview`, `regression.py add/red`.
Diagrams: architecture (above), test coverage (above); state machine none; failure modes below.
Failure modes registry:
  CODEPATH | FAILURE MODE | RESCUED? | TEST? | USER SEES? | LOGGED?
  generated CI workflow | hostile page name | Y (env quoting, strip) | Y | none | n/a
  generated CI workflow | label create fails | Y (file without label) | Y | FAILED label warning | yes
  file.py | label create fails | Y (same fallback) | Y | FAILED label line | yes
  milestone.py | removed subcommand | Y | Y | one-line REFUSED | stderr
  issues importers | removed name imported | Y (gate) | Y | none | n/a
  feature_group | label collision | Y (No feature) | Y | grouped as No feature | no
Critical gaps: 0 after obligations (before: H2 had RESCUED=N, a silent loss of the CI defect report).
Worktree parallelization: Sequential implementation, no parallelization opportunity worth the merge cost: the five skill modules are independent, but the toy tests, `fakegh/gh` and `.loop/regression.tsv` are shared and the wording commit must land first; lanes would conflict on those three files.

Implementation tasks (eng): T9 label helper hardening and env quoting (P1); T10 label-failure fallback in file.py and the generated step (P1); T11 removed-token refusals and importer gate (P1); T12 PATH sandbox and grep guard in toys (P1); T13 break scripts and sentinels (P1); T14 size and line gates as explicit commands (P2).
Taste decisions: D3 stays (one PR); D9 breaks built at red time by mutation, fallback to restoring the old function.
Completion summary: Scope Challenge scope accepted as-is; Reality rows 7/7, 0 unverified; Architecture 3 issues; Code Quality 2; Test gaps 6 closed; Performance 0; failure modes critical gaps 0; unresolved decisions 1 (D3 split, a gate item); outside voice unavailable (usage limit), native subagent completed; lanes 0 parallel / 1 sequential.

Phase 2 (Design review): skipped, no UI scope detected (scope check uiRequired=false); not a completed review.

## Decision Audit Trail

| # | Phase | Decision | Classification | Principle | Rationale | Rejected |
|---|-------|----------|----------------|-----------|-----------|----------|
| 1 | CEO | Mode SELECTIVE EXPANSION | Mechanical | P6 | review-pipeline override | other modes |
| 2 | CEO | Accept fake-gh-log assertion (Binding Limit A check) | Mechanical | P2 | in blast radius, S effort | skip |
| 3 | CEO | Decline splitting the label system to a second goal (D3) | Taste | P1 | done line 2 needs issues still tagged; label is the only replacement identity | split into two goals |
| 4 | CEO | Keep truncated page name as label key, cut to 42 (D4) | Taste | P3 | page names have no ID; slug needs new infrastructure | slug or numeric key |
| 5 | CEO | Keep `feature_group` milestone-title fallback with a row leg | Mechanical | P1 | old issues stay grouped on ship day | drop fallback |
| 6 | CEO | Skip label-collision docs check | Mechanical | P5 | design premise 3: no new check | add check |
| 7 | CEO | Defer live feature-label backfill to owner triage | Mechanical | P3 | Binding Limit A | backfill in goal |
| 8 | CEO | Accept PR-body ledger of retired rows, day-one note, sentinel per row, merge origin/main first | Mechanical | P1 | closes silent-history, silent-red and rebase risks | regression.py retire command |
| 9 | CEO | Outside voice unavailable (usage limit), native subagent only | Mechanical | P6 | missing coverage never blocks | wait for reset |
| 10 | DX | Accept refusal-message fixes, copy-paste examples, removed-subcommand REFUSED, dry-run suffix | Mechanical | P1 | closes CAP6-class gaps for the agent reader | leave messages bare |
| 11 | DX | Decline stable error codes (D5), uppercase verb grammar (D6), truncated-label print (D7), digest footer (D8) | Taste | P3/P5 | owner commands are three; design strings are what rows grep; a footer is a soft note | add them |
| 12 | DX | Outside voice unavailable (usage limit), native subagent only | Mechanical | P6 | missing coverage never blocks | wait |
| 13 | Eng | Scope accepted as-is; structure arrangement kept (one PR, per-skill hunks) | Taste | P2/P1 | never reduce; a split would separate the label code from its removals | split into a deletion-only PR and a label PR (D3, both native passes suggested it, gate item) |
| 14 | Eng | Accept H1 env quoting and H2 label-failure fallback | Mechanical | P1 | injection surface and a silent loss of the CI defect report | interpolate the name; fail the step |
| 15 | Eng | Accept PATH sandbox, importer gate, removed-token rules, parser correction, size gates | Mechanical | P1/P5 | closes five test gaps | trust the process promise |
| 16 | Eng | Breaks built at red time by mutation (D9) | Taste | P5 | stored patches rot against parallel edits | stored `git apply -R` patch |
| 17 | Eng | Outside voice unavailable (usage limit), native subagent only | Mechanical | P6 | missing coverage never blocks | wait |
