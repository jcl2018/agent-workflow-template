# dev/package.py passes on main: scripts at most 20,480 bytes, at most 99 files, every script standalone (#3800, SET-3)

- Slug: package-pass
- Touches: skills, dev

## Done lines

Frozen. A wrong done line needs a new goal.

1. dev/package.py exits 0 on the merged head, and a script over 20,480 bytes or a 100th file makes it fail

## Verify by hand

<!-- Numbered steps for a person, each with an Expect: line. A release needs this. -->
