# Design: health-issues-listing

## Problem
`issues.fetch` lists every issue of the repo (open and closed, one `gh api --paginate --slurp` call, 20 s limit). On a
repo with thousands of issues that listing takes about 30 s (17 MB), so `health.py triage` and `file` refuse with
`REFUSED[gh]` and cannot close or file anything. Every caller needs only a slice: health issues, or open issues.

## Approaches
1. Raise the timeout. One line, but the listing still grows with the repo and every health run reads all closed issues.
   Rejected by the owner's brief ("don't just raise the timeout").
2. Ask gh only for what a caller needs, one page at a time. `fetch(root, scope)` with three scopes: `health` (open
   issues labelled health: triage, finding-age), `open` (open issues: the judge, the `#N` feature lookup) and `held`
   (every health issue, any state, plus the open issues: `file`, which needs the marker keys and the covering check).
   Each scope is a list of filtered queries (`state=open&labels=health`), each read page by page (`per_page=100&page=N`,
   a page of fewer than 100 ends it) with its own timeout, so the time grows with the slice, and a failed page refuses
   with one line naming the page. Chosen.

## Chosen
Approach 2 in `skills/workflow-health/scripts/issues.py` (13 KB now, under the cap). The cache is keyed by root and
scope, the fixture (`LOOP_HEALTH_GH_FIXTURE`) is filtered the same way, and results are also filtered client-side (so a
gh stand-in that ignores filters gives the same answer). A hard page cap stops a stand-in that repeats a full page.
Callers: `file.held_all` uses `held`; `issues.open_findings` and `rules.finding_age` use `health`; `judge` and the `#N`
lookup use `open` (a closed non-health issue named by `#N` no longer maps to a feature: it falls through to the next
citation, the same as an unknown number).

## What each done line needs
"triage --close refuses no more on a repo with over 3,000 open issues": a toy serves 3,200 open issues through a gh
stand-in that honours `labels`, `state`, `per_page` and `page` and sleeps per call, and checks triage lists the health
issues from one small query, `file` reads all pages, and the listing is cut into pages of 100.
"a failed page refuses with one line": a stand-in that fails on page 2 gives one `REFUSED[gh]` line naming the page.

## Open questions
None. The existing toys that pinned the old single call (`test-health.sh`, `test-health-report.sh`) are updated to the
paged calls.
