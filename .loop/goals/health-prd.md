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
