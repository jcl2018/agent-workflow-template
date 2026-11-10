#!/usr/bin/env python3
"""Worker sessions: each goal runs in its own app session, named "worker · <goal>", and reports by session message.

usage: sessions.py <command> [options]

  assign SLUG               give a frozen goal to a worker session (watch.py does this for every goal it starts)
  bind SLUG ID [--name N] [--cwd DIR]  record a session started with the app's own tools; prints the WORKER command
                            form and the WORKTREE to work in, and refuses a session folder (--cwd, or a worker binding
                            itself from its own folder) outside the goal worktree. It revives a failed or stopped goal
                            (a worker binding itself only attaches).
  reserve SLUG ID [--undo]  take a free session for a goal under the pool lock (goal.py resume uses it)
  report SLUG [--step S] [--status running|waiting|merged|failed] [--pr URL] [--ask Q --words W...] [--text T]
                            record a worker's session message: each step change, and its result when the goal ends.
                            merged is checked with gh; waiting with --ask is a question for the owner, without it the
                            goal ended with its pull request waiting. A goal that ended frees its session.
  send SLUG TEXT            send a worker session the owner's answer or a follow-up (operate.py send does this)
  list                      the sessions this repo knows, with their goals

A session tool does the talking: the command in `session_command` (.loop/config.json) or $LOOP_SESSION_TOOL, called as
`TOOL start NAME` (prints the new session's id), `TOOL rename ID NAME` and `TOOL send ID TEXT`. With no tool, or one
that fails or passes its timeout (LOOP_SESSION_TIMEOUT, 30 s), the goal falls back to a background process and the board says "background".
The pool lives in <git common dir>/loop/session-pool.json. Where auto_merge is on, a goal that ends with its pull
request open gets the release step run for it, as worker.py does for a background goal. Nothing else here merges.
"""
import argparse
import contextlib
import datetime
import fcntl
import json
import os
import re
import shlex
import signal
import subprocess
import sys
import tempfile

# No terminal, no waiting: a prompt from git or gh must fail, not block.
os.environ.update(GIT_TERMINAL_PROMPT="0", GH_PROMPT_DISABLED="1", GIT_EDITOR="true", GIT_ASKPASS="true", SSH_ASKPASS="true")
if not sys.stdin or not sys.stdin.isatty():
    os.dup2(os.open(os.devnull, os.O_RDONLY), 0)

SLUG = re.compile(r"^[a-z0-9][a-z0-9-]{0,50}$")
SEND = ("You are the worker session for goal {slug}; this replaces any goal you had before. Work only in its worktree: "
        "cd {tree} first, and run every goal.py and flow.py command there with LOOP_ROLE=worker set. Run every flow step "
        "inside this session: flow.py prints IN SESSION and the skill to invoke; run it yourself with the recommended "
        "answer at every question, never push from ship, and record each step with goal.py record. Send the operation "
        "session{to} a session message at each change of step or status, and your result when the goal ends (merged, "
        "failed or waiting, with the pull request).\n\n")
FREE_TRIES = 2  # free sessions tried before a new one: each try can take a minute when the tool hangs


def git(*args):
    done = subprocess.run(["git", *args], capture_output=True, text=True)
    return done.stdout.strip() if done.returncode == 0 else ""


def now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def base():
    return os.path.join(os.path.abspath(git("rev-parse", "--git-common-dir") or ".git"), "loop")


def read(path, empty):
    try:
        with open(path) as handle:
            found = json.load(handle)
        return found if isinstance(found, type(empty)) else empty
    except (OSError, ValueError):
        return empty


