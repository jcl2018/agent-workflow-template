#!/usr/bin/env python3
"""Show where every goal stands: a report and one self-contained HTML page.

usage: monitor.py <command> [options]

  report                 print every run, what waits on you, and findings
  dashboard [--out FILE] write one self-contained HTML page

Run state lives in <git common dir>/loop/. It runs git and nothing else. watch.py starts and moves goals.
"""
import argparse
import datetime
import hashlib
import html
import itertools
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import graph  # noqa: E402

# No terminal, no waiting: a prompt from git or gh must fail, not block.
os.environ.update(GIT_TERMINAL_PROMPT="0", GH_PROMPT_DISABLED="1", GIT_EDITOR="true", GIT_ASKPASS="true", SSH_ASKPASS="true")
if not sys.stdin or not sys.stdin.isatty():
    os.dup2(os.open(os.devnull, os.O_RDONLY), 0)

SLUG = re.compile(r"^[a-z0-9][a-z0-9-]{0,50}$")


CRITERION = re.compile(r"^- ([A-Z]{2,5}-\d+): \*\*(Unreviewed|Reviewed \d{4}-\d\d-\d\d)\*\* (.+?)(?: <!-- reviewed (\w+) -->)?$")


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
        item = graph.parse(line)
        if not item:
            continue
        if not SLUG.match(item["slug"]) or item["slug"] in seen or not item["goal"] or not item["done"]:
            print("SKIPPED queue line (needs a good slug, a goal and a done line): %s" % line.strip()[:80])
            continue
        seen.add(item["slug"])
        goals.append(item)
    return goals


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
    """A running record whose worker is gone has failed. With no pid, there's no process to check."""
    for state in runs():
        if state.get("status") == "running" and state.get("pid") and not alive(state.get("pid")):
            fresh = load(state["slug"])
            if fresh and fresh.get("status") == "running" and fresh.get("pid") == state.get("pid"):
                fresh["status"] = "failed"
                fresh["finding"] = log_tail(state["slug"])
                save(fresh, "failed: agent pid %s ended without finishing" % state.get("pid"))


def pool():
    """The session pool's busy map and why it can't be read (graph.read_pool); report reads it like watch (issue 111)."""
    found, why = graph.read_pool(os.path.join(loop_dir(), "session-pool.json"))
    return graph.assigned(found), why


def plan(limit):
    """Split queued goals into those that may start now and those that wait, with the reason."""
    taken, why = pool()
    return graph.ready(parse_queue(), {state["slug"]: state for state in runs()}, limit, taken, why)


def facts():
    refresh()
    cfg = config()
    states = runs()
    ready, held = plan(graph.parallel_of(cfg))
    return states, held + [(goal, "ready; watch starts it") for goal in ready]


def returned():
    """Reviewed criteria whose wording changed, as (id, page, text). docs.py check fails on each."""
    folder = os.path.join(root(), config().get("wiki_dir") or "docs/wiki")
    found = []
    for name in sorted(os.listdir(folder)) if os.path.isdir(folder) else []:
        with open(os.path.join(folder, name)) as handle:
            lines = handle.read().splitlines()
        for number, match in [(n, CRITERION.match(line)) for n, line in enumerate(lines)]:
            if match:  # the seal covers the text and its indented sub-bullets, as criteria.py's seal_of
                key, stage, text, mark = match.groups()
                below = [x.rstrip() for x in itertools.takewhile(lambda x: x.strip() and x[:1].isspace(), lines[number + 1:])]
                if stage != "Unreviewed" and mark != hashlib.sha256("\n".join([text] + below).encode()).hexdigest()[:8]:
                    found.append((key, name[:-3], text))
    return found


def status_block(fragment=False):
    """The live board, from board_status.py beside this file: the same content in report, board and dashboard."""
    helper = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "board_status.py")
    if not os.path.exists(helper):
        return ""
    return subprocess.run([sys.executable, helper] + ["--html"] * fragment, capture_output=True, text=True, cwd=root()).stdout


def over_budget(states):
    """(slug, line) for each step or test run that reached its time budget, with what it left (the run file's budget_hits)."""
    return [(state["slug"], "%s %s hit its %s-minute budget; left: %s" % (
        hit.get("step"), {"step": "step", "prep": "preparation"}.get(hit.get("kind"), "tests"), hit.get("minutes"), hit.get("left")))
        for state in states for hit in state.get("budget_hits") or [] if isinstance(hit, dict)]


def cmd_report(args):
    states, held = facts()
    print(status_block())
    rows = [("SLUG", "KIND", "STATUS", "STEP", "TRIES", "PR")]
    for state in states:
        rows.append((state["slug"], state.get("kind") or "goal", state.get("status", ""), state.get("step") or "-",
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
    over = over_budget(states)
    if over:  # shown only when there is one, so the usual report keeps its layout
        print("\nBUDGET HITS")
        print("\n".join("- %s: %s" % item for item in over))
    print("\nREVIEWED CRITERIA CHANGED")
    back = returned()
    print("\n".join("- %s (%s): %s" % item for item in back) if back else "(none)")
    taken, _ = pool()
    print("\nHELD OR FREEZING")
    kept = [s for s in states if graph.held(s, taken)]
    for state in kept:
        print("- %s: held since %s, no worker; give it a session (sessions.py bind %s ID)" % (
            state["slug"], state.get("held_at") or state.get("updated") or "?", state["slug"]))
    on_disk = {s["slug"] for s in states}
    for entry in graph.freezing(taken, on_disk):
        print("- %s: freezing in session %s since %s" % (entry["slug"], entry.get("name") or entry["id"], entry.get("since") or "?"))
    if not kept and not graph.freezing(taken, on_disk):
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
           "<p class=mute>Written %s from %s</p>" % (e(now()), e(root())), status_block(True)]
    waiting = [state for state in states if state.get("status") == "waiting"]
    out.append("<section class=wait><h2>Waiting on you (%d)</h2>" % len(waiting))
    for state in waiting:
        wait = state.get("waiting") or {}
        out.append("<p><b>%s</b>: %s</p><ul>" % (e(state["slug"]), e(wait.get("ask", ""))))
        out.extend("<li>Type <code>%s</code></li>" % e(words) for words in wait.get("words") or [])
        out.append("</ul>")
    if not waiting:
        out.append("<p>Nothing.</p>")
    out.append("</section><h2>Runs</h2><div class=scroll><table><tr><th>Slug</th><th>Kind</th><th>Status</th>"
               "<th>Step</th><th>Tries</th><th>Pull request</th></tr>")
    for state in states:
        status = state.get("status", "")
        out.append("<tr><td>%s</td><td>%s</td><td class='%s'>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>" % (
            e(state["slug"]), e(state.get("kind") or "goal"), e(status), e(status), e(state.get("step") or "-"),
            e(state.get("tries", 0)), e(state.get("pr") or "-")))
    out.append("</table></div>" + ("" if states else "<p>No runs yet.</p>"))
    out.append("<h2>Findings</h2><ul>")
    found = [state for state in states if state.get("status") in ("stopped", "failed")]
    out.extend("<li><b>%s</b> (%s): %s</li>" % (e(state["slug"]), e(state["status"]), e(state.get("finding")))
               for state in found)
    over = over_budget(states)
    out.append(("" if found else "<li>None.</li>") + "</ul>" + ("<h2>Budget hits</h2><ul>" + "".join(
        "<li><b>%s</b>: %s</li>" % (e(slug), e(line)) for slug, line in over) + "</ul>" if over else "") + "<h2>Queued, not started</h2><ul>")
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
