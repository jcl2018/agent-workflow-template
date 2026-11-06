# Add a board page ready to publish as an Artifact, honoring a manual theme

- Slug: board-artifact-page
- Level: standard
- Touches: skills/workflow-monitoring/scripts/board.py, skills/workflow-monitoring/references/operation.md, dev/toy/test-board.sh

## Done lines

Frozen. A wrong done line needs a new goal.

1. board.py also writes board-artifact.html without doctype, html, head or body tags, starting with the title and style
2. Both pages use theme tokens that follow prefers-color-scheme and a manual data-theme setting of dark or light
3. references/operation.md says to publish board-artifact.html, and dev/toy/test-board.sh proves the page's tags and theme rules
4. The repo checks pass

## Verify by hand

<!-- One or more numbered steps a person can follow, each with an Expect: line. Every release needs this. -->

## Design

## Plan
