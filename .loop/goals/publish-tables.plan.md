# Plan: publish-tables

## Build steps
1. `skills/workflow-release/scripts/wiki.py`: add `CRITERIA` path and `rerender(tree, cfg)`: run `criteria.py render --tables` with cwd=tree; if `git status --porcelain` shows changed files under the wiki folder, `git add` and commit them in the throwaway tree ("Wiki: re-render generated tables"), print `RERENDERED <pages>`; return the page names. Call it in `publish()` right after the checkout and before the private-name scan and `docs.py publish`. A render failure is not fatal: print it and let docs.py publish report what is still stale.
2. `dev/toy/test-publish-tables.py` (`# windows: ok`): detached worktree of HEAD in a temp dir; (a) corrupt a line of the generated Tests page, assert `docs.py check` reports STALE Tests, call `wiki.rerender`, assert it is clean and committed; (b) make a hand-written page stale (a commit to a path it maps), call `wiki.rerender`, assert `docs.py check` still reports STALE for that page.
3. Regression rows `publish-tables-regen` (a) and `publish-tables-handwritten` (b), level land, seen red before the change (rerender absent), then passing.
4. Docs: Release/Documentation wiki page line for DOC-11's behaviour (Unreviewed text only); no reviewed requirement changed.

## Done line test
1. Both rows above, via the toy.

## What could break
Render in the tree must not touch Settings, Automation or README (`--tables`). A repo with no criteria has no feature pages: render prints TABLES OK and changes nothing.

## Out of scope
Pushing the rendered tables to the base (main's own copies re-render in the next goal's lane); merge.py (at its size cap).

VERDICT: self: plan checked against wiki.py publish() and criteria.py render --tables
