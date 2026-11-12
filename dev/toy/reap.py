#!/usr/bin/env python3
"""Find and stop the processes a toy test started, by an environment marker they all inherit.

usage: reap.py list VAR=VALUE                 print "<pid> <ppid> <argv>" for each own process with that exact env entry
       reap.py reap VAR=VALUE [--label NAME]   TERM, then KILL, up to 5 rounds; exit 1 with a REAP line if any is left
       reap.py sweep [--dry-run] [--marker V]  stop processes whose TOY_REAP_ID names a test shell that is gone;
                                              without --marker only markers of this lane (TOY_REAP_LANE, else the
                                              _LOOP_LANE_LABEL hash, else hand), never another lane's (issue 435)
       reap.py format LABEL MARKER PID:ARGV... print the REAP line for those survivors (used by the defect test)
Any other command or option, or an option missing its value, prints this text and exits 2.

Only processes of the current user are looked at. The marker must be a whole environment entry: the same text
in a command line or inside another variable's value never matches. The caller and its ancestors are never
touched. On macOS environments come from sysctl KERN_PROCARGS2; on Linux from /proc/<pid>/environ. A process
whose environment can't be read is printed by `list` as "UNREADABLE <pid> <why>" (exit 3); a zombie counts as gone.
macOS shows an empty environment for system binaries (/bin/sleep, /bin/bash); such a process matches only while
an ancestor carries the marker, so stand-ins should run a non-system bash or python3, as the toy tests do.
"""
import ctypes
import ctypes.util
import errno
import hashlib
import os
import re
import signal
import subprocess
import sys
import time

ROUNDS, WAIT = 5, 0.5
LINUX = os.path.isdir("/proc/self") and sys.platform.startswith("linux")
_libc = None


def fail(why, hint):
    sys.stderr.write("REAP: cannot list processes: %s. Fix: %s\n" % (why, hint))
    sys.exit(1)


def table():
    """{pid: (ppid, start, zombie)} for every process of this user."""
    uid, out = os.getuid(), {}
    if LINUX:
        for name in os.listdir("/proc"):
            if not name.isdigit():
                continue
            try:
                if os.stat("/proc/" + name).st_uid != uid:
                    continue
                with open("/proc/%s/stat" % name) as f:
                    rest = f.read().rsplit(")", 1)[1].split()
            except OSError:
                continue
            out[int(name)] = (int(rest[1]), rest[19], rest[0] == "Z")
        return out
    try:
        text = subprocess.run(["ps", "-ax", "-o", "pid=,ppid=,uid=,stat=,lstart="], capture_output=True,
                              text=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError) as e:
        fail("ps failed (%s)" % e, "check that ps runs in this shell")
    for line in text.splitlines():
        cells = line.split(None, 4)
        if len(cells) == 5 and cells[2] == str(uid):
            out[int(cells[0])] = (int(cells[1]), cells[4].strip(), cells[3].startswith("Z"))
    return out


def procargs(pid):
    """(argv, env) of a process, or raise OSError."""
    if LINUX:
        with open("/proc/%d/environ" % pid, "rb") as f:
            env = f.read().split(b"\0")
        try:
            with open("/proc/%d/cmdline" % pid, "rb") as f:
                argv = f.read().split(b"\0")
        except OSError:
            argv = []
        return [a.decode("utf-8", "replace") for a in argv if a], [e.decode("utf-8", "replace") for e in env if e]
    global _libc
    if _libc is None:
        _libc = ctypes.CDLL(ctypes.util.find_library("c"), use_errno=True)
    size = ctypes.c_size_t(1 << 20)
    buf = ctypes.create_string_buffer(size.value)
    mib = (ctypes.c_int * 3)(1, 49, pid)  # CTL_KERN, KERN_PROCARGS2
    if _libc.sysctl(mib, 3, buf, ctypes.byref(size), None, ctypes.c_size_t(0)) != 0:
        code = ctypes.get_errno()
        raise OSError(code, os.strerror(code))
    raw = buf.raw[:size.value]
    if len(raw) < 4:
        raise OSError(errno.EIO, "short procargs")
    argc = int.from_bytes(raw[:4], sys.byteorder)
    parts = raw[4:].split(b"\0")
    i = 1  # skip the exec path
    while i < len(parts) and parts[i] == b"":
        i += 1
    argv = parts[i:i + argc]
    env = []
    for item in parts[i + argc:]:
        if item == b"":
            break
        env.append(item)
    return [a.decode("utf-8", "replace") for a in argv], [e.decode("utf-8", "replace") for e in env]


