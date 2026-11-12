#!/usr/bin/env python3
"""The goal dependency graph: which queued goals wait on which, and which may start. Shared by watch, monitor and board.

A queue line may carry `depends: a, b` or `depends-on: a, b` (both spellings mean the same). A goal waits only on goals it depends on, and only until they are merged;
sharing files is never a reason to wait (the later goal merges the base before its pull request). The only other limit
is `parallel` in .loop/config.json (0 or unset: unlimited). A goal a worker session was handed before it was frozen
(a busy entry in the session pool with no run yet) holds a slot too, and is never started a second time. Imported, not run.
"""
import atexit
import datetime
import json
import os
import re
import subprocess
import sys
import time

os.environ.setdefault("GIT_TERMINAL_PROMPT", "0")  # no terminal, no waiting: git must fail, not prompt
SLUG = re.compile(r"^[a-z0-9][a-z0-9-]{0,50}$")
LIVE = ("running", "waiting")
LAST_BAD = {}  # pool path -> the malformed entries read_pool set aside on its last read


def parse(line):
    """One '- slug: ...' queue line as a dict: slug, goal, touches, depends, done, release, prd (the PRD it builds, e.g.
    "Monitoring MON-4") and parts (ready parts a split could start first). None when it isn't a goal line."""
    if not line.startswith("- slug:"):
        return None
    item = {"done": [], "touches": [], "depends": [], "parts": [], "release": "", "goal": "", "slug": "", "prd": ""}
    for part in line.strip()[2:].split("|"):
        key, _, value = part.partition(":")
        key, value = key.strip(), " ".join(value.split())
        if key == "done" and value:
            item["done"].append(value)
        elif key in ("touches", "depends", "depends-on", "parts"):
            name = key if key in ("touches", "parts") else "depends"
            item[name] += [x.strip() for x in re.split(r"[,\s]+", value) if x.strip() and x.strip() not in item[name]]
        elif key in ("slug", "goal", "release", "prd"):
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
    """The session pool as (entries, ""), or (None, reason) when it can't be trusted: unreadable, not JSON or not an
    object. An entry that isn't an object, or a busy entry without a valid goal, is left out and kept in LAST_BAD
    (pool.quarantine moves it to a side file). A missing file is an empty pool."""
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
    bad = {key: item for key, item in found.items() if not isinstance(item, dict) or (
        item.get("state") == "busy" and not (isinstance(item.get("slug"), str) and SLUG.match(item["slug"])))}
    if bad:  # one bad entry no longer blocks the pool (issue 122): it is set aside, and pool.py keeps it in a side file
        LAST_BAD[path] = bad
        found = {key: item for key, item in found.items() if key not in bad}
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


# One goal's state, decided once for every reader (issue 113): the live board, the board digest, report, watch and
# handoff all ask here, so held, freezing, silent and slot-holding mean the same everywhere. Imported, not run.
#
#   classify(run, taken, at, cfg)  one of: running, waiting, failed, stopped, held, silent, done, merged, retired, queued
#   holds_slot(run, taken)         a live goal uses a worker slot: a pid, or a busy pool entry; with the pool known, a
#                                  session goal whose session was freed holds none (issue 112)
#   held(run, taken)               running with no worker: the pool is known, no busy session names it, no pid
#   freezing(taken, on_disk)       pool entries handed a goal that has no run record yet
#   silent_for(run, at)            seconds since the worker last spoke (latest report, bind or change), or None
#   stamp_held(runs, taken, at, folder)  record when each goal first read held in <loop>/held.json (replan.py, each pass)
#   with_held(runs, folder)        fill held_at from that file
#
# The pool is the busy map from graph.assigned (None when the pool can't be read: then nothing is called held).
# `silent_minutes` in .loop/config.json (default 30) is MON-8's limit; LOOP_SESSION_QUIET (seconds) overrides it.
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


def load_run(slug):
    """The run record of a goal in this repo ({} if missing or the slug is bad)."""
    try:
        top = subprocess.run(["git", "rev-parse", "--git-common-dir"], capture_output=True, text=True).stdout.strip()
        with open(os.path.join(os.path.abspath(top), "loop", "runs", slug + ".json")) as handle:
            return json.load(handle) if SLUG.match(slug) else {}
    except (OSError, ValueError):
        return {}


# Pods (MON-15) and the merge lock (MON-15): the one place every skill asks. goal.py and merge.py load this file by path
# and carry on without it when workflow-monitoring isn't installed. Imported, not run.
#
#   pod_id()        $LOOP_POD_ID, else the operation session's own id ($CLAUDE_SESSION_ID); "" in a worker or with neither
#   stamp(state)    record the caller's pod on a goal that has none; a goal with no pod belongs to no one
#   foreign(state)  the owning pod's id when it is not the caller's (a worker never counts), else ""
#   refuse(state)   print the one REFUSED line naming the owner to stderr and exit 2 (no try is used)
#   merge_lock(common)  one merge per repo at a time, across pods; released at exit; a dead or old holder is replaced
def pod_id():
    if os.environ.get("LOOP_ROLE") == "worker":
        return ""
    return re.sub(r"[^A-Za-z0-9_.-]", "", os.environ.get("LOOP_POD_ID") or os.environ.get("CLAUDE_SESSION_ID") or "")[:64]


def stamp(state):
    if pod_id() and not state.get("pod"):
        state["pod"] = pod_id()


def foreign(state):
    owner = str(state.get("pod") or "") if isinstance(state, dict) else ""
    return owner if owner and os.environ.get("LOOP_ROLE") != "worker" and owner != pod_id() else ""


def refuse(state):
    owner = foreign(state)
    if owner:
        sys.stderr.write("REFUSED: goal %s is owned by pod %s. Fix: act from that pod (set LOOP_POD_ID=%s), not from here.\n" % (
            state.get("slug"), owner, owner))
        sys.exit(2)


def merge_lock(common):
    """Take <git common dir>/loop/merge.lock (created exclusively, holding the pid), waiting while its holder is alive and
    its file younger than LOOP_MERGE_LOCK_SECONDS (default 1800); a dead or older holder is replaced by one atomic rename,
    so two waiters never both take it. Released at exit if still ours."""
    path, told = os.path.join(common, "loop", "merge.lock"), False
    os.makedirs(os.path.dirname(path), exist_ok=True)
    while True:
        try:
            with os.fdopen(os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY), "w") as handle:
                handle.write("%d\n" % os.getpid())
            break
        except FileExistsError:
            pid, dead, age, seen = 0, False, 0, ""
            try:
                age = time.time() - os.stat(path).st_mtime
                seen = open(path).read()
                pid = int(seen.split()[0])
                os.kill(pid, 0)
            except ProcessLookupError:
                dead = True
            except FileNotFoundError:
                continue
            except (OSError, ValueError, IndexError):
                pass
            if dead or age > int(os.environ.get("LOOP_MERGE_LOCK_SECONDS") or 1800):
                mine = "%s.stale.%d" % (path, os.getpid())
                try:
                    os.rename(path, mine)
                    if open(mine).read() != seen:  # a new holder took the path since we looked: put its lock back
                        os.link(mine, path)
                    os.unlink(mine)
                except OSError:
                    pass
                continue
            if not told:
                sys.stderr.write("WAITING: another pod is merging into this repo (pid %d); one merge at a time.\n" % pid)
                told = True
            time.sleep(0.2)

    def release():
        try:
            if open(path).read().split()[:1] == [str(os.getpid())]:
                os.unlink(path)
        except OSError:
            pass
    atexit.register(release)
