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
1. Run `bash dev/toy/test-package-hang.sh`.
   Expect: `ALL PASS` in under a minute (stdin, child, bound, loop and term cases).
2. Run `sleep 120 | python3 dev/package.py --out /tmp/p.zip` (stdin is a pipe that stays open).
   Expect: package.py prints its usual PASS or FAIL lines and exits within about 15 seconds, while `sleep` keeps the pipe open; on main it never finishes.
3. Run `python3 dev/package.py --timeout 1 --out /tmp/p.zip`.
   Expect: exit 3 and one line `TIMEOUT: package.py stopped after 1 seconds waiting on <phase>`, and no `/tmp/p.zip` or `.part` file.

## Behavior changes

- `dev/package.py` runs each script's `--help` with stdin on `/dev/null`, in its own process group, with a limit
  (`PACKAGE_CHILD_SECONDS`, default 30). A script that reads stdin now fails fast as "does not run alone"; one that never
  ends is refused as "--help did not finish in N seconds".
- New hard bound for the whole run: `--timeout N`, else `PACKAGE_TIMEOUT`, else 300 seconds. When hit: exit 3 and one line
  `TIMEOUT: package.py stopped after N seconds waiting on <what>`. `--timeout` of 0 or less is refused with exit 2.
- SIGTERM, SIGINT and SIGHUP kill the running child's group and exit 128+N with one `STOPPED:` line; an inherited ignore
  (nohup) is kept. On Windows a timer thread gives the same bound and `taskkill /T /F` ends the child's tree.
- The ZIP is written to a temporary `.part` file beside `--out` and renamed, so a stopped run leaves no half ZIP.
- Script folders are copied with symlinks kept as links (never followed).

## Notes for review

- **Cause.** `check_scripts` ran every shipped script with `--help` on the caller's stdin and with no limit.
  `skills/workflow-monitoring/scripts/govern_hook.py` ignores `--help` and reads its hook JSON from stdin, so a lane or toy
  test that started package.py with an open stdin pipe blocked forever. A probe of all 80 scripts found it the only one.
  `regression.py run` already gives rows `/dev/null` stdin and a 900 s tree kill, so the holds came from callers outside
  that path; fixing package.py covers them all.
- **Seen failing on main.** Rows package-hang-stdin, -bound and -slot each failed with main's package.py swapped in (the
  stdin case hangs until the harness limit; main has no `--timeout`). The `loop` case passes on main too; it is a guard.
- **Pre-existing on main, not from this goal:** `dev/test-package.sh` reports 5 wrong, because the real tree is refused
  (103 files, over the 99 limit, and command `automation` missing from listing.commands). The same output appears on main.
- **Follow-ups, outside this goal's touches:** govern_hook.py should print usage and exit on `--help`
  (skills/workflow-monitoring); `regression.py criteria` and `red` should bound their children the same way
  (skills/workflow-regression).
- No file under skills/ changed or was added.
