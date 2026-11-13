# A resumed goal keeps its release ask: with auto_merge on, a goal set to ask waits for the owner after a resume (#812)

- Slug: resume-ask-honored
- Touches: skills/workflow-release/scripts, skills/workflow-delivery/scripts, skills/workflow-monitoring/scripts, dev/toy

## Done lines

Frozen. A wrong done line needs a new goal.

1. A goal set to ask, resumed with auto_merge on, stops before merge with the ask shown, and an unresumed one still merges

## Verify by hand

<!-- Numbered steps for a person, each with an Expect: line. A release needs this. -->

1. Run `python3 dev/toy/test-resume-ask.py`.
   Expect: four PASS lines for the prompts and the worker step, then two more PASS lines, and exit 0.
2. With auto_merge on, read `mend.release_text({"slug": "g", "release": "ask"})`.
   Expect: the text asks "Cut a release or leave it unreleased?" and never names merge.py.
