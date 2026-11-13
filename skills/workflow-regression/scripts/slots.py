#!/usr/bin/env python3
"""Lane slots and row-file locks. Imported by regression.py and lanes_cli.py; not a command. workflow-delivery's
lanekit.py holds exact copies of the pieces its lane.py uses (lanekit.COPIED, and EXIT_WAIT, EXIT_STALE, POLL), and
dev/toy/test-lane-control.sh fails when a copy differs from the function here: change both together.

The pool: `lane_limit` slots per machine (flow file, default 2, 0 is unlimited; LOOP_LANE_LIMIT overrides it) in
~/.workflow-loop/lanes (or $LOOP_LANES_DIR), a folder that must be yours and closed to others. Only a FULL lane takes a
slot, after it has planned; AFFECTED, REUSED, by-id and red runs never wait. It limits concurrent FULL regression lanes,
best effort, not the machine's load. Waiting lanes are served first in, first out by ticket files. A holder keeps a
flock on its slot file and its ticket, so a dead process frees both; slot files are never unlinked. A run inside a
slot holder (`_LOOP_LANE_HELD` names that slot, still locked by that pid) takes none, so a nested run never waits on
its own parent. `_LOOP_LANE_*` variables are internal: the lane sets them.
Row files (.loop/regression.tsv, .loop/regression-runs.tsv) are edited under locks in <git common dir>/loop/locks,
which serializes writers across every worktree of a repo. controls.py (throwaway control repos) and setup's seed write
them without the lock.
Exit codes, shared with lane.py: 0 pass, 1 fail, 2 lane-wait timeout, 3 no lane, 4 a hand run's slot wait timed out,
5 LANE_STALE, 124 time limit. Messages: workflow-regression/references/commands.md.
"""
import glob
import json
import os
import re
import subprocess
import sys
import time
try:
    import fcntl
except ImportError:  # native Windows: msvcrt byte-range locks under flock's names
    import msvcrt
    import types

    def _flock(handle, op):
        fd = handle if isinstance(handle, int) else handle.fileno()
        here = os.lseek(fd, 0, 1)
        os.lseek(fd, 0x7FFFFFFF, 0)  # one byte far past any content: readers never block
        try:
            while True:
                try:
                    return msvcrt.locking(fd, msvcrt.LK_UNLCK if op & 8 else msvcrt.LK_NBLCK, 1)
                except OSError:
                    if op & 8:
                        return  # unlock of a lock not held: a no-op, as with flock
                    if op & 4:
                        raise BlockingIOError("locked")
                    time.sleep(0.05)
        finally:
            os.lseek(fd, here, 0)

    fcntl = types.SimpleNamespace(LOCK_SH=1, LOCK_EX=2, LOCK_NB=4, LOCK_UN=8, flock=_flock)

# No terminal, no waiting: a prompt from git or gh must fail, not block.
os.environ.update(GIT_TERMINAL_PROMPT="0", GH_PROMPT_DISABLED="1", GIT_EDITOR="true", GIT_ASKPASS="true", SSH_ASKPASS="true")

EXIT_WAIT, EXIT_STALE, POLL = 4, 5, 2.0


def note(line):
    """An error or warning line: stderr, and the lane's note file when a lane runs this."""
    print(line, file=sys.stderr, flush=True)
    path = os.environ.get("_LOOP_LANE_NOTE")
    if path:
        try:
            with open(path, "a") as handle:
                handle.write(line + "\n")
        except OSError:
            pass


def flow_file():
    return os.path.expanduser(os.environ.get("LOOP_FLOW") or "~/.workflow-loop/flow.json")


def _flow():
    try:
        data = json.load(open(flow_file()))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def limit():
    """Lane slots on this machine: LOOP_LANE_LIMIT, else the flow file's lane_limit, else 2; 0 is unlimited."""
    raw, source = os.environ.get("LOOP_LANE_LIMIT"), "LOOP_LANE_LIMIT"
    if raw is None:
        raw, source = _flow().get("lane_limit"), flow_file()
        if raw is None:
            return 2
    if not isinstance(raw, bool) and str(raw).strip().isdigit():
        return int(str(raw).strip())
    note('NOTE: lane_limit "%s" from %s is not a whole number >= 0; using 2 lane slots.' % (raw, source))
    return 2


