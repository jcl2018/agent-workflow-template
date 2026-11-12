#!/usr/bin/env python3
"""What the live board draws, in one module (three were merged to keep the skill package under its file cap):

1. The Dependencies graph (issues 94 and 123):
The live board's Dependencies section as a graph a phone can read (issues 94 and 123): running and queued goals, top
to bottom, one band per depth, at most 60 columns, with a legend. Pure functions; imported, not run.

  [>] running   [=] holding or paused   [ ] queued   [?] waiting on you   [!] stuck

Goals that wait on nothing come first, packed side by side; each later band lists one goal a line with what it waits on
(`[ ] c <- a, b`), so a goal that waits on several is drawn once with every arrow. A `|` / `v` joins the bands. A goal in
a cycle carries `(cycle)` and the cycle is drawn once, never followed. No goals: `- (none)`.

2. Issues lines a phone can read (issue 97):
Issues lines a phone can read (issue 97). A stopped or failed goal is shown by its cause in plain words, never by
the agent's raw output, and goals stopped by one cause share one line: "usage limit: 4 goals paused until Nov 11
16:00; they resume by themselves" (only where resume_on_limit is on). While every live goal is paused by one cause, the finish says "paused until ...".
Pure functions; imported by live_board.py, not run.

  cause(run)          (key, words, until): the plain cause of a failed or stopped goal
  stuck(runs)         the Issues lines for failed and stopped goals, grouped by cause, each with its fix
  paused(runs)        "paused until <when>" when all live goals wait out one usage limit, else ""

3. Pull request states and the health verdict, fast (MON-9):
Pull request states for the board, fast (MON-9: the board builds in under 10 seconds). gh is asked in parallel, each
call bounded, and a MERGED answer is kept in <git common dir>/loop/pr-states.json for good (OPEN and CLOSED can change,
so they are asked each time, all at once). The file is written whole through a temp file and os.replace, so
a reader never sees half of it; when two writers race, the last one wins and a lost answer is only asked again.
Imported by live_board.py, board.py and pool.py, not run.

  states(runs, root)  {slug: MERGED|CLOSED|OPEN|""} for each done, unmerged run with a pull request
  state(url, root)    one pull request's state ("" when gh can't say)

4. The per-goal budget and decided-depth lines, and the private-name Issues lines (DEL-8, DEL-6, DEL-9):
Imported by live_board.py (as bb); were board_budget.py.

"""
import concurrent.futures
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import time
import board_page
import board_status as bs

os.environ.update(GIT_TERMINAL_PROMPT="0", GH_PROMPT_DISABLED="1", GIT_EDITOR="true", GIT_ASKPASS="true", SSH_ASKPASS="true")  # no prompt ever blocks

WIDTH = 60
MARKS = {"running": ">", "held": "=", "paused": "=", "holding": "=", "awaiting merge": "=", "done": "=", "queued": " ",
         "waiting": "?", "failed": "!", "stopped": "!", "stuck": "!", "silent": "!", "freezing": ">"}
LEGEND = "[>] running [=] holding [ ] queued [?] you [!] stuck"


def box(node, cut):
    return "[%s] %s%s%s" % (MARKS.get(node.get("mark"), " "), node["slug"], " owned by " + node["owner"] if node.get("owner") else "",
                            " (cycle)" if node["slug"] in cut else "")


def pack(pieces, width, gap="  "):
    """Pieces side by side, wrapped at width; a piece longer than width stands alone (the caller's fit wraps it)."""
    lines, line = [], ""
    for piece in pieces:
        if line and len(line) + len(gap) + len(piece) > width:
            lines.append(line)
            line = ""
        line = piece if not line else line + gap + piece
    return lines + ([line] if line else [])


def cycled(nodes):
    """Slugs that can reach themselves through what they wait on."""
    by = {node["slug"]: node["depends"] for node in nodes}

    def reach(start):
        seen, todo = set(), list(by[start])
        while todo:
            slug = todo.pop()
            if slug not in seen:
                seen.add(slug)
                todo += by.get(slug, [])
        return seen

    return {slug for slug in by if slug in reach(slug)}


def render(items, width=WIDTH):
    """Lines for the Dependencies section. items: dicts with slug, mark and depends (slugs it waits on)."""
    if not items:
        return ["- (none)"]
    known = {node["slug"] for node in items}
    nodes = [dict(node, depends=[d for d in node.get("depends") or [] if d in known]) for node in items]
    cut = cycled(nodes)
    bands = board_page.levels(nodes)
    out = pack([box(node, cut) for node in bands[0]], width) if bands else []
    for band in bands[1:]:
        out += ["  |", "  v"]
        for node in band:
            line = "%s <- %s" % (box(node, cut), ", ".join(node["depends"]))
            out += pack([line], width)
    return out + ["", LEGEND]


