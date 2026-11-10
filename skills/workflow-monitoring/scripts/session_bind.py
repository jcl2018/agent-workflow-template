#!/usr/bin/env python3
"""sessions.py bind, moved here for room: record a session the app started for a goal, hand it the worker command and
the goal worktree, and refuse a session folder outside that worktree. Imported by sessions.py; not run.

  WORKER <slug>: ...    the command form for goal steps (LOOP_ROLE=worker); no process can set another's environment
  WORKTREE <slug>: ...  the folder to work in; --cwd DIR, or a worker binding itself, outside it is CWD_OUTSIDE
A failed or stopped goal is revived with the same fields as goal.py resume; a worker binding itself only attaches.
"""
import os
import sys



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


def cmd_bind(g, args):
    g.bad_slug(args.slug)
    name = args.name or g.name_of(args.slug)
    worker = os.environ.get("LOOP_ROLE") == "worker"
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
                state.update(status="running", tries=0, refusals=0, finding="", waiting=None, note=None, report=None)
            elif was in ("queued", "", None):
                state.update(status="running", finding="", report=None)
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
