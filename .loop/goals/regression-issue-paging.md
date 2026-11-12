# Stop regression issue spam: page through every regression issue instead of the newest 200 (actions.py:133), treat a job-time skip like exit 77 so it opens no issue (actions.py:170-182), fix test-regression.sh:185-186 to expect no issue for a skipped row, then close the duplicate and never-ran issues

- Slug: regression-issue-paging
- Touches: skills/workflow-regression/scripts, dev/toy/test-regression.sh

## Done lines

Frozen. A wrong done line needs a new goal.

1. actions.py reads all regression issues, refusing to file when the list may be cut off
2. a row skipped for job time opens no defect issue, and test-regression.sh proves it including a case with more than 200 existing issues
3. open regression defect issues drop to at most one per failing row

## Verify by hand

<!-- Numbered steps for a person, each with an Expect: line. A release needs this. -->
