# automation-routines: design

## Problem
Health and regression are the only routines a repo can schedule with a Runbook. A repo's own routine (a digest, a site
deploy) has no required Runbook, no generated prompt, and a scheduled prompt can drift into holding the steps, so two
machines run different rounds. The owner wants the Runbook in the repo to be the only place the steps live.

## Approaches
1. A new registry file and a new skill script for prompts. Cost: a new file under skills/ (not allowed) and a third
   registry beside `.loop/routines.tsv` and the config `automation` list. Risk: drift between the three.
2. Reuse what exists. The config `automation` list is the schedule registry (name, cadence, runs); `.loop/routines.tsv`
   maps built-in routines to their Runbook page. A custom entry (any name but health, regression, digest email) carries
   `"page"` (and optionally `"routine"`, the `### ` heading, default its name), so the docs check requires its Runbook
   exactly as it does for routines.tsv. `docs.py prompts` prints one pointer line per routine from both. A health Adoption
   rule `prompt-pointer` reads each installed scheduled-task prompt (`~/.claude/scheduled-tasks/<task>/SKILL.md`, the
   place `scheduled_task` already looks) and WARNs on any line that is not a pointer. Cost: small edits in existing scripts.

## Chosen
Approach 2. The pointer line is `In <repo>, fast-forward to origin/main, then read <wiki_dir>/<Page>.md's Runbook section
<routine> and follow it exactly.` `deployments.py` owns the routine list and the prompt text; `docs.py prompts` prints it;
`report.py` holds the health rule; `controls.py` and `rules.py` register its negative control. The Automation block row
for a custom routine already comes from `entries()`; it gains no new code. The AUT-1/2/3/4/8 wording changes are drafted
in DECISIONS.md under "Waiting on owner un-review", not applied to the Reviewed pages.

## Done line
A routine added to the config registry gets a schedule row (Automation block), a required Runbook (docs check) and a
generated one-line prompt (`docs.py prompts`); health warns on a prompt that holds steps (`prompt-pointer`). Python toy
`dev/toy/test-automation-routines.py` proves each, and each has a regression row seen red.

## Open questions
None. Scripts stay under 20,480 bytes and no file is added under skills/.
