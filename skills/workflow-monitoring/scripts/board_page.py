#!/usr/bin/env python3
"""Draw the live board from board.json: board.html and board-artifact.html; change run records; the template lag; and
the roadmap as a dependency graph.

usage: board_page.py [--in FILE] [--out DIR]
       board_page.py note SLUG TEXT | retire SLUG --reason TEXT | checkin   (board.py forwards these here)
       board_page.py lag | migrate

Reads board.json (default <git common dir>/loop/board.json) and writes both pages beside it, or into --out. Both show the live
board that live_board.py prints, so the page and the text agree. board-artifact.html has no doctype, html, head or body tags.
The pages have no scripts and load nothing from the network.

Run records: `note SLUG TEXT` records a worker's latest message on its run; `retire SLUG --reason TEXT` retires it;
`checkin` marks now as the last check-in.

Template lag (template_lag, which live_board.py calls; `lag` prints the Issues lines): each followed repo on an older
template version than the operator's installed skills. The baseline is the installed workflow-package.json beside the
skills, else a checkout's VERSION. Each repo's version is template_version in its base branch's .loop/config.json; a
repo with none reads "template version unknown". A repo that holds the board's own skills checkout is the template
itself and is skipped. It runs git and nothing else. `migrate` (operate.py runs it each pass, queue_migrations) queues one
`migrate-<repo>` goal in each such repo through goal.py queue and prints the Issues lines for what it did not queue.

Status graph (span, mark, chain, unknown, total, levels, render_text, ...; shared by the live board): a node is a dict:
slug, mark, depends (slugs it waits on), stage (0 to 8, steps begun), left (seconds still needed, 0 when nothing is, None
when there is no estimate yet). Marks: merged, awaiting merge, running, waiting, failed, queued, and unknown for a
dependency that is no goal here. The total is the longest chain of what is left through the dependencies, because goals
that don't wait on each other run side by side; it is never the sum. Pure functions, nothing read from disk.
"""
import argparse
import datetime
import html
import json
import os
import re
import subprocess
import sys

# No terminal, no waiting: a prompt from git or gh must fail, not block.
os.environ.update(GIT_TERMINAL_PROMPT="0", GH_PROMPT_DISABLED="1", GIT_EDITOR="true", GIT_ASKPASS="true", SSH_ASKPASS="true")

DARK = "--bg:#141414;--fg:#eee;--mute:#aaa;--line:#333"

CSS = ":root{--bg:#fff;--fg:#1b1b1b;--mute:#666;--line:#ddd}\n" \
      "@media (prefers-color-scheme:dark){:root:not([data-theme=light]){%s}}\n:root[data-theme=dark]{%s}\n" % (DARK, DARK) + """\
body{background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,sans-serif;margin:0 auto;max-width:1000px;padding:16px}
h1{font-size:22px}.mute{color:var(--mute)}pre{font:14px/1.5 ui-monospace,monospace;white-space:pre-wrap;overflow-wrap:anywhere;margin:0}"""


def esc(value):
    return html.escape(str(value if value is not None else ""), quote=True)

def page(doc, bare=False):
    name, style = "<title>Operation board</title>", "<style>%s</style>" % CSS
    out = [name + style + "<h1>Operation board</h1>"] if bare else [
        "<!doctype html><html lang=en><head><meta charset=utf-8>",
        "<meta name=viewport content='width=device-width,initial-scale=1'>" + name,
        style + "</head><body><h1>Operation board</h1>"]
    every = doc["cadence"] + " min" if doc["cadence"] != "off" else "never (off)"
    out.append("<p class=mute>%s. Written %s. Check in every %s.%s</p>" % (
        esc(doc["digest"]), esc(doc["generated"]), esc(every), esc(" Next check-in " + doc["next_at"] + "." if doc["next_at"] else "")))
    helper = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "live_board.py")
    if os.path.exists(helper):
        out.append(subprocess.run([sys.executable, helper, "--html"], capture_output=True, text=True).stdout)
    return "\n".join(out) + ("" if bare else "</body></html>") + "\n"

def write(path, text):
    temp = path + ".%d.tmp" % os.getpid()
    with open(temp, "w") as handle:
        handle.write(text)
    os.replace(temp, path)


