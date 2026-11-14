# Design: package-rows-tracked

## Problem
Four package rows fail in every pr lane on this Windows PC, for reasons outside the goal being delivered. `package-caps-held`
says the tree ships 187 files and `package-headroom-held` says 180, when the real package is 98: `dev/package.py`'s `walk`
(and the headroom toy's own `os.walk`) count every file on disk, including `__pycache__/*.pyc` and lane output that git
ignores. `package-gate-head` and `settings-render-fresh` fail with no reason because their commands end in `grep -q`, which
swallows the toy's output, so the lane shows a bare FAIL.

## Approaches
1. Keep the disk walk and skip more names (`.pyc`, lane output). Cheap, but it needs a new skip for every kind of loose file
   and can hide a real stray file a pull request adds.
2. Walk what git tracks: `walk` asks `git ls-files` (the shipped paths) when the root is the top of a git checkout and
   falls back to the disk walk elsewhere, so a loose package is still checked. Cost: one git call; risk: a tracked file
   missing from disk (skipped) and a root inside another repo (falls back).
Chosen: 2. It is what the ZIP would hold if built from the commit, and the headroom toy counts through `package.walk`, so
the two cannot disagree. A tracked forbidden folder (`vendor`, `node_modules`) still fails.

Rows: `package-gate-head` runs `test-package-gate.py head` (the toy now takes `controls` or `head`, and `PACKAGE_GATE_ROOT`
for a stand-in checkout) so its exit status is the answer and the lane prints the `FAIL: head: <rule>: <text>` lines;
`settings-render-fresh` loses its `-q` so the STALE lines print.

## Done line
- The four rows pass on a clean origin/main and with 90 loose `.pyc` files added: `dev/toy/test-package-tracked.py`
  (seen red before the fix, green after).
- A real breach (a tracked script of 20,480 bytes) fails the head row and names the script; a stale page prints its STALE line.

## Open questions
None for the owner. `dev/package.py` was already over 20,000 bytes before this change; it grew by about 1 KB.
