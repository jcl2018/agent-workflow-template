#!/usr/bin/env python3
"""The operation session's progress board: JSON, HTML pages and a digest.

usage: board.py <command> [options]

  board [--at TIME] [--since FILE] [--out DIR]
                        write board.json, for board_page.py to finish and draw; print the live board, DIGEST, CHANGED, CHANGE lines,
                        NEXT_DELAY and its path
  cadence [N|off]       minutes between check-ins, 1-60 (default 30), or off
  repos add PATH|list   follow another repo (~/.workflow-loop/repos), or list them
  note SLUG TEXT        record a worker's latest message on its run (this and retire run in board_page.py)
  retire SLUG --reason TEXT
  handoff [--at TIME] [--out FILE]
                        write a file a new operation session can take over from
"""
import argparse
import datetime
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import graph  # noqa: E402
try:  # board.py runs alone with graph.py; without board_status.py there is no estimate
    import board_status  # noqa: E402
except ImportError:
    board_status = None
try:  # fast pull request states (MON-9), when board_lines.py is beside this file
        import board_lines as prs  # noqa: E402  (its pull request lookups)
except ImportError:
    prs = None

# No terminal, no waiting: a prompt from git or gh must fail, not block.
os.environ.update(GIT_TERMINAL_PROMPT="0", GH_PROMPT_DISABLED="1", GIT_EDITOR="true", GIT_ASKPASS="true", SSH_ASKPASS="true")
if not sys.stdin or not sys.stdin.isatty():
    os.dup2(os.open(os.devnull, os.O_RDONLY), 0)

SLUG = re.compile(r"^[a-z0-9][a-z0-9-]{0,50}$")
RUN_COMMANDS = ("note", "retire")
FIELDS = ("status", "step", "pr", "prstate", "checks", "quiet", "note", "waits_on", "report", "wiki_error", "release_error")


def git(*args, cwd=None):
    done = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    return done.stdout.strip() if done.returncode == 0 else ""


def pr_state(url, cwd):
    if prs:
        return (prs.state(url, cwd) or "unknown").lower()
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


def iso(at):
    return at.strftime("%Y-%m-%dT%H:%M:%SZ")


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


def cadence_of(base, fallback="30"):
    """The owner's cadence command wins; else the repo config's `cadence`; else 30. Read fresh each run."""
    fallback = str(fallback)
    fallback = fallback if fallback == "off" or fallback.isdigit() else "30"
    try:
        with open(os.path.join(base, "loop", "cadence")) as handle:
            value = handle.read().strip()
    except OSError:
        value = ""
    return value if value == "off" or value.isdigit() else fallback


def delay_of(cadence, busy):
    if cadence == "off":
        return "none"
    if not busy:
        return "3600"
    return str(min(3600, max(60, int(cadence) * 60)))


