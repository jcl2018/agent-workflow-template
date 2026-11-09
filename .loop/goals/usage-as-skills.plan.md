# Plan: usage-as-skills

Goal: `.loop/goals/usage-as-skills.md` (done lines and Verify by hand belong to delivery; not restated or reopened here).
There is no separate design doc; the goal file is the design.
Reviewed by /autoplan (unattended; native CEO + Eng pass, abbreviated; no outside voice, no UI or DX scope beyond the docs themselves). Every question took the recommended answer. The run stops at the final gate and approves nothing.

## What exists

- Usage blocks on six feature pages (Delivery, Documentation, Health, Monitoring, Regression, Setup; Home is not a feature page) list `script.py verb` commands.
- `skills/workflow-docs/scripts/criteria.py` `unknown_commands` already requires each backticked `*.py` in a Usage block to appear in some `SKILL.md` or `commands.md`. That is the opposite of the new rule and gets replaced.
- Toy tests for Usage live in `dev/toy/test-criteria.sh` (the `usage_page` cases, incl. the `ghost.py` truth case).
- Every SKILL.md already has one `## \`verb ...\`` section per command, each showing the script call. They are the base for the command map.
- All six pages sit at 5 criteria with the cap at 6, so one new criterion fits on the Documentation page.

## Decisions (all auto, recommended)

1. **Command syntax.** `/<skill> <verb> [args]`, the verb being the SKILL.md section heading (`/workflow-monitoring go "goal" --done "line"`, `/workflow-monitoring operate`). A Usage line may instead be a quoted plain request ("start a goal to add caching"). Each line ends with what it does in a few words.
2. **`operate` becomes a documented verb** of workflow-monitoring (today it is prose: "run `operate.py run`"). Same for `send`. The map names the routine; no script behavior changes.
3. **Check replaces the truth check.** `unknown_commands` is replaced by two findings, both kind `USAGE`: (a) a Usage line that names a `.py` or `.sh` file or a `python`/`python3`/`bash` command fails, with the fix "write it as an agent request or /skill verb"; (b) a backticked `/skill verb` that is not a verb in that skill's SKILL.md command map is a finding (keeps the old "real command" truth, in the new form). A repo with no `skills/` dir skips (b), as today.
4. **README** (listed under Touches): its python command block becomes the same skill commands, with one line pointing at SKILL.md for the routine each runs. README is not a feature page, so the check does not apply to it; keep it consistent by hand.
5. **Taste, surfaced at the gate:** the new DOC criterion is added Unreviewed on Documentation (DOC-6, fills the cap). Marking it Reviewed is the owner's call (`criteria.py review --user`).

## Work (in this order)

1. **SKILL.md command maps.** In each of the seven SKILL.md files add a `## Command map` table: `Ask` (`/skill verb ...`) | `Runs` (the exact script routine, `python3 scripts/x.py verb`). Cover every verb the matching wiki Usage uses, including delivery's `goal new`/`step`/`record`/`pr` and `merge`/`release`, docs `audit`/`check`/`publish`/`restore`/`criteria`/`milestone`, monitoring `operate`/`send`/`go`/`watch`/`resume`/`report`/`dashboard`/`met`/`cleanup`, health `check`/`judge`/`run`, regression `add`/`red`/`run`/`sync`/`workflow`, setup `setup`/`settings reference`/`fill-repo`. Existing per-verb sections stay; the map points at them. Check the packaged skill copy (`dev/package.py`) ships SKILL.md unchanged.
2. **Check, `criteria.py`.** Implement decision 3. Message text names the page, the offending token and the fix. Update the `rules()` / template wording so `template.md` says Usage lines are agent requests, with one copy-paste example.
3. **Toy tests**, `dev/toy/test-criteria.sh` (`usage_page` helper): a Usage naming `calc.py` fails; naming `run.sh` fails; `python3 calc.py` fails; `/workflow-delivery go "x"` passes; an unknown `/workflow-delivery nosuch` fails; a plain-words request passes; no Usage still passes. Replace the old `ghost.py` case. Run red before green. Add regression rows (category `criterion`, goal DOC-6) with `regression.py add` then `red`; run `regression.py sync` and `criteria.py render` twice for a clean diff.
4. **DOC-6** on `docs/wiki/Documentation.md`: "A feature page's Usage is written as what the owner asks the agent, and names no script file." Unreviewed. Update that page's own Usage first.
5. **Rewrite the other five Usage blocks** from their SKILL.md maps, one line each, in the new form; criterion text untouched; `docs/wiki/Home.md` untouched.
6. **README** command block, decision 4.
7. **Gates before PR:** `docs.py check`, `health.py check`, `dev/toy/test-criteria.sh`, `test-docs.sh`, `test-docs-command.sh`, `test-health.sh` all green; `docs.py publish` is not run.

## Risks

- Wiki pages go stale if a SKILL.md verb is renamed later; check (b) catches it.
- `operate.py run` has no existing verb heading, so its map row must match what the script actually does (read it first, do not paraphrase).
- Adding a criterion to a reviewed-hash page: only Documentation changes its Criteria list; other pages' criterion lines must stay byte-identical or their hashes break.

## Not in scope

Changing any script behavior or flags; renaming skills; enforcing the rule on README or SKILL.md prose; auto-generating the maps from the scripts.

## PR body must list under `## Behavior changes`

Docs check now fails a Usage naming a script file or python/bash command; the old "script name must appear in a skill file" check is gone; DOC-6 added (Unreviewed).

## Decision audit

| # | Decision | Class | Principle |
|---|---|---|---|
| 1 | `/skill verb` plus plain-words syntax | mechanical | explicit |
| 2 | `operate`/`send` become documented verbs | mechanical | completeness |
| 3 | Replace the old truth check, keep a verb-exists check | mechanical | DRY, completeness |
| 4 | Update README block too | taste | completeness (Touches lists it) |
| 5 | DOC-6 added Unreviewed | taste | pragmatic; owner reviews |

<!-- autoplan-accepted:eng -->
- The check fails a feature page whose Usage names a .py or .sh file or a python/bash command, and a toy test proves it.
- Every `/skill verb` in a Usage maps to a verb in that skill's SKILL.md command map.
- docs check and health stay green.
<!-- /autoplan-accepted:eng -->
