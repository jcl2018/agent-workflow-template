# Design: issue-cleanup

Status: DRAFT (owner approval not given by the worker). Mode: Builder.

## Problem

The template has 820 open issues; 722 are defect+regression issues that regression-green-2 cleans up. The other 98 (health
findings, enhancements, goal bugs) pile up: many were fixed by later goals, many are the same finding filed twice, and the real
ones are hard to see. The owner asked to fix them.

## Premises

1. Scope is exactly the open issues with no `regression` label (98 today); the 722 defect+regression issues are not touched.
   Agreed.
2. Every issue gets one verdict from evidence read now, not from its title: `fixed` (the code, doc or check on `origin/main`
   now does what the issue asked: cite the commit, PR or the command output), `stale` (the thing it reported no longer exists or
   its health check no longer fires: cite the check output), `duplicate-of #N` (same finding as an issue that stays open or is
   closed as fixed: cite both), or `needs-code` (still true on main). Agreed.
3. A health issue is judged by re-running the health check that opened it (`workflow-health check`, the size rule, the page
   checks) on current `origin/main`: still firing means `needs-code` or `duplicate`, silent means `stale`. A review finding
   (`health: review ...`) is judged by reading the code it names. Agreed.
4. Closing goes through `gh issue close N --comment "<one-line reason + evidence>"`, one issue at a time, from a script that
   prints each line before it runs and stops on the first error; `--reason completed` for fixed, `not planned` for stale and
   duplicates. Nothing is deleted, nothing is edited but state and one comment, and a close can be undone by reopening. A
   duplicate is closed in favour of the older issue, which gets one comment naming what was folded in. Agreed.
5. Every `needs-code` issue is either covered by a goal already in the queue or in a finding line, or gets one new finding line in
   `.loop/findings.md` (`- <slug>: <what to build> (issues #N, #M)`), one line per real piece of work, folding the issues that
   need the same change. Agreed.
6. The branch carries only `.loop/findings.md` (and this goal's design and plan files); the pull request body holds the table of
   every issue, its verdict and its evidence, with no private name or path. The closes themselves are outside git: the pull
   request lists them and the operation can reopen any. Agreed.
7. Issues opened after this run starts (the health run files new ones every few hours) are out of scope; the run records the
   highest issue number it covered. Agreed.

## Approach

Triage in four groups by what they are (size findings; requirement, criteria, docs, consistency and hygiene findings; review
findings; bugs and enhancements), each read against `origin/main` by a reviewer subagent that writes a verdict table with
evidence; the worker checks each verdict itself (re-runs the check or reads the code) before any issue closes, then closes
through the script and writes the finding lines.

## Not in scope

The 722 defect+regression issues; fixing any code; changing labels or milestones; deleting an issue.