def time_limit(root):
    """A lane's time limit in seconds and its source: the flow file's limit, else step_limit, else 2700."""
    value = _flow().get("limit")
    if value:
        return float(value), "flow file limit"
    try:
        value = json.load(open(os.path.join(root, ".loop", "config.json"))).get("step_limit")
    except (OSError, ValueError, AttributeError):
        value = None
    return (float(value), "step_limit") if value else (2700.0, "the default")


def lanes_dir():
    return os.path.realpath(os.path.expanduser(os.environ.get("LOOP_LANES_DIR") or "~/.workflow-loop/lanes"))


def check(pool):
    """Create the pool 0700; refuse one that isn't yours or that others can write (OSError names why)."""
    os.makedirs(pool, mode=0o700, exist_ok=True)
    if os.name == "nt":  # no uid or group bits: the pool sits in the user's own profile, private by its ACL
        return
    info = os.stat(pool)
    if info.st_uid != getattr(os, "getuid", lambda: 0)() or info.st_mode & 0o022:
        raise OSError("not owned by you, or writable by group or others")


def _open(path, flags=0):
    return os.open(path, os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0) | flags, 0o600)


def _locked(fd):
    """True when another holder has this file locked."""
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        return True
    fcntl.flock(fd, fcntl.LOCK_UN)
    return False


def _read(path):
    try:
        with open(path) as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def port_base():
    """(fd, base) for a lane's own ports (REG-8): flock the first free port-N file (N 0..99) in the pool and return
    20000 + 100 * N, held while fd stays open; (None, why) when the pool is unavailable or all 100 are held."""
    try:
        pool = lanes_dir()
        check(pool)
        for number in range(100):
            fd = _open(os.path.join(pool, "port-%d" % number))
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                return fd, 20000 + 100 * number
            except BlockingIOError:
                os.close(fd)
    except OSError as error:
        return None, "port pool unavailable: %s" % error
    return None, "no port lease free (100 in use)"


def held(pool):
    """A nested run: _LOOP_LANE_HELD names this pool's slot, still locked by the pid it names."""
    parts = os.environ.get("_LOOP_LANE_HELD", "").rsplit(":", 2)
    if len(parts) != 3 or os.path.realpath(parts[0]) != pool or not parts[1].isdigit():
        return False
    path = os.path.join(pool, "slot-%s" % parts[1])
    if not os.path.isfile(path):
        return False
    fd = _open(path)
    try:
        return _locked(fd) and str(_read(path).get("pid")) == parts[2]
    finally:
        os.close(fd)


def holders(pool):
    found = []
    for path in sorted(glob.glob(os.path.join(pool, "slot-*"))):
        info = _read(path)
        fd = _open(path)
        try:
            busy = _locked(fd)
        finally:
            os.close(fd)
        if info and busy:
            found.append("%s since %s" % (str(info.get("label", "?"))[:80],
                                          time.strftime("%H:%M", time.localtime(info.get("since", 0)))))
    return found


def last_change(pool):
    """The newest slot-file change: the queue clock (any slot taken restarts a waiting lane's span)."""
    times = [os.path.getmtime(path) for path in glob.glob(os.path.join(pool, "slot-*"))]
    return max(times) if times else 0.0


def _counter(pool):
    return open(os.path.join(pool, "counter.lock"), "a+")


def _ticket(pool, label):
    """Take a ticket: created as .tmp, flocked by its holder, renamed into place, all under the counter lock."""
    with _counter(pool) as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        lock.seek(0)
        seq = int((lock.read().strip() or "0").splitlines()[-1]) + 1
        lock.truncate(0)
        lock.write(str(seq))
        lock.flush()
        name = os.path.join(pool, "ticket-%09d" % seq)
        fd = _open(name + ".tmp", os.O_EXCL)
        fcntl.flock(fd, fcntl.LOCK_EX)
        os.write(fd, json.dumps({"label": label[:80], "pid": os.getpid(), "since": time.time()}).encode())
        os.rename(name + ".tmp", name)
    return seq, fd, name


def _first(pool):
    """The lowest live ticket; dead tickets (no lock held) are swept under the counter lock."""
    with _counter(pool) as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        for path in sorted(glob.glob(os.path.join(pool, "ticket-*"))):
            fd = _open(path)
            try:
                if _locked(fd):
                    if not path.endswith(".tmp"):
                        return int(os.path.basename(path)[7:])
                elif not path.endswith(".tmp") or time.time() - os.path.getmtime(path) > 10:
                    os.unlink(path)
            finally:
                os.close(fd)
    return None


