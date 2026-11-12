# Plan: package-hang

## Implementation plan

Design: `.loop/designs/package-hang.md`. Every change is in `dev/package.py` and `dev/toy/`; no file under `skills/`.

1. **Children never wait on stdin or forever** (`dev/package.py`).
   - `run_alone(cmd, cwd, what)`: `Popen` with `stdin=DEVNULL`, captured output, `start_new_session=True`, and
     `communicate(timeout=CHILD_SECONDS)`; on timeout, `killpg(SIGKILL)` and refuse the script by name.
   - `CHILD_SECONDS` from `PACKAGE_CHILD_SECONDS`, else 30.
   - `check_scripts` uses it for each `--help` run; `manifest`'s `git remote get-url` gets `/dev/null` stdin and the limit.
2. **A hard bound on the whole run.** `--timeout`, else `PACKAGE_TIMEOUT`, else 300 seconds, through `signal.alarm`. The
   handler kills the current child's process group, prints `TIMEOUT: package.py stopped after N seconds waiting on <what>`
   once, and exits 3. `wait_on()` names each phase: the walk of each shipped path, the copy of a script's folder, a
   script's --help, git, writing the ZIP, and each check group.
3. **No looping copy.** `copytree(..., symlinks=True)`.
4. **Toy test** `dev/toy/test-package-hang.sh` with cases `stdin`, `bound` and `loop` (as in the design), store-free and
   network-free, each run under a harness limit so a hang reads as a failure, not a stuck lane.
5. **Rows** (`.loop/regression.tsv`), each seen failing on main's `package.py` with `regression.py red`:
   - `package-hang-stdin` (done line 1): `bash dev/toy/test-package-hang.sh stdin`;
   - `package-hang-bound` (done lines 2 and 3): `bash dev/toy/test-package-hang.sh bound`;
   - `package-hang-loop` (done line 1): `bash dev/toy/test-package-hang.sh loop` (if main hangs here; otherwise kept as
     a guard).
   Then `criteria.py render` for `docs/wiki/Tests.md`.
6. **Checks.** `bash dev/test-package.sh`, the existing package rows (sync-*, pods-*, plan-cache), `docs.py check`.
7. **Before `goal.py pr`.** Merge origin/main last; VERSION as the repo's release step sets it. Push with the hooks, no
   bypass. Stop at the PR.

## Review record

- Plan review: CEO 8 findings (3 High), Eng 14 (1 High); the outside voice was unavailable. Folded in as items 8-14,
  which override items 1-7 where they differ. CEO F1 and F8 and Eng F14 are outside this goal's touches and go to the PR
  as follow-ups.

## Amendments after review

8. **Why package.py is the layer.** `regression.py run` already gives rows `/dev/null` stdin and kills each row's tree at
   900 s, so the 1-9 hour holds came from runs outside that path (toy tests and lanes that start package.py with an open
   stdin pipe, as `test-plan-cache.sh`'s `</dev/null` workaround shows). Fixing package.py covers every caller.
9. **Signal-safe stop.** One `stop()` path for the time bound and for SIGTERM/SIGINT/SIGHUP: a reentry guard, kill the
   current child's group, remove a `.part` ZIP and the lone scripts copy, write the one line with `os.write`, `os._exit`.
   SIGTERM exits 128+15 with `STOPPED: package.py got signal 15 while waiting on <what>`. An inherited ignore of SIGINT or
   SIGHUP (nohup) is kept.
10. **No escape window.** Stop signals are blocked with `pthread_sigmask` while a child starts and is recorded. After a
    kill, `communicate` waits at most 5 s, then closes the pipes, so a detached grandchild never turns one script's
    failure into a whole-run wait.
11. **Windows.** No SIGALRM: a daemon `threading.Timer` takes the same stop path. Children start in a new process group
    and are killed with `taskkill /T /F`.
12. **The ZIP** is written to a `mkstemp` `.part` file beside `--out` and renamed, so concurrent runs never share a name
    and a stopped run leaves no half ZIP. `--timeout` 0 or less is refused with exit 2.
13. **Tests.** Add a `child` case (a `--help` that sleeps, cut at `PACKAGE_CHILD_SECONDS=2` and refused by name) and a
    `term` case (an outside SIGTERM stops the run with one line and no child left). Sleepers carry a per-run token, and
    each case proves its sleeper started before asserting none is left. The `loop` case also asserts no traceback; it is
    a guard (main does not hang there), and the PR says so.
14. **The PR** lists every behavior change: the `--timeout` flag, `PACKAGE_TIMEOUT` and `PACKAGE_CHILD_SECONDS`, exit 3
    and 128+N, the TIMEOUT and STOPPED lines, `/dev/null` stdin for children, symlinks kept in copies, and the `.part`
    file. Follow-ups: govern_hook.py should answer `--help` (skills/workflow-monitoring), and `regression.py criteria` and
    `red` should bound their children the same way (skills/workflow-regression).