LIMIT = re.compile(r"usage limit|rate limit|limit reached|hit your (?:weekly |daily )?limit|out of (?:usage|credits)|quota", re.I)
RESET = re.compile(r"(?:resets?|reset at|until|try again (?:at|after))\s+(?:at\s+)?([A-Z][a-z]{2,8}\.? \d{1,2},? \d{1,2}(?::\d\d)?\s*(?:[ap]m)?|\d{1,2}(?::\d\d)?\s*[ap]m|\d\d:\d\d(?: UTC)?)", re.I)
CAUSES = [
    ("limit", LIMIT, "usage limit"),
    ("permission", re.compile(r"permission|not allowed|denied|unauthori[sz]ed|forbidden", re.I), "a permission was refused"),
    ("tests", re.compile(r"\btests? (?:failed|red)|lane (?:failed|red)|\bFAIL\b|regression", re.I), "its tests failed"),
    ("tries", re.compile(r"3 failed tries|tries used up|stopped after", re.I), "it used up its tries"),
    ("crash", re.compile(r"ended without finishing|traceback|crash|killed|exit code|no STEP", re.I), "its worker ended early"),
]
LIVE = ("running", "waiting", "failed", "stopped")


def text_of(run):
    return " ".join(str(x) for x in ((run.get("report") or {}).get("text"), run.get("finding")) if x)


def cause(run):
    said = text_of(run)
    for key, pattern, words in CAUSES:
        if pattern.search(said):
            found = RESET.search(said) if key == "limit" else None
            return key, words, found.group(1).strip() if found else ""
    return "other", "it %s; see its log" % (run.get("status") or "stopped"), ""


def stuck(runs, auto_resume=False):
    """Grouped lines: one per cause shared by two or more goals, one per goal otherwise. auto_resume is the repo's
    resume_on_limit, so the fix says what really happens after a usage limit. Each line pair stays short;
    live_board.fit wraps anything over 60 columns at word boundaries."""
    groups = {}
    for run in runs:
        if run.get("status") in ("failed", "stopped"):
            key, _, until = cause(run)
            groups.setdefault((key, until) if key == "limit" else key, []).append(run)  # one line per reset time
    out = []
    for key, members in groups.items():
        _, words, until = cause(members[0])
        slugs = [run["slug"] for run in members]
        if isinstance(key, tuple):
            when = " until " + until if until else " until the limit resets"
            out.append("- usage limit: %d goal%s paused%s" % (len(slugs), "" if len(slugs) == 1 else "s", when))
            out.append("    %s" % ", ".join(slugs))
            if auto_resume:  # resume_on_limit is on: watch resumes them after limit_wait
                out.append("    fix: none needed; they resume by themselves after the reset")
            else:
                out.append('    fix: after the reset, type "resume <goal>" for each (resume_on_limit is off)')
        elif len(slugs) > 1:
            out.append("- %d goals stopped: %s" % (len(slugs), words))
            out.append("    %s" % ", ".join(slugs))
            out.append('    fix: look at one, then type "resume <goal>" for each')
        else:
            out.append("- %s is %s: %s" % (slugs[0], members[0].get("status"), words))
            out.append('    fix: look at the problem, then type "resume %s"' % slugs[0])
    return out


def paused(runs):
    live = [run for run in runs if run.get("status") in LIVE]
    if not live or any(run.get("status") not in ("failed", "stopped") or cause(run)[0] != "limit" for run in live):
        return ""
    until = next((cause(run)[2] for run in live if cause(run)[2]), "")
    return "paused until " + (until or "the usage limit resets")


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


def fresh(entry):
    return isinstance(entry, dict) and entry.get("state") == "MERGED"  # only a merge is final; OPEN and CLOSED are asked anew


def lookup(urls, root):
    """{url: state} for each url, from the cache where fresh, else from gh in parallel. No gh at all: every state unknown."""
    if not shutil.which("gh"):
        return {url: "" for url in urls}
    path, now = cache_path(root), time.time()
    cache = load(path) if path else {}
    out = {url: cache[url]["state"] for url in urls if fresh(cache.get(url))}
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
            if os.path.exists(path + ".lock") and time.time() - os.path.getmtime(path + ".lock") > 900:
                os.remove(path + ".lock")  # a refresher that died left its lock: start again
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


# ---- budget, decided depth and private-name Issues lines (DEL-8, DEL-6, DEL-9)
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
    """3.0M, 0.4M, 25k or 500: a small budget never reads as 0.0M."""
    return "%.1fM" % (n / 1e6) if n >= 100000 else "%dk" % round(n / 1000) if n >= 1000 else "%d" % n


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
        wait = " ".join(str(run.get("release_pr_waiting") or "").split())
        if wait and not run.get("release_url"):  # nothing reruns merge.py by itself once the goal's PR merged
            out += ["- %s: the release pull request waits: %s" % (run["slug"], wait[:200]),
                    "    fix: run merge.py %s again once its checks pass; it merges the release PR and creates the release" % run["slug"]]
        text = " ".join(str(run.get("finding_error") or "").split())
        if text:
            said, _, fix = text.partition(". Fix: ")
            out += ["- %s: a finding stayed local: %s" % (run["slug"], said[:200]),
                    "    fix: %s" % (fix[:200] or "remove what the scan found, then push the finding commit")]
    return out
