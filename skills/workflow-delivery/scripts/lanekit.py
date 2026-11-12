#!/usr/bin/env python3
"""The lane's kit, imported by lane.py and goal.py; not a command. Five parts:

1. Copies of the slots.py pieces lane.py uses (EXIT_WAIT, EXIT_STALE, POLL, flow_file, time_limit, lanes_dir, port_base,
   last_change, lane_limit, timeout_line, rows_line and their helpers): a skill imports only its own scripts. Each copy
   (COPIED) must match workflow-regression/scripts/slots.py exactly; dev/toy/test-lane-control.sh fails on drift.
2. The one commit a lane may make before it starts (prep, generated): the re-rendered wiki Tests tables and the run
   dates they come from, as `git commit --only` of those paths with a 60 s timeout. Any other change refuses with
   LANE_DIRTY; a refused or hung commit unstages and starts nothing (LANE_PREP_FAILED).
3. What goal.py pr does after its lane passes, before it pushes (record(state, base)): issue states (`tests.py issues
   --write`, 120 s), run results merged into .loop/regression-runs.tsv (`lanes_cli.py merge-runs`), one commit of
   those two files with the Tests tables re-rendered, then state["pr_lane"], ["pr_head"] and ["pr_base"] for
   merge.py's HEAD_MOVED and BASE_MOVED checks. Messages: workflow-regression/references/commands.md.
4. The step budgets: step_budget_minutes (default 30) bounds a review or ship step, test_budget_minutes (default 15)
a test run; neither goes under 15; budget_hits in the run file names what a stopped step left.
5. Who may signal a lane: pstart/same (a pid counts only while its start time matches the one stored with it), audit
(runs/kills.log, one line per signal sent) and died/death (LANE_DIED names the signal that ended a lane).
"""
import portlock as fcntl
import glob
import json
import os
import re
import subprocess
import sys
import time

import tempfile

# No terminal, no waiting: a prompt from git or gh must fail, not block.
os.environ.update(GIT_TERMINAL_PROMPT="0", GH_PROMPT_DISABLED="1", GIT_EDITOR="true", GIT_ASKPASS="true", SSH_ASKPASS="true")

HERE = os.path.dirname(os.path.abspath(__file__))
REG = os.path.normpath(os.path.join(HERE, "..", "..", "workflow-regression", "scripts"))
NOTHING = "the lane committed and pushed nothing"
BOOKKEEPING = (".loop/regression-runs.tsv", ".loop/goals/", ".loop/queue.md", ".loop/findings.md")
FILES = (".loop/regression-issues.tsv", ".loop/regression-runs.tsv")
EXIT_WAIT, EXIT_STALE, POLL = 4, 5, 2.0
EXIT_PREP = 125  # a lane stopped at its preparation budget, before any row
TERMINAL = ("pass", "fail")
COPIED = ('flow_file', '_flow', 'time_limit', 'lanes_dir', 'check', '_open', 'port_base', 'last_change', 'lane_limit', 'timeout_line', 'rows_line')  # from slots.py, kept identical


def flow_file():
    return os.path.expanduser(os.environ.get("LOOP_FLOW") or "~/.workflow-loop/flow.json")


def _flow():
    try:
        data = json.load(open(flow_file()))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def time_limit(root):
    """A lane's time limit in seconds and its source: the flow file's limit, else step_limit, else 2700."""
    value = _flow().get("limit")
    if value:
        return float(value), "flow file limit"
    try:
        value = json.load(open(os.path.join(root, ".loop", "config.json"))).get("step_limit")
    except (OSError, ValueError, AttributeError):
        value = None
    return (float(value), "step_limit") if value else (2700.0, "the default")


def lanes_dir():
    return os.path.realpath(os.path.expanduser(os.environ.get("LOOP_LANES_DIR") or "~/.workflow-loop/lanes"))


