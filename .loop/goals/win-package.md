# Make dev/package.py give the same verdict on Windows as on Linux (issue #1397)

- Slug: win-package
- Touches: dev/package.py

## Done lines

Frozen. A wrong done line needs a new goal.

1. On Windows with a non-UTF-8 locale, python dev/package.py on main reports no failure that it does not report on Linux for the same commit
2. On Windows the does-not-run-alone check finishes within 2 minutes

## Verify by hand

1. On Windows, run `PYTHONUTF8=0 python dev/package.py` from a checkout with `core.autocrlf=true`.
   Expect: no "no SKILL.md" lines, no script reported over 20 KB for its CRLF bytes, no UnicodeDecodeError, and it ends within 2 minutes.
2. Run `bash dev/toy/test-package-win.sh`.
   Expect: `PASS: parity`, `PASS: no-stdin`, `ALL PASS`.
