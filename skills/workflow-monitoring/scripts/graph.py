#!/usr/bin/env python3
"""The goal dependency graph: which queued goals wait on which, and which may start. Shared by watch, monitor and board.

A queue line may carry `depends: a, b` or `depends-on: a, b` (both spellings mean the same). A goal waits only on goals it depends on, and only until they are merged;
sharing files is never a reason to wait (the later goal merges the base before its pull request). The only other limit
is `parallel` in .loop/config.json (0 or unset: unlimited). A goal a worker session was handed before it was frozen
(a busy entry in the session pool with no run yet) holds a slot too, and is never started a second time. Imported, not run.
"""
import datetime
import json
import re

SLUG = re.compile(r"^[a-z0-9][a-z0-9-]{0,50}$")
LIVE = ("running", "waiting")


def parse(line):
    """One '- slug: ...' queue line as a dict: slug, goal, touches, depends, done, release. None when it isn't a goal line."""
    if not line.startswith("- slug:"):
        return None
    item = {"done": [], "touches": [], "depends": [], "release": "", "goal": "", "slug": ""}
    for part in line.strip()[2:].split("|"):
        key, _, value = part.partition(":")
        key, value = key.strip(), " ".join(value.split())
        if key == "done" and value:
            item["done"].append(value)
        elif key in ("touches", "depends", "depends-on"):
            name = "touches" if key == "touches" else "depends"
            item[name] += [x.strip() for x in re.split(r"[,\s]+", value) if x.strip() and x.strip() not in item[name]]
        elif key in ("slug", "goal", "release"):
            item[key] = value
    return item


def area(path):
    """The area a touched path belongs to: skills/<name> for a skill (a file directly in skills/ is just skills), else its first folder, else the root file itself.
    Backticks, a leading ./ and a trailing / are dropped first, and a segment with * ends the fold before it."""
    parts = [x for x in str(path).strip().strip("`").strip().removeprefix("./").rstrip("/").split("/") if x]
    parts = parts[:next((i for i, x in enumerate(parts) if "*" in x), len(parts))]
    if not parts:
        return ""
    if parts[0] == "skills" and (len(parts) > 2 or len(parts) == 2 and "." not in parts[1]):
        return "/".join(parts[:2])
    return parts[0]


def size(done, touches):
    """(done lines, distinct touched areas) of a goal, or None when either is missing."""
    areas = {area(path) for path in touches or []} - {""}
    return (len(done), len(areas)) if done and areas else None


def merged(run):
    """A goal is merged once its run is done and either merge.py or the worker's report says its pull request landed."""
    return bool(run) and run.get("status") == "done" and (run.get("release") in ("merged", "cut") or (run.get("report") or {}).get("status") == "merged")


def unmet(goal, records, queued):
    """The dependencies of goal that are not merged yet, as (slug, why)."""
    found = []
    for dep in goal["depends"]:
        run = records.get(dep)
        if merged(run):
            continue
        found.append((dep, "%s (%s)" % (dep, run.get("status") if run else "queued" if dep in queued else "unknown goal")))
    return found


def read_pool(path):
    """The session pool as (entries, ""), or (None, reason) when it can't be trusted: unreadable, not JSON, not an
    object, an entry that isn't an object, or a busy entry without a valid goal. A missing file is an empty pool."""
    try:
        with open(path) as handle:
            found = json.load(handle)
    except FileNotFoundError:
        return {}, ""
    except OSError as error:
        return None, "can't read it: %s" % (error.strerror or error)
    except ValueError as error:
        return None, "bad JSON: %s" % error
    if not isinstance(found, dict):
        return None, "it is not a JSON object"
    for key, item in found.items():
        if not isinstance(item, dict):
            return None, "entry %s is not an object" % key
        if item.get("state") == "busy" and not (isinstance(item.get("slug"), str) and SLUG.match(item["slug"])):
            return None, "busy entry %s has no valid goal" % key
    return found, ""


