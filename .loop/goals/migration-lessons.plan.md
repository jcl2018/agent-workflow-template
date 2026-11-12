# Plan: migration-lessons

Files: FINDINGS.md (append 12 dated bullets), docs/wiki/Monitoring.md and docs/wiki/Delivery.md (Unreviewed wording only
where a lesson changes behaviour), GitHub issues (new ones and one comment). Checked: FINDINGS.md, both wiki pages and the
issue numbers below exist on origin/main / GitHub.

## Build steps

1. File one issue per untracked actionable lesson (labels: enhancement or defect): Windows-safe check on every merge (1),
   held workers look silent without a session_command (2), `--reply-hook` plus `--govern-hook` installs the hook twice (6),
   setup states up front that un-reviewing needs the owner's own sentence (7), a review hold before auto_merge (9), two
   sessions ran one scheduled routine at once (10), adoption stamps the template version (12). Comment on #1410 for 11.
2. Close #1396 with a pointer to PR 2616, which fixed it.
3. Append 12 dated bullets to FINDINGS.md, each naming its issue, merged PR or goal.
4. Add Unreviewed requirement wording: Monitoring.md (held workers say so on the board; the idle pool is how work
   starts over Remote Control) and Delivery.md (a Windows-safe check on every merge; a review hold before auto_merge).
   Re-render the Tests tables; run `docs.py check`.
5. Fill Verify by hand, commit.

## Tests

Each done line is a repo fact checked by a script, not behaviour: a regression row `findings-one-per-lesson` greps
FINDINGS.md for the 12 dated entries and an issue number or goal on each; `docs.py check` for DOCS OK. Seen red by
running it before the FINDINGS edit.

## Could break

Wording past criteria_max on a page: Setup.md is at it and is left alone. The Unreviewed lock hash is not touched.

## Out of scope

Fixing any lesson; reviewing any requirement.
