# Design: machine-status

## Problem
The check-in says nothing about the machine it runs on, goals start with no regard for free memory, a stale main checkout goes unfixed (329 commits behind), a goal waiting its turn in the pr queue reads silent, and other pods' goals crowd the check-in.

## Approaches
1. A separate monitor script and config for each concern. More files; the package has one free slot.
2. Fold each concern into the scripts that already own it: board_status (machine reading, floor), graph (ready holds a goal under the floor; a fresh pr-queue file counts as speaking), checkin (Machine line, this pod only, checkout ask), operate (behind check), pool (no session under the floor), reply_hook (lets the new lines follow the headline).

## Choice
Approach 2: no new file; every touched script except reply_hook stays under 19,000 bytes.

## Done line
Python toy dev/toy/test-machine-status.py with five rows (line, floor, checkout, alive, pod), each seen red. GRD-12, MON-16, MON-17 wording waits in DECISIONS.md for the owner.

## Open
`min_free_memory_gb` is in this repo's config.json but not yet in the settings registry (workflow-setup, outside this goal's touches): filed as backlog.
