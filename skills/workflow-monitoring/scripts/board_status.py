#!/usr/bin/env python3
"""The run facts the live board is built from, plus every name of board_log.py (log facts) and board_model.py (the estimate
model the backtest picks, the accuracy line, the stall floor), re-exported so readers keep using board_status; running it
prints the live board (see live_board.py). board_report.py says why the board uses its model.

usage: board_status.py [--html]

Prints the live board as text, or with --html as the fragment board-artifact.html embeds.
"""
import argparse
import json
import os
import re
import statistics
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import graph  # noqa: E402
import board_page  # noqa: E402
# board_log sets the no-prompt guard (GIT_TERMINAL_PROMPT and the rest) before any git or gh process starts.
from board_log import (COMMON, FLOW, HOLD, STEPS, UNHOLD, after, current, flow_seconds, git, goal_file,  # noqa: E402,F401
                       holding, named, read_json, size_of, stamp)
from board_model import (CANDIDATES, CELLS, LABELS, MIN_BACKTEST, MODEL, SIMILAR, STALL, STALL_FLOOR,  # noqa: E402,F401
                         STEP_UP, TILT, History, accuracy_text, backtest, base, blend_cell, cached, chosen, envelope,
                         estimate, estimate_full, estimate_text, folds, holds, left_time, lifted_steps, model, overrun,
                         pace_of, score, size_cell, span, spread, stall_lines, stalled, step_left, step_now, steps_cell,
                         steps_for, table)

ASKING = ("waiting", "failed", "stopped")


def seconds_by_step(run, at):
    """Time each step took, from the gaps before its log entries, plus the gap since the last entry for the current step."""
    found, log = {}, run.get("log") or []
    for before, entry in zip(log, log[1:]):
        word = entry.split(" ", 2)[1] if entry.count(" ") else ""
        a, b = stamp(before), stamp(entry)
        if word in STEPS and a and b:
            found[word] = found.get(word, 0) + (b - a).total_seconds()
    last = stamp(log[-1]) if log else None
    if run.get("status") == "running" and run.get("step") in STEPS and last:
        found[run["step"]] = found.get(run["step"], 0) + max(0, (at - last).total_seconds())
    return found


def tokens_by_step(run):
    value = run.get("tokens")
    return {step: n for step, n in value.items() if step in STEPS and isinstance(n, int)} if isinstance(value, dict) else {}


def usual(runs, mine, step, pick):
    values = [pick(run).get(step) for run in runs if run["slug"] != mine["slug"] and run.get("status") == "done"]
    values = [v for v in values if v]
    return statistics.median(values) if values else None


def board_items(live, queue, freezing, lines, runs, at, root, waits, held=None):
    """The board's goal items: slug, mark, depends, stage, left, the estimate, and partial (a step with no estimate). held:
    the slugs the session pool says are held (None when unknown), whose step time stops growing."""
    def item(run, mark, depends):
        found = estimate_full(run, runs, at, root, held)
        return dict(slug=run["slug"], mark=mark, depends=waits(depends), stage=0, est=found and found[:4], owner=graph.foreign(run),
                    left=found[0] if found else None, partial=bool(found and found[4]))
    out = [item(r, board_page.mark(r.get("status")), r.get("waits_on") or []) for r in live]
    out += [item(dict(g, status="queued"), "queued", g["depends"]) for g in queue]
    out += [item(dict(lines.get(f["slug"]) or {"slug": f["slug"]}, status="queued"), board_page.mark("running"),
                 (lines.get(f["slug"]) or {}).get("depends") or []) for f in freezing]
    return out


def queued(root, runs):
    """Queued goals, as queue.md lines parsed by graph.parse: the ones with no run record yet."""
    by_slug = {run["slug"] for run in runs}
    try:
        with open(os.path.join(root, ".loop", "queue.md")) as handle:
            return [item for item in map(graph.parse, handle.read().splitlines()) if item and item["slug"] not in by_slug]
    except OSError:
        return []


def github_state(url, cwd):
    """MERGED, CLOSED or OPEN as gh says it; any doubt (no gh, no answer) is an empty string."""
    try:
        done = subprocess.run(["gh", "pr", "view", url, "--json", "state"], cwd=cwd, capture_output=True, text=True, timeout=20)
        state = str(json.loads(done.stdout).get("state", "")).upper() if done.returncode == 0 else ""
        return state if state in ("MERGED", "CLOSED", "OPEN") else ""
    except (OSError, ValueError, AttributeError, subprocess.SubprocessError):
        return ""


def pr_states(runs, root):
    """GitHub's state of each done run's pull request, asked once per run."""
    return {run["slug"]: github_state(run["pr"], root) for run in runs if run.get("status") == "done" and run.get("pr") and not graph.merged(run)}


def error_open(run, gone, marker):
    """An error stays under Issues unless its goal merged. A record-merged goal's error stays when it was logged after the merge
    (the wiki publishes after it); one merged only on GitHub never merged through here, so what it logged came before."""
    log = [str(entry).split(" ", 2)[1:] or [""] for entry in run.get("log") or []]
    last = lambda test: max([n for n, parts in enumerate(log) if test(parts)] + [-1])
    if marker == "wiki not published" and last(lambda parts: " ".join(parts).startswith(("wiki published", "wiki unchanged"))) > last(lambda parts: " ".join(parts).startswith(marker)):
        return False   # a later publish went through or found nothing to change
    if run["slug"] not in gone:
        return True
    return graph.merged(run) and last(lambda parts: " ".join(parts).startswith(marker)) > last(lambda parts: parts[0] == "merged")


