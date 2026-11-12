# Finish Windows support left after #2616: replace os.getuid, os.killpg and os.kill(pid, 0) in workflow-health workflows.py and workflow-setup update.py with the portable helpers (proctree, portlock), and bring workflow-delivery private.py back under the 20,480-byte cap

- Slug: win-posix-rest
- Touches: skills/workflow-health/scripts, skills/workflow-setup/scripts/update.py, skills/workflow-delivery/scripts/private.py

## Done lines

Frozen. A wrong done line needs a new goal.

1. no script under skills/ calls os.getuid, os.killpg or os.kill(pid, 0) outside proctree, and the Windows-safe rows pass on native Windows
2. every script under skills/ is at most 20,480 bytes

## Verify by hand

<!-- Numbered steps for a person, each with an Expect: line. A release needs this. -->

1. Run `bash dev/toy/test-portable.sh` on native Windows Python and on Linux or macOS.
   Expect: every line reads PASS and the last line reads ALL PASS, including the lines for the calls outside proctree, the health helpers and the 20480-byte cap.
2. Run `python skills/workflow-delivery/scripts/private.py check` and `private.py where`.
   Expect: both print their usual lines (a pattern count; WORKER or NOT A WORKER) with no traceback.
