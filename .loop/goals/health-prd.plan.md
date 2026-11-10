# Plan: health-prd

Source: `.loop/goals/health-prd.design.md` (spec review converged after 2 rounds; its Rule contracts govern). Done
lines: `.loop/goals/health-prd.md`. The owner approved the PRD itself on 2026-11-10 (approved page in the operation's
private folder; docs-format writes it to docs/wiki/Health.md).

## URGENT, outside this plan

None.

## Implementation plan

1. `skills/workflow-health/scripts/groups.py` (new): the twelve groups in order, each `(name, angle, rules)`:
   - Requirements: rows, proof, done, not-enforced-7d
   - Traceability: defect-tests, issue-milestone, row-requirement
   - Consistency: ids-unique, refs, usage-readme
   - Docs: docs-check
   - Freshness: nightly, unreleased, finding-age
   - Tests: seen-red, skipped, network
   - Performance: cost, test-time, check-time
   - Security and privacy: private, scan-hook, workflow-permissions
   - Size: scripts, skill-lines, requirements-per-page
   - Hygiene: findings, waiting, branches, worktrees, local-branches, idle-sessions
   - Adoption: config, checks-run-tests, template-version, scheduled
   - Controls: controls

   Mine stays outside the twelve. `assert len(GROUPS) == 12`. A slug per group (requirements, traceability,
   consistency, docs, freshness, tests, performance, security, size, hygiene, adoption, controls) is used in `--group`
   and in the `health:<slug>` tags. The old names stay as aliases for one release: criteria → requirements, traceability and tests,
   cost → performance.
2. health.py: FAMILY, ORDER, NAMES, RULES and gather() come from groups.py. Existing rule functions keep their bodies
   and move groups:
   - size_rows → Size `scripts`;
   - criteria_rows is split. `rows`, `done` and `proof` (draft only) go to Requirements; never-failed goes to Tests
     `seen-red`.
   - defect_rows → Traceability;
   - docs_rows → Docs;
   - hygiene_rows plus lean.py → Hygiene;
   - cost.py and lean test-time → Performance.

   Size budget: health.py is 18.4 KB, so the group tables move out (groups.py) and the new rules go in new modules.
   report.py: each group heading prints its angle, `== Requirements (my angle: is every promise I approved proven?) ==`,
   and report.RULES/RULE_OF come from groups.py.
3. New rule modules, each rule `fn(root, ctx) -> rows`, where ctx caches the gh issue list, the pages and the rows for
   one run:
   - `rules_trace.py`: Requirements `rows`, Unreviewed WARN "not enforced" (fixes 118, reading the Reviewed stamp with
     criteria.LINE semantics); `not-enforced-7d`; Traceability `issue-milestone` and `row-requirement`; Consistency
     `ids-unique`, `refs` and `usage-readme`.
   - `rules_fresh.py`: Freshness `nightly`, `unreleased` and `finding-age`; Tests `seen-red`, `skipped` and `network`;
     Adoption `config`, `checks-run-tests`, `template-version` and `scheduled`.
   - `rules_guard.py`: Security `private` (file:line plus pattern name only), `scan-hook` and `workflow-permissions`;
     Size `skill-lines` and `requirements-per-page`; Performance `check-time` (in-process); Hygiene `idle-sessions`.
   - `ghcache.py`: one paginated `gh api --paginate` issues fetch per run (C19), with `gh issue view N` for numbers not fetched.
     gh missing → INFO "gh not available here".
4. Controls: a fixture per new rule (23 new, listed in C18, in a new module beside controls.py), each building the smallest broken repo that makes the rule
   fire. A rule with no control makes health.py refuse (exit 2), as today. The controls rule and Mine are exempt.
   Controls run only in the full check (`--skip controls` stays fast, HLT-7).
5. cost.py (fixes 124): goals with no tokens recorded are left out of the token check. UNREAD only when no finished
   goal's record can be read.
6. `feature.py` (new): `feature_of(row)` maps a path through .loop/docs.tsv (longest prefix), a requirement id through
   the page that defines it, an issue number through its milestone, and a review finding through its named feature
   (docs.tsv pages only). Backlog when nothing fits.
7. file.py:
   - The milestone comes from feature_of.
   - The marker gains `evidence=<sha8>` (stable citations only; review citations normalized).
   - LINK: a covering open non-health issue on that milestone (exact token match of path, id or row id) gets one
     comment carrying `<!-- loop-health-link KEY evidence=H -->`, skipped when already present.
   - A closed issue labelled `health:closed` with the same hash stays closed.
   - `--review FILE` reads a saved `review --json`.
   - The tags are `health:<slug>` and `health:review-<kind>`.
8. `triage.py` (new), exposed as `health.py triage`:
   - It lists open health issues per milestone by kind, age and count.
   - `--close --feature F --kind K [--older D] --why W` always prints the matched list; with `--yes` it closes exactly
     that list, adding the words as a comment and the `health:closed` label. Zero matches prints `NOTHING TO CLOSE`.
