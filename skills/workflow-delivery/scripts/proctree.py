"""Stop a whole process tree, and ask about a pid, on every platform.

usage: import proctree   then proctree.kill(pid, signal.SIGTERM) for a child started with start_new_session=True,
proctree.probe(pid) where os.kill(pid, 0) was (ProcessLookupError when gone), proctree.pstart(pid) for the process's
start time (a reused pid reads differently), and proctree.alive(pid) on Windows.

POSIX: kill is os.killpg, so the child's whole session goes; pstart is ps. Windows has no process group a signal
reaches (and os.kill(pid, 0) there sends Ctrl+C, os.getuid and ps do not exist), so kill runs taskkill /T /F, which stops
the child and every process it started, and alive and pstart ask the process itself. Either kill is quiet when gone.
"""
import json
import os
import shutil
import subprocess
import tempfile
import zlib

if os.name == "nt":
    import ctypes

    def _k32():
        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        k32.OpenProcess.restype = ctypes.c_void_p  # a HANDLE: pointer-sized, never truncated to an int
        k32.CloseHandle.argtypes = [ctypes.c_void_p]
        k32.GetExitCodeProcess.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_ulong)]
        k32.GetProcessTimes.argtypes = [ctypes.c_void_p] + [ctypes.POINTER(ctypes.c_ulonglong)] * 4
        return k32

    def kill(pid, sig=None):
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(int(pid))], stdin=subprocess.DEVNULL,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def alive(pid):
        try:
            pid = int(pid)
        except (TypeError, ValueError):
            return False
        k32 = _k32()
        handle = k32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
        if not handle:
            return ctypes.get_last_error() == 5  # access denied: it runs, as EPERM on POSIX
        code = ctypes.c_ulong()
        try:
            return bool(k32.GetExitCodeProcess(handle, ctypes.byref(code))) and code.value == 259  # STILL_ACTIVE
        finally:
            k32.CloseHandle(handle)

    def pstart(pid):
        k32 = _k32()
        handle = k32.OpenProcess(0x1000, False, int(pid))
        if not handle:
            return ""
        times = [ctypes.c_ulonglong() for _ in range(4)]  # creation, exit, kernel, user
        try:
            return str(times[0].value) if k32.GetProcessTimes(handle, *[ctypes.byref(t) for t in times]) else ""
        finally:
            k32.CloseHandle(handle)

    def probe(pid):
        if not alive(pid):
            raise ProcessLookupError(pid)
else:
    import signal

    def kill(pid, sig=signal.SIGKILL):
        try:
            os.killpg(pid, sig)
        except OSError:  # already gone
            pass

    def probe(pid):
        os.kill(pid, 0)

    def pstart(pid):
        return subprocess.run(["ps", "-o", "lstart=", "-p", str(pid)], capture_output=True, text=True).stdout.strip()


def alive_since(pid, start=""):
    """A pid that runs, is no zombie and, given a start, still began then."""
    try:
        probe(pid)
    except PermissionError:
        pass
    except (OSError, TypeError):
        return False
    if start and pstart(pid) != start:
        return False
    return os.name == "nt" or subprocess.run(["ps", "-o", "stat=", "-p", str(pid)], capture_output=True, text=True).stdout.strip()[:1] != "Z"


def tmp_for(top, slug, name):
    """REG-8: prefix of the lane's temp folder, outside every checkout; "" when the system temp is in one."""
    root = here = os.path.realpath(tempfile.gettempdir())
    while not os.path.lexists(here + "/.git") and os.path.dirname(here) != here:
        here = os.path.dirname(here)
    return "" if os.path.lexists(here + "/.git") else "%s/loop-lane-%08x-%s-%s-" % (root, zlib.crc32(os.path.realpath(top).encode()), slug, name)


def rm_tmp(held):
    path = (held or {}).get("tmp") or ""
    if os.path.basename(path).startswith("loop-lane-") and not os.path.islink(path):
        shutil.rmtree(path, ignore_errors=True)


FLOW_FILE = "~/.workflow-loop/flow.json"
NO_FLOW = ("no skill flow is set. Fix: write %s naming your idea, plan, review, test and ship skills and their "
           "unattended command (loop-files.md)." % FLOW_FILE)
FLOW = ("idea", "plan", "review", "qa", "ship")
TEMPLATE = """# {goal}

- Slug: {slug}
- Touches: {touches}

## Done lines

Frozen. A wrong done line needs a new goal.

{done}

## Verify by hand

<!-- Numbered steps for a person, each with an Expect: line. A release needs this. -->
"""


def flow_set():
    try:
        spec = json.load(open(os.path.expanduser(os.environ.get("LOOP_FLOW") or FLOW_FILE)))
        steps = dict(spec.get("suite") or {}, **(spec.get("steps") or {}))
    except (OSError, ValueError, AttributeError, TypeError):
        return False
    return all(steps.get(step) for step in FLOW)


if __name__ == "__main__":
    print(__doc__.strip())
