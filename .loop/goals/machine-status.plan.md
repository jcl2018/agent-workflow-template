# Plan: machine-status

## Build steps
1. board_status.py: `memory`, `allowed` (floor min_free_memory_gb, default 3.5; goals = 1 + one per 1.5 GB above), `machine_line`.
2. graph.py: `ready` holds a goal as "memory low" past `allowed`; `with_held` sets `queue_at` from a fresh pr-queue file and `last_spoke` counts it (alive, not silent); board.py reads it too.
3. checkin.py: Machine line after the headline; `gather` splits other pods' goals into one line each; Needs you carries the checkout-behind ask.
4. operate.py: `behind_ask` each pass writes `<loop>/checkout-behind.txt` and names a free worker; pool.py `need` creates no session under the floor.
5. reply_hook.py: the Machine and pod lines may follow the headline; trimmed to stay under the 20,480-byte cap.
6. Toy dev/toy/test-machine-status.py with five rows, each seen red; DECISIONS.md holds GRD-12, MON-16, MON-17.

## Verified against the code
Every function named exists and was edited; no new file under skills/; scripts touched stay under 19,000 bytes except reply_hook (20,334, as before).

## Could break
A machine under 3.5 GB of free commit memory starts no goal until it frees: intended, 0 turns it off. LOOP_MACHINE stands in for a machine in toys.

## Out of scope
Registering min_free_memory_gb in the setup settings table; applying the wording to the Reviewed pages.
