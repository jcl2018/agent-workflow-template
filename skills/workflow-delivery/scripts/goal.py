#!/usr/bin/env python3
"""Hold one goal's record: done lines, the skill flow's steps, PR.

usage: goal.py <command> <slug> [options]

  new SLUG --here --goal TEXT --done LINE [--touches A,B] [--release R]
  queue SLUG --goal TEXT --done LINE [--touches A,B] [--depends-on A,B]
  step SLUG NAME [--note TEXT] [--tokens N]
  record SLUG STEP --file REPLY [--in-session] [--tokens N|unknown]
  pr SLUG  merge the latest base, push, open the PR
Goal steps (step, record, pr) refuse outside a worker.
  wait SLUG --ask TEXT --words W [--words W]
  answer SLUG                 a waiting goal goes on
  finding SLUG TEXT   stops a live goal; a done or merged one is only noted
  resume SLUG --why T [--by W]    the operation revives a stopped session goal
  touches SLUG --add PATH --why T the operation widens a goal's touches
  set SLUG [--depth D] [--bump B] [--budget-minutes N] [--budget-tokens N] --why T
  show SLUG
A refusal that changes nothing uses no try (exit 2, guards.py).
"""
import argparse
import datetime
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lanekit, guards, fit, private  # noqa: E402,E401
fcntl = lanekit.fcntl
import role


try:  # pods (MON-15): workflow-monitoring's graph.py, loaded by path
    _spec = importlib.util.spec_from_file_location("pods_graph", os.path.join(os.path.dirname(__file__), "..", "..", "workflow-monitoring", "scripts", "graph.py"))
    pods = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(pods)
except Exception:
    pods = None

# A git or gh prompt must fail, not block.
os.environ.update(GIT_TERMINAL_PROMPT="0", GH_PROMPT_DISABLED="1", GIT_EDITOR="true", GIT_ASKPASS="true", SSH_ASKPASS="true")
if not sys.stdin or not sys.stdin.isatty():
    os.dup2(os.open(os.devnull, os.O_RDONLY), 0)

FLOW = ("idea", "plan", "review", "qa", "ship")
FLOW_FILE = "~/.workflow-loop/flow.json"
NO_FLOW = ("no skill flow is set. Fix: write %s naming your idea, plan, review, test and ship skills and the "
           "command that runs them unattended (see loop-files.md)." % FLOW_FILE)


MAX_TRIES = 3
SLUG = re.compile(r"^[a-z0-9][a-z0-9-]{0,50}$")


def no(text):
    sys.exit("REFUSED: " + text)


def run(args, cwd=None, check=False):
    done = subprocess.run(args, cwd=cwd, capture_output=True, text=True)
    if check and done.returncode:
        no("%s: %s" % (" ".join(args), done.stderr.strip()))
    return done


def git(*args, check=True):
    return run(["git"] + list(args), check=check).stdout.strip()


def read(path):
    with open(path) as handle:
        return handle.read()


def write(path, text, mode="w"):
    with open(path, mode) as handle:
        handle.write(text)


def now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def state_dir():
    common = os.path.abspath(git("rev-parse", "--git-common-dir"))
    path = os.path.join(common, "loop", "runs")
    os.makedirs(path, exist_ok=True)
    return path


def state_path(slug):
    return os.path.join(state_dir(), slug + ".json")


SEEN = {}  # slug -> last record


def load(slug):
    try:
        state = json.loads(read(state_path(slug)))
    except OSError:
        no("no goal named %s. Fix: start it with new." % slug)
    SEEN[slug] = json.dumps(state)
    return state


