#!/usr/bin/env python3
"""The same smoke set on every agent and machine; each run appends one dated line to .loop/matrix-runs.tsv.

usage: matrix-smoke.py [--agent claude-app|claude-cli|codex|ci] [--no-record] [--keep] [--skills DIR] [--only STEP[,STEP]]

Steps, in order (each prints `PASS: <step>: ...` or `FAIL: <step>: ...`):
  package   build the Agensi ZIP with dev/package.py and unpack it; every later step runs the unpacked skills, not the checkout's
  adopt     adopt a toy repo (dev/toy/make.sh) with the unpacked setup.py and merge the adoption
  freeze    freeze a goal in it (goal.py new --here)
  qa        run its land rows (regression.py run land): the result line must show no failed row
  health    health.py check prints its HEALTH verdict
  runbook   resolve the first routine of .loop/routines.tsv to its Runbook section on its page and the file its Steps name
  relay     a goal frozen under pod-a is adopted under pod-b (goal.py adopt), and the merge lock is taken and released

The record (date, agent, os, machine, commit, result) is what `health.py check` reads (rule `matrix`). The result is `pass` only
when every step passed. --agent defaults to `ci` under GitHub Actions, else `claude-cli`: the agent that runs this script is the
one the line proves, so a Codex or app session passes its own name. Needs git, bash (Git Bash on Windows) and python3.
"""
import argparse
import datetime
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
STEPS = ("package", "adopt", "freeze", "qa", "health", "runbook", "relay")
AGENTS = ("claude-app", "claude-cli", "codex", "ci")
fails = []


def say(ok, step, text):
    print("%s: %s: %s" % ("PASS" if ok else "FAIL", step, text))
    if not ok:
        fails.append(step)


def run(cmd, cwd=None, env=None, timeout=600):
    merged = dict(os.environ, **(env or {}))
    done = subprocess.run(cmd, cwd=cwd, env=merged, capture_output=True, text=True, timeout=timeout, stdin=subprocess.DEVNULL)
    return done.returncode, (done.stdout or "") + (done.stderr or "")


def os_name():
    return {"Windows": "windows", "Darwin": "macos", "Linux": "linux"}.get(platform.system(), platform.system().lower())


def find_skills(folder):
    for base, dirs, _ in os.walk(folder):
        if os.path.isfile(os.path.join(base, "workflow-setup", "scripts", "setup.py")):
            return base
    return ""


def step_package(work, skills_arg):
    if skills_arg:
        say(os.path.isdir(skills_arg), "package", "using --skills %s (not the package)" % skills_arg)
        return skills_arg
    out = os.path.join(work, "package.zip")
    code, text = run([sys.executable, os.path.join(ROOT, "dev", "package.py"), "--root", ROOT, "--out", out])
    if code or not os.path.isfile(out):
        say(False, "package", "dev/package.py exited %d: %s" % (code, text.strip().splitlines()[-1][:160] if text.strip() else ""))
        return ""
    target = os.path.join(work, "pkg")
    with zipfile.ZipFile(out) as bundle:
        bundle.extractall(target)
    skills = find_skills(target)
    say(bool(skills), "package", "built and unpacked the ZIP (%d bytes)" % os.path.getsize(out) if skills else "the ZIP holds no workflow-setup")
    return skills


def step_adopt(work, skills, env):
    code, text = run(["bash", os.path.join(HERE, "make.sh"), os.path.join(work, "toy")])
    repo = os.path.join(work, "toy", "repo")
    if code:
        say(False, "adopt", "make.sh exited %d" % code)
        return ""
    code, text = run([sys.executable, os.path.join(skills, "workflow-setup", "scripts", "setup.py")], repo, env)
    wrote = "WROTE the adoption on branch workflow-setup" in text  # exit 1 with a REFUSED agent_command line is normal on a first run
    merged = run(["git", "switch", "-q", "main"], repo)[0] == 0 and run(["git", "merge", "-q", "--no-edit", "workflow-setup"], repo)[0] == 0
    run(["git", "push", "-q", "origin", "main"], repo)
    say(wrote and merged, "adopt", "setup adopted the toy repo and the adoption merged" if wrote and merged else "setup said: " + text.strip()[-160:])
    return repo if wrote and merged else ""


