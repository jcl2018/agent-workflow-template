# One operation session governs every repo in the pod, with exactly two layers (operation and workers) and no per-repo operation session, and every check-in's dependency map is grouped by repo with each repo's name as a clear header (owner, 2026-11-11: "Add when the operation that I should only get one operation session for the entire pod. So it can manage. There's no operation plus operation session in the monitoring and the worker session. They're just two layers. And also for the printout, when operation session should print out all the should show the dependency map. It should show by groups first group by the reponents. Right now it's not showing the reponents very cleanly.")

- Slug: single-operation
- Touches: skills/workflow-monitoring, dev/toy, .loop/regression.tsv, docs/wiki/Monitoring.md, docs/wiki/Tests.md

## Done lines

Frozen. A wrong done line needs a new goal.

1. Monitoring gains MON-13 "One operation session for the whole pod: it governs every registered repo directly and talks to each worker; there are only two layers, operation and workers; no repo gets its own operation session" and MON-14 "The check-in dependency map is grouped by repo first: one block per repo, headed by the repo's name, goals and their dependencies inside it, cross-repo dependencies drawn between blocks", both marked Reviewed with the owner's quote
2. Starting a second operation session for a repo the pod already governs is refused with a line naming the existing operation session, and a regression row sees it fail before the fix and pass after
3. The check-in printout (board_status/checkin/graph) renders the dependency map as per-repo blocks with the repo name as the header, within 60 characters wide, and a test renders a three-repo fixture and checks the grouping
4. every script stays under 18 KB and the package at 99 files or fewer

## Verify by hand

<!-- Numbered steps for a person, each with an Expect: line. A release needs this. -->
