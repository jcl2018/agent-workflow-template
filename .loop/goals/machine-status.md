# Each check-in shows this machine's status and only this machine's goals; goals start only above the memory floor, and the main checkout is kept current

- Slug: machine-status
- Touches: skills/workflow-monitoring, dev/toy, docs, .loop/regression.tsv

## Done lines

Frozen. A wrong done line needs a new goal.

1. checkin.py prints a Machine line and only this pod's goals; pool refuses a start under min_free_memory_gb; operate flags a main checkout behind origin/main; a queued goal with a fresh queue file reads alive

## Verify by hand

<!-- Numbered steps for a person, each with an Expect: line. A release needs this. -->
