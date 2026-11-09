# Show each feature page's Usage as what the owner asks the agent (a skill command or a plain request), not as script files

- Slug: usage-as-skills
- Touches: docs/wiki, skills/workflow-docs, README.md, dev/toy

## Done lines

Frozen. A wrong done line needs a new goal.

1. Every Usage line on every feature page is written as an agent request, a skill command such as /workflow-monitoring operate or /workflow-delivery go "goal" --done "line", or a plain-words request such as "start a goal to add caching", with what it does in a few words; no Usage line names a script file or a python command
2. Each skill's SKILL.md maps each of those commands to the script routine it runs under the hood, so asking the agent runs exactly that routine
3. The docs check fails a feature page whose Usage names a .py or .sh file, and a toy test proves it; docs check and health stay green

## Verify by hand

<!-- One or more numbered steps a person can follow, each with an Expect: line. Every release needs this. -->
