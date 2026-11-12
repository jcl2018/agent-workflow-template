# Plan: pr-body-file

Checked against the code: the `--body` argument sites are goal.py:417 (via `run`), merge.py:182 (`autorelease.sh`),
health automation.py (4, via `rounds.gh`), file.py (3, via `run`/`args_of`), mail.py:298 (`rounds.gh`), regression
runs.py (2, `gh`) and actions.py (2, `write`). Release notes (autorelease.py:267, release.py:374) already use
`--notes-file`. sync.py already uses `--body-file`. Script sizes: goal.py 20,465 and merge.py 20,475 bytes (cap 20,480),
so those two must not grow; fit.py (18,980), autorelease.py (15,752), rounds.py (16,591) have room. No new file under
skills/ (99-file cap).

## Build steps
1. fit.py: `pr_create(g, state, body)` writes the body to a temp file, runs `gh pr create ... --body-file`, removes
   it. goal.py calls it and drops its inline `--body` (net shrink).
2. autorelease.py: `sh_body(args, text, cwd)` appends `--body-file` + temp file (UTF-8, removed in `finally`); the
   existing notes-file code in `publish` uses it too. merge.py `start` calls it (net shrink).
3. health: `rounds.gh(*args, body=None)`; automation.py, mail.py pass `body=`. file.py `run(args, root, body=None)`;
   `args_of` returns the body apart from the args. regression: `runs.gh(*args, body=None)`; actions.py `write(...)`
   takes `body=`.
4. Fakes read `--body-file`: fakegh/gh, fakegh/fake.py (issue edit/comment), release-gh.py, stubs in
   test-automation.sh, test-automation-email.sh, test-regression.sh, test-milestones.sh.
5. New toy test dev/toy/test-body-file.sh (`# windows: ok`, Python only): every wrapper, with a 40,000-character
   body, runs a subprocess stub that fails any argument over 8,000 characters and checks `--body-file` content equals
   the body and the temp file is gone; and no `"--body"` literal followed by a text in skills/.
6. Regression row `pr-body-file` (level land) seen red on the base, then green.

## Tests per done line
Done line 1 → row `pr-body-file` runs test-body-file.sh: red before (the wrappers and `fit.pr_create` do not exist /
`--body` is an argument), green after.

## Could break
Fakes in the bash toy tests (skipped on Windows; they run on CI); a temp file left behind on an exception (removed in
`finally`); encoding (write UTF-8 explicitly); the 20,480-byte cap (checked with the size rule).

## Out of scope
`gh issue close --comment` (short fixed text), `--title`, and sync.py (already `--body-file`).
