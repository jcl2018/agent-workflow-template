#!/usr/bin/env python3
"""A goal's regression lane: start or poll it, wait for it, and check it before a step is recorded.

Imported by role.py, which re-exports lane, need_lane, lane_text, lane_argv and flow_spec. Run as
`role.py lane SLUG qa|ship|pr` (start or poll), `role.py lane-wait SLUG qa|ship|pr [--timeout S]` (block until the lane
for HEAD ends; never starts one) and `lane.py lane-exec ...` (a lane's child).
A lane tests committed HEAD and never pushes. Before it starts it may make one commit: the re-rendered Tests tables and
the run dates they come from. One lane per goal runs at a time; a lane on an older HEAD is stopped first. Its latest
result is always at <runs>/<slug>.<name>-lane.last. Exit codes and messages: lanekit.py, workflow-regression/references/commands.md.
"""
import fcntl
import json
import os
import re
import shlex
import shutil
import signal
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REG = os.path.normpath(os.path.join(HERE, "..", "..", "workflow-regression", "scripts"))
sys.path.insert(0, HERE)
import lanekit  # noqa: E402
# No terminal, no waiting: a prompt from git or gh must fail, not block (lanekit sets it too).
os.environ.update(GIT_TERMINAL_PROMPT="0", GH_PROMPT_DISABLED="1", GIT_EDITOR="true", GIT_ASKPASS="true", SSH_ASKPASS="true")
from lanekit import BOOKKEEPING, NOTHING, dirty, generated, git, prep  # noqa: E402,F401

NAMES = ("qa", "ship", "pr")
TERMINAL = ("pass", "fail")
flow_spec = lanekit._flow  # the flow file as a dict ({} when missing or bad)


def lane_argv():
    """The one lane command, resolved from this package: every prompt, run and receipt uses exactly this."""
    return ["python3", os.path.join(REG, "regression.py"), "run", "land", "--reuse", "--tier", "goal"]


def lane_text():
    return shlex.join(lane_argv())


def kill(pid):
    try:
        os.killpg(pid, signal.SIGTERM)
    except OSError:  # already gone
        pass


def drop(*paths):
    for path in paths:
        try:
            os.remove(path)
        except (FileNotFoundError, TypeError):  # another poller took it first, or no path
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


def mtime(path):
    try:
        return os.path.getmtime(path)
    except OSError:
        return None


def deadline(held):
    """The one liveness clock: the time limit runs from the started marker; queued and planning lanes get 4x the limit,
    a queued lane counted from the last slot change (a healthy backlog never times out). Old jobs keep the old rule."""
    if "markers" not in held:
        return held["started"] + held["limit"], "past its time limit of %ds" % held["limit"]
    began = mtime(held["rc"] + ".started")
    if began:
        return began + lanekit.lane_limit(held)[0], "past its time limit of %ds (%s)" % lanekit.lane_limit(held)
    if os.path.exists(held["rc"] + ".queued"):
        return max(held["started"], lanekit.last_change(held.get("pool") or lanekit.lanes_dir())) + 4 * held["limit"], \
            "queued or planning past %ds" % (4 * held["limit"])
    return held["started"] + 4 * held["limit"], "queued or planning past %ds" % (4 * held["limit"])


def live(held):
    """A lane job still ours and running: no exit status yet, inside its deadline (else the pid may be another's)."""
    return not os.path.exists(held["rc"]) and time.time() < deadline(held)[0] + 60 and alive(held["pid"])


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


def job_of(runs, slug, name):
    base = os.path.join(runs, "%s.%s-lane" % (slug, name))
    return base, read_json(base + ".job")


def stop(base, held):
    if held and live(held):
        kill(held["pid"])
    drop(base + ".job")
    if held:
        drop(*[held["rc"] + end for end in ("", ".queued", ".started", ".note", ".claimed", ".limit")])


