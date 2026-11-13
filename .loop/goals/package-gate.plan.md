# Plan: package gate

Checked against the code: `walk`, `check_files`, `check_scripts` and `failures` exist in dev/package.py and are
importable without side effects; the 99-file and 20,480-byte rules are its own.

## Build steps
1. dev/toy/test-package-gate.py: controls on a synthetic package, then the head's tracked files.
2. Rows package-gate-controls (DEL-5) and package-gate-head (SET-3) in .loop/regression.tsv, each seen red.

## Test per done line
`package-gate-head` fails on a head with a script over the cap and passes on main; `package-gate-controls` shows each rule
(size, file count, standalone) fails a package.

## What could break
The head row is slow (about 20 s: one `--help` run per script). A package with a failure outside these three rules is
still package.py's to report (the package-passes row).

## Out of scope
Changing package.py or the lane code; the Windows skip of package-passes.