def _slot(pool, count, label):
    for index in range(count):
        fd = _open(os.path.join(pool, "slot-%d" % index))
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            os.close(fd)
            continue
        os.ftruncate(fd, 0)
        os.write(fd, json.dumps({"label": label[:80], "pid": os.getpid(), "since": time.time()}).encode())
        return fd, index
    return None, None


def started():
    """Mark the lane's start once: a row's nested run sees the outer lane's marker and leaves its clock alone."""
    path = os.environ.get("_LOOP_LANE_STARTED")
    if path and not os.path.exists(path):
        open(path, "w").close()


def acquire(root, label, planned_head, unclean):
    """Hold a slot for a FULL lane (or none: unlimited, nested, pool unavailable), recheck the plan, mark the start."""
    count = limit()
    if count == 0:
        return started()
    pool = lanes_dir()
    try:
        check(pool)
        if held(pool):
            return started()
        seq, ticket, name = _ticket(pool, label)
    except OSError as error:
        note("LANE_SLOTS_UNAVAILABLE: %s: %s; running without a slot. Fix: chmod 700 %s, or set LOOP_LANES_DIR to a "
             "writable folder." % (pool, error.strerror or error, pool))
        return started()
    queued, began, told, fd = os.environ.get("_LOOP_LANE_QUEUED"), time.time(), 0.0, None
    seconds = time_limit(root)[0]
    try:
        while fd is None:
            try:
                if _first(pool) == seq:
                    fd, index = _slot(pool, count, label)
            except OSError as error:
                note("LANE_SLOTS_UNAVAILABLE: %s: %s; running without a slot. Fix: chmod 700 %s, or set LOOP_LANES_DIR to "
                     "a writable folder." % (pool, error.strerror or error, pool))
                return started()
            if fd is not None:
                break
            busy = "; ".join(holders(pool)) or "the next waiter"
            if time.time() - told > 300:
                told = time.time()
                line = ("LANE_WAIT: %d of %d lane slots busy (%s); this full lane waits its turn and starts when one frees. "
                        "To skip the pool for this run: LOOP_LANE_LIMIT=0" % (count, count, busy))
                print(line, flush=True)
                if queued:
                    with open(queued, "w") as handle:
                        handle.write(line + "\n")
            if not queued and not sys.stdin.isatty() and time.time() - began > 4 * seconds:
                note("LANE_WAIT_TIMEOUT: waited %ds for a lane slot (%s); nothing ran. Fix: run the same command again "
                     "later, or set LOOP_LANE_LIMIT=0 for this run to skip the pool" % (time.time() - began, busy))
                sys.exit(EXIT_WAIT)
            time.sleep(POLL)
    finally:
        os.close(ticket)
        for path in (name, queued):
            try:
                os.unlink(path) if path else None
            except OSError:
                pass
    os.environ["_LOOP_LANE_HELD"] = "%s:%d:%d" % (pool, index, os.getpid())
    recheck(root, planned_head, unclean)
    started()
    return fd


def recheck(root, planned, unclean):
    """After a wait, the plan must still match: same HEAD, no new changes in the worktree."""
    import lanes
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True).stdout.strip()
    if head != planned:
        note("LANE_STALE: HEAD moved while queued (planned %s, now %s); no rows ran. Fix: run the same command again to "
             "plan on %s" % (planned[:12], head[:12], head[:12]))
        sys.exit(EXIT_STALE)
    new = sorted(set(lanes.dirty(root)) - set(unclean))
    if new:
        note("LANE_STALE: the worktree changed while queued (%s); no rows ran. Fix: commit or revert those paths, then "
             "run the same command again" % ", ".join(new[:5]))
        sys.exit(EXIT_STALE)


def _lock_path(root, name):
    done = subprocess.run(["git", "rev-parse", "--git-common-dir"], cwd=root, capture_output=True, text=True)
    if done.returncode:
        sys.exit("REFUSED: %s is not in a git repo, so its row files can't be locked. Fix: run this inside the repo." % root)
    folder = os.path.join(os.path.abspath(os.path.join(root, done.stdout.strip())), "loop", "locks")
    try:
        os.makedirs(folder, exist_ok=True)
    except OSError:
        pass
    return os.path.join(folder, name + ".lock")


