#!/usr/bin/env python3
"""Bring a second Mac or Windows machine to this machine's setup. Standard library only.

usage: machine.py [plan|apply|check] [--repo DIR] [--platform mac|windows] [--home DIR]
       machine.py record-task NAME MODE [--home DIR]
  plan (the default)  a dry run: lists what apply would write, then the owner checklist; writes nothing
  apply               installs the skill links, hooks, private-names file, mailer and one scheduled task per repo
                      (<repo>-health-regression, every 4 hours) plus the repo's own machine_setup items
  check               lists each gap as "GAP item: what -> run: fix"; writes nothing; exit 0 only with no gap
  record-task         records that you registered task NAME in the app with permission mode MODE (a note to
                      yourself: the app's own setting is the truth, and check only reminds you of it)
A value (secret, owner address, home path) is never written: a text that holds one is refused.
Windows: py -3 skills\\workflow-setup\\scripts\\machine.py (the same verbs; Windows forms are marked unverified).
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys

sys.dont_write_bytecode = True  # check writes nothing: no __pycache__ beside the scripts it imports
HERE = os.path.dirname(os.path.realpath(__file__))
SK = os.path.dirname(os.path.dirname(HERE))  # the skills folder, in a clone or installed
CLONE = os.path.dirname(SK)
sys.path.insert(0, HERE)
import seed  # noqa: E402
NO_PROMPT = ("bypass",)  # permission modes that never stop to ask
MODEL = "claude-sonnet-5-5"
UD = "Us" + "ers"  # spelled in two parts so this file holds no home path itself
LEAKS = (("home path", r"(?i)(/%s/|/home/|/root/|[A-Z]:\\{1,2}%s\\{1,2})[^/\\\s]+" % (UD, UD)),
         ("address", r"[\w.+-]+(@|%40)[\w-]+\.[\w.-]+"),
         ("secret", r"(AKIA[0-9A-Z]{16}|gh[pousr]_\w{30,}|github_pat_\w{20,}|sk-[\w-]{20,}|xox[bp]-[\w-]{10,}|-----BEGIN [A-Z ]*PRIVATE KEY)"),
         ("secret", r"(?i)(password|token|secret)\s*[:=]\s*[^\s<{$]{8,}"))
ALLOW = r"mcp__[A-Za-z0-9_-]+(__[A-Za-z0-9_-]+)?"  # an allow rule from a repo may only name an MCP tool, never a wildcard
WIN = " [unverified on Windows]"


class Ctx:
    def __init__(self, args):
        self.win = (args.platform or ("windows" if os.name == "nt" else "mac")) == "windows"
        self.home = os.path.realpath(args.home or os.path.expanduser("~"))
        self.repo = repo_of(args.repo or os.getcwd())
        self.loop = os.path.join(self.home, ".workflow-loop")
        self.routines = os.path.join(self.loop, "routines")
        self.tasks = os.path.join(self.home, ".claude", "scheduled-tasks")
        self.skills = os.path.join(self.home, ".claude", "skills")
        self.py = "py -3" if self.win else "python3"
        self.state_path = os.path.join(self.loop, "machine.json")
        try:
            state = json.load(open(self.state_path))
        except (OSError, ValueError):
            state = {}
        state = state if isinstance(state, dict) else {}
        self.state = {k: state[k] if isinstance(state.get(k), dict) else {} for k in ("repos", "modes")}
        self.refused = False
        self.name = name_of(self.repo) if self.repo else ""
        if self.name and self.state["repos"].get(self.name, self.repo) != self.repo:  # two repos called alike keep two tasks
            self.name += "-" + hashlib.sha1(self.repo.encode()).hexdigest()[:4]

    def show(self, path):
        path = os.path.realpath(path)
        return "~" + path[len(self.home):].replace(os.sep, "/") if inside(path, self.home) else path.replace("\\", "/")

    def save(self):
        os.makedirs(self.loop, exist_ok=True)
        with open(self.state_path + ".tmp", "w") as handle:
            handle.write(json.dumps(self.state, indent=2) + "\n")
        os.replace(self.state_path + ".tmp", self.state_path)


def git(repo, *args):
    done = subprocess.run(["git", "-C", repo] + list(args), capture_output=True, text=True)
    return done.stdout.strip() if done.returncode == 0 else ""


def repo_of(path):
    top = git(path, "rev-parse", "--show-toplevel")
    return os.path.realpath(top) if top else ""


def name_of(repo):
    url = re.sub(r"^[a-z+]+://[^/@]*@", "", git(repo, "remote", "get-url", "origin") or repo)  # never a login in a name
    base = url.rstrip("/").replace("\\", "/").split("/")[-1].split(":")[-1]
    return re.sub(r"[^a-z0-9-]+", "-", re.sub(r"\.git$", "", base).lower()).strip("-") or "repo"


def cadence(name):  # every 4 hours; the minute is staggered by the name so repos do not start together
    return "%d */4 * * *" % (int(hashlib.sha1(name.encode()).hexdigest()[:4], 16) % 60)


def leak(text, home=""):
    forms = [f for f in {home, home.replace("\\", "/"), home.replace("/", "\\"), home.replace("/", "\\\\")} if len(f) > 3]
    for number, line in enumerate(text.splitlines(), 1):
        for kind, pattern in LEAKS:
            if re.search(pattern, line):
                return number, kind
        if any(f in line for f in forms):
            return number, "home path"
    return None


def inside(path, root):
    path, root = os.path.realpath(path), os.path.realpath(root)
    return path == root or path.startswith(root + os.sep)


def read(path):
    try:
        return open(path).read()
    except OSError:
        return None


def in_repo(path):  # the nearest folder that exists decides: a dotfiles repo holding the home folder counts too
    folder = os.path.dirname(os.path.realpath(path))
    while folder and not os.path.isdir(folder):
        folder = os.path.dirname(folder)
    return bool(repo_of(folder))


def put(c, label, path, text, mode=None):
    """Write one file outside every repo; refuse text that holds a private value (line and kind, never the text)."""
    bad = leak(text, c.home)
    if bad:
        c.refused = True
        print("REFUSED %s: line %d holds a %s; keep it in a local file and name the file instead" % (label, bad[0], bad[1]))
        return False
    if in_repo(path) or any(root and inside(path, root) for root in [CLONE, c.repo]):
        c.refused = True
        print("REFUSED %s: %s is inside a repo, so it could be committed; write it under a folder no repo holds" % (label, c.show(path)))
        return False
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if read(path) != text:
        with open(path + ".tmp", "w", newline="\n") as handle:
            handle.write(text)
        os.replace(path + ".tmp", path)
    if mode and not c.win:
        os.chmod(path, mode)
    return True


def template(name):
    found = re.search(r"^```text template=%s\n(.*?)^```$" % name, read(os.path.join(SK, "workflow-monitoring", "references", "operation.md")) or "", re.M | re.S)
    return found.group(1) if found else None


def link(c, src, dst):
    if os.path.lexists(dst):
        return
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    try:
        if c.win and os.name == "nt":
            subprocess.run(["cmd", "/c", "mklink", "/J", dst, src], capture_output=True, check=True)
        elif c.win:
            shutil.copytree(src, dst)  # a junction needs Windows; a copy is the form the toy Windows home holds
        else:
            os.symlink(src, dst)
    except (OSError, subprocess.CalledProcessError):
        shutil.copytree(src, dst)


def skill_dirs():
    return [d for d in sorted(os.listdir(SK)) if d.startswith("workflow-")] if os.path.isdir(SK) else []


def routine(c, name, repo, body, what):
    """The routine file holds the full prompt; the task folder's SKILL.md only points at it."""
    if body is None:
        print("GAP template: the machine templates are missing -> run: reinstall the skills (workflow-monitoring)")
        return
    text = body
    for key, value in (("name", name), ("repo", repo), ("path", c.show(c.state["repos"].get(repo) or c.repo or "")), ("py", c.py),
                       ("scripts", c.show(SK)), ("guide", c.show(os.path.join(SK, "workflow-monitoring", "references", "operation.md")))):
        text = text.replace("{%s}" % key, value)  # plain replacement: a repo's own routine text may hold braces
    task = "---\nmodel: %s\nname: %s\ndescription: %s\n---\n\nRead ~/.workflow-loop/routines/%s.md and follow it exactly. It is the full prompt for this run (a REAL run, never a demo). If that file is missing, stop and report \"routine file missing\".\n" % (MODEL, name, what, name)
    if put(c, name, os.path.join(c.routines, name + ".md"), text):
        put(c, name, os.path.join(c.tasks, name, "SKILL.md"), task)


