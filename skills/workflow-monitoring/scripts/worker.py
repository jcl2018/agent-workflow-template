#!/usr/bin/env python3
"""A worker runs one goal's own loop to the end, then reports back to the operation session.

Also holds sessions.py bind (worker_line, announce, cmd_bind) and the session tool (tool, call), imported by sessions.py.

usage: worker.py <command> [options]

  loop SLUG -- COMMAND...   run the goal's agent command; when it ends, send the result back (watch.py and mend.py start this)
  report SLUG STATUS [--pr URL] [--words TEXT]
                            send a result back by hand: STATUS is merged, failed or waiting
  met SLUG N [N...]         record that done lines N are met, (kept off the live board)
  cleanup [--dry-run]       delete the loop/* branches already merged into main that no worktree has checked out
                            (git branch -d, never a remote); health.py check names this as the fix
  send SLUG TEXT            the operation session sends a worker an answer or follow-up; goal.py and flow.py print it
                            to the worker's agent the next time they run, then file it away

A report is a prompt message in the run record's `report`: {"status", "pr", "text", "at"}. The board shows it, and a
failed or waiting one stays at the top of Issues until the goal moves on. It never merges.
"""
import argparse
import datetime
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile

try:
    import fcntl
except ImportError:  # native Windows msvcrt byte-range locks under flock's names
    import msvcrt
    import time
    import types

    def _flock(handle, op):
        fd = handle if isinstance(handle, int) else handle.fileno()
        here = os.lseek(fd, 0, 1)
        os.lseek(fd, 0x7FFFFFFF, 0)  # one byte far past any content: readers never block
        try:
            while True:
                try:
                    return msvcrt.locking(fd, msvcrt.LK_UNLCK if op & 8 else msvcrt.LK_NBLCK, 1)
                except OSError:
                    if op & 8:
                        return  # unlock of a lock not held: a no-op, as with flock
                    if op & 4:
                        raise BlockingIOError("locked")
                    time.sleep(0.05)
        finally:
            os.lseek(fd, here, 0)

    fcntl = types.SimpleNamespace(LOCK_SH=1, LOCK_EX=2, LOCK_NB=4, LOCK_UN=8, flock=_flock)

# No terminal, no waiting: a prompt from git or gh must fail, not block.
os.environ.update(GIT_TERMINAL_PROMPT="0", GH_PROMPT_DISABLED="1", GIT_EDITOR="true", GIT_ASKPASS="true", SSH_ASKPASS="true")
if not sys.stdin or not sys.stdin.isatty():
    os.dup2(os.open(os.devnull, os.O_RDONLY), 0)

import proctree  # noqa: E402

TOKENS = re.compile(r"(\d[\d,]*) (?:total )?tokens", re.I)


def git(*args):
    done = subprocess.run(["git"] + list(args), capture_output=True, text=True)
    return done.stdout.strip() if done.returncode == 0 else ""


def now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def base():
    return os.path.join(os.path.abspath(git("rev-parse", "--git-common-dir")), "loop")


def path_of(slug):
    return os.path.join(base(), "runs", slug + ".json")


def load(slug):
    try:
        with open(path_of(slug)) as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return None


def save(state, note=None):
    state["updated"] = now()
    if note:
        state.setdefault("log", []).append("%s %s" % (state["updated"], note))
        print("%s %s: %s" % (state["updated"], state["slug"], note))
    temp = path_of(state["slug"]) + ".%d.tmp" % os.getpid()
    with open(temp, "w") as handle:
        json.dump(state, handle, indent=2)
    os.replace(temp, path_of(state["slug"]))


def merged(url):
    try:
        done = subprocess.run(["gh", "pr", "view", url, "--json", "state", "-q", ".state"], capture_output=True, text=True, timeout=20)
        return done.returncode == 0 and done.stdout.strip() == "MERGED"
    except (OSError, subprocess.SubprocessError):
        return False


