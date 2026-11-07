#!/usr/bin/env python3
"""Show where every goal stands: a report and one self-contained HTML page.

usage: monitor.py <command> [options]

  report                 print every run, what waits on you, and findings
  dashboard [--out FILE] write one self-contained HTML page

Run state lives in <git common dir>/loop/. It runs git and nothing else. watch.py starts and moves goals.
"""
import argparse
import datetime
import html
import json
import os
import re
import subprocess
import sys

SLUG = re.compile(r"^[a-z0-9][a-z0-9-]{0,50}$")
LEVELS = ("0", "1", "2")
LIVE = ("running", "waiting")


def git(*args, cwd=None, check=True):
    done = subprocess.run(["git"] + list(args), cwd=cwd, capture_output=True, text=True)
    if check and done.returncode:
        sys.exit("REFUSED: git %s: %s" % (" ".join(args), done.stderr.strip()))
    return done.stdout.strip() if done.returncode == 0 else ""


def now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def common():
    return os.path.abspath(git("rev-parse", "--git-common-dir"))


def loop_dir(*parts):
    path = os.path.join(common(), "loop", *parts)
    os.makedirs(path, exist_ok=True)
    return path


def root():
    return git("rev-parse", "--show-toplevel")


def config():
    try:
        with open(os.path.join(root(), ".loop", "config.json")) as handle:
            return json.load(handle)
    except (OSError, ValueError):
        sys.exit("REFUSED: no readable .loop/config.json. Fix: run workflow-setup and merge its branch.")


def record_path(slug):
    return os.path.join(loop_dir("runs"), slug + ".json")


def load(slug):
    try:
        with open(record_path(slug)) as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return None


def save(state, note=None):
    state["updated"] = now()
    if note:
        state.setdefault("log", []).append("%s %s" % (state["updated"], note))
        print("%s %s: %s" % (state["updated"], state["slug"], note))
    path = record_path(state["slug"])
    temp = path + ".%d.tmp" % os.getpid()
    with open(temp, "w") as handle:
        json.dump(state, handle, indent=2)
    os.replace(temp, path)


def runs():
    found = []
    folder = loop_dir("runs")
    for name in sorted(os.listdir(folder)):
        if name.endswith(".json"):
            state = load(name[:-5])
            if state and state.get("slug"):
                found.append(state)
    return found


def parse_queue():
    """Goals from .loop/queue.md, one `- slug: .. | key: ..` line each. Other lines are ignored."""
    try:
        with open(os.path.join(root(), ".loop", "queue.md")) as handle:
            lines = handle.read().splitlines()
    except OSError:
        return []
    goals, seen = [], set()
    for line in lines:
        if not line.startswith("- slug:"):
            continue
        item = {"done": [], "touches": [], "level": "0", "release": ""}
        for part in line.strip()[2:].split("|"):
            key, _, value = part.partition(":")
            key, value = key.strip(), " ".join(value.split())
            if key == "done" and value:
                item["done"].append(value)
            elif key == "touches":
                item["touches"] = [path.strip() for path in value.split(",") if path.strip()]
            elif key in ("slug", "goal", "level", "release"):
                item[key] = value
        slug = item.get("slug", "")
        if not SLUG.match(slug) or slug in seen or not item.get("goal") or not item["done"]:
            print("SKIPPED queue line (needs a good slug, a goal and a done line): %s" % line.strip()[:80])
            continue
        if item["level"] not in LEVELS:
            print("SKIPPED queue line: level %r is not 0, 1 or 2 (the old names minimum, quick, standard and full are gone): %s"
                  % (item["level"], line.strip()[:60]))
            continue
        seen.add(slug)
        goals.append(item)
    return goals


def overlap(a, b):
    a, b = os.path.normpath(a), os.path.normpath(b)
    return a == b or a.startswith(b + os.sep) or b.startswith(a + os.sep)


def blocker(goal, live):
    for state in live:
        if any(overlap(mine, theirs) for mine in goal["touches"] for theirs in state.get("touches") or []):
            return state["slug"]
    return ""


def alive(pid):
    if not pid:
        return False
    try:
        if os.waitpid(pid, os.WNOHANG)[0] == pid:
            return False
    except ChildProcessError:
        pass
    except OSError:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def log_tail(slug):
    try:
        with open(os.path.join(loop_dir("logs"), slug + ".log"), errors="replace") as handle:
            return handle.read()[-200:]
    except OSError:
        return ""


def refresh():
    """A running record whose agent is gone has failed. A visible session has no process to check."""
    for state in runs():
        if state.get("status") == "running" and not state.get("external") and not alive(state.get("pid")):
            fresh = load(state["slug"])
            if fresh and fresh.get("status") == "running" and fresh.get("pid") == state.get("pid"):
                fresh["status"] = "failed"
                fresh["finding"] = log_tail(state["slug"])
                save(fresh, "failed: agent pid %s ended without finishing" % state.get("pid"))


def plan(limit):
    """Split queued goals into those that may start now and those that wait, with the reason."""
    records = {state["slug"]: state for state in runs()}
    live = [state for state in records.values() if state.get("status") in LIVE]
    start, held = [], []
    for goal in parse_queue():
        if goal["slug"] in records:
            continue
        hit = blocker(goal, live)
        if hit:
            held.append((goal, "conflict with %s" % hit))
        elif len(live) >= limit:
            held.append((goal, "slots full (%d of %d)" % (len(live), limit)))
        else:
            start.append(goal)
            live.append({"slug": goal["slug"], "touches": goal["touches"], "status": "running"})
    return start, held


