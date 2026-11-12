# Inside a pod there are exactly two layers, one operation session and its workers, with no per-repo operation session; several pods (for example one in Claude Code and one in Codex) may run at the same time without knowing each other; and the check-in dependency map is grouped by repo (owner, 2026-11-11: "Add when the operation that I should only get one operation session for the entire pod. So it can manage. There's no operation plus operation session in the monitoring and the worker session. They're just two layers. And also for the printout ... It should show by groups first group by the reponents." and later: "you should expect it that I have multiple monitoring sessions ... they don't need to know each other. It's just like they can do their own stuff concurrently.")

- Slug: pod-layers
- Touches: skills/workflow-monitoring, dev/toy, .loop/regression.tsv, docs/wiki/Monitoring.md, docs/wiki/Tests.md

## Done lines

Frozen. A wrong done line needs a new goal.

1. Monitoring gains MON-13 "Two layers per pod: one operation session governs every repo in its pod directly and talks to each worker, with no per-repo operation session in between; several pods may run concurrently and independently, each with its own operation session, and none needs to know the others" and MON-14 "The check-in dependency map is grouped by repo first: one block per repo headed by the repo's name, goals and dependencies inside, cross-repo dependencies drawn between blocks", both Reviewed with the owner's quotes
2. Nothing refuses or warns when a second, independent operation session runs on the same machine or repo; a test runs two operation sessions over fixture repos and shows both work
3. The check-in printout renders the dependency map as per-repo blocks with the repo name as header, within 60 characters, tested on a three-repo fixture
4. every script stays under 18 KB and the package at 99 files or fewer

## Verify by hand

<!-- Numbered steps for a person, each with an Expect: line. A release needs this. -->
