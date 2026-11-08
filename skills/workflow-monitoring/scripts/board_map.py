#!/usr/bin/env python3
"""Finish board.json for board_page.py: the dependency map, expected finishes, today's finished goals and every step.

usage: board_map.py FILE

Reads what board.py wrote and adds those sections to the same file. It calls neither git nor gh.
"""
import datetime
import json
import os
import statistics
import sys

STEPS = {"goal": ["idea", "plan", "build", "checks", "review", "qa", "ship", "pr"]}
ORDER = STEPS["goal"] + ["release"]
TEXT = {"idea": "Shape the idea into a design", "plan": "Review the design into a plan", "build": "Build the change",
        "checks": "Run the checks", "review": "Review the change", "qa": "Test the change", "ship": "Prepare it to ship",
        "pr": "Open the pull request",
        "release": "Answer the release question"}
OPEN = ("running", "waiting", "failed", "stopped", "queued")


def stamp(text):
    try:
        return datetime.datetime.fromisoformat(str(text).replace("Z", "+00:00")).astimezone(datetime.timezone.utc)
    except ValueError:
        return None


def key(run):
    return "%s/%s" % (run["repo"], run["slug"])


def blockers(run):
    return [slug.strip() for slug in str(run.get("waits_on") or "").split(",") if slug.strip()]


def span(seconds):
    seconds = max(0, int(seconds))
    return "%dh%02dm" % divmod(seconds // 60, 60) if seconds >= 3600 else "%dm" % (seconds // 60)


def sections(doc):
    """Worked out from the rows alone; nothing here reads a run record."""
    at, rows, waiting = stamp(doc["generated"]), doc["runs"], doc["waiting"]
    for queued in doc["dependencies"]:
        queued["boxes"] = STEPS.get(queued["level"], STEPS["goal"])
    history = {}
    for r in rows:
        if r["status"] == "done" and r["took"] > 0:
            history.setdefault(r["level"], []).append(r["took"])
    usual = {level: statistics.median(took) for level, took in history.items()}
    expected = []
    for r in rows:
        if r["status"] == "running":
            old = usual.get(r["level"])
            guess = "estimate: about %s left" % span(max(0, old - r["elapsed"])) if old else \
                "no estimate: no finished %s goals yet" % r["level"]
            expected.append({"repo": r["repo"], "slug": r["slug"], "level": r["level"], "estimate": guess})
    today = at.strftime("%Y-%m-%d")
    done = [{"repo": r["repo"], "slug": r["slug"], "pr": r["pr"], "prstate": r["prstate"], "result": "delivered" if r["pr"] else "finished, no pull request"}
            for r in rows if r["status"] == "done" and r["last"].startswith(today)]
    note = "%d item(s) wait on you, so do not archive yet." % len(waiting) if waiting else "Nothing waits on you, so these can be archived."
    steps = []
    for r in rows:
        mine = STEPS.get(r["level"], STEPS["goal"])
        at_step = ORDER.index(r["step"]) if r["step"] in ORDER else -1
        for step in mine + (["release"] if r["status"] == "done" or r["step"] == "release" else []):
            index = ORDER.index(step)
            state = "done" if r["status"] == "done" or index < at_step else r["status"] if index == at_step or r["status"] == "retired" else "pending"
            steps.append({"repo": r["repo"], "slug": r["slug"], "step": step, "status": state})
    doc.update({"usual": usual, "expected": expected, "finished": {"items": done, "note": note}, "steps": steps})


class Map:
    """Works out the lanes and arrows. Goals that are retired are left out, and arrows to them are dropped."""

    def __init__(self, doc):
        self.at = stamp(doc["generated"])
        self.doc, self.history = doc, doc["usual"]
        queued = [dict(d, status="queued", waits_on=d["on"], elapsed=0, note="", finding="", eta="", next="",
                       waiting=None, last="", branch="") for d in doc["dependencies"]]
        self.known = doc["runs"] + queued
        self.shown, self.ended, self.waiters, self.seen = {}, {}, {}, set()
        self.steps = {}
        for step in doc["steps"]:
            self.steps.setdefault(key(step), []).append(step)
        today = self.at.strftime("%Y-%m-%d")
        for run in self.known:
            kept = run["status"] in OPEN or (run["status"] == "done" and run["last"].startswith(today))
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
                                                 waits_on="", touches=[], note="", next="", finding="", eta="")
            if found["status"] != "retired":
                self.show(found)
        self.shown[key(run)] = run

    def link(self, run, slug):
        found = self.find(run, slug)
        if found and found["status"] == "retired":
            return
        target = key(found) if found else "%s/%s" % (run["repo"], slug)
        why = "depends on " + slug
        self.waiters.setdefault(target, []).append((key(run), why))

    def begins(self, run):
        ends = [self.finish(found) for found in (self.find(run, slug) for slug in blockers(run)) if found]
        return None if None in ends else max(ends + [self.at])

    def finish(self, run):
        name = key(run)
        if name not in self.ended:
            self.ended[name] = self.at if run["status"] == "done" else None  # None also stops a cycle
            usual = self.history.get(run.get("level"))
            if run["status"] in ("running", "waiting") and usual is not None:
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
        names = [s["step"] for s in steps] or run.get("boxes") or []
        states = [s["status"] for s in steps] or [fallback] * len(names)
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


def main():
    if len(sys.argv) != 2 or sys.argv[1].startswith("-"):
        print(__doc__)
        return 0
    try:
        with open(sys.argv[1]) as handle:
            doc = json.load(handle)
    except (OSError, ValueError):
        sys.exit("REFUSED: no readable %s. Fix: run board.py board first." % sys.argv[1])
    sections(doc)
    doc["dependency_map"] = Map(doc).result()
    temp = sys.argv[1] + ".%d.tmp" % os.getpid()
    with open(temp, "w") as handle:
        handle.write(json.dumps(doc, indent=2, sort_keys=True) + "\n")
    os.replace(temp, sys.argv[1])
    return 0


if __name__ == "__main__":
    sys.exit(main())
