# package-headroom plan

Checked against the code: every function named below exists where it is listed.

## Build steps
1. rules.py: move the f_* control fixtures into controls.py (CONTROLS entries added there) and move no_fit and prompt_pointer in from report.py.
2. lane.py: move alive (as proctree.alive_since), tmp_for and rm_tmp into proctree.py; lane.py re-exports `alive`, `tmp_for`, `rm_tmp` so role.py and test-lane-tmpdir.sh keep working; trim comments.
3. goal.py: move TEMPLATE, FLOW, NO_FLOW and flow_set into proctree.py (re-imported by name); one `ME` for `sys.modules[__name__]`; shared `ok`/`auto` conditions in cmd_record.
4. actions.py: move the "Check the routine" step into slots.py as ROUTINE_STEP, substituted by `@ROUTINE@`; the rendered workflow is byte-identical.
5. Fold design-guide.md into loop-files.md; update.py, dev/package.py, test-package.sh, test-adopt.sh and test-stale-groups.sh name loop-files.md.

## Test
Regression row package-headroom-held runs dev/toy/test-package-headroom.py: the five scripts at 19,000 bytes or less and at most 98 files. Seen red against origin/main's rules.py.

## Could break
An import that named a moved function (checked: role, health controls, test-automation-routines), the generated workflow text (compared before and after), the packaged shared files.

## Out of scope
The other 22 scripts over 19,000 bytes; a 97-file package.
