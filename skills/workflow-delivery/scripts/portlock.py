"""flock on every platform: fcntl's own where it exists, msvcrt byte-range locks on Windows.

usage: import portlock as fcntl   then fcntl.flock(fd_or_file, fcntl.LOCK_EX | fcntl.LOCK_NB) as on POSIX.

On Windows the lock is one byte far past any content, so readers of a locked file are never blocked; a blocking lock
polls until it is free, LOCK_NB raises BlockingIOError, and closing the handle frees it, as with flock.
"""
try:
    from fcntl import LOCK_EX, LOCK_NB, LOCK_SH, LOCK_UN, flock  # noqa: F401
except ImportError:  # Windows
    import msvcrt
    import os
    import time

    LOCK_SH, LOCK_EX, LOCK_NB, LOCK_UN = 1, 2, 4, 8
    AT = 0x7FFFFFFF

    def flock(handle, op):
        fd = handle if isinstance(handle, int) else handle.fileno()
        here = os.lseek(fd, 0, os.SEEK_CUR)
        os.lseek(fd, AT, os.SEEK_SET)
        try:
            if op & LOCK_UN:
                try:
                    msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
                except OSError:
                    pass  # not held: flock's unlock is a no-op too
                return
            while True:
                try:
                    msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
                    return
                except OSError:
                    if op & LOCK_NB:
                        raise BlockingIOError("locked by another holder")
                    time.sleep(0.05)
        finally:
            os.lseek(fd, here, os.SEEK_SET)


if __name__ == "__main__":
    print(__doc__.strip())
