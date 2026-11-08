# Make Setup adopt any repo and ship as an updatable package, as SET-1 to SET-5 say

- Slug: setup-adopt
- Touches: skills/workflow-setup, dev, listing.json, VERSION, README.md, skills/loop-files.md

## Done lines

Frozen. A wrong done line needs a new goal.

1. One setup command, run in a new or existing repo, prints what it found and what it would add or convert, then writes on a branch the loop config, feature pages with criteria and tests, milestones, the regression workflow and the health rules, adapting existing files instead of overwriting them
2. The package is built with its version number and every skill, works by copying into any SKILL.md agent, and keeps every script under 20 KB
3. An update command in an installed repo shows the newer version and what changed, and updates the skills without touching the repo's config, criteria, docs or private settings
4. A design guide in the package explains how the loop, operation and workers, criteria and tests, regression and health fit together
5. A toy test proves adopting a fresh toy repo and updating it, and the repo checks pass

## Verify by hand

<!-- One or more numbered steps a person can follow, each with an Expect: line. Every release needs this. -->
