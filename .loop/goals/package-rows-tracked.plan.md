# Plan: package-rows-tracked

Checked against the code: `dev/package.py` has `walk(root)` (called once, in `main`), `SHIPPED`, `BAD_DIRS`, `check_files`
(fails a path ending in `/` as a forbidden folder); `dev/toy/test-package-caps.py` and `test-package-gate.py` call
`package.walk`; `test-package-headroom.py` counted with its own `os.walk`; rows `package-caps-held`, `package-headroom-held`,
`package-gate-head` and `settings-render-fresh` are in `.loop/regression.tsv`. Other users of package.py (test-adopt.sh,
test-package-hang.sh) run it on temp trees that are not git checkouts, so they keep the disk walk.

## Steps
1. `dev/toy/test-package-tracked.py`: controls first, run red. Loose `__pycache__`, `.pyc` and a stray file must not change
   `walk`; a non-git folder still walks the disk; a tracked `vendor/` still fails; a tracked file deleted from disk is not
   walked; headroom and caps pass with 90 loose `.pyc` files; the gate's head part fails a tracked 20,480-byte script and
   prints `FAIL: head: Scripts: <path> is ...`; the four rows have no `grep -q` over their toy's output.
2. `dev/package.py`: `tracked(root)` (`git rev-parse --show-prefix` empty, then `git ls-files -z -- SHIPPED`, files that
   exist) and `walk` uses it, else the old disk walk. A tracked path under a `BAD_DIRS` folder also lists the folder.
3. `test-package-headroom.py` counts with `package.walk`; `test-package-gate.py` takes `controls` or `head` and
   `PACKAGE_GATE_ROOT`.
4. `.loop/regression.tsv`: `package-gate-head` runs `test-package-gate.py head`; `settings-render-fresh` drops `-q`; a new
   row `package-rows-tracked` runs the toy (seen_red 2026-11-13). Render the Tests tables (`criteria.py render`).

## Test for the done line
The four rows pass on this checkout and with loose files added (the new toy, red before step 2 with 5 FAILs, green after);
the gate row fails with its reason on a tracked cap breach.

## Could break
A package folder that is a git checkout with an index that does not match disk (the tracked list wins; deleted files are
skipped). `git` missing from PATH falls back to the disk walk.

## Out of scope
Making the lane delete `__pycache__`; the lane runner's output rules (workflow-regression); other rows with `grep -q`.
