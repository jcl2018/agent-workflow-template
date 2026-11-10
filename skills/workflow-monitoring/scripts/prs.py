#!/usr/bin/env python3
"""Pull request states for the board, fast (MON-9: the board builds in under 10 seconds). gh is asked in parallel, each
call bounded, and a MERGED answer is kept in <git common dir>/loop/pr-states.json for good (OPEN and CLOSED can change,
so they are asked each time, all at once). The file is written whole through a temp file and os.replace, so
a reader never sees half of it; when two writers race, the last one wins and a lost answer is only asked again.
Imported by board_status.py and board.py, not run.

  states(runs, root)  {slug: MERGED|CLOSED|OPEN|""} for each done, unmerged run with a pull request
  state(url, root)    one pull request's state ("" when gh can't say)
"""
import concurrent.futures
import json
import os
import shutil
import subprocess
import sys
import time

TIMEOUT = float(os.environ.get("LOOP_PR_TIMEOUT", "3"))
WORKERS = 16  # 16 calls of at most 3 s each: one wave, well inside MON-9's 10 seconds


def cache_path(root):
    try:
        common = subprocess.run(["git", "rev-parse", "--git-common-dir"], cwd=root, capture_output=True, text=True, timeout=5).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""
    return os.path.join(os.path.abspath(os.path.join(root, common)), "loop", "pr-states.json") if common else ""


def load(path):
    try:
        with open(path) as handle:
            found = json.load(handle)
        return found if isinstance(found, dict) else {}
    except (OSError, ValueError):
        return {}


def save(path, found):
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = "%s.%d.tmp" % (path, os.getpid())
        with open(tmp, "w") as handle:
            json.dump(found, handle, indent=1, sort_keys=True)
        os.replace(tmp, path)
    except OSError:
        pass


def ask(url, root):
    try:
        done = subprocess.run(["gh", "pr", "view", url, "--json", "state", "-q", ".state"], cwd=root, capture_output=True,
                              text=True, timeout=TIMEOUT)
        out = done.stdout.strip() if done.returncode == 0 else ""
        got = str(json.loads(out).get("state", "") if out.startswith("{") else out).upper()  # -q, or JSON when ignored
        return got if got in ("MERGED", "CLOSED", "OPEN") else ""
    except (OSError, ValueError, AttributeError, subprocess.SubprocessError):
        return ""


def fresh(entry, now):
    return isinstance(entry, dict) and entry.get("state") == "MERGED"  # only a merge is final; OPEN and CLOSED are asked anew


def lookup(urls, root):
    """{url: state} for each url, from the cache where fresh, else from gh in parallel. No gh at all: every state unknown."""
    if not shutil.which("gh"):
        return {url: "" for url in urls}
    path, now = cache_path(root), time.time()
    cache = load(path) if path else {}
    out = {url: cache[url]["state"] for url in urls if fresh(cache.get(url), now)}
    todo = [url for url in dict.fromkeys(urls) if url not in out]
    if todo:
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(WORKERS, len(todo))) as pool:
            for url, got in zip(todo, pool.map(lambda u: ask(u, root), todo)):
                out[url] = got
                if got == "MERGED":
                    cache[url] = {"state": got, "at": now}
        if path:
            save(path, cache)
    return out


HEALTH_TTL = int(os.environ.get("LOOP_HEALTH_TTL", "900"))
REFRESH = r"""
import json, os, re, subprocess, sys, time
script, path = sys.argv[1], sys.argv[2]
try:
    out = subprocess.run([sys.executable, script, "check"], capture_output=True, text=True, timeout=600).stdout
    got = re.search(r"^HEALTH: (not green|green)", out, re.M)
    tmp = path + ".%d.tmp" % os.getpid()
    json.dump({"verdict": got.group(1) if got else "unknown", "at": time.time()}, open(tmp, "w"))
    os.replace(tmp, path)
finally:
    try:
        os.remove(path + ".lock")
    except OSError:
        pass
"""


def health(root, script):
    """workflow-health's last verdict with its age ("green, 2h ago"), never run inline: the board stays fast. A verdict
    older than HEALTH_TTL starts one detached refresh (a lock file keeps it to one); none yet reads "unknown (checking)"."""
    path = cache_path(root).replace("pr-states.json", "health-verdict.json")
    if not path:
        return "unknown"
    found = load(path)
    age = time.time() - float(found.get("at") or 0)
    if age > HEALTH_TTL and os.path.exists(script):
        try:
            os.close(os.open(path + ".lock", os.O_CREAT | os.O_EXCL | os.O_WRONLY))
            subprocess.Popen([sys.executable, "-c", REFRESH, script, path], cwd=root, stdin=subprocess.DEVNULL,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        except OSError:  # a refresh is already running (or can't start): show what we have
            pass
    if not found.get("verdict"):
        return "unknown (checking)"
    minutes = int(age // 60)
    return "%s, %s ago" % (found["verdict"], "%dm" % minutes if minutes < 120 else "%dh" % (minutes // 60))


def states(runs, root, merged=lambda run: False):
    wanted = {run["slug"]: run["pr"] for run in runs if run.get("status") == "done" and run.get("pr") and not merged(run)}
    found = lookup(list(wanted.values()), root)
    return {slug: found.get(url, "") for slug, url in wanted.items()}


def state(url, root):
    return lookup([url], root).get(url, "") if url else ""
