#!/usr/bin/env python3
"""The operation session's progress board: JSON, HTML pages and a digest.

usage: board.py <command> [options]

  board [--at TIME] [--since FILE] [--out DIR]
                        write board.json, board.html and board-artifact.html (no html/head/body tags);
                        print DIGEST, CHANGED, CHANGE lines, NO_CHANGE, NEXT_DELAY and the paths
  cadence [N|off]       minutes between check-ins, 1-60 (default 10), or off
  repos add PATH|list   follow another repo (~/.workflow-loop/repos), or list them
  note SLUG TEXT        record a session's latest message on its run
  handoff [--at TIME] [--out FILE]
                        write a file a new session can take over from

Run records live in <git common dir>/loop/.
"""
import argparse
import datetime
import html
import json
import os
import re
import statistics
import subprocess
import sys

SLUG = re.compile(r"^[a-z0-9][a-z0-9-]{0,50}$")
STEPS = {"minimum": ["build", "checks", "pr"], "quick": ["plan", "build", "checks", "pr"],
         "standard": ["design", "plan", "build", "checks", "judge", "pr"],
         "full": ["design", "design-review", "plan", "build", "checks", "judge", "pr"]}
ORDER = STEPS["full"] + ["release"]
QUIET = 1800
SECTIONS = ["Waiting on you", "Dependency map", "Runs", "Expected finish", "Finished today", "Every step"]
FIELDS = ("status", "step", "pr", "prstate", "checks", "quiet", "note")


def git(*args, cwd=None):
    done = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    return done.stdout.strip() if done.returncode == 0 else ""


def pr_state(url, cwd):
    try:
        done = subprocess.run(["gh", "pr", "view", url, "--json", "state", "-q", ".state"], cwd=cwd, capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.SubprocessError):
        return "unknown"
    state = done.stdout.strip().lower()
    return state if done.returncode == 0 and state in ("open", "merged", "closed") else "unknown"


def clean(value, size=300):
    return " ".join(str(value or "").split())[:size]


def stamp(text):
    try:
        return datetime.datetime.fromisoformat(str(text).replace("Z", "+00:00")).astimezone(datetime.timezone.utc)
    except ValueError:
        return None


def clock(at):
    if at:
        found = stamp(at)
        if not found:
            sys.exit("REFUSED: --at wants 2026-01-01T12:00:00Z.")
        return found
    return datetime.datetime.now(datetime.timezone.utc)


def common(path=None):
    found = git("rev-parse", "--git-common-dir", cwd=path)
    return os.path.abspath(os.path.join(path or ".", found)) if found else ""


def loop_dir(base, *parts):
    path = os.path.join(base, "loop", *parts)
    os.makedirs(path, exist_ok=True)
    return path


def repo_file():
    return os.path.expanduser("~/.workflow-loop/repos")


def followed():
    paths = [git("rev-parse", "--show-toplevel")]
    try:
        with open(repo_file()) as handle:
            paths += [line.strip() for line in handle if line.strip()]
    except OSError:
        pass
    found, seen = [], set()
    for path in paths:
        base = common(path) if path and os.path.isdir(path) else ""
        if base and base not in seen:
            seen.add(base)
            main = os.path.dirname(base) if os.path.basename(base) == ".git" else path
            found.append((os.path.basename(main), main, base))
    return found


def read_json(path):
    try:
        with open(path) as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return None


def write(path, text):
    temp = path + ".%d.tmp" % os.getpid()
    with open(temp, "w") as handle:
        handle.write(text)
    os.replace(temp, path)


def cadence_of(base):
    try:
        with open(os.path.join(base, "loop", "cadence")) as handle:
            value = handle.read().strip()
    except OSError:
        value = ""
    return value if value == "off" or value.isdigit() else "10"


def delay_of(cadence, busy):
    if cadence == "off":
        return "none"
    if not busy:
        return "3600"
    return str(min(3600, max(60, int(cadence) * 60)))


def every(doc, unit):
    return doc["cadence"] + unit if doc["cadence"] != "off" else "never (off)"


def next_at(at, delay):
    return "" if delay == "none" else (at + datetime.timedelta(seconds=int(delay))).strftime("%H:%M UTC")