def write(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    temp = path + ".%d.tmp" % os.getpid()
    with open(temp, "w") as handle:
        json.dump(data, handle, indent=2)
    os.replace(temp, path)


@contextlib.contextmanager
def locked():
    """Every read-modify-write of the pool holds this lock, so two commands can't take the same free session."""
    os.makedirs(base(), exist_ok=True)
    with open(os.path.join(base(), "session-pool.lock"), "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        yield


def pool():
    return read(os.path.join(base(), "session-pool.json"), {})


def save_pool(found):
    write(os.path.join(base(), "session-pool.json"), found)


def load(slug):
    return read(os.path.join(base(), "runs", slug + ".json"), {}) if SLUG.match(slug or "") else {}


def save(state, note):
    state["updated"] = now()
    state.setdefault("log", []).append("%s %s" % (state["updated"], note))
    write(os.path.join(base(), "runs", state["slug"] + ".json"), state)
    print("%s %s: %s" % (state["updated"], state["slug"], note))


def name_of(slug):
    return "worker · " + slug


def release(slug, found=None):
    """Free every session the pool holds for this goal. A caller holding the pool lock passes its pool in and saves it;
    with none, this takes the lock, reads, frees and saves itself (mend.py and report call it that way)."""
    if found is None:
        with locked():
            held = release(slug, pool())
            save_pool(held)
        return held
    for item in found.values():
        if item.get("slug") == slug and item.get("state") == "busy":
            item["state"] = "free"
    return found


def tool(cfg):
    if os.environ.get("LOOP_SESSION_TOOL"):
        return shlex.split(os.environ["LOOP_SESSION_TOOL"])
    found = cfg.get("session_command")
    return [os.path.expanduser(str(part)) for part in found] if isinstance(found, list) and found else []


HUNG = []  # set when a call times out: the tool is given up for the rest of this run
LAST_ERROR = [""]  # the last call's failure: the tool's first stderr line, "cannot start", or "timed out"


def timeout():
    try:
        return max(1.0, float(os.environ.get("LOOP_SESSION_TIMEOUT") or 30))
    except ValueError:
        return 30.0


def call(command, *args):
    """One session tool call: its last output line, or None when it can't start or reach a session. A call past the
    timeout (LOOP_SESSION_TIMEOUT, default 30 s) is killed with its process group, then the tool is given up for the
    run (watch.py clears that each round). Output goes to a file, so a helper the tool leaves running can't hold it."""
    LAST_ERROR[0] = ""
    if HUNG:
        LAST_ERROR[0] = "the session tool timed out earlier in this run"
        return None
    with tempfile.TemporaryFile("w+") as out, tempfile.TemporaryFile("w+") as err:
        try:
            child = subprocess.Popen(command + list(args), stdout=out, stderr=err,
                                     stdin=subprocess.DEVNULL, start_new_session=True)
        except OSError as error:
            LAST_ERROR[0] = "cannot start %s: %s" % (command[0], error.strerror or error)
            return None
        try:
            child.wait(timeout=timeout())
        except BaseException as error:  # a timeout, or an interrupt: never leave the tool running
            try:
                os.killpg(child.pid, signal.SIGKILL)
            except OSError:
                pass
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                pass
            if not isinstance(error, subprocess.TimeoutExpired):
                raise
            HUNG.append(" ".join(args[:1]))
            LAST_ERROR[0] = "timed out after %d s" % timeout()
            return None
        out.seek(0)
        lines = out.read().strip().splitlines()
        if child.returncode:
            err.seek(0)
            first = (err.read().strip().splitlines() or ["exit %d" % child.returncode])[0]
            LAST_ERROR[0] = first[:200]
    return (lines[-1].strip() if lines else "") if child.returncode == 0 else None


def assign(state, prompt, cfg):
    """Give the goal to a free session, or a new one; rename it, send it the goal. False means: start a background process.
    A send that fails may still have arrived; the board names the fallback and its reason, so a second worker shows."""
    command, slug = tool(cfg), state["slug"]
    state["worker"], state["worker_why"] = "background", "no session tool is set (session_command)"
    if not command:
        return False
    with locked():
        return assign_locked(state, prompt, command, slug)


def assign_locked(state, prompt, command, slug):
    found, to = pool(), os.environ.get("LOOP_OPERATION_SESSION", "")
    text = SEND.format(slug=slug, tree=state.get("worktree") or "its worktree", to=" (%s)" % to if to else "") + worker_line(slug) + "\n\n" + prompt
    free = sorted(s for s, item in found.items() if item.get("state") == "free")[:FREE_TRIES]
    sid, reused = None, False
    for sid in free + [None]:  # free ones first, then a new one
        reused = sid is not None
        sid = sid or call(command, "start", name_of(slug))
        if not sid:
            state["worker_why"] = "the session tool timed out" if HUNG else "the session tool could not start a session"
            break
        if call(command, "rename", sid, name_of(slug)) is not None and call(command, "send", sid, text) is not None:
            break
        state["worker_why"] = ("the session tool timed out on session %s" if HUNG else "the session tool could not reach session %s") % sid
        found.setdefault(sid, {"name": name_of(slug), "slug": slug})["state"] = "unreachable"
        save_pool(found)
        sid = None
        if HUNG:
            break
    if not sid:
        return False
    found[sid] = {"name": name_of(slug), "slug": slug, "state": "busy", "since": now()}
    save_pool(found)
    state.update(worker="session", worker_why="", session={"id": sid, "name": name_of(slug)}, pid=None, status="running")
    save(state, "assigned to session %s (%s)%s" % (sid, name_of(slug), ", reused" if reused else ""))
    return True


def config():
    return read(os.path.join(git("rev-parse", "--show-toplevel"), ".loop", "config.json"), {})


def held(slug):
    state = load(slug)
    if not state:
        sys.exit("REFUSED: no run named %s." % slug)
    return state


def cmd_assign(args):
    state = held(args.slug)
    if not assign(state, args.text, config()):
        print("BACKGROUND %s: %s" % (args.slug, state["worker_why"]))
        return 1
    return 0


def worker_line(slug):
    delivery = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "workflow-delivery", "scripts"))
    return "WORKER %s: run goal steps as LOOP_ROLE=worker python3 %s/goal.py ... (and flow.py, role.py lane)" % (slug, delivery)