def finalize(base, held, name):
    """Turn an ended lane into its result, once: the first caller claims the rc file under the lane's lock."""
    out, last = base + ".txt", base + ".last"
    with open(base + ".lock", "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            os.replace(held["rc"], held["rc"] + ".claimed")
        except FileNotFoundError:
            done = read_json(last) or {}
            if done.get("attempt") == held["attempt"] and done.get("state") in TERMINAL:
                return ("pass" if done["state"] == "pass" else "fail"), done.get("line", ""), done.get("ids", [])
            if os.path.exists(held["rc"] + ".claimed"):
                return "running", "RUNNING: the lane is being finished by another caller; run this same command again", []
            stop(base, held)
            return "fail", "LANE_DIED: the lane ended with no exit status (log %s); the next call starts a new lane; %s." % (out, NOTHING), []
    rc = int((open(held["rc"] + ".claimed").read().strip() or "1"))
    text = open(out).read() if os.path.exists(out) else ""
    began, now = mtime(held["rc"] + ".started"), time.time()
    notes = open(held["rc"] + ".note").read().strip() if os.path.exists(held["rc"] + ".note") else ""
    ids = re.findall(r"^(?:FAIL|UNPROVEN) ([^\s:]+)", text, re.M)
    kind = (re.findall(r"^(REUSED|AFFECTED|FULL(?: \([^)]*\))?)", text, re.M) or ["FULL"])[0]
    ran, reused = len(re.findall(r"^(?:PASS|FAIL|KNOWN) ", text, re.M)), re.findall(r"\((\d+) reused\)", text)
    took = now - (began or held["started"])
    line = "LANE %s %s %d/%d in %ds" % (name, kind, ran, ran + int((reused or [0])[0]), took)
    try:  # the repo config: goal_lane_minutes here, wiki_dir for the dirt check below
        wiki = json.load(open(os.path.join(git("rev-parse", "--show-toplevel").stdout.strip(), ".loop", "config.json")))
    except (OSError, ValueError):
        wiki = {}
    wiki = wiki if isinstance(wiki, dict) else {}
    limit = wiki.get("goal_lane_minutes") if isinstance(wiki.get("goal_lane_minutes"), (int, float)) else 10
    if not kind.startswith("FULL") and took > limit * 60:  # S21: health warns too (REG-7)
        line += "; over %g min (goal_lane_minutes)" % limit
    killed = re.findall(r"^KILLED (\S+): signal (\S+) \(pid (\d+)\)", text, re.M)  # issue 435: say what stopped a row
    if killed:
        line += "; " + ", ".join("%s killed by %s (pid %s)" % k for k in killed)
    if began and began - held["started"] >= 1:
        line += " (queued %ds)" % (began - held["started"])
    line += lanekit.rows_line(text, ran, out)
    status, made = "fail", generated(wiki)  # rendered Tests tables a row left are the next prep commit's (done line 5)
    after = [p for p in dirty() if p not in made]
    if rc == lanekit.EXIT_STALE:
        stop(base, held)
        set_last(base + ".last", held["attempt"], state="ended", rc=rc, note=notes, ended=now)
        return "running", "%s\nRUNNING: the lane restarts on the new plan; run this same command again" % notes, []
    if not began and "markers" in held and rc:
        line += "\nthe lane never reported its start (a test_record wrapper may strip _LOOP_LANE_* variables)"
    if after:
        line += "\nLANE_DIRTY at end: a row left %s. Fix: make it clean up; %s." % (", ".join(after[:10]), NOTHING)
        ids = []
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
    set_last(base + ".last", held["attempt"], state=status, rc=rc, line=line, ids=ids, note=notes, ended=now)
    stop(base, held)
    return status, line, ids


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


def lane(runs, slug, name, spec, cfg, wait=90):
    """Start or poll this goal's NAME lane (qa, ship or pr): (status, line, failing ids); status is running, pass or fail.
    It runs in the background through the flow file's optional test_record prefix and tests the committed HEAD only."""
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
    if held and not live(held) and not os.path.exists(held["rc"]) and not os.path.exists(held["rc"] + ".claimed"):
        if time.time() - held["started"] > 30:  # a claimed rc is another caller finishing it: never stale
            stop(base, held)
            held = None
    done = read_json(base + ".last") or {}
    if not held and done.get("head") == head and done.get("state") == "pass":  # lane-wait finished it: reuse, never rerun
        return "pass", done.get("line", ""), []
    if not held:
        top = git("rev-parse", "--show-toplevel").stdout.strip()
        line, refusal = prep(top, cfg, base + ".txt")
        if refusal:
            return "fail", refusal, []
        head = git("rev-parse", "HEAD").stdout.strip()
        prefix = [os.path.expanduser(part) for part in spec.get("test_record") or []]
        if prefix and not (shutil.which(prefix[0]) or os.path.isfile(prefix[0])):
            return "fail", "LANE_RECORDER: the flow file's test_record command %s isn't on this machine. Fix: install it " \
                "or remove \"test_record\" from the flow file; %s." % (prefix[0], NOTHING), []
        seconds, source = (float(spec["limit"]), "flow file limit") if spec.get("limit") else lanekit.time_limit(top)
        try:
            handle = os.open(base + ".job", os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            return "running", "RUNNING: run this same command again", []
        attempt = "%d-%d" % (os.getpid(), time.time() * 1000)
        held = {"head": head, "attempt": attempt, "started": time.time(), "limit": seconds, "source": source,
                "rc": "%s.%s.rc" % (base, attempt), "pool": lanekit.lanes_dir(), "markers": 1}
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", _LOOP_LANE_LABEL="%s/%s %s" % (os.path.basename(top), slug, name),
                   _LOOP_LANE_QUEUED=held["rc"] + ".queued", _LOOP_LANE_STARTED=held["rc"] + ".started",
                   _LOOP_LANE_NOTE=held["rc"] + ".note")
        env.pop("_LOOP_LANE_HELD", None)
        env["TMPDIR"] = base + ".tmp"  # REG-8: its own temp folder, emptied at each start
        shutil.rmtree(env["TMPDIR"], ignore_errors=True)
        os.makedirs(env["TMPDIR"])
        with open(base + ".txt", "w") as log:
            if line:
                log.write(line + "\n")
            child = subprocess.Popen([sys.executable, os.path.abspath(__file__), "lane-exec", held["rc"], str(seconds),
                                      base + ".last", attempt, held["pool"], "--"] + prefix + lane_argv(), stdout=log,
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
        return "fail", "LANE_DIED: the lane ended with no exit status (log %s); the next call starts a new lane; %s." % (
            base + ".txt", NOTHING), []
    return finalize(base, held, name)


def lane_status(runs, slug, name):
    """Status-and-finalize without spawning, killing, rendering or committing: (state, line); state is running, pass,
    fail or none (no lane for HEAD)."""
    head = git("rev-parse", "HEAD").stdout.strip()
    base, held = job_of(runs, slug, name)
    if held and held.get("head") == head:
        if live(held):
            return "running", running_line(held)
        if os.path.exists(held["rc"]) or os.path.exists(held["rc"] + ".claimed"):
            status, line, _ = finalize(base, held, name)
            return status, line
    done = read_json(base + ".last") or {}
    if done.get("head") == head and done.get("state") in TERMINAL:
        return done["state"], done.get("line", "")
    return "none", "NO LANE: none ran on %s; start one with role.py lane %s %s" % (head[:12], slug, name)


def wait_for(runs, slug, name, timeout=None):
    """role.py lane-wait: block while this HEAD's lane runs; exit 0 pass, 1 fail, 2 timeout (it keeps running), 3 none."""
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


def need_lane(runs, slug, reply, step="qa"):
    """(why, fix, code) when record qa or record ship must refuse because that step's lane hasn't passed on this HEAD,
    else None. Only a reply goal.py record counts as a failed try (its last STEP line is failed and it has no PENDING
    line) skips the check."""
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
                fix + " (reruns only the rows the change can affect; a path no row maps is left to the full suite)",
                "HEAD_MOVED")
    return None


def lane_exec(rc, seconds, last, attempt, pool, argv):
    """A lane's child: run the lane in this process's own group; enforce the deadline (time limit from the started marker,
    the queue span while queued, 4x while planning) by killing the group; write .last ended, then the exit status."""
    held = {"rc": rc, "limit": seconds, "started": time.time(), "pool": pool, "markers": 1}
    lease, port = lanekit.port_base()  # REG-8: its own ports, held while this child lives
    if lease is None:
        with open(rc + ".note", "a") as note:
            note.write("Note: %s; LOOP_LANE_PORT_BASE unset\n" % port)
    env = dict(os.environ, **({"LOOP_LANE_PORT_BASE": str(port)} if lease is not None else {}))
    child, seen = subprocess.Popen(argv, env=env), None
    try:
        while True:
            try:
                code = child.wait(timeout=1)
                break
            except subprocess.TimeoutExpired:
                pass
            state = "running" if os.path.exists(rc + ".started") else "queued" if os.path.exists(rc + ".queued") else None
            if state and state != seen:
                seen = set_last(last, attempt, state=state) and state
            if time.time() > deadline(held)[0]:
                signal.signal(signal.SIGTERM, signal.SIG_IGN)
                kill(os.getpgrp())
                try:
                    child.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    child.kill()
                code = 124
                break
    except Exception:  # an unexpected failure: a compact trace in the lane log, and a failing status
        import traceback
        print("\n".join(traceback.format_exc().splitlines()[-20:]), flush=True)
        code = 1
    set_last(last, attempt, state="ended", rc=code)
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
        return 0 if status != "fail" else 124 if "(FULL_TIMEOUT)" in line else 1
    print("usage: role.py lane SLUG qa|ship|pr            start or poll a goal's regression lane\n"
          "       role.py lane-wait SLUG qa|ship|pr [--timeout S]   block until the lane for HEAD ends")
    return 0 if argv in ([], ["-h"], ["--help"]) else 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
