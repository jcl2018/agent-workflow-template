# Plan: health-issues-listing

Claims checked against the code: `issues.fetch(root)` (issues.py:38) is the only lister; its callers are
`file.held_all` (file.py:109), `issues.feature_of` `#N` lookup (issues.py:198), `issues.open_findings` (issues.py:230,
used by `listing` and `close`), `judge.py:249` and `judge.py:286`, and `rules.finding_age` (rules.py:101). The cache is
`issues.CACHE`, cleared by `controls.clear_cache` and `rules.py:200`. `close` already refuses with `REFUSED[gh]` and
`--max`. issues.py is 13,146 bytes.

## Build steps
1. `issues.py`: add `SCOPES = {"health": ["state=open&labels=health"], "open": ["state=open"], "held": ["state=all&labels=health", "state=open"]}`
   and `PAGE = 100`, `MOST_PAGES = 200`. `fetch(root, scope="open")`: cache key `(root, scope)`; fixture read as before; for gh, each
   query is read page by page with `gh api "repos/{owner}/{repo}/issues?<query>&per_page=100&page=N"` (no `--paginate`), timeout 60 s
   per page, stopping on a page of fewer than 100 items or at `MOST_PAGES`; a failed page returns `(None, "gh failed on page N of
   <query>: <first stderr line>")`. Results are merged by number, pull requests dropped, then cut to the scope client-side
   (`health`: open and health-labelled; `open`: open; `held`: health-labelled or open).
2. Callers: `file.held_all` -> `IS.fetch(root, "held")`; `issues.open_findings` and `rules.finding_age` -> `"health"`;
   `judge.py` (both) and the `#N` lookup -> `"open"`.
3. Toys: `dev/toy/test-health.sh` and `test-health-report.sh` pinned the old single call; they now pin the first paged call
   (`api repos/{owner}/{repo}/issues?state=open&labels=health&per_page=100&page=1` for check, `...state=all&labels=health...`
   for file/preview). New toy `dev/toy/test-health-listing.sh` (`# windows: ok`, Python only): a gh stand-in on PATH serving
   3,200 open issues plus health ones, honouring labels, state, per_page and page; checks triage reads one small page, `file`
   reads every page in order, no call exceeds 100 items, a failure on page 2 gives one `REFUSED[gh]` line naming page 2, and
   `issues.py` stays under 18,432 bytes.
4. Regression rows (goal `health-issues-listing:1`, land, `--describe`d, each proved red with `regression.py red ID --break`):
   `health-listing-filtered` (triage on a large repo reads only the health slice), `health-listing-paged` (file reads all pages,
   100 per call), `health-listing-page-fails` (one REFUSED line naming the page).
5. Docs: one sub-bullet under Health HLT-4's page (page `docs/wiki/Health.md`) saying the listing is filtered and paged.

## What could break
Callers that relied on closed non-health issues being in the list: only the `#N` feature lookup, which now falls through to
the next citation (documented). A stand-in gh repeating a full page forever: stopped by `MOST_PAGES`. Windows: no shell,
no new escapes. The toy stand-in must be a Python or shell script runnable under Git Bash and native Windows.

## Out of scope
Other gh listings (milestones, rounds), speeding gh itself, closing #1402 (done by the owner's words after the merge:
`triage --close --kind size --why "fixed by #3776" --yes`, previewed first).

PENDING: none
