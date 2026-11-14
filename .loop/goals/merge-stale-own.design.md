# Design: merge-stale-own

**Problem.** `merge.py` refuses on any stale wiki page in the repo. `wiki.pending` runs `docs.py audit --base "" --dry-run`
(every page `docs.py check` calls stale), so a goal is refused for a page a different goal made stale. On 2026-11-13
held-time-budget (green) was refused for "STALE Automation: 1 commits since the page: 3c1ef1e0", a matrix-smoke commit
it does not touch. #3905 gave the lane rows `docs.py check --own`; merge.py's wiki step never got it (#3941).

**Approaches.**
- (a) Add an `--own` flag to `docs.py audit` and pass it from `wiki.pending`. Cost: `docs.py` is at 19,792 of 20,480
  bytes and `audit.py` would need the notes printing too. Risk: two scripts change for one rule.
- (b) Keep the scope rule in one place, `docs.py check --own` (`audit.own_split`), and have `wiki.pending` ask it which
  stale pages the goal's diff does not touch, then drop only the `REWRITE <page>: STALE ...` lines of those pages and
  print each as `FINDING STALE <page> ...`. Cost: one extra `docs.py check --own` run, `wiki.py` only (10.9 KB). Risk:
  none to the check itself, since `--own` is unchanged and on main itself it keeps every STALE.

**Chosen: (b).** The scope is defined once, by the command the lane rows already use. Anything that is not an untouched
STALE page (MISSING, UNMAPPED, REWRITE of a page the diff touched, counts, criteria) still refuses. Health and the
scheduled run still flag main's staleness because plain `docs.py check` is unchanged.

**Done line.** A page stale from a commit the goal does not touch no longer stops merge.py (it prints as a FINDING);
a page the goal's own diff makes stale still refuses. Python toy `dev/toy/test-merge-stale-own.py` builds a throwaway
repo with both cases and calls `wiki.pending`; rows seen red before the change.

**Open questions.** None. The Delivery page (maps skills/workflow-release) gets a Runbook sentence, no locked section.