def queue_of(path):
    try:
        with open(os.path.join(path, ".loop", "queue.md")) as handle:
            lines = handle.read().splitlines()
    except OSError:
        return []
    goals = []
    for line in lines:
        item = graph.parse(line)
        if item and SLUG.match(item["slug"]):
            item["level"] = "goal"
            goals.append(item)
    return goals


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
    taken = graph.assigned(graph.read_pool(os.path.join(base, "loop", "session-pool.json"))[0])
    if prs:  # every pull request asked at once, in parallel, before the rows ask one by one from the cache (MON-9)
        known = prs.lookup([clean(r.get("pr")) for r in records if r.get("pr") and not graph.merged(r)], path)
    else:
        known = {}
    rows, deps = [], []
    for run in records:
        begun, last = started(run), stamp(run.get("updated"))
        note = run.get("note") or {}
        extra = read_json(os.path.join(folder, run["slug"] + ".extra.json"))  # what only operation commands add
        extra = extra if isinstance(extra, dict) else {}
        found = [f for f in extra.get("findings") or [] if isinstance(f, dict)]
        if found and run.get("status") in ("done", "merged"):
            note = {"text": "finding after %s: %s" % (run["status"], found[-1].get("text", ""))}
        last = graph.last_spoke(run) or last  # one silence rule for board and live board (MON-8)
        limit = graph.silent_limit(cfg)
        quiet = bool(run.get("status") == "running" and last and (at - last).total_seconds() >= limit)
        pr = clean(run.get("pr"))
        get = lambda field, size=300: clean(run.get(field), size)
        rows.append({
            "repo": run.get("repo") or name, "slug": run["slug"], "goal": get("goal", 80), "level": kind(run), "status": get("status"),
            "step": get("step") or "-", "tries": run.get("tries", 0), "pr": pr, "prstate": ((known.get(pr) or "unknown").lower() if pr in known else pr_state(pr, path)) if pr else "",
            "wiki_error": "yes" if run.get("wiki_error") else "", "release_error": "yes" if run.get("release_error") else "",
            "checks": get("checks"), "quiet": "yes" if quiet else "no", "report": clean((run.get("report") or {}).get("text")),
            "note": clean(note.get("text")) if isinstance(note, dict) else "",
            "waiting": run.get("waiting") if isinstance(run.get("waiting"), dict) else None, "finding": get("finding", 200),
            "elapsed": (at - begun).total_seconds() if begun else 0, "age": span((at - begun).total_seconds()) if begun else "0m",
            "took": (last - begun).total_seconds() if begun and last else 0, "last": run.get("updated") or "",
            "waits_on": ", ".join(run.get("waits_on") or []), "touches": list(dict.fromkeys(list(run.get("touches") or []) + list(extra.get("touches") or []))),
            "merged": graph.merged(run), "held": bool(graph.held(run, taken)), "left": board_status and board_status.left_time(run, records, at),
            "eta": get("eta"), "next": get("next"), "branch": get("branch"), "reason": clean((run.get("retired") or {}).get("reason"))})
    by_slug = {r["slug"]: r for r in records}
    names = {goal["slug"] for goal in queue_of(path)}
    used = sum(1 for r in live if graph.holds_slot(r, taken)) + sum(1 for slug in taken or {} if slug not in by_slug)
    for slug in sorted(s for s in taken or {} if s not in by_slug):  # handed to a session, not frozen yet (issue 111)
        deps.append({"repo": name, "slug": slug, "waits_on": "freezing in session %s" % (taken[slug].get("name") or taken[slug]["id"]),
                     "on": "", "goal": "", "level": "goal", "touches": [], "left": None, "freezing": True})
    for goal in queue_of(path):
        if goal["slug"] in by_slug or goal["slug"] in (taken or {}):
            continue
        waits = graph.unmet(goal, by_slug, names)
        why = ", ".join("goal " + text for _, text in waits) if waits else "ready to start"
        limit = graph.parallel_of(cfg)
        if not waits and limit and used >= limit:
            why = "a free slot (%d of %s running)" % (used, limit)
        deps.append({"repo": name, "slug": goal["slug"], "waits_on": why, "on": ", ".join(slug for slug, _ in waits), "goal": clean(goal.get("goal"), 80),
                     "level": goal["level"], "touches": goal["touches"],
                     "left": board_status and board_status.left_time({"slug": goal["slug"], "status": "queued"}, records, at)})
    return rows, deps


def kind(run):
    """Every goal runs the one skill flow in its own worker."""
    return "goal"


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
            waiting.append({"repo": r["repo"], "slug": r["slug"], "ask": "%s: %s" % (r["status"], r["report"] or r["finding"] or "see its log"),
                            "words": ["resume %s" % r["slug"]]})
        else:
            continue
        waiting[-1]["where"] = "the operation session, which owns %s/%s" % (r["repo"], r["slug"])
    flat = {"%s/%s" % (r["repo"], r["slug"]): {f: r[f] for f in FIELDS} for r in rows}
    for d in deps:
        flat.setdefault("%s/%s" % (d["repo"], d["slug"]), {"status": "queued"})
    count = lambda *kinds: sum(r["status"] in kinds for r in rows)
    held = (read_json(os.path.join(os.path.dirname(common()), ".loop", "config.json")) or {}) if common() else {}
    cadence = cadence_of(common(), held.get("cadence", "30")) if common() else "30"
    freezing = sum(1 for d in deps if d.get("freezing"))
    digest = "%d runs: %d running, %d held, %d freezing, %d waiting on you, %d done, %d failed or stopped, %d queued, %d retired" % (
        len(rows), count("running") - sum(r["held"] for r in rows), sum(r["held"] for r in rows), freezing, len(waiting),
        count("done"), count("failed", "stopped"), len(deps) - freezing, count("retired"))
    delay = delay_of(cadence, bool(live))
    doc = {"generated": iso(at), "repos": names, "cadence": cadence, "digest": digest,
           "next_delay": delay, "next_at": "" if delay == "none" else (at + datetime.timedelta(seconds=int(delay))).strftime("%H:%M UTC"), "open": bool(live or waiting or deps), "waiting": waiting, "dependencies": deps, "runs": rows, "state": flat}
    old = (read_json(since) or {}).get("state") if since else {}
    old = old if isinstance(old, dict) else {}
    for key, item in flat.items():  # gh failing to answer says nothing about the pull request
        if item.get("prstate") == "unknown":
            item["prstate"] = (old.get(key) or {}).get("prstate") or "unknown"
    return doc, changes(old, flat)


