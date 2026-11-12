# Implement the owner-approved Health PRD: twelve rule groups each with its angle, a repo reviewer that files findings per feature on its milestone, triage, and the first full inspection of this repo (owner, 2026-11-10: "I want to approve 1, 2, 3")

- Slug: health-prd
- Touches: skills/workflow-health, skills/workflow-regression, docs/wiki/Health.md, .loop/config.json, .loop/regression.tsv, dev/toy, .github/workflows/health.yml, skills/workflow-monitoring/scripts/worker.py

## Done lines

Frozen. A wrong done line needs a new goal.

1. HLT-2: check runs exactly the twelve groups (Requirements, Traceability, Consistency, Docs, Freshness, Tests, Performance, Security and privacy, Size, Hygiene, Adoption, Controls) plus Mine, each printing its angle, each rule with a negative control
2. HLT-4: preview and file put each finding on the milestone of the feature it is about (Backlog only when none fits), tagged with its group or kind; a repeat updates, a fix closes, a return reopens, and an open issue that already covers a finding is linked, not duplicated
3. HLT-5 and HLT-9: review reads every PRD page, the README, milestones, open issues, tests and code per feature and reports conflicts, gaps, drift, weak tests and savings, each naming its feature, angle and evidence; a finding without evidence is dropped; review writes nothing
4. HLT-8: triage shows open findings per feature by kind, age and count; closing a batch records the owner's words and the review does not refile them unless the evidence changes
5. HLT-6 (merged in from health-hygiene): every rule has a negative control, a slow land run names its slowest rows, and stale local worktrees and branches are flagged with the commands to remove them
6. HLT-1 and HLT-7: two checks on an unchanged repo print the same lines, check changes nothing, and check without controls finishes in under 60 seconds
7. First inspection, after docs-format has merged: review and check run on this repo, the owner sees the preview, and on the owner's word every finding is filed on its feature milestone with evidence and no duplicates
8. Each of HLT-1..HLT-9 has a regression row seen failing then passing, listed in the Health Tests table
9. Issues 118, 124, 158 and 159 are fixed, each with a defect row seen failing then passing (owner-approved issue mapping 2026-11-10)

## Verify by hand

<!-- Numbered steps for a person, each with an Expect: line. A release needs this. -->

1. Run `python3 skills/workflow-health/scripts/health.py check --skip controls` in this repo.
   Expect: twelve group headings, each with its angle, then Mine and one `HEALTH:` line, in under a minute, and no file changes (`git status` stays clean).
2. Run `python3 skills/workflow-health/scripts/health.py preview`.
   Expect: only `WOULD` or `SAME` lines and a `PREVIEW: N to write, nothing written` line.
3. Run `python3 skills/workflow-health/scripts/health.py triage`.
   Expect: the open health issues per feature with kind, count and age, and nothing written.
4. Run `python3 skills/workflow-health/scripts/health.py review` from a Claude session.
   Expect: a `judge: session` line, then a `JUDGE UNAVAILABLE` line naming a prompt file for an in-session subagent (with no session, as in the scheduled run, it says `judge: claude -p (no session)`).

Closes #124
Closes #158
Closes #159

## Notes for the reviewer

- Issue 118 is met by docs-format's fix on main (its `enforce.py` rule and defect rows `health-not-enforced-*` and `health-unreviewed-warn-issue-118`), so this goal adds no second rule; done line 9 counts it from there.
- First inspection (done line 7), run on the owner's answer "c" (Everything) to "which groups to file": 79 issues opened (#322 to #400), 1 linked, 4 updated, 2 closed, each on its feature's milestone and none duplicated.
- Judge rule, in the owner's words: "wanto to reconsitder it should use session first and then claud -p later". The judge and the review run in a session first and use `claude -p` only with no session; each report logs `judge: session` or `judge: claude -p (no session)`. The review then ran in a session: 1 shallow issue kept and updated (#358), 42 closed as not confirmed (#359 to #400), 14 new (#401 to #414), 3 linked (#129, #181, #268).
- The package allows at most 99 files, and main was at 99, so the new modules are folded into existing ones (one new `rules.py`, `references/milestones.md` folded into `commands.md`): the package builds with exactly 99 files and every script this goal changed stays under 18 KB.
- The Automation, Documentation, Health and Regression pages show STALE against this branch's commits and have sealed Reviewed text, so they need the owner's re-review; the Tests tables are current.
- The qa lane ran 82 of 463 selected rows in its 15-minute budget (all passed); the other 381 run in the scheduled full suite.