def release_step(state):
    """The release step is part of the goal: a worker that ended with its pull request waiting, where auto_merge is on,
    gets merge.py run for it, so the goal is never left half done."""
    tree = state.get("worktree") or ""
    try:
        with open(os.path.join(tree, ".loop", "config.json")) as handle:
            auto = json.load(handle).get("auto_merge") is True
    except (OSError, ValueError):
        return
    script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "workflow-release", "scripts", "merge.py")
    if auto and state.get("status") == "done" and state.get("pr") and not merged(state["pr"]) and os.path.exists(script):
        done = subprocess.run([sys.executable, script, state["slug"]], cwd=tree, capture_output=True, text=True)
        print("release step for %s: exit %d %s" % (state["slug"], done.returncode, (done.stdout + done.stderr).strip()[-300:]))


def message(slug, status, pr, words=""):
    text = "worker %s reports %s" % (slug, status) + (" (%s)" % pr if pr else "") + (": " + words if words else "")
    return {"status": status, "pr": pr or "", "text": text, "at": now()}


def log_since(slug, mark):
    try:
        with open(os.path.join(base(), "logs", slug + ".log"), "rb") as handle:
            handle.seek(mark)
            return handle.read().decode("utf-8", "replace")
    except OSError:
        return ""


def outcome(state, text):
    """What a finished worker sends back, from its run record."""
    status, pr = state.get("status"), state.get("pr", "")
    if status == "done":
        landed = bool(pr) and merged(pr)
        return message(state["slug"], "merged" if landed else "waiting", pr, "" if landed else "its pull request waits for review and merge")
    if status == "waiting":
        ask = state.get("waiting") or {}
        return message(state["slug"], "waiting", pr, "%s Type: %s" % (ask.get("ask", ""), " or ".join(ask.get("words") or [])))
    return message(state["slug"], "failed", pr, " ".join((state.get("finding") or text[-200:] or "see its log").split()))


def cmd_loop(args):
    state = load(args.slug)
    if not state or not args.command:
        sys.exit("REFUSED: loop needs a run record and a command after --.")
    mark = os.path.getsize(os.path.join(base(), "logs", args.slug + ".log")) if os.path.exists(os.path.join(base(), "logs", args.slug + ".log")) else 0
    code = subprocess.run(args.command, env=dict(os.environ, LOOP_ROLE="worker")).returncode
    state = load(args.slug) or state
    release_step(state)
    state = load(args.slug) or state
    text = log_since(args.slug, mark)
    if state.get("status") == "running":
        state["status"], state["finding"] = "failed", state.get("finding") or "the agent ended (exit %d) without finishing: %s" % (code, " ".join(text[-200:].split()))
    found = TOKENS.findall(text)
    if found:
        state["tokens"] = dict(state.get("tokens") or {}, total=int(found[-1].replace(",", "")))
    report = outcome(state, text)  # asks gh whether the pull request merged: slow, so reread before saving
    fresh = load(args.slug) or state  # issue 159: a merge recorded from outside meanwhile is never overwritten
    if (fresh.get("report") or {}).get("status") == "merged" or fresh.get("status") in ("merged",):
        report = fresh.get("report") or report
    elif fresh.get("status") != state.get("status") and fresh.get("status") not in ("running",):
        report = outcome(fresh, text)
    fresh.update(status=state["status"] if fresh.get("status") == "running" else fresh.get("status"),
                 finding=fresh.get("finding") or state.get("finding", ""), report=report)
    if found:
        fresh["tokens"] = state["tokens"]
    save(fresh, report["text"])
    return 0


def cmd_report(args):
    state = load(args.slug)
    if not state:
        sys.exit("REFUSED: no run named %s." % args.slug)
    state["report"] = message(args.slug, args.status, args.pr or state.get("pr", ""), args.words)
    save(state, state["report"]["text"])
    return 0


def cmd_met(args):
    state = load(args.slug)
    if not state:
        sys.exit("REFUSED: no run named %s." % args.slug)
    state["met"] = sorted(set(state.get("met") or []) | set(args.lines))
    save(state, "done lines met: %s" % ", ".join(map(str, state["met"])))
    return 0


