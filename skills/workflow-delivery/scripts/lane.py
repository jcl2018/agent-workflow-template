#!/usr/bin/env python3
"""A goal's regression lane: start or poll it, wait for it, and check it before a step is recorded.

Imported by role.py. Run as `role.py lane SLUG qa|ship|pr` (start or poll), `role.py lane-wait SLUG qa|ship|pr
[--timeout S]` (block until HEAD's lane ends) and `lane.py lane-exec ...` (a lane's child). A lane tests committed HEAD
and never pushes; it may first commit the re-rendered Tests tables. One lane per goal runs at a time; a lane on an older
HEAD is stopped first. Its latest result is <runs>/<slug>.<name>-lane.last. Messages: lanekit.py, workflow-regression/references/commands.md.
Its TMPDIR is a folder under the system temp, per repo, goal and lane, never inside a git checkout, removed when it ends.
"""
import portlock as fcntl
import json
import os
import re
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
REG = os.path.normpath(os.path.join(HERE, "..", "..", "workflow-regression", "scripts"))
sys.path.insert(0, HERE)
import lanekit  # noqa: E402
# No terminal, no waiting: a prompt from git or gh must fail, not block (lanekit sets it too).
os.environ.update(GIT_TERMINAL_PROMPT="0", GH_PROMPT_DISABLED="1", GIT_EDITOR="true", GIT_ASKPASS="true", SSH_ASKPASS="true")
from lanekit import NOTHING, TERMINAL, died, dirty, drop, generated, git, mtime, prep, read_json, running_line, set_last  # noqa: E402,F401

NAMES = ("qa", "ship", "pr")
GRACE = 60  # seconds a claimed rc belongs to its finisher; an older one is an orphan


def tmp_for(top, slug, name):
    """REG-8: the prefix of the lane's own temp folder, outside every git checkout (#814); "" when the system temp is in one."""
    root = here = os.path.realpath(tempfile.gettempdir())
    while not os.path.lexists(here + "/.git") and here != "/":
        here = os.path.dirname(here)
    return "" if os.path.lexists(here + "/.git") else "%s/loop-lane-%08x-%s-%s-" % (root, zlib.crc32(os.path.realpath(top).encode()), slug, name)


def rm_tmp(held):
    path = (held or {}).get("tmp") or ""
    if os.path.basename(path).startswith("loop-lane-") and not os.path.islink(path):
        shutil.rmtree(path, ignore_errors=True)


flow_spec = lanekit._flow  # the flow file as a dict ({} when missing or bad)


def lane_argv(seconds=0):
    """The one lane command, resolved from this package: every prompt, run and receipt uses exactly this."""
    return ["python3", os.path.join(REG, "regression.py"), "run", "land", "--reuse", "--tier", "goal"] + (
        ["--budget", str(int(seconds))] if seconds else [])


def lane_text():
    return shlex.join(lane_argv())


def kill(pid):
    try:
        os.killpg(pid, signal.SIGTERM)
    except OSError:  # already gone
        pass


def alive(pid):
    """A pid that runs and is no zombie. EPERM means it runs but this poller may not signal it (a sandbox): alive."""
    try:
        os.kill(pid, 0)
    except PermissionError:
        pass
    except (OSError, TypeError):
        return False
    return subprocess.run(["ps", "-o", "stat=", "-p", str(pid)], capture_output=True, text=True).stdout.strip()[:1] != "Z"


def deadline(held):
    """The liveness clock: the limit from the started marker; 4x while queued or planning."""
    if "markers" not in held:
        return held["started"] + held["limit"], "past its time limit of %ds" % held["limit"]
    began = mtime(held["rc"] + ".started")
    if began:
        return began + lanekit.lane_limit(held)[0], "past its time limit of %ds (%s)" % lanekit.lane_limit(held)
    if held.get("prep_by"):  # before the first row the preparation budget rules
        return held["prep_by"], "past its preparation budget"
    if os.path.exists(held["rc"] + ".queued"):
        return max(held["started"], lanekit.last_change(held.get("pool") or lanekit.lanes_dir())) + 4 * held["limit"], \
            "queued or planning past %ds" % (4 * held["limit"])
    return held["started"] + 4 * held["limit"], "queued or planning past %ds" % (4 * held["limit"])


