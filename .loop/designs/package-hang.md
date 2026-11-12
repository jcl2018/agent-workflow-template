# Design: package-hang

Status: idea for the plan step. It meets the frozen done lines in `.loop/goals/package-hang.md` and changes none of them.

## Problem

On 2026-11-12 eight `dev/package.py` runs from toy tests and lanes sat for 1 to 9 hours, each holding a shared
regression slot until the operation session killed them.

## Cause (reproduced)

`check_scripts` runs every shipped script as `python3 -E -s <copy>/scripts/<name>.py --help` to prove it runs alone. The
child inherits package.py's stdin and has no time limit. `skills/workflow-monitoring/scripts/govern_hook.py` ignores
`--help` and reads its hook JSON from stdin (`json.load(sys.stdin)`). A lane or a toy test that starts package.py with
stdin on a pipe that is never closed therefore blocks forever on that one child. With stdin on `/dev/null` the same run
finishes in about 10 seconds; with `sleep 200 | package.py` it never finishes on main. A per-script probe found
govern_hook.py the only script that blocks; `dev/toy/test-plan-cache.sh` already passes `</dev/null` to work around it.

## Approach (all in `dev/package.py`)

1. Every child gets `stdin=/dev/null`, a time limit (`PACKAGE_CHILD_SECONDS`, else 30) and its own process group, which
   is killed when the limit is hit. A script that times out is refused by name: `FAIL Scripts: <script> --help did not
   finish in N seconds with no stdin`.
2. A hard bound on the whole run (`--timeout`, else `PACKAGE_TIMEOUT`, else 300 seconds) through `SIGALRM`. When hit,
   it kills the running child's process group, prints one line `TIMEOUT: package.py stopped after N seconds waiting on
   <what>` and exits 3. Each phase names what it waits on (the walk, a copy, a script's --help, git, the ZIP).
3. `copytree(..., symlinks=True)`, so a looping symlink in a scripts folder is copied as a link, never followed. The walk
   already does not follow links.
4. `git remote get-url` gets `/dev/null` stdin and the child limit.

Because package.py always exits within its bound and kills its children's groups on the way out, no lane slot is held by
a package.py run past the bound.

## Test

`dev/toy/test-package-hang.sh`, store-free and network-free, on a small synthetic package:
- `stdin`: a script that reads its JSON from stdin (like govern_hook.py), run under an open stdin pipe: the run finishes
  and the script is refused by name. On main it hangs (the harness limit fires).
- `bound`: a script that sleeps and starts a grandchild, with `--timeout 3`: exit 3, one TIMEOUT line naming the script's
  --help, and no grandchild left. On main, `--timeout` is unknown.
- `loop`: a looping symlink in a scripts folder does not hang the run.

## What stays out

- govern_hook.py is not changed (skills/ is outside this goal's touches); package.py no longer depends on its stdin.
- No new file under skills/.