def cmd_send(args):
    if not load(args.slug):
        sys.exit("REFUSED: no run named %s." % args.slug)
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import graph  # noqa: E402
    graph.refuse(load(args.slug))
    folder = os.path.join(base(), "inbox")
    os.makedirs(folder, exist_ok=True)
    with open(os.path.join(folder, args.slug + ".txt"), "a") as handle:
        handle.write(" ".join(args.text.split()) + "\n")
    print("SENT to %s: %s" % (args.slug, " ".join(args.text.split())[:200]))
    return 0


def cmd_cleanup(args):
    top = git("rev-parse", "--show-toplevel")
    try:
        with open(os.path.join(top, ".loop", "config.json")) as handle:
            name = json.load(handle).get("base") or "main"
    except (OSError, ValueError, AttributeError):
        name = "main"
    ref = "origin/" + name if git("rev-parse", "--verify", "--quiet", "origin/" + name) else name
    gone = 0
    listed = subprocess.run(["git", "branch", "--merged", ref], capture_output=True, text=True).stdout  # git() strips the first line's indent
    for line in sorted(listed.splitlines()):
        branch = line[2:].strip()
        if line.startswith("  ") and branch.startswith("loop/"):  # "*" and "+" mark a branch checked out somewhere
            if not args.dry_run and subprocess.run(["git", "branch", "-d", branch], capture_output=True).returncode:
                print("KEPT %s: git would not delete it" % branch)
                continue
            gone += 1
            print("%s %s" % ("WOULD DELETE" if args.dry_run else "DELETED", branch))
    print("%d merged loop branch(es) %s" % (gone, "found" if args.dry_run else "deleted"))
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    item = sub.add_parser("loop")
    item.add_argument("slug")
    item.add_argument("command", nargs=argparse.REMAINDER)
    item = sub.add_parser("report")
    item.add_argument("slug")
    item.add_argument("status", choices=["merged", "failed", "waiting"])
    item.add_argument("--pr", default="")
    item.add_argument("--words", default="")
    item = sub.add_parser("met")
    item.add_argument("slug")
    item.add_argument("lines", nargs="+", type=int)
    item = sub.add_parser("cleanup")
    item.add_argument("--dry-run", action="store_true")
    item = sub.add_parser("send")
    item.add_argument("slug")
    item.add_argument("text")
    args = parser.parse_args()
    if args.cmd == "loop" and args.command[:1] == ["--"]:
        args.command = args.command[1:]
    return globals()["cmd_" + args.cmd](args)



def worker_line(slug):
    delivery = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "workflow-delivery", "scripts"))
    return "WORKER %s: run goal steps as LOOP_ROLE=worker python3 %s/goal.py ... (and flow.py, role.py lane)" % (slug, delivery)


def inside(folder, tree):
    folder, tree = os.path.realpath(folder), os.path.realpath(tree)
    return folder == tree or folder.startswith(tree + os.sep)


def announce(g, args, tree, was, worker):
    """Print the WORKER and WORKTREE lines for whoever binds to pass on (assign's message already carries them)."""
    attempt = (g.load(args.slug) or {}).get("attempt")
    lines = [worker_line(args.slug) + (" (attempt %s: pass --attempt %s to sessions.py report)" % (attempt, attempt) if attempt else "")]
    lines += ["WORKTREE %s: %s" % (args.slug, tree)] if tree else []
    if was in ("failed", "stopped") and worker:
        lines.append("NEXT: ask the operation session to resume %s (a worker binding itself only attaches)" % args.slug)
    print("\n".join(lines))
    return 0


def self_id(args):
    """`bind SLUG self`: the id of the session this runs in, from CLAUDE_CODE_HOST_SESSION_ID (issue 117); unset is a
    usage error before any work."""
    if args.id != "self":
        return
    args.id = os.environ.get("CLAUDE_CODE_HOST_SESSION_ID", "").strip()
    if not args.id:
        sys.stderr.write("REFUSED: bind %s self reads CLAUDE_CODE_HOST_SESSION_ID, which is not set here; nothing was "
                         "bound. Fix: sessions.py bind %s <ID>, with the session's id from the app (BIND_SELF_UNSET)\n"
                         % (args.slug, args.slug))
        sys.exit(2)


