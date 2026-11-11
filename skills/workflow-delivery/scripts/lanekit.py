#!/usr/bin/env python3
"""The lane's kit, imported by lane.py and goal.py; not a command. Three parts:

1. Copies of the slots.py pieces lane.py uses (EXIT_WAIT, EXIT_STALE, POLL, flow_file, time_limit, lanes_dir,
   port_base, last_change, lane_limit, timeout_line, rows_line and the helpers they call): a skill imports only its own
   scripts, so workflow-delivery keeps these copies. Each copied function (COPIED) must have exactly the same source as
   in workflow-regression/scripts/slots.py; dev/toy/test-lane-control.sh fails when one drifts. Change both together.
2. The one commit a lane may make before it starts (prep, generated): the re-rendered wiki Tests tables and the run
   dates they come from. A page counts only when its edits are all in its ## Tests section (what criteria.py renders),
   or it is the full Tests page render writes whole; any other change refuses with LANE_DIRTY and nothing is rendered or
   committed. The commit is `git commit --only` of those paths with a 60 s timeout; a refused or hung commit unstages
   them and starts nothing (LANE_PREP_FAILED).
3. What goal.py pr does after its pr lane passes, before it pushes (record(state, base)):
  1. issue states (V5): `tests.py issues --write` once, bounded to 120 s; a failure leaves the file and prints NOTE;
  2. run results (DX-19): `lanes_cli.py merge-runs` merges the branch's lane record's row results, with any flaky flag,
     into .loop/regression-runs.tsv under the row lock, so the rows a goal ran show on the wiki and in health once it
     merges; a failure prints NOTE;
  3. one commit of those two files when they changed, with the wiki Tests tables re-rendered from them, then
  4. state["pr_lane"] (the pull request body's lane part), state["pr_head"] (the head goal.py pr pushes: the lane's
     commit plus that bookkeeping commit) and state["pr_base"] (the base commit it was merged with), for merge.py's
     HEAD_MOVED and BASE_MOVED checks.
Exit codes and messages: workflow-regression/references/commands.md.
"""
import fcntl
import glob
import json
import os
import re
import subprocess
import sys
import time

import budget

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
COPIED = ('flow_file', '_flow', 'time_limit', 'lanes_dir', 'check', '_open', 'port_base', 'last_change', 'lane_limit', 'timeout_line', 'rows_line')  # from slots.py, kept identical (dev/toy/test-lane-control.sh)


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
    budget.hit(os.path.dirname(base), os.path.basename(base)[:-len(".%s-lane" % name)], name, "test", int(cut[-1][0]), cut[-1][1])
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

def git_out(*args):
    done = subprocess.run(["git"] + list(args), capture_output=True, text=True)
    return done.stdout.strip() if done.returncode == 0 else ""


def issues(top):
    tests = os.path.join(REG, "tests.py")
    if not os.path.exists(tests) or not os.path.exists(os.path.join(top, ".loop", "regression.tsv")):
        return
    try:
        done = subprocess.run([sys.executable, tests, "issues", "--write", "--root", top], capture_output=True, text=True,
                              timeout=120, stdin=subprocess.DEVNULL)
        why = (done.stderr.strip().splitlines() or [""])[-1] if done.returncode else ""
    except subprocess.TimeoutExpired:
        why = "timed out"
    if why:
        print("NOTE: issue states not refreshed: %s" % why[:200])


def results(top):
    """Run results (DX-19): workflow-regression's lanes_cli.py merge-runs, run by path (a skill never imports another's)."""
    cli = os.path.join(REG, "lanes_cli.py")
    if not os.path.exists(cli):
        return
    done = subprocess.run([sys.executable, "-B", cli, "merge-runs", "--root", top], capture_output=True, text=True,
                          stdin=subprocess.DEVNULL)  # -B: it must not write a cache into the skill folder
    if done.returncode:
        why = ((done.stderr or done.stdout).strip().splitlines() or ["exit %d" % done.returncode])[-1]
        print("NOTE: lane results not recorded in regression-runs.tsv: %s" % why[:200])


def lane_part(slug):
    """The pull request body's lane part (DX-21): the pr lane's LANE line, and each row with why it ran, folded."""
    common = git_out("rev-parse", "--git-common-dir")
    base = os.path.join(os.path.abspath(common), "loop", "runs", "%s.pr-lane" % slug) if common and slug else ""
    try:
        with open(base + ".last") as handle:
            line = str(json.load(handle).get("line", "")).split("\n")[0]
        with open(base + ".txt") as handle:
            rows = [text.rstrip() for text in handle if text.startswith(("SELECTED ", "FULL (", "UNMAPPED "))]
    except (OSError, ValueError):
        return ""
    folded = "\n\n<details><summary>Rows and why they ran</summary>\n\n```\n%s\n```\n</details>" % "\n".join(rows) if rows else ""
    return "\n### Regression lane\n\n%s%s\n" % (line, folded) if line else ""