def step_freeze(repo, skills, env):
    goal = [sys.executable, os.path.join(skills, "workflow-delivery", "scripts", "goal.py")]
    code, text = run(goal + ["new", "smoke", "--here", "--goal", "Add a subtract function", "--done", "calc.py has subtract(a, b)"],
                     repo, dict(env, LOOP_ROLE="worker"))
    say("FROZEN smoke" in text, "freeze", "goal frozen" if "FROZEN smoke" in text else text.strip()[-160:])


def step_qa(repo, skills, env):
    code, text = run([sys.executable, os.path.join(skills, "workflow-regression", "scripts", "regression.py"), "run", "land"], repo, env)
    line = next((l for l in text.splitlines() if l.startswith("RESULT ")), "")
    ok = bool(re.match(r"RESULT \d+ passed.* 0 failed", line))
    say(ok, "qa", line or text.strip()[-160:])


def step_health(repo, skills, env):
    code, text = run([sys.executable, os.path.join(skills, "workflow-health", "scripts", "health.py"), "check"], repo, dict(env, LOOP_BOARD_HEALTH="green"))
    line = next((l for l in text.splitlines() if l.startswith("HEALTH: ")), "")
    say(bool(line), "health", line or "no HEALTH line: " + text.strip()[-160:])


def step_runbook():
    """The first routine in .loop/routines.tsv names a page; its '### routine' section must have a Steps line, and the workflow
    file that line names must exist. This reads the pointer an agent given only 'run routine X' would follow; it never runs the
    live routine (a scheduled one writes issues and mail)."""
    try:
        lines = [l.split("\t") for l in open(os.path.join(ROOT, ".loop", "routines.tsv")) if l.strip() and not l.startswith("#")]
        routine, page = lines[0][0], lines[0][1]
        text = open(os.path.join(ROOT, "docs", "wiki", page.replace(".md", "") + ".md")).read()
    except (OSError, IndexError):
        say(False, "runbook", "no routine in .loop/routines.tsv, or its page is unreadable")
        return
    section = re.search(r"^### %s\s*$(.*?)(?=^#{2,3} |\Z)" % re.escape(routine), text, re.M | re.S)
    steps = re.search(r"\*\*Steps:\*\*(.*)", section.group(1)) if section else None
    named = re.findall(r"`(\.github/workflows/[^`]+|[^`]+\.py)`", steps.group(1)) if steps else []
    ok = bool(named) and all(os.path.exists(os.path.join(ROOT, n)) or n.endswith(".py") for n in named)
    say(ok, "runbook", "routine %s: Steps names %s" % (routine, ", ".join(named)) if ok else "routine %s has no Runbook Steps naming a file" % routine)


def step_relay(repo, skills, env, work):
    goal = [sys.executable, os.path.join(skills, "workflow-delivery", "scripts", "goal.py")]
    stub = os.path.join(work, "py")
    os.makedirs(stub, exist_ok=True)
    with open(os.path.join(stub, "sitecustomize.py"), "w") as handle:  # gh is answered inside python: a PATH stub is not runnable on Windows
        handle.write("import subprocess\n_run = subprocess.run\n"
                     "def run(args, *a, **k):\n"
                     "    if args and args[0] == 'gh':\n"
                     "        return subprocess.CompletedProcess(args, 0, '{\"url\": \"https://github.com/o/r/pull/7\", \"state\": \"OPEN\"}', '')\n"
                     "    return _run(args, *a, **k)\n"
                     "subprocess.run = run\n")
    pods = dict(env, PYTHONPATH=stub)
    run(["git", "switch", "-q", "main"], repo)
    code, text = run(goal + ["new", "relay", "--here", "--goal", "Relay goal", "--done", "relay works", "--touches", "calc.py"],
                     repo, dict(pods, LOOP_POD_ID="pod-a", LOOP_ROLE="worker"))
    pushed = code == 0 and run(["git", "push", "-q", "-u", "origin", "loop/relay"], repo)[0] == 0
    common = os.path.abspath(os.path.join(repo, run(["git", "rev-parse", "--git-common-dir"], repo)[1].strip()))
    record = os.path.join(common, "loop", "runs", "relay.json")
    if os.path.exists(record):
        os.remove(record)  # the second pod never had pod-a's record
    code, text = run(goal + ["adopt", "relay"], repo, dict(pods, LOOP_POD_ID="pod-b", LOOP_ROLE="worker"))
    adopted = pushed and "ADOPTED relay" in text
    graph = os.path.join(skills, "workflow-monitoring", "scripts")
    probe = ("import sys, os; sys.path.insert(0, %r); import graph; common = %r\n"
             "graph.merge_lock(common); held = os.path.exists(os.path.join(common, 'loop', 'merge.lock')); print('HELD' if held else 'NOLOCK')\n"
             % (graph, common))
    code, text2 = run([sys.executable, "-c", probe], repo, env)
    released = not os.path.exists(os.path.join(common, "loop", "merge.lock"))
    ok = adopted and "HELD" in text2 and released
    say(ok, "relay", "frozen under pod-a, adopted under pod-b, merge lock taken and released" if ok
        else "adopted=%s lock=%s released=%s %s" % (adopted, "HELD" in text2, released, (text if not adopted else text2).strip()[-120:]))