def check(pool):
    """Create the pool 0700; refuse one that isn't yours or that others can write (OSError names why)."""
    os.makedirs(pool, mode=0o700, exist_ok=True)
    info = os.stat(pool)
    if info.st_uid != os.getuid() or info.st_mode & 0o022:
        raise OSError("not owned by you, or writable by group or others")


def _open(path, flags=0):
    return os.open(path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | flags, 0o600)


def port_base():
    """(fd, base) for a lane's own ports (REG-8): flock the first free port-N file (N 0..99) in the pool and return
    20000 + 100 * N, held while fd stays open; (None, why) when the pool is unavailable or all 100 are held."""
    try:
        pool = lanes_dir()
        check(pool)
        for number in range(100):
            fd = _open(os.path.join(pool, "port-%d" % number))
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                return fd, 20000 + 100 * number
            except BlockingIOError:
                os.close(fd)
    except OSError as error:
        return None, "port pool unavailable: %s" % error
    return None, "no port lease free (100 in use)"


def last_change(pool):
    """The newest slot-file change: the queue clock (any slot taken restarts a waiting lane's span)."""
    times = [os.path.getmtime(path) for path in glob.glob(os.path.join(pool, "slot-*"))]
    return max(times) if times else 0.0


def lane_limit(held):
    """(seconds, source) of a lane's time limit."""
    return held["limit"], held.get("source", "flow file limit")


def timeout_line(text, why, held):
    """The LANE_TIMEOUT line."""
    return ("LANE_TIMEOUT: %s; the lane was killed, rows partly ran, nothing committed or pushed. Fix: run the same "
            "command again, or raise the flow file \"limit\" (else step_limit)." % why)


def budget_note(text, base, name):
    """The BUDGET line of a run that stopped at its test budget (kept on the goal's record), else ''."""
    cut = re.findall(r"^BUDGET (\d+) min: .*?LEFT \d+ to the scheduled full suite: (.*)$", text, re.M)
    if not cut:
        return ""
    hit(os.path.dirname(base), os.path.basename(base)[:-len(".%s-lane" % name)], name, "test", int(cut[-1][0]), cut[-1][1])
    return "\n" + re.findall(r"^BUDGET .*$", text, re.M)[-1]


def rows_line(text, ran, log):
    """The LANE line's end (DX-12, DX-18 ROWS): the goal tier's ROWS counts, the selected rows a timeout left unfinished,
    and the lane log."""
    found = re.search(r"^ROWS: (\d+) selected (\(.*?\)), (\d+) reused; unmapped: (\d+)$", text, re.M)
    if not found:
        return "; log: %s" % log
    count, parts, reused, loose = found.groups()
    return "; rows: %s selected %s, %s reused, %d unfinished; unmapped: %s; log: %s" % (
        count, parts, reused, max(int(count) - ran, 0), loose, log)


# Small lane helpers (moved from lane.py to keep it under the size cap).

def mtime(path):
    try:
        return os.path.getmtime(path)
    except OSError:
        return None


def drop(*paths):
    for path in paths:
        try:
            os.remove(path)
        except (FileNotFoundError, TypeError):  # another poller took it first, or no path
            pass


def read_json(path):
    try:
        data = json.load(open(path))
        return data if isinstance(data, dict) else None
    except (OSError, ValueError):
        return None