def custom(repo):
    try:
        items = json.load(open(os.path.join(repo, ".loop", "config.json"))).get("machine_setup") or []
    except (OSError, ValueError, AttributeError):
        return []
    return items if isinstance(items, list) else [None]


def doubled(c):
    try:
        listed = [e["path"] for e in json.load(open(os.path.join(c.loop, "schedule", "repos.json")))["repos"].values()]
    except (OSError, ValueError, KeyError):
        return False
    return os.path.realpath(c.repo) in listed


def hooks_gap(c):
    try:
        import seed
        folder, _ = seed.hooks_dir(c.repo)
        return "" if all(seed.hook_state(os.path.join(folder, h)) == "installed" for h in seed.GUARD) else "run: machine.py apply"
    except (ImportError, OSError):
        return "run: machine.py apply"


def held(c, task, body=True):
    ok = os.path.exists(os.path.join(c.tasks, task, "SKILL.md")) and (not body or os.path.exists(os.path.join(c.routines, task + ".md")))
    return "" if ok else "run: machine.py apply"


def items(c):
    """(name, text, gap, do): gap() is "" when the machine holds the item, else the fix; do() applies it."""
    names, mailer = os.path.join(c.loop, "private-names"), os.path.join(c.routines, "send-mail.py")
    out = [("skills", "link the workflow skills into ~/.claude/skills" + WIN * c.win,
            lambda: "" if all(os.path.lexists(os.path.join(c.skills, d)) for d in skill_dirs()) else "run: machine.py apply",
            lambda: [link(c, os.path.join(SK, d), os.path.join(c.skills, d)) for d in skill_dirs()]),
           ("private-names", "create the empty private-names file ~/.workflow-loop/private-names (mode 600)",
            lambda: "" if os.path.exists(names) else "run: machine.py apply, then add your private names to it",
            lambda: put(c, "private-names", names, "", 0o600)),
           ("mailer", "install the unattended SMTP send script (it reads the local mail.env and mail-to only)",
            lambda: "" if read(mailer) == template("mailer") and read(mailer) else "run: machine.py apply",
            lambda: put(c, "mailer", mailer, template("mailer") or "", 0o700)),
           ("task:operation-checkin", "register the operation check-in task (a pointer to the operation guide, no prompt text)",
            lambda: held(c, "operation-checkin"),
            lambda: routine(c, "operation-checkin", "operation", template("checkin"), "Operation check-in: a pointer to the operation guide."))]
    if c.repo:
        name, task = c.name, c.name + "-health-regression"

        def register():
            c.state["repos"][name] = c.repo
            routine(c, task, name, template("health-regression"),
                    "Every 4 hours on this machine: health and full regression for %s; one email to the owner." % name)
        auto = os.path.join(SK, "workflow-health", "scripts", "automation.py")
        out += [("hooks", "install the private-name git hooks in this repo" + WIN * c.win, lambda: hooks_gap(c),
                 lambda: seed.git_hooks(c.repo, adopting=True)),
                ("task:" + task, "write the %s task (every 4 hours, minute %s) and its routine file" % (task, cadence(name).split()[0]),
                 lambda: held(c, task), register),
                ("local-schedule", "drop this repo from local-schedule's launch agent (the task replaces its 4-hourly run)",
                 lambda: "run: python3 %s local uninstall --root %s" % (c.show(auto), c.repo) if doubled(c) else "",
                 lambda: subprocess.run([sys.executable, auto, "local", "uninstall", "--root", c.repo], capture_output=True,
                                        env=dict(os.environ, LOOP_SCHEDULE_HOME=os.path.join(c.loop, "schedule"),
                                                   LOOP_AGENTS_DIR=os.path.join(c.home, "Library", "LaunchAgents"))))]
        for item in custom(c.repo):
            out += custom_item(c, name, item if isinstance(item, dict) else {})
    return out


