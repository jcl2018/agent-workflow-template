# Narrow each regression row's file dependencies so a code change reruns only the rows that test it

- Slug: narrow-rows
- Touches: skills/workflow-regression, dev/toy, .loop/regression.tsv

## Done lines

Frozen. A wrong done line needs a new goal.

1. Each toy test script declares the files it actually exercises instead of whole folders, and lanes.py uses those to map changed files to rows
2. A one-file change in one skill reruns only that skill's rows, measured on this repo and shown in the PR
3. A row whose dependencies cannot be worked out still reruns on any change, never skipped
4. A toy test proves a narrow change reruns only its rows and a wide one reruns all
5. Per DOC-3, each done line above is recorded on its PRD page as one or more Given/When/Then scenarios under the requirement it serves, each linked to its regression row with its last result

## Verify by hand

<!-- Numbered steps for a person, each with an Expect: line. A release needs this. -->
