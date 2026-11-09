#!/usr/bin/env python3
"""The goal dependency graph: which queued goals wait on which, and which may start. Shared by watch, monitor and board.

A queue line may carry `depends: a, b` or `depends-on: a, b` (both spellings mean the same). A goal waits only on goals it depends on, and only until they are merged;
sharing files is never a reason to wait (the later goal merges the base before its pull request). The only other limit
is `parallel` in .loop/config.json (0 or unset: unlimited). Imported, not run.
"""
import datetime
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


def holds_slot(run):
    """A running goal uses a worker slot when a process or a worker session has it; one with neither uses none."""
    return run.get("status") != "running" or bool(run.get("pid")) or run.get("worker") == "session"


def parallel_of(cfg):
    """Workers allowed at once, read fresh from the config. 0, unset or unreadable means unlimited."""
    try:
        return max(0, int(cfg.get("parallel") or 0))
    except (TypeError, ValueError):
        return 0


def ready(goals, records, limit):
    """Split queued goals into (start, held). held is [(goal, reason)]; start never exceeds the free worker slots (limit 0: no limit)."""
    queued = {goal["slug"] for goal in goals}
    used = sum(1 for run in records.values() if run.get("status") in LIVE and holds_slot(run))
    start, held = [], []
    for goal in goals:
        if goal["slug"] in records:
            continue
        waits = unmet(goal, records, queued)
        if waits:
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
