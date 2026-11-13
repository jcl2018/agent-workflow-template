# stale-blocks-all plan

1. own.py: split() moves a STALE line of a mapped page the goal's diff (merge-base with main..HEAD) never touches to a FINDING note; base ref origin/<base> then <base>; no ref means judge as before.
2. docs.py: `check --own` calls it; plain check unchanged.
3. dev/toy/test-stale-own.py (Python, runs on Windows): throwaway repo with B stale on main; five checks.
4. Rows: stale-own-finding, stale-own-main-reported (control), stale-own-goal-fails, each seen red; settings-render-fresh and review-findings-skill-lines call `check --own` and re-seen red.
5. Docs: rows guard DOC-15's STALE bullet; audit regenerates Tests tables.
