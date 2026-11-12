# Design: routine-runbooks

Goal: `.loop/goals/routine-runbooks.md` (3 frozen done lines). A Codex scheduled run once sent a fixture dry run instead of the real newsletter, because nothing told it what a full run is. An agent given only "run routine X" must be able to read one page that says so.

## Approach

The feature page that owns a routine carries an optional `## Runbook` section, placed after Usage. One `### <routine>` subsection per routine, each with seven fields as `- **Field:** text` lines: Serves (PRD ids), Schedule, Steps, Full run, Output, Never, Check. It follows the Deployments pattern: rules in `template.md`, a pure format function in `pageformat.py`, hooked from `criteria.py`'s page contract.

A small registry, `.loop/routines.tsv` (`routine<TAB>page`), says which routine each page owns. `docs.py check` fails a registered routine whose page has no `### routine` runbook, and any Runbook missing a field or holding loose text.

Two runbooks are written for this repo: `health-round` on Health (check, file, judge, digest, mail) and `regression-round` on Regression. Each was written from the workflows as they are (`health.yml`, `regression.yml`), not from memory.

## Decisions

- Registry as a `.loop` file, not a third column of `docs.tsv`: other readers split `docs.tsv` on its first tab and would glue the new column onto the last path. Not a setting either: setup is held by another goal, and a registry is repo data.
- The Runbook is not part of the PRD review fingerprints, so an agent can correct it as it learns without un-reviewing the requirements (the owner's own words: add the exact correction there).
- Every field is required with at least 12 characters. The check cannot judge whether a text is true; it judges that the full-run and output fields exist. Truth is for the owner's review of the page and for the `repo` test, which asserts the shipped runbooks say a full run is live and a fixture never stands in.
- No new file under skills/ (the package is at 99 of 100): the code went into `pageformat.py`, `criteria.py`, `deployments.py` (rules) and `template.md`.
- DOC-16 on the Documentation page and AUT-8 on the Automation page, both Unreviewed, are for the owner to review. DOC-15 is settings-table's, so DOC-16 here. Documentation then holds 15 requirements, which is `criteria_max`; settings-table's DOC-15 makes 16, so whichever merges second raises `criteria_max` in `.loop/config.json` to 16.

## Done lines

1. Format and check: `pageformat.runbook` and `pageformat.owed`; toy cases good, refused, registry, locked.
2. Health and Regression runbooks; the registry names both; toy case repo.
3. Toy tests only under dev/toy; file count stays 99.