9. `review.py` (new), exposed as `health.py review [--feature F] [--json]`; the judge alias stays.
   - Deterministic layer per feature, reusing check's rows: gaps (no non-functional requirement, an open issue naming
     no requirement id) and drift (a Usage verb not in the skill's command map).
   - Judge layer: judge_command with tagged `FINDING|feature|kind|angle|evidence|fix` lines. Evidence is verified (a
     page id, a file:line, a row id, an issue number), and unverified findings are dropped and counted. With no judge,
     it prints `JUDGE UNAVAILABLE: <reason>` with the first stderr line (fixes 158).
   - It ends with ranked next steps per feature and writes nothing.
10. Issue 158 and setup: judge.py's error includes the command's first stderr line, and setup prints whether
    judge_command's executable is found.
11. Issue 159: the SKILL.md description and references/commands.md charts are rewritten for check (twelve groups),
    preview, file, review and triage; the run chart is removed.
12. Tests:
    - dev/toy/test-health-prd.sh (new) covers: the groups and angles; every new rule firing and passing; LINK and the
      evidence hash; triage dry run and --yes; review with fake judges (good, unverifiable, failing); determinism
      (check twice, identical); check changing no tracked file; and the check time.
    - Existing tests that name the old groups are updated (test-health-report, test-health, test-health-hygiene,
      test-health-judge, test-milestones, test-automation, test-summary). Their group names change, and the behavior
      they assert stays.
13. Rows: one or more per HLT-1..HLT-6 now and HLT-7..HLT-9 after docs-format is on main (the operation's decision b),
    plus defect rows for 118, 124, 158 and 159, each seen red. The Health Tests table is re-rendered.
14. Step 14 delivers done line 7, the first inspection. After docs-format merges: `health.py review` and `check` on this repo, then the
    preview goes to the owner through the operation. Filing happens only on the owner's word.

### Known limits, stated

- Model findings are not deterministic; only the deterministic layer is held to HLT-1.
- gh and local-state rules are INFO where their data is absent, such as a fresh clone or no gh.
- Old group names stay accepted as aliases for one release.


<!-- autoplan-accepted:ceo -->
- C1: file.py reads both marker forms (`<!-- loop-health KEY -->` and `<!-- loop-health KEY evidence=H -->`). A key stays `group:subject:label`, and every row keeps its current subject and raw rule label (limit, rows, proof, stale, unmapped and the other docs kinds, open, waiting, run, merged, branch, time, tokens, defect-tests, test-time, worktrees, local-branches); only the group part moves. Migration maps the old family by its raw label: size:* stays size; criteria:*:rows (including criteria:done-lines:rows) to requirements; criteria:*:defect-tests to traceability; criteria:ROW:proof to requirements when ROW is a draft in today's .loop/regression.tsv, else to tests (the row's state, never the issue prose); docs:* stays docs; hygiene:* stays hygiene except hygiene:lane:test-time to performance; cost:* (including cost:judge:saves-*) to performance. A closed issue labelled health:closed with an old-form marker (no evidence hash) matches on its migrated key alone and stays closed. An issue filed before the rename is updated in place, never refiled or orphaned. Tests: one fakegh issue per old family and label above; each gets an update, none an open plus a stranded old issue.
- C2: automation.py GROUPS becomes the groups whose every rule reads only tracked files or gh: requirements, traceability, consistency, docs, size and adoption. Inputs: requirements rows, proof and done read regression.py sync (tracked .loop/regression.tsv and pages); traceability defect-tests reads defects.py (tracked files and gh), issue-milestone gh, row-requirement tracked files; consistency, docs (docs.py check), size and adoption (config.json, regression.tsv, VERSION, listing.json, .github/workflows) read tracked files only. `not-enforced-7d` reads the local run records (health.py:164-166), so on a fresh clone it is INFO "not applicable here", never PASS or FAIL. .github/workflows/health.yml is regenerated with `automation.py workflow`; it is outside the goal's Touches list, so this half waits for the owner's word at the final gate. Test: test-automation.sh asserts the new group list in the generated workflow.
- C3: file.py's held() reads health issues through ghcache's paginated fetch (no 500 cap). Test: fakegh with more than one page of issues; an issue on page two is SAME, not reopened.
- C4: feature.py imports milestone.features() and the goal_feature path match; no second docs.tsv parser.
- C5: before opening an issue on a feature milestone, file ensures that milestone exists (milestone.ensure); preview names a milestone it would create. Test: fakegh with no feature milestone; file creates it once, then the issue.
- C6: nightly, scan-hook, idle-sessions and check-time join file.py REPORT_ONLY, and REPORT_ONLY's "control" entry follows the controls rule's new label: shown in check, never filed or closed.
- C7: the cost-unread-tokens row (.loop/regression.tsv:113) is red now, because b490a73 changed its test output; its command is rewritten to grep the new INFO line and its seen-failing date records the red state before the rewrite. No tokens recorded is INFO; UNREAD stays only for a finished goal whose record cannot be read.
- C10: controls.CONTROLS is re-keyed to the new rule names and labels (size to scripts, criteria-rows to rows, criteria-done to done, and so on), and the new fixtures live in a new module beside controls.py so controls.py stays under 18 KB.
- C11: the `criteria` alias expands to requirements, traceability and tests for one release, so `--group criteria` still checks every rule it checked before; `cost` maps to performance.
- C12: each new rule's trigger and state are the design's Recommended Approach bullets as superseded by its Rule contracts section (.loop/goals/health-prd.design.md); a rule the design does not define is not built.
- C13: requirement map. HLT-1 and HLT-7: steps 3 (check-time), 12 (determinism, read-only, time). HLT-2: steps 1-4. HLT-3: step 2 (report). HLT-4: steps 6-7. HLT-5 and HLT-9: step 9. HLT-6: step 4 and the existing lean rules. HLT-8: step 8. Done lines: 1 steps 1-4; 2 steps 6-7 with C1, C3, C5; 3 step 9; 4 steps 7-8; 5 step 4 and the existing lean rules (test-time, worktrees, local-branches); 6 steps 3 and 12; 7 step 14; 8 step 13; 9 steps 5, 10, 11 and 13.
- C14: if this goal is otherwise done before docs-format merges, the HLT-7..HLT-9 rows and step 14 stay pending and the goal waits; it does not add the HLT-7..HLT-9 lines to Health.md itself.
- Already done and committed on this branch (b490a73): 124's cost.py change and 158's judge.py stderr change with their test lines. Plan steps 5 and 10 build on them; 158's setup `command -v` check is still to do.
- C15: file.py GROUPS, DEFAULT and TAG (file.py:24-26) are built from groups.py with the C11 aliases, so preview and file accept the new slugs and the old names; the default preview names every filable group except mine and controls. Test: `preview --group requirements` and `preview --group criteria` both run.
- C16: triage `--close` refuses without --why (exit 2, one REFUSED line), per the design's Rule contracts. Test: --close with no --why writes nothing and exits 2.
- C17: one rule signature: gather() calls every rule as fn(root, ctx); groups.py wraps each existing fn(root) rule in a one-line adapter, so their bodies stay unchanged. The regression.py sync output is cached in ctx and read by both Requirements and Tests.
- C18: the new rules, each with one new fixture (23): requirements not-enforced-7d; traceability issue-milestone, row-requirement; consistency ids-unique, refs, usage-readme; freshness nightly, unreleased, finding-age; tests seen-red, skipped, network; performance check-time; security private, scan-hook, workflow-permissions; size skill-lines, requirements-per-page; hygiene idle-sessions; adoption config, checks-run-tests, template-version, scheduled. requirements rows gains the Unreviewed WARN (118) and its existing fixture gains that case.
- C19: ghcache fetches with `gh api --paginate "repos/{owner}/{repo}/issues?state=all&per_page=100"` (gh issue list has no page option), drops entries carrying a pull_request field, and fakegh learns that route. Test: two pages in fakegh; an issue on page two is seen.
- C20: check-time reads its budget from ctx (default 60 seconds), so its fixture sets the budget to 0 and the rule fires at once.
- C21: preview lists each migration as `MIGRATE #N OLD-KEY -> NEW-KEY` before any write, so the owner sees the mapping on the live tracker first.
- C22: a filed issue closes only when its own rule ran and returned PASS this run; a rule that returned INFO or UNREAD closes none of its issues, even when other rules in its group passed (file.py:96-99 decides per group today). Test: a group with one PASS rule and one INFO rule; the INFO rule's open issue stays open.
- C23: triage `--close --yes` acts on at most 20 issues unless `--max N` names a higher number; over the cap it prints the list and REFUSED. Test: 21 matches with no --max closes none.
- C24: `workflow-permissions` WARNs on a workflow with no `permissions:` key and on `permissions: write-all`.
- C25: an issue filed from a model finding says so in its body (`found by the judge, evidence verified`), so the owner can weigh it.
- C26: tests assert that every group heading carries an angle, not the exact angle wording; and `health.py check --group size` passes on this repo after the change.
- C27: file checks each gh act's return code; a failing act prints `FAILED <act>: <first stderr line>`, the run continues with the rest and exits non-zero (file.py apply ignores it today). Test: fakegh failing one create; the line and exit code appear.
- C28: `file --review FILE` re-verifies every citation in the saved review against the repo at filing time and drops (and counts) findings whose evidence no longer exists.
<!-- /autoplan-accepted:ceo -->

<!-- autoplan-accepted:dx -->
- C29: file creates a missing feature milestone through the GitHub call alone (the gh api part of milestone.ensure, split out), never link_page, so file changes nothing tracked; a creation failure prints `FAILED[milestone] <name>: <stderr line>`, skips that milestone's issues and exits non-zero. The `health:closed` label is created the same way as the group labels. Test: no feature milestone and no Milestone line on the page; file creates the milestone and leaves the page byte-identical.
- C30: preview and file gather only the groups they will file (never Mine's private commands unless `--group mine` is named). Test: a Mine command that would write a file does not run during `preview --group requirements`.
- C31: ghcache fails closed for writers: any gh error or partial page makes preview, file and triage exit 2 with `REFUSED[gh-read] could not read issues (page N): <stderr line>. Fix: gh auth status, then rerun`; check's rules keep a row with a fix line (`install gh and run gh auth login`). JUDGE UNAVAILABLE names its fix: `set judge_command in .loop/config.json; health.py setup shows whether it resolves`. Test: fakegh failing page 2; file writes nothing and exits 2.
- C32: triage and review validate --feature against docs.tsv pages and --kind against known kinds, refusing an unknown value with exit 2 and the valid list; `--older` is whole days; the C23 over-cap refusal reads `REFUSED[cap] 21 matches over 20. Fix: add --max 21` with exit 2.
- C33: rules read the time from ctx (`now`), so tests pin the clock; check-time is evaluated last and measures the whole non-control run against ctx's budget (default 60 seconds, `health_check_seconds` in .loop/config.json overrides); rows print thresholds and states, never measured values.
- C34: every refusal exits 2 and starts `REFUSED[code]`, every failed write starts `FAILED[code]`; exit 0 green, 1 not green, 2 refused; references/commands.md lists each code with its fix. Existing `sys.exit("REFUSED...")` paths (exit 1 today) move to exit 2, and their tests follow.
- C35: old names (criteria, cost, --family, suggest) print one stderr NOTE naming the new name and the release that removes them; `run` is removed (159); `--json` keeps the `family` key with the new group values; the CHANGELOG lists the renamed groups, rules and exit codes.
- C36: `review --json` prints one JSON object on stdout only: schema 1, repo, HEAD sha, judge status, findings and dropped counts. `file --review` refuses a missing or other schema with the command that regenerates it, and warns when the saved HEAD differs from the current one (then C28 re-verifies).
- C37: `review --verbose` prints one `DROPPED <feature> <kind>: <evidence> (not found)` line per dropped finding.
- C38: references/commands.md gains a quickstart (prerequisites: python3; gh for preview, file and triage; judge_command for the judge layer; expected output; exit codes), two copy-paste flows (preview, then file; review --json > r.json, then file --review r.json; triage --close dry run, then --yes) and an "Adding a rule" section; the exit-2 "no control" refusal names the rule and the module its fixture belongs in; fix hints are complete commands. SKILL.md stays under 150 lines by moving the per-group table to commands.md.
- C39: each group heading prints its slug: `== Security and privacy [security] (my angle: ...) ==`.
- C40: C27's FAILED lines end with one summary, `N acts failed, M succeeded; rerun is safe (issues match by marker)`, and gh stderr is stripped of token-like strings before printing. Test: fakegh failing one create; a rerun creates exactly one issue.
<!-- /autoplan-accepted:dx -->

<!-- autoplan-accepted:eng -->
- C41: a per-rule table names each rule's evidence inputs, identity fields only (path, requirement id, row id, pattern name, issue number, goal slug), never sizes, ages, counts, dates or line numbers. Tests: a script grown by one byte and the clock moved one day both leave a `health:closed` issue closed.
- C42: ghcache reads pages with `gh api --paginate --slurp` (gh 2.92 here), or a raw_decode loop where --slurp is missing; any non-zero gh exit is a failed read whatever stdout holds. fakegh emits concatenated pages and can fail mid-stream; both are tested.
- C43: HLT-1 determinism holds for a fixed tracker snapshot and is tested against fakegh; check-time is left out of the determinism comparison and is INFO unless the full default group set ran. ghcache fetches open issues (paginated) for issue-milestone, health-labelled issues of all states for findings and finding-age, and one cached `gh issue view N` per referenced number for refs, never the whole history.
- C44: ctx carries a monotonic run deadline (the check-time budget); every gh and subprocess call gets min(its timeout, the time left); when it runs out, the remaining gh-backed rules are UNREAD "deadline reached".
- C45: two issues that resolve to one migrated key keep the lowest number, and preview lists the rest as `DUPLICATE #N -> #M`, closed only by file. A requirements:R:proof issue closing while tests:R:seen-red opens when R leaves draft is the intended transition, tested through draft, runnable and proven. A marker-only change (adding evidence=) is listed as MIGRATE, and body comparison ignores the evidence token so issues do not churn.
- C46: evidence `file:line` must be a tracked repo-relative path (in git ls-files) with the line inside the file; review findings from another repo (C36 repo field) are refused. Every issue body and comment is sanitized before writing: fields capped (300 characters), @mentions, URLs and HTML comments stripped so no `loop-health` marker can be forged, token-like strings removed (C40). idle-sessions rows name no session path.
- C47: gather returns a status per canonical rule id (ran-pass, ran-fail, unread, skipped, not-run) next to the rows; report.complete and file.plan read it instead of inferring from missing rows; a failed regression.py sync marks every sync-fed rule in requirements and tests UNREAD; hygiene_rows' output is mapped to rule ids by the adapter (test-time to performance). Tests: failed sync, partial output and a skipped rule each close nothing and print no PASS.
- C48: not-enforced-7d and skipped read the tracked .loop/regression-runs.tsv (id, status, date): not-enforced-7d FAILs when no row of a requirement is PASS there; skipped WARNs on a SKIPPED row whose date is 7 or more days old; nightly reads the nightly lane record's time. The implementer confirms what the date column records and states it in the rule's contract. With regression-runs.tsv tracked, not-enforced-7d needs no local state, which replaces C2's INFO note.
- C49: row-requirement resolves a row's goal by type: a requirement id (must be defined on a page), `slug:N` (the goal file must have done line N), a defect reference, or `-` (explicitly unbound, INFO); it FAILs only on an unresolvable reference. Passing controls cover each valid form.
- C50: file orders each issue's acts (create, label, link) and stops an issue's later acts after a failure; triage adds `health:closed` first, then the comment, then closes; an unknown outcome is reconciled by marker on the next run. "Rerun is safe" in C40 means sequential runs. Tests: failure after server-side success, and a failure between triage's label and close.
- C51: every prerequisite read finishes before any write: milestones paginated with a return-code check (milestone.held reads one page today), covering issues' comments paginated; an incomplete read is the C31 refusal.
- C52: one longest-prefix helper in milestone.py serves goal_feature and feature_of; routing per subject type: docs findings by page name, proof and seen-red rows through the row's goal (requirement page or goal Touches), cost findings through the goal slug's Touches; ties go to the longest path, then Backlog. file sets a milestone only when opening, or when the issue is still on Backlog; it never moves an issue the owner placed.
- C53: the regenerated health workflow gives the check step GH_TOKEN, records the check's exit code in the summary instead of swallowing it, extracts review output by its new heading, and builds the skipped-groups sentence from groups.py; test-automation.sh asserts those lines. This lands with C2's health.yml half, on the owner's word.
- C54: LINK matches only qualified tokens (a path containing `/`, a prefixed requirement id such as HLT-3, a full row id) on the feature's milestone; a short id inside prose never links (negative test). Provisional pending taste d2.
- C55: each new module gets an expected size before building; triage and review keep their argparse in their own modules and health.py only dispatches; a fourth rules module is allowed when one passes 18 KB.
- C56: `preview` and `file --group criteria` print the expanded groups on stderr; a test shows `file --group criteria` acts on the same issues it did before, plus migrated keys.
- C57: callers that test exit code 1 for refusals (automation.py's workflow template, the loop scripts) are searched and updated with C34.
- C59: tests added: a page-two pull request dropped; `triage --older` at the day boundary with the pinned clock; `review --json` without a judge prints valid schema 1; a rerun after FAILED[milestone] creates it once; Mine does not run during file.
- C60: a build-time check confirms each C18 rule has its Rule contracts entry in the design; a rule without one is reported and not built.
<!-- /autoplan-accepted:eng -->
## Review record

Autoplan run loop-health-prd-20261110-013753, unattended worker plan step. The owner decides at the final gate; nothing
here is approved. UI scope: no (scope tool: uiRequired=false). DX scope: yes (scope tool: dxRequired=true, 3 term
matches: command x2, SKILL.md x1). Outside voice: Codex preflight `ready`.

### Phase 1 (CEO), Step 0

Methodology read in full: 4 ranges, lines 1-2257 of 2257. Mode: SELECTIVE EXPANSION (autoplan override; 0E's own count
of about 30 changed files would have recommended SCOPE REDUCTION, recorded here and not applied).

**System audit.** Base is main at e145b43 (v0.21.0). The branch carries the goal and design commits. The worktree also
holds uncommitted edits for two in-scope issues: cost.py (124: no tokens is INFO, not UNREAD), judge.py (158: the error
carries the first stderr line) and dev/toy/test-health-judge.sh (their assertions). No TODOS.md in this repo; deferrals
go to "NOT in scope" below and to the owner. `health.py check --skip controls` takes 1.92 s and `--group controls` 1.73 s
on this repo today [measured: /usr/bin/time -p, this worktree].

**0A Premise challenge.** The real problem: the owner cannot see, per feature, where the repo falls short of its own
PRDs, and every health issue lands on Backlog. The plan attacks that directly (feature milestones, review per feature,
triage). Do-nothing cost: findings keep piling on Backlog unrouted, and 118/124/158/159 stay open. Premise table:

| Premise | Claim | Receipt | Verdict |
|---|---|---|---|
| P-1 | health.py is 18.4 KB, so rules must go to new modules | `wc -c` 18403 bytes, skills/workflow-health/scripts/health.py:40 (LIMIT 20 KB) | verified |
| P-2 | the Reviewed stamp has a date the rules can read | skills/workflow-docs/scripts/criteria.py:40 (LINE captures `Reviewed (\d{4}-\d\d-\d\d)`) | verified |
| P-3 | a feature map from docs.tsv must be built | skills/workflow-health/scripts/milestone.py:45 (features) and :131 (goal_feature, longest-path match) already exist | finding: reuse |
| P-4 | renaming groups is a report-only change | skills/workflow-health/scripts/file.py:35 (key_of = family:subject:rule) keys every filed issue on the group name | finding: migration needed |
| P-5 | the scheduled workflow is unaffected | skills/workflow-health/scripts/automation.py:30 (GROUPS = "size,criteria,docs"), .github/workflows/health.yml:49 | finding: must regroup |
| P-6 | one gh fetch with no cap serves every gh rule | skills/workflow-health/scripts/file.py:79 (held: `--limit 500`) has the same cap R2-5 named | finding: share ghcache |
| P-7 | 124 changes Cost from UNREAD to INFO | .loop/regression.tsv:113 (cost-unread-tokens expects UNREAD) contradicts the fix | finding: retire or rewrite row |
| P-8 | the marker can gain `evidence=` in place | skills/workflow-health/scripts/file.py:85 (regex `loop-health (\S+) -->`) fails on a marker with a second token | finding: parse both forms |

unverified=0.

**0B Existing code leverage.** Rules keep their bodies (health.py size_rows, criteria_rows, docs_rows, defect_rows,
hygiene_rows; lean.py; cost.py). controls.py's fixture pattern (controls.py:80-150) serves every new rule. milestone.py
holds features(), ensure() and goal_feature(); feature.py must import them, not re-parse docs.tsv. file.py's plan()
(file.py:92) already computes open/update/reopen/close/same; LINK and the hash extend it. judge.py's ask() (judge.py:140)
already runs judge_command; review.py reuses it.

**0C Dream state.**
```
  CURRENT                         THIS PLAN                               12-MONTH IDEAL
  7 groups, 12 rules, all   --->  12 angled groups, ~36 rules each   --->  every PRD requirement traced to code,
  issues on Backlog, judge        with a control; findings on feature      rows and issues; owner triages one
  is free text                    milestones; evidence-checked review;     screen per feature; health trends over
                                  triage with recorded owner words         releases
```
The plan moves straight toward the ideal; trend over releases is the missing piece (NOT in scope).

**0D.** No new approach choice: the design's Approach B was taken at the idea step, and the Rule contracts govern.

**0E.** SELECTIVE EXPANSION (override). No new approach decision was needed.

**0F/0G cherry-picks (auto-decided, P1/P2 in blast radius, each under one day of CC work):**

| # | Proposal | Effort | Decision | Reasoning |
|---|---|---|---|---|
| C1 | Migrate filed-issue markers across the rename (criteria to requirements, cost to performance; old `loop-health KEY -->` and new `loop-health KEY evidence=H -->` both parse) | S | ACCEPTED | P-4/P-8: without it every open health issue is orphaned and refiled as a duplicate, breaking done line 2 ("a repeat updates") |
| C2 | Regroup automation.py GROUPS to the new runner-readable slugs and regenerate .github/workflows/health.yml | S | ACCEPTED (taste: health.yml is outside the goal's Touches list) | P-5: the alias expires after one release and then the scheduled job files nothing |
| C3 | file.py held() reads issues through ghcache (paginated, no 500 cap) | S | ACCEPTED | P-6, R2-5's own reasoning applies to the filer: a missed old issue is refiled |
| C4 | feature.py builds on milestone.features()/goal_feature() | S | ACCEPTED | P-3, DRY (P4) |
| C5 | file ensures the feature milestone exists (milestone.ensure) before `issue create --milestone` | S | ACCEPTED | gh refuses a missing milestone; the feature milestones may not exist yet |
| C6 | New local-state rules (scan-hook, idle-sessions, check-time) join file.py REPORT_ONLY | S | ACCEPTED | file.py:28 already keeps local paths and names off GitHub; a runner would close them as fixed |
| C7 | Retire or rewrite the cost-unread-tokens row for 124's INFO behavior | S | ACCEPTED | P-7: the row would go red against the fix |
| C8 | Health trend per release (verdict and counts per group over time) | M | DEFERRED | outside the PRD; needs stored history, which conflicts with read-only check |
| C9 | triage summary in the Automation digest comment | S | DEFERRED | crosses into the Automation feature; after triage ships |

**0H.** CEO summary saved outside the repo (the CEO plans folder for this project). Spec review loop below.

**0I Temporal interrogation.**
- Hour 1: groups.py and the alias table; the marker migration (C1) must land with the rename, in the same commit.
- Hours 2-3: which sync lines feed Requirements vs Tests (one cached regression.py sync per run, read by both).
- Hours 4-5: lane-control's REG-7 edit to health.py RULES collides with the table move; rebase onto it.
- Hours 6+: 24 fixtures; the slowest are gh-backed ones, which use fakegh.
Effort: human ~2 weeks / CC ~1.5 days.

<!-- autoplan-accepted:ceo -->
- C1: file.py reads both marker forms (`<!-- loop-health KEY -->` and `<!-- loop-health KEY evidence=H -->`). A key stays `group:subject:label`, and every row keeps its current subject and raw rule label (limit, rows, proof, stale, unmapped and the other docs kinds, open, waiting, run, merged, branch, time, tokens, defect-tests, test-time, worktrees, local-branches); only the group part moves. Migration maps the old family by its raw label: size:* stays size; criteria:*:rows (including criteria:done-lines:rows) to requirements; criteria:*:defect-tests to traceability; criteria:ROW:proof to requirements when ROW is a draft in today's .loop/regression.tsv, else to tests (the row's state, never the issue prose); docs:* stays docs; hygiene:* stays hygiene except hygiene:lane:test-time to performance; cost:* (including cost:judge:saves-*) to performance. A closed issue labelled health:closed with an old-form marker (no evidence hash) matches on its migrated key alone and stays closed. An issue filed before the rename is updated in place, never refiled or orphaned. Tests: one fakegh issue per old family and label above; each gets an update, none an open plus a stranded old issue.
- C2: automation.py GROUPS becomes the groups whose every rule reads only tracked files or gh: requirements, traceability, consistency, docs, size and adoption. Inputs: requirements rows, proof and done read regression.py sync (tracked .loop/regression.tsv and pages); traceability defect-tests reads defects.py (tracked files and gh), issue-milestone gh, row-requirement tracked files; consistency, docs (docs.py check), size and adoption (config.json, regression.tsv, VERSION, listing.json, .github/workflows) read tracked files only. `not-enforced-7d` reads the local run records (health.py:164-166), so on a fresh clone it is INFO "not applicable here", never PASS or FAIL. .github/workflows/health.yml is regenerated with `automation.py workflow`; it is outside the goal's Touches list, so this half waits for the owner's word at the final gate. Test: test-automation.sh asserts the new group list in the generated workflow.
- C3: file.py's held() reads health issues through ghcache's paginated fetch (no 500 cap). Test: fakegh with more than one page of issues; an issue on page two is SAME, not reopened.
- C4: feature.py imports milestone.features() and the goal_feature path match; no second docs.tsv parser.
- C5: before opening an issue on a feature milestone, file ensures that milestone exists (milestone.ensure); preview names a milestone it would create. Test: fakegh with no feature milestone; file creates it once, then the issue.
- C6: nightly, scan-hook, idle-sessions and check-time join file.py REPORT_ONLY, and REPORT_ONLY's "control" entry follows the controls rule's new label: shown in check, never filed or closed.
- C7: the cost-unread-tokens row (.loop/regression.tsv:113) is red now, because b490a73 changed its test output; its command is rewritten to grep the new INFO line and its seen-failing date records the red state before the rewrite. No tokens recorded is INFO; UNREAD stays only for a finished goal whose record cannot be read.
- C10: controls.CONTROLS is re-keyed to the new rule names and labels (size to scripts, criteria-rows to rows, criteria-done to done, and so on), and the new fixtures live in a new module beside controls.py so controls.py stays under 18 KB.
- C11: the `criteria` alias expands to requirements, traceability and tests for one release, so `--group criteria` still checks every rule it checked before; `cost` maps to performance.
- C12: each new rule's trigger and state are the design's Recommended Approach bullets as superseded by its Rule contracts section (.loop/goals/health-prd.design.md); a rule the design does not define is not built.
- C13: requirement map. HLT-1 and HLT-7: steps 3 (check-time), 12 (determinism, read-only, time). HLT-2: steps 1-4. HLT-3: step 2 (report). HLT-4: steps 6-7. HLT-5 and HLT-9: step 9. HLT-6: step 4 and the existing lean rules. HLT-8: step 8. Done lines: 1 steps 1-4; 2 steps 6-7 with C1, C3, C5; 3 step 9; 4 steps 7-8; 5 step 4 and the existing lean rules (test-time, worktrees, local-branches); 6 steps 3 and 12; 7 step 14; 8 step 13; 9 steps 5, 10, 11 and 13.
- C14: if this goal is otherwise done before docs-format merges, the HLT-7..HLT-9 rows and step 14 stay pending and the goal waits; it does not add the HLT-7..HLT-9 lines to Health.md itself.
- Already done and committed on this branch (b490a73): 124's cost.py change and 158's judge.py stderr change with their test lines. Plan steps 5 and 10 build on them; 158's setup `command -v` check is still to do.
- C15: file.py GROUPS, DEFAULT and TAG (file.py:24-26) are built from groups.py with the C11 aliases, so preview and file accept the new slugs and the old names; the default preview names every filable group except mine and controls. Test: `preview --group requirements` and `preview --group criteria` both run.
- C16: triage `--close` refuses without --why (exit 2, one REFUSED line), per the design's Rule contracts. Test: --close with no --why writes nothing and exits 2.
- C17: one rule signature: gather() calls every rule as fn(root, ctx); groups.py wraps each existing fn(root) rule in a one-line adapter, so their bodies stay unchanged. The regression.py sync output is cached in ctx and read by both Requirements and Tests.
- C18: the new rules, each with one new fixture (23): requirements not-enforced-7d; traceability issue-milestone, row-requirement; consistency ids-unique, refs, usage-readme; freshness nightly, unreleased, finding-age; tests seen-red, skipped, network; performance check-time; security private, scan-hook, workflow-permissions; size skill-lines, requirements-per-page; hygiene idle-sessions; adoption config, checks-run-tests, template-version, scheduled. requirements rows gains the Unreviewed WARN (118) and its existing fixture gains that case.
- C19: ghcache fetches with `gh api --paginate "repos/{owner}/{repo}/issues?state=all&per_page=100"` (gh issue list has no page option), drops entries carrying a pull_request field, and fakegh learns that route. Test: two pages in fakegh; an issue on page two is seen.
- C20: check-time reads its budget from ctx (default 60 seconds), so its fixture sets the budget to 0 and the rule fires at once.
- C21: preview lists each migration as `MIGRATE #N OLD-KEY -> NEW-KEY` before any write, so the owner sees the mapping on the live tracker first.
- C22: a filed issue closes only when its own rule ran and returned PASS this run; a rule that returned INFO or UNREAD closes none of its issues, even when other rules in its group passed (file.py:96-99 decides per group today). Test: a group with one PASS rule and one INFO rule; the INFO rule's open issue stays open.
- C23: triage `--close --yes` acts on at most 20 issues unless `--max N` names a higher number; over the cap it prints the list and REFUSED. Test: 21 matches with no --max closes none.
- C24: `workflow-permissions` WARNs on a workflow with no `permissions:` key and on `permissions: write-all`.
- C25: an issue filed from a model finding says so in its body (`found by the judge, evidence verified`), so the owner can weigh it.
- C26: tests assert that every group heading carries an angle, not the exact angle wording; and `health.py check --group size` passes on this repo after the change.
- C27: file checks each gh act's return code; a failing act prints `FAILED <act>: <first stderr line>`, the run continues with the rest and exits non-zero (file.py apply ignores it today). Test: fakegh failing one create; the line and exit code appear.
- C28: `file --review FILE` re-verifies every citation in the saved review against the repo at filing time and drops (and counts) findings whose evidence no longer exists.
<!-- /autoplan-accepted:ceo -->
<!-- autoplan-baseline-edits:ceo {"sourceSha256":"726d92a3ffa3b9b98d548ab1c2400ecef5c14af3f4bae9e1778099a25e70f2ce","replacements":[{"oldText":"14. The first inspection is done line 7. After docs-format merges:","newText":"14. Step 14 delivers done line 7, the first inspection. After docs-format merges:"},{"oldText":"The old names stay as aliases for one release: criteria → requirements,\n   cost → performance.","newText":"The old names stay as aliases for one release: criteria → requirements, traceability and tests,\n   cost → performance."},{"oldText":"4. controls.py: a fixture per new rule (about 24 new),","newText":"4. Controls: a fixture per new rule (23 new, listed in C18, in a new module beside controls.py),"},{"oldText":"   - `ghcache.py`: one paginated `gh issue list --state all` per run,","newText":"   - `ghcache.py`: one paginated `gh api --paginate` issues fetch per run (C19),"}]} -->

**0H Spec review loop (3 launches, the cap).** Round 1: 6/10 FAIL, 12 issues (old-to-new key table, controls re-key,
criteria alias, stale "uncommitted" line, red cost row, rule contracts, runner groups, step 14 wording, HLT map,
controls.py size, docs-format gate). Round 2: 6/10 FAIL, 12 new issues (file.py GROUPS/DEFAULT/TAG, old closed markers,
triage --why, nightly report-only, step 1 and step 4 wording, not-enforced-7d on a runner, proof split, rule signature,
judge savings keys, health.yml outside Touches). Round 3: 5/10 FAIL, 6 issues (full keys with subject and raw labels,
done-line map, per-rule inputs for C2, enumerated fixtures, gh issue list cannot paginate, check-time control).
Every round-1 and round-2 issue was absent from the next round. Round 3 is at the cap: issues verified: 6 of 6 (C1
rewritten to keep subject and raw label, C13 done-line map, C2 inputs, C18, C19, C20; applied edits, not a verdict).
Score 5 (latest). Metrics recorded: iterations 3, found 30, fixed 24, remaining 6. 0H document approval: auto-decided A
(approve and continue; unattended, the documents carry the exact decisions above). DONE_WITH_CONCERNS: round 3 was not
re-reviewed.

Baseline edits made in the Implementation plan (recorded above): step 1's alias text (C11), step 3's ghcache fetch
(C19), step 4's fixture count and module (C10, C18), step 14's wording.

### Phase 1 (CEO), dual voices

Input bound: ceo 981caa0a (snapshot after the spec loop). Native Claude CEO subagent: completed, INPUT hash matched.
Codex CEO voice: completed (OUTSIDE_STATUS: completed provider=codex host=claude, model gpt-6-astra, VERDICT findings P1).

Native findings (Claude subagent) and dispositions:
- F1 (high) coverage grows while the pain is signal; add a per-rule signal metric. DEFERRED (outside the PRD; listed in NOT in scope).
- F2 (medium) `assert len(GROUPS) == 12` hard-codes a taxonomy. REJECTED: HLT-2 and done line 1 name exactly twelve.
- F3 (high) the proof split reads issue prose. ACCEPTED: C1 now routes by the row's state in regression.tsv; C21 previews migrations.
- F4 (medium) size budget unchecked after the change. ACCEPTED: C26.
- F5 (medium) no check-time baseline. FACTUAL: measured 1.92 s without controls and 1.73 s for controls on this repo [measured: /usr/bin/time -p]; HLT-7's 60 s leaves room. No change.
- F6 (high) the goal hangs on docs-format; split it. USER CHALLENGE uc1 (Codex agrees on re-scoping).
- F7 (medium) ship the judge layer later. Part of uc1; done line 3 needs the judgment kinds, so the plan keeps it unless the owner splits.
- F8 (medium) tests pin angle wording. ACCEPTED: C26.
- F9 (medium) wrap gitleaks, zizmor or Scorecard. REJECTED: none is installed here, and the reuse ladder forbids a new dependency for a few lines.
- F10 (medium) auto-close on a passing check. FACTUAL: file.py plan() already closes a fixed finding (file.py:118-125); triage --close is for won't-fix.
- F11 (medium) rank groups by uniqueness. ACCEPTED as build order: Requirements, Traceability and the feature map first (design Next Steps 1-3 already).
- Bulk close cap. ACCEPTED: C23. Pagination cost. NOTED in Failure Modes; the check-time rule warns past budget.

Codex findings and dispositions:
- X1 (high) done lines measure the checker, not product value; run a delivery pilot. USER CHALLENGE uc1.
- X2 (high) alternatives never challenged scope. USER CHALLENGE uc1.
- X3 (high) a real citation does not make a finding correct. ACCEPTED in part: C25 labels model findings; filing stays on the owner's word (step 14). An adjudicated eval set is DEFERRED.
- X4 (high) a stable hash can hide a materially changed problem behind a dismissal. TASTE d1 (the design chose stability on purpose, R2-6).
- X5 (high) INFO can masquerade as resolution in a mixed group. ACCEPTED: C22 (closure per rule, PASS only).
- X6 (high) LINK on a shared path token is too loose. TASTE d2.
- X7 (high) workflow-permissions passes `write-all`; workflow policies penalize legitimate choices. ACCEPTED in part: C24. The policy-vs-correctness split is part of uc1.
- X8 (medium) no workload model for full issue history and review context. NOTED in Failure Modes.

```
CEO DUAL VOICES — CONSENSUS TABLE:
  Dimension                            Claude  Codex  Consensus
  1. Premises valid?                    mixed   no     CONFIRMED concern (migration and evidence premises)
  2. Right problem to solve?            partly  no     CONFIRMED concern (signal over coverage) -> uc1
  3. Scope calibration correct?         no      no     CONFIRMED: too big for one goal -> uc1
  4. Alternatives sufficiently explored? no     no     CONFIRMED gap (split, fewer rules)
  5. Competitive/market risks covered?  no      no     CONFIRMED gap (generic checks have substitutes)
  6. 6-month trajectory sound?          risky   risky  CONFIRMED risk (goal open on docs-format; policy debt)
```

### Phase 1 (CEO), review sections

**Section 1, Architecture.** Current scope: SELECTIVE EXPANSION, C1-C7 and C10-C26 accepted, C8/C9 deferred, uc1, d1, d2
pending for the owner.
```
  health.py (entry, check/preview/file/judge/review/triage)
     |-- groups.py  (12 groups, angles, aliases, adapters) <-- report.py, file.py, controls*.py, automation.py
     |-- rules: health.py legacy fns | rules_trace.py | rules_fresh.py | rules_guard.py  (fn(root, ctx))
     |-- ctx: ghcache.py (gh api --paginate) + sync cache + pages
     |-- review.py --> judge.py (judge_command) --> evidence verifier --> rows (no writes)
     |-- file.py --> feature.py --> milestone.py (features, ensure) --> gh (writes only on file/--live)
     |-- triage.py --> ghcache (read) / gh (close only with --yes)
```
Data flows (happy, nil, empty, error) for the filer: rows -> plan -> gh. Nil: gh missing gives held() None and file
refuses, as today. Empty: no findings closes only issues whose rule returned PASS (C22). Error: gh write fails mid-run;
file prints each act and stops; the next run reconciles by marker. Coupling: groups.py becomes the hub every module reads;
justified, it replaces four copies of the group list (health.py:48-51, report.py:9-16, file.py:24-28, automation.py:30).
Rollback: revert the merge; old markers still parse because C1 reads both forms, and new-form markers on issues are
ignored by old code only as unknown keys (it would reopen nothing, but would open duplicates; see Failure Modes).
Findings: 1 (rollback after a file run with new markers duplicates issues under old code). Disposition: recorded in
Section 9's rollback plan (do not run `file` until the release is cut).

**Section 2, Error and rescue map.**
```
  CODEPATH                 | WHAT CAN GO WRONG                   | CLASS            | RESCUED | USER SEES
  ghcache.fetch            | gh missing / auth / rate limit      | OSError, rc!=0   | Y       | INFO "gh not available here"
  ghcache.fetch            | malformed JSON page                 | ValueError       | Y       | INFO, never PASS
  groups import            | len != 12 or rule without control   | AssertionError / exit 2 | N (by design) | refusal line
  rules_* (each)           | unreadable file, bad regex input    | OSError, re.error | Y      | UNREAD for that rule
  review.judge             | judge missing / exits non-zero      | OSError, rc!=0   | Y       | JUDGE UNAVAILABLE: <stderr line>
  review.judge             | garbage or untagged output          | parse miss       | Y       | findings dropped, count printed
  review.verify            | citation does not exist             | n/a              | Y       | finding dropped and counted
  file.apply               | milestone missing                   | gh rc!=0         | Y (C5)  | milestone created, then issue
  file.apply               | gh write fails mid-plan             | gh rc!=0         | partial | the failing act printed; rerun reconciles
  triage --close           | no --why / over cap                 | refusal          | Y       | REFUSED, exit 2
```
GAP: file.apply today ignores a failing `gh` return code per act (file.py:151-160 runs and moves on). Disposition:
ACCEPTED into Eng scope as a check item (print FAILED for a failing act and exit non-zero); recorded as a task.

**Section 3, Security.** Threats: (a) `private` findings filed publicly point at a leak (likelihood low, impact medium);
the design shows file:line and pattern name only and its control proves the text never prints. (b) LLM prompt injection
through repo text into the judge: findings are only text, verified against the repo, and filing needs the owner's word;
mitigated. (c) triage bulk close: gated by --why, dry run, --yes and the C23 cap. (d) workflow-permissions weak check:
C24. No new secrets or dependencies. Findings: 2 (a: TASTE d3 report-only vs filed; d: accepted C24).

**Section 4, Data flow and edge cases.**
```
  rows -> key/evidence -> migrate(old key?) -> match held issue -> act(open|update|reopen|close|same|link)
   shadow: nil gh -> refuse | empty rows -> per-rule PASS closes only | dup old+new marker -> new wins, old updated
           stale review JSON -> citations re-verified at file time? (open) | two file runs at once -> duplicates
```
Edge cases: two concurrent `file` runs can both open the same new issue (no lock); the stale saved review file is not
re-verified (design R2-13 left open). Dispositions: concurrent runs NOTED (single-owner tool, automation runs one job);
re-verification at file time ACCEPTED into Eng as a check item.

**Section 5, Code quality.** New modules follow the existing pattern (a module per concern, a row() helper, controls by
fixture). DRY fixes accepted: C4 (milestone.py), C15 (file.py tables), C17 (one signature). Risk: three rules_* modules
each re-implement page parsing; Eng should put page parsing in one place (criteria.py LINE already exists). No method
over 5 branches can be judged before code exists.

**Section 6, Tests.** New things and their tests: groups/angles (presence, C26), 23 rules (fire and pass each, via
fixtures), migration (one per old family, C1), per-rule closure (C22), pagination (C19), milestone ensure (C5), LINK and
hash (design), triage (dry run, --yes, --why refusal, cap), review (good, unverifiable, failing judge), determinism,
read-only, check time, size after change (C26). Hostile QA test: a judge citing a real file:line for a false claim;
that passes verification by design (X3). Flaky risk: ages and `unreleased` depend on the clock; fixtures must pin dates.

**Section 7, Performance.** Today 1.92 s without controls [measured]. New cost: one paginated gh fetch (about 1 s per 100
issues page) plus `gh issue view` per unknown number, cached. Worst case grows with issue history (X8). check-time warns
past 60 s. Controls: 23 more fixtures at roughly 0.15 s each [estimated from 1.73 s / 12 fixtures] adds about 3.5 s.

**Section 8, Observability.** The report is the observability: every rule prints a line, INFO says why it did not run,
review prints dropped-finding counts and JUDGE UNAVAILABLE reasons. Gap: file prints acts but not a final count of
failures; covered by the Section 2 gap task.

**Section 9, Deployment and rollout.** Order: merge, cut the release, then run `file` (new markers). Rollback: before any
`file` run, revert is clean; after one, reverting means old code sees new keys as unknown and opens duplicates, so the
rollback is "fix forward". The scheduled workflow keeps working through the alias (C11) until health.yml is regenerated
(C2, owner's word).

**Section 10, Long-term trajectory.** Debt: aliases for one release, two controls modules, a hub module. Reversibility
3/5 (issue markers on GitHub are the one-way part). Path dependency: groups.py makes adding a rule a one-line change.
Platform potential: feature.py and ghcache serve Monitoring and Delivery later.

**Section 11, Design and UX.** SKIPPED (no UI scope).

### Phase 1 (CEO), required outputs

REALITY: premise-table pass 8 premises, unverified=0, 5 findings folded into C1-C7 skills/workflow-health/scripts/file.py:35
REALITY: already-done finding b490a73 already landed 124 and 158 on this branch; plan steps 5 and 10 build on it skills/workflow-health/scripts/cost.py:108
REALITY: surface-check finding health.py has check, judge, suggest, preview, run, file today; review and triage are new, and `gh issue list` has no page flag (C19) skills/workflow-health/scripts/health.py:360
REALITY: binding-decisions pass no branch decisions logged; the design's Rule contracts bind and C12 cites them .loop/goals/health-prd.design.md:180
REALITY: numbers pass 18403 bytes for health.py and 10270 for controls.py [measured: wc -c]; 1.92 s and 1.73 s [measured: time -p] skills/workflow-health/scripts/health.py:40
REALITY: deferred-asks pass issues 118, 124, 158 and 159 are all in scope; no request left out .loop/goals/health-prd.md:19
REALITY: pr-count pass no ship policy file; one PR for the goal (uc1 would make two) .loop/goals/health-prd.md:5

**NOT in scope.**
- Deferred: C8 health trend per release (needs stored history; read-only check). C9 triage summary in the Automation
  digest (Automation feature). F1 per-rule signal metric. X3 adjudicated eval set for the judge.
- Rejected: F2 dropping the exact-twelve assert (HLT-2). F9 wrapping external scanners (none installed).
- No TODOS.md exists here; these go to the owner at the gate.

**What already exists.** health.py rule functions (size, criteria, docs, defects, hygiene), lean.py (test-time,
worktrees, local-branches), cost.py, controls.py fixtures, report.py, file.py plan/preview/apply with markers,
milestone.py (features, ensure, goal_feature, move), judge.py (ask, gather, parse), automation.py (workflow, digest),
criteria.py LINE regex, fakegh. The plan reuses each (C4, C15, C17).

**Dream state delta.** After this plan: angled groups, feature routing, evidence-checked review, triage. Still missing
for the 12-month ideal: trend over releases and a signal measure of which rules the owner acts on.

**Failure Modes Registry.**
```
  CODEPATH        | FAILURE MODE                          | RESCUED | TEST  | USER SEES             | LOGGED
  file migrate    | old marker not mapped                 | Y (C1)  | Y     | update, no duplicate  | preview
  file close      | INFO rule closes its issue            | Y (C22) | Y     | stays open            | preview
  file apply      | gh act fails mid-plan                 | N <- GAP| N     | partial, silent rc    | act line only  (task E1)
  rollback        | old code after new markers            | N       | N     | duplicates            | none (fix forward; Section 9)
  ghcache         | history too large, slow check         | partial | N     | check-time WARN       | report
  review          | real citation, false claim            | N       | N     | issue on owner's word | label (C25)
  file --review   | stale saved review file               | N <- GAP| N     | outdated finding filed| none  (Eng item)
  concurrent file | two runs open the same issue          | N       | N     | duplicate issue       | none (single job)
```
CRITICAL GAPS: 0 rows with rescued=N, test=N and silent (file apply prints the act; stale review is visible in the body).

```
  +====================================================================+
  |            MEGA PLAN REVIEW — COMPLETION SUMMARY                   |
  +====================================================================+
  | Mode selected        | SELECTIVE EXPANSION                         |
  | System Audit         | 124/158 already landed; markers key on group |
  | Step 0               | 17 cherry-picks accepted, 2 deferred        |
  | Section 1  (Arch)    | 1 issue found                               |
  | Section 2  (Errors)  | 10 error paths mapped, 1 GAP                |
  | Section 3  (Security)| 2 issues found, 0 High severity             |
  | Section 4  (Data/UX) | 5 edge cases mapped, 2 unhandled            |
  | Section 5  (Quality) | 1 issue found                               |
  | Section 6  (Tests)   | Diagram produced, 1 gap (X3)                |
  | Section 7  (Perf)    | 1 issue found (X8)                          |
  | Section 8  (Observ)  | 1 gap found                                 |
  | Section 9  (Deploy)  | 1 risk flagged (rollback after file)        |
  | Section 10 (Future)  | Reversibility: 3/5, debt items: 3           |
  | Section 11 (Design)  | SKIPPED (no UI scope)                       |
  +--------------------------------------------------------------------+
  | NOT in scope         | written (6 items)                           |
  | What already exists  | written                                     |
  | Dream state delta    | written                                     |
  | Error/rescue registry| 10 rows, 0 CRITICAL GAPS                    |
  | Failure modes        | 8 total, 0 CRITICAL GAPS                    |
  | TODOS.md updates     | 0 (no TODOS.md; 4 deferrals to the owner)   |
  | Scope proposals      | 19 proposed, 17 accepted (SEL)              |
  | CEO plan             | written (CEO plans folder, outside repo)    |
  | Outside voice        | codex completed                             |
  | Lake Score           | N/A (no scored questions asked)             |
  | Diagrams produced    | 4 (architecture, data flow, error map, failure modes) |
  | Stale diagrams found | 0                                           |
  | Unresolved decisions | 4 (uc1, d1, d2, d3)                         |
  | Reality rows         | 7/7 rows, 0 unverified                      |
  +====================================================================+
```

### Phase 2 (Design)

Skipped: no UI scope (scope tool uiRequired=false, no rendered files or visual terms). Not a completed review.

### Phase 2.5 (DX)

Methodology read in full: 4 ranges, lines 1-1905 of 1905. Mode: DX POLISH (autoplan override). Product type: CLI tool
(health.py) shipped as an agent skill (SKILL.md). Web research: not run; reference benchmarks from in-distribution
knowledge, labelled as such.

**Persona (auto-decided, P6, from README "You review the pull request. One session governs and the others build").**
```
TARGET DEVELOPER PERSONA
========================
Who:       a solo repo owner who set the repo up from this template and works through an AI coding agent
Context:   asks "how healthy is the repo" or files and triages findings before a release; the agent runs health.py
Tolerance: one command for a report; a few minutes to configure a judge; no tolerance for a bulk close surprise
Expects:   one verdict line, a fix per finding, nothing written unless asked, same answer twice
```
Second lens for Pass 3: the agent itself, which reads every line literally and cannot ask.

**Empathy narrative.** I ask my agent "is the repo healthy?". It runs `python3 skills/workflow-health/scripts/health.py
check` and two seconds later I get twelve headed groups, each with its angle, and a last line `HEALTH: not green`. The
FAIL lines name a fix. Good. Then I want the issues on the right milestones: the agent runs `preview`, which lists
MIGRATE lines for my old criteria issues (I did not know that would happen; the preview is what saves me), then WOULD
lines on Health and Delivery. I say yes. Later I run `review`; with no judge set I get the deterministic findings and a
JUDGE UNAVAILABLE line, and I am not sure what to set or where (predicted confusion: the line names no config key).
Triage shows counts per feature; I close a batch of won't-fix with my words. If I typo `--kind`, today's plan prints
NOTHING TO CLOSE and I think I am done (predicted confusion, fixed below). Observed facts: the check command, its 1.92 s
run time and the verdict line exist today (health.py:266, measured). The rest is predicted from the plan.

**Competitive benchmark (reference, not measured).**

| Tool | Start to result | Time + evidence type | DX choice | Source |
|---|---|---|---|---|
| OpenSSF Scorecard CLI | install binary, set GITHUB_AUTH_TOKEN, run on a repo | ~5 min, reported (in-distribution) | one score per check with a doc link per check | in-distribution |
| repolinter | npm install, run with a ruleset | ~3 min, reported (in-distribution) | rule files, JSON output | in-distribution |
| this product, check | skill installed, run one command | under 1 min, observed for the run (1.92 s), setup excluded | one verdict line, fix per line | health.py:266 |
| this product, review with judge | set judge_command, run review | ~5 min, estimated | deterministic layer works without a judge | plan step 9 |

Target (auto-decided, P5): Champion (under 2 min) for check and preview; Competitive (2-5 min) for review with a judge.

**Magical moment (auto-decided, P5, lowest-effort vehicle).** The first `preview` after the upgrade shows every old issue
mapped (MIGRATE) and every finding on its feature milestone, with nothing written. Vehicle: existing preview output
(C21), no new surface.

**Developer journey map.**
```
STAGE           | DEVELOPER DOES                          | FRICTION POINTS                         | STATUS
----------------|-----------------------------------------|-----------------------------------------|--------
1. Discover     | reads SKILL.md description              | description lists old groups (159)      | fixed (step 11)
2. Install      | skill already installed with the repo   | none                                    | ok
3. Hello World  | health.py check                         | slug vs heading name differ             | fixed (C39)
4. Real Usage   | preview, file, review, triage           | typo reads as NOTHING TO CLOSE; JSON handoff unversioned | fixed (C32, C36)
5. Debug        | reads FAILED / REFUSED / JUDGE lines    | no fix line, mixed exit codes           | fixed (C34, C31)
6. Upgrade      | first preview after the release         | silent aliases, old JSON consumers      | fixed (C35)
```

**First-time developer report.**
```
Persona: solo owner via agent. Attempting: health after the upgrade.
T+0:00  check: twelve groups print; the verdict is last.
T+0:30  agent runs `--group security`; works only because the slug is guessed (C39 prints it).
T+1:00  preview: MIGRATE lines appear; owner reads them before saying yes (C21).
T+2:00  review: JUDGE UNAVAILABLE with no config key named (C31 adds the fix line).
T+3:00  triage --close with a misspelled kind: today NOTHING TO CLOSE (C32 refuses with the valid kinds).
```

**Dual voices.** Native Claude DX subagent: completed (INPUT dx 3ea26ae4 matched). Codex DX voice: completed
(OUTSIDE_STATUS: completed provider=codex host=claude, VERDICT findings P1).

```
DX DUAL VOICES — CONSENSUS TABLE:
  Dimension                           Claude  Codex  Consensus
  1. Getting started < 5 min?          7/10    4/10   DISAGREE (Codex counts template setup) -> resolved by C38 quickstart
  2. API/CLI naming guessable?         6/10    5/10   CONFIRMED gap (selectors, slugs, aliases)
  3. Error messages actionable?        5/10    4/10   CONFIRMED gap (fix, recovery, codes, exit codes)
  4. Docs findable & complete?         6/10    4/10   CONFIRMED gap (copy-paste flows, adding a rule)
  5. Upgrade path safe?                n/a     6/10   CONFIRMED gap on deprecation notices (both name it)
  6. Dev environment friction-free?    5/10    n/a    CONFIRMED gap on side effects (Codex) and escape hatches (Claude)
```

Findings and dispositions (N = native, X = Codex):
- N1/X3 gh read failure must not look like success; writers fail closed. ACCEPTED C31. Whether a failing gh read in check is UNREAD or INFO: TASTE d4.
- N2 INFO "gh not available" names no fix. ACCEPTED C31.
- N3/X2 FAILED lines lack recovery and a summary. ACCEPTED C27 extended (C40).
- N4 milestone ensure and the health:closed label failures. ACCEPTED C29.
- N5/X7 triage typos, units, cap refusal. ACCEPTED C32.
- N6 JUDGE UNAVAILABLE names no fix. ACCEPTED C31 (fix line); exit 0 stays per the design contract.
- N7 clock rules break determinism. ACCEPTED C33 (ctx carries `now`; rows print thresholds only, per the design).
- N8 suppress one finding (allowlist). DEFERRED: new surface, outside DX POLISH; NOT in scope.
- N9/X2 stable codes and exit codes. ACCEPTED C34.
- N medium: deprecation notes (C35), review JSON schema (C36), DROPPED lines (C37), check-time budget key (C20 note in C33), feature list on unknown --feature (C32), adding-a-rule guide and copy-paste flows (C38), slug in headings (C39), `--summary` one line per group DEFERRED.
- X1 quickstart with prerequisites, output and exit codes. ACCEPTED C38.
- X4 versioned review JSON envelope, stdout JSON only. ACCEPTED C36.
- X5 preview gathers every group including Mine (health.py:324), and milestone.ensure writes a tracked wiki page through link_page (milestone.py:80-90). ACCEPTED C29, C30.
- X6 check-time must measure the whole run; shared subprocess deadline. ACCEPTED in part: check-time evaluated last over the whole non-control run (C33). Shared deadline DEFERRED.
- X8 copy-paste fix hints. ACCEPTED C38.
- X9 compatibility for JSON consumers and old commands. ACCEPTED C35.
- X10 saved review bound to repo and revision. ACCEPTED C36; finding identity vs evidence freshness stays TASTE d1.

**Pass 1, Getting started: 7 -> 8.** One command gives a full report today (health.py:266). Gap: no quickstart naming
prerequisites (python3, gh for filing, judge_command for review), expected output and exit codes. C38 adds it. A 10 would
also time the quickstart in CI; not in DX POLISH scope.

**Pass 2, CLI design: 6 -> 8.** Verbs are guessable; selectors were not. C32 validates --feature/--kind against known
values and lists them; C39 prints the slug in each heading; C35 notes aliases. `file` doing open, update, reopen, close
and link stays one verb (established; preview names every act).

**Pass 3, Errors: 4 -> 7.**
```
ERROR PATH MATRIX (agent-ready-v1)
Path                    | Class      | what | fix  | recovery | code | context | trace | redaction | channel | Cap
triage --close (no why) | usage      | pass | pass | N/A      | C34  | N/A     | N/A   | pass      | exit 2  | none after C34
file gh act fails       | dependency | pass | C40  | C40      | C34  | pass    | N/A   | C40       | exit 1  | was CAP6:recovery
ghcache page 2 fails    | dependency | pass | C31  | C31      | C34  | pass    | N/A   | C40       | exit 2  | was CAP6:recovery (CAP4 if partial list used)
review judge fails      | dependency | pass | C31  | pass     | C34  | pass    | N/A   | C40       | exit 0  | was CAP6:fix
unexpected crash        | unexpected | pass | gap  | gap      | gap  | gap     | traceback today | unknown | exit 1 | CAP6:trace (residual)
```
Residual: an unexpected exception prints a raw traceback; accepted as residual (scores 7, not 8). Redaction: C40 strips
tokens from gh stderr before printing.

**Pass 4, Docs: 5 -> 7.** Step 11 rewrites charts; C38 adds the quickstart, two copy-paste flows (preview to file;
review --json to file --review; triage dry run to --yes) and an "Adding a rule" section. SKILL.md is 125 lines and the
new skill-lines rule caps it at 150, so the per-group table moves to references/commands.md.

**Pass 5, Upgrade: 6 -> 8.** C1/C21 migrate issues; C35 adds stderr deprecation notes with the removal version, keeps
`suggest` and `--family`, removes `run` (159), and keeps the JSON `family` key with new group values, noted in the
CHANGELOG.

**Pass 6, Dev environment: 6 -> 7.** Works in Actions (automation.py). C30 stops preview from running Mine's private
commands; C29 stops file from editing a tracked wiki page. Dry-run exists (preview, triage default). No per-rule
escape hatch (deferred).

**Pass 7, Community: 5 -> 5.** Single-owner template; issues and the wiki are the channels. No findings in scope.

**Pass 8, Measurement: 3 -> 4.** check-time reports the run budget (C33). No TTHW instrumentation; a `/devex-review`
after shipping is the measurement. No new telemetry (not approved).

```
+====================================================================+
|              DX PLAN REVIEW — SCORECARD                             |
+====================================================================+
| Dimension            | Score  | Prior  | Trend  |
|----------------------|--------|--------|--------|
| Getting Started      |  8/10  |  7/10  |  +1    |
| API/CLI/SDK          |  8/10  |  6/10  |  +2    |
| Error Messages       |  7/10  |  4/10  |  +3    |
| Documentation        |  7/10  |  5/10  |  +2    |
| Upgrade Path         |  8/10  |  6/10  |  +2    |
| Dev Environment      |  7/10  |  6/10  |  +1    |
| Community            |  5/10  |  5/10  |   0    |
| DX Measurement       |  4/10  |  3/10  |  +1    |
+--------------------------------------------------------------------+
| TTHW                 | <1 min check / ~5 min review | same | 0  |
| Competitive Rank     | Champion (check), Competitive (review)      |
| Magical Moment       | designed via preview (MIGRATE + milestones) |
| Product Type         | CLI tool in an agent skill                  |
| Mode                 | POLISH                                      |
| Overall DX           |  7/10  |  5/10  |  +2    |
+====================================================================+
| DX PRINCIPLE COVERAGE                                               |
| Zero Friction      | covered                                        |
| Learn by Doing     | covered (copy-paste flows, C38)                |
| Fight Uncertainty  | covered (C31, C32, C34, C40)                   |
| Opinionated + Escape Hatches | gap (no per-finding suppress; deferred) |
| Code in Context    | covered                                        |
| Magical Moments    | covered                                        |
| Agents Are Users   | covered (exit codes, JSON envelope)            |
+====================================================================+
```
Prior scores are this review's pre-fix pass scores (no earlier DX review of this plan).

```
DX IMPLEMENTATION CHECKLIST
============================
[x] Time to hello world < 2 min (check)
[x] Installation is one command (skill installed with the repo)
[x] First run produces meaningful output
[ ] Magical moment delivered via preview MIGRATE + milestone lines (C21, to build)
[ ] Every error message meets the agent-ready contract (C31, C32, C34, C40; crash trace residual)
[ ] CLI naming guessable without docs (C32, C39)
[x] Every parameter has a sensible default
[ ] Docs have copy-paste examples that work (C38)
[ ] Upgrade path documented with deprecation notes (C35)
[x] Works in CI without special configuration (automation.py)
[x] Changelog exists and is maintained
N/A TypeScript types, free tier, community channel
```

**NOT in scope (DX).** Per-finding allowlist (N8); `--summary` view; shared subprocess deadline (X6); TTHW telemetry.

**What already exists (DX).** preview (dry run), REFUSED lines (health.py:242-351), the verdict line and exit code
(report.py), commands.md charts, automation.py's workflow, triage's dry-run design.

<!-- autoplan-accepted:dx -->
- C29: file creates a missing feature milestone through the GitHub call alone (the gh api part of milestone.ensure, split out), never link_page, so file changes nothing tracked; a creation failure prints `FAILED[milestone] <name>: <stderr line>`, skips that milestone's issues and exits non-zero. The `health:closed` label is created the same way as the group labels. Test: no feature milestone and no Milestone line on the page; file creates the milestone and leaves the page byte-identical.
- C30: preview and file gather only the groups they will file (never Mine's private commands unless `--group mine` is named). Test: a Mine command that would write a file does not run during `preview --group requirements`.
- C31: ghcache fails closed for writers: any gh error or partial page makes preview, file and triage exit 2 with `REFUSED[gh-read] could not read issues (page N): <stderr line>. Fix: gh auth status, then rerun`; check's rules keep a row with a fix line (`install gh and run gh auth login`). JUDGE UNAVAILABLE names its fix: `set judge_command in .loop/config.json; health.py setup shows whether it resolves`. Test: fakegh failing page 2; file writes nothing and exits 2.
- C32: triage and review validate --feature against docs.tsv pages and --kind against known kinds, refusing an unknown value with exit 2 and the valid list; `--older` is whole days; the C23 over-cap refusal reads `REFUSED[cap] 21 matches over 20. Fix: add --max 21` with exit 2.
- C33: rules read the time from ctx (`now`), so tests pin the clock; check-time is evaluated last and measures the whole non-control run against ctx's budget (default 60 seconds, `health_check_seconds` in .loop/config.json overrides); rows print thresholds and states, never measured values.
- C34: every refusal exits 2 and starts `REFUSED[code]`, every failed write starts `FAILED[code]`; exit 0 green, 1 not green, 2 refused; references/commands.md lists each code with its fix. Existing `sys.exit("REFUSED...")` paths (exit 1 today) move to exit 2, and their tests follow.
- C35: old names (criteria, cost, --family, suggest) print one stderr NOTE naming the new name and the release that removes them; `run` is removed (159); `--json` keeps the `family` key with the new group values; the CHANGELOG lists the renamed groups, rules and exit codes.
- C36: `review --json` prints one JSON object on stdout only: schema 1, repo, HEAD sha, judge status, findings and dropped counts. `file --review` refuses a missing or other schema with the command that regenerates it, and warns when the saved HEAD differs from the current one (then C28 re-verifies).
- C37: `review --verbose` prints one `DROPPED <feature> <kind>: <evidence> (not found)` line per dropped finding.
- C38: references/commands.md gains a quickstart (prerequisites: python3; gh for preview, file and triage; judge_command for the judge layer; expected output; exit codes), two copy-paste flows (preview, then file; review --json > r.json, then file --review r.json; triage --close dry run, then --yes) and an "Adding a rule" section; the exit-2 "no control" refusal names the rule and the module its fixture belongs in; fix hints are complete commands. SKILL.md stays under 150 lines by moving the per-group table to commands.md.
- C39: each group heading prints its slug: `== Security and privacy [security] (my angle: ...) ==`.
- C40: C27's FAILED lines end with one summary, `N acts failed, M succeeded; rerun is safe (issues match by marker)`, and gh stderr is stripped of token-like strings before printing. Test: fakegh failing one create; a rerun creates exactly one issue.
<!-- /autoplan-accepted:dx -->

### Phase 3 (Eng)

Methodology read in full: 4 ranges, lines 1-2143 of 2143. Scope gate: the plan file named by the caller (B). Correction
carried into the CEO premise table: criteria.py lives in skills/workflow-docs/scripts (criteria.py:40), not in
workflow-regression.

**Scope Challenge A.**
- What already exists: rule bodies in health.py, lean.py, cost.py, defects.py; report.complete (report.py:40) synthesizes
  PASS for silent rules; file.plan/preview/apply (file.py:92-160); milestone.features/held/ensure/goal_feature
  (milestone.py:45-146); lanes.py lane records; .loop/regression-runs.tsv (tracked: id, status, date per row);
  criteria.py LINE (workflow-docs); fakegh in dev/toy.
- Minimum change: the PRD needs all four parts; nothing is deferrable without breaking a frozen done line (CEO uc1 asks
  the owner whether to split instead).
- Complexity: about 30 changed files [estimated: 8 new modules, about 9 edited scripts, 8 test scripts, docs and rows];
  new modules 8 (groups, rules_trace, rules_fresh, rules_guard, ghcache, feature, triage, review, plus a controls module).
  Gate B trips (8+ files, 2+ new modules).
- Search: not run (no web research here); [Layer 1] choices only: gh api pagination with --slurp, json, argparse.
- TODOS: no TODOS.md in this repo; deferrals stay in NOT in scope for the owner.
- Retrospective: closure semantics already changed twice in file.py history (f87b657 "clean group still closes its
  issues", 0b66c6c "controls never filed"). C22 touches that recurring area, so its tests are critical.
- Distribution: ships in the package release (listing.json, VERSION); no new artifact channel.

**Scope Challenge B (auto-decided).** Structure question `plan-eng-review-structure`: Original arrangement (8 modules)
vs a smaller one (fold ghcache and feature into file.py, triage into file.py). Auto-decided Original arrangement: file.py
is 8.1 KB and gains LINK, the hash and migration, so folding more in breaks the 20 KB scripts rule; P5. No feature cuts
(P2, never reduce). Scope record: feature answers none; structure A (auto, P5); accepted scope: as planned plus C1-C40;
pending remedies: uc1, d1-d5. Scope Challenge result: scope accepted as-is.

REALITY: premise-table pass 9 premises checked, unverified=0; criteria.py path corrected to workflow-docs skills/workflow-docs/scripts/criteria.py:40
REALITY: already-done finding b490a73 on this branch already carries 124 and 158; origin/main has no health-prd work skills/workflow-health/scripts/judge.py:148
REALITY: surface-check finding `gh issue list` has no page flag; gh 2.92.0 here has `gh api --paginate --slurp`; review and triage subcommands do not exist yet skills/workflow-health/scripts/health.py:360
REALITY: binding-decisions pass design Rule contracts and the CEO accepted block bind; no logged branch decisions .loop/goals/health-prd.design.md:180
REALITY: numbers pass 18403 B health.py, 8109 B file.py, 10270 B controls.py [measured: wc -c]; ~30 files [estimated] skills/workflow-health/scripts/file.py:1
REALITY: deferred-asks pass 118, 124, 158, 159 all mapped to steps (C13) .loop/goals/health-prd.md:19
REALITY: pr-count pass one PR unless the owner accepts uc1 (then two) .loop/goals/health-prd.md:5

**Dual voices.** Native Claude eng subagent: completed (INPUT eng 706633b1 matched). Codex eng voice: completed
(OUTSIDE_STATUS: completed provider=codex host=claude, VERDICT findings P1).

```
ENG DUAL VOICES — CONSENSUS TABLE:
  Dimension                           Claude  Codex  Consensus
  1. Architecture sound?               yes*    no     DISAGREE in degree: structure sound, result contract missing -> C47 (both name it)
  2. Test coverage sufficient?         no      no     CONFIRMED gaps (lifecycle, failure-after-success, multi-page)
  3. Perf risks + budget/bench named?  no      no     CONFIRMED (fetch every issue; no run deadline) -> C43, C44
  4. Security threats covered?         no      partly CONFIRMED (untrusted text into issues; repo identity) -> C46, C36
  5. Error paths handled?              no      no     CONFIRMED (partial reads, write ordering) -> C50, C51
  6. Deployment risk manageable?       partly  no     CONFIRMED (workflow credentials and exit codes) -> C53
```

Findings (N = native, X = Codex) and dispositions, all auto-decided unless marked:
- [CRITICAL] (confidence: 9/10) skills/workflow-health/scripts/report.py:40-55 — `complete()` writes PASS for any rule
  of a ran group with no row; SHARED covers only criteria rows -> done-lines. With sync split across two groups, a failed
  sync could print PASS and, under C22, authorize closes. (X1, N M1) ACCEPTED C47.
- [CRITICAL] (confidence: 9/10) skills/workflow-regression/scripts/regression.py:184 — draft rows carry
  `goal="slug:N"`, so `row-requirement` as designed FAILs every done-line row. (X3) ACCEPTED C49.
- [CRITICAL] (confidence: 8/10) gh api --paginate prints concatenated arrays without --slurp. (N H2) ACCEPTED C42.
- [CRITICAL] (confidence: 8/10) evidence hash inputs undefined per rule; a byte count or age in it reopens every
  dismissed issue. (N H1) ACCEPTED C41.
- [INFORMATIONAL] (confidence: 8/10) skills/workflow-health/scripts/milestone.py:62-68 — milestones read one page,
  no return-code check. (X8) ACCEPTED C51.
- [INFORMATIONAL] (confidence: 8/10) skills/workflow-health/scripts/milestone.py:138-142 — goal_feature returns the
  first matching page, not the longest prefix. (X9) ACCEPTED C52.
- [INFORMATIONAL] (confidence: 8/10) skills/workflow-health/scripts/automation.py:81 — the check step swallows its exit
  code and gets no GH_TOKEN. (X10) ACCEPTED C53 (part of C2's health.yml half, owner's word).
- [INFORMATIONAL] (confidence: 7/10) temporal rule sources: lane records merge runs (lanes.py:90-99) and carry no
  per-row age; .loop/regression-runs.tsv is tracked and holds id, status, date. (X2) ACCEPTED C48.
- [INFORMATIONAL] (confidence: 7/10) migration identity across draft -> runnable, duplicates on one key, marker-only
  rewrites. (N H4, X4, N M3) ACCEPTED C45.
- [INFORMATIONAL] (confidence: 7/10) model and repo text into issues; evidence paths not confined. (N H5, X5)
  ACCEPTED C46; repo identity in C36 tightened by C46.
- [INFORMATIONAL] (confidence: 7/10) write ordering and failure after server success. (X6) ACCEPTED C50.
- [INFORMATIONAL] (confidence: 7/10) check depends on the live tracker; fetching every issue; check-time flips with
  load. (N H3, N M2, X7) ACCEPTED C43, C44.
- [INFORMATIONAL] (confidence: 6/10) module sizes (N M4) ACCEPTED C55. criteria alias in file (N M5) ACCEPTED C56.
  LINK short tokens (N M6) folded into TASTE d2's default (C54). Exit-code callers (N L3) ACCEPTED C57. Test gaps (N L4)
  ACCEPTED C59. Contract per rule build check (N L5) ACCEPTED C60. idle-sessions output (N L1) ACCEPTED in C46.
  Per-number lookups (N L2) folded into C43.

**Section 1, Architecture.**
```
                         health.py (dispatch only; argparse for review/triage in their modules)
                              |
            +-----------------+------------------+------------------+
            |                 |                  |                  |
        groups.py         report.py           file.py            review.py   triage.py
   (12 groups, angles,  (headings with      (plan/preview/      (det. layer   (list, close
    aliases, rule ids,   slug+angle,         apply, migrate,     + judge,      dry run/--yes,
    adapters, status)    complete() from     LINK, hash)         verify)       cap)
            |            rule status)           |   |               |   |         |
   rules: health.py legacy | rules_trace | rules_fresh | rules_guard  |   judge.py  |
            |                                   |   +-> feature.py -+   (ask)      |
          ctx: now, deadline, sync cache,       |        |                         |
               pages, ghcache ------------------+--------+-------------------------+
               (gh api --paginate --slurp)               milestone.py (features, longest prefix,
                                                          create-only milestone call; link_page stays
                                                          in milestone.py's own commands)
```
Design-twice: shape A (plan) puts rule results in rows plus a per-rule status set owned by groups.py; shape B would put
each rule behind a class with run/control/evidence methods. A hides more behind less (one function signature, one
status set) and matches the repo's function-per-rule style; pick A. Red flags: hand-synced list (the group list lives
in four places today: health.py:48-51, report.py:9-16, file.py:24-28, automation.py:30) fixed by groups.py (C15);
two ways to do one task (goal_feature first-match vs feature_of longest prefix) fixed by C52; split ownership of
"ran" (report.complete vs file.plan) fixed by C47. Production failure per integration: gh rate limit mid-pagination
(C31, C42); judge timeout (JUDGE UNAVAILABLE); milestone creation failure (C29).

**Section 2, Code quality.** Findings: C47 (rule status), C52 (one longest-prefix helper; callers milestone.attach and
feature_of), C55 (sizes). Shared code: page parsing for requirement ids is needed by rules_trace (ids-unique, refs),
feature.py and review.py; put it in one helper next to criteria.LINE use (callers: three proposed modules, labelled
proposals). No stale ASCII diagrams in touched files today.

**Section 3, Test review.** Framework: bash toy tests in dev/toy (test-*.sh) driving the scripts with fakegh, rows in
.loop/regression.tsv.
```
CODE PATHS                                              USER FLOWS
[+] groups.py                                           [+] check
  ├── [GAP] exactly-12 assert, alias expansion            ├── [GAP] twelve headed groups, slug + angle (C26, C39)
  └── [GAP] rule status set (C47)                         ├── [★★ TESTED] same lines twice (same-lines row)
[+] rules_* (23 new rules)                                └── [GAP] fixed tracker snapshot determinism (C43)
  ├── [GAP] fire + pass per rule via fixtures (C18)     [+] preview -> file
  ├── [GAP] row-requirement typed forms (C49)             ├── [GAP] MIGRATE and DUPLICATE lines (C21, C45)
  └── [GAP] temporal rules with pinned now (C33, C48)     ├── [GAP] [→E2E] file on fakegh: milestones, LINK, labels
[+] ghcache                                               ├── [GAP] rerun after FAILED creates one issue (C40, C50)
  ├── [GAP] two pages, PR dropped (C19, C42)              └── [GAP] gh fails page 2: nothing written, exit 2 (C31)
  └── [GAP] mid-stream failure = failed read            [+] review
[+] file.py                                               ├── [GAP] good / unverifiable / failing judge
  ├── [GAP] migration per old family (C1)                 ├── [GAP] --json schema 1 with no judge (C36)
  ├── [GAP] closure only on own PASS (C22, C47)           └── [GAP] [→EVAL] judge prompt quality (deferred, X3)
  ├── [GAP] evidence hash stable: +1 byte, +1 day (C41) [+] triage
  └── [GAP] sanitized bodies, no forged marker (C46)      ├── [GAP] dry run, --yes, --why refusal, cap, unknown kind
[+] feature.py                                            └── [GAP] label-before-close ordering (C50)
  └── [GAP] routing per subject type, ties (C52)
[+] automation.py
  └── [★★ TESTED] group list in workflow (test-automation.sh) -> extend for C53
COVERAGE: 2/26 paths tested today (all new code) | QUALITY: ★★:2 | GAPS: 24 (1 E2E, 1 eval deferred)
```
Every GAP becomes a case in dev/toy/test-health-prd.sh or an extension of the named existing test; the value cards are
in the test plan artifact. Regression rule: existing behavior at risk (filed-issue identity, closure, exit codes,
`--group criteria`) gets explicit preservation tests (C1, C22, C56, C34). Tests made obsolete: cost-unread-tokens row
(rewritten, C7); `run` chart assertions (159).
Test plan artifact: written to the project's state folder (eng-review-test-plan for this branch).

**Section 4, Performance.** Hot path: check without controls, budget 60 s (HLT-7), today 1.92 s [measured]. New costs:
open-issue fetch plus health-label fetch (pages of 100) and per-referenced-number views, bounded by the run deadline
(C43, C44). Memory: issue lists in ctx, a few MB at most for thousands of issues [estimated]. Controls: 23 fixtures,
about 3.5 s more [estimated from 1.73 s / 12]. Finding: a full-history fetch per check had no bound; fixed by C43/C44.

**Failure modes registry.**
```
  PATH            | FAILURE                               | TEST    | HANDLING          | USER SEES          | GAP?
  report.complete | failed sync shown as PASS             | C47     | status set        | UNREAD             | fixed
  file.plan       | close on INFO/skipped rule            | C22/C47 | per-rule PASS     | issue stays open   | fixed
  ghcache         | page N fails / concatenated JSON      | C42     | fail closed       | REFUSED[gh-read]   | fixed
  file.apply      | create ok remotely, timeout locally   | C50     | marker reconcile  | one issue on rerun | fixed
  triage          | close ok, label fails                 | C50     | label first       | stays dismissed    | fixed
  rules temporal  | no per-row age in lane records        | C48     | regression-runs   | WARN with date     | fixed
  row-requirement | done-line rows flagged                | C49     | typed resolver    | PASS               | fixed
  review/file     | injected text posted to issues        | C46     | sanitize, confine | clean body         | fixed
  check           | tracker growth past 60 s              | C44     | deadline          | UNREAD (deadline)  | fixed
  concurrent file | two runs open the same issue          | none    | none              | duplicate          | accepted (single job)
```
Critical gaps (no test, no handling, silent): 0 after the accepted items.

**Worktree parallelization.**
| Step | Modules touched | Depends on |
|---|---|---|
| groups + report + adapters | skills/workflow-health/scripts (groups, report, health) | — |
| rules modules + controls | skills/workflow-health/scripts (rules_*, controls*) | groups |
| ghcache + feature + file | skills/workflow-health/scripts (ghcache, feature, file, milestone) | groups |
| review + triage | skills/workflow-health/scripts (review, triage, judge) | ghcache, feature |
| docs, rows, tests | skills/workflow-health/references, dev/toy, .loop | all above |
Lane A: groups -> rules. Lane B (after groups): ghcache/feature/file -> review/triage. Conflict flag: both lanes touch
health.py dispatch and the same scripts folder; sequential is safer. Sequential implementation recommended.

**NOT in scope (Eng).** Concurrent `file` runs (single scheduled job); judge eval suite (X3, deferred); per-finding
allowlist; health trend.

**What already exists (Eng).** As Scope Challenge A; reused: report.complete (extended, C47), file.plan (extended),
milestone helpers (C29, C51, C52), lanes/regression-runs (C48), criteria.LINE, fakegh (extended).

```
Eng completion summary
- Step 0: Scope Challenge — scope accepted as-is (structure A, auto-decided)
- Reality rows: 7/7 applicable rows emitted, 0 unverified premises
- Architecture Review: 3 issues found (C47, C52, deadline)
- Code Quality Review: 3 issues found (C47, C52, C55)
- Test Review: diagram produced, 24 gaps identified (all planned)
- Performance Review: 1 issue found (C43/C44)
- NOT in scope: written
- What already exists: written
- TODOS.md updates: 0 written (no TODOS.md in this repo; 8 deferrals listed for the owner)
- Failure modes: 0 critical gaps flagged
- Unresolved decisions: 6 (uc1, d1-d5)
- Outside voice: codex completed
- Parallelization: 2 lanes, 0 parallel / 2 sequential
- Lake Score: N/A (no scored questions asked)
```

<!-- autoplan-accepted:eng -->
- C41: a per-rule table names each rule's evidence inputs, identity fields only (path, requirement id, row id, pattern name, issue number, goal slug), never sizes, ages, counts, dates or line numbers. Tests: a script grown by one byte and the clock moved one day both leave a `health:closed` issue closed.
- C42: ghcache reads pages with `gh api --paginate --slurp` (gh 2.92 here), or a raw_decode loop where --slurp is missing; any non-zero gh exit is a failed read whatever stdout holds. fakegh emits concatenated pages and can fail mid-stream; both are tested.
- C43: HLT-1 determinism holds for a fixed tracker snapshot and is tested against fakegh; check-time is left out of the determinism comparison and is INFO unless the full default group set ran. ghcache fetches open issues (paginated) for issue-milestone, health-labelled issues of all states for findings and finding-age, and one cached `gh issue view N` per referenced number for refs, never the whole history.
- C44: ctx carries a monotonic run deadline (the check-time budget); every gh and subprocess call gets min(its timeout, the time left); when it runs out, the remaining gh-backed rules are UNREAD "deadline reached".
- C45: two issues that resolve to one migrated key keep the lowest number, and preview lists the rest as `DUPLICATE #N -> #M`, closed only by file. A requirements:R:proof issue closing while tests:R:seen-red opens when R leaves draft is the intended transition, tested through draft, runnable and proven. A marker-only change (adding evidence=) is listed as MIGRATE, and body comparison ignores the evidence token so issues do not churn.
- C46: evidence `file:line` must be a tracked repo-relative path (in git ls-files) with the line inside the file; review findings from another repo (C36 repo field) are refused. Every issue body and comment is sanitized before writing: fields capped (300 characters), @mentions, URLs and HTML comments stripped so no `loop-health` marker can be forged, token-like strings removed (C40). idle-sessions rows name no session path.
- C47: gather returns a status per canonical rule id (ran-pass, ran-fail, unread, skipped, not-run) next to the rows; report.complete and file.plan read it instead of inferring from missing rows; a failed regression.py sync marks every sync-fed rule in requirements and tests UNREAD; hygiene_rows' output is mapped to rule ids by the adapter (test-time to performance). Tests: failed sync, partial output and a skipped rule each close nothing and print no PASS.
- C48: not-enforced-7d and skipped read the tracked .loop/regression-runs.tsv (id, status, date): not-enforced-7d FAILs when no row of a requirement is PASS there; skipped WARNs on a SKIPPED row whose date is 7 or more days old; nightly reads the nightly lane record's time. The implementer confirms what the date column records and states it in the rule's contract. With regression-runs.tsv tracked, not-enforced-7d needs no local state, which replaces C2's INFO note.
- C49: row-requirement resolves a row's goal by type: a requirement id (must be defined on a page), `slug:N` (the goal file must have done line N), a defect reference, or `-` (explicitly unbound, INFO); it FAILs only on an unresolvable reference. Passing controls cover each valid form.
- C50: file orders each issue's acts (create, label, link) and stops an issue's later acts after a failure; triage adds `health:closed` first, then the comment, then closes; an unknown outcome is reconciled by marker on the next run. "Rerun is safe" in C40 means sequential runs. Tests: failure after server-side success, and a failure between triage's label and close.
- C51: every prerequisite read finishes before any write: milestones paginated with a return-code check (milestone.held reads one page today), covering issues' comments paginated; an incomplete read is the C31 refusal.
- C52: one longest-prefix helper in milestone.py serves goal_feature and feature_of; routing per subject type: docs findings by page name, proof and seen-red rows through the row's goal (requirement page or goal Touches), cost findings through the goal slug's Touches; ties go to the longest path, then Backlog. file sets a milestone only when opening, or when the issue is still on Backlog; it never moves an issue the owner placed.
- C53: the regenerated health workflow gives the check step GH_TOKEN, records the check's exit code in the summary instead of swallowing it, extracts review output by its new heading, and builds the skipped-groups sentence from groups.py; test-automation.sh asserts those lines. This lands with C2's health.yml half, on the owner's word.
- C54: LINK matches only qualified tokens (a path containing `/`, a prefixed requirement id such as HLT-3, a full row id) on the feature's milestone; a short id inside prose never links (negative test). Provisional pending taste d2.
- C55: each new module gets an expected size before building; triage and review keep their argparse in their own modules and health.py only dispatches; a fourth rules module is allowed when one passes 18 KB.
- C56: `preview` and `file --group criteria` print the expanded groups on stderr; a test shows `file --group criteria` acts on the same issues it did before, plus migrated keys.
- C57: callers that test exit code 1 for refusals (automation.py's workflow template, the loop scripts) are searched and updated with C34.
- C59: tests added: a page-two pull request dropped; `triage --older` at the day boundary with the pinned clock; `review --json` without a judge prints valid schema 1; a rerun after FAILED[milestone] creates it once; Mine does not run during file.
- C60: a build-time check confirms each C18 rule has its Rule contracts entry in the design; a rule without one is reported and not built.
<!-- /autoplan-accepted:eng -->

### /autoplan Review Complete

#### URGENT, outside this plan

None.

#### Plan Summary
The plan rebuilds health into twelve angled groups (23 new rules, each with a control), routes findings to feature
milestones with migration of existing issues, adds an evidence-checked review and a triage command, and fixes issues
118, 124, 158 and 159. Reviews added 60 amendments (C1-C60), mostly on issue identity, closure safety, gh reads and
error contracts; both outside and native voices recommend splitting the goal, which waits on the owner.

#### Decisions Made: 39 total (31 auto-decided, 6 taste choices, 1 user challenge, 1 plan approval pending)
Auto-decided: see the Decision Audit Trail; the rest are the gate items below.

#### Review Scores
- CEO: SELECTIVE EXPANSION; 17 cherry-picks accepted, 2 deferred; Codex completed, Claude subagent completed; consensus 6/6 confirmed concerns.
- Design: skipped (no UI scope).
- DX: 5/10 -> 7/10, TTHW under 1 min (check) / about 5 min (review with judge); Codex completed, Claude subagent completed; consensus 5/6 confirmed, 1 disagreement resolved.
- Eng: scope accepted as-is; 24 test gaps planned; 0 critical gaps after amendments; Codex completed, Claude subagent completed; consensus 5/6 confirmed, 1 disagreement in degree.
- CYCLE: actual 30m (estimate 14m) | ceo 15m (outside 4m) | dx 7m (outside 3m) | eng 8m (outside 4m)

#### Cross-Phase Themes
- Scope too big for one goal: CEO (both voices) and DX/Eng Codex ("revise and split") -> uc1.
- gh read failures must never look like success or close issues: CEO X5, DX N1/X3, Eng H2/X8 -> C22, C31, C42, C47, C51, d4.
- Filed-issue identity across the rename and over time: CEO F3, Eng H1/H4/X4 -> C1, C41, C45.
- Text from the model or repo reaching GitHub: CEO X3, Eng H5/X5 -> C25, C46.

#### Deferred (no TODOS.md in this repo; for the owner)
- Health trend per release (C8); triage summary in the Automation digest (C9); per-rule signal metric (CEO F1); judge eval set (CEO X3); per-finding allowlist (DX N8); `--summary` view; shared subprocess deadline beyond C44; concurrent `file` runs.

#### Final gate (pending the owner; nothing approved)
- uc1 (approval) Split or re-scope the goal. Default if approved: b (split into goal A: groups, migration, fixes, deterministic rules; goal B: review, triage, HLT-7..9, first inspection, health.yml). Your direction (a, one goal) stands until you answer.
- d1 (auto, default a) Closed findings stay closed until the evidence hash changes; b: 90-day expiry.
- d2 (auto, default a) LINK on qualified tokens only (C54).
- d3 (auto, default a) private findings filed with file:line and pattern name only; b: report-only.
- d4 (auto, default a) A failing gh read in check is UNREAD; gh absent stays INFO.
- d5 (auto, default a) skipped and not-enforced-7d read .loop/regression-runs.tsv.
- d6 (auto, default a) Regenerate .github/workflows/health.yml in this goal (outside Touches).
- p1 (approval) Plan approval: a approve as-is (recommended), b with overrides, c interrogate, d revise, e reject. Pending.
Reply grammar: `rec`, `rec except <tokens>`, or tokens such as `uc1a d2b p1a` (gate_rev=1).

#### Implementation Tasks (aggregated across phases)
- [ ] **T2 (P1, human: ~3h / CC: ~15min) — file.py** — Close an issue only on its own rule's PASS (C22)
  - Surfaced by: ceo-review — Codex X5: INFO can masquerade as resolution
  - Files: skills/workflow-health/scripts/file.py
- [ ] **T1 (P1, human: ~4h / CC: ~20min) — file.py** — Migrate filed-issue markers across the group rename (C1, C21)
  - Surfaced by: ceo-review — CEO P-4/P-8: key_of keys on group
  - Files: skills/workflow-health/scripts/file.py
- [ ] **T4 (P1, human: ~2h / CC: ~10min) — file.py** — Per-rule evidence input table; stable hash tests (C41)
  - Surfaced by: eng-review — native H1
  - Files: skills/workflow-health/scripts/file.py
- [ ] **T3 (P1, human: ~2h / CC: ~10min) — ghcache** — gh api --paginate --slurp, scoped fetches, run deadline (C42-C44)
  - Surfaced by: eng-review — native H2/H3, Codex X7
  - Files: skills/workflow-health/scripts/ghcache.py
- [ ] **T1 (P1, human: ~4h / CC: ~20min) — groups.py** — Per-rule status set feeds report.complete and file.plan (C47)
  - Surfaced by: eng-review — report.py:40 synthesizes PASS
  - Files: skills/workflow-health/scripts/groups.py, skills/workflow-health/scripts/report.py, skills/workflow-health/scripts/file.py
- [ ] **T2 (P1, human: ~2h / CC: ~10min) — rules_trace.py** — Typed goal resolver for row-requirement (C49)
  - Surfaced by: eng-review — regression.py:184 slug:N goals
  - Files: skills/workflow-health/scripts/rules_trace.py
- [ ] **T1 (P1, human: ~2h / CC: ~10min) — file.py** — File never edits tracked pages; preview never runs Mine (C29, C30)
  - Surfaced by: devex-review — Codex DX X5: milestone.ensure calls link_page; plan_for gathers all groups
  - Files: skills/workflow-health/scripts/file.py, skills/workflow-health/scripts/milestone.py, skills/workflow-health/scripts/health.py
- [ ] **T2 (P1, human: ~2h / CC: ~10min) — ghcache** — Writers fail closed on any gh read failure (C31)
  - Surfaced by: devex-review — native DX N1: partial list files duplicates
  - Files: skills/workflow-health/scripts/ghcache.py
- [ ] **T3 (P2, human: ~1h / CC: ~5min) — automation.py** — Regroup automation GROUPS; regenerate health.yml on the owner's word (C2)
  - Surfaced by: ceo-review — P-5: automation.py:30 hardcodes criteria
  - Files: skills/workflow-health/scripts/automation.py, .github/workflows/health.yml
- [ ] **T5 (P2, human: ~30min / CC: ~5min) — regression** — Rewrite the red cost-unread-tokens row for 124 (C7)
  - Surfaced by: ceo-review — P-7: regression.tsv:113
  - Files: .loop/regression.tsv
- [ ] **T4 (P2, human: ~1h / CC: ~5min) — triage.py** — Bulk close cap 20 with --max (C23)
  - Surfaced by: ceo-review — native CEO: bulk close cap
  - Files: skills/workflow-health/scripts/triage.py
- [ ] **T6 (P2, human: ~2h / CC: ~10min) — feature.py** — Longest-prefix helper and per-subject routing (C52)
  - Surfaced by: eng-review — milestone.py:138 first match
  - Files: skills/workflow-health/scripts/feature.py, skills/workflow-health/scripts/milestone.py
- [ ] **T5 (P2, human: ~3h / CC: ~15min) — file.py** — Write ordering, sanitizing, complete prerequisite reads (C46, C50, C51)
  - Surfaced by: eng-review — Codex X6/X8, native H5
  - Files: skills/workflow-health/scripts/file.py, skills/workflow-health/scripts/triage.py, skills/workflow-health/scripts/milestone.py
- [ ] **T7 (P2, human: ~1h / CC: ~5min) — rules_fresh.py** — Temporal rules read regression-runs.tsv (C48)
  - Surfaced by: eng-review — Codex X2
  - Files: skills/workflow-health/scripts/rules_fresh.py
- [ ] **T3 (P2, human: ~3h / CC: ~15min) — cli** — REFUSED[code]/FAILED[code] with exit 2; codes table in commands.md (C34)
  - Surfaced by: devex-review — both DX voices: no stable codes, mixed exit codes
  - Files: skills/workflow-health/scripts/health.py, skills/workflow-health/references/commands.md
- [ ] **T5 (P2, human: ~2h / CC: ~10min) — docs** — Quickstart, copy-paste flows, adding-a-rule guide (C38)
  - Surfaced by: devex-review — Codex DX X1/X8
  - Files: skills/workflow-health/references/commands.md, skills/workflow-health/SKILL.md
- [ ] **T4 (P2, human: ~2h / CC: ~10min) — review.py** — Versioned review --json envelope bound to repo and HEAD (C36)
  - Surfaced by: devex-review — Codex DX X4/X10
  - Files: skills/workflow-health/scripts/review.py

<!-- AUTONOMOUS DECISION LOG -->
## Decision Audit Trail

| # | Phase | Decision | Classification | Principle | Rationale | Rejected |
|---|-------|----------|----------------|-----------|-----------|----------|
| 1 | Preamble | Skip the offered skill-suite upgrade (1.92 to 1.98) | Mechanical | P6 | an unattended plan step must not change installed tooling mid-run | upgrading now |
| 2 | CEO 0E | Mode SELECTIVE EXPANSION | Mechanical | override | autoplan sets it; 0E's own count (about 30 files) would say REDUCTION | SCOPE REDUCTION |
| 3 | CEO 0G | Accept C1-C7 | Mechanical | P1, P2 | in blast radius, each under a day; C1/C3/C7 fix real breakage | defer |
| 4 | CEO 0G | Defer C8 trend, C9 digest | Mechanical | P3 | outside the PRD or another feature | add |
| 5 | CEO 0H | Accept spec round-1 fixes (C10-C14) | Mechanical | P1 | reviewer-cited gaps with code receipts | keep text |
| 6 | CEO 0H | Accept spec round-2 fixes (C15-C17) | Mechanical | P1, P5 | file.py would refuse new slugs; one signature | keep text |
| 7 | CEO 0H | Accept spec round-3 fixes (C18-C20), stop at the cap | Mechanical | P1 | three-launch cap; 6 of 6 applied | a fourth review |
| 8 | CEO 0H | Approve the scope documents (A) | Mechanical | P6 | unattended; documents carry the exact decisions | revise |
| 9 | CEO C2 | health.yml regeneration waits for the owner | Taste | P5 | outside the goal's Touches list | regenerate now |
| 10 | CEO voices | Proof split by row state, migration preview (C1, C21) | Mechanical | P5 | prose routing is brittle (F3) | issue body text |
| 11 | CEO voices | Per-rule closure on PASS only (C22) | Mechanical | P1 | INFO must not close an issue (X5) | per-group closure |
| 12 | CEO voices | Bulk close cap 20 (C23) | Mechanical | P1 | a wrong filter cannot close a milestone | no cap |
| 13 | CEO voices | workflow-permissions flags write-all (C24) | Mechanical | P1 | a declaration alone proves nothing (X7) | declaration only |
| 14 | CEO voices | Label model findings in issues (C25) | Mechanical | P5 | owner weighs model output (X3) | unlabelled |
| 15 | CEO voices | Angle presence tests, size after change (C26) | Mechanical | P5 | copy changes must not break tests (F8, F4) | exact text |
| 16 | CEO voices | Keep exactly-twelve assert | Mechanical | PRD | HLT-2 names twelve (F2) | count-free assert |
| 17 | CEO voices | No external scanner wrappers | Mechanical | P4 | none installed (F9) | wrap gitleaks/zizmor |
| 18 | CEO voices | Split or re-scope the goal | User Challenge | both models | see gate uc1 | - |
| 19 | CEO voices | Evidence hash vs dismissal expiry | Taste | P5 | design chose stability (R2-6); Codex X4 | expiry |
| 20 | CEO voices | LINK match scope | Taste | P5 | path tokens over-match (X6) | path match |
| 21 | CEO S3 | private findings filed vs report-only | Taste | P1 | design files file:line and name only | report-only |
| 22 | CEO S2/S4 | gh act failures reported, review re-verified at filing (C27, C28) | Mechanical | P1 | silent partial writes; stale saved review | leave as is |
| 23 | DX | Mode DX POLISH, persona solo owner via agent, targets Champion/Competitive | Mechanical | override, P6, P5 | autoplan override; README audience | DX EXPANSION |
| 24 | DX | Accept C29-C40 (side effects, fail-closed gh, selectors, codes, JSON envelope, docs, deprecation) | Mechanical | P1, P5 | both voices; in blast radius | leave as is |
| 25 | DX | Defer per-finding allowlist, --summary, shared deadline | Mechanical | P3 | new surface outside DX POLISH | build now |
| 26 | DX | Failing gh read in check: UNREAD vs INFO | Taste | P1 vs design | both voices say failing is not absent; design says INFO | keep INFO |
| 27 | Eng | Structure: original arrangement (8 modules) | Mechanical | P5 | folding into file.py breaks the 20 KB rule | smaller arrangement |
| 28 | Eng | Accept C41-C60 (result contract, typed goals, pagination, evidence table, write order, routing, workflow, sanitizing) | Mechanical | P1, P5 | code receipts in both voices | leave as is |
| 29 | Eng | Concurrent file runs not handled | Mechanical | P3 | one scheduled job; owner runs file by hand | a lock |
| 30 | Eng | No TODOS.md written; deferrals listed for the owner | Mechanical | P5 | repo has no TODOS.md and the step may not add repo files | create TODOS.md |
| 31 | Eng | skipped/not-enforced-7d read regression-runs.tsv | Taste | P5 | tracked source exists; date semantics to confirm (d5) | lane records |