def draw_main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--in", dest="source", default="")
    parser.add_argument("--out", default="")
    args = parser.parse_args()
    found = subprocess.run(["git", "rev-parse", "--git-common-dir"], capture_output=True, text=True).stdout.strip()
    path = os.path.abspath(args.source or os.path.join(found, "loop", "board.json"))
    try:
        with open(path) as handle:
            doc = json.load(handle)
    except (OSError, ValueError):
        sys.exit("REFUSED: no readable %s. Fix: run board.py board first." % path)
    folder = os.path.abspath(args.out) if args.out else os.path.dirname(path)
    os.makedirs(folder, exist_ok=True)
    write(os.path.join(folder, "board.html"), page(doc))
    write(os.path.join(folder, "board-artifact.html"), page(doc, True))
    for name, file in (("HTML", "board.html"), ("ARTIFACT", "board-artifact.html")):
        print(name, os.path.join(folder, file))
    return 0


# Run records (board.py forwards note, retire and checkin here).

RUNS_DOC = """Change run records for board.py, which forwards these commands here.

usage: board_page.py <command> [options]

  note SLUG TEXT        record a worker's latest message on its run
  retire SLUG --reason TEXT
  checkin               mark now as the last check-in; marks the last check-in
"""
SLUG = re.compile(r"^[a-z0-9][a-z0-9-]{0,50}$")


def clean(value, size=300):
    return " ".join(str(value or "").split())[:size]


def now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def common():
    done = subprocess.run(["git", "rev-parse", "--git-common-dir"], capture_output=True, text=True)
    return os.path.abspath(done.stdout.strip()) if done.returncode == 0 else ""


def loop_dir(base, *parts):
    path = os.path.join(base, "loop", *parts)
    os.makedirs(path, exist_ok=True)
    return path


def read_json(path):
    try:
        with open(path) as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return None


def run_of(slug):
    path = os.path.join(loop_dir(common(), "runs"), slug + ".json")
    run = read_json(path) if SLUG.match(slug) else None
    if not isinstance(run, dict):
        sys.exit("REFUSED: no run named %s in this repo." % slug)
    run["updated"] = now()
    return path, run


def cmd_note(args):
    path, run = run_of(args.slug)
    run["note"] = {"text": clean(args.text), "at": run["updated"]}
    write(path, json.dumps(run, indent=2))
    print("NOTED %s" % args.slug)
    return 0


def cmd_retire(args):
    path, run = run_of(args.slug)
    if run.get("status") == "running":
        sys.exit("REFUSED: %s is running. Fix: stop its agent, then run watch --once." % args.slug)
    run["retired"] = {"reason": clean(args.reason), "at": run["updated"]}
    run["status"], run["waiting"] = "retired", None
    run.setdefault("log", []).append("%s retired: %s" % (run["updated"], clean(args.reason)))
    write(path, json.dumps(run, indent=2))
    print("RETIRED %s" % args.slug)
    return 0


def cmd_checkin(args):
    write(os.path.join(loop_dir(common()), "checkin.json"), json.dumps({"at": now()}))
    print("CHECKED IN")
    return 0


def runs_main():
    parser = argparse.ArgumentParser(description=RUNS_DOC, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    item = sub.add_parser("note")
    item.add_argument("slug")
    item.add_argument("text")
    item = sub.add_parser("retire")
    item.add_argument("slug")
    item.add_argument("--reason", required=True)
    sub.add_parser("checkin")
    args = parser.parse_args()
    return globals()["cmd_" + args.command](args)


# The template lag.


def git(*args, cwd=None):
    try:
        done = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.SubprocessError):
        return ""
    return done.stdout.strip() if done.returncode == 0 else ""


SKILLS = os.path.realpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, os.pardir))


def version_key(text):
    """The first three integers of a version; empty or unreadable is older than any version."""
    return tuple(int(x) for x in re.findall(r"\d+", str(text or ""))[:3])


def baseline():
    """The operator's installed template version: workflow-package.json beside the skills, else a checkout's VERSION."""
    held = read_json(os.path.join(SKILLS, "workflow-package.json"))
    if isinstance(held, dict) and held.get("version"):
        return str(held["version"]), False
    try:
        with open(os.path.join(SKILLS, os.pardir, "VERSION")) as handle:
            return handle.read().strip(), True
    except OSError:
        return "", True


def followed(root):
    try:
        with open(os.path.expanduser("~/.workflow-loop/repos")) as handle:
            extra = [line.strip() for line in handle if line.strip()]
    except OSError:
        extra = []
    return list(dict.fromkeys([root] + extra))


