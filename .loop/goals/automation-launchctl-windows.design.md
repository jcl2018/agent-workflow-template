# Design: automation-launchctl-windows

Problem: `docs.py automation` calls `launchctl list` (and `gh run list`) with no guard, so on Windows the missing program raises FileNotFoundError and the command crashes (#4018).

Approaches: (1) catch OSError around each probe and report the state as unknown; (2) skip the mac probe when os.name is nt. Chosen: 1, because it also covers a missing gh and a Linux host, and says plainly that the state is unknown. The probe moves with `live()` from counting.py (18,423 of 18,432 bytes) to audit.py, which has room; docs.py calls it from there. No requirement wording changes.

Done line needs: a toy that makes launchctl and gh missing and asserts exit 0 and "unknown" lines (dev/toy/test-automation-launchctl.py), plus a row guarding DOC-15 seen red.