def save(state, note=None):
    """Locked save: only keys changed here win."""
    state["updated"] = now()
    if note:
        state.setdefault("log", []).append("%s %s" % (state["updated"], note))
    path, slug = state_path(state["slug"]), state["slug"]
    with open(path + ".lock", "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            disk = json.loads(read(path))
        except (OSError, ValueError):
            disk = {}
        was = json.loads(SEEN.get(slug, "{}"))
        merged = dict(disk, **{k: v for k, v in state.items() if k not in was or was[k] != v})
        merged = {k: v for k, v in merged.items() if k in state or k not in was}
        have = disk.get("log") or []
        merged["log"] = have + [line for line in state.get("log") or [] if line not in have]
        role.report(disk, merged, state["updated"])
        temp = path + ".%d.tmp" % os.getpid()
        write(temp, json.dumps(merged, indent=2))
        os.replace(temp, path)
    state.clear()
    state.update(merged)
    SEEN[slug] = json.dumps(merged)


def root():
    return git("rev-parse", "--show-toplevel")


def config():
    path = os.path.join(root(), ".loop", "config.json")
    try:
        return json.loads(read(path))
    except (OSError, ValueError):
        no("no readable .loop/config.json. Fix: run workflow-setup and merge its branch.")


def goal_file(slug):
    return os.path.join(root(), ".loop", "goals", slug + ".md")


def done_lines(slug):
    try:
        text = read(goal_file(slug))
    except OSError:
        no("no goal file for %s here. Fix: run this from the goal's worktree." % slug)
    part = text.split("## Done lines", 1)[-1].split("\n## ", 1)[0]
    return [line.strip() for line in part.splitlines() if re.match(r"\s*\d+\. ", line)]


def done_sha(lines):
    return hashlib.sha256("\n".join(lines).encode()).hexdigest()


def frozen(state):
    if done_sha(done_lines(state["slug"])) != state["done_sha"]:
        fail_stop(state, "The done lines changed after they were frozen. A wrong done line needs a new goal.")


def held(slug):
    state = load(slug)
    frozen(state)
    return state


def base_ref(state):
    base = config()["base"]
    if run(["git", "rev-parse", "--verify", "--quiet", "origin/" + base]).returncode == 0:
        return "origin/" + base
    return base


def fail_stop(state, text):
    guards.fail_stop(sys.modules[__name__], state, text)


def failed_try(state, why, step="build", fix="fix it, then run the step again"):
    guards.failed_try(sys.modules[__name__], state, why, step, fix)


def cmd_wait(args):
    return guards.cmd_wait(sys.modules[__name__], args)


def cmd_answer(args):
    return guards.cmd_answer(sys.modules[__name__], args)


def flow_set():
    """The private flow file names a skill for every step."""
    try:
        spec = json.loads(read(os.path.expanduser(os.environ.get("LOOP_FLOW") or FLOW_FILE)))
        steps = dict(spec.get("suite") or {}, **(spec.get("steps") or {}))
    except (OSError, ValueError, AttributeError, TypeError):
        return False
    return all(steps.get(step) for step in FLOW)


def valid(args):
    if not SLUG.match(args.slug):
        no("bad slug. Fix: lowercase letters, digits and dashes.")
    if not args.done:
        no("no done lines. Fix: give at least one --done.")
    if not flow_set():
        no(NO_FLOW)


def cmd_new(args):
    if not args.here:
        no("one session governs. Fix: use workflow-monitoring go, or --here if no agent can run it.")
    valid(args)
    fit.main_here(sys.modules[__name__], args)
    if os.path.exists(state_path(args.slug)):
        no("%s already exists. Fix: pick a new slug." % args.slug)
    cfg = config()
    fit.nag(sys.modules[__name__], args)
    touches = [item.strip() for item in args.touches.split(",") if item.strip()]
    branch = "loop/" + args.slug
    current = git("branch", "--show-current")
    if current == cfg["base"]:
        git("switch", "-c", branch)
    elif current != branch:
        no("on branch %s. Fix: go to %s or %s first." % (current, cfg["base"], branch))
    lines = ["%d. %s" % (index, " ".join(line.split())) for index, line in enumerate(args.done, 1)]
    fields = fit.frozen_fields(sys.modules[__name__], args, lines, touches)
    path = goal_file(args.slug)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    write(path, fit.TEMPLATE.format(goal=" ".join(args.goal.split()), slug=args.slug,
                                touches=", ".join(touches) or "not declared", done="\n".join(lines)))
    git("add", path)
    git("commit", "-m", "Goal: %s" % args.slug, "--", path)
    state = {"slug": args.slug, "goal": args.goal, "status": "running", "step": "idea", "tries": 0, "flow": {},
             "branch": branch, "worktree": root(), "touches": touches, "pid": None, "pr": "",
             "batch": bool(os.environ.get("LOOP_BATCH")), "done_sha": done_sha(lines),
             "release": args.release, "waiting": None, "finding": "", "log": []}
    state.update(fields)
    guards.stamp(state, "idea")
    pods and pods.stamp(state)
    save(state, "frozen %d done lines" % len(lines))
    print("FROZEN %s branch=%s step=idea" % (args.slug, branch))
    return 0


def cmd_adopt(args):
    return fit.cmd_adopt(sys.modules[__name__], args)


def cmd_queue(args):
    return fit.cmd_queue(sys.modules[__name__], args)


def cmd_set(args):
    return fit.cmd_set(sys.modules[__name__], args)


def cmd_step(args):
    state = load(args.slug)
    fit.budget_stop(args.slug, state, state_dir(), config())
    state["step"] = args.name
    if args.tokens:
        state["tokens"] = dict(state.get("tokens") or {}, **{args.name: args.tokens})
    save(state, args.name + (": " + args.note if args.note else ""))
    print("STEP %s %s" % (args.slug, args.name))
    return 0


def next_step(state):
    left = [step for step in FLOW if step not in state.get("flow", {})]
    return "flow.py %s %s" % (state["slug"], left[0]) if left else "pr"


def cmd_record(args):
    """Apply a flow step's result."""
    state = held(args.slug)
    guards.waiting_gate(sys.modules[__name__], state)
    fit.add_tokens(state, args.step, args.tokens)
    ran = os.path.join(state_dir(), "%s.%s.ran" % (args.slug, args.step))
    if args.in_session:  # the session ran it
        args.file = role.session_reply(state, args.slug, args.step, args.file, state_dir(), FLOW)
    lane = role.need_lane(state_dir(), args.slug, args.file, args.step) if args.step in ("qa", "ship") else None
    if lane:
        guards.refuse_no_try(state, *lane, save)
    reply = os.path.realpath(args.file)
    if reply != os.path.realpath(os.path.join(state_dir(), "%s.%s.txt" % (args.slug, args.step))) or not os.path.exists(ran):
        guards.refuse_no_try(state, "%s wasn't run by flow.py" % args.step, "run flow.py %s %s until it prints NEXT" % (
            args.slug, args.step), guards.NOT_RUN_BY_FLOW, save)
    text = read(reply)
    found = re.findall(r"^\W*STEP:\s*(done|skipped|pending|failed)\b[ :.-]*(.*)$", text, re.M | re.I)
    result, why = (found[-1][0].lower(), found[-1][1].strip()) if found else ("", "")
    pending = guards.pending_items(text)
    session = args.in_session or state.get("worker") == "session"
    if not result and not pending and session:  # flow.py's session route
        guards.refuse_no_try(state, "the %s reply has no STEP line" % args.step, "end the reply with the DEPTH line and a "
                             "STEP: done|skipped|pending|failed line, then record again", guards.NO_STEP_LINE, save)
    stamp, cfg = "", config()
    if result in ("done", "skipped") or ((pending or result == "pending") and cfg.get("auto_approve") is True):
        stamp, refusal, ask, skipped = guards.check_record(state, args.step, text, cfg, result)
        for line in skipped:
            state.setdefault("log", []).append("%s rule %s" % (now(), line))
        if ask:
            state["status"], state["waiting"] = "waiting", {"ask": ask[:600], "words": ["go on " + args.slug, "stop " + args.slug]}
            save(state, "%s waits for the owner (no try used): %s" % (args.step, ask[:200]))
            print("WAITING %s (no try used): %s" % (args.slug, ask))
            return 0
        if refusal:
            guards.refuse_no_try(state, refusal[0], refusal[1], refusal[2], save)
    os.remove(ran)
    if result in ("done", "skipped") or pending or result == "pending":
        guards.clear_refusals(state)
    if result in ("done", "skipped") or ((pending or result == "pending") and cfg.get("auto_approve") is True):
        fit.keep(sys.modules[__name__], state, args.step, text)
    if (pending or result == "pending") and cfg.get("auto_approve") is True:
        took = "; ".join(pending) or why or "the step's pending gate"
        state["flow"][args.step] = "done: auto-approved: " + took[:200] + stamp
        state["step"] = role.after(args.step)
        state["note"] = {"text": "auto-approved at %s: %s" % (args.step, took[:240]), "at": now()}
        guards.advance(sys.modules[__name__], state)
        save(state, "%s auto-approved: %s" % (args.step, took[:300]))
        print("AUTO-APPROVED %s %s: %s" % (args.slug, args.step, took))
        print("NEXT: " + ("build, then " if args.step == "plan" else "") + next_step(state))
        return 0
    if pending or result == "pending":
        state["flow"][args.step] = "pending"
        ask = "%s left this for you: %s" % (args.step, "; ".join(pending) or why or "see its reply")
        state["status"], state["waiting"] = "waiting", {"ask": ask[:600], "words": ["go on " + args.slug,
                                                                                     "stop " + args.slug]}
        save(state, "%s pending: %s" % (args.step, ask[:200]))
        print("WAITING %s: %s" % (args.slug, ask))
        return 0
    if result in ("done", "skipped"):
        state["flow"][args.step] = result + (" in session" if args.in_session else "") + (": " + why[:120] if why else "") + stamp
        state["step"] = role.after(args.step)
        guards.advance(sys.modules[__name__], state)
        save(state, "%s %s" % (args.step, state["flow"][args.step]))
        print("RECORDED %s %s" % (args.step, state["flow"][args.step]))
        print("NEXT: " + ("build, then " if args.step == "plan" else "") + next_step(state))
        return 0
    failed_try(state, "%s %s" % (args.step, "failed: " + why[:200] if result else "gave no STEP line"), args.step,
               "fix the cause, then run flow.py %s %s again" % (args.slug, args.step))
    return 1


def cmd_pr(args):
    state = held(args.slug)
    fit.budget_stop(args.slug, state, state_dir(), config())
    guards.waiting_gate(sys.modules[__name__], state)
    left = [step for step in FLOW if not str(state.get("flow", {}).get(step, "")).startswith(("done", "skipped"))]
    if left:
        no("the flow hasn't finished: %s. Fix: run flow.py %s %s." % (", ".join(left), args.slug, left[0]))
    what, detail = role.sync(config()["base"])
    if what == "merged":
        state = held(args.slug)
    fit.round_stop(sys.modules[__name__], state, what)
    if what == "conflict":
        failed_try(state, "merging %s conflicts in: %s" % (config()["base"], detail), "build",
                   "merge %s yourself, resolve the conflicts, commit, then pr" % config()["base"])
        return 1
    if what == "dirty":
        no("the merge was refused: %s. Fix: commit or remove the changes, then run pr again." % detail)
    if what == "merged":
        print("MERGED %s into the branch" % detail)
    guards.sync_touches(goal_file(args.slug), guards.touches_of(state_dir(), state))
    if git("status", "--porcelain", "--", goal_file(args.slug)):
        git("commit", "-m", "Goal: %s touches" % args.slug, "--", goal_file(args.slug))
    head = git("rev-parse", "HEAD")
    left = [step for step in FLOW if not str(state.get("flow", {}).get(step, "")).startswith(("done", "skipped"))]
    if left:
        no("the flow hasn't finished: %s. Fix: run flow.py %s %s." % (", ".join(left), args.slug, left[0]))
    owed = fit.owed(root(), read(goal_file(args.slug)))
    if owed:
        no("no passing defect test, seen failing, for %s. Fix: regression.py add --category defect --link ..., then red." % ", ".join(owed))
    if git("status", "--porcelain", "--", "."):
        print("NOTE: uncommitted files stay out of the PR")
    head = role.bump_version(sys.modules[__name__], state, head)
    gate, line, ids = role.lane(state_dir(), args.slug, "pr", role.flow_spec(), config())
    print(line)
    if gate == "running":
        return 0
    if gate == "fail":
        return fit.pr_fail(sys.modules[__name__], state, head, line, ids)
    role.record(state, config()["base"])
    known = run(["gh", "pr", "view", state["branch"], "--json", "url,state"])
    info = json.loads(known.stdout) if known.returncode == 0 else {}
    body = fit.pr_text(sys.modules[__name__], state)
    state["step"] = "pr"
    save(state, "pr")
    for wait in (2, 5, 0):
        pushed = run(["git", "push", "-u", "origin", state["branch"]])
        if not pushed.returncode:
            break
        time.sleep(wait)
    if pushed.returncode:
        no("push failed:\n" + pushed.stderr)
    url = info["url"] if info.get("state") == "OPEN" else ""
    if not url:
        path = state_path(args.slug) + ".body"
        write(path, body)
        done = run(["gh", "pr", "create", "--base", config()["base"], "--head", state["branch"],
                    "--title", state["goal"][:70], "--body-file", path], check=True)
        url = done.stdout.strip().splitlines()[-1]
    state["pr"] = url
    state["statuses"] = "ok" if private.pr_result(root(), config()["base"], head, state["branch"], True) else "failed"
    state["step"] = "release"
    state["status"] = "done"
    save(state, "pull request " + url)
    print("PR " + url)
    print("NEXT: " + ("workflow-release merges it: merge.py %s" % args.slug if config().get("auto_merge") is True and state.get("release") != "ask"
                      else "workflow-release asks cut or leave. The loop never merges."))
    if state["statuses"] == "failed":
        print("NEXT: the pull request will not merge until the status posts; run private.py statuses --head %s --ok" % head)
    return 5 * (state["statuses"] == "failed")


def cmd_finding(args):
    state = load(args.slug)
    if state.get("status") in ("done", "merged"):
        return guards.note_finding(state_dir(), state, args.text)
    fail_stop(state, args.text)


def cmd_resume(args):
    pods and pods.refuse(load(args.slug) or {})
    return guards.cmd_resume(sys.modules[__name__], args)


def cmd_touches(args):
    return guards.cmd_touches(sys.modules[__name__], args)


def cmd_show(args):
    state = load(args.slug)
    state["resume_at"] = fit.resume_at(state, guards.moved_since_plan(sys.modules[__name__], state))
    print(json.dumps(state, indent=2))
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    def add(name, func, *options):
        item = sub.add_parser(name)
        item.add_argument("slug")
        item.set_defaults(func=func)
        for flag, kinds in options:
            item.add_argument(flag, **kinds)
    goal = (("--goal", {"required": True}), ("--done", {"action": "append", "default": []}),
            ("--touches", {"default": ""}))
    add("new", cmd_new, *goal, ("--release", {"default": ""}), ("--here", {"action": "store_true"}))
    add("queue", cmd_queue, *goal, ("--depends-on", {"default": ""}))
    add("adopt", cmd_adopt)
    add("step", cmd_step, ("name", {}), ("--note", {"default": ""}), ("--tokens", {"type": int, "default": 0}))
    add("record", cmd_record, ("step", {"choices": FLOW}), ("--file", {"required": True}), ("--in-session", {"action": "store_true"}),
        ("--tokens", {"default": ""}))
    add("wait", cmd_wait, ("--ask", {"required": True}), ("--words", {"action": "append", "required": True}))
    add("finding", cmd_finding, ("text", {}))
    add("resume", cmd_resume, ("--why", {"required": True}), ("--by", {"default": "operation session"}))
    add("touches", cmd_touches, ("--add", {"required": True}), ("--why", {"required": True}))
    add("set", cmd_set, ("--depth", {"choices": ("full", "condensed")}), ("--bump", {"choices": ("minor", "major")}),
        ("--budget-minutes", {"type": int}), ("--budget-tokens", {"type": int}), ("--why", {"required": True}))
    for name, func in (("pr", cmd_pr), ("answer", cmd_answer), ("show", cmd_show)):
        add(name, func)
    args = parser.parse_args()
    if args.command in ("step", "record", "pr"):
        role.guard(args.command, args.slug)
        role.inbox(os.path.abspath(git("rev-parse", "--git-common-dir")), args.slug)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
