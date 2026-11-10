#!/usr/bin/env python3
"""The live board's per-goal budget and decided-depth lines, and the Issues lines for the private-name scan. Imported by
live_board.py; not run.

  line(run, cfg, at, runs)  budget: 35m of 120m, 0.4M of 3.0M tokens[, OVER time][, OVER tokens]
                            "budget: none set" when both halves are 0; only the set half when one is 0
  depth(run, setting, runs) "condensed (small: 1 done line, one area)": the depth the goal is held to, and why
  issues(root, runs)        a missing private-name list, and each finding a scan kept local (finding_error)

Time is the sum of board_status.seconds_by_step(run, at) and tokens are fit.spent_tokens(run): the same numbers health's
cost rule reads. The budget is the one the goal carries (even 0), else the repo settings (fit.budget), with the owner's
settings in the sidecar merged over the run record (fit.view). The token budget is a spending limit, so OVER tokens shows
at or over it; the time budget is advisory and shows OVER time past it. Decisions come from workflow-delivery's fit.py,
loaded from the sibling skill; without it every function here returns nothing and the board prints as before.
"""
import importlib.util
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import board_status as bs  # noqa: E402

FIT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "workflow-delivery", "scripts", "fit.py")
LIST = "~/.workflow-loop/private-names"
SHOWN = "$HOME/.workflow-loop/private-names"  # the board shows no ~/ path (test-live-board)


def load_fit():
    """workflow-delivery's fit module, or None when it is missing or broken."""
    if not os.path.exists(FIT):
        return None
    try:
        spec = importlib.util.spec_from_file_location("fit", FIT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    except Exception:  # a broken sibling leaves the board as it was
        return None


fit = load_fit()


def mega(n):
    return "%.1fM" % (n / 1e6)


def spent(run, at):
    """(whole minutes, tokens) a goal has spent so far."""
    return int(sum(bs.seconds_by_step(run, at).values()) // 60), fit.spent_tokens(run)


def line(run, cfg, at, runs=None):
    """The budget line for one goal, or '' without fit."""
    if fit is None:
        return ""
    held, _ = fit.budget(fit.view(run, runs), cfg)
    minutes, tokens = spent(run, at)
    seconds = sum(bs.seconds_by_step(run, at).values())
    halves, over = [], []
    if held["minutes"] > 0:
        halves.append("%dm of %dm" % (minutes, held["minutes"]))
        over += ["OVER time"] if seconds > held["minutes"] * 60 else []
    if held["tokens"] > 0:
        halves.append("%s of %s tokens" % (mega(tokens), mega(held["tokens"])))
        over += ["OVER tokens"] if tokens >= held["tokens"] else []
    return "budget: " + (", ".join(halves + over) if halves else "none set")


def depth(run, setting, runs=None):
    """The depth the goal is held to and why, or '' without fit."""
    if fit is None:
        return ""
    found, why = fit.depth_for(setting, fit.view(run, runs))
    return "%s (%s)" % (found, why) if why else found


def missing_list():
    """True when no private-name list exists where private.py looks (a comments-only file exists: off on purpose)."""
    given = os.environ.get("LOOP_PRIVATE_NAMES")
    return not os.path.exists(given if given else os.path.expanduser(LIST))


def issues(root, runs=()):
    """Issues lines: the missing list (when fit is installed beside this skill), then each finding kept local."""
    out = []
    if fit is not None and missing_list():
        out += ["- no private-name list: nothing is scanned (create %s; a file holding only comments says off on purpose)" % SHOWN,
                "    fix: write one pattern per line to %s (or point $LOOP_PRIVATE_NAMES at a file)" % SHOWN]
    for run in runs:
        text = " ".join(str(run.get("finding_error") or "").split())
        if text:
            said, _, fix = text.partition(". Fix: ")
            out += ["- %s: a finding stayed local: %s" % (run["slug"], said[:200]),
                    "    fix: %s" % (fix[:200] or "remove what the scan found, then push the finding commit")]
    return out
