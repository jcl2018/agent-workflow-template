# Replace goal level names with numbers, and give every level a design

- Slug: numbered-levels-2
- Level: standard
- Touches: skills/workflow-delivery, skills/workflow-monitoring, skills/workflow-release, skills/workflow-regression, skills/loop-files.md, listing.json, dev/toy, docs/wiki/Delivery.md, docs/wiki/Monitoring.md, docs/wiki/Release.md, README.md, docs/ROADMAP.md

## Done lines

Frozen. A wrong done line needs a new goal.

1. Levels are 0, 1 and 2, and 0 is the default for go, queue lines and goal.py; the names minimum, quick, standard and full are refused with a line naming the new levels
2. Level 0 runs design, plan, build, checks and pull request, with no judge; level 1 adds one fresh judge after the build and before the pull request; level 2 adds a design review before the build
3. At level 2 the skill reads an optional private setting, the file ~/.workflow-loop/design-skill or the variable LOOP_DESIGN_SKILL, naming a design-review skill to use; with none set or the skill missing it uses the built-in design review, and it says which ran; the setting is never stored in the repo
4. A risky path raises a goal to level 1 at least
5. The SKILL files, the wiki pages named in touches, README and listing.json use only the numbered levels, and a grep for the old names as level values finds nothing outside the refusal and its tests
6. The repo checks pass

## Verify by hand

<!-- One or more numbered steps a person can follow, each with an Expect: line. Every release needs this. -->

## Design

## Plan
