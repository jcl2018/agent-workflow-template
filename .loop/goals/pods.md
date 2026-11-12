# Inside a pod there are exactly two layers, one operation session and its workers; several pods (for example Claude Code and Codex) may run at once without messaging each other, coordinating only through shared on-disk state: each goal records the pod that owns it, only the owner acts on it, and one merge into a repo's main happens at a time across pods; the check-in dependency map is grouped by repo (owner, 2026-11-11: "Add when the operation that I should only get one operation session for the entire pod ... They're just two layers ... It should show by groups first group by the reponents." / "you should expect it that I have multiple monitoring sessions ... they don't need to know each other." / "yes add now", approving goal ownership and a cross-pod merge lock)

- Slug: pods
- Touches: skills/workflow-monitoring, skills/workflow-release, skills/workflow-delivery/scripts/goal.py, dev/toy, .loop/regression.tsv, docs/wiki/Monitoring.md, docs/wiki/Release.md, docs/wiki/Tests.md, docs/wiki/Delivery.md

## Done lines

Frozen. A wrong done line needs a new goal.

1. Monitoring gains MON-13 "Two layers per pod: one operation session governs every repo in its pod directly and talks to each worker, with no per-repo operation session; several pods may run concurrently and independently", MON-14 "The check-in dependency map is grouped by repo first: one block per repo headed by the repo's name, cross-repo dependencies drawn between blocks", and MON-15 "Pods coordinate through shared state, not messages: every goal records its owning pod and only that pod starts, answers, merges or resumes it; other pods show it read-only as owned by that pod; merges into one repo's main are serialized across pods by a short lock", all Reviewed with the owner's quotes
2. A goal's run record carries its owning pod id; goal.py, sessions.py and merge.py refuse to act on another pod's goal with one line naming the owner, and the board marks such goals "owned by <pod>"; tests prove both
3. merge.py takes a per-repo merge lock (released on exit, stale-lock safe) so two pods never merge into the same main at once; a test runs two merges concurrently and shows them serialized
4. Nothing refuses a second independent operation session on the same machine or repo; a two-pod fixture test shows both working without collision
5. The check-in printout renders the dependency map as per-repo blocks with repo headers, within 60 characters, tested on a three-repo fixture
6. every script stays under 18 KB and the package at 99 files or fewer

## Verify by hand

<!-- Numbered steps for a person, each with an Expect: line. A release needs this. -->
1. In one repo run `CLAUDE_SESSION_ID=pod-a python3 skills/workflow-monitoring/scripts/operate.py claim`, then the same with `pod-b`. Expect: both print `CLAIMED operation session` with no REFUSED, WARN or `replaced`; `cat .git/loop/operation.id` lists pod-a and pod-b.
2. Queue a goal as pod-a (`LOOP_POD_ID=pod-a python3 skills/workflow-monitoring/scripts/watch.py watch --once`), then `cat .git/loop/runs/<slug>.json`. Expect: `"pod": "pod-a"`.
3. As pod-b run `LOOP_POD_ID=pod-b python3 skills/workflow-monitoring/scripts/operate.py send <slug> hi`. Expect: exactly one line `REFUSED: goal <slug> is owned by pod pod-a. Fix: ...`, exit status 2, the record unchanged.
4. Run `python3 skills/workflow-monitoring/scripts/checkin.py` as pod-b. Expect: the goal reads `owned by pod-a` and no question for it is numbered under Needs you; as pod-a it has no such words.
5. In two shells run `python3 skills/workflow-release/scripts/merge.py <slug>` for two goals of one auto_merge repo at once. Expect: the second prints `WAITING: another pod is merging into this repo` and starts only after the first ends; `.git/loop/merge.lock` is gone afterwards.
6. Write a dead pid into `.git/loop/merge.lock` (`echo 999999 > ...`) and run a merge. Expect: it takes the lock at once (no WAITING).
7. Run `python3 skills/workflow-monitoring/scripts/checkin.py` with two followed repos in `~/.workflow-loop/repos`. Expect: one `== name ==` block per repo, no line over 60 characters, `Between repos` for a `repo/slug` dependency, the legend once.