def custom_item(c, repo, item):
    kind, name = item.get("kind"), re.sub(r"[^A-Za-z0-9_.-]+", "-", str(item.get("name") or ""))
    label = "custom:%s:%s" % (kind, name)
    if not name or kind not in ("allow", "routine", "secret", "connector"):
        return [("custom:bad", "a machine_setup item is not a list entry with a name and a kind (allow, routine, secret, connector)",
                 lambda: "fix: edit the item in .loop/config.json", lambda: None)]
    if kind == "allow":
        path, rule = os.path.join(c.home, ".claude", "settings.json"), str(item.get("rule") or "")
        ok = re.fullmatch(ALLOW, rule)

        def data():
            text = read(path)
            try:
                doc = json.loads(text) if text else {}
                return doc if isinstance(doc, dict) and isinstance(doc.get("permissions") or {}, dict) else None
            except ValueError:
                return None

        def add():
            doc = data()
            if doc is None or not ok:
                c.refused = True
                print("REFUSED %s: %s" % (label, "the rule must name one MCP tool (mcp__server__tool), no wildcard" if not ok else "settings.json is not readable JSON, left alone"))
                return
            allow = doc.setdefault("permissions", {}).setdefault("allow", [])
            if rule not in allow:
                allow.append(rule)
            put(c, label, path, json.dumps(doc, indent=2) + "\n")
        return [(label, "allow rule %s (%s) in ~/.claude/settings.json" % (name, rule if ok else "REFUSED: not an MCP tool name"),
                 lambda: "" if ok and rule in ((data() or {}).get("permissions") or {}).get("allow", []) else "run: machine.py apply", add)]
    if kind == "routine":
        task, rel = repo + "-custom-" + name, str(item.get("file") or "")
        full = os.path.realpath(os.path.join(c.repo, rel))
        body = read(full) if rel and not os.path.isabs(rel) and inside(full, c.repo) and git(c.repo, "ls-files", "--error-unmatch", rel) else None
        cron = str(item.get("cron") or cadence(task))
        return [(label, "register routine %s as task %s at \"%s\" with its routine file" % (name, task, cron), lambda: held(c, task),
                 lambda: routine(c, task, repo, body, "Repo routine %s for %s." % (name, repo)) if body is not None
                 else print("GAP %s: the routine file must be a tracked file inside the repo -> run: fix the item in .loop/config.json" % label))]
    path = os.path.expanduser(str(item.get("path") or ""))
    gap = (lambda: "" if os.path.exists(path) else "run: create it yourself, see the checklist") if kind == "secret" and path else (lambda: "")
    return [(label, "%s %s (yours to provide; setup never writes it)" % (kind, name), gap, lambda: None)]


