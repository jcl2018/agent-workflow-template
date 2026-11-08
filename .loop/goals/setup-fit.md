# Fix the Setup gaps found by adopting three real repos

- Slug: setup-fit
- Touches: skills/workflow-setup, skills/workflow-docs, dev/package.py, dev/toy

## Done lines

Frozen. A wrong done line needs a new goal.

1. Setup finds a repo's real test commands from its CI workflows and scripts, and never sets a check that runs zero tests
2. Setup refuses to finish with a bare agent_command and prints the line to add the allowed tools
3. Setup proposes feature pages from a repo's own features (milestones, tracks, folders with code) instead of every top-level folder, and the docs check accepts the feature list in .loop/docs.tsv instead of a fixed page set
4. Setup follows a repo's existing version and changelog habit, and reports a .gitignore that would block its own files with the exact exception to add
5. The package's leak scan blocks every private prefix the local leak hook blocks, read from a private setting outside the repo
6. A toy test adopts a fake repo with CI tests, a bare agent command, its own feature list and a blocking .gitignore, and proves each line above

## Verify by hand

<!-- One or more numbered steps a person can follow, each with an Expect: line. Every release needs this. -->
