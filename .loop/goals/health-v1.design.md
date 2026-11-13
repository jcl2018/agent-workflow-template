# health-v1 design

Problem: the health Runbook still describes a GitHub Actions workflow that was removed; triage can only close a whole kind; review findings may cite a bare requirement id; open review issues are never closed when a finding disappears; an over-time suite does not warn.

Approaches: (1) small targeted changes in the health scripts and page, each with a Python toy that runs on any platform; (2) rework triage and the review into one new command. Chosen: 1, lower risk and reviewable.

Done lines: triage --issue N closes only that issue (toy); a review finding without a file:line or row citation is dropped (toy); the unrun-rows WARN waits on suite-shard merging, then reads the new suite-times.tsv column in cost.py and lean.py with a toy.

Open questions: none for the owner except the requirement wording in DECISIONS.md, which needs the owner's un-review first.
