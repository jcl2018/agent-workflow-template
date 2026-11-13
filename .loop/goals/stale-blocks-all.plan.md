# stale-blocks-all plan

Goal: a stale page the goal didn't touch never fails its pr lane; main's staleness stays reported (#3876).

## Steps
1. audit.py `own_split(root, found, notes, rows, name)`: for each STALE line that came from the page map ("N commits since the page"), whose page is in .loop/docs.tsv, and whose mapped paths `git diff <base>...HEAD` never touches, move it to the notes as `FINDING STALE <page>`. Base ref is origin/<base> then <base>; no ref, no git answer, or HEAD already an ancestor of the base (main itself) leaves every line as is.
2. docs.py: `check --own` calls it after the other checks; plain check unchanged (health, the scheduled run and main keep every STALE).
3. Rows settings-render-fresh and review-findings-skill-lines call `check --own` (the second also allows FINDING lines).
4. dev/toy/test-stale-own.py (Python, runs on Windows): throwaway repo with origin/main ref; seven checks: plain and --own on a goal branch, plain and --own on main, a goal-made stale page still fails, B stays a FINDING beside it, a block-staleness line is never moved.
5. Rows stale-own-finding, -main-reported, -main-own-fails, -goal-fails, -block-kept, all guarding DOC-1 (a page behind the code is reported stale), each seen red.

## Risks and how each is held
- Hiding a page the goal made stale: the diff test is per mapped path; fail closed when git gives no answer.
- Hiding main's staleness from the scheduled run (its rows use --own): the ancestor guard keeps every STALE on main.
- Block staleness (Settings, Automation, README) is judged by render, not paths: never moved.
- Package cap 98 files: the code lives in audit.py, no new file.

## Rejected
Changing plain check: health would stop seeing main's staleness. A new own.py: breaks the package headroom row.