def behind(root):
    """[(repo, held, want)] for each followed repo whose base branch holds an older template_version than the baseline, or none. The
    version is read from origin/<base> as last fetched, then the local branch. The board's own checkout is the template: skipped."""
    want, source = baseline()
    out = []
    for repo in followed(root):
        if source and SKILLS.startswith(os.path.realpath(repo) + os.sep) or not os.path.isdir(repo):
            continue
        cfg = read_json(os.path.join(repo, ".loop", "config.json"))
        if not isinstance(cfg, dict):
            continue
        name = cfg.get("base") or "main"
        base = git("show", "origin/%s:.loop/config.json" % name, cwd=repo) or git("show", "%s:.loop/config.json" % name, cwd=repo)
        try:
            held = str((json.loads(base) if base else cfg).get("template_version") or "")
        except ValueError:
            held = str(cfg.get("template_version") or "")
        if not held or version_key(held) < version_key(want):
            out.append((repo, held, want))
    return out


def template_lag(root):
    """Issues lines for each followed repo on an older template version than the operator's installed skills (the baseline)."""
    out = []
    for repo, held, want in behind(root):
        name = os.path.basename(os.path.realpath(repo))
        out.append("- %s: template version unknown" % name if not held else "- %s runs template v%s, older than v%s" % (name, held, want))
        out.append("    fix: ask for workflow-setup update in that repo")
    return out


def queue_migrations(root):
    """Queue one migrate-<repo> goal (goal.py queue, in that repo) for each followed repo behind the template; the Issues lines it has
    to say. Written once per repo: an exact slug match in .loop/queue.md or a goal state (queued, running, waiting) skips it; a finished
    goal for this version with the repo still behind is an Issues line; one for an older version allows migrate-<repo>-v<X-Y-Z>. It
    queues only into a checkout on its base branch whose queue file is unmodified. The queued line stays an uncommitted edit."""
    out = []
    for repo, held, want in behind(root):
        name = re.sub(r"[^a-z0-9]+", "-", os.path.basename(os.path.realpath(repo)).lower()).strip("-") or "repo"
        slug = re.compile(r"^migrate-%s(-v\d+-\d+-\d+)?$" % re.escape(name))
        try:
            with open(os.path.join(repo, ".loop", "queue.md")) as handle:
                queued = re.findall(r"^- slug: (\S+)", handle.read(), re.M)
        except OSError:
            queued = []
        runs = os.path.join(repo, git("rev-parse", "--git-common-dir", cwd=repo) or ".git", "loop", "runs")
        states = {f[:-5]: read_json(os.path.join(runs, f)) or {} for f in (os.listdir(runs) if os.path.isdir(runs) else []) if f.endswith(".json")}
        mine = [s for s in dict.fromkeys(queued + list(states)) if slug.match(s)]
        if any(s not in states or states[s].get("status") not in ("done", "merged") for s in mine):
            continue  # queued, running or waiting: one is enough
        if any(re.search(r"template v%s\b" % re.escape(want), str(states[s].get("goal"))) for s in mine):
            out.append("- %s: migrate goal for v%s finished, repo still behind" % (name, want))
            continue
        cfg = read_json(os.path.join(repo, ".loop", "config.json")) or {}
        why = ""
        if git("branch", "--show-current", cwd=repo) != (cfg.get("base") or "main"):
            why = "its checkout is not on %s" % (cfg.get("base") or "main")
        elif git("status", "--porcelain", "--", ".loop/queue.md", cwd=repo):
            why = ".loop/queue.md has uncommitted changes"
        if why:
            out.append("- %s: behind v%s, nothing was queued: %s" % (name, want, why))
            continue
        goal = os.path.join(SKILLS, "workflow-delivery", "scripts", "goal.py")
        done = subprocess.run([sys.executable, goal, "queue", "migrate-%s%s" % (name, "-v" + want.replace(".", "-") if mine else ""), "--goal",
                               "Migrate %s to template v%s: close the pull-request gaps (migration-check --pr); the owner then closes the Mac and wiki gaps and runs the full migration-check" % (name, want),
                               "--touches", ".loop,README.md,docs/wiki", "--done", "setup.py migration-check --pr exits 0, run in this goal's worktree"],
                              cwd=repo, capture_output=True, text=True)
        if done.returncode:
            out.append("- %s: behind v%s, nothing was queued: %s" % (name, want, (done.stderr.strip() or done.stdout.strip()).splitlines()[-1][:160]))
    return out


# The status graph.

STAGES = 8
CELLS = 10
DONE = ("merged", "awaiting merge")
MARKS = {"done": "awaiting merge", "stopped": "failed"}


