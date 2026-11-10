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

1. In a toy repo (`bash dev/toy/test-guards.sh /tmp/guards g2` builds one and leaves it), record a step whose reply has no
   DEPTH line: `LOOP_ROLE=worker python3 skills/workflow-delivery/scripts/goal.py record <slug> plan --file reply.txt --in-session`.
   Expect: `REFUSED (no try used): plan refused: no DEPTH line (rule depth-line, added in v0.12.1)`, exit 2, and the
   goal still running with tries 0 (`goal.py show <slug>`).
2. Mark a session goal stopped, then run `python3 skills/workflow-delivery/scripts/goal.py resume <slug> --why "check"` from the main checkout.
   Expect: `RESUMED <slug> at <step>`, status running, tries 0, and `resumed by operation session: check` in its log.
3. Run `python3 skills/workflow-delivery/scripts/goal.py record <slug> idea --file x` without LOOP_ROLE.
   Expect: a `REFUSED` line naming the goal's session, its worktree and `LOOP_ROLE=worker python3 .../goal.py record <slug> idea --file x`.
4. Run `python3 skills/workflow-monitoring/scripts/sessions.py bind <slug> <id> --cwd /tmp`.
   Expect: `REFUSED: session folder /tmp is outside the goal worktree ... (CWD_OUTSIDE)`; without `--cwd`, a `WORKTREE <slug>: <path>` line.

## Closes

Closes #147
Closes #148
Closes #149
Closes #157
Closes #121
Refs #160 (line 6 as the owner chose (a): bind/assign hand over the worktree and refuse a known outside folder; the
desktop app's own edit guard is out of the template's reach, so this issue stays open)
