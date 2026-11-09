# Plan: wiki-sync

Goal: `.loop/goals/wiki-sync.md` (done lines and Verify by hand are frozen and belong to delivery; not restated or reopened here).
No design doc exists for this goal; the goal file is the design.

## Implementation plan

Root cause: `wiki.py prepare` and `merge.py` ask `release.docs_trouble(top, base)`, which runs `docs.py audit --base origin/main`. `docs.problems` then excludes every commit already reachable from the base (`skip = ["^"+sha for sha in seen + [base]]`), so a page left stale by earlier merged goals (today: Documentation, stale since operate-fit-2) is invisible to the release step, while `docs.py check` (no base) reports it. The release step must use the same notion of stale as `docs.py check`.

Order: engine fix, then toy test (red first), then the pages, then docs.

1. **One stale rule (done line 1).** `wiki.pending` stops passing the base to the stale test. In `release.docs_trouble`, add a keyword (e.g. `whole=False`); `wiki.pending` calls it with `whole=True`, which runs `docs.py audit` with `--base ""` (the same value `docs.py check` defaults to). `release.py`'s own two callers (line 128, 321) and `test-docs-command.sh` keep today's base-relative behaviour, so nothing outside the wiki half changes. `wiki.cmd_prepare` uses the same call, so `prepare` and `merge` can never disagree. The cheap alternative of changing `docs.problems` for everyone is rejected: the audit's base exclusion exists so a goal is not blamed for older pages in other callers.
2. **Refresh, not just list.** `wiki.py prepare` already prints one `REWRITE <page>: STALE ...` line per page; with step 1 that now includes pages no touched path maps to. Update the `wiki.py` docstring and `skills/workflow-release/SKILL.md` ("each stale mapped page" becomes "each page `docs.py check` calls stale"), and make the NEXT line name the pages. The agent still rewrites the prose; the script only finds and commits (it never writes page wording).
3. **Refuse to merge while stale (done line 1).** `merge.py` already calls `wiki.pending` before `gh pr merge` and fails through `autorelease.fail`; keep that, now fed by step 1. A page that cannot be made un-stale by editing (the mapped path keeps changing on the branch) is still refused, with the page names in the message. No bypass flag is added.
4. **Toy test (done line 3), red first.** Extend `dev/toy/test-wiki.sh` (4 KB now; stays under 20 KB): map a second page (`Notes`) to a path the goal never touches, publish it, land a commit on `main` that changes that path (so the page is stale on the base), then run a goal that touches only `calc.py`. Asserts: `prepare` lists `Notes` as stale; `merge.py` refuses naming `Notes`; after the page is rewritten and `prepare --commit`, `docs.py check` prints `DOCS OK`, the branch is pushed, `merge.py` merges and publishes, and `wikifile Notes.md` on the bare wiki shows the new text. Add the case, run it against the unfixed `wiki.py` first and record that it fails, then fix. Add a `.loop/regression.tsv` row for it with `regression.py red` before green, as earlier plans did.
5. **Pages now (done line 2).** Rewrite `docs/wiki/Documentation.md` from what is merged (the `doc-usage` and `docs-command` work, `criteria_max`, Usage section) without changing any criterion wording; confirm every other page is clean with `docs.py check`, and add `wiki-sync` to the Delivery page's description of the release step. `.loop/docs.tsv` needs no new row (Delivery already maps `skills/workflow-release`). Then `docs.py check` must print `DOCS OK`. Publishing (`docs.py publish`) pushes to the GitHub wiki, which is outward-facing: delivery runs it with the release step after the merge, and this plan only makes the pages publish-ready and records the exact command.
6. **Docs and size.** `skills/workflow-release/SKILL.md`, `docs/wiki/Delivery.md` summary/Usage; re-render criteria tables; every script stays under 20 KB (`release.py` is 18.4 KB, so the new keyword is a few lines and the logic goes in `wiki.py`, 4 KB).

## Amendments from review (CEO + Eng, native voice only)

1. **Read-only wide check, scoped fix.** `wiki.pending` and `merge.py` run the whole-repo stale pass with `--dry-run` (list only). `prepare --commit` keeps its base-relative fixing call for mechanical repairs, so the commit stays scoped to the goal; the wide pass only lists.
2. **Same rule in cut.** `release.py` cut and its pre-cut report (lines 128, 321) call `docs_trouble(whole=True)` when `.loop/docs.tsv` exists, so cut cannot call clean a page merge then refuses. `test-docs-command.sh` stays base-relative.
3. **Name pages.** `merge.py` and the NEXT line extract page names from the `REWRITE <page>:` lines.
4. **No bypass, documented dead end.** The refusal stays hard (done line 1). SKILL.md says what to do when a page cannot be cleared (it stays under Needs you via `autorelease.fail`; the owner rewrites it).
5. **Toy test additions.** Assert the `prepare` stale set equals `docs.py check`'s; add a cannot-clear case (page left stale, merge refuses by name); keep `Notes` clean before the later Home/refused-publish sections.
6. **Criteria untouched.** Step 5 diffs the `## Criteria` section of Documentation before and after and fails on any changed line.
7. **PR body** lists under `## Behavior changes`: `wiki.py` pending/prepare, `merge.py`, cut report: base-relative to whole-repo stale rule.
8. **Sizes.** `wiki.py` is 5160 B, `release.py` 18395 B (cap 20480); recheck after the edit.
9. Deferred to TODOS: a scheduled `docs.py check` that queues a refresh goal, so the merge gate is a backstop.

## Failure modes

| Step | Failure | Handling |
|---|---|---|
| 1 | A repo with old stale pages now blocks every merge until they are rewritten | intended by done line 1; the refusal names each page and the fix |
| 1 | Page stale only because of a merge commit or the page's own edit | unchanged: `docs.problems` already ignores merges and counts from the page's last commit |
| 1 | `--base ""` makes the audit blame the goal for everything | only `wiki.pending` uses it; release.py's checks keep the base |
| 3 | Release step loops forever on a page it cannot clear | refusal is final and printed once; no auto-rewrite |
| 4 | Toy repo has no history to make a page stale on base | the test makes the base commit itself, after the page publish |
| 5 | `docs.py publish` refused (wiki off, page not tool-written) | prints the `REFUSED:` reason; delivery reports it under Needs you |

## Review record

<!-- autoplan-accepted:eng -->
- Whole-repo stale pass is list-only; fixes stay base-relative in prepare --commit.
- merge, cut and prepare agree with `docs.py check`'s stale set, proved by a toy assert; refusal names pages; no bypass flag.
- Criteria wording in Documentation unchanged (before/after diff); publish stays a delivery step.
- PR body lists the behavior change.
<!-- /autoplan-accepted:eng -->

## Decision Audit Trail

| # | Phase | Decision | Classification | Principle | Rationale | Rejected |
|---|-------|----------|----------------|-----------|-----------|----------|