def guarded(procs):
    """The caller and its ancestors."""
    keep, pid = set(), os.getpid()
    while pid and pid not in keep:
        keep.add(pid)
        pid = procs.get(pid, (0,))[0]
    return keep


def started_at(start):
    """A process's start as epoch seconds, from table()'s start field, or None if it can't be read."""
    try:
        if LINUX:
            with open("/proc/stat") as f:
                boot = next(int(line.split()[1]) for line in f if line.startswith("btime "))
            return boot + int(start) / os.sysconf("SC_CLK_TCK")
        return time.mktime(time.strptime(start, "%a %b %d %H:%M:%S %Y"))
    except (OSError, ValueError, StopIteration):
        return None


def since_of(marker):
    """The epoch a toy marker was made (reap.sh's toy-PID-EPOCH-..., test-no-leftovers' outer-PID-EPOCH-N), or None."""
    m = re.search(r"=[a-z]+-\d+-(\d{9,})-", marker)
    return int(m.group(1)) if m else None


def find(test, procs=None, since=None):
    """[(pid, start, argv, ppid)] whose environment passes test(env), plus [(pid, why)] live unreadable. With since
    (epoch seconds), an unreadable process that started before it is left out: it can't carry a marker made later,
    as a CI runner's own processes, whose environments the runner user may not read (EACCES), never do."""
    procs = table() if procs is None else procs
    keep, hits, unread, hidden, other = guarded(procs), [], [], [], set()
    for pid, (ppid, start, zombie) in sorted(procs.items()):
        if pid in keep or zombie:
            continue
        try:
            argv, env = procargs(pid)
        except OSError as e:
            other.add(pid)
            began = started_at(start) if since is not None else None
            if began is None or began >= since - 60:  # a minute's slack for clock steps
                unread.append((pid, start, errno.errorcode.get(e.errno, str(e.errno))))
            continue
        if test(env):
            hits.append((pid, start, argv, ppid))
        elif not env:  # macOS hides a system binary's environment (/bin/sleep, /bin/bash): judged by its parent
            hidden.append((pid, start, argv, ppid))
        else:
            other.add(pid)
    marked = {h[0] for h in hits}
    for pid, start, argv, ppid in hidden:  # judged by the nearest ancestor whose environment is known
        up, seen = ppid, 0
        while up > 1 and seen < 64 and up not in marked and up not in other:
            up, seen = procs.get(up, (0,))[0], seen + 1
        if up in marked:
            hits.append((pid, start, argv, ppid))
    if unread:  # a process that ended while being read is gone, not unreadable
        now = table()
        unread = [(p, why) for p, s, why in unread if live(now, p, s)]
    return hits, unread


def live(procs, pid, start):
    now = procs.get(pid)
    return bool(now) and now[1] == start and not now[2]


def wait_gone(pairs):
    until = time.time() + WAIT
    while time.time() < until:
        procs = table()
        if not any(live(procs, p, s) for p, s in pairs):
            return
        time.sleep(0.05)


def short(argv):
    return " ".join(argv)[:80]


def signal_all(hits, sig):
    procs = table()
    for pid, start, _argv, _ppid in hits:
        if live(procs, pid, start):
            try:
                os.kill(pid, sig)
            except (ProcessLookupError, PermissionError):
                pass


def stop(test):
    """Rounds of TERM then KILL; returns the survivors."""
    hits, _ = find(test)
    for n in range(ROUNDS):
        if not hits:
            return []
        signal_all(hits, signal.SIGTERM if n == 0 else signal.SIGKILL)
        wait_gone([(p, s) for p, s, _a, _q in hits])
        hits, _ = find(test)
    return hits


def reap_line(label, marker, left):
    pids = " ".join(str(p) for p, _a in left)
    return ("REAP: %s %s: %d left after %d rounds: %s. Fix: kill -9 %s, or bash dev/toy/reap.sh --sweep-dead after "
            "this test's shell exits." % (label, marker, len(left), ROUNDS,
                                          ", ".join("%s (%s)" % (p, a[:80]) for p, a in left), pids))


def entry_is(want):
    return lambda env: want in env


def usage():
    sys.stderr.write(__doc__)
    sys.exit(2)


def options(args, flags, valued):
    """{option: value} for args made only of FLAGS and VALUED options (each with a value); else a usage error."""
    out, i = {}, 0
    while i < len(args):
        if args[i] in flags:
            out[args[i]] = True
        elif args[i] in valued and i + 1 < len(args) and not args[i + 1].startswith("--"):
            out[args[i]] = args[i + 1]
            i += 1
        else:
            usage()
        i += 1
    return out


