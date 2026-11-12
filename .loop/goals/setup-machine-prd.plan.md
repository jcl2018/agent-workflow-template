# Plan: setup-machine-prd

Checked against the code: `docs/wiki/Setup.md` holds SET-1..SET-10 (10 of `criteria_max` 15); `docs.py criteria Setup`
prints `NEXT SET-11`; `setup.py` installs the govern hook from `--reply-hook` (`reply_hook()`, main at line 213);
`sessions.py assign` and `pool.py need` live in workflow-monitoring; regression rows live in `.loop/regression.tsv`.

The owner's follow-up (strict adoption replay, golden data from the first run on 2026-11-11) folds into SET-11, so the
page ends at exactly 15 requirements.

## Build steps

1. File four enhancement issues: SET-11 (prerequisite checklist + strict replay), SET-12 (multi-repo adoption),
   SET-14 (connector checks), SET-15 (private-name scoping). SET-13 cites #1404. No private names in any of them.
2. Add `dev/toy/adoption-golden.tsv`: the eight golden steps in order (step, what setup checks, the golden result,
   the exact fix it asks for), no private names.
3. Add SET-11..SET-15 under `## Requirements` (SET-11..SET-14 Functional, SET-15 Non-functional), all **Unreviewed**,
   each naming its issue; SET-11 names the fixture.
4. Add `dev/toy/test-adoption-golden.sh`: fails unless the fixture has exactly steps 1..8 in order, each with a
   check, golden result and fix, holds no path or account, and SET-11 on the Setup page names the fixture.
5. `regression.py add adoption-golden --level land --goal SET-11`, then `regression.py red` with a break that drops a
   fixture step; `docs.py render` / `audit`, then `docs.py check` until DOCS OK.

## Tests per done line

1. `adoption-golden` (land): seen failing with step 8 removed from the fixture, passing after. It guards the golden
   data and SET-11's reference to it; the replay itself is unbuilt (SET-11 is Unreviewed).
2. `docs.py check` prints `DOCS OK`; the page's count is 15, not over `criteria_max`.

## What could break

The page is now full: the next Setup requirement needs a merge or a new page. A private name in the fixture or issues
would block pushes: run `private.py scan` before `goal.py pr`.

## Out of scope

Building the checklist, multi-repo flow, connector probe, replay or private-list scoping; the Windows fixes (#1396,
#1397) belong to sibling goals.