def inside(folder, tree):
    folder, tree = os.path.realpath(folder), os.path.realpath(tree or "/nonexistent")
    return folder == tree or folder.startswith(tree + os.sep)


def cmd_bind(args):
    state = held(args.slug)
    worker = os.environ.get("LOOP_ROLE") == "worker"
    if state.get("pid") and state.get("status") == "running":
        sys.exit("REFUSED: %s is running as background pid %s; let it end first." % (args.slug, state["pid"]))
    tree = state.get("worktree") or ""
    for folder in [f for f in (args.cwd, os.getcwd() if worker else "") if f]:  # a worker is checked where it runs too
        if inside(folder, tree):
            continue
        sys.exit("REFUSED: session folder %s is outside the goal worktree %s. Fix: start or move the session in %s, then "
                 "bind again (CWD_OUTSIDE)" % (folder, tree, tree))
    with locked():
        found = pool()
        other = found.get(args.id) or {}
        if other.get("state") == "busy" and other.get("slug") != args.slug:
            sys.exit("REFUSED: session %s is busy with goal %s." % (args.id, other.get("slug")))
        name = args.name or name_of(args.slug)
        release(args.slug, found)  # a session the goal had before goes back to the pool
        found[args.id] = {"name": name, "slug": args.slug, "state": "busy", "since": now()}
        save_pool(found)
    was, note = state.get("status"), "bound to session %s (%s)" % (args.id, name)
    if was in ("failed", "stopped") and not worker:  # the same fields as guards.revive (goal.py resume)
        state.update(status="running", tries=0, refusals=0, finding="", waiting=None, note=None, report=None)
        note += "; revived by bind (was %s)" % was
    elif was in ("queued", "", None):
        state.update(status="running", finding="", report=None)
    state.update(worker="session", worker_why="", session={"id": args.id, "name": name}, pid=None)
    save(state, note)
    lines = [worker_line(args.slug), "WORKTREE %s: %s" % (args.slug, tree)]
    if was in ("failed", "stopped") and worker:
        lines.append("NEXT: ask the operation session to resume %s (a worker binding itself only attaches)" % args.slug)
    print("\n".join(lines))
    command = tool(config())
    if command and call(command, "send", args.id, " ".join(lines[:2])) is None:
        print("NOTE: the session didn't get these lines (%s); tell it yourself" % LAST_ERROR[0])
    return 0


def cmd_reserve(args):
    """Take session ID for SLUG when it is free or already this goal's; --undo gives it back."""
    with locked():
        found = pool()
        item = found.get(args.id) or {}
        if args.undo:  # put back exactly what reserve found
            if item.get("slug") == args.slug and "prior" in item:
                found[args.id] = item.pop("prior") or {}
                if not found[args.id]:
                    del found[args.id]
                save_pool(found)
            return 0
        if item.get("state") == "busy" and item.get("slug") != args.slug:
            sys.exit("REFUSED: session %s now serves goal %s. Fix: sessions.py bind %s ID with a free session (SESSION_TAKEN)" % (
                args.id, item.get("slug"), args.slug))
        prior = {k: v for k, v in item.items() if k != "prior"}
        found[args.id] = dict(prior, name=item.get("name") or name_of(args.slug), slug=args.slug, state="busy", since=now(), prior=prior)
        save_pool(found)
    print("RESERVED session %s for %s" % (args.id, args.slug))
    return 0