def assigned(pool):
    """{slug: entry with its session id} for each goal a busy session holds; None when the pool is unknown."""
    if pool is None:
        return None
    taken = {}
    for sid, item in sorted(pool.items()):
        if item.get("state") == "busy":
            taken.setdefault(item["slug"], dict(item, id=sid))
    return taken


def holds_slot(run, taken=None):
    """A running goal uses a worker slot when a process or a worker session has it (in its run, or as a busy pool
    entry while it is between freezing and its worker's bind); one with none of these uses none."""
    return (run.get("status") != "running" or bool(run.get("pid")) or run.get("worker") == "session"
            or bool(taken and run.get("slug") in taken))


def parallel_of(cfg):
    """Workers allowed at once, read fresh from the config. 0, unset or unreadable means unlimited."""
    try:
        return max(0, int(cfg.get("parallel") or 0))
    except (TypeError, ValueError):
        return 0


def pool_fix(why):
    """The one line every reader prints for a pool it can't trust."""
    return ("the session pool can't be read (%s); fix: check it with python3 -m json.tool, repair it (moved aside, every held goal is forgotten); "
            "nothing was started" % why)


def ready(goals, records, limit, taken=None, why=""):
    """Split queued goals into (start, held). held is [(goal, reason)]; start never exceeds the free worker slots (limit 0: no limit).
    taken (from assigned) adds one slot per goal a session holds with no run yet, and holds that goal: its session freezes it.
    With why set and taken None (the pool can't be read), nothing starts: every goal is held with the fix."""
    if taken is None and why:
        return [], [(goal, pool_fix(why)) for goal in goals]
    queued = {goal["slug"] for goal in goals}
    taken = taken or {}
    used = sum(1 for run in records.values() if run.get("status") in LIVE and holds_slot(run, taken))
    used += sum(1 for slug in taken if slug not in records)
    start, held = [], []
    for goal in goals:
        if goal["slug"] in records:
            continue
        waits = unmet(goal, records, queued)
        if goal["slug"] in taken:
            held.append((goal, "assigned to session %s; not frozen yet" % taken[goal["slug"]].get("name", taken[goal["slug"]]["id"])))
        elif waits:
            held.append((goal, "waits on " + ", ".join(why for _, why in waits)))
        elif limit and used >= limit:
            held.append((goal, "slots full (%d of %d)" % (used, limit)))
        else:
            start.append(goal)
            used += 1
    return start, held



def clock(at):
    """HH:MM in the local time zone with its name; a platform with no zone name gets UTC+hhmm."""
    local = at.astimezone()
    return local.strftime("%H:%M %Z") if local.strftime("%Z") else local.strftime("%H:%M UTC%z")


def localize(text):
    """Rewrite 'HH:MM UTC' (today, UTC) and 'YYYY-MM-DDTHH:MM:SSZ' stamps in printed text as local time with the zone name."""
    today = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")

    def clock_of(day, hour, minute):
        return clock(datetime.datetime.fromisoformat("%sT%s:%s:00+00:00" % (day, hour, minute)))

    text = re.sub(r"(\d{4}-\d\d-\d\d)T(\d\d):(\d\d):\d\dZ", lambda m: m.group(1) + " " + clock_of(m.group(1), m.group(2), m.group(3)), text)
    return re.sub(r"\b(\d\d):(\d\d) UTC\b", lambda m: clock_of(today, m.group(1), m.group(2)), text)


def flow(nodes):
    """The dependency flow chart as lines: one per goal others wait on, `[mark] a --> [mark] b, [mark] c`. Empty with no dependencies.
    A dependency that is no goal here reads [? not a goal here]; a cycle is drawn once, never followed."""
    by = {node["slug"]: node for node in nodes}
    label = lambda slug: "[%s] %s" % (by[slug]["mark"], slug) if slug in by else "[? not a goal here] " + slug
    waiting = {}
    for node in nodes:
        for dep in node["depends"]:
            waiting.setdefault(dep, []).append(node["slug"])
    if not waiting:
        return []
    return ["flow (arrow = must finish before):"] + ["%s --> %s" % (label(dep), ", ".join(label(s) for s in waiting[dep])) for dep in sorted(waiting)]
