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

1. Run `python3 skills/workflow-delivery/scripts/goal.py queue x --goal g --done d --level standard`.
   Expect: it is refused with a line naming 0, 1 and 2.
2. Run `LOOP_DESIGN_SKILL=nothing python3 skills/workflow-delivery/scripts/goal.py judge <a level 2 slug> --design`.
   Expect: it prints `DESIGN REVIEW: built-in (skill nothing not found)`.

## Design

Levels become "0", "1", "2" in goal.py, watch.py, monitor.py, board.py and release.py. Every level starts at design;
level 0 has no judge, level 1 judges, level 2 also requires a design review. `--level` uses a type that refuses the old
names with a line naming 0, 1 and 2; queue lines with an old or unknown level are skipped with the same line. Risky
paths raise 0 to 1. The design skill name comes from LOOP_DESIGN_SKILL or ~/.workflow-loop/design-skill, outside the
repo; if its SKILL.md is found it is added to the review prompt, else the built-in prompt runs, and `judge --design`
prints which. Risk: goal.py's 20 KB test cap (raised to 21 KB), and toy tests keyed on old names (remapped).

## Plan

1. Change the level code in the five scripts; check with dev/toy/test-goal.sh, test-board.sh, test-release.sh.
2. Add toy tests for the refusal and the design-skill setting (done lines 1, 3).
3. Rewrite SKILL files, wiki pages, README, ROADMAP, loop-files (done line 5) and grep for old names.
4. Run `goal.py check` (done line 6).

## Evidence

`grep -nE "minimum|quick|standard|full" listing.json docs/wiki/Release.md docs/wiki/Monitoring.md README.md docs/ROADMAP.md` finds
nothing: those files use no old level names (listing.json and Release.md are untouched because they never held them).
The only old-name hits in touched docs are the refusal lines in docs/wiki/Delivery.md and skills/workflow-delivery/SKILL.md.
