# Goals stop only for real failures: a rule added mid-goal, a format slip, a finished goal's finding or an in-session restart no longer stop or stall a goal (issues 147, 148, 149, 157, 121, 160)

- Slug: loop-guards
- Touches: skills/workflow-delivery, skills/workflow-monitoring, dev/toy, .loop/regression.tsv, docs/wiki

## Done lines

Frozen. A wrong done line needs a new goal.

1. A reply-format rule added after a step started applies only to steps that start after it lands, and its refusal names the rule and the release that added it (147)
2. A refused record that changes nothing (format, wrong HEAD) does not use a try; it prints the fix and leaves the goal running (148)
3. goal.py resume SLUG resets a stopped or failed goal in the session that owns it, logging who asked and why, with no headless worker (149)
4. goal.py touches SLUG --add PATH widens a goal's touches with a logged reason, and goal.py finding on a finished goal records it without stopping it (157)
5. Binding a worker session sets LOOP_ROLE=worker for it, or the refusal says exactly how (121)
6. The worktree-isolation hook allows edits in the goal worktree bound to the session (160)
7. A toy test proves each guard, seen failing on the old code; the issues close when this merges

## Verify by hand

<!-- Numbered steps for a person, each with an Expect: line. A release needs this. -->
