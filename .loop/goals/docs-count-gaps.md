# Fix issues 104, 105, 106 and 107: close the four count-detection gaps in the docs check

- Slug: docs-count-gaps
- Touches: skills/workflow-docs, .loop/regression.tsv, dev/toy

## Done lines

Frozen. A wrong done line needs a new goal.

1. A word or extra space between a number and its noun no longer hides a wrong count (104)
2. Indented code blocks are skipped like fenced ones (105)
3. A page's tests count includes the defect tests its page shows (106)
4. A line naming a criterion id is skipped only on the page that defines it (107)
5. One defect test per issue, each seen failing once and linked to its issue
6. Per DOC-3, each done line above is recorded on its PRD page as one or more Given/When/Then scenarios under the requirement it serves, each linked to its regression row with its last result

## Verify by hand

<!-- Numbered steps for a person, each with an Expect: line. A release needs this. -->
