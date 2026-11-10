#!/usr/bin/env python3
"""Pull request states for the board, fast (MON-9: the board builds in under 10 seconds). gh is asked in parallel, each
call bounded, and answers are kept in <git common dir>/loop/pr-states.json: MERGED for good, OPEN and CLOSED for
TTL seconds (a closed pull request can be reopened). The file is written whole through a temp file and os.replace, so
a reader never sees half of it; when two writers race, the last one wins and a lost answer is only asked again.
Imported by board_status.py and board.py, not run.

  states(runs, root)  {slug: MERGED|CLOSED|OPEN|""} for each done, unmerged run with a pull request
  state(url, root)    one pull request's state ("" when gh can't say)
"""
import concurrent.futures
import json
import os
import subprocess
import time

TTL = int(os.environ.get("LOOP_PR_TTL", "60"))
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
        done = subprocess.run(["gh", "pr", "view", url, "--json", "state"], cwd=root, capture_output=True, text=True, timeout=TIMEOUT)
        got = str(json.loads(done.stdout).get("state", "")).upper() if done.returncode == 0 else ""
        return got if got in ("MERGED", "CLOSED", "OPEN") else ""
    except (OSError, ValueError, AttributeError, subprocess.SubprocessError):
        return ""


def fresh(entry, now):
    return isinstance(entry, dict) and (entry.get("state") == "MERGED" or now - float(entry.get("at") or 0) < TTL)


def lookup(urls, root):
    """{url: state} for each url, from the cache where fresh, else from gh in parallel."""
    path, now = cache_path(root), time.time()
    cache = load(path) if path else {}
    out = {url: cache[url]["state"] for url in urls if fresh(cache.get(url), now)}
    todo = [url for url in dict.fromkeys(urls) if url not in out]
    if todo:
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(WORKERS, len(todo))) as pool:
            for url, got in zip(todo, pool.map(lambda u: ask(u, root), todo)):
                out[url] = got
                if got:
                    cache[url] = {"state": got, "at": now}
        if path:
            save(path, cache)
    return out


def states(runs, root, merged=lambda run: False):
    wanted = {run["slug"]: run["pr"] for run in runs if run.get("status") == "done" and run.get("pr") and not merged(run)}
    found = lookup(list(wanted.values()), root)
    return {slug: found.get(url, "") for slug, url in wanted.items()}


def state(url, root):
    return lookup([url], root).get(url, "") if url else ""
