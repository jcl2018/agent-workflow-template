#!/bin/bash
# reads: skills/
# reads: skills/workflow-regression/scripts/slots.py skills/workflow-delivery/scripts/lanekit.py
# reads: skills/workflow-monitoring/scripts/session_bind.py skills/workflow-setup/scripts/update.py
# Native Windows has no fcntl: each skill's lock module falls back to msvcrt byte-range locks. This hides fcntl, plants a fake
# msvcrt and checks the fallback in all four skills: a held lock makes LOCK_NB raise BlockingIOError, a free one is taken,
# unlock never raises, and the file position is put back. usage: test-portlock.sh
here=$(cd "$(dirname "$0")/../.." && pwd)
. "$here/dev/toy/reap.sh"
fails=0
for pair in workflow-regression:slots workflow-delivery:lanekit workflow-monitoring:session_bind workflow-setup:update; do
  skill=${pair%%:*}; mod=${pair##*:}
  out=$(cd "$here/skills/$skill/scripts" && python3 - "$mod" <<'PY' 2>&1
import importlib, os, sys, tempfile, types
for name in ("subprocess", "shlex", "signal", "glob", "json", "re", "hashlib", "io", "zipfile", "contextlib", "argparse", "datetime", "time"):
    importlib.import_module(name)  # the real standard library first: a planted msvcrt would make it think this is Windows
sys.modules["fcntl"] = None  # import fcntl -> ImportError, as on Windows
held = set()
fake = types.ModuleType("msvcrt")
fake.LK_UNLCK, fake.LK_NBLCK = 0, 2
def locking(fd, mode, n):
    if mode == fake.LK_NBLCK:
        if fd in held:
            raise OSError("locked")
        held.add(fd)
    else:
        held.discard(fd)
fake.locking = locking
sys.modules["msvcrt"] = fake
f = importlib.import_module(sys.argv[1]).fcntl
with tempfile.TemporaryFile() as handle:
    handle.write(b"abc"); handle.seek(1)
    f.flock(handle, f.LOCK_EX | f.LOCK_NB)
    assert handle.fileno() in held and os.lseek(handle.fileno(), 0, 1) == 1, "lock not taken or position moved"
    try:
        f.flock(handle, f.LOCK_EX | f.LOCK_NB)
        raise SystemExit("a held lock did not raise")
    except BlockingIOError:
        pass
    f.flock(handle, f.LOCK_UN)
    f.flock(handle, f.LOCK_UN)  # not held: a no-op
    assert not held
print("ok")
PY
)
  if [ "$out" = ok ]; then echo "PASS: $skill falls back to msvcrt locks when fcntl is missing"; else echo "FAIL: $skill: $out"; fails=$((fails + 1)); fi
done
[ "$fails" = 0 ] && echo "ALL PASS" || { echo "$fails FAILED"; exit 1; }
