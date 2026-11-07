#!/usr/bin/env python3
"""Draw the operation board from board.json: the dependency map, board.html and board-artifact.html.

usage: board_page.py [--in FILE] [--out DIR]

Reads board.json (default <git common dir>/loop/board.json), saves its dependency_map back into that file, and writes
both pages beside it, or into --out. board-artifact.html has no doctype, html, head or body tags. The pages have no
scripts and load nothing from the network.
"""
import argparse
import datetime
import html
import json
import os
import subprocess
import sys

TEXT = {"design": "Write the design", "design-review": "Review the design", "plan": "Write the plan", "build": "Build the change",
        "checks": "Run the checks", "judge": "Judge the change against its done lines", "pr": "Open the pull request",
        "release": "Answer the release question", "session": "A tracked session", "poc": "Answer a question, read-only"}
OPEN = ("running", "waiting", "failed", "stopped", "queued")
WORDS = {"waiting": "needs you", "unknown": "not tracked"}
BOX_W, BOX_H, GAP, HEAD, ROW, TRACK = 118, 60, 22, 22, 18, 12
HOW = ("Each lane is a run and each box a step, coloured by status, with its expected finish. Solid arrows run inside a run; "
       "thick dashed arrows cross runs and say why it waits. Hover a box for details, or tap it to open them in the list below.")
DARK = ("--bg:#141414;--fg:#eee;--mute:#aaa;--line:#333;--warn-bg:#3a2e10;--warn:#ffcc66;--bad:#ff6b81;--ok:#6fd08c;--run:#7db4ff;"
        "--idle:#8a8a8a;--band:#1e1e1e")
CSS = ":root{--bg:#fff;--fg:#1b1b1b;--mute:#666;--line:#ddd;--warn-bg:#fff4d6;--warn:#8a5a00;--bad:#b00020;--ok:#1b7f3b;--run:#1f5fbf;" \
      "--idle:#777;--band:#f6f6f6}\n" \
      "@media (prefers-color-scheme:dark){:root:not([data-theme=light]){%s}}\n:root[data-theme=dark]{%s}\n" % (DARK, DARK) + """\
body{background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,sans-serif;margin:0 auto;max-width:1000px;padding:16px}
h1{font-size:22px}h2{font-size:17px;margin-top:28px}table{border-collapse:collapse;width:100%}
th,td{border-bottom:1px solid var(--line);padding:6px 8px;text-align:left;vertical-align:top}
.wait{background:var(--warn-bg);border:2px solid var(--warn);border-radius:8px;padding:12px 16px}
.wait h2{color:var(--warn);margin-top:0}code{font-size:16px;font-weight:600;word-break:break-all}.mute{color:var(--mute)}
.scroll{overflow-x:auto}@media (max-width:600px){body{font-size:14px}th,td{padding:4px}}
.map svg{display:block;max-width:none}.band{fill:var(--band)}.lane{fill:var(--fg);font-size:12px;font-weight:600}
.box rect{fill:var(--bg);stroke:var(--idle);stroke-width:2}.box text{fill:var(--fg);font-size:11px}.box .t{font-size:12px;font-weight:600}
.box:hover rect,.box:focus rect{stroke-width:3.5}.step{fill:none;stroke:var(--idle);stroke-width:1.25}
.wire{fill:none;stroke:var(--warn);stroke-width:2.5;stroke-dasharray:6 4}.tag{fill:var(--warn);font-size:11px;font-weight:600}
.cap{fill:var(--idle)}.capw{fill:var(--warn)}
.s-done rect{stroke:var(--ok)}.s-running rect{stroke:var(--run)}.s-waiting rect{stroke:var(--warn)}
.s-failed rect,.s-stopped rect{stroke:var(--bad)}.s-unknown rect{stroke-dasharray:3 3}
.keys{display:flex;flex-wrap:wrap;gap:4px 14px;font-size:13px;color:var(--mute);margin:8px 0}
.key{display:inline-block;width:12px;height:12px;border:2px solid var(--idle);margin-right:4px}.key.s-done{border-color:var(--ok)}
.key.s-running{border-color:var(--run)}.key.s-waiting{border-color:var(--warn)}.key.s-failed{border-color:var(--bad)}
.list details{border-bottom:1px solid var(--line);padding:6px 0}.list dl{margin:4px 0;scroll-margin-top:48px}.list details details{margin-left:14px;border:0;padding:3px 0}
.list summary{cursor:pointer;overflow-wrap:anywhere}.list dl:target{outline:2px solid var(--warn);outline-offset:2px}
.list dt{color:var(--mute);font-size:13px}.list dd{margin:0 0 6px;overflow-wrap:anywhere}"""


