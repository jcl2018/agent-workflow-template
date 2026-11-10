#!/usr/bin/env python3
"""Re-plan the goal graph at each check-in to finish soonest (MON-10). Run by operate.py after watch, every pass.

usage: replan.py [plan]       re-read every goal's progress, log what changed and why, print the new changes
       replan.py since ISO    print the changes logged after a time (the check-in lists those since the last one)

What it does, and only this:
- starts: watch starts every goal whose dependencies are merged, up to the slot limit; each start it finds is logged
  with its reason (dependencies met, a slot free), so no ready goal sits idle without a line saying why;
- merges: two queued goals (not started) with the same PRD (`prd:` on their queue lines, first word) and overlapping
  `touches:` are proposed merged; goals missing either field are never proposed;
- splits: a queued or running goal that two or more queued goals wait on, whose queue line names `parts:`, is
  proposed split so the named part can start first;
- merge line: goals done with an open pull request are ordered critical path first (the most goals waiting on them,
  then the longest time left behind them); advisory, shown in the check-in, merge.py is not changed.
It never stops, restarts or edits a goal, and never applies a merge or a split: the owner does, with board.py retire
and a new queue line. Each change goes once into <git common dir>/loop/replan.log as `<time> <kind> <slugs>: <reason>`;
a proposal already logged with the same reason is not logged or shown again.
"""
import argparse
import datetime
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import board_status as bs  # noqa: E402
import goal_state  # noqa: E402
import graph  # noqa: E402
os.environ.update(GIT_TERMINAL_PROMPT="0", GH_PROMPT_DISABLED="1", GIT_EDITOR="true", GIT_ASKPASS="true", SSH_ASKPASS="true")  # no prompt ever blocks


def root():
    return bs.git("rev-parse", "--show-toplevel")


def loop_dir(top):
    common = subprocess.run(["git", "rev-parse", "--git-common-dir"], cwd=top, capture_output=True, text=True).stdout.strip()
    return os.path.join(os.path.abspath(os.path.join(top, common)), "loop")


def runs(folder):
    out = {}
    for name in sorted(os.listdir(os.path.join(folder, "runs"))) if os.path.isdir(os.path.join(folder, "runs")) else []:
        run = bs.read_json(os.path.join(folder, "runs", name)) if name.endswith(".json") else None
        if isinstance(run, dict) and graph.SLUG.match(str(run.get("slug", ""))):
            out[run["slug"]] = run
    return out


def queue(top):
    try:
        with open(os.path.join(top, ".loop", "queue.md")) as handle:
            return [item for item in map(graph.parse, handle.read().splitlines()) if item and graph.SLUG.match(item["slug"])]
    except OSError:
        return []


def dependents(lines):
    """{slug: set of goals that wait on it, directly or through others}."""
    direct = {}
    for item in lines:
        for dep in item["depends"]:
            direct.setdefault(dep, set()).add(item["slug"])
    out = {}
    for slug in direct:
        seen, todo = set(), list(direct[slug])
        while todo:
            here = todo.pop()
            if here not in seen:
                seen.add(here)
                todo += list(direct.get(here, ()))
        out[slug] = seen
    return out


def proposals(lines, records):
    """[(kind, slugs, reason)] for this pass."""
    out = []
    by = {item["slug"]: item for item in lines}
    for slug, run in sorted(records.items()):
        if run.get("status") in graph.LIVE and slug in by:
            met = ", ".join(by[slug]["depends"]) or "none"
            out.append(("start", slug, "started: dependencies met (%s) and a slot was free" % met))
    queued = [item for item in lines if item["slug"] not in records]
    for i, a in enumerate(queued):
        for b in queued[i + 1:]:
            same = a["prd"] and b["prd"] and a["prd"].split()[0] == b["prd"].split()[0]
            shared = sorted(set(a["touches"]) & set(b["touches"]))
            if same and shared:
                out.append(("merge", "%s+%s" % (a["slug"], b["slug"]), "same PRD %s and shared files %s: propose one goal"
                            % (a["prd"].split()[0], ", ".join(shared[:3]))))
    waits = dependents(lines)
    for item in lines:
        held = sorted(s for s in waits.get(item["slug"], ()) if s not in records)
        live = item["slug"] not in records or (records[item["slug"]].get("status") in graph.LIVE)
        if live and len(held) >= 2 and item["parts"]:
            out.append(("split", item["slug"], "%d goals wait on it (%s); propose starting part %s first"
                        % (len(held), ", ".join(held[:4]), item["parts"][0])))
    line = [slug for slug, run in records.items() if run.get("status") == "done" and not graph.merged(run)]
    if len(line) > 1:
        line.sort(key=lambda slug: (-len(waits.get(slug, ())), slug))
        out.append(("order", ",".join(line), "merge line, critical path first: %s (advisory)" % " > ".join(line)))
    return out


def log_path(folder):
    return os.path.join(folder, "replan.log")


def plan(top=None, at=None):
    """Log this pass's new changes; return them as lines."""
    top = top or root()
    folder = loop_dir(top)
    at = at or datetime.datetime.now(datetime.timezone.utc)
    seen_path = os.path.join(folder, "replan.json")
    seen = bs.read_json(seen_path) or {}
    seen = seen if isinstance(seen, dict) else {}
    records = runs(folder)
    found, _ = graph.read_pool(os.path.join(folder, "session-pool.json"))
    goal_state.stamp_held(list(records.values()), graph.assigned(found), at, folder)  # true held time (issue 115)
    new = []
    for kind, slugs, reason in proposals(queue(top), records):
        key = "%s %s" % (kind, slugs)
        if seen.get(key) != reason:
            seen[key] = reason
            new.append("%s %s %s: %s" % (at.strftime("%Y-%m-%dT%H:%M:%SZ"), kind, slugs, reason))
    if new:
        os.makedirs(folder, exist_ok=True)
        with open(log_path(folder), "a") as handle:
            handle.write("\n".join(new) + "\n")
        tmp = seen_path + ".%d.tmp" % os.getpid()
        with open(tmp, "w") as handle:
            json.dump(seen, handle, indent=1, sort_keys=True)
        os.replace(tmp, seen_path)
    return new


def open_proposals(top):
    """Merge and split proposals still true now, as '<kind> <slugs>: <reason>', shown at every check-in until acted on."""
    return ["%s %s: %s" % (kind, slugs, reason) for kind, slugs, reason in proposals(queue(top), runs(loop_dir(top)))
            if kind in ("merge", "split")]


def since(top, stamp):
    try:
        with open(log_path(loop_dir(top))) as handle:
            return [line.rstrip("\n") for line in handle if line[:20] > stamp]
    except OSError:
        return []


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd")
    sub.add_parser("plan")
    item = sub.add_parser("since")
    item.add_argument("stamp")
    args = parser.parse_args()
    if getattr(args, "stamp", None) is not None and not re.match(r"^\d{4}(-\d\d(-\d\d(T\d\d(:\d\d(:\d\dZ?)?)?)?)?)?$", args.stamp):
        sys.exit("REFUSED: %r is not a time. Fix: give it as YYYY-MM-DDTHH:MM:SSZ." % args.stamp)
    if args.cmd == "since":
        lines = since(root(), args.stamp)
    else:
        lines = plan()
    print("\n".join(lines) if lines else "REPLAN: no change")
    return 0


if __name__ == "__main__":
    sys.exit(main())
