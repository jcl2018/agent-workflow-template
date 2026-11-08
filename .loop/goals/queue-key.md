# Accept both depends: and depends-on: in queue lines

- Slug: queue-key
- Touches: skills/workflow-monitoring/scripts/graph.py, skills/loop-files.md, dev/toy

## Done lines

Frozen. A wrong done line needs a new goal.

1. A queue line with depends: or depends-on: waits on the named goals the same way, and loop-files.md shows the key
2. A toy test proves both spellings

## Verify by hand

1. Run `bash dev/toy/test-status-graph.sh`.
   Expect: it ends with ALL PASS, including "depends: and depends-on: parse to the same waits".
2. Open `skills/loop-files.md` and find the queue-line paragraph.
   Expect: it shows `depends: a, b` (or `depends-on:`) as the dependency key.
