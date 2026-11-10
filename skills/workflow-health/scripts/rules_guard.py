"""Security and privacy, Size, Performance check-time and Hygiene idle-sessions rules (groups.py). Read-only.

  private                tracked files matching a leak pattern (leak_patterns in the private flow file): FAIL with
                         file:line and the pattern's number only, never the matched text; INFO with no pattern set
  scan-hook              no commit scan hook (core.hooksPath or hooks/pre-commit): WARN; INFO in CI, where it can't be
  workflow-permissions   a workflow with no top-level permissions: (WARN)
  skill-lines            a SKILL.md of 150 lines or more (FAIL)
  requirements-per-page  a page with more requirements than criteria_max (default 6) (FAIL)
  check-time             the check, up to its Performance group, past 60 seconds (WARN; no number on a pass)
  idle-sessions          a busy worker session whose goal has ended (WARN; INFO with no session pool)
"""
import glob
import json
import os
import subprocess

# No terminal, no waiting: a prompt from git or gh must fail, not block.
os.environ.update(GIT_TERMINAL_PROMPT="0", GH_PROMPT_DISABLED="1", GIT_EDITOR="true", GIT_ASKPASS="true", SSH_ASKPASS="true")
import sys
import time

from rules_trace import LINE, pages, row

SKILL_LINES = 150
CHECK_SECONDS = 60


def git(root, *args):
    done = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True)
    return done.stdout if done.returncode in (0, 1) else None


def patterns():
    found = []
    for path in dict.fromkeys(os.path.expanduser(p) for p in ("~/.workflow-loop/flow.json", os.environ.get("LOOP_FLOW") or "")):
        try:
            with open(path) as handle:
                items = json.load(handle).get("leak_patterns") or []
        except (OSError, ValueError, AttributeError):
            continue
        found += [p for p in items if isinstance(p, str) and p.strip()]
    return list(dict.fromkeys(found))


def private(root):
    wanted = patterns()
    if not wanted:
        return [row("INFO", "security", "patterns", "private", "not applicable here: no leak_patterns set in the private flow file")]
    out = []
    for number, pattern in enumerate(wanted, 1):
        hits = git(root, "grep", "-n", "-I", "-E", "-e", pattern, "--", ".", ":(exclude).git")
        if hits is None:  # git grep exits 128 on a bad pattern: never a silent pass
            out.append(row("UNREAD", "security", "pattern %d" % number, "private", "leak pattern %d is not a valid regex" % number,
                           "fix leak_patterns in the private flow file"))
            continue
        for line in hits.splitlines():
            where = ":".join(line.split(":", 2)[:2])  # file:line, never the text
            out.append(row("FAIL", "security", where, "private", "matches leak pattern %d" % number,
                           "remove it from the file and from history", where))
    return out


def scan_hook(root):
    hooks = (git(root, "config", "core.hooksPath") or "").strip()
    common = (git(root, "rev-parse", "--git-common-dir") or ".git").strip()
    path = os.path.join(root, hooks, "pre-commit") if hooks else os.path.join(root, common, "hooks", "pre-commit")
    if os.path.isfile(path) and os.access(path, os.X_OK):
        return []
    if os.environ.get("CI") or os.environ.get("GITHUB_ACTIONS"):
        return [row("INFO", "security", "pre-commit", "scan-hook", "not applicable here: a fresh clone has no hooks")]
    return [row("WARN", "security", "pre-commit", "scan-hook", "no commit scan hook is installed",
                "install it (workflow-setup)", "pre-commit")]


def workflow_permissions(root):
    out = []
    for path in sorted(glob.glob(os.path.join(root, ".github", "workflows", "*.y*ml"))):
        text = open(path, errors="replace").read()
        if not any(line.startswith("permissions:") for line in text.splitlines()):
            name = os.path.relpath(path, root)
            out.append(row("WARN", "security", name, "workflow-permissions", "no top-level permissions:",
                           "declare the least permissions it needs", name))
    return out


def skill_lines(root):
    out = []
    for path in sorted(glob.glob(os.path.join(root, "skills", "*", "SKILL.md"))):
        count = sum(1 for _ in open(path, errors="replace"))
        if count >= SKILL_LINES:
            name = os.path.relpath(path, root)
            out.append(row("FAIL", "size", name, "skill-lines", "%d lines, %d or more" % (count, SKILL_LINES),
                           "move detail into references/", name))
    return out


