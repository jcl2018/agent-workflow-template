# stale-blocks-all design

Problem: rows review-findings-skill-lines and settings-render-fresh fail whenever docs.py check prints any STALE line on the merged head, so one page already stale on main fails every goal's pr lane (#3876).

Approaches: (1) a `check --own` flag in docs.py, with the logic in a new own.py: a STALE line for a mapped page whose paths the goal's diff (merge-base with main to HEAD) never touches becomes a FINDING line, said and not failed; the two rows call `check --own`; plain check is unchanged, so health and the scheduled run still report main's staleness. (2) change plain check itself: rejected, it would hide main's staleness from health.

Done lines: with a stale page on main the goal doesn't map to, `check --own` passes and prints the page as FINDING; a page the goal's diff made stale still fails; plain check on main still prints STALE (control row). Three rows, seen red, all from one Python toy.

Open questions: none for the owner.
