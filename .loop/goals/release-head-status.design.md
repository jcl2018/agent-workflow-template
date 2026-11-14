# Design: release-head-status (#3870)

## Problem
merge.py's release step (`autorelease.release_statuses`) re-runs the affected rows in a fresh detached copy of the release
PR's head and posts failure under every required check name whenever that run exits non-zero, with its output thrown away.
A release head only moves VERSION and CHANGELOG over a base that already holds the goal's tested tree, yet in thermis#907 the
fresh copy could not run the rows (or exited 1 for a reason that is no failed row), "stories" and "Cloudflare Pages" got
failure for a head nobody tested, and the refusal asked the owner to merge by hand.

## Approaches
1. Carry the pass: when the goal's pr lane passed (`statuses: ok`) and the release head differs from its parent only in the
   version file and CHANGELOG, post success without a lane. Otherwise run the lane, capture its output, post failure only for
   rows that printed `FAIL id`, post nothing when no row ran and failed, and make the refusal name the rows or the reason.
   Cost: about 60 lines in autorelease.py, 3 in merge.py. Risk: a carried pass trusts the goal's lane; the diff test is exact
   (names only, against the parent), so any other change runs the lane.
2. Always run the lane but make it robust (install deps, retry). Cost: repo-specific, never ends; the lane is already slow.

## Chosen
Approach 1: it removes the lane from the common case and makes the uncommon one honest.

## Done line
- Bump-only head: `carried()` posts success, no lane. Real failure: rows named in `release_status_why` and in the
  RELEASE_STATUS_FAILED refusal; a lane that could not run: RELEASE_STATUS_UNTESTED, no status posted.

## Open questions
None.