def record(agent, result):
    commit = run(["git", "rev-parse", "--short", "HEAD"], ROOT)[1].strip()
    path = os.path.join(ROOT, ".loop", "matrix-runs.tsv")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    new = not os.path.exists(path)
    with open(path, "a", newline="\n") as handle:
        if new:
            handle.write("# date\tagent\tos\tmachine\tcommit\tresult\n")
        handle.write("%s\t%s\t%s\t%s\t%s\t%s\n" % (datetime.date.today().isoformat(), agent, os_name(),
                                                  re.sub(r"\s", "", platform.node()) or "unknown", commit or "unknown", result))
    print("RECORDED %s: %s on %s %s" % (os.path.relpath(path, ROOT), agent, os_name(), result))


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--agent", choices=AGENTS, default="ci" if os.environ.get("GITHUB_ACTIONS") else "claude-cli")
    parser.add_argument("--no-record", action="store_true")
    parser.add_argument("--keep", action="store_true")
    parser.add_argument("--skills", default="", help="run this skills folder instead of the unpacked package")
    parser.add_argument("--only", default="", help="comma list of steps to run (the first ones are still needed by the later ones)")
    args = parser.parse_args()
    only = [s for s in args.only.split(",") if s]
    bad = [s for s in only if s not in STEPS]
    if bad:
        print("REFUSED: no step %s. Fix: use one of %s." % (bad[0], ", ".join(STEPS)), file=sys.stderr)
        return 2
    want = lambda name: not only or name in only
    work = tempfile.mkdtemp(prefix="matrix-smoke-")
    home = os.path.join(work, "home")
    os.makedirs(os.path.join(home, ".workflow-loop"))
    gitconfig = os.path.join(work, "gitconfig")
    open(gitconfig, "w").close()
    env = {"HOME": home, "USERPROFILE": home, "GIT_CONFIG_GLOBAL": gitconfig, "GIT_CONFIG_NOSYSTEM": "1", "GIT_TERMINAL_PROMPT": "0",
           "LOOP_NO_GIT_HOOKS": "1", "PYTHONDONTWRITEBYTECODE": "1"}
    for name in ("LOOP_ROLE", "LOOP_POD_ID", "LOOP_FLOW", "LOOP_SESSION_TOOL", "LOOP_OPERATION_SESSION", "CLAUDE_SESSION_ID"):
        os.environ.pop(name, None)
    try:
        skills = step_package(work, args.skills) if want("package") or only else step_package(work, args.skills)
        repo = ""
        if skills:
            repo = step_adopt(work, skills, env) if want("adopt") else ""
            if repo and want("freeze"):
                step_freeze(repo, skills, env)
            if repo and want("qa"):
                step_qa(repo, skills, env)
            if repo and want("health"):
                step_health(repo, skills, env)
            if want("runbook"):
                step_runbook()
            if repo and want("relay"):
                step_relay(repo, skills, env, work)
    finally:
        if args.keep:
            print("KEPT %s" % work)
        else:
            shutil.rmtree(work, ignore_errors=True)
    result = "fail" if fails or (not only and not skills) else "pass"
    print("SMOKE %s on %s %s: %s" % (args.agent, os_name(), platform.node(), result))
    if not args.no_record and not only:  # a partial run proves no cell
        record(args.agent, result)
    return 0 if result == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
