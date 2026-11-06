# Fix the wiki's two errors and record proof for the judge

- Slug: project-wiki-2
- Level: standard
- Touches: docs/wiki, .loop/goals/project-wiki-2.md, dev/toy

## Done lines

Frozen. A wrong done line needs a new goal.

1. docs/wiki/Documentation.md names the init command and what it does, matching skills/workflow-docs/SKILL.md
2. docs/wiki/Home.md says dev/toy/test-monitoring.sh exists but was not re-run after the commands changed, and that dev/toy/test-goal.sh covers monitoring logic
3. The goal file's Evidence section holds the real output of: every SKILL.md command heading, each script's --help, ls dev dev/toy, and the FINDINGS.md or DECISIONS.md line behind each Home claim
4. Each command and flag on the feature pages appears in that evidence, and any that does not is removed from the page
5. dev/toy/test-goal.sh and dev/toy/test-release.sh pass with LOOP_BATCH=1 set in the environment
6. The repo checks pass

## Verify by hand

<!-- One or more numbered steps a person can follow, each with an Expect: line. Every release needs this. -->

## Design

## Plan
