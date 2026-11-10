#!/usr/bin/env python3
"""Operation commands on a goal that live outside goal.py (which stays under 20 KB): `set` (the owner's per-goal depth,
bump and budget) and `queue`. Imported by goal.py; each takes goal.py's module as g.

`set` is operation-only, like `touches` and `resume`: it refuses LOOP_ROLE=worker, so nothing a worker runs can lower
a goal's depth or raise its budget. Its values go to the operation sidecar under its lock (guards.add_set), never to the
run record, which a worker's save rewrites.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fit  # noqa: E402
import guards  # noqa: E402
import prbody  # noqa: E402
import private  # noqa: E402
import role  # noqa: E402

SET_AFTER_RECORD = "SET_AFTER_RECORD"


def cmd_set(g, args):
    guards.operation_only(g, "set", args.slug)
    state = g.load(args.slug)
    if not (args.depth or args.bump or args.budget_minutes is not None or args.budget_tokens is not None):
        g.no("nothing to set. Fix: give --depth, --bump, --budget-minutes or --budget-tokens")
    why = " ".join(args.why.split())
    if args.depth and any(fit.recorded(state, s) for s in ("plan", "review")):
        done = [s for s in ("review", "plan") if fit.recorded(state, s)][-1]
        g.no("%s is already recorded, so a new depth wouldn't bind it; nothing changed. Fix: goal.py set first, then "
             "flow.py %s %s --again (%s)" % (done, args.slug, done, SET_AFTER_RECORD))
    if args.bump and state.get("release") in ("cut", "merged"):
        g.no("%s's release has started; nothing changed (%s)" % (args.slug, SET_AFTER_RECORD))
    runs = g.state_dir()
    if args.depth:
        guards.add_set(runs, args.slug, "depth_override", {"depth": args.depth, "why": why}, "set depth %s: %s" % (args.depth, why))
    if args.bump:
        guards.add_set(runs, args.slug, "bump", args.bump, "set bump %s: %s" % (args.bump, why))
    if args.budget_minutes is not None or args.budget_tokens is not None:
        held, _ = fit.budget(fit.view(state, runs), g.config())
        if args.budget_minutes is not None:
            held["minutes"] = max(0, args.budget_minutes)
        if args.budget_tokens is not None:
            held["tokens"] = max(0, args.budget_tokens)
        guards.add_set(runs, args.slug, "budget", held, "set budget %dm, %d tokens: %s" % (held["minutes"], held["tokens"], why))
    print("SET %s: %s" % (args.slug, ", ".join(
        "%s=%s" % (k, v) for k, v in fit.sidecar(runs, args.slug).items())))
    return 0


def cmd_queue(g, args):
    g.valid(args)
    if any("|" in text for text in [args.goal, args.touches] + args.done):
        g.no("no | in a queue line.")
    path = os.path.join(g.root(), ".loop", "queue.md")
    held = g.read(path) if os.path.exists(path) else ""
    if os.path.exists(g.state_path(args.slug)) or "- slug: %s |" % args.slug in held:
        g.no("%s already exists. Fix: pick a new slug." % args.slug)
    parts = ["slug: " + args.slug]
    if args.touches:
        parts.append("touches: " + args.touches)
    if args.depends_on:
        parts.append("depends-on: " + args.depends_on)
    parts.append("goal: " + " ".join(args.goal.split()))
    parts += ["done: " + " ".join(line.split()) for line in args.done]
    g.write(path, ("" if held.endswith("\n") or not held else "\n") + "- " + " | ".join(parts) + "\n", "a")
    print("QUEUED %s in .loop/queue.md" % args.slug)
    return 0


def frozen_fields(g, args, lines, touches):
    """What `new` records beside the done lines: the goal's size and the budget it carries (0 = none set)."""
    bad = [t for t in touches if fit.surface(t) is None]
    if bad:
        g.no("%s isn't a GitHub surface. Fix: one of github:%s" % (", ".join(bad), ", github:".join(fit.SURFACES)))
    if fit.says_bump(args.goal):
        print("WARN: the goal text says %s; the operation records it with goal.py set %s --bump %s --why ..." % (
            fit.says_bump(args.goal), args.slug, fit.says_bump(args.goal)))
    return {"size": fit.size_of(lines, touches, g.root()), "budget": fit.budget_of(g.config())}


def pr_text(g, state):
    """The pull request body, after the private-name scan of the branch, the title and the body (DEL-9): a hit or a
    broken list refuses with no try, before anything is pushed."""
    base, cfg = g.base_ref(state), g.config()
    body = prbody.pr_body(g.read(g.goal_file(state["slug"])), fit.view(state, g.state_dir()), cfg, role.setting_of(cfg),
                          "", prbody.regen_warnings(g.root(), base))
    found = private.scan(g.root(), base, {"pr-title": state["goal"][:70], "pr-body": body})
    stop = private.refusal(found, base)
    if stop:
        guards.refuse_no_try(state, stop[0], stop[1], stop[2], g.save)
    if found["state"] == "none":
        state.setdefault("log", []).append("%s %s" % (guards.now(), found["note"]))
    return body.replace("\n## Result\n", "\n## Result\n\n" + found["note"] + "\n", 1)
