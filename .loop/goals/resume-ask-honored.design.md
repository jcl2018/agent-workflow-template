# Design: a resumed goal keeps its release ask (#812)

## Problem
A goal started with `--release ask` records `release: ask`. After a resume with `auto_merge` on, the prompt built by
`mend.release_text` and `watch.release_text` checks `auto_merge` first and tells the worker to run `merge.py`, and
`worker.release_step` (also reached from `sessions.py report`) runs `merge.py` for any finished goal. The ask is lost.

## Approaches
1. Guard `merge.py` itself when a worker runs it and the goal says ask. One choke point, but `merge.py` is 20,444 bytes
   (cap 20,480) and the owner's own cut/leave path also goes through the goal's record.
2. Make each caller honor the ask: the two prompt builders check `release != "ask"` before `auto_merge`, the worker's
   release step skips an ask, and goal.py's NEXT line stops advertising merge.py. Four one-line edits, no new files.

## Chosen
Approach 2: the ask is read where the decision to merge is made, and the files stay under the size cap.

## Done line
"A goal set to ask, resumed with auto_merge on, stops before merge with the ask shown, and an unresumed one still
merges": `dev/toy/test-resume-ask.py` checks both prompts and the worker step for an ask and for a plain goal.

## Open questions
None.
