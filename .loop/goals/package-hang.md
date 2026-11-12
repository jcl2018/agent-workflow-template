# dev/package.py never hangs: on 2026-11-12 eight package.py runs from toy tests and lanes (with --root/--out under temp folders) sat for 1 to 9 hours, holding the shared regression slots until the operation session killed them; the cause is found (stdin wait, lock, walk of a huge or looping tree, or a child that never exits) and fixed so every run finishes or fails within a bounded time with a clear message. PRD: Delivery

- Slug: package-hang
- Touches: dev/package.py, dev/toy, .loop/regression.tsv, docs/wiki/Tests.md

## Done lines

Frozen. A wrong done line needs a new goal.

1. the hang is reproduced in a toy test, seen failing (timing out) on current main and passing on the fix
2. package.py has a hard time bound and exits non-zero with one line naming what it waited on when hit
3. no lane slot can be held by a package.py run past that bound
4. no new file under skills/

## Verify by hand

<!-- Numbered steps for a person, each with an Expect: line. A release needs this. -->
