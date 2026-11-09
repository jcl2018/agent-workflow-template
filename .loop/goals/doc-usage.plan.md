# Plan: doc-usage

Goal: `.loop/goals/doc-usage.md` (done lines and Verify by hand belong to delivery; not restated or reopened here).
Design: `.loop/goals/doc-usage.design.md`.
Reviewed by /autoplan (unattended, CEO + DX + Eng, native voice only; no outside voice). Every question took the recommended answer; the only auto decision kept the design as one goal (the proposal to split out the not-enforced rows was declined).

## Amendments to the design (from review)

Work in this order, so a red test never blocks the page rewrites: 1-4 first, then 5-6, then 7.

1. **Cap reader, `criteria.py` only.** `health.py` has no cap logic of its own (it reaches the cap through the docs check), so design step 2 shrinks to: health.py is unchanged, and one test sets `criteria_max` to 1 and asserts both `docs check` and health fail. `criteria_max` is the only name anywhere.
2. **Bad value is loud.** Reject bool, non-integer and out-of-range (1..50) `criteria_max` with a named finding (key, bad value, file, fix), never a silent fall back to 6. A missing key means 6. Resolve the repo root as `docs.py` does (cwd or `--repo`).
3. **Stale sheets.** `max_criteria` becomes an ignored optional key in the rules parse; a consumer sheet that still carries it, or lacks it, must not break the loader. The shipped sheet drops it.
4. **Finding text.** The CAP finding names the page, count, limit, its source (`criteria_max` in `.loop/config.json`) and the fix. Usage out of place and a `Commands` section each get a message that says rename to Usage and place it between Summary and Criteria.
5. **Setup.** `settings.py` validates `criteria_max` (positive int) before writing and rejects with what/fix on stderr and a non-zero exit; add a test, plus a check that `references/settings.md` matches `settings.py` output.
6. **Usage format and truth.** Add one copy-paste Usage example to the sheet's Layout prose (command in backticks, one line of purpose). Add a deterministic warning-level check that each backticked command in a Usage block appears in the matching `SKILL.md` or `references/commands.md`. Absence of Usage stays silent.
7. **Not-enforced rows.** Re-read the real Tests cells first (SET-2 shows a final not-enforced row; HLT-5 is a judge section). SET-2 rides the `criteria_max` setting test. HLT-5 gets a structural test only; if no honest test exists, list it in the goal report as an expected outcome.

## Work

- `criteria.py`, `template.md` (drop number, say "the repo's criteria limit", add `usage` optional between Summary and Criteria), `settings.py` + regenerated `references/settings.md`, `.loop/config.json` `criteria_max: 6`.
- DOC-1 in `docs/wiki/Documentation.md`: frozen wording, unreviewed, then `criteria.py review --user`. Keep regression row ids; run `regression.py sync` and render twice with a clean diff.
- Rewrite Delivery, Documentation, Health, Monitoring, Regression, Setup to the template (Home is not a feature page); Usage from each skill's real commands; criterion wording untouched; at most 6 criteria.
- `dev/toy/test-docs-command.sh:44` switches from seding `max_criteria: 5` in the sheet to setting `criteria_max` in the temp repo's config, and asserts the sheet no longer contains `max_criteria`.
- `dev/toy/test-docs.sh` cases: cap 1 fails a 2-criterion page and default 6 passes; invalid `criteria_max`; Usage passes; no commands and no Usage passes; Usage out of order or empty; `Commands` still fails; Usage with a fenced code block. Rows category `criterion`, goal DOC-1 / SET-2, seen red before green.
- Sweep current-facing docs (README, wiki, references) for `max_criteria`; leave CHANGELOG history.

## PR body must list under `## Behavior changes`

Default cap 5 to 6; the sheet's `max_criteria` key removed; Usage allowed; DOC-1 wording; CAP finding text.