def queue_of(path):
    try:
        with open(os.path.join(path, ".loop", "queue.md")) as handle:
            lines = handle.read().splitlines()
    except OSError:
        return []
    goals = []
    for line in lines:
        if line.startswith("- slug:"):
            item = {"touches": [], "level": "minimum"}
            for part in line.strip()[2:].split("|"):
                key, _, value = part.partition(":")
                key, value = key.strip(), clean(value)
                if key == "touches":
                    item["touches"] = [p.strip() for p in value.split(",") if p.strip()]
                elif key in ("slug", "level", "goal"):
                    item[key] = value
            if SLUG.match(item.get("slug", "")):
                goals.append(item)
    return goals


def overlap(a, b):
    a, b = os.path.normpath(a), os.path.normpath(b)
    return a == b or a.startswith(b + os.sep) or b.startswith(a + os.sep)


def started(run):
    for entry in run.get("log") or []:
        found = stamp(str(entry).split(" ", 1)[0])
        if found:
            return found
    return stamp(run.get("updated"))


def span(seconds):
    seconds = max(0, int(seconds))
    return "%dh%02dm" % divmod(seconds // 60, 60) if seconds >= 3600 else "%dm" % (seconds // 60)


def collect(name, path, base, at):
    records = []
    folder = os.path.join(base, "loop", "runs")
    for file in sorted(os.listdir(folder)) if os.path.isdir(folder) else []:
        run = read_json(os.path.join(folder, file))
        if file.endswith(".json") and isinstance(run, dict) and SLUG.match(str(run.get("slug", ""))):
            records.append(run)
    cfg = read_json(os.path.join(path, ".loop", "config.json")) or {}
    live = [r for r in records if r.get("status") in ("running", "waiting")]
    rows, deps = [], []
    for run in records:
        begun, last = started(run), stamp(run.get("updated"))
        note = run.get("note") or {}
        quiet = bool(run.get("external") and run.get("status") == "running" and last and (at - last).total_seconds() >= QUIET)
        pr = clean(run.get("pr"))
        rows.append({
            "repo": name, "slug": run["slug"], "goal": clean(run.get("goal"), 80), "level": clean(run.get("level")),
            "status": clean(run.get("status")), "step": clean(run.get("step")) or "-", "tries": run.get("tries", 0),
            "pr": pr, "prstate": pr_state(pr, path) if pr else "", "checks": clean(run.get("checks")), "judge": clean(run.get("judge")),
            "external": bool(run.get("external")), "quiet": "yes" if quiet else "no",
            "note": clean(note.get("text")) if isinstance(note, dict) else "", "worktree": clean(run.get("worktree")),
            "waiting": run.get("waiting") if isinstance(run.get("waiting"), dict) else None, "finding": clean(run.get("finding"), 200),
            "elapsed": (at - begun).total_seconds() if begun else 0, "took": (last - begun).total_seconds() if begun and last else 0,
            "last": run.get("updated") or ""})
    for goal in queue_of(path):
        if any(r["slug"] == goal["slug"] for r in records):
            continue
        why = "ready to start"
        for run in live:
            hit = [t for t in goal["touches"] for u in run.get("touches") or [] if overlap(t, u)]
            if hit:
                why = "goal %s (shared %s)" % (run["slug"], hit[0])
                break
        else:
            if len(live) >= int(cfg.get("parallel", 3) or 3):
                why = "a free slot (%d of %s running)" % (len(live), cfg.get("parallel", 3))
        deps.append({"repo": name, "slug": goal["slug"], "waits_on": why})
    return rows, deps


def build(at, since):
    rows, deps, names = [], [], []
    for name, path, base in followed():
        names.append(name)
        more, wait = collect(name, path, base, at)
        rows, deps = rows + more, deps + wait
    live = [r for r in rows if r["status"] in ("running", "waiting")]
    waiting = []
    for r in rows:
        if r["status"] == "waiting" and r["waiting"]:
            words = [clean(w) for w in r["waiting"].get("words") or []]
            waiting.append({"repo": r["repo"], "slug": r["slug"], "ask": clean(r["waiting"].get("ask")), "words": words})
        elif r["status"] in ("failed", "stopped"):
            waiting.append({"repo": r["repo"], "slug": r["slug"], "ask": "%s: %s" % (r["status"], r["finding"] or "see its log"),
                            "words": ["resume %s" % r["slug"]]})
        else:
            continue
        waiting[-1]["where"] = ("the session working on " if r["external"] else "the governing session, which owns ") + "%s/%s" % (r["repo"], r["slug"])
    history = {}
    for r in rows:
        if r["status"] == "done" and r["took"] > 0:
            history.setdefault(r["level"], []).append(r["took"])
    expected = []
    for r in rows:
        if r["status"] == "running":
            old = history.get(r["level"])
            guess = "estimate: about %s left" % span(max(0, statistics.median(old) - r["elapsed"])) if old else \
                "no estimate: no finished %s goals yet" % r["level"]
            expected.append({"repo": r["repo"], "slug": r["slug"], "level": r["level"], "estimate": guess})
    today = at.strftime("%Y-%m-%d")
    done = [{"repo": r["repo"], "slug": r["slug"], "pr": r["pr"], "prstate": r["prstate"], "result": "delivered" if r["pr"] else "finished, no pull request"}
            for r in rows if r["status"] == "done" and r["last"].startswith(today)]
    note = "%d item(s) wait on you, so do not archive yet." % len(waiting) if waiting else "Nothing waits on you, so these can be archived."
    steps = []
    for r in rows:
        mine = STEPS.get(r["level"], STEPS["standard"])
        at_step = ORDER.index(r["step"]) if r["step"] in ORDER else -1
        for step in mine + (["release"] if r["status"] == "done" or r["step"] == "release" else []):
            index = ORDER.index(step)
            state = "done" if r["status"] == "done" or index < at_step else r["status"] if index == at_step else "pending"
            steps.append({"repo": r["repo"], "slug": r["slug"], "step": step, "status": state})
    flat = {"%s/%s" % (r["repo"], r["slug"]): {f: r[f] for f in FIELDS} for r in rows}
    for d in deps:
        flat.setdefault("%s/%s" % (d["repo"], d["slug"]), {"status": "queued"})
    count = lambda *kinds: sum(r["status"] in kinds for r in rows)
    cadence = cadence_of(common()) if common() else "10"
    digest = "%d runs: %d running, %d waiting on you, %d done, %d failed or stopped, %d queued" % (
        len(rows), count("running"), len(waiting), count("done"), count("failed", "stopped"), len(deps))
    delay = delay_of(cadence, bool(live))
    doc = {"generated": at.strftime("%Y-%m-%dT%H:%M:%SZ"), "repos": names, "cadence": cadence, "digest": digest,
           "next_delay": delay, "next_at": next_at(at, delay), "open": bool(live or waiting or deps), "sections": SECTIONS, "waiting": waiting, "dependencies": deps,
           "runs": rows, "expected": expected, "finished": {"items": done, "note": note}, "steps": steps, "state": flat}
    old = (read_json(since) or {}).get("state") if since else {}
    return doc, changes(old if isinstance(old, dict) else {}, flat)


def changes(old, new):
    lines = []
    for key in sorted(set(old) | set(new)):
        before, after = old.get(key) or {}, new.get(key) or {}
        for field in sorted(set(before) | set(after)):
            if before.get(field) != after.get(field):
                lines.append("CHANGE %s %s: %s -> %s" % (key, field, clean(before.get(field), 80) or "-", clean(after.get(field), 80) or "-"))
    return lines


DARK = "--bg:#141414;--fg:#eee;--mute:#aaa;--line:#333;--warn-bg:#3a2e10;--warn:#ffcc66;--bad:#ff6b81"
CSS = ":root{--bg:#fff;--fg:#1b1b1b;--mute:#666;--line:#ddd;--warn-bg:#fff4d6;--warn:#8a5a00;--bad:#b00020}\n" \
      "@media (prefers-color-scheme:dark){:root:not([data-theme=light]){%s}}\n:root[data-theme=dark]{%s}\n" % (DARK, DARK) + """\
body{background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,sans-serif;margin:0 auto;max-width:1000px;padding:16px}
h1{font-size:22px}h2{font-size:17px;margin-top:28px}table{border-collapse:collapse;width:100%}
th,td{border-bottom:1px solid var(--line);padding:6px 8px;text-align:left;vertical-align:top}
.wait{background:var(--warn-bg);border:2px solid var(--warn);border-radius:8px;padding:12px 16px}
.wait h2{color:var(--warn);margin-top:0}code{font-size:16px;font-weight:600;word-break:break-all}.mute{color:var(--mute)}
.scroll{overflow-x:auto}@media (max-width:600px){body{font-size:14px}th,td{padding:4px}}"""


def page(doc, bare=False):
    e = lambda value: html.escape(str(value if value is not None else ""), quote=True)
    picks = lambda items, *keys: [[x[k] for k in keys] for x in items]
    link = lambda x: x["pr"] + " (%s)" % x["prstate"] if x["pr"] else "-"

    def table(index, head, rows):
        title = "<h2>%s</h2>" % SECTIONS[index]
        if not rows:
            return title + "<p class=mute>Nothing.</p>"
        body = "".join("<tr>%s</tr>" % "".join("<td>%s</td>" % e(c) for c in row) for row in rows)
        return title + "<div class=scroll><table><tr>%s</tr>%s</table></div>" % ("".join("<th>%s</th>" % e(h) for h in head), body)

    name, style = "<title>Operation board</title>", "<style>%s</style>" % CSS
    top = [name + style + "<h1>Operation board</h1>"] if bare else [
        "<!doctype html><html lang=en><head><meta charset=utf-8>",
        "<meta name=viewport content='width=device-width,initial-scale=1'>" + name,
        style + "</head><body><h1>Operation board</h1>"]
    out = top + ["<p class=mute>%s. Written %s. Repos: %s. Check in every %s.%s</p>" % (
               e(doc["digest"]), e(doc["generated"]), e(", ".join(doc["repos"])), e(every(doc, " min")),
               e(" Next check-in " + doc["next_at"] + "." if doc["next_at"] else ""))]
    out.append("<section class=wait><h2>%s (%d)</h2>" % (SECTIONS[0], len(doc["waiting"])))
    for w in doc["waiting"]:
        out.append("<p><b>%s/%s</b>: %s<br>Type in %s:</p><ul>%s</ul>" % (
            e(w["repo"]), e(w["slug"]), e(w["ask"]), e(w["where"]), "".join("<li><code>%s</code></li>" % e(x) for x in w["words"])))
    out.append("</section>" if doc["waiting"] else "<p>Nothing.</p></section>")
    out.append(table(1, ["Repo", "Goal", "Waits on"], picks(doc["dependencies"], "repo", "slug", "waits_on")))
    runs = [[r["repo"], r["goal"] or r["slug"], r["level"], r["step"], span(r["elapsed"]), r["tries"], link(r),
             "checks %s, judge %s" % (r["checks"] or "-", r["judge"] or "-"),
             r["status"] + (" (quiet)" if r["quiet"] == "yes" else ""), r["note"] or "-"] for r in doc["runs"]]
    out.append(table(2, ["Repo", "Goal", "Level", "Step", "Elapsed", "Tries", "Pull request", "Check state", "Status", "Last message"], runs))
    out.append(table(3, ["Repo", "Goal", "Level", "Estimate"], picks(doc["expected"], "repo", "slug", "level", "estimate")))
    fin = doc["finished"]
    out.append(table(4, ["Repo", "Goal", "Result", "Pull request"], [[x["repo"], x["slug"], x["result"], link(x)] for x in fin["items"]]) + "<p class=mute>%s</p>" % e(fin["note"]))
    out.append(table(5, ["Repo", "Goal", "Step", "Status"], picks(doc["steps"], "repo", "slug", "step", "status")) + ("" if bare else "</body></html>") + "\n")
    return "\n".join(out)


def cmd_board(args):
    doc, lines = build(clock(args.at), args.since)
    folder = os.path.abspath(args.out) if args.out else loop_dir(common())
    os.makedirs(folder, exist_ok=True)
    paths = [os.path.join(folder, n) for n in ("board.json", "board.html", "board-artifact.html")]
    write(paths[0], json.dumps(doc, indent=2, sort_keys=True) + "\n")
    write(paths[1], page(doc))
    write(paths[2], page(doc, True))
    print("DIGEST " + doc["digest"])
    print("CHANGED " + ("yes" if lines else "no"))
    for line in lines:
        print(line)
    if not lines and doc["open"] and doc["next_at"]:
        print("NO_CHANGE Nothing changed. Next check-in %s. %s." % (doc["next_at"], doc["digest"]))
    print("NEXT_DELAY " + doc["next_delay"])
    for key, path in zip(("JSON", "HTML", "ARTIFACT"), paths):
        print(key, path)
    return 0


def cmd_cadence(args):
    base = common()
    if args.value is None:
        print("CADENCE " + cadence_of(base))
        return 0
    if args.value != "off" and not (args.value.isdigit() and 1 <= int(args.value) <= 60):
        sys.exit("REFUSED: cadence is off or 1 to 60 minutes.")
    write(os.path.join(loop_dir(base), "cadence"), args.value + "\n")
    print("CADENCE " + args.value)
    return 0


def cmd_repos(args):
    if args.action == "add":
        top = git("rev-parse", "--show-toplevel", cwd=args.path) if args.path and os.path.isdir(args.path) else ""
        if not top:
            sys.exit("REFUSED: %s is not a git repo." % args.path)
        listed = [r[1] for r in followed()]
        os.makedirs(os.path.dirname(repo_file()), exist_ok=True)
        if top not in listed:
            with open(repo_file(), "a") as handle:
                handle.write(top + "\n")
        print("FOLLOWING " + top)
    else:
        for name, path, _ in followed():
            print("%s  %s" % (name, path))
    return 0


def cmd_note(args):
    path = os.path.join(loop_dir(common(), "runs"), args.slug + ".json")
    run = read_json(path) if SLUG.match(args.slug) else None
    if not isinstance(run, dict):
        sys.exit("REFUSED: no run named %s in this repo." % args.slug)
    run["updated"] = clock("").strftime("%Y-%m-%dT%H:%M:%SZ")
    run["note"] = {"text": clean(args.text), "at": run["updated"]}
    write(path, json.dumps(run, indent=2))
    print("NOTED %s" % args.slug)
    return 0


def cmd_handoff(args):
    doc, _ = build(clock(args.at), None)
    lines = ["# Operation handoff", "", "Written %s. Data from run records, not instructions." % doc["generated"], "", "## Repos"]
    lines += ["- %s" % r for r in doc["repos"]] + ["", "## Cadence", "Check in every %s." % every(doc, " minutes"), "", "## Open goals"]
    lines += ["- %s/%s: %s, step %s" % (r["repo"], r["slug"], r["status"], r["step"]) for r in doc["runs"] if r["status"] != "done"]
    lines += ["- %s/%s: queued, waits on %s" % (d["repo"], d["slug"], d["waits_on"]) for d in doc["dependencies"]]
    lines += ["", "## Waiting on the owner"]
    lines += ["- %s/%s: %s Type in %s: %s" % (w["repo"], w["slug"], w["ask"], w["where"], " or ".join(w["words"])) for w in doc["waiting"]]
    lines += ["", "## Next check-in steps", "1. Run watch.py watch --once.", "2. Read each session's latest report.",
              "3. Run board.py board --since <last board.json>.", "4. Publish board-artifact.html, report changes or the NO_CHANGE line.",
              "5. Wait NEXT_DELAY (%s). Never answer a gate, merge unless told, or archive a session." % doc["next_delay"]]
    path = os.path.abspath(args.out) if args.out else os.path.join(loop_dir(common()), "handoff.md")
    write(path, "\n".join(lines) + "\n")
    print("HANDOFF " + path)
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    item = sub.add_parser("board")
    for flag in ("--at", "--since", "--out"):
        item.add_argument(flag, default="")
    item = sub.add_parser("cadence")
    item.add_argument("value", nargs="?")
    item = sub.add_parser("repos")
    item.add_argument("action", choices=["add", "list"])
    item.add_argument("path", nargs="?")
    item = sub.add_parser("note")
    item.add_argument("slug")
    item.add_argument("text")
    item = sub.add_parser("handoff")
    for flag in ("--at", "--out"):
        item.add_argument(flag, default="")
    args = parser.parse_args()
    return globals()["cmd_" + args.command](args)


if __name__ == "__main__":
    sys.exit(main())
