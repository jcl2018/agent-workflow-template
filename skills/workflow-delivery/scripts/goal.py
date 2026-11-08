#!/usr/bin/env python3
"""Hold one goal's record: done lines, the skill flow's steps, checks, PR.

usage: goal.py <command> <slug> [options]

  new SLUG --here --goal TEXT --done LINE [--touches A,B] [--release R]
  queue SLUG --goal TEXT --done LINE [--touches A,B] [--depends-on A,B]
  step SLUG NAME [--note TEXT] [--tokens N]
  check SLUG
  record SLUG STEP --file REPLY  record a flow step flow.py ran: idea, plan, review, qa or ship
  pr SLUG  merge the latest base (rerun checks if it changed), push, open the PR, join its milestone
Goal steps (step, check, record, pr) refuse outside a worker; a worker also sees what the operation session sent it.
  wait SLUG --ask TEXT --words W [--words W]
  answer SLUG
  finding SLUG TEXT
  show SLUG
"""
import argparse
import datetime
import hashlib
import json
import os
import re
import subprocess
import sys
import time

import role

# No terminal, no waiting: a prompt from git or gh must fail, not block.
os.environ.update(GIT_TERMINAL_PROMPT="0", GH_PROMPT_DISABLED="1", GIT_EDITOR="true", GIT_ASKPASS="true", SSH_ASKPASS="true")
if not sys.stdin or not sys.stdin.isatty():
    os.dup2(os.open(os.devnull, os.O_RDONLY), 0)

FLOW = ("idea", "plan", "review", "qa", "ship")
FLOW_FILE = "~/.workflow-loop/flow.json"
NO_FLOW = ("no skill flow is set. Fix: write %s naming your idea, plan, review, test and ship skills and the "
           "command that runs them unattended (see loop-files.md)." % FLOW_FILE)


MAX_TRIES = 3
SLUG = re.compile(r"^[a-z0-9][a-z0-9-]{0,50}$")
TEMPLATE = """# {goal}

- Slug: {slug}
- Touches: {touches}

## Done lines

Frozen. A wrong done line needs a new goal.

{done}

## Verify by hand

<!-- Numbered steps for a person, each with an Expect: line. A release needs this. -->
"""
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


def load(slug):
    try:
        return json.loads(read(state_path(slug)))
    except OSError:
        no("no goal named %s. Fix: start it with new." % slug)


def save(state, note=None):
    state["updated"] = now()
    if note:
        state.setdefault("log", []).append("%s %s" % (state["updated"], note))
    path = state_path(state["slug"])
    try:
        role.report(json.loads(read(path)), state, state["updated"])
    except (OSError, ValueError):
        role.report({}, state, state["updated"])
    temp = path + ".%d.tmp" % os.getpid()
    write(temp, json.dumps(state, indent=2))
    os.replace(temp, path)


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


def write_finding(state, text):
    line = "- %s: %s\n" % (state["slug"], " ".join(text.split()))
    path = os.path.join(root(), ".loop", "findings.md")
    write(path, line, "a")
    git("add", ".loop/findings.md")
    git("commit", "-m", "Finding: %s" % state["slug"], "--", ".loop/findings.md", check=False)
    push = run(["git", "push", "-u", "origin", "HEAD"])
    if push.returncode:
        print("NOTE: finding stays local, push failed: " + push.stderr.strip()[:200])


def fail_stop(state, text):
    state["status"] = "stopped"
    state["finding"] = text
    state["waiting"] = None
    save(state, "stopped: " + text)
    write_finding(state, text)
    print("STOPPED %s: %s" % (state["slug"], text))
    sys.exit(3)


def failed_try(state, why, step="build", fix="fix it, then run check again"):
    state["tries"] = state.get("tries", 0) + 1
    most = int(config().get("max_tries") or MAX_TRIES)
    if state["tries"] >= most:
        fail_stop(state, "Failed %d tries. Last: %s" % (state["tries"], why))
    state["step"] = step
    save(state, "try %d failed: %s" % (state["tries"], why))
    print("TRY %d OF %d FAILED: %s" % (state["tries"], most, why))
    print("NEXT: " + fix)


