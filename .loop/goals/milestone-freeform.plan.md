# Plan: milestone-freeform

Goal: `.loop/goals/milestone-freeform.md` (done lines and Verify by hand are frozen and belong to delivery; not restated or reopened here). Design: `.loop/goals/milestone-freeform.design.md` (APPROVED).

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