def main(argv):
    signal.signal(signal.SIGPIPE, signal.SIG_IGN)
    if not argv:
        usage()
    cmd, args = argv[0], argv[1:]
    try:
        if cmd == "list" and len(args) == 1 and "=" in args[0]:
            hits, unread = find(entry_is(args[0]), since=since_of(args[0]))
            for pid, _s, a, ppid in hits:
                print("%d %d %s" % (pid, ppid, short(a)))
            for pid, why in unread:
                print("UNREADABLE %d %s" % (pid, why))
            return 3 if unread else 0
        if cmd == "reap" and args and "=" in args[0]:
            label = options(args[1:], (), ("--label",)).get("--label", "toy test")
            left = stop(entry_is(args[0]))
            if left:
                sys.stderr.write(reap_line(label, args[0], [(p, short(a)) for p, _s, a, _q in left]) + "\n")
                return 1
            return 0
        if cmd == "format" and len(args) >= 3:
            print(reap_line(args[0], args[1], [tuple(x.split(":", 1)) for x in args[2:]]))
            return 0
        if cmd == "sweep":
            opts = options(args, ("--dry-run",), ("--marker",))
            return sweep(opts.get("--dry-run", False), opts.get("--marker"))
    except BrokenPipeError:
        return 1
    usage()


def own_lane():
    """This lane's id, as reap.sh puts it in every marker: TOY_REAP_LANE, else the label's hash, else hand."""
    label = os.environ.get("_LOOP_LANE_LABEL")
    return os.environ.get("TOY_REAP_LANE") or (hashlib.sha1(label.encode()).hexdigest()[:8] if label else "hand")


def ours(marker, only):
    """A marker this sweep may judge: exactly --marker when given, else one ending in this lane's id."""
    return marker == only if only is not None else marker.endswith("-L" + own_lane())


def owner_gone(env, only):
    for item in env:
        m = re.match(r"TOY_REAP_ID=(toy-(\d+)-\S+)$", item)
        if m and ours(m.group(1), only):
            try:
                os.kill(int(m.group(2)), 0)
            except ProcessLookupError:
                return m.group(1)
            except PermissionError:
                return None
    return None


def sweep(dry, only):
    procs = table()
    hits, _ = find(lambda env: any(re.match(r"TOY_REAP_ID=toy-\d+-", e) and ours(e[len("TOY_REAP_ID="):], only)
                                   for e in env), procs)
    verdict, hidden, targets = {}, [], []
    for pid, _s, _a, _q in hits:
        try:
            env = procargs(pid)[1]
        except OSError:
            continue
        if env:
            verdict[pid] = owner_gone(env, only)
        else:
            hidden.append(pid)
    for pid in hidden:  # a hidden-env hit (see find) takes the verdict of its nearest marked ancestor
        up, seen = procs.get(pid, (0,))[0], 0
        while up > 1 and seen < 64 and up not in verdict:
            up, seen = procs.get(up, (0,))[0], seen + 1
        verdict[pid] = verdict.get(up)
    for pid, start, _a, ppid in hits:
        if pid not in verdict:
            continue
        marker = verdict[pid]
        if marker:
            targets.append((pid, start, marker))
        else:
            print("SKIP %d (owner pid alive)" % pid)
    for pid, _s, marker in targets:
        print("%s %d %s" % ("WOULD SWEEP" if dry else "SWEPT", pid, marker))
    if dry:
        print("WOULD SWEEP %d" % len(targets))
        return 0
    wanted = {(p, s) for p, s, _m in targets}
    left = stop_set(wanted)
    print("SWEPT %d" % (len(targets) - len(left)))
    if left:
        sys.stderr.write("SWEEP: %d left: %s\n" % (len(left), " ".join(str(p) for p, _s in left)))
        return 1
    return 0


def stop_set(wanted):
    """Stop exactly these (pid, start) processes; returns the survivors."""
    hits = [(p, s, [], 0) for p, s in wanted]
    for n in range(ROUNDS + 1):
        procs = table()
        hits = [h for h in hits if live(procs, h[0], h[1])]
        if not hits or n == ROUNDS:
            break
        signal_all(hits, signal.SIGTERM if n == 0 else signal.SIGKILL)
        wait_gone([(p, s) for p, s, _a, _q in hits])
    return [(p, s) for p, s, _a, _q in hits]


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
