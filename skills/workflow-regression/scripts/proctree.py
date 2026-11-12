"""Stop a whole process tree, and tell whether a pid runs, on every platform.

usage: import proctree   then proctree.kill(pid, signal.SIGTERM) for a child started with start_new_session=True,
and proctree.alive(pid) on Windows.

POSIX: kill is os.killpg, so the child's whole session goes. Windows has no process group a signal reaches (and
os.kill(pid, 0) there sends Ctrl+C), so kill runs taskkill /T /F, which stops the child and every process it started,
and alive asks the process's exit code. Either kill is quiet when the tree is already gone.
"""
import os
import subprocess

if os.name == "nt":
    import ctypes

    def kill(pid, sig=None):
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(int(pid))], stdin=subprocess.DEVNULL,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def alive(pid):
        try:
            pid = int(pid)
        except (TypeError, ValueError):
            return False
        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        handle = k32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
        if not handle:
            return ctypes.get_last_error() == 5  # access denied: it runs, as EPERM on POSIX
        code = ctypes.c_ulong()
        try:
            return bool(k32.GetExitCodeProcess(handle, ctypes.byref(code))) and code.value == 259  # STILL_ACTIVE
        finally:
            k32.CloseHandle(handle)
else:
    import signal

    def kill(pid, sig=signal.SIGKILL):
        try:
            os.killpg(pid, sig)
        except OSError:  # already gone
            pass


if __name__ == "__main__":
    print(__doc__.strip())
