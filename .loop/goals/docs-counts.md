# Fix issue 39: catch numbers in the docs that drift from the code

- Slug: docs-counts
- Touches: skills/workflow-docs, docs/wiki, README.md, skills/design-guide.md, dev/toy

## Done lines

Frozen. A wrong done line needs a new goal.

1. The docs check compares every count it can verify (number of skills, feature pages, criteria per page, tests per feature) with the code and fails on a mismatch, naming the file, the stated number and the real one
2. Every such count in the README, wiki and design guide is correct now
3. A toy test where a page says the wrong number of skills proves the check fails, and issue 39 closes when this merges

## Verify by hand

<!-- One or more numbered steps a person can follow, each with an Expect: line. Every release needs this. -->

1. Run `python3 skills/workflow-docs/scripts/docs.py check` in the repo.
   Expect: `DOCS OK`, because the README and design guide say seven skills and there are seven.
2. Change "the seven skills" to "the eight skills" in `skills/design-guide.md` and run the check again.
   Expect: `COUNT skills/design-guide.md: says eight skills, the repo has 7`, and exit code 1. Undo the change.