def flow_set():
    """The private flow file names a skill for every step. Its contents never go in the repo."""
    try:
        steps = json.loads(read(os.path.expanduser(os.environ.get("LOOP_FLOW") or FLOW_FILE))).get("steps") or {}
    except (OSError, ValueError, AttributeError):
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
    if os.path.exists(state_path(args.slug)):
        no("%s already exists. Fix: pick a new slug." % args.slug)
    cfg = config()
    touches = [item.strip() for item in args.touches.split(",") if item.strip()]
    branch = "loop/" + args.slug
    current = git("branch", "--show-current")
    if current == cfg["base"]:
        git("switch", "-c", branch)
    elif current != branch:
        no("on branch %s. Fix: go to %s or %s first." % (current, cfg["base"], branch))
    lines = ["%d. %s" % (index, " ".join(line.split())) for index, line in enumerate(args.done, 1)]
    path = goal_file(args.slug)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    write(path, TEMPLATE.format(goal=" ".join(args.goal.split()), slug=args.slug,
                                touches=", ".join(touches) or "not declared", done="\n".join(lines)))
    git("add", path)
    git("commit", "-m", "Goal: %s" % args.slug, "--", path)
    state = {"slug": args.slug, "goal": args.goal, "status": "running", "step": "idea", "tries": 0, "flow": {},
             "branch": branch, "worktree": root(), "touches": touches, "pid": None, "pr": "",
             "batch": bool(os.environ.get("LOOP_BATCH")), "done_sha": done_sha(lines), "checks": "",
             "release": args.release, "waiting": None, "finding": "", "log": []}
    save(state, "frozen %d done lines" % len(lines))
    print("FROZEN %s branch=%s step=idea" % (args.slug, branch))
    return 0


def cmd_queue(args):
    valid(args)
    if any("|" in text for text in [args.goal, args.touches] + args.done):
        no("no | in a queue line.")
    path = os.path.join(root(), ".loop", "queue.md")
    held = read(path) if os.path.exists(path) else ""
    if os.path.exists(state_path(args.slug)) or "- slug: %s |" % args.slug in held:
        no("%s already exists. Fix: pick a new slug." % args.slug)
    parts = ["slug: " + args.slug]
    if args.touches:
        parts.append("touches: " + args.touches)
    if args.depends_on:
        parts.append("depends-on: " + args.depends_on)
    parts.append("goal: " + " ".join(args.goal.split()))
    parts += ["done: " + " ".join(line.split()) for line in args.done]
    write(path, ("" if held.endswith("\n") or not held else "\n") + "- " + " | ".join(parts) + "\n", "a")
    print("QUEUED %s in .loop/queue.md" % args.slug)
    return 0


def cmd_step(args):
    state = load(args.slug)
    state["step"] = args.name
    if args.tokens:
        state["tokens"] = dict(state.get("tokens") or {}, **{args.name: args.tokens})
    save(state, args.name + (": " + args.note if args.note else ""))
    print("STEP %s %s" % (args.slug, args.name))
    return 0


def cmd_check(args):
    state = held(args.slug)
    state["step"] = "checks"
    save(state, "checks")
    commands = config().get("checks", [])
    if not commands and config().get("require_checks", True) is False:
        state["checks"], state["checks_sha"] = "none", git("rev-parse", "HEAD")
        save(state, "no checks: require_checks is off")
        print("NO CHECKS %s: require_checks is off in this repo, so nothing was tested" % args.slug)
        print("NEXT: " + next_step(state))
        return 0
    if not commands:
        fail_stop(state, "The repo has no check commands. Add them to .loop/config.json.")
    parts, sums, failed = [], [], False
    for command in commands:
        done = subprocess.run(command, shell=True, capture_output=True, text=True, cwd=root())
        parts.append("$ %s\nexit %d\n%s%s" % (command, done.returncode, done.stdout[-4000:], done.stderr[-4000:]))
        sums.append("CHECK exit %d: %s" % (done.returncode, command))
        failed = failed or done.returncode != 0
    report = "\n".join(sums) + "\n\n" + "\n".join(parts)
    write(os.path.join(state_dir(), args.slug + ".checks.txt"), report)
    state["checks"] = "fail" if failed else "pass"
    state["checks_sha"] = git("rev-parse", "HEAD")
    if failed:
        print(report)
        failed_try(state, "checks failed")
        return 1
    save(state, "checks pass")
    print("CHECKS PASS %s" % args.slug)
    print("NEXT: " + next_step(state))
    return 0