def requirements_per_page(root):
    try:
        with open(os.path.join(root, ".loop", "config.json")) as handle:
            limit = int(json.load(handle).get("criteria_max", 6))
    except (OSError, ValueError, TypeError, AttributeError):
        limit = 6
    return [row("FAIL", "size", name, "requirements-per-page", "%d requirements, over %d" % (len(LINE.findall(text)), limit),
                "merge requirements, or raise criteria_max", name)
            for name, text in pages(root).items() if len(LINE.findall(text)) > limit]


def check_time(root):
    start = float(os.environ.get("LOOP_HEALTH_T0") or 0) or (getattr(sys.modules.get("__main__"), "T0", [None]) or [None])[0]
    if not start:
        return [row("INFO", "performance", "check", "check-time", "not measured outside health.py check")]
    if time.time() - start > CHECK_SECONDS:
        return [row("WARN", "performance", "check", "check-time", "the check took over %d seconds" % CHECK_SECONDS,
                    "find the slow rule (health.py check --group NAME)", "check")]
    return []


def idle_sessions(root):
    common = (git(root, "rev-parse", "--git-common-dir") or ".git").strip()
    loop = os.path.join(root, common, "loop")
    try:
        with open(os.path.join(loop, "session-pool.json")) as handle:
            pool = json.load(handle)
    except (OSError, ValueError):
        return [row("INFO", "hygiene", "sessions", "idle-sessions", "not applicable here: no session pool")]
    out = []
    for sid, item in sorted((pool or {}).items()):
        if not isinstance(item, dict) or item.get("state") != "busy" or not item.get("slug"):
            continue
        try:
            with open(os.path.join(loop, "runs", item["slug"] + ".json")) as handle:
                status = json.load(handle).get("status")
        except (OSError, ValueError, AttributeError):
            continue
        if status in ("done", "merged"):
            out.append(row("WARN", "hygiene", sid, "idle-sessions", "busy with %s, which is %s" % (item["slug"], status),
                           "sessions.py free %s" % item["slug"], sid))
    return out


FUNCTIONS = {"private": private, "scan-hook": scan_hook, "workflow-permissions": workflow_permissions,
             "skill-lines": skill_lines, "requirements-per-page": requirements_per_page, "check-time": check_time,
             "idle-sessions": idle_sessions}


def _c():
    import controls
    return controls


def f_private(root):
    c = _c(); c.repo(root)
    c.write(root, "flow.json", json.dumps({"leak_patterns": ["PLANTED-SECRET-[0-9]+"]}))
    os.environ["LOOP_FLOW"] = os.path.join(root, "flow.json")
    c.write(root, "notes.txt", "see PLANTED-SECRET-42\n")
    c.commit(root, "plant")


def f_scan_hook(root):
    c = _c(); c.repo(root)
    os.environ.pop("CI", None); os.environ.pop("GITHUB_ACTIONS", None)


def f_workflow_permissions(root):
    c = _c(); c.repo(root)
    c.write(root, ".github/workflows/x.yml", "on: push\njobs: {}\n")


def f_skill_lines(root):
    c = _c(); c.repo(root)
    c.write(root, "skills/x/SKILL.md", "line\n" * SKILL_LINES)


def f_requirements_per_page(root):
    c = _c(); c.repo(root, {"criteria_max": 1})
    c.write(root, "docs/wiki/One.md", "# One\n\n## Requirements\n\n- AB-1: **Unreviewed** a.\n- AB-2: **Unreviewed** b.\n")


def f_check_time(root):
    c = _c(); c.repo(root)
    os.environ["LOOP_HEALTH_T0"] = "1"


def f_idle_sessions(root):
    c = _c(); c.repo(root)
    c.run_record(root, "gone", {"status": "done"})
    with open(os.path.join(root, ".git", "loop", "session-pool.json"), "w") as handle:
        json.dump({"s1": {"name": "worker · gone", "slug": "gone", "state": "busy"}}, handle)


CONTROLS = {"private": ("security", "private", f_private), "scan-hook": ("security", "scan-hook", f_scan_hook),
            "workflow-permissions": ("security", "workflow-permissions", f_workflow_permissions),
            "skill-lines": ("size", "skill-lines", f_skill_lines),
            "requirements-per-page": ("size", "requirements-per-page", f_requirements_per_page),
            "check-time": ("performance", "check-time", f_check_time),
            "idle-sessions": ("hygiene", "idle-sessions", f_idle_sessions)}
