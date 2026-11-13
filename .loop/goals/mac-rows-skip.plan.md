# Plan: mac-rows-skip

## Build steps
1. dev/toy/test-local-schedule.sh: after the header comments and before `set -u`, add a guard: not Darwin => print `SKIP: macOS only (launchd and SCHEDULE_PLATFORM); this host is <uname>` and `exit 77`.
2. dev/toy/test-mac-skip.py (`# windows: ok`): on a non-Darwin host, run the script and assert exit 77 and the SKIP reason; on Darwin it exits 77 itself.
3. Row `mac-rows-skip-77` (land, DOC/REG-10), seen red by breaking the guard.
4. Fill the goal's Verify by hand.

## Test for the done line
1. mac-rows-skip-77. The Linux scheduled run is checked by hand.

## Could break
A macOS host must still run the toy: the guard only exits off Darwin.

## Out of scope
The 42 other Linux FAILs (reported, not changed).

VERDICT: self: plan checked against test-local-schedule.sh and the probe output
