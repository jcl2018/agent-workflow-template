# Design: final-criteria

Status: shaped by office-hours with the recommended answer at every question. Nothing approved, merged or pushed.

## Problem

The wiki criteria drifted from what the owner approved. The owner's final set is 6 features x 5 criteria = 30,
in `~/projects/agent-workflow-template/.local/criteria-review.md` (outside the repo, gitignored via `.local/`,
never committed, never quoted into a commit message or PR body beyond the criterion lines themselves).
The goal's done lines are frozen; this design meets them.

## Approach (recommended, taken)

One mechanical rewrite, in this order, so each step can be checked on its own:

1. **Cap.** `MAX_CRITERIA = 5` in `skills/workflow-docs/scripts/criteria.py`; fix any text that says six (docstring, skill doc, README, tests in `dev/toy/test-criteria.sh`).
2. **Pages.** Under `docs/wiki/`: add `Setup.md`; rewrite `Delivery`, `Monitoring`, `Documentation`, `Regression`, `Health` Criteria sections; delete `Release.md` and `Milestones.md`; update `Home.md` (page table loses Release and Milestones, gains Setup). Each page keeps Summary, Criteria, Tests and nothing else.
3. **Wording.** Copy each criterion line from the file verbatim (the text after the id), as `- ID: **Unreviewed** text`. Do not trim, fix typos or reflow. The "Small fixes asked about" and "Gaps:" lines in the file are not criteria and stay out of the pages (they are follow-up work, see below).
4. **Folding.** The removed pages' content moves "as the file says": Release into DEL-5 (already in its wording), Milestones into DOC-5 (milestones) and HLT-4 (Backlog issues). Their Summary prose moves to the Delivery, Documentation and Health Summary sections; only facts that are still true.
5. **Docs map.** `.loop/docs.tsv`: drop Release and Milestones rows; add `Setup  skills/workflow-setup,dev/install-local.sh`; trim Home to `README.md,FINDINGS.md,DECISIONS.md`; point Documentation, Health and Delivery at the paths that absorbed the removed pages (milestone script and `dev/toy/fakegh` under Documentation; `workflow-release` skill under Delivery).
6. **Regression map.** Re-point the `goal` column of every row in `.loop/regression.tsv` at exactly one new id (table below). Rows that fit none are listed in the goal's report and left with an empty goal column only if `criteria.py`'s LINK check allows it; otherwise parked on the closest criterion and flagged in the report (see PENDING).
7. **Review.** `criteria.py review --user` over all 30 ids, dated 2026-11-08 (the owner approved each in chat that day; the goal file states this, so `--user` is honest). Then `criteria.py render` rewrites every Tests table; a criterion with no passing row shows "not enforced".
8. **Checks.** `docs.py check`, `criteria.py render --check`, the regression suite and the repo's own checks.

Order matters: wording first, review last, because Reviewed locks the wording by hash.

## Regression row mapping (proposed)

Old ids on the left are the `goal` column today.

| Old goal id | Rows | New criterion |
|---|---|---|
| DEL-5, DEL-6, DEL-8 | frozen-done-lines, starts-at-idea, steps-through-flow, stop-after-3-tries, DEL-1, DEL-2 | DEL-1 (flow runs unattended, 3 tries) or DEL-2 (frozen done lines: frozen-done-lines, DEL-1 row) |
| DEL-7, DEL-9 | auto-approved, DEL-3, DEL-4, never-merges | DEL-3 (auto-approved / Needs you) ; never-merges has no exact fit, see unmapped |
| DEL-10 | DEL-10 | DEL-4 (PR carries done lines/plan/verify), if its test checks the PR body; else unmapped |
| REL-4..REL-9 | REL-1..3, refused-unmet, docs-only, wiki-release | DEL-5 (release automatic); refused-unmet also REG-1 candidate, but one row maps to one criterion, so DEL-5 |
| DOC-4, DOC-5 | DOC-1..3, stale-merge-order | DOC-4 (enforce command, stale refused) |
| DOC-6 | page-shape, criteria-no-scripts | DOC-1 (template) |
| DOC-7 | tests-not-enforced, tests-last-run, tests-table-stale | DOC-1 (Tests table) |
| DOC-8, DOC-9 | review-dated, review-owner-only, reviewed-lock, unreview-lifts | DOC-2 |
| MON-14..19 | board/workers rows | MON-3 (board), MON-4 (printout: waits-first, status-order, needs-you-stuck, estimates-shown, stuck-stays-top), MON-1 (worker-per-goal, worker-refuses, one-way-to-run, MON-4/MON-8 batch rows, MON-1 overlap row), MON-2 (worker-reports) |
| REG-4..REG-8 | REG-1..3, tests-seen-failing, one-issue, one-link | REG-2 (seen failing, one link), REG-5 (known doesn't block, no token, one issue) |
| HLT-*, MIL-* | health and milestone rows | HLT-1 (same lines, no writes), HLT-2 (size, criteria row, docs row, unread), HLT-4 (MIL-* issue and milestone rows, HLT-7*), DOC-5 (MIL-2, milestone placement) |

The implementer builds the final one-to-one table by reading each row's command and picking the criterion whose
words it proves; the table above is the starting guess, not the answer. Likely unmapped (to be listed in the
report, not silently forced): `never-merges`, `one-failure`, `MON-9`, `MON-13` (mender behaviour), `dependencies-on-map`
unless it proves "goals touching the same files never run together" (then MON-1), `HLT-3b`/`MIL-5` duplicates.
Criteria with no proving row (expected: SET-1..5, MON-5, REG-3, REG-4, HLT-3, HLT-5, DOC-3, DEL-4 if DEL-10 is unrelated) show as **not enforced**.
That is the honest result, not a gap to paper over with weak tests.

## Out of scope

- The "Gaps" and "Small fixes" lines in the file (cadence loop, token recording, Mine group, filing, nightly wiki-release failure #58, etc.): follow-up goals, not this one.
- Writing new tests to make criteria enforced (DOC-3 says the loop does that after review; separate goals).
- Changing any done line.

## Risks

- Verbatim copy: do it by script from the file (or a diff check against it) so there is no hand-typing drift. Done line 5 is a diff of criterion text against the file; add that diff to the report.
- `criteria.py`'s SCRIPT check rejects script file names in criteria; the 30 lines contain none (checked: `SKILL.md` is not a script extension).
- Duplicate ids: `seen` is global, so old ids (DEL-5 etc.) must be fully replaced, and every `regression.tsv` goal id re-pointed, or the LINK check fails ("rows link to X, which no page has").
- `.local/criteria-review.md` must not be staged: `.local/` is already in `.gitignore`; run `git status` before commit.
- Links to `Release`/`Milestones` in README.md, Home.md, skill docs (`workflow-release` mentions, README lines 125 and 159) break when pages go; fix or retarget to Delivery.

## Open decisions

None blocking. Every question took the recommended answer.
