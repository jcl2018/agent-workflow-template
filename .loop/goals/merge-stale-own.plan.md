# Plan: merge-stale-own

Checked: `wiki.pending` (wiki.py) is the one function merge.py and `wiki.py prepare` use for stale pages; it calls
`release.docs_trouble(top, base, whole=True)`, which runs `docs.py audit --base "" --dry-run` and returns every REWRITE
line. `docs.py check --own` already prints `FINDING STALE <page>: ...` for a stale page the goal's diff does not touch
(`audit.own_split`), and keeps every STALE when run on main itself.

1. wiki.py: `own_findings(top)` runs `docs.py check --own` and returns the pages it prints as `FINDING STALE <page>`.
2. wiki.py `pending`: drop the `REWRITE <page>: STALE ...` lines of those pages, print each as
   `FINDING STALE <page>: ... (not touched by this goal; left for health)`, return the rest.
3. `dev/toy/test-merge-stale-own.py` (Windows ok): a throwaway repo with a mapped page and a base branch. Case 1: a page
   made stale on the base by a commit the branch does not touch: `pending` returns no line, and prints the FINDING.
   Case 2: the branch's own commit makes a page stale: `pending` still returns its REWRITE line. Case 3: on the base
   branch itself every stale page still counts. Rows `merge-stale-other-passes` and `merge-stale-own-refuses`, seen red.
4. Delivery page Runbook: one sentence that merge.py's wiki check refuses only for pages the goal's diff made stale.
   No locked section is edited.

**What could break.** `pending` drops a STALE line if `check --own` misreads the base (no origin/main in a detached
tree): then `own_split` returns nothing moved and every stale page still refuses, which is today's behaviour.

**Out of scope.** The edit+revert routes around STALE; owner review of any page; health's own staleness findings.