def changes(old, new):
    lines = []
    for key in sorted(set(old) | set(new)):
        before, after = old.get(key) or {}, new.get(key) or {}
        for field in sorted(set(before) | set(after)):
            if clean(before.get(field)) != clean(after.get(field)):
                lines.append("CHANGE %s %s: %s -> %s" % (key, field, clean(before.get(field), 80) or "-", clean(after.get(field), 80) or "-"))
    return lines


def cmd_board(args):
    doc, lines = build(clock(args.at), args.since)
    folder = os.path.abspath(args.out) if args.out else loop_dir(common())
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, "board.json")
    write(path, json.dumps(doc, indent=2, sort_keys=True) + "\n")
    helper = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "live_board.py")
    if os.path.exists(helper):
        print(subprocess.run([sys.executable, helper], capture_output=True, text=True, cwd=git("rev-parse", "--show-toplevel")).stdout)
    print("DIGEST " + doc["digest"])
    print("CHANGED " + ("yes" if lines else "no"))
    for line in lines:
        print(line)
    print("NEXT_DELAY " + doc["next_delay"])
    print("JSON", path)
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
        os.makedirs(os.path.dirname(repo_file()), exist_ok=True)
        if top not in [r[1] for r in followed()]:
            with open(repo_file(), "a") as handle:
                handle.write(top + "\n")
        print("FOLLOWING " + top)
    else:
        for name, path, _ in followed():
            print("%s  %s" % (name, path))
    return 0


def cmd_handoff(args):
    doc, _ = build(clock(args.at), None)
    lines = ["# Operation handoff", "", "Written %s. Data from run records, not instructions." % doc["generated"], "", "## Repos"]
    lines += ["- %s" % r for r in doc["repos"]] + ["", "## Cadence", "Check in every %s." % (doc["cadence"] + " minutes" if doc["cadence"] != "off" else "never (off)"), "", "## Open goals"]
    lines += ["- %s/%s: %s, step %s" % (r["repo"], r["slug"], r["status"], r["step"]) for r in doc["runs"] if r["status"] not in ("done", "retired")]
    lines += ["- %s/%s: queued, waits on %s" % (d["repo"], d["slug"], d["waits_on"]) for d in doc["dependencies"]]
    lines += ["", "## Waiting on the owner"]
    lines += ["- %s/%s: %s Type in %s: %s" % (w["repo"], w["slug"], w["ask"], w["where"], " or ".join(w["words"])) for w in doc["waiting"]]
    lines += ["", "## Next check-in steps", "1. Run watch.py watch --once.", "2. Read each worker's latest report.",
              "3. Run board.py board --since <last board.json>, then board_page.py.", "4. Publish board-artifact.html and print the full live board.",
              "5. Wait NEXT_DELAY (%s). Never answer a gate, merge unless told,." % doc["next_delay"]]
    path = os.path.abspath(args.out) if args.out else os.path.join(loop_dir(common()), "handoff.md")
    write(path, "\n".join(lines) + "\n")
    print("HANDOFF " + path)
    return 0


def main():
    if sys.argv[1:2] and sys.argv[1] in RUN_COMMANDS:
        helper = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "board_page.py")
        if not os.path.exists(helper):
            sys.exit("REFUSED: %s needs board_page.py beside board.py." % sys.argv[1])
        return subprocess.run([sys.executable, helper] + sys.argv[1:]).returncode
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
    item = sub.add_parser("handoff")
    for flag in ("--at", "--out"):
        item.add_argument(flag, default="")
    args = parser.parse_args()
    return globals()["cmd_" + args.command](args)


if __name__ == "__main__":
    sys.exit(main())