def undo(top, paths):
    """Put the uncommitted bookkeeping back to HEAD, so the next lane doesn't start on LANE_DIRTY."""
    subprocess.run(["git", "reset", "-q", "--"] + paths, cwd=top, capture_output=True)
    for path in paths:
        if subprocess.run(["git", "cat-file", "-e", "HEAD:" + path], cwd=top, capture_output=True).returncode == 0:
            subprocess.run(["git", "checkout", "-q", "HEAD", "--", path], cwd=top, capture_output=True)


def record(state, base):
    """Refresh issue states and run results, commit them if they changed, then note the head and base for merge.py."""
    top = git_out("rev-parse", "--show-toplevel")
    if top:
        issues(top)
        results(top)
        changed = [path for path in FILES if git_out("status", "--porcelain", "--", path)]
        criteria = os.path.join(os.path.dirname(REG), "..", "workflow-docs", "scripts", "criteria.py")
        try:
            cfg = json.load(open(os.path.join(top, ".loop", "config.json")))
        except (OSError, ValueError):
            cfg = {}
        cfg = cfg if isinstance(cfg, dict) else {}
        try:
            if changed and os.path.exists(os.path.join(top, ".loop", "docs.tsv")) and os.path.exists(criteria):
                subprocess.run([sys.executable, criteria, "render"], cwd=top, capture_output=True, text=True, timeout=300)
                changed += generated(cfg)  # only the Tests tables it re-rendered: never other dirty files
            if changed:  # a new (untracked) file must be added before --only can commit it
                subprocess.run(["git", "add", "--"] + changed, cwd=top, capture_output=True, text=True)
                done = subprocess.run(["git", "commit", "--only", "-q", "-m", "pr: record issue states and the lane's results",
                                       "--"] + changed, cwd=top, capture_output=True, text=True, stdin=subprocess.DEVNULL,
                                      timeout=60)
                if done.returncode:
                    print("NOTE: the bookkeeping commit failed: %s; those files were put back (a new file stays, untracked), so "
                          "the next pr run derives them again" % ((done.stderr or done.stdout).strip().splitlines() or ["?"])[-1])
                    undo(top, changed)
        except subprocess.TimeoutExpired as error:  # never crash pr after its lane passed
            print("NOTE: the bookkeeping step timed out (%s); nothing more committed" % " ".join(error.cmd[:3]))
            lock = os.path.join(top, git_out("rev-parse", "--git-path", "index.lock"))
            if error.cmd[0] == "git" and os.path.exists(lock):  # only our killed commit's lock; a render takes none
                os.remove(lock)
            undo(top, changed)
    state["pr_lane"] = lane_part(state.get("slug", ""))
    head = git_out("rev-parse", "HEAD")
    state["pr_head"] = head
    state["pr_base"] = git_out("merge-base", head, "origin/" + base) or git_out("rev-parse", "origin/" + base)


def need_lane(runs, slug, reply, step="qa"):
    """(why, fix, code) when record qa|ship must refuse (no lane passed on HEAD), else None."""
    text = open(reply).read() if os.path.isfile(reply) else ""
    found = re.findall(r"^\W*STEP:\s*(done|skipped|pending|failed)\b", text, re.M | re.I)
    if found and found[-1].lower() == "failed" and not re.search(r"^\W*PENDING:", text, re.M):
        return None
    head = git("rev-parse", "HEAD").stdout.strip()
    try:
        ok = open(os.path.join(runs, "%s.%s-lane.ok" % (slug, step))).read().strip()
    except OSError:
        ok = ""
    fix = "python3 %s lane %s %s" % (os.path.join(HERE, "role.py"), slug, step)
    if not ok:
        return ("the %s lane has not passed on %s" % (step, head[:12]), fix, "LANE_MISSING")
    if ok != head:
        return ("HEAD moved since the %s lane passed (lane on %s, HEAD %s)" % (step, ok[:12], head[:12]),
                fix + " (reruns only the rows the change can affect)",
                "HEAD_MOVED")
    return None


def died(log):
    return "LANE_DIED: the lane ended with no exit status (log %s); the next call starts a new lane; %s." % (log, NOTHING)


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
