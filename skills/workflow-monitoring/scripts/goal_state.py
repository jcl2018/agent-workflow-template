#!/usr/bin/env python3
"""One goal's state, decided once for every reader (issue 113): the live board, the board digest, report, watch and
handoff all ask here, so held, freezing, silent and slot-holding mean the same everywhere. Imported, not run.

  classify(run, taken, at, cfg)  one of: running, waiting, failed, stopped, held, silent, done, merged, retired, queued
  holds_slot(run, taken)         a live goal uses a worker slot: a pid, or a busy pool entry; with the pool known, a
                                 session goal whose session was freed holds none (issue 112)
  held(run, taken)               running with no worker: the pool is known, no busy session names it, no pid
  freezing(taken, on_disk)       pool entries handed a goal that has no run record yet
  silent_for(run, at)            seconds since the worker last spoke (latest report, bind or change), or None
  held_since(run)                when the goal first read as held (held_at, issue 115), else its last change
  stamp_held(runs, taken, at, folder)  record when each goal first read held in <loop>/held.json (replan.py, each pass)
  with_held(runs, folder)        fill held_at from that file

The pool is the busy map from graph.assigned (None when the pool can't be read: then nothing is called held).
`silent_minutes` in .loop/config.json (default 30) is MON-8's limit; LOOP_SESSION_QUIET (seconds) overrides it.
"""
import datetime
import json
import os

LIVE = ("running", "waiting")
ASKING = ("waiting", "failed", "stopped")


def parse_at(text):
    """A recorded time as an aware UTC datetime (naive counts as UTC), or None."""
    try:
        found = datetime.datetime.fromisoformat(str(text).replace("Z", "+00:00"))
    except ValueError:
        return None
    return found if found.tzinfo else found.replace(tzinfo=datetime.timezone.utc)


def iso(at):
    return at.astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def silent_limit(cfg=None):
    """Seconds a worker may stay silent before it shows under Needs you (MON-8)."""
    if os.environ.get("LOOP_SESSION_QUIET", "").isdigit():
        return int(os.environ["LOOP_SESSION_QUIET"])
    try:
        return max(1, int((cfg or {}).get("silent_minutes") or 30)) * 60
    except (TypeError, ValueError):
        return 1800


def merged(run):
    return bool(run) and run.get("status") == "done" and (
        run.get("release") in ("merged", "cut") or (run.get("report") or {}).get("status") == "merged")


def held(run, taken):
    return run.get("status") == "running" and taken is not None and run.get("slug") not in taken and not run.get("pid")


def holds_slot(run, taken=None):
    """A live goal's slot: anything not running holds one (waiting keeps its worker); a running goal holds one when it
    has a pid or a busy pool entry. Without the pool (taken None) a session goal is trusted to hold its slot."""
    if run.get("status") != "running":
        return True
    if run.get("pid") or (taken and run.get("slug") in taken):
        return True
    return taken is None and run.get("worker") == "session"


def freezing(taken, on_disk):
    return [dict(entry, slug=slug) for slug, entry in sorted((taken or {}).items()) if slug not in on_disk]


def last_spoke(run):
    """The newest of the worker's latest report, its bind and the run's last change."""
    times = [parse_at(run.get("updated")), parse_at(run.get("bound_at")), parse_at((run.get("report") or {}).get("at"))]
    reports = run.get("reports") if isinstance(run.get("reports"), list) else []
    if reports and isinstance(reports[-1], dict):
        times.append(parse_at(reports[-1].get("at")))
    times = [t for t in times if t]
    return max(times) if times else None


def silent_for(run, at):
    last = last_spoke(run)
    return None if not last or not at else max(0.0, (at - last).total_seconds())


def held_since(run):
    return parse_at(run.get("held_at")) or parse_at(run.get("updated"))


def held_file(folder):
    return os.path.join(folder, "held.json")


def with_held(runs, folder):
    """The runs with held_at filled from <loop>/held.json (kept apart so stamping never races a worker's run write)."""
    try:
        with open(held_file(folder)) as handle:
            found = json.load(handle)
    except (OSError, ValueError):
        found = {}
    for run in runs:
        if isinstance(found, dict) and found.get(run.get("slug")) and not run.get("held_at"):
            run["held_at"] = found[run["slug"]]
    return runs


def stamp_held(runs, taken, at, folder):
    """held_at is set the first time a goal reads held and dropped once it has a worker again (issue 115). Writes
    held.json when anything changed; never touches a run file. Without the pool (taken None) nothing changes."""
    if taken is None:
        return False
    try:
        with open(held_file(folder)) as handle:
            old = json.load(handle)
    except (OSError, ValueError):
        old = {}
    old = old if isinstance(old, dict) else {}  # a malformed file is started again, never a crash
    new = {r["slug"]: old.get(r["slug"]) or iso(at) for r in runs if r.get("slug") and held(r, taken)}
    if new == old:
        return False
    tmp = held_file(folder) + ".%d.tmp" % os.getpid()
    with open(tmp, "w") as handle:
        json.dump(new, handle, indent=1, sort_keys=True)
    os.replace(tmp, held_file(folder))
    return True


def classify(run, taken=None, at=None, cfg=None):
    """The one state name for a run record (a queue line with no run is 'queued')."""
    if not run:
        return "queued"
    status = run.get("status") or "queued"
    if status == "done":
        return "merged" if merged(run) else "done"
    if status in ("retired", "waiting", "failed", "stopped", "queued"):
        return status
    if held(run, taken):
        return "held"
    quiet = silent_for(run, at)
    if status == "running" and quiet is not None and quiet >= silent_limit(cfg):
        return "silent"
    return "running" if status == "running" else status
