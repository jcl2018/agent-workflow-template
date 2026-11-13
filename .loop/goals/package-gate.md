# A pull request whose merged head breaks the package fails its lane (DEL-5, SET-3)

- Slug: package-gate
- Touches: skills/workflow-delivery/scripts, skills/workflow-regression/scripts, dev

## Done lines

Frozen. A wrong done line needs a new goal.

1. The PR lane fails when a script is over 20,480 bytes or the package has over 99 files, and passes on main

## Verify by hand

<!-- Numbered steps for a person, each with an Expect: line. A release needs this. -->

1. Run `python3 dev/toy/test-package-gate.py`.
   Expect: four control PASS lines and `PASS: head: this checkout's package passes ...`, exit 0.
2. Append 21,000 bytes of comment to any tracked script under skills/ and run it again.
   Expect: a `FAIL: head: Scripts: <file> is ... bytes` line and exit 1.
