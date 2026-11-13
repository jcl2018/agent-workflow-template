# Plan: skill-governs-line

Claims checked against the code: dev/toy/test-batch.sh:75 (loop over three files) greps `governance only` and
`runs neither|never runs`; dev/toy/test-defect.sh:238 (case skill-kept) greps `governance only` in
skills/workflow-delivery/SKILL.md; that SKILL.md line 19 reads "One session governs, and the others build" and line 20
"never runs `go`"; skills/workflow-monitoring/SKILL.md:90 and references/operation.md:4 still say "governance only".
test-batch.sh:80 greps the Tests list as " — [id](", but docs/wiki/Monitoring.md now lists "| [id](Tests#t-id) |".
Rows: skill-says-governs (.loop/regression.tsv:15), skill-kept (:173). Both toys run under bash only, so they skip on
native Windows.

## Build steps
1. test-batch.sh:75: `grep -qiE "governance only|one session governs"` and keep `runs neither|never runs`. The check's
   name is unchanged, because the row greps its PASS text.
2. test-defect.sh:238: `grep -qiE "governance only|one session governs"`.
3. test-batch.sh:80: match the table row `| [$id](Tests#t-$id) |`.
4. Proof: under a Linux shim both toys pass, then fail when the governance lines are deleted from the delivery SKILL.md
   (first `One session governs`, then both it and `never runs`). The rows already carry seen-red dates; their proof on
   the real platform is owed off-platform (bash rows), so they are listed as PENDING off-platform proofs.

## What could break
A looser alternation passing on something that is not the line: the second half (`runs neither|never runs`) is kept,
and the first phrase is specific to this line. The two Tests-list checks must still fail when the id is missing.

## Out of scope
Rewording SKILL.md; the other rows; the 150-line cap.

PENDING: the Mac proof of skill-says-governs and skill-kept (bash rows, skipped on native Windows)
