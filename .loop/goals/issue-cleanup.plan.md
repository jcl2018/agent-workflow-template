# Plan: issue-cleanup

Goal file: .loop/goals/issue-cleanup.md (done lines frozen). Design: .loop/goals/issue-cleanup.design.md (Premises 1-7 are the rules
this plan implements).

## Implementation plan

### Context

The template repository has 820 open issues; 98 have no `regression` label (health findings, enhancements, goal bugs). The 722
defect+regression issues belong to regression-green-2. This goal reads each of the 98 against current `origin/main`, closes the
ones that are fixed, stale or duplicate with a one-line reason and evidence, and turns the rest into finding lines. It writes only
`.loop/findings.md` (plus this goal's design and plan files) in git; the closes go through `gh`.

### Changes

1. Snapshot: list the open non-regression issues with `gh issue list` (number, title, labels, body) into a local file outside git, and
   record the highest number covered (issues filed later are out of scope).
2. Triage in four groups, each by a reviewer subagent reading `origin/main` and writing a verdict table (issue, verdict, evidence):
   (a) size findings (re-run the size check, compare the files named); (b) requirement, criteria, docs, consistency and hygiene
   findings (re-run `workflow-health check` and the page checks); (c) review findings (read the code each names); (d) bugs,
   enhancements, goals and the rest (read the code and the commits since the issue was filed).
3. The worker re-checks every verdict itself before it counts: re-runs the named check or reads the cited code and commit; a verdict
   it cannot confirm becomes `needs-code`, never a close.
4. Folding: a duplicate group keeps its oldest open issue; the others close as duplicates naming it, and the kept one gets one comment
   listing what was folded in.
5. Closing: a small script (kept outside git) reads the verified table and, one issue at a time, prints the line then runs
   `gh issue close N --reason <completed|not planned> --comment "<reason; evidence>"`, stops at the first error and writes what it
   closed to a log; nothing is deleted or edited but state and one comment.
6. `.loop/findings.md`: one line per real piece of work, `- <slug>: <what to build> (issues #N, #M)`, folding issues that need the same
   change, skipping any already covered by a goal in the queue or an existing finding (the line then cites that goal or finding in
   the table instead).
7. The pull request body carries the table of every issue (number, verdict, reason, evidence, goal line), with no private name or
   path.

### Tests

The checks are the evidence: each close names a commit, a PR or a check output a reader can re-run. After the run, a final
`gh issue list` shows no open non-regression issue that is fixed, stale or a duplicate; every remaining one is named in
`.loop/findings.md` or a queued goal; the 722 regression issues are unchanged (count compared before and after).

### Not in scope

The 722 defect+regression issues; any code change; labels, milestones, deletion.
