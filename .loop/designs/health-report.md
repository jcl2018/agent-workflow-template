# Design: health-report

Status: DRAFT for owner review. Meets the frozen done lines in .loop/goals/health-report.md; changes none of them.

## Problem (measured on this branch)
- `health.py check` prints `HEALTH REPORT`, then only the groups that have rows, then a verdict. It has no header naming the groups it ran or skipped, and the group is called `cost`, not `performance`. HLT-3 and HLT-4 on the Health page are the old one-line wording (done line 1 replaces it with the owner's text).
- `health.py run` files every WARN/FAIL/UNREAD row with one shared label `health`. There are no per-group tags, no confirm step, and no way to file one group. Its only preview is "no token = WOULD lines".
- `health.py` is 17786 B against the 20 KB cap (warn at 18432 B). Report and filing changes cannot land inside it. Health would warn on itself.

## Approach (recommended): split report and filing out of health.py, add `preview` and `file`
1. New `scripts/report.py` (pure formatting, no I/O). It takes the rows plus the groups run and skipped and prints:
   - a header line: `groups run: size, criteria, docs, hygiene, performance; skipped: mine (no setting)`;
   - each group in `ORDER`, titled by its display name (`cost` shows as `performance`, `mine` as `Mine`), listing every rule it checked with PASS/WARN/FAIL/UNREAD, a `-> fix:` on every non-pass line, then one verdict line.
   - Existing rules already emit PASS rows. Where one emits only on trouble, it gets a PASS row so "every rule it checked" holds. A rule that cannot read its data stays UNREAD and keeps the verdict red.
   - `--json` carries the same data plus `groups_run` and `groups_skipped`.
   - Internal family names (`cost`) stay as they are. Only the display and the tag change. `--family` stays; `--group` is added as the same option.
2. New `scripts/file.py` (the old `cmd_run` moves here and grows):
   - `preview` lists every issue it would open, update, close or reopen, each with its `health:<group>` tag, and writes nothing, even when a token is set. It needs no `--live` and no network write.
   - `file --group NAME[,NAME]` is the only command that writes. With no `--group` it refuses (naming the groups) rather than filing everything, since nothing is written until the owner confirms or names groups. It touches only issues of the named groups: open, update, close and reopen are all limited to those groups' markers.
   - Each issue gets the milestone `Backlog` and the label `health:<group>` (`health:size`, `health:criteria`, `health:docs`, `health:hygiene`, `health:performance`, `health:mine`), created with `gh label create --force`. The old plain `health` label is added too, so the existing search keeps working (see PENDING).
   - Hidden marker keys stay `family:subject:rule` (cost keeps `cost:`), so issues already filed are found and updated, and an old issue gets its new tag on the next `file`.
   - The `performance` group also files the judge's savings candidates. This calls the model through `judge_command`, so `preview` and `file` run the judge only when `--group performance` is named. No judge, or an unavailable judge, means no savings issues are opened or closed (same "unread closes none" rule).
   - `mine` is filed only when named explicitly, as `health:mine`. Today `run` never files it. HLT-4 now lists the tag, so that changes, and it is a PENDING decision.
3. `health.py` keeps `check`/`judge` and the thin CLI, and delegates to `report.py` and `file.py`. `run` stays as a deprecated alias of `preview` for one release. The 9-rule cap is untouched (no rule is added or retired). Target: `health.py` under 18432 B; `report.py` and `file.py` each well under 20 KB.
4. Docs. `SKILL.md` and `references/commands.md` describe `check`, `preview`, `file --group`. The Health page Usage lists the agent requests, one per line: check, preview, file by group, judge. For example "Ask: run a health check", "Ask: preview what health would file", "Ask: file the health:docs findings" and "Ask: judge the health report". The Criteria section gets the owner's HLT-3/HLT-4 text, marked Reviewed 2026-11-08 by `criteria.py review --user`. The Tests table gets rows for the new tests.
5. Tests. One new toy test, `dev/toy/test-health-report.sh`, using `fakegh` and a toy repo that has findings in several groups (a near-20-KB script, a stale page, a leftover merged branch, an over-budget goal). It asserts: the header names groups run and skipped; every group lists every rule with a state, each non-pass line has a fix, and there is one verdict; cost reads as performance; an unread rule is never pass. It also asserts that `preview` makes no `gh` write call (the fakegh log has no create/edit/close/reopen) and prints the tag on each line; and that `file --group size` creates only `health:size` issues on Backlog, leaving docs and hygiene issues alone (including an existing open `health:docs` issue). A later run updates in place, a fix closes, a return reopens, per group. Regression rows go in `.loop/regression.tsv` so the criteria rule stays green.

## Alternatives considered
- B, minimal: add the header and a `--group` flag inside health.py. Rejected: pushes health.py past the size warning and past the cap soon after; Health would fail its own Size rule.
- C, filing stays one flag on `run`: `run --live --family X`. Rejected: the owner wants a separate preview step and no write without a named group; overloading `run` keeps the old "token means write" trap.
- D, a full redesign into a `health` package. Rejected: bigger install surface, and not asked for.

## Risks
- Existing health issues carry only the `health` label. The first `file` per group relabels them. Preview must show that as an "update". It is not a new issue.
- Per-group tags need labels to exist. Create with `--force`; tolerate failures in preview.
- Filing the judge's savings sends repo data to the model (already true of `judge`). It is opt-in: only with `--group performance`.
- Toy test depends on `fakegh` supporting label and edit calls. If it lacks them, extend `fakegh` (dev/toy only).

## Distribution
No new artifact. Two new scripts ship inside the existing `workflow-health` skill. They must be listed anywhere the skill's script list is (listing.json, loop-files.md, the Agensi single-file note, where a missing sibling already prints `UNREAD`).

## Open decisions (recommended answer taken for each)
- Keep the old `health` label next to `health:<group>`: yes.
- `file` with no `--group` refuses: yes.
- `mine` filed only when named: yes.
- `run` kept one release as an alias of `preview`: yes.