def checklist(c, tasks):
    steps = ["mail login: create ~/.workflow-loop/mail.env (SMTP_USER, SMTP_PASSWORD; SMTP_HOST, SMTP_PORT if not Gmail; mode 600) and ~/.workflow-loop/mail-to (one address) | verify: %s ~/.workflow-loop/routines/send-mail.py --check" % c.py,
             "account logins: claude, and gh auth login | verify: claude --version; gh auth status",
             "private names: one pattern per line in ~/.workflow-loop/private-names | verify: machine.py check",
             "permission mode: choose a mode that never asks (bypass) for each task in the app, then machine.py record-task NAME bypass | verify: machine.py check"]
    steps += ["register task %s in the app at \"%s\" with the no-prompt mode | verify: machine.py check" % (t, cron) for t, cron in tasks]
    if c.win:
        steps.append("Windows: install Git for Windows (sh hooks) and Python (py -3); junctions need developer mode, else a copy is used" + WIN)
    return ["owner steps (setup cannot do these):"] + ["%d. %s" % (n, s) for n, s in enumerate(steps, 1)]


def tasks_of(its):  # (task name, its cron) for every task item
    out = []
    for name, text, *_ in its:
        if name.startswith("task:"):
            found = re.search(r'at "([^"]+)"', text)
            out.append((name[5:], found.group(1) if found else cadence(name[5:].replace("-health-regression", ""))))
    return out


