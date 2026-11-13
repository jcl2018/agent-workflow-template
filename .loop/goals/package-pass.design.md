# Design: package-pass

## Problem
`dev/package.py` fails on main (#3800, SET-3): `fit.py` is 22,994 bytes and `lane.py` 20,561 (cap 20,480), the shipped tree is
102 files (cap 99, counting listing.json, README.md and LICENSE), and `render.py --help` exits 2 so it "does not run alone".

## Approaches
1. Raise the caps. Refused by the goal: the caps are the contract.
2. Cut prose and merge small helpers into existing ones, changing no behaviour. Cost: importer edits and a re-render of generated pages.

## Choice
Approach 2.
- fit.py and lane.py: shorten docstrings and drop section comments (fit.py 20,134, lane.py 20,435 bytes).
- render.py: `--help` prints the usage and exits 0.
- Files, 102 to 99: `session_bind.py` into `worker.py` (sessions.py imports worker; it already did lazily, and has the same stdin guard);
  `default-flow.md` into delivery's `references/commands.md` (flow.py reads the `## step` sections from there); `start.md` into docs'
  `references/commands.md` (entry.py reads the `## Loop` ... `## Settings` sections from there). Same text, same behaviour.
- A Python toy, `dev/toy/test-package-caps.py`, proves a 20,480-byte script and a 100th file fail, and the real tree passes both caps.

## Done lines
1. `dev/package.py` exits 0 on the merged head: PASS, 99 files.
2. A script over the cap or a 100th file fails: the toy.

## Open questions
- fit.py (346 bytes) and lane.py (45 bytes) have almost no room; another goal that adds to them will break the package again. Recommended: a later goal that splits them.
DEPTH: condensed