DOCS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "workflow-docs", "scripts", "docs.py")


def wiki_check(root):
    """The pages docs.py check reports now, as sorted [(kind, page)]; None when the check could not judge."""
    try:
        done = subprocess.run([sys.executable, DOCS, "check"], cwd=root, capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    if done.returncode not in (0, 1) or "NO PAGES" in done.stdout:
        return None
    found = {m.groups() for m in re.finditer(r"^([A-Z]+) (\S+): ", done.stdout, re.M)} if done.returncode else set()
    return sorted(item for item in found if item[0] != "LAG")  # a repo behind the installed skills shows as template_lag


# The machine this pod runs on (machine-status): the check-in's Machine line, and the memory floor that holds a goal back from starting.
GB, NAMES = 2 ** 30, ("ram", "commit", "cpu", "claude", "node")


def memory():
    """(free RAM, free commit) in GB, or (None, None). LOOP_MACHINE="ram,commit,cpu,claude,node" stands in for the machine (toys)."""
    fake = os.environ.get("LOOP_MACHINE")
    if fake:
        got = [float(x) if x.strip() else None for x in (fake.split(",") + [""] * 5)[:5]]
        return got[0], got[1]
    try:
        if os.name == "nt":
            import ctypes

            class Status(ctypes.Structure):
                _fields_ = [("size", ctypes.c_ulong), ("load", ctypes.c_ulong)] + [(n, ctypes.c_ulonglong) for n in ("tp", "ap", "tc", "ac", "tv", "av", "ae")]
            one = Status(size=ctypes.sizeof(Status))
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(one))
            return one.ap / GB, one.ac / GB
        if os.path.exists("/proc/meminfo"):
            info = {k: int(v.split()[0]) for k, v in (l.split(":", 1) for l in open("/proc/meminfo") if ":" in l)}
            return info["MemAvailable"] / 2 ** 20, (info["CommitLimit"] - info["Committed_AS"]) / 2 ** 20
        pages = {k: int(v.strip(" .")) for k, v in (l.split(":", 1) for l in subprocess.run(["vm_stat"], capture_output=True, text=True).stdout.splitlines()[1:] if ":" in l)}
        free = (pages["Pages free"] + pages["Pages inactive"] + pages.get("Pages purgeable", 0)) * 16384 / GB  # macOS has no commit limit: reclaimable RAM
        return free, free
    except Exception:
        return None, None


def allowed(cfg=None):
    """Goals memory lets start now: None when it can't be read or the floor is 0, 0 under min_free_memory_gb of free commit
    (default 3.5), else one plus one per 1.5 GB above the floor."""
    cfg = cfg if cfg is not None else read_json(os.path.join(git("rev-parse", "--show-toplevel") or ".", ".loop", "config.json")) or {}
    try:
        floor, each = float(cfg.get("min_free_memory_gb", 3.5)), 1.5  # a goal's worker needs about 1.5 GB
    except (TypeError, ValueError):
        return None
    commit = memory()[1]
    return None if commit is None or floor <= 0 else 0 if commit < floor else 1 + int((commit - floor) / each)


def machine_line(cfg):
    """Machine: free RAM and commit memory, CPU, the claude and node processes, and the goal slots memory allows."""
    ram, commit = memory()
    cpu, count = None, {"claude": None, "node": None}
    fake = os.environ.get("LOOP_MACHINE")
    if fake:
        got = [float(x) if x.strip() else None for x in (fake.split(",") + [""] * 5)[:5]]
        cpu, count = got[2], {"claude": got[3], "node": got[4]}
    else:
        try:
            if os.name == "nt":
                seen = subprocess.run(["tasklist", "/fo", "csv", "/nh"], capture_output=True, text=True, timeout=20).stdout.lower().splitlines()
                names = [l.split('","')[0].strip('"').replace(".exe", "") for l in seen]
                import ctypes
                import time
                tick = [ctypes.c_ulonglong() for _ in range(3)]
                snap = lambda: (ctypes.windll.kernel32.GetSystemTimes(*map(ctypes.byref, tick)), [x.value for x in tick])[1]
                one = snap()
                time.sleep(0.2)
                two = snap()
                busy = (two[1] - one[1]) + (two[2] - one[2])  # kernel time includes idle
                cpu = 100 * (1 - (two[0] - one[0]) / busy) if busy else None
            else:
                names = [os.path.basename(l.strip()) for l in subprocess.run(["ps", "-A", "-o", "comm="], capture_output=True, text=True, timeout=20).stdout.splitlines()]
                cpu = os.getloadavg()[0] / (os.cpu_count() or 1) * 100
            count = {k: sum(n == k for n in names) for k in count}
        except Exception:
            pass
    show = lambda v, unit="": "unreadable" if v is None else "%.1f%s" % (v, unit)
    room = allowed(cfg)
    return "Machine: RAM %s, commit %s free, CPU %s, %s claude, %s node; memory allows %s" % (
        show(ram, " GB"), show(commit, " GB"), "unreadable" if cpu is None else "%d%%" % cpu,
        "?" if count["claude"] is None else int(count["claude"]), "?" if count["node"] is None else int(count["node"]),
        "any number of goals" if room is None else "no new goal (under the %s GB floor)" % cfg.get("min_free_memory_gb", 3.5) if room == 0
        else "%d goal start%s" % (room, "" if room == 1 else "s"))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--html", action="store_true")
    args = parser.parse_args()
    import live_board  # noqa: E402  (live_board imports this module)
    lines = live_board.render()
    sys.stdout.write(live_board.fragment(lines) if args.html else "\n".join(lines) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
