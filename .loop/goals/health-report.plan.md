# Plan: health-report

Goal: `.loop/goals/health-report.md` (done lines and Verify by hand are frozen and belong to delivery; not restated or reopened here).
Design: `.loop/designs/health-report.md` (DRAFT, recommended approach A). Reviewed by /autoplan (unattended; no UI scope, no developer-tool scope). Every question took the recommended answer.

## Implementation plan

Order: criteria wording, then report module, then filing module, then CLI wiring, then toy test, then docs.

1. **HLT-3 and HLT-4 wording (done line 1).** In `docs/wiki/Health.md`, unreview HLT-3 and HLT-4, replace each with the owner's text word for word as the goal gives it, then `criteria.py review --user` for HLT-3 and HLT-4 only, dated 2026-11-08, then `criteria.py render`. Existing HLT-3/HLT-4 regression rows stay linked; new rows come in step 6.
2. **`scripts/report.py` (done line 2).** Pure formatting, no I/O. Input: rows, groups run, groups skipped (with reason). Output: a header `groups run: ...; skipped: ... (why)`, then each group in `ORDER` by display name (`cost` shows as `performance`, `mine` as `Mine`), every rule it checked with PASS/WARN/FAIL/UNREAD, `-> fix:` on each non-pass line, then one verdict. Rules that today emit a row only on trouble get a PASS row so "every rule it checked" holds. UNREAD stays red. `--json` adds `groups_run` and `groups_skipped`. Internal family names and marker keys are unchanged; `--group` is added as the same option as `--family`.
3. **`scripts/file.py` (done line 3).** `cmd_run` moves here. `preview` lists each issue it would open, update, close or reopen with its `health:<group>` tag and makes no `gh` write call, even with a token. `file --group NAME[,NAME]` is the only writer; with no `--group` it refuses and names the groups. Open, update, close and reopen are all limited to the named groups' markers. Each issue gets milestone `Backlog` and label `health:<group>` (size, criteria, docs, hygiene, performance, mine), labels created with `gh label create --force`; the old `health` label is kept too so the existing search finds old issues. An old issue gets its tag on the next `file` and preview shows it as an update. The judge's savings candidates are filed only under `--group performance` (judge runs only then); an unavailable judge opens and closes none. `mine` is filed only when named.
4. **CLI wiring.** `health.py` keeps `check` and `judge`, delegates to `report.py` and `file.py` through the sibling path (missing sibling prints `UNREAD`, as for the other siblings). `run` stays one release as a deprecated alias of `preview`. The 9-rule cap is untouched. Target: `health.py` under 18432 B (it is 17786 B now), new modules each well under 20 KB.
5. **Docs (done line 4).** `SKILL.md` and `references/commands.md` describe `check`, `preview`, `file --group`. The Health page Usage lists the agent requests one per line: run a health check, preview what health would file, file the health:<group> findings (by group), judge the health report. Tests table and Summary updated; list the new scripts in `listing.json`, `loop-files.md` and the single-file note. `docs.py check` and `criteria.py render --check` pass.
6. **Toy test (done line 5).** New `dev/toy/test-health-report.sh` using `fakegh` and a toy repo with findings in several groups (near-20-KB script, stale page, merged branch, over-budget goal). Asserts: header names groups run and skipped; every group lists every rule with a state; each non-pass line has a fix; one verdict; cost reads as performance; an unread rule is never pass; `preview` makes no create/edit/close/reopen call in the fakegh log and prints the tag per line; `file --group size` creates only `health:size` issues on Backlog and leaves an existing open `health:docs` issue untouched; a later run updates in place, a fix closes, a return reopens, per group; `file` with no `--group` refuses. Extend `fakegh` (dev/toy only) if it lacks label or edit calls. Add `.loop/regression.tsv` rows for HLT-3 and HLT-4, each seen failing once with `regression.py red` before passing.

## Failure modes

| Step | Failure | Handling |
|---|---|---|
| 2 | A rule emits no row when healthy, so it vanishes from the report | add PASS rows; the test counts every rule per group |
| 2 | Display name `performance` leaks into marker keys and orphans old issues | display and tag only; keys stay `family:subject:rule` |
| 3 | Preview writes through a token | preview has no write path; test checks the fakegh log |
| 3 | `file` with no group files everything | refuses naming the groups |
| 3 | A group's filing closes another group's issue | close/reopen filtered by the group's markers; test with an open `health:docs` issue |
| 3 | Rule unread then closes its issues | unread closes none (kept from `cmd_run`) |
| 3 | Judge sends repo data to a model unasked | judge runs only with `--group performance` |
| 4 | `health.py` passes the size warning | logic lives in the new modules; check its byte count |
| 4 | Siblings absent on a single-file install | `UNREAD`, verdict red, as today |
| 6 | `fakegh` lacks label or edit | extend it in dev/toy |

## Review record

Single-pass review by the planning agent, no separate outside voices (unattended run; Codex not consulted). Findings that changed the plan: `file` with no group refuses (nothing written until the owner names groups); preview must not depend on `--live`; judge savings filed only under `--group performance`; `health.py` must stay under its size warning, so report and filing split out; the old `health` label is kept for lookup of existing issues.

<!-- autoplan-accepted:ceo -->
- Keep the owner's HLT-3/HLT-4 text verbatim; report, preview and file(by group) as specified in the goal; filing never touches groups not named.
<!-- /autoplan-accepted:ceo -->
<!-- autoplan-accepted:eng -->
- `preview` makes no write call; `file` requires `--group`; markers unchanged; `health.py` stays under 18432 B; toy test uses `fakegh` and no model.
<!-- /autoplan-accepted:eng -->

## Decision Audit Trail

| # | Phase | Decision | Classification | Principle | Rationale | Rejected |
|---|-------|----------|----------------|-----------|-----------|----------|
| 1 | Eng | Split `report.py` and `file.py` out of `health.py` | Mechanical | P5 | health.py is 17786 B of 20480 | Inline edit (B), package (D) |
| 2 | Eng | `preview` separate from `file`, no token trap | Taste | P5 | Owner wants no write until confirmed | Overload `run --live` (C) |
| 3 | Eng | Keep old `health` label beside `health:<group>` | Taste | P4 | Existing issues and search keep working | Drop old label |
| 4 | Eng | `file` with no `--group` refuses | Taste | P5 | Matches "nothing written until I name groups" | File everything |
| 5 | Eng | `mine` filed only when named | Taste | P5 | HLT-4 lists the tag; mine runs outside the repo | Never file mine |
| 6 | Eng | `run` kept one release as alias of `preview` | Taste | P6 | Nothing calling it breaks | Remove now |
| 7 | Eng | Judge savings filed only under `--group performance` | Mechanical | P5 | Judge calls a model with repo data | Always judge |
| 8 | Eng | Display `performance`, keep internal `cost` keys | Mechanical | P3 | Old issues stay matched | Rename keys |