def stamp(text):
    try:
        return datetime.datetime.fromisoformat(str(text).replace("Z", "+00:00")).astimezone(datetime.timezone.utc)
    except ValueError:
        return None


def overlap(a, b):
    a, b = os.path.normpath(a), os.path.normpath(b)
    return a == b or a.startswith(b + os.sep) or b.startswith(a + os.sep)


def key(run):
    return "%s/%s" % (run["repo"], run["slug"])


def blockers(run):
    return [slug.strip() for slug in str(run.get("waits_on") or "").split(",") if slug.strip()]


class Map:
    """Works out the lanes and arrows. Goals that are retired are left out, and arrows to them are dropped."""

    def __init__(self, doc):
        self.at = stamp(doc["generated"])
        self.doc, self.history = doc, doc["usual"]
        queued = [dict(d, status="queued", waits_on=d["on"], tracked=False, elapsed=0, note="", finding="", eta="", next="",
                       waiting=None, last="", branch="") for d in doc["dependencies"]]
        self.known = doc["runs"] + queued
        self.shown, self.ended, self.waiters, self.seen = {}, {}, {}, set()
        self.steps = {}
        for step in doc["steps"]:
            self.steps.setdefault(key(step), []).append(step)
        today = self.at.strftime("%Y-%m-%d")
        for run in self.known:
            kept = run["status"] in OPEN or (run["status"] == "done" and ((run["tracked"] and run["level"] != "poc") or run["last"].startswith(today)))
            if kept:
                self.show(run)
        for run in list(self.shown.values()):
            for slug in blockers(run):
                self.link(run, slug)

    def find(self, run, slug):
        same = [item for item in self.known if item["slug"] == slug]
        return next((item for item in same if item["repo"] == run["repo"]), same[0] if same else None)

    def show(self, run):
        """Blockers first, so lanes read top to bottom and dashed arrows run downward."""
        if key(run) in self.seen:
            return
        self.seen.add(key(run))
        for slug in blockers(run):
            found = self.find(run, slug) or dict(run, slug=slug, goal="Not tracked on this board", status="unknown", ghost=True,
                                                 waits_on="", touches=[], tracked=False, note="", next="", finding="", eta="")
            if found["status"] != "retired":
                self.show(found)
        self.shown[key(run)] = run

    def link(self, run, slug):
        found = self.find(run, slug)
        if found and found["status"] == "retired":
            return
        target = key(found) if found else "%s/%s" % (run["repo"], slug)
        hit = [t for t in run.get("touches") or [] for u in (found or {}).get("touches") or [] if overlap(t, u)]
        why = "%s %s" % ("session" if found and found["tracked"] else "goal", slug) + (", shared %s" % hit[0] if hit else "")
        self.waiters.setdefault(target, []).append((key(run), why))

    def begins(self, run):
        ends = [self.finish(found) for found in (self.find(run, slug) for slug in blockers(run)) if found]
        return None if None in ends else max(ends + [self.at])

    def finish(self, run):
        name = key(run)
        if name not in self.ended:
            self.ended[name] = self.at if run["status"] == "done" else None  # None also stops a cycle
            usual = self.history.get(run.get("level"))
            if run["tracked"]:
                self.ended[name] = stamp(run["eta"]) if run["eta"] else None
            elif run["status"] in ("running", "waiting") and usual is not None:
                self.ended[name] = self.at + datetime.timedelta(seconds=max(0, usual - run["elapsed"]))
            elif run["status"] == "queued" and usual is not None and self.begins(run):
                self.ended[name] = self.begins(run) + datetime.timedelta(seconds=usual)
        return self.ended[name]

    def next_text(self, run, state, ups, index):
        ask = (run.get("waiting") or {}).get("ask") if state == "waiting" else ""
        hold = next((d["waits_on"] for d in self.doc["dependencies"] if key(d) == key(run)), "")
        if ask or run["next"]:
            return ask or run["next"]
        if state in ("failed", "stopped"):
            return run["finding"] or "See its log"
        if hold and hold != "ready to start":
            return "Waits on " + hold
        if state == "done":
            return "Nothing: this step is finished"
        if state == "running":
            return "Then %s" % ups[0] if ups else "Finishes the run"
        return "Starts after the step before it" if index else "Starts when the goal starts"

    def boxes(self, name, run):
        steps = self.steps.get(name, [])
        ghost = run.get("ghost")
        fallback = "unknown" if ghost else "queued" if run["status"] == "queued" else "pending"
        names = [s["step"] for s in steps] or run.get("boxes") or ["poc" if run.get("level") == "poc" else "session"]
        states = [s["status"] for s in steps] or [run["status"] if run["tracked"] else fallback] * len(names)
        left = [n for n, state in zip(names, states) if state != "done"]
        begin = self.at if run["status"] != "queued" else self.begins(run)
        end = None if ghost else self.finish(run)
        out = []
        for index, (step, state) in enumerate(zip(names, states)):
            if state == "done":
                eta = "done"
            elif begin and end and state not in ("failed", "stopped"):
                eta = (begin + (end - begin) * (left.index(step) + 1) / len(left)).strftime("~%H:%M UTC")
            else:
                eta = "no estimate"
            ups = [names[index + 1]] if index + 1 < len(names) else ["%s (%s)" % w for w in self.waiters.get(name, [])]
            finished = [n for n, s in zip(names, states) if s == "done"]
            out.append({"id": "%s:%s" % (name, step), "step": step, "status": state, "eta": eta,
                        "what": "%s: %s" % (TEXT.get(step, step), run["goal"] or run["slug"]),
                        "done": ", ".join(finished + ([run["note"]] if run["note"] else [])) or "Nothing yet",
                        "next": self.next_text(run, state, ups, index), "unblocks": ups})
        return out

    def result(self):
        lanes, arrows = [], []
        for name, run in self.shown.items():
            boxes = self.boxes(name, run)
            lanes.append({"run": name, "title": run["goal"] or run["slug"], "status": run["status"], "branch": run.get("branch") or "",
                          "boxes": boxes})
            arrows += [{"from": a["id"], "to": b["id"], "on": ""} for a, b in zip(boxes, boxes[1:])]
        ends = {lane["run"]: (lane["boxes"][0]["id"], lane["boxes"][-1]["id"]) for lane in lanes}
        for blocker, waiters in self.waiters.items():
            arrows += [{"from": ends[blocker][1], "to": ends[who][0], "on": why} for who, why in waiters if blocker in ends and who in ends]
        return {"lanes": lanes, "arrows": arrows}


