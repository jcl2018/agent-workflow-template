#!/usr/bin/env python3
"""A goal's budgets, counted on active time only (#3878). minutes() is the time the goal spent on its steps, with the board's
held-time rule (workflow-monitoring's board_log.flow_seconds, loaded by path): time waiting in the pr queue, on a hold, on
an owner answer or after a stop counts nothing. budget_stop() refuses a new step past the minute or token budget.
"""
import datetime
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def board_log():
    """workflow-monitoring's board_log module, or None when it is missing or broken."""
    path = os.path.join(HERE, "..", "..", "workflow-monitoring", "scripts", "board_log.py")
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(path)))
        spec = importlib.util.spec_from_file_location("active_board_log", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    except Exception:
        return None


def wall(state, at):
    """Minutes since the goal froze: the fallback when the board's rule can't be loaded."""
    try:
        began = datetime.datetime.strptime(state["log"][0].split()[0], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)
        return int(max(0, (at - began).total_seconds()) // 60)
    except (KeyError, IndexError, ValueError, AttributeError):
        return 0


def minutes(state, at=None):
    """Whole minutes of active step time: the gaps between log entries, and the time since the last one while the run is running."""
    at = at or datetime.datetime.now(datetime.timezone.utc)
    module = board_log()
    if module is None:
        return wall(state, at)
    return int(sum(module.flow_seconds(state, at).values()) // 60)


def budget_stop(slug, state, runs, cfg, fit, at=None):
    """Past its time or token budget a goal starts no new step; only goal.py set raises it."""
    held, source = fit.budget(fit.view(state, runs), cfg)
    for name, spent in (("minutes", minutes(state, at)), ("tokens", fit.spent_tokens(state))):
        if held[name] and spent >= held[name]:
            sys.exit("REFUSED: %d %s spent, at the %s budget of %d (%s); no new step starts. Fix: goal.py set %s --budget-%s N "
                     "--why ... from the operation session (BUDGET_%s)" % (spent, name, name[:-1] if name == "minutes" else name,
                                                                         held[name], source, slug, name, name.upper()))