def next_step(state):
    left = [step for step in FLOW if step not in state.get("flow", {})]
    return "flow.py %s %s" % (state["slug"], left[0]) if left else "pr"


def cmd_record(args):
    """Apply what a flow step left: done or skipped moves on, pending waits on the owner, anything else is a try."""
    state = held(args.slug)
    reply = os.path.realpath(args.file)
    ran = os.path.join(state_dir(), "%s.%s.ran" % (args.slug, args.step))
    if reply != os.path.realpath(os.path.join(state_dir(), "%s.%s.txt" % (args.slug, args.step))) or not os.path.exists(ran):
        no("%s wasn't run by flow.py. Fix: run flow.py %s %s until it prints NEXT." % (args.step, args.slug, args.step))
    text = read(reply)
    found = re.findall(r"^\W*STEP:\s*(done|skipped|pending|failed)\b[ :.-]*(.*)$", text, re.M | re.I)
    result, why = (found[-1][0].lower(), found[-1][1].strip()) if found else ("", "")
    pending = [" ".join(item.split()) for item in re.findall(r"^\W*PENDING:\s*(.+)$", text, re.M)]
    os.remove(ran)
    if (pending or result == "pending") and config().get("auto_approve") is True:
        took = "; ".join(pending) or why or "the step's pending gate"
        state["flow"][args.step] = "done: auto-approved: " + took[:200]
        state["step"] = role.after(args.step)
        state["note"] = {"text": "auto-approved at %s: %s" % (args.step, took[:240]), "at": now()}
        save(state, "%s auto-approved: %s" % (args.step, took[:300]))
        print("AUTO-APPROVED %s %s: %s" % (args.slug, args.step, took))
        print("NEXT: " + ("build, then check" if args.step == "plan" else "check" if args.step != "idea" else next_step(state)))
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
        state["flow"][args.step] = result + (": " + why[:120] if why else "")
        state["step"] = role.after(args.step)
        save(state, "%s %s" % (args.step, state["flow"][args.step]))
        print("RECORDED %s %s" % (args.step, state["flow"][args.step]))
        print("NEXT: " + ("build, then check" if args.step == "plan" else "check" if args.step != "idea" else next_step(state)))
        return 0
    failed_try(state, "%s %s" % (args.step, "failed: " + why[:200] if result else "gave no STEP line"), args.step,
               "fix the cause, then run flow.py %s %s again" % (args.slug, args.step))
    return 1


def bump_version(state, head):
    cfg = config()
    name = cfg.get("version_file") or "VERSION"
    path = os.path.join(root(), name)
    if not cfg.get("pr_bumps_version") or not os.path.exists(path):
        return head
    version = read(path).strip()
    if version != git("show", "%s:%s" % (base_ref(state), name), check=False).strip():
        return head
    if not re.match(r"^\d+(\.\d+)+$", version):
        no("the version %r isn't numbers and dots. Fix: set it by hand." % version)
    parts = version.split(".")
    parts[-1] = str(int(parts[-1]) + 1)
    write(path, ".".join(parts) + "\n")
    git("add", "--", name)
    git("commit", "-m", "Bump version to " + ".".join(parts), "--", name)
    new = git("rev-parse", "HEAD")
    state["checks_sha"] = new
    save(state, "bumped %s to %s" % (name, ".".join(parts)))
    return new


