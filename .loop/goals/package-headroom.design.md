# package-headroom design

Problem: rules.py, lane.py, goal.py, actions.py and report.py sit within 1 KB of the 20,480-byte script cap, and the package holds 99 files against a cap of 99, so the next goal that adds a line or a file breaks `dev/package.py`.

## Approaches
1. Trim prose only. Cheap, but lane.py and goal.py were already trimmed once and have too little prose left to reach 19,000.
2. Fold and trim: move code and constants to a sibling that has room (fixtures to controls.py, process and temp helpers and shared constants to proctree.py, a workflow step to slots.py, report's adoption rules to rules.py), fold design-guide.md into loop-files.md, and cut comments. Moves keep every name importable from where it was. Chosen: no behaviour change, no new file.

## Done line
- dev/package.py passes: five scripts at 19,000 bytes or less (rules 18,117, lane 18,837, goal 18,878, actions 18,815, report 16,240) and 98 files.
- A toy asserts the five sizes and the file cap.

## Open questions
None. A second reference doc did not fold as cleanly, so 98 files is the target.