def esc(value):
    return html.escape(str(value if value is not None else ""), quote=True)


def cut(text, size):
    return text if len(text) <= size else text[:size - 1] + "…"


def tip(box):
    lines = [box["what"], "Status: %s. Expected: %s." % (WORDS.get(box["status"], box["status"]), box["eta"]), "Done: " + box["done"],
             "Next: " + box["next"], "Unblocks: " + (", ".join(box["unblocks"]) or "nothing")]
    return "\n".join(lines)


def svg(graph, ids):
    """Lanes stack from the top. A dashed arrow leaves the end of its run, drops down a left gutter and enters the next run."""
    lanes = graph["lanes"]
    wires = [a for a in graph["arrows"] if a["on"]]
    inbound = {}
    for wire in wires:
        inbound.setdefault(wire["to"], []).append(wire)
    gutter = 12 + TRACK * len(wires)
    places, tops, y = {}, {}, 8
    bands, out = [], []
    for lane in lanes:
        count = max([len(inbound.get(b["id"], [])) for b in lane["boxes"]] + [0])
        y += count * ROW
        tops[lane["run"]] = y
        bands.append((lane, y))
        for index, box in enumerate(lane["boxes"]):
            places[box["id"]] = (gutter + index * (BOX_W + GAP), y + HEAD)
        y += HEAD + BOX_H + 18
    width = gutter + max([len(lane["boxes"]) for lane in lanes] + [1]) * (BOX_W + GAP)
    out.append("<svg role=img aria-label='Dependency map' width=%d height=%d viewBox='0 0 %d %d'><defs>" % (width, y, width, y))
    for name in ("cap", "capw"):
        out.append("<marker id=%s viewBox='0 0 8 8' refX=7 refY=4 markerWidth=9 markerHeight=9 markerUnits=userSpaceOnUse orient=auto>"
                   "<path class=%s d='M0,0 L8,4 L0,8 z'></path></marker>" % (name, name))
    out.append("</defs>")
    for lane, top in bands:
        out.append("<rect class=band x=0 y=%d width=%d height=%d rx=6></rect>" % (top - 2, width, HEAD + BOX_H + 10))
        out.append("<text class=lane x=%d y=%d>%s</text>" % (gutter + 26, top + 13, esc(cut(lane["run"] + ": " + lane["title"], 70))))
    for arrow in graph["arrows"]:
        if not arrow["on"] and arrow["from"] in places and arrow["to"] in places:
            x1, y1 = places[arrow["from"]]
            x2, _ = places[arrow["to"]]
            out.append("<path class=step marker-end='url(#cap)' d='M%d,%d H%d'></path>" % (x1 + BOX_W, y1 + BOX_H // 2, x2 - 2))
    for track, wire in enumerate(wires):
        x1, y1 = places[wire["from"]]
        x2, y2 = places[wire["to"]]
        row = inbound[wire["to"]].index(wire)
        many = len(inbound[wire["to"]])
        lane_top = y2 - HEAD
        rail = lane_top - 4 - (many - 1 - row) * ROW
        enter = x2 + 10 + 10 * row
        out.append("<path class=wire marker-end='url(#capw)' d='M%d,%d V%d H%d V%d H%d V%d'></path>" % (
            x1 + BOX_W // 2, y1 + BOX_H, y1 + BOX_H + 7, 6 + TRACK * track, rail, enter, y2 - 2))
        out.append("<text class=tag x=%d y=%d>%s</text>" % (x2 + 16 + 10 * many, rail + 4, esc(wire["on"])))
    for lane in lanes:
        for box in lane["boxes"]:
            x, top = places[box["id"]]
            out.append("<a class='box s-%s' href='#b%d' transform='translate(%d,%d)'><title>%s</title><rect width=%d height=%d rx=6></rect>"
                       "<text class=t x=8 y=17>%s</text><text x=8 y=33>%s</text><text x=8 y=49>%s</text></a>" % (
                           esc(box["status"]), ids[box["id"]], x, top, esc(tip(box)), BOX_W, BOX_H, esc(cut(box["step"], 16)),
                           esc(WORDS.get(box["status"], box["status"])), "" if box["eta"] == "done" else esc(box["eta"])))
    out.append("</svg>")
    return "".join(out)


def words(graph, ids):
    out = ["<div class=list>"]
    for lane in graph["lanes"]:
        out.append("<details><summary><b>%s</b>: %s (%s)%s</summary>" % (
            esc(lane["run"]), esc(lane["title"]), esc(WORDS.get(lane["status"], lane["status"])),
            esc(", branch " + lane["branch"]) if lane["branch"] else ""))
        for box in lane["boxes"]:
            out.append("<details><summary>%s, %s, %s</summary><dl id=b%d>" % (esc(box["step"]), esc(WORDS.get(box["status"], box["status"])), esc(box["eta"]), ids[box["id"]]))
            rows = (("What it is", box["what"]), ("Done so far", box["done"]), ("What's next", box["next"]),
                    ("What it unblocks", ", ".join(box["unblocks"]) or "Nothing"))
            out.extend("<dt>%s</dt><dd>%s</dd>" % (esc(k), esc(v)) for k, v in rows)
            out.append("</dl></details>")
        out.append("</details>")
    out.append("</div>")
    return "".join(out)


def page(doc, bare=False):
    e = esc
    picks = lambda items, *keys: [[x[k] for k in keys] for x in items]
    link = lambda x: x["pr"] + " (%s)" % x["prstate"] if x["pr"] else "-"
    sections = doc["sections"]
    every = doc["cadence"] + " min" if doc["cadence"] != "off" else "never (off)"

    def table(index, head, rows):
        title = "<h2>%s</h2>" % sections[index]
        if not rows:
            return title + "<p class=mute>Nothing.</p>"
        body = "".join("<tr>%s</tr>" % "".join("<td>%s</td>" % e(c) for c in row) for row in rows)
        return title + "<div class=scroll><table><tr>%s</tr>%s</table></div>" % ("".join("<th>%s</th>" % e(h) for h in head), body)

    name, style = "<title>Operation board</title>", "<style>%s</style>" % CSS
    out = [name + style + "<h1>Operation board</h1>"] if bare else [
        "<!doctype html><html lang=en><head><meta charset=utf-8>",
        "<meta name=viewport content='width=device-width,initial-scale=1'>" + name,
        style + "</head><body><h1>Operation board</h1>"]
    out.append("<p class=mute>%s. Written %s. Repos: %s. Check in every %s.%s</p>" % (
        e(doc["digest"]), e(doc["generated"]), e(", ".join(doc["repos"])), e(every),
        e(" Next check-in " + doc["next_at"] + "." if doc["next_at"] else "")))
    out.append("<section class=wait><h2>%s (%d)</h2>" % (sections[0], len(doc["waiting"])))
    for w in doc["waiting"]:
        out.append("<p><b>%s/%s</b>: %s<br>Type in %s:</p><ul>%s</ul>" % (
            e(w["repo"]), e(w["slug"]), e(w["ask"]), e(w["where"]), "".join("<li><code>%s</code></li>" % e(x) for x in w["words"])))
    out.append("</section>" if doc["waiting"] else "<p>Nothing.</p></section>")
    graph = doc["dependency_map"]
    ids = {box["id"]: index for index, box in enumerate(b for lane in graph["lanes"] for b in lane["boxes"])}
    out.append("<h2>%s</h2>" % sections[1])
    if graph["lanes"]:
        out.append("<p class=mute>%s</p><div class=keys>%s<span>Dashed: waits on another run</span></div><div class='scroll map'>%s</div>%s" % (
            e(HOW), "".join("<span><i class='key s-%s'></i>%s</span>" % pair for pair in (
                ("done", "Done"), ("running", "Running"), ("waiting", "Needs you"), ("failed", "Failed or stopped"), ("queued", "Queued or pending"))),
            svg(graph, ids), words(graph, ids)))
    else:
        out.append("<p class=mute>Nothing.</p>")
    runs = [[r["repo"], r["goal"] or r["slug"], r["level"], r["step"], r["age"], r["tries"], link(r),
             "checks %s, judge %s" % (r["checks"] or "-", r["judge"] or "-"),
             r["status"] + (" (quiet)" if r["quiet"] == "yes" else "") + (": " + r["reason"] if r["reason"] else ""),
             r["waits_on"] or "-", r["note"] or "-"] for r in doc["runs"]]
    out.append(table(2, ["Repo", "Goal", "Level", "Step", "Elapsed", "Tries", "Pull request", "Check state", "Status", "Waits on", "Last message"], runs))
    out.append(table(3, ["Repo", "Goal", "Level", "Estimate"], picks(doc["expected"], "repo", "slug", "level", "estimate")))
    fin = doc["finished"]
    out.append(table(4, ["Repo", "Goal", "Result", "Pull request"], [[x["repo"], x["slug"], x["result"], link(x)] for x in fin["items"]]) + "<p class=mute>%s</p>" % e(fin["note"]))
    out.append(table(5, ["Repo", "Goal", "Step", "Status"], picks(doc["steps"], "repo", "slug", "step", "status")) + ("" if bare else "</body></html>") + "\n")
    return "\n".join(out)


def write(path, text):
    temp = path + ".%d.tmp" % os.getpid()
    with open(temp, "w") as handle:
        handle.write(text)
    os.replace(temp, path)


def main():
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
    doc["dependency_map"] = Map(doc).result()
    write(path, json.dumps(doc, indent=2, sort_keys=True) + "\n")
    folder = os.path.abspath(args.out) if args.out else os.path.dirname(path)
    os.makedirs(folder, exist_ok=True)
    write(os.path.join(folder, "board.html"), page(doc))
    write(os.path.join(folder, "board-artifact.html"), page(doc, True))
    for name, file in (("HTML", "board.html"), ("ARTIFACT", "board-artifact.html")):
        print(name, os.path.join(folder, file))
    return 0


if __name__ == "__main__":
    sys.exit(main())