def gaps(c, its):
    out = ["GAP %s: %s -> %s" % (n, t, g()) for n, t, g, _ in its if g()]
    for task, _ in tasks_of(its):
        mode = c.state["modes"].get(task)
        if mode is None:
            out.append("GAP mode:%s: NOT RUNNING until you register it in the app and record its mode -> run: machine.py record-task %s bypass" % (task, task))
        elif mode not in NO_PROMPT:
            out.append("GAP mode:%s: mode %s would stop to ask -> run: set bypass in the app, then machine.py record-task %s bypass" % (task, mode, task))
    for mail in ("mail.env", "mail-to"):
        if not os.path.exists(os.path.join(c.loop, mail)):
            out.append("GAP %s: the owner-only mail file is missing -> run: see checklist step 1" % mail)
    pointer = read(os.path.join(c.routines, "operation-checkin.md"))
    if pointer is not None and (len(pointer.splitlines()) > 3 or "operation.md" not in pointer):
        out.append("GAP check-in: the routine file holds more than a pointer -> run: delete it, then machine.py apply")
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("verb", nargs="?", default="plan", choices=("plan", "apply", "check", "record-task"))
    parser.add_argument("rest", nargs="*")
    parser.add_argument("--repo", default="")
    parser.add_argument("--platform", choices=("mac", "windows"), default="")
    parser.add_argument("--home", default="")
    args = parser.parse_args()
    c = Ctx(args)
    its, found = items(c), []
    if args.verb == "record-task":
        known = [t for t, _ in tasks_of(its)]
        if len(args.rest) != 2 or args.rest[0] not in known or held(c, args.rest[0], False):
            print("REFUSED: usage: machine.py record-task NAME MODE, for a task apply has written here (%s)" % (", ".join(known) or "none"))
            return 2
        c.state["modes"][args.rest[0]] = args.rest[1]
        c.save()
        print("RECORDED task %s mode %s (a note: the app's own mode is what counts)" % tuple(args.rest))
        return 0
    if c.win:
        print("WINDOWS: its forms are untested here, each marked%s" % WIN)
    if args.verb == "plan":
        print("DRY RUN: nothing written; run `apply` to write")
        for name, text, gap, _ in its:
            print("%s %s: %s" % ("OK  " if not gap() else "WILL", name, text))
    elif args.verb == "apply":
        for name, text, gap, do in its:
            if gap() or name.startswith("task:"):
                do()
                print(("DONE " if not gap() else "FAILED ") + name + ("" if not gap() else ": still a gap, see above"))
            else:
                print("OK   %s" % name)
        if c.repo:
            c.state["repos"][c.name] = c.repo
            c.save()
        print("NOT RUNNING until you do the owner steps below for each task")
    else:
        found = gaps(c, its)
        print("\n".join(found) or "MACHINE OK (modes are notes you recorded; the app's setting is the truth)")
    print("\n".join(checklist(c, tasks_of(its))))
    return 1 if c.refused or found or (args.verb == "apply" and any(g() for _, _, g, _ in its)) else 0


if __name__ == "__main__":
    sys.exit(main())