def set_last(path, attempt, **fields):
    """Write .last under the lane's lock; pass and fail are terminal for their attempt and never replaced."""
    with open(path + ".lock", "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        old = read_json(path) or {}
        if old.get("attempt") == attempt and old.get("state") in TERMINAL:
            return old
        data = dict(old if old.get("attempt") == attempt else {}, attempt=attempt, **fields)
        temp = "%s.%d.tmp" % (path, os.getpid())
        with open(temp, "w") as handle:
            json.dump(data, handle, indent=1, sort_keys=True)
        os.replace(temp, path)
        return data


# The lane's preparation budget (REG-7, DEL-8): what a lane does before its first row (the Tests-table prep, planning and the
# slot wait) shares one budget, prep_budget_minutes. The lane child (lane.py lane-exec) writes one `.times` record (planning
# seconds, slot-wait seconds and, for a cut, the part that was running); lane.py's finalize reads it here, says the three parts
# on every LANE line, and on a cut prints LANE_PREP_BUDGET and records the hit (kind prep) so the board and health list it.

def holders(pool):
    """Labels of the lanes holding slots now, for the cut line."""
    out = []
    for path in sorted(glob.glob(os.path.join(pool or "", "slot-*"))):
        label = (read_json(path) or {}).get("label")
        if label:
            out.append(str(label)[:60])
    return out


def timing(held, rc):
    """(plan, wait, cut) seconds and part from the lane child's one .times record; zeros when absent or malformed."""
    data = read_json(rc + ".times") or {}
    num = lambda key: float(data[key]) if isinstance(data.get(key), (int, float)) and not isinstance(data.get(key), bool) else 0.0
    return num("plan"), num("wait"), str(data.get("cut") or "")


def before_rows(held, plan, wait):
    """The LANE line's before-rows part (appended after the existing text): prep, planning and slot wait seconds."""
    note = "; before rows: prep %ds, planning %ds, slot wait %ds" % (held.get("prep_s") or 0, plan, wait)
    return note + ("; LOOP_PREP_BUDGET in effect" if held.get("override") else "")


def cut_line(name, held, plan, wait, part):
    """The LANE_PREP_BUDGET text: which part ran long, all three parts, the one shared budget, who holds the slots."""
    got = ", ".join(holders(held.get("pool"))) or "none"
    return ("LANE_PREP_BUDGET: the %s lane used its %s preparation budget before any row ran: %s ran long (prep %ds, "
            "planning %ds, slot wait %ds; the three share one budget); slots held by: %s; no row ran, %s beyond the prep "
            "commit. Fix: run the same command again (it replans on this HEAD); raise prep_budget_minutes only if prep or "
            "planning is the part that ran long." % (name, "%ds (LOOP_PREP_BUDGET)" % held["budget"] if held.get("override") else "%d-minute" % round(held.get("budget", 0) / 60),
                                                      part or "preparation",
                                                      held.get("prep_s") or 0, plan, wait, got, NOTHING))


def prep_hit(base, name, held, plan, wait, part):
    """Record the cut on the goal's run file (kind prep), so the board and health list it with the part."""
    left = "%s ran long (prep %ds, planning %ds, slot wait %ds)" % (part or "preparation", held.get("prep_s") or 0, plan, wait)
    hit(os.path.dirname(base), os.path.basename(base)[:-len(".%s-lane" % name)], name, "prep",
               round(held.get("budget", 0) / 60), left)


def pstart(pid):
    """A process's start time as ps prints it; a reused pid reads differently."""
    return subprocess.run(["ps", "-o", "lstart=", "-p", str(pid)], capture_output=True, text=True).stdout.strip()


def same(pid, start):
    """pid still began at start; with none stored it is never ours to signal."""
    return bool(start) and pstart(pid) == start


def audit(runs, who, pid, why):
    """One line per signal the loop sends: a lane that dies traces to it, or shows there was none."""
    with open(os.path.join(runs, "kills.log"), "a") as handle:
        handle.write("%s %s -> %s (%s): %s\n" % (time.strftime("%FT%T"), who, pid, pstart(pid), why))


def died(log, sig=""):
    return "LANE_DIED: the lane ended with no exit status%s (log %s); %s" % (" (killed by %s)" % sig if sig else "", log, NOTHING)


def death(base, log, sig=""):
    """A lane that ended with no exit status, or was signalled from outside: LANE_DIED, naming the signal."""
    return "fail", died(log, sig), []


def running_line(held, other=None):
    if other:
        return "WAITING: the %s lane of this goal is still running; run this same command again, or block with role.py " \
            "lane-wait SLUG %s" % (other, other)
    queued = held["rc"] + ".queued"
    if os.path.exists(queued):
        return "WAITING: %s; run this same command again" % open(queued).read().strip()
    if "markers" in held and not os.path.exists(held["rc"] + ".started"):
        return "RUNNING: planning the lane; run this same command again"
    return "RUNNING: the regression lane is running; run this same command again"


# The lane's prep commit (was tables.py).

def git(*args):
    return subprocess.run(["git"] + list(args), capture_output=True, text=True)


def dirty():
    out = git("status", "--porcelain", "--no-renames", "--untracked-files=all").stdout
    return [line[3:].strip('"') for line in out.splitlines() if not line[3:].strip('"').startswith(BOOKKEEPING)]


def generated(cfg):
    """The dirty paths a lane may leave or commit before it starts: rendered Tests sections and the full Tests page."""
    return [p for p in dirty() if is_page(p, cfg) and tests_only(p)]


def is_page(path, cfg):
    return path.startswith((cfg.get("wiki_dir") or "docs/wiki").rstrip("/") + "/") and path.endswith(".md")


def tests_only(path):
    """A page whose edits are all in its ## Tests section (what criteria.py renders) is a prep path; so is the full Tests
    page (Tests.md), which render writes whole (DOC-10)."""
    if os.path.basename(path) == "Tests.md":
        return True
    now = open(path).read() if os.path.exists(path) else None
    shown = git("show", "HEAD:" + path)
    if now is None or shown.returncode:
        return False
    return outside(now) == outside(shown.stdout) if outside(shown.stdout) is not None else now == shown.stdout


def outside(text):
    """A page without its ## Tests section (from that heading to the next ## heading): what a render never changes."""
    found = re.search(r"^## Tests[ \t]*$", text, re.M)
    if not found:
        return None  # a page with no Tests section: only an identical page is unchanged
    rest = re.search(r"^## ", text[found.end():], re.M)
    return text[:found.start()] + (text[found.end() + rest.start():] if rest else "")


def prep(top, cfg, log):
    """Re-render the Tests tables and commit them with the run dates (or nothing). Returns (line, refusal)."""
    criteria = os.path.normpath(os.path.join(HERE, "..", "..", "workflow-docs", "scripts", "criteria.py"))
    for path in dirty():
        if not (is_page(path, cfg) and tests_only(path)):
            if is_page(path, cfg):
                return None, "LANE_DIRTY: %s has edits above its ## Tests section; commit or revert them, then run the " \
                    "same command again; %s." % (path, NOTHING)
            return None, "LANE_DIRTY at start: %s. Fix: commit or remove them; %s." % (", ".join(dirty()[:10]), NOTHING)
    if not os.path.exists(os.path.join(top, ".loop", "docs.tsv")) or not os.path.exists(criteria):
        return "", None
    done = subprocess.run([sys.executable, criteria, "render"], cwd=top, capture_output=True, text=True, timeout=300)
    if done.returncode:
        first = (done.stderr or done.stdout).strip().splitlines()[-1:] or ["exit %d" % done.returncode]
        return None, "LANE_PREP_FAILED: criteria.py render failed: %s. Fix: run it by hand; %s." % (first[0][:200], NOTHING)
    paths = [p for p in dirty() if is_page(p, cfg)]
    if git("status", "--porcelain", "--", ".loop/regression-runs.tsv").stdout.strip():
        paths.append(".loop/regression-runs.tsv")
    if not paths:
        return "", None
    proc = subprocess.Popen(["git", "commit", "--only", "-q", "-m", "Lane: re-render the Tests tables", "--"] + paths,
                            cwd=top, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, stdin=subprocess.DEVNULL,
                            start_new_session=True)  # its own group: a hung hook's children die with it
    try:
        out, err = proc.communicate(timeout=60)
        why = (err or out).strip().splitlines()[-1:] if proc.returncode else None
    except subprocess.TimeoutExpired:
        import signal
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except OSError:  # already gone
            pass
        out, err = proc.communicate()
        lock = os.path.join(top, git("rev-parse", "--git-path", "index.lock").stdout.strip())
        if os.path.exists(lock):  # the commit we killed held it; left behind it blocks every later commit
            os.remove(lock)
        why = ["timed out after 60s"]
    if why is not None:
        with open(log, "a") as handle:
            handle.write("prep commit: %s\n%s\n" % (" ".join(paths), err or out or ""))
        git("reset", "-q", "--", *paths)
        return None, ("LANE_PREP_FAILED: git commit failed: %s (full output: %s); the prep paths are unstaged and left "
                      "modified, nothing committed or pushed. Fix: make the commit pass (see the log), then run role.py lane "
                      "SLUG NAME again." % ((why or ["no message"])[0][:200], log))
    return "LANE_PREP: re-rendered the Tests tables (commit %s)" % git("rev-parse", "--short", "HEAD").stdout.strip(), None


# goal.py pr's bookkeeping (was prsteps.py).

# ---- the time budgets of the loop's steps (was budget.py)
FLOOR = 15
DEFAULTS = {"step_budget_minutes": 30, "test_budget_minutes": 15, "prep_budget_minutes": 15}
LEFT = re.compile(r"^\W*BUDGET:\s*left:\s*(.+)$", re.M | re.I)


def minutes(cfg, key):
    """The setting in whole minutes; exits with a fix line when it is under the 15-minute floor or not a whole number."""
    value = cfg.get(key, DEFAULTS[key])
    if isinstance(value, bool) or not isinstance(value, int) or value < FLOOR:
        sys.exit("REFUSED: %s is %r in .loop/config.json, under the %d-minute floor. Fix: set it to %d or more." % (
            key, value, FLOOR, FLOOR))
    return value


def prep_seconds(cfg):
    """(seconds, override) a lane may spend before its first row: prep_budget_minutes, or the test-only LOOP_PREP_BUDGET
    (whole seconds, never read from config), which the lane line then says is in effect."""
    value = os.environ.get("LOOP_PREP_BUDGET", "")
    if value.isdigit() and int(value) > 0:
        return int(value), True
    return minutes(cfg, "prep_budget_minutes") * 60, False


def label(hit):
    """What a budget hit was: a step, preparation (before a lane's first row) or tests."""
    return {"step": "step", "prep": "preparation"}.get(hit.get("kind"), "tests")


def seconds(cfg, key, limit=0):
    """Seconds a step or run may take: the budget, or the flow file's own limit when that is shorter."""
    budget = minutes(cfg, key) * 60
    return min(budget, limit) if limit else budget


def left_of(text):
    """What a reply says it left, from its last `BUDGET: left: ...` line, else ''."""
    found = LEFT.findall(text or "")
    return " ".join(found[-1].split())[:300] if found else ""


def hit(runs, slug, step, kind, limit, left):
    """Record that STEP (kind step: the step itself, test: its test run) reached its budget of LIMIT minutes and what it left."""
    path = os.path.join(runs, slug + ".json")
    try:
        with open(path) as handle:
            state = json.load(handle)
    except (OSError, ValueError):
        return
    kept = [h for h in state.get("budget_hits") or [] if not (h.get("step") == step and h.get("kind") == kind)]
    state["budget_hits"] = kept + [{"step": step, "kind": kind, "minutes": limit, "left": left or "not stated"}]
    with tempfile.NamedTemporaryFile("w", dir=runs, delete=False, suffix=".tmp") as handle:
        json.dump(state, handle, indent=2)
    os.replace(handle.name, path)


def reached(state, step):
    """Whether this goal's step was stopped at its step budget (recorded by flow.py, never by the step's own words)."""
    return any(h.get("step") == step and h.get("kind") == "step" for h in state.get("budget_hits") or [])


def lines(state):
    """One line per budget hit of a run record, for the board and for health."""
    return ["%s: %s hit its %s-minute budget; left: %s" % (
        state.get("slug", "?"), "%s %s" % (h.get("step"), label(h)), h.get("minutes"),
        h.get("left")) for h in state.get("budget_hits") or [] if isinstance(h, dict)]