def span(seconds):
    seconds = int(seconds)
    return "%dh%02dm" % divmod(seconds // 60, 60) if seconds >= 3600 else "%dm" % (seconds // 60) if seconds >= 60 else "<1m"


def mark(status, merged=False):
    """The mark for a run's status."""
    return "merged" if merged else MARKS.get(status, status)


def completed(items):
    """Nodes plus a visible node for every dependency that is not a goal here."""
    known = {node["slug"] for node in items}
    extra = [dict(slug=dep, mark="unknown", depends=[], stage=0, left=0) for node in items for dep in node["depends"]
             if dep not in known and not known.add(dep)]
    return items + extra


def chain(items):
    """(seconds, path, cycles): the longest chain of what is left, the goals on it, and the goals where a cycle was cut."""
    by, memo, cut = {node["slug"]: node for node in items}, {}, []

    def walk(slug, stack):
        if slug in memo:
            return memo[slug]
        if slug in stack:
            cut.append(slug)
            return 0, []
        node = by[slug]
        best = max([walk(dep, stack + (slug,)) for dep in node["depends"] if dep in by] + [(0, [])], key=lambda found: found[0])
        memo[slug] = (best[0] + (node["left"] or 0), best[1] + [slug])
        return memo[slug]

    found = max([walk(node["slug"], ()) for node in items] + [(0, [])], key=lambda found: found[0])
    return found[0], found[1], sorted(set(cut))


def unknown(items):
    """Goals not finished that have no estimate yet."""
    return [node["slug"] for node in items if node["left"] is None and node["mark"] not in DONE]


def total(items, at=None):
    """The total line: the longest chain, 'at least' when some goal has no estimate, and a note for a cut cycle."""
    seconds, path, cycles = chain(items)
    missing = unknown(items)
    if not seconds and missing:
        line = "no estimate yet (%d goal%s without one)" % (len(missing), "" if len(missing) == 1 else "s")
    elif not seconds:
        line = "nothing left"
    else:
        line = "%s%s, the longest chain: %s" % ("at least " if missing else "about ", span(seconds), " > ".join(path))
        line += ", finish about %s" % (at + datetime.timedelta(seconds=seconds)).astimezone().strftime("%H:%M") if at else ""
        line += " (%d goal%s without an estimate)" % (len(missing), "" if len(missing) == 1 else "s") if missing else ""
    return line + ("; cycle cut at " + ", ".join(cycles) if cycles else "")


def levels(items):
    """Nodes grouped by depth: goals that wait on nothing first, then those that wait on them. A cycle is cut, not followed."""
    by, depth = {node["slug"]: node for node in items}, {}

    def deep(slug, stack):
        if slug not in depth:
            depth[slug] = 1 + max([deep(dep, stack + (slug,)) for dep in by[slug]["depends"] if dep in by and dep not in stack + (slug,)] + [0])
        return depth[slug]

    for node in items:
        deep(node["slug"], ())
    return [[node for node in items if depth[node["slug"]] == level] for level in range(1, max(depth.values(), default=0) + 1)]


def bar(stage):
    full = round(CELLS * stage / STAGES)
    return "[%s%s]" % ("#" * full, "-" * (CELLS - full))


def merged_line(prs):
    """Merged goals collapse to one line of pull request numbers."""
    return "merged: " + " ".join(prs) if prs else "(no merged goals yet)"


def line(node):
    """One node: its mark, stage, bar, time to finish and what it waits on."""
    stage = STAGES if node["mark"] in DONE else node["stage"]
    time = "done" if node["mark"] in DONE else "no estimate yet" if node["left"] is None else "~%s left" % span(node["left"])
    if node["mark"] == "unknown":
        return "- [? not a goal here] %s" % node["slug"]
    return "- [%s] %s  stage %d of %d %s  %s%s" % (node["mark"], node["slug"], stage, STAGES, bar(stage), time,
                                                "  <- waits on " + ", ".join(node["depends"]) if node["depends"] else "")


def render_text(items, under=None):
    """The graph as text: a heading per level, a line per node, anything in under[slug] indented beneath its node."""
    items, out = completed(items), []
    for number, level in enumerate(levels(items), 1):
        out.append("level %d%s" % (number, " (waits on nothing)" if number == 1 else ""))
        for node in level:
            out.append(line(node))
            out += (under or {}).get(node["slug"], [])
    return out or ["(no goals)"]


def main():
    if sys.argv[1:2] and sys.argv[1] in ("note", "retire", "checkin"):
        return runs_main()
    if sys.argv[1:] == ["migrate"]:
        print("\n".join(queue_migrations(git("rev-parse", "--show-toplevel") or os.getcwd())))
        return 0
    if sys.argv[1:] == ["lag"]:
        root = git("rev-parse", "--show-toplevel") or os.getcwd()
        print("\n".join(template_lag(root)) or "- (none)")
        return 0
    return draw_main()


if __name__ == "__main__":
    if not sys.stdin or not sys.stdin.isatty():
        os.dup2(os.open(os.devnull, os.O_RDONLY), 0)
    sys.exit(main())