def cmd_bind(g, args):
    g.bad_slug(args.slug)
    self_id(args)
    name = args.name or g.name_of(args.slug)
    worker = os.environ.get("LOOP_ROLE") == "worker"
    g.graph.refuse(g.load(args.slug) or {})
    tree = (g.load(args.slug) or {}).get("worktree") or ""
    for folder in [f for f in (args.cwd, os.getcwd() if worker else "") if f and tree]:  # a worker is checked where it runs
        if not inside(folder, tree):
            sys.exit("REFUSED: session folder %s is outside the goal worktree %s. Fix: start or move the session in %s, "
                     "then bind again (CWD_OUTSIDE)" % (os.path.realpath(folder), tree, tree))
    was = None
    with g.locked():
        found, state = g.pool(), g.load(args.slug)
        if state.get("pid") and state.get("status") == "running" and g.alive(state["pid"]):
            sys.exit("REFUSED: %s is running as background pid %s; let it end first." % (args.slug, state["pid"]))
        other = found.get(args.id) or {}
        if other.get("state") == "busy" and other.get("slug") != args.slug:
            sys.exit("REFUSED: session %s is busy with goal %s." % (args.id, other.get("slug")))
        if other.get("freed_from") == args.slug and other.get("state") != "busy" and not args.force:
            sys.exit("REFUSED: session %s was freed from %s at %s. Fix: if you've confirmed no other worker has %s, run "
                     "sessions.py bind %s %s --force." % (args.id, args.slug, other.get("freed_at"), args.slug, args.slug, args.id))
        same = other.get("state") == "busy" and other.get("slug") == args.slug
        if state and same and (state.get("session") or {}).get("id") == args.id and state.get("status") in ("running", "waiting", "done"):
            print("BOUND %s to session %s (%s)" % (args.slug, args.id, other.get("name") or name))
            return announce(g, args, tree, None, worker)  # both records already agree: nothing changes, bound_at stays
        if not same:
            g.release(args.slug, found)  # a session the goal had before goes back to the pool
            found[args.id] = {"name": name, "slug": args.slug, "state": "busy", "since": g.now()}
            g.save_pool(found)
        if state:
            was = state.get("status")
            if was in ("failed", "stopped") and not worker:  # the same fields as goal.py resume (guards.revive)
                state.update(status="running", tries=0, refusals=0, finding="", waiting=None, note=None, report={})
            elif was in ("queued", "", None):
                state.update(status="running", finding="", report={})
            new = (state.get("session") or {}).get("id") != args.id or was in ("failed", "stopped")  # a new worker: next attempt
            state.update(worker="session", worker_why="", session={"id": args.id, "name": name}, pid=None, bound_at=g.now(),
                         attempt=int(state.get("attempt") or 0) + (1 if new else 0))  # an older attempt's report is not applied (114)
            state.pop("held_at", None)
            found[args.id]["attempt"] = state["attempt"]
            g.save_pool(found)
            g.save(state, "bound to session %s (%s)%s" % (args.id, name, "; revived by bind (was %s)" % was
                                                           if was in ("failed", "stopped") and not worker else ""))
    if not state:
        print("ASSIGNED %s to session %s (%s); not frozen yet. Next: in its worktree the worker runs goal.py new %s "
              "--here ..., then sessions.py bind %s %s." % (args.slug, args.id, name, args.slug, args.slug, args.id))
        return 0
    print("BOUND %s to session %s (%s)" % (args.slug, args.id, name))
    return announce(g, args, tree, was, worker)


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
            proctree.kill(child.pid)
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
            LAST_ERROR[0] = (err.read().strip().splitlines() or ["exit %d" % child.returncode])[0][:200]
    return (lines[-1].strip() if lines else "") if child.returncode == 0 else None


if __name__ == "__main__":
    sys.exit(main())
