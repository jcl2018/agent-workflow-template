# Design: prep-budget

Status: DRAFT (owner approval not given by the worker). Mode: Builder.

## Problem

A goal lane's time is bounded in two places today: the rows it runs stop at test_budget_minutes (default 15, floor 15) and the
whole lane is killed at the flow file's limit or test_budget_minutes plus five minutes. The work before the first row (the
prep commit that re-renders the Tests tables, planning which rows the change reaches, and waiting for a lane slot) is only
bounded by 4x the lane limit while queued or planning, so lane-control's own pr step took 42 minutes, 13 of them before any
row ran (owner, 2026-11-11: "I really want the 15-minute budget to ... maybe you should apply an additional budget set a
budget for that to cover that step. Let's make it 15 minutes as well.").

## Premises

1. One setting, prep_budget_minutes in .loop/config.json (default 15, floor 15, refused below with a fix line, exactly like
   step_budget_minutes and test_budget_minutes), read by the lanes through budget.py. Agreed.
2. The budget covers the three parts together, measured from the moment the lane starts its prep: prep (the Tests-table render
   and commit), planning (choosing the rows) and the slot wait. A lane that reaches it before its first row stops (kills its
   child), prints LANE_PREP_BUDGET naming which part ran long (the one running at the stop) with every part's seconds, says
   no row ran and nothing was committed or pushed beyond the prep commit, and tells the goal to run the same command again
   (it replans on the same HEAD, so nothing is started over but the lane itself). Agreed.
3. Every lane records how long prep, planning and the slot wait each took (in its .last record and on its LANE line), and a
   lane that hit the preparation budget is recorded in the goal's run file's budget_hits (kind prep, with the part), so the
   board (monitoring report) and health list it with the part that ran long, next to the step and test hits. Agreed.
4. The rows' own budget and the lane's overall limit are unchanged: once the first row starts the existing limit (the flow file's,
   else test_budget_minutes plus five minutes) applies, so a whole lane is at most prep_budget plus that. Agreed.
5. A test-only override, LOOP_PREP_BUDGET (seconds), lets the toy tests exercise a stop without waiting 15 minutes (the same
   precedent as LOOP_SESSION_QUIET); it is documented as test-only and never read from .loop/config.json. Agreed.
6. REG-7 gains the owner's words as an Unreviewed sentence; DEL-8 gains a sentence for the record and board; both pages are
   already Unreviewed and the owner reviews at the PR. Agreed.

## Approaches

A. Time the three parts in lane.py/lanekit.py and stop in the lane child (chosen). lane.py is at the 20 KB script cap, so the
   new logic lives in lanekit.py (with a small helper moved out of lane.py), and budget.py learns the setting. Effort M.
B. Put a timeout inside regression.py's planning and slot code. Rejected: the slot code is copied between slots.py and
   lanekit.py on purpose, prep happens before regression.py starts, and the lane child already owns the clock.

## Success

The setting, the stop, the timings and the board and health lines each have a regression row seen failing then passing; the
goal's own pr lane finishes within both budgets.
