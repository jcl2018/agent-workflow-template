# A failing row's regression issue carries the row's last output lines, in CI and on the Mac tick

- Slug: capture-row-output
- Touches: skills/workflow-regression/scripts, dev/toy

## Done lines

Frozen. A wrong done line needs a new goal.

1. A failing row's issue body holds the row's last 40 output lines, never an empty block

## Verify by hand

<!-- Numbered steps for a person, each with an Expect: line. A release needs this. -->

1. Run `python3 dev/toy/test-row-output.py` from the repo root.
   Expect: every line starts with `PASS:`, including `Mac tick: a silent failing row gives an issue body of its last 40 output lines` and `CI: the issue body holds the last 40 output lines of the row`.
2. After the next scheduled regression run, open a regression issue for a row that ends in `| grep -q` (for example `skill-says-governs`, if it is still failing).
   Expect: its output block holds the row's last lines, not an empty block.

