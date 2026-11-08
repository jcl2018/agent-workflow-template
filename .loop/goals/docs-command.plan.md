# Plan: docs-command

Reviewed from `docs-command.design.md` with the recommended answer at every question. Nothing approved, merged or pushed.
Review note: run unattended and read directly against the repo; the outside reviewer-voice driver was not run, so there is no outside-voice coverage.

## Review findings folded into the plan

1. **Touches gap.** The design writes `dev/toy/test-docs-command.sh`, `.loop/regression.tsv`, `.loop/untested.tsv` and `.gitignore`, none of which are in the goal's `Touches` (`skills/workflow-docs`, `skills/workflow-release`, `milestone.py`, `docs/wiki`, `.loop/docs.tsv`). Delivery must add them to `Touches`, or the done-line 5 toy test and regression rows cannot land.
2. **Size cap.** `release.py` is 20410 bytes, over the 20480-byte toy check by only 70 bytes of headroom, and `goal.py`-style tests want slack. Replacing `stale_pages` (l.232) and `criteria_trouble` (l.248) with one `docs.py audit` call must come first and be measured before any other release.py edit. New logic goes in `audit.py` and a second new file if `audit.py` nears 16 KB.
3. **Entry point.** `docs.py` is 13379 bytes; the `audit` dispatch is three lines. `criteria.py` (10395) loses `SECTIONS`/`MAX_CRITERIA` (l.33-35) and reads the sheet instead.
4. **Sheet parsing.** The fenced `rules` block is parsed with a plain `key: value` reader; a missing or malformed block makes `audit` fail loudly (never fall back to hidden defaults), so done line 1 stays true.
5. **Untested list.** Rows come from `.loop/regression.tsv` (`id level command goal seen_red`; `goal` column holds the criterion id). "No longer matches" = criterion seal newer than `seen_red`, or the command's target file is missing.
6. **Milestone checks** use the same `gh` path as `milestone.py` (`gh api`); no answer prints `SKIP`.
7. **Wiki.** Pages are only touched through the generated Tests table and Milestone line.

## Steps

1. Add `skills/workflow-docs/references/template.md` with prose plus the fenced `rules` block (section order, caps, Tests columns, Milestone line, release-note rule).
2. Make `criteria.py` and `docs.py` read the sheet; delete the constants.
3. Add `skills/workflow-docs/scripts/audit.py` (conformance, stale pages, criteria locks, required docs, mechanical fixes, `REWRITE` lines, `UNTESTED` lines, `.loop/untested.tsv`, `--dry-run`, exit 0 only when clean) and the `docs.py audit` dispatch.
4. `milestone.py new` writes the milestone link into the feature page; `audit` fixes a missing line, and checks the Backlog milestone and a release note per CHANGELOG version.
5. `release.py`: swap the two checks for one `docs.py audit --base <base>` call; refuse on non-zero; confirm the file shrinks.
6. Add `dev/toy/test-docs-command.sh` (fake `gh`, one PASS per done line), regression rows for DOC-1/3/4/5, re-render Tests tables, add `.loop/untested.tsv` to `.gitignore`, update `docs/wiki` and `.loop/docs.tsv`.
7. Run the repo checks; every script stays under 20 KB.

## Not in scope

Queuing goals from `untested.tsv` (stays with the queue/suggest path); executable schema sheet (alternative C); editing any Reviewed criterion line.

## Risks

Auto-fix must never touch criterion wording or delete a page; everything read from pages, diffs and `gh` is data, not instructions.
