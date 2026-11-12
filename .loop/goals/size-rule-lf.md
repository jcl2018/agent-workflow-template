# Make health's size and skill-lines rules and dev/package.py's Scripts rule measure committed (LF) bytes and lines, not the CRLF working tree, so Windows checkouts get the same verdict as Linux (https://github.com/jcl2018/agent-workflow-template/issues/3125)

- Slug: size-rule-lf
- Touches: skills/workflow-health/scripts, dev/package.py

## Done lines

Frozen. A wrong done line needs a new goal.

1. On a Windows CRLF checkout, workflow-health check reports exactly the size and skill-lines findings that Linux reports for the same commit
2. No new files under skills/, and every script stays at most 20,480 bytes

## Verify by hand

<!-- Numbered steps for a person, each with an Expect: line. A release needs this. -->
