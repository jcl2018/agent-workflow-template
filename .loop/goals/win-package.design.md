# Design: win-package

## Problem

`dev/package.py` gives a different verdict on native Windows than on Linux for the same commit (issue #1397). Three
causes: `os.walk` and `relpath` give backslash paths while every check compares forward-slash paths (so no SKILL.md is
found); with `core.autocrlf=true` the checkout holds CRLF, so script sizes count the extra bytes and the frontmatter
regex (`---\n`) never matches; and the subprocesses decode output with the locale code page (cp936 here), open the
README and flow file with it, and the `--help` runs inherit stdin with no timeout, so one waiting script stalls the run.

## Approaches

1. **Normalise at the edges of package.py (chosen).** `walk` returns `/` paths; `read` turns CRLF into LF for files that
   are text, which is what git stores and what Linux sees; every `open` and `subprocess.run` names UTF-8 (`errors=
   "replace"`), the `--help` child runs with `-X utf8`, `stdin=DEVNULL` and a timeout. Cost: about 15 changed lines in
   one file. Risk: a file committed with CRLF would be counted without it; none is committed so today (`git ls-files
   --eol` shows no `i/crlf`).
2. **Read the tree from git (`git ls-files`, `git cat-file`).** Exact parity with the committed blobs, but package.py
   must also check trees that are not git repos (test-package.sh copies the tree to a temp folder), so it needs two code
   paths. Higher cost and risk.

Chosen: 1, because it fixes every observed cause in one file and keeps the temp-copy tests working.

Also: the does-not-run-alone check copies the scripts folder once per folder instead of once per script, so the check is
bounded by spawn time, and a child that passes the timeout fails with `timed out`.

## Done lines

1. Non-UTF-8 locale verdict matches Linux: needs the path, CRLF and encoding fixes. Proven by a defect test that runs
   package.py on a CRLF copy of the tree under an ASCII locale (`PYTHONUTF8=0 PYTHONCOERCECLOCALE=0 LC_ALL=C`) with a
   script whose `--help` prints non-ASCII, and compares its FAIL lines with the same tree in LF.
2. Check finishes within 2 minutes: needs `stdin=DEVNULL` and the timeout. The same test plants a script whose `--help`
   reads stdin and runs package.py with an open pipe on stdin, under a bound.

## Open questions

None left for the owner.
