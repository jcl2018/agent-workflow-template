# Any agent (Claude or Codex) given only "run routine X" does the full job, because the feature page that owns each routine carries a "Runbook" section an agent must read first: the PRD lines it serves, the schedule, the exact steps or command, what a FULL run is (live sources, real output, never a dry run or fixture on a scheduled run), the one output and where it goes (for example one email to the agent account), the forbidden shortcuts, and how to check the run was real; the repo's Automation section links each routine to its runbook (owner, 2026-11-11: "they would like to know the PRD and the exact prompt I guess what I have passed before is not enough. They probably need to read the GitHub page again. So I wanted to the documentation to have a delivery session ... I wanted to add the exact correction there.")

- Slug: routine-runbooks
- Touches: skills/workflow-docs, dev/toy, .loop/regression.tsv, docs/wiki/Documentation.md, docs/wiki/Automation.md, docs/wiki/Health.md, docs/wiki/Regression.md, docs/wiki/Tests.md

## Done lines

Frozen. A wrong done line needs a new goal.

1. the page format gains an optional Runbook section with the fields above; docs.py check fails a routine in the registry whose page has no Runbook, and a Runbook missing the full-run or output fields
2. the template's Health and Regression pages carry Runbooks for the 4-hourly check, judge and digest, and the regression digest; an automation prompt reduces to "read the <page> Runbook and follow it exactly"
3. toy tests prove the check; no new file under skills/

## Verify by hand

<!-- Numbered steps for a person, each with an Expect: line. A release needs this. -->
