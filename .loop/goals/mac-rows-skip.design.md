# Design: mac-rows-skip

## Problem
The scheduled Linux regression run (43398277164) FAILs 58 rows. #3832 blames macOS-only rows. A Linux probe of those 58 rows (throwaway workflow on a probe branch, never merged) shows the 16 rows that run `dev/toy/test-local-schedule.sh` (15 `ls-*` rows plus `aut-email-secrets`) fail only because `automation.py local install` refuses off macOS (`SCHEDULE_PLATFORM`); they open an issue each run. The other 42 FAILs have other causes.

## Approaches
1. Guard at the top of the toy: exit 77 with a reason when `uname -s` is not Darwin. Cost: 3 lines in one script; the runner already turns 77 into SKIPPED, opens no issue (REG-10). Risk: none for macOS.
2. Export `LOOP_SCHEDULE_PLATFORM=darwin` in the toy so it runs on Linux. Runs more, but the plist, launchctl and BSD tools are macOS facts, and the owner asked for a skip.

## Chosen
1. Only test-local-schedule.sh is macOS-only (other toys that mention launchctl already branch on `uname` or use fakes). A Python toy proves a non-Darwin host gets exit 77 and a reason from the guard.

## Split
Platform-only 16 (all in test-local-schedule.sh). Real or other 42, reported to the operation session; not changed here.

## Done line
1. The guard plus the toy row; the Linux scheduled run showing no platform-only FAIL is checked by hand after release.