def edit(root, name, change):
    """Run change() under the row file's lock: it re-reads and writes the file itself, so no writer loses another's edit."""
    path = _lock_path(root, name)
    try:
        handle = open(path, "w")
    except OSError as error:
        sys.exit("REFUSED: cannot lock .loop/%s: %s (%s); nothing was written. Fix: make %s writable and rerun the same "
                 "command." % (name, os.strerror(error.errno or 0), path, os.path.dirname(path)))
    with handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        return change()


def write_table(path, header, lines):
    temp = "%s.%d.tmp" % (path, os.getpid())
    with open(temp, "w") as handle:
        handle.write(header + "".join(line + "\n" for line in lines))
    os.replace(temp, path)


def lane_limit(held):
    """(seconds, source) of a lane's time limit."""
    return held["limit"], held.get("source", "flow file limit")


def timeout_line(text, why, held):
    """The LANE_TIMEOUT line."""
    return ("LANE_TIMEOUT: %s; the lane was killed, rows partly ran, nothing committed or pushed. Fix: run the same "
            "command again, or raise the flow file \"limit\" (else step_limit)." % why)


def rows_line(text, ran, log):
    """The LANE line's end (DX-12, DX-18 ROWS): the goal tier's ROWS counts, the selected rows a timeout left unfinished,
    and the lane log."""
    found = re.search(r"^ROWS: (\d+) selected (\(.*?\)), (\d+) reused; unmapped: (\d+)$", text, re.M)
    if not found:
        return "; log: %s" % log
    count, parts, reused, loose = found.groups()
    return "; rows: %s selected %s, %s reused, %d unfinished; unmapped: %s; log: %s" % (
        count, parts, reused, max(int(count) - ran, 0), loose, log)


# The summary job of the regression workflow: one combined summary after every shard (REG-4, REG-7); actions.py embeds it.
SUMMARY_JOB = r"""  summary:
    needs: regression
    if: always()
    runs-on: ubuntu-latest
    timeout-minutes: 10
    permissions:
      contents: read
      issues: write
      pull-requests: read
    steps:
      - uses: actions/checkout@v4
        with:
          persist-credentials: false
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Download every shard's results
        continue-on-error: true
        uses: actions/download-artifact@v4
        with:
          pattern: results-*
          path: ${{ runner.temp }}/shards
      - name: Write one run summary, one table per feature
        continue-on-error: true
        env:
          GH_TOKEN: ${{ github.token }}
          SHARDS: "@SHARDS@"
        run: |
          here=$(mktemp -d)
          cat > "$here/tests.py" <<'TESTS_PY_EOF'
@TESTS@
          TESTS_PY_EOF
          all="$here/results.tsv"; : > "$all"
          reported=0
          for f in "$RUNNER_TEMP"/shards/*/regression-results.tsv; do
            [ -f "$f" ] || continue
            reported=$(( reported + 1 )); cat "$f" >> "$all"
          done
          [ "$reported" -gt 0 ] || rm -f "$all"  # no shard left results: the plain fallback says so
          started=$(sed -n 's/^# started //p' "$all" 2>/dev/null | sort -n | head -n 1 || true)
          case "$started" in ''|*[!0-9]*) started=$(date +%s) ;; esac  # never an expression
          unrun=$(grep -c '^# unrun ' "$all" 2>/dev/null || true); unrun=${unrun:-0}
          timeout 120 python3 -I "$here/tests.py" issues --write >/dev/null || true
          took=$(( $(date +%s) - started ))
          {
            GH_TOKEN= python3 -I "$here/tests.py" summary --results "$all" --took "$took" || {
              printf '## Regression\n\nThe grouped summary could not be written; see this step'"'"'s log.\n\n| Test | Result |\n|---|---|\n'
              grep -v '^#' "$all" 2>/dev/null | awk -F'\t' '{print "| " $1 " | " $2 " |"}'
            }
            printf '\nSHARDS %s of %s reported. UNRUN %s (rows skipped for out of job time).\n' "$reported" "$SHARDS" "$unrun"
          } | tee -a "$GITHUB_STEP_SUMMARY"  # the run's log shows the counts too
"""