def facts():
    refresh()
    cfg = config()
    states = runs()
    ready, held = plan(int(cfg.get("parallel", 3) or 3))
    return states, held + [(goal, "ready; watch starts it") for goal in ready]


def cmd_report(args):
    states, held = facts()
    rows = [("SLUG", "LEVEL", "STATUS", "STEP", "TRIES", "PR")]
    for state in states:
        rows.append((state["slug"], state.get("level", ""), state.get("status", ""), state.get("step") or "-",
                     str(state.get("tries", 0)), state.get("pr") or "-"))
    widths = [max(len(row[col]) for row in rows) for col in range(6)]
    for row in rows:
        print("  ".join(cell.ljust(widths[col]) for col, cell in enumerate(row)).rstrip())
    if len(rows) == 1:
        print("(no runs yet)")
    print("\nWAITING ON YOU")
    waiting = [state for state in states if state.get("status") == "waiting"]
    for state in waiting:
        wait = state.get("waiting") or {}
        print("- %s: %s" % (state["slug"], wait.get("ask", "")))
        for words in wait.get("words") or []:
            print("    type: %s" % words)
    if not waiting:
        print("(nothing)")
    print("\nFINDINGS")
    found = [state for state in states if state.get("status") in ("stopped", "failed")]
    for state in found:
        print("- %s (%s): %s" % (state["slug"], state["status"], " ".join(str(state.get("finding", "")).split())))
    if not found:
        print("(none)")
    print("\nQUEUED, NOT STARTED")
    for goal, why in held:
        print("- %s: %s" % (goal["slug"], why))
    if not held:
        print("(none)")
    return 0


CSS = """:root{--bg:#fff;--fg:#1b1b1b;--mute:#666;--line:#ddd;--warn-bg:#fff4d6;--warn:#8a5a00;--bad:#b00020}
@media (prefers-color-scheme:dark){:root{--bg:#141414;--fg:#eee;--mute:#aaa;--line:#333;--warn-bg:#3a2e10;
--warn:#ffcc66;--bad:#ff6b81}}
body{background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,sans-serif;margin:0 auto;max-width:960px;
padding:16px}h1{font-size:22px}h2{font-size:17px;margin-top:28px}table{border-collapse:collapse;width:100%}
th,td{border-bottom:1px solid var(--line);padding:6px 8px;text-align:left;vertical-align:top}
.wait{background:var(--warn-bg);border:2px solid var(--warn);border-radius:8px;padding:12px 16px}
.wait h2{color:var(--warn);margin-top:0}code{font-size:16px;font-weight:600}.mute{color:var(--mute)}
.failed,.stopped{color:var(--bad);font-weight:600}.scroll{overflow-x:auto}"""


def cmd_dashboard(args):
    states, held = facts()
    e = lambda value: html.escape(str(value if value is not None else ""), quote=True)
    out = ["<!doctype html><html lang=en><head><meta charset=utf-8>",
           "<meta name=viewport content='width=device-width,initial-scale=1'><title>Loop dashboard</title>",
           "<style>%s</style></head><body><h1>Loop dashboard</h1>" % CSS,
           "<p class=mute>Written %s from %s</p>" % (e(now()), e(root()))]
    waiting = [state for state in states if state.get("status") == "waiting"]
    out.append("<section class=wait><h2>Waiting on you (%d)</h2>" % len(waiting))
    for state in waiting:
        wait = state.get("waiting") or {}
        out.append("<p><b>%s</b>: %s</p><ul>" % (e(state["slug"]), e(wait.get("ask", ""))))
        out.extend("<li>Type <code>%s</code></li>" % e(words) for words in wait.get("words") or [])
        out.append("</ul>")
    if not waiting:
        out.append("<p>Nothing.</p>")
    out.append("</section><h2>Runs</h2><div class=scroll><table><tr><th>Slug</th><th>Level</th><th>Status</th>"
               "<th>Step</th><th>Tries</th><th>Pull request</th></tr>")
    for state in states:
        status = state.get("status", "")
        out.append("<tr><td>%s</td><td>%s</td><td class='%s'>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>" % (
            e(state["slug"]), e(state.get("level")), e(status), e(status), e(state.get("step") or "-"),
            e(state.get("tries", 0)), e(state.get("pr") or "-")))
    out.append("</table></div>" + ("" if states else "<p>No runs yet.</p>"))
    out.append("<h2>Findings</h2><ul>")
    found = [state for state in states if state.get("status") in ("stopped", "failed")]
    out.extend("<li><b>%s</b> (%s): %s</li>" % (e(state["slug"]), e(state["status"]), e(state.get("finding")))
               for state in found)
    out.append(("" if found else "<li>None.</li>") + "</ul><h2>Queued, not started</h2><ul>")
    out.extend("<li><b>%s</b>: %s</li>" % (e(goal["slug"]), e(why)) for goal, why in held)
    out.append(("" if held else "<li>None.</li>") + "</ul></body></html>\n")
    path = os.path.abspath(args.out) if args.out else os.path.join(loop_dir(), "dashboard.html")
    temp = path + ".%d.tmp" % os.getpid()
    with open(temp, "w") as handle:
        handle.write("\n".join(out))
    os.replace(temp, path)
    print(path)
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    item = sub.add_parser("report", help="print the state of every run")
    item.set_defaults(func=cmd_report)
    item = sub.add_parser("dashboard", help="write the HTML dashboard")
    item.add_argument("--out", default="", help="file to write (default <common>/loop/dashboard.html)")
    item.set_defaults(func=cmd_dashboard)
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
