# Design: publish-tables

## Problem
After a merge, `wiki.py publish` checks out origin/<base> and runs `docs.py publish`, which refuses with `STALE Tests` when the generated Tests tables no longer match a fresh render (the rows or their last runs moved with the merge). The wiki then lags the repo until someone re-renders by hand. A generated-table-only staleness should never block the publish; a stale hand-written page still must.

## Approaches
1. Re-render in the publish tree: in `wiki.publish`, after checking out origin/<base>, run `criteria.py render --tables` there, commit any changed generated pages in that throwaway tree, then run `docs.py publish`. Cost: about 20 lines in wiki.py (merge.py stays under its size cap). Risk: the repo's own pages stay stale until the next goal re-renders, so the wiki is right but main still reads STALE.
2. Re-render and push to the base from the release step. Fixes both, but a protected base needs a release PR, and a push from the release step can race other merges. Too much risk for this goal.

## Chosen
Approach 1. The wiki is what the owner reads; main's own Tests pages are re-rendered by the next goal's lane (existing behaviour). Only `--tables` is used, so Settings, Automation and README blocks are untouched. Hand-written staleness (`docs.py` commits-since-page check) is not touched, so it still refuses.

## Done line
1. Needs: wiki.py re-render before docs.py publish; a Python toy proving (a) a generated-only stale Tests publishes, (b) a stale hand-written page still refuses; both through the real `wiki.publish` on a toy repo with a bare wiki.

## Open questions
None.
