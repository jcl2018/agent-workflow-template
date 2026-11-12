# lanes-abs-path: design

The goal line named `lanes.references()`; the real source is `narrow.scan()`: a quoted literal in a Python file that is an absolute folder (`"/private/tmp/x"`) goes through `os.path.join(root, lit)`, which returns the absolute path, `isdir` is true, and it joins the folders `lanes.walk()` walks. `references()` cannot produce an absolute path (its regex needs a name first), but it also skips one now, as the goal asks.

## Decisions
- Fix at the two places an absolute path can reach a join with the root: `narrow.scan` (the quoted-folder branch) and `lanes.references`. One guard each, 3 lines in all; no new file under skills/ (lanes.py 19824 of 20480 bytes).
- Per-file references are already cached per plan (`lanes.scan` and `narrow.scan` key on the file in `cache`), so no new cache; the walk of an outside folder was the cost.
- Proof: `dev/toy/test-lanes-abs-path.sh` runs the real analysis on a toy folder with a spy on `os.walk`; seen failing with main's lanes.py and narrow.py, passing with the fix. Reach of all 613 rows of this repo compared before and after: 0 differ.

## Done lines
1. Toy rows `lanes-abs-not-walked` and `lanes-abs-same-reach`, each seen red.
2. Same rows picked: 613 of 613 row reaches identical.
3. No new file under skills/.
