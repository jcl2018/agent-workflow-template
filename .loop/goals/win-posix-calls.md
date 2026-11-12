# Make lanes, slots and step timeouts work on native Windows Python (issue #1396): no os.getuid, os.O_NOFOLLOW or os.killpg crash

- Slug: win-posix-calls
- Touches: skills/workflow-delivery/scripts, skills/workflow-monitoring/scripts, skills/workflow-regression/scripts

## Done lines

Frozen. A wrong done line needs a new goal.

1. On Windows, lanekit.port_base() and slots.port_base() return a port base instead of raising AttributeError
2. On Windows, a step or child stopped for a timeout or a mend takes its whole process tree with it
3. On Linux the regression land tests still pass

## Verify by hand

<!-- Numbered steps for a person, each with an Expect: line. A release needs this. -->
