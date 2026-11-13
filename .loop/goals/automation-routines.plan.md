# automation-routines: plan

Checked against the code: `deployments.owed` (docs check, DOC-16) reads `.loop/routines.tsv`; `counting.entries` builds
the Automation rows from the config `automation` list; `enforce.scheduled_task` knows where scheduled tasks live
(`~/.claude/scheduled-tasks/<id>/SKILL.md`, `LOOP_SCHEDULED_TASKS_DIR`); health rules register in `report.py` GROUPS,
`rules.py` FUNCTIONS and CONTROLS, with a fixture in `controls.py`. All exist at v0.28.10.

## Build steps
1. `deployments.py`: `routines(root)` (routines.tsv rows plus custom config entries with `page`), `owed` uses it (a custom
   entry with no page is a finding), `prompt(...)` text and `POINTER` regex.
2. `docs.py prompts`: one `PROMPT <routine>: <line>` per routine.
3. `report.py`: `prompt_pointer(root)` rule (adoption); register in `GROUPS`, `rules.FUNCTIONS`, `rules.CONTROLS`, a
   fixture in `rules.py`; `controls.py` restores `LOOP_SCHEDULED_TASKS_DIR`.
4. Toy `dev/toy/test-automation-routines.py` (Python): custom entry gets the Automation row, owes a Runbook, prompt line,
   health warns on a prompt with steps and stays quiet on pointers only.
5. Rows seen red; commands/wiki lines (Automation Usage is owner-locked, so Documentation/Health Usage and runbooks
   only); DECISIONS.md draft under "Waiting on owner un-review" for AUT-1, AUT-2, AUT-3, AUT-4, AUT-8.

## What could break
The health rule count in docs and tests that list the rules; script sizes (rules.py, report.py near the cap).

## Out of scope
Rewriting the Reviewed AUT pages (drafted only), changing the launch agent, a prompt writer that installs prompts.

DEPTH: full