def cmd_pr(args):
    state = held(args.slug)
    left = [step for step in FLOW if not str(state.get("flow", {}).get(step, "")).startswith(("done", "skipped"))]
    if left:
        no("the flow hasn't finished: %s. Fix: run flow.py %s %s." % (", ".join(left), args.slug, left[0]))
    what, detail = role.sync(config()["base"])
    if what == "conflict":
        failed_try(state, "merging %s conflicts in: %s" % (config()["base"], detail), "build",
                   "merge %s yourself, resolve the conflicts, commit, run check, then pr" % config()["base"])
        return 1
    if what == "merged":
        print("MERGED %s into the branch; running the checks again" % detail)
        if cmd_check(args):
            return 1
        state = held(args.slug)
    head = git("rev-parse", "HEAD")
    gated = config().get("require_checks", True) is not False
    if gated and (state.get("checks") != "pass" or state.get("checks_sha") != head):
        no("checks have not passed on this commit. Fix: run check.")
    if git("status", "--porcelain", "--", "."):
        print("NOTE: uncommitted files stay out of the PR")
    head = bump_version(state, head)
    state["step"] = "pr"
    save(state, "pr")
    for wait in (2, 5, 0):
        pushed = run(["git", "push", "-u", "origin", state["branch"]])
        if not pushed.returncode:
            break
        time.sleep(wait)
    if pushed.returncode:
        no("push failed:\n" + pushed.stderr)
    known = run(["gh", "pr", "view", state["branch"], "--json", "url,state"])
    info = json.loads(known.stdout) if known.returncode == 0 else {}
    url = info["url"] if info.get("state") == "OPEN" else ""
    if not url:
        body = read(goal_file(args.slug))
        flow = "".join("\n- %s: %s" % (step, state["flow"][step]) for step in FLOW)
        ran = "pass on %s" % head[:10] if state.get("checks") == "pass" else "none ran; this repo configures no checks"
        body += "\n## Result\n\nChecks: %s. Skill flow:%s\n" % (ran, flow)
        done = run(["gh", "pr", "create", "--base", config()["base"], "--head", state["branch"],
                    "--title", state["goal"][:70], "--body", body], check=True)
        url = done.stdout.strip().splitlines()[-1]
    state["pr"] = url
    state["step"] = "release"
    state["status"] = "done"
    save(state, "pull request " + url)
    print("PR " + url)
    hook = os.path.normpath(os.path.join(sys.argv[0], "..", "..", "..", "workflow-health", "scripts", "milestone.py"))
    if os.path.exists(hook):
        print(run([sys.executable, hook, "attach", args.slug, "--live"]).stdout.strip())
    print("NEXT: " + ("workflow-release merges it: merge.py %s" % args.slug if config().get("auto_merge") is True
                      else "workflow-release asks cut or leave. The loop never merges."))
    return 0


def cmd_wait(args):
    state = load(args.slug)
    state["status"] = "waiting"
    state["waiting"] = {"ask": args.ask, "words": args.words}
    save(state, "waiting: " + args.ask)
    print("WAITING %s: %s" % (args.slug, args.ask))
    return 0


def cmd_answer(args):
    state = load(args.slug)
    state["status"] = "running"
    state["waiting"] = None
    save(state, "answered")
    print("ANSWERED %s" % args.slug)
    return 0


def cmd_finding(args):
    state = load(args.slug)
    fail_stop(state, args.text)


def cmd_show(args):
    print(json.dumps(load(args.slug), indent=2))
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
    add("step", cmd_step, ("name", {}), ("--note", {"default": ""}), ("--tokens", {"type": int, "default": 0}))
    add("record", cmd_record, ("step", {"choices": FLOW}), ("--file", {"required": True}))
    add("wait", cmd_wait, ("--ask", {"required": True}), ("--words", {"action": "append", "required": True}))
    add("finding", cmd_finding, ("text", {}))
    for name, func in (("check", cmd_check), ("pr", cmd_pr), ("answer", cmd_answer), ("show", cmd_show)):
        add(name, func)
    args = parser.parse_args()
    if args.command in ("step", "check", "record", "pr"):
        role.guard(args.command)
        role.inbox(os.path.abspath(git("rev-parse", "--git-common-dir")), args.slug)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
