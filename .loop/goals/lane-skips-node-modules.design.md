# Design: lane-skips-node-modules

Problem: the lane's planning walks every folder a row names (lanes.walk). It skipped files inside __pycache__ but still descended into it, and it descended into node_modules. On Windows a worktree's node_modules (tens of thousands of files) used the whole planning budget in thermis (#3939); __pycache__ is #3943.

Approaches: (1) prune node_modules and __pycache__ in os.walk's dirs so they are never entered; (2) filter the results afterwards (still pays the walk). Chosen: 1. lanes.py is 20,467 bytes of the 20,480 cap, so the change is a compact in-place edit.

Done line needs: a toy with a 3,000-file node_modules that asserts the walk returns only the real files, never enters the two folders and is fast, plus a row guarding REG-7 seen red.