def merged(url):
    try:
        done = subprocess.run(["gh", "pr", "view", url, "--json", "state", "-q", ".state"], capture_output=True, text=True, timeout=20)
        return done.returncode == 0 and done.stdout.strip() == "MERGED"
    except (OSError, subprocess.SubprocessError):
        return False


def release_step(state):
    """Where auto_merge is on, a goal that ended with its pull request open gets merge.py, as worker.py does."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    try:
        import worker
    except ImportError:
        return
    worker.release_step(state)


def cmd_report(args):
    state = held(args.slug)
    if args.step:
        state["step"] = args.step
    if args.pr:
        state["pr"] = args.pr
    pr, said = state.get("pr", ""), args.status
    ended = said in ("merged", "failed") or (said == "waiting" and not args.ask)
    if said == "waiting" and args.ask:  # a question for the owner: the goal stops until it is answered
        state.update(status="waiting", waiting={"ask": args.ask, "words": args.words or ["go on " + args.slug]})
    elif said == "failed":
        state.update(status="failed", finding=args.text or state.get("finding") or "the worker session reported failed")
    elif said in ("merged", "waiting"):  # the goal ended with a pull request: done, merged or waiting for review
        if not pr:
            sys.exit("REFUSED: %s with no pull request. Fix: pass --pr URL." % said)
        state["status"] = "done"
        if config().get("auto_merge") is True and not merged(pr):
            release_step(state)
            state = load(args.slug) or state
        said = "merged" if merged(pr) else "waiting"
    elif said == "running":
        state["status"] = "running"
    who = (state.get("session") or {}).get("name") or args.slug
    text = args.text or "%s: step %s, %s" % (who, state.get("step") or "-", said or state.get("status"))
    if said == "waiting" and not args.ask:
        text = args.text or "%s reports waiting (%s): its pull request waits for review and merge" % (who, pr)
    state.setdefault("reports", []).append({"at": now(), "step": state.get("step") or "-", "status": said or state.get("status"), "text": text})
    del state["reports"][:-30]
    if said in ("merged", "failed", "waiting"):
        state["report"] = {"status": said, "pr": pr, "text": text, "at": now()}
    if ended:
        release(args.slug)
    save(state, "session report: " + text)
    return 0


def cmd_send(args):
    """Send the owner's answer or a follow-up to the goal's worker session; 1 when it has none or can't be reached."""
    state = held(args.slug)
    sid, command = (state.get("session") or {}).get("id"), tool(config())
    if state.get("worker") != "session" or not sid or not command:
        print("NO SESSION for %s: the inbox carries it" % args.slug)
        return 1
    if call(command, "send", sid, " ".join(args.text.split())) is None:
        print("UNREACHED session %s for %s: the inbox carries it (%s)" % (sid, args.slug, LAST_ERROR[0]))
        return 1
    print("SENT to session %s (%s)" % (sid, (state.get("session") or {}).get("name")))
    return 0


def cmd_list(args):
    for sid, item in sorted(pool().items()):
        print("%s  %s  %s  %s" % (sid, item.get("state"), item.get("name"), item.get("slug")))
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    item = sub.add_parser("assign")
    item.add_argument("slug")
    item.add_argument("--text", default="")
    item = sub.add_parser("bind")
    item.add_argument("slug")
    item.add_argument("id")
    item.add_argument("--name", default="")
    item.add_argument("--cwd", default="")
    item = sub.add_parser("reserve")
    item.add_argument("slug")
    item.add_argument("id")
    item.add_argument("--undo", action="store_true")
    item = sub.add_parser("report")
    item.add_argument("slug")
    item.add_argument("--status", default="", choices=["", "running", "waiting", "merged", "failed"])
    for flag in ("--step", "--pr", "--text", "--ask"):
        item.add_argument(flag, default="")
    item.add_argument("--words", action="append", default=[])
    item = sub.add_parser("send")
    item.add_argument("slug")
    item.add_argument("text")
    sub.add_parser("list")
    args = parser.parse_args()
    return globals()["cmd_" + args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