def live(held):
    """A lane job still ours and running: no exit status yet, inside its deadline."""
    return not os.path.exists(held["rc"]) and time.time() < deadline(held)[0] + 60 and alive(held["pid"])


def job_of(runs, slug, name):
    base = os.path.join(runs, "%s.%s-lane" % (slug, name))
    return base, read_json(base + ".job")


def stop(base, held):
    if held and live(held):
        kill(held["pid"])
    drop(base + ".job")
    if held:
        rm_tmp(held)
        drop(*[held["rc"] + end for end in ("", ".queued", ".started", ".note", ".claimed", ".times", ".times.tmp")])


def fresh(held):
    """A claimed rc younger than GRACE: another caller is finishing that lane now."""
    at = mtime(held["rc"] + ".claimed")
    return bool(at) and time.time() - at < GRACE


def finalize(base, held, name):
    """Turn an ended lane into its result, once: the first caller claims the rc file under the lane's lock."""
    out, last = base + ".txt", base + ".last"
    with open(base + ".lock", "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        ended = mtime(held["rc"])
        try:
            os.replace(held["rc"], held["rc"] + ".claimed")
            os.utime(held["rc"] + ".claimed")
        except FileNotFoundError:
            done = read_json(last) or {}
            if done.get("attempt") == held["attempt"] and done.get("state") in TERMINAL:
                return ("pass" if done["state"] == "pass" else "fail"), done.get("line", ""), done.get("ids", [])
            if fresh(held):
                return "running", "RUNNING: the lane is being finished by another caller; run this same command again", []
            if not os.path.exists(held["rc"] + ".claimed"):
                stop(base, held)
                return "fail", died(out), []
            os.utime(held["rc"] + ".claimed")  # its finisher died: this caller takes the orphan claim over
    rc = int((open(held["rc"] + ".claimed").read().strip() or "1"))
    rm_tmp(held)
    text = open(out).read() if os.path.exists(out) else ""
    began, now = mtime(held["rc"] + ".started"), time.time()
    notes = open(held["rc"] + ".note").read().strip() if os.path.exists(held["rc"] + ".note") else ""
    ids = re.findall(r"^(?:FAIL|UNPROVEN) ([^\s:]+)", text, re.M)
    kind = (re.findall(r"^(REUSED|AFFECTED|FULL(?: \([^)]*\))?)", text, re.M) or ["FULL"])[0]
    ran, reused = len(re.findall(r"^(?:PASS|FAIL|KNOWN) ", text, re.M)), re.findall(r"\((\d+) reused\)", text)
    took = (ended or now) - (began or held["started"])
    line = "LANE %s %s %d/%d in %ds" % (name, kind, ran, ran + int((reused or [0])[0]), took)
    cfg = read_json(os.path.join(git("rev-parse", "--show-toplevel").stdout.strip(), ".loop", "config.json")) or {}
    limit = cfg.get("goal_lane_minutes")
    limit = limit if isinstance(limit, (int, float)) and not isinstance(limit, bool) and limit > 0 else 10
    if not kind.startswith("FULL") and took > limit * 60:
        line += "; over %g min (goal_lane_minutes)" % limit
    plan, wait, part = lanekit.timing(held, held["rc"])
    line += lanekit.budget_note(text, base, name)
    killed = re.findall(r"^KILLED (\S+): signal (\S+) \(pid (\d+)\)", text, re.M)
    if killed:
        line += "; " + ", ".join("%s killed by %s (pid %s)" % k for k in killed)
    if began and began - held["started"] >= 1:
        line += " (queued %ds)" % (began - held["started"])
    line += lanekit.before_rows(held, plan, wait) + lanekit.rows_line(text, ran, out)
    status, made = "fail", generated(cfg)
    after = [p for p in dirty() if p not in made]
    if rc == lanekit.EXIT_STALE:
        stop(base, held)
        set_last(base + ".last", held["attempt"], state="ended", rc=rc, note=notes, ended=now)
        return "running", "%s\nRUNNING: the lane restarts on the new plan; run this same command again" % notes, []
    if not began and "markers" in held and rc not in (0, lanekit.EXIT_PREP):
        line += "\nthe lane never reported its start (a test_record wrapper may strip _LOOP_LANE_* variables)"
    if after:
        line += "\nLANE_DIRTY at end: a row left %s. Fix: make it clean up; %s." % (", ".join(after[:10]), NOTHING)
        ids = []
    elif rc == lanekit.EXIT_PREP:
        line += "\n" + lanekit.cut_line(name, held, plan, wait, part)
        lanekit.prep_hit(base, name, held, plan, wait, part)
    elif rc == 124:
        line += "\n" + lanekit.timeout_line(text, deadline(held)[1], held)
    elif rc == lanekit.EXIT_WAIT:
        line += "\nLANE_BUG: the lane's child stopped waiting for a slot (exit 4), which a lane never does; %s." % NOTHING
    elif rc:
        line += "\nLANE_FAIL %s (log %s). Reproduce one: python3 %s run <id>; %s." % (
            ", ".join(ids) or "exit %d" % rc, out, lane_argv()[1], NOTHING)
    else:
        status = "pass"
        with open(base + ".ok", "w") as handle:
            handle.write(held["head"])
    set_last(base + ".last", held["attempt"], state=status, rc=rc, line=line, ids=ids, note=notes, ended=now,
             prep_s=held.get("prep_s") or 0, plan_s=plan, wait_s=wait)
    stop(base, held)
    return status, line, ids


def lane(runs, slug, name, spec, cfg, wait=90):
    """Start or poll a goal's qa, ship or pr lane on committed HEAD: (running|pass|fail, line, failing ids)."""
    head = git("rev-parse", "HEAD").stdout.strip()
    base, held = job_of(runs, slug, name)
    if held and held.get("head") != head:  # HEAD moved: that lane tested other content
        stop(base, held)
        held = None
    for other in NAMES:
        other_base, other_held = job_of(runs, slug, other)
        if other == name or not other_held:
            continue
        if other_held.get("head") != head:  # an older HEAD's lane never blocks this one
            stop(other_base, other_held)
        elif live(other_held):
            return "running", running_line(other_held, other), []
    if held and not live(held) and not os.path.exists(held["rc"]) and not fresh(held):
        if time.time() - held["started"] > 30 and not os.path.exists(held["rc"] + ".claimed"):  # an orphan claim: finalize
            stop(base, held)
            held = None
    done = read_json(base + ".last") or {}
    if not held and done.get("head") == head and done.get("state") == "pass" and not dirty():  # lane-wait finished it
        return "pass", done.get("line", ""), []
    if not held:
        top = git("rev-parse", "--show-toplevel").stdout.strip()
        began_prep = time.time()
        line, refusal = prep(top, cfg, base + ".txt")
        if refusal:
            return "fail", refusal, []
        spent, (budget_s, override) = time.time() - began_prep, lanekit.prep_seconds(cfg)
        if spent >= budget_s:  # preparing the Tests tables alone used the budget: no lane is started
            cut = {"budget": budget_s, "prep_s": spent, "override": override}
            lanekit.prep_hit(base, name, cut, 0, 0, "preparing the Tests tables")
            return "fail", lanekit.cut_line(name, cut, 0, 0, "preparing the Tests tables"), []
        head = git("rev-parse", "HEAD").stdout.strip()
        prefix = [os.path.expanduser(part) for part in spec.get("test_record") or []]
        if prefix and not (shutil.which(prefix[0]) or os.path.isfile(prefix[0])):
            return "fail", "LANE_RECORDER: the flow file's test_record command %s isn't on this machine. Fix: install it " \
                "or remove \"test_record\" from the flow file; %s." % (prefix[0], NOTHING), []
        seconds, source = (float(spec["limit"]), "flow file limit") if spec.get("limit") else lanekit.time_limit(top)
        tests = lanekit.minutes(cfg, "test_budget_minutes") * 60  # rows stop at it; the lane limit is a backstop
        if tests + 300 < seconds:
            seconds, source = tests + 300, "test_budget_minutes"
        tmp = tmp_for(top, slug, name)
        if not tmp:
            return "fail", "LANE_TMPDIR: %s is in a git checkout. Fix: set TMPDIR to a folder outside any repo; %s." % (tempfile.gettempdir(), NOTHING), []
        try:
            handle = os.open(base + ".job", os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            return "running", "RUNNING: run this same command again", []
        attempt = "%d-%d" % (os.getpid(), time.time() * 1000)
        held = {"head": head, "attempt": attempt, "started": time.time(), "limit": seconds, "source": source,
                "rc": "%s.%s.rc" % (base, attempt), "pool": lanekit.lanes_dir(), "markers": 1, "prep_s": spent,
                "prep_by": 0 if prefix else began_prep + budget_s, "budget": budget_s, "override": override}  # a wrapper may strip the markers
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", _LOOP_LANE_LABEL="%s/%s %s" % (os.path.basename(top), slug, name),
                   _LOOP_LANE_QUEUED=held["rc"] + ".queued", _LOOP_LANE_STARTED=held["rc"] + ".started",
                   _LOOP_LANE_NOTE=held["rc"] + ".note", _LOOP_LANE_PREP_BY=str(held["prep_by"]))
        env.pop("_LOOP_LANE_HELD", None)
        env["TMPDIR"] = held["tmp"] = tempfile.mkdtemp(prefix=os.path.basename(tmp), dir=os.path.dirname(tmp))  # REG-8: new each start
        with open(base + ".txt", "w") as log:
            if line:
                log.write(line + "\n")
            child = subprocess.Popen([sys.executable, os.path.abspath(__file__), "lane-exec", held["rc"], str(seconds),
                                      base + ".last", attempt, held["pool"], "--"] + prefix + lane_argv(tests), stdout=log,
                                     stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, start_new_session=True, env=env)
        held["pid"] = child.pid
        os.write(handle, json.dumps(held).encode())
        os.close(handle)
        set_last(base + ".last", attempt, head=head, state="starting", started=held["started"], log=base + ".txt",
                 pool=held["pool"], rc=None, line=line or "", note="")
        if line:
            print(line)
    stop_at = time.time() + wait
    while live(held) and time.time() < stop_at:
        time.sleep(0.2)
    if live(held):
        return "running", running_line(held), []
    if not os.path.exists(held["rc"]) and not os.path.exists(held["rc"] + ".claimed"):
        stop(base, held)
        return "fail", died(base + ".txt"), []
    return finalize(base, held, name)


def lane_status(runs, slug, name):
    """Status-and-finalize without spawning or committing: (state, line): running, pass, fail or none."""
    head = git("rev-parse", "HEAD").stdout.strip()
    base, held = job_of(runs, slug, name)
    if held and held.get("head") == head:
        if live(held):
            return "running", running_line(held)
        if os.path.exists(held["rc"]) or os.path.exists(held["rc"] + ".claimed"):
            status, line, _ = finalize(base, held, name)
            return status, line
        if time.time() - held["started"] > 30 and not alive(held["pid"]):  # ran and died with no exit status: never NO LANE
            stop(base, held)
            return "fail", died(base + ".txt")
    done = read_json(base + ".last") or {}
    if done.get("head") == head and done.get("state") in TERMINAL:
        return done["state"], done.get("line", "")
    return "none", "NO LANE: none ran on %s; start one with role.py lane %s %s" % (head[:12], slug, name)


def wait_for(runs, slug, name, timeout=None):
    """role.py lane-wait: block while this HEAD's lane runs; exit 0 pass, 1 fail, 2 timeout, 3 none."""
    until = time.time() + timeout if timeout else None
    while True:
        state, line = lane_status(runs, slug, name)
        if state != "running":
            print(line, file=sys.stdout if state in ("pass", "none") else sys.stderr)
            return {"pass": 0, "fail": 1, "none": 3}[state]
        if until and time.time() > until:
            print("LANE_WAIT_TIMEOUT: the %s lane of %s still %s after %ds; it keeps running. Fix: run role.py lane-wait "
                  "%s %s again" % (name, slug, "waiting" if line.startswith("WAITING") else "running", timeout, slug, name),
                  file=sys.stderr)
            return 2
        time.sleep(lanekit.POLL)


def lane_exec(rc, seconds, last, attempt, pool, argv):
    """A lane's child: run the lane in its own group, kill it past deadline(), write .last ended, then the rc."""
    held = {"rc": rc, "limit": seconds, "started": time.time(), "pool": pool, "markers": 1,
            "prep_by": float(os.environ.get("_LOOP_LANE_PREP_BY") or 0)}
    marks = {}  # when the .queued and .started markers were first seen: the planning and the slot wait
    lease, port = lanekit.port_base()  # REG-8: its own ports, held while this child lives
    if lease is None:
        with open(rc + ".note", "a") as note:
            note.write("Note: %s; LOOP_LANE_PORT_BASE unset\n" % port)
    env = dict(os.environ)
    env.pop("LOOP_LANE_PORT_BASE", None)  # never an outer lane's range
    if lease is not None:
        env["LOOP_LANE_PORT_BASE"] = str(port)
    child, seen = subprocess.Popen(argv, env=env), None
    try:
        while True:
            try:
                code = child.wait(timeout=1)
                break
            except subprocess.TimeoutExpired:
                pass
            state = "running" if os.path.exists(rc + ".started") else "queued" if os.path.exists(rc + ".queued") else None
            if state and state not in marks:
                marks[state] = time.time()
            if state and state != seen:
                seen = set_last(last, attempt, state=state) and state
            if time.time() > deadline(held)[0]:
                cut = held["prep_by"] and not os.path.exists(rc + ".started")  # before the first row: the preparation budget
                marks["cut"] = "waiting for a slot" if "queued" in marks else "planning" if cut else ""
                signal.signal(signal.SIGTERM, signal.SIG_IGN)
                kill(os.getpgrp())
                try:
                    child.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    child.kill()
                code = lanekit.EXIT_PREP if cut and not os.path.exists(rc + ".started") else 124  # a row began at the last moment: timeout
                break
    except Exception:  # an unexpected failure: a compact trace in the lane log, and a failing status
        import traceback
        print("\n".join(traceback.format_exc().splitlines()[-20:]), flush=True)
        code = 1
    set_last(last, attempt, state="ended", rc=code)
    now, queued, ran = time.time(), marks.get("queued"), marks.get("running")
    with open(rc + ".times.tmp", "w") as handle:  # one atomic record
        json.dump({"plan": (queued or ran or now) - held["started"], "wait": (ran or now) - queued if queued else 0,
                   "cut": marks.get("cut", "")}, handle)
    os.replace(rc + ".times.tmp", rc + ".times")
    with open(rc + ".tmp", "w") as handle:
        handle.write(str(code))
    os.replace(rc + ".tmp", rc)


def main(argv):
    """role.py lane / lane-wait, and lane.py lane-exec."""
    if argv[:1] == ["lane-exec"]:
        return lane_exec(argv[1], float(argv[2]), argv[3], argv[4], argv[5], argv[7:])
    if argv[:1] in (["lane"], ["lane-wait"]) and len(argv) >= 3 and argv[2] in NAMES:
        top = os.path.abspath(git("rev-parse", "--git-common-dir").stdout.strip())
        runs = os.path.join(top, "loop", "runs")
        if argv[0] == "lane-wait":
            timeout = float(argv[argv.index("--timeout") + 1]) if "--timeout" in argv else None
            return wait_for(runs, argv[1], argv[2], timeout)
        cfg = json.load(open(os.path.join(git("rev-parse", "--show-toplevel").stdout.strip(), ".loop", "config.json")))
        status, line, _ = lane(runs, argv[1], argv[2], flow_spec(), cfg)
        print(line, file=sys.stderr if status == "fail" else sys.stdout)
        return 0 if status != "fail" else 1
    print("usage: role.py lane SLUG qa|ship|pr            start or poll a goal's regression lane\n"
          "       role.py lane-wait SLUG qa|ship|pr [--timeout S]   block until the lane for HEAD ends")
    return 0 if argv in ([], ["-h"], ["--help"]) else 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
