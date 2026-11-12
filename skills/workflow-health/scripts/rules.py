"""Freshness, Tests and Adoption rules (report.py). Read-only; dates are days, so two runs on one day print the same lines.

  nightly           the newest recorded nightly run is older than a day (WARN; INFO when no nightly row exists)
  unreleased        commits after the newest v* tag, the oldest over 3 days old (WARN; INFO with no tag)
  finding-age       an open health issue older than 30 days (WARN; INFO when gh is not available here)
  skipped           a row recorded SKIPPED for over 7 days (WARN), from .loop/regression-runs.tsv
  network           a land row whose command reaches the network: curl, wget, http:// or https:// (WARN; fakegh is fine)
  config            .loop/config.json does not parse, or has no base (FAIL)
  checks-run-tests  the regression workflow exists but no land row does (WARN)
  template-version  VERSION is not the newest CHANGELOG heading (WARN; INFO when either is missing); or the repo's template_version
                    is missing or older than the installed template (WARN: run the migrate goal)
  scheduled         the regression or health workflow is missing, or has no schedule (WARN)
  no-fit            an open [adoption] line in .loop/findings.md, written by setup: one WARN row each (report.py)
  agent-tools       agent_command (or the flow file's command) grants its agent no tools (WARN) (report.py)
Security and privacy, Size, Performance check-time and Hygiene idle-sessions rules (also read-only):
  private                tracked files matching a leak pattern (leak_patterns in the private flow file): FAIL with
                         file:line and the pattern's number only, never the matched text; INFO with no pattern set
  scan-hook              no commit scan hook (core.hooksPath or hooks/pre-commit): WARN; INFO in CI, where it can't be
  workflow-permissions   a workflow with no top-level permissions: (WARN)
  skill-lines            a SKILL.md of 150 lines or more (FAIL)
  requirements-per-page  a page with more requirements than criteria_max (default 6) (FAIL)
  check-time             the check, up to its Performance group, past 60 seconds (WARN; no number on a pass)
  idle-sessions          a busy worker session whose goal has ended (WARN; INFO with no session pool)
"""
import datetime
import glob
import json
import os
import re
import subprocess
import sys
import time

import issues as IS
import report as _report
from defects import LINE, behind, pages, row, table


# No terminal, no waiting: a prompt from git or gh must fail, not block.
os.environ.update(GIT_TERMINAL_PROMPT="0", GH_PROMPT_DISABLED="1", GIT_EDITOR="true", GIT_ASKPASS="true", SSH_ASKPASS="true")



def today():
    return datetime.date.today()


def days_since(text):
    try:
        return (today() - datetime.date.fromisoformat(str(text)[:10])).days
    except ValueError:
        return None


def last_runs(root):
    """{row id: (status, date)} from .loop/regression-runs.tsv."""
    out = {}
    try:
        with open(os.path.join(root, ".loop", "regression-runs.tsv")) as handle:
            for line in handle:
                cells = line.rstrip("\n").split("\t")
                if line.strip() and not line.startswith("#") and len(cells) >= 3:
                    out[cells[0]] = (cells[1], cells[2])
    except OSError:
        pass
    return out


def nightly(root):
    ids = [item["id"] for item in table(root) if item["level"] == "nightly"]
    if not ids:
        return [row("INFO", "freshness", "nightly", "nightly", "no nightly rows")]
    runs = last_runs(root)
    dates = [runs[key][1] for key in ids if key in runs]
    newest = max(dates) if dates else ""
    age = days_since(newest) if newest else None
    if age is None or age > 1:
        return [row("WARN", "freshness", "nightly", "nightly", "the newest nightly run is %s" % (newest or "missing"),
                    "check that the nightly workflow runs", "nightly")]
    return []


def git(root, *args):
    done = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True)
    return done.stdout.strip() if done.returncode == 0 else ""


def unreleased(root):
    tag = git(root, "describe", "--tags", "--abbrev=0", "--match", "v*")
    if not tag:
        return [row("INFO", "freshness", "release", "unreleased", "no v* release tag")]
    dates = git(root, "log", "--format=%cs", "--reverse", tag + "..HEAD").splitlines()
    age = days_since(dates[0]) if dates else None
    if age is not None and age > 3:
        return [row("WARN", "freshness", tag, "unreleased", "%d commits since %s, the oldest from %s" % (len(dates), tag, dates[0]),
                    "cut a release (workflow-release)", tag)]
    return []


def finding_age(root):
    found, why = IS.fetch(root)
    if found is None:
        return [row("INFO", "freshness", "findings", "finding-age", why)]
    return [row("WARN", "freshness", "#%d" % i["number"], "finding-age", "open since %s" % str(i.get("created_at"))[:10],
                "fix it or close it with triage", "#%d" % i["number"])
            for i in found if i.get("state") == "open" and IS.is_health(i) and (days_since(i.get("created_at")) or 0) > 30]


def skipped(root):
    return [row("WARN", "tests", key, "skipped", "skipped since %s" % date, "make it run again, or retire it", key)
            for key, (status, date) in sorted(last_runs(root).items())
            if status == "SKIPPED" and (days_since(date) or 0) > 7]


def network(root):
    hits = re.compile(r"\b(curl|wget)\s|https?://")
    return [row("WARN", "tests", item["id"], "network", "its command reaches the network", "use a stand-in (dev/toy/fakegh)", item["id"])
            for item in table(root) if item["level"] == "land" and hits.search(item["command"]) and "fakegh" not in item["command"]]


def config(root):
    path = os.path.join(root, ".loop", "config.json")
    try:
        with open(path) as handle:
            found = json.load(handle)
    except (OSError, ValueError) as error:
        return [row("FAIL", "adoption", ".loop/config.json", "config", "can't be read: %s" % str(error)[:80], "fix the JSON")]
    if not isinstance(found, dict) or not found.get("base"):
        return [row("FAIL", "adoption", ".loop/config.json", "config", "has no base branch", "set base (workflow-setup)")]
    return []


def checks_run_tests(root):
    if not os.path.exists(os.path.join(root, ".github", "workflows", "regression.yml")):
        return []
    if not any(item["level"] == "land" for item in table(root)):
        return [row("WARN", "adoption", "regression.yml", "checks-run-tests", "the regression workflow has no land row to run",
                    "add a land row (regression.py add)", "regression.yml")]
    return []


def template_version(root):
    try:
        version = open(os.path.join(root, "VERSION")).read().strip()
        head = re.search(r"^## v(\S+)", open(os.path.join(root, "CHANGELOG.md")).read(), re.M)
    except OSError:
        return [row("INFO", "adoption", "VERSION", "template-version", "no VERSION or CHANGELOG.md")]
    if head and head.group(1) != version:
        return [row("WARN", "adoption", "VERSION", "template-version", "VERSION %s, newest CHANGELOG heading v%s" % (version, head.group(1)),
                    "release again, or fix VERSION", "VERSION")]
    return []


def scheduled(root):
    """The regression workflow must be scheduled unless regression_runs is mac (read from the config: no gh call); a leftover
    health.yml is a WARN, as health runs on the Mac now."""
    out, flows = [], os.path.join(root, ".github", "workflows")
    try:
        mac = json.load(open(os.path.join(root, ".loop", "config.json"))).get("regression_runs") == "mac"
    except (OSError, ValueError, AttributeError):
        mac = False
    text = open(os.path.join(flows, "regression.yml")).read() if os.path.exists(os.path.join(flows, "regression.yml")) else ""
    if "schedule:" not in text and not mac:
        out.append(row("WARN", "adoption", "regression.yml", "scheduled", "missing" if not text else "has no schedule",
                       "write it (workflow-regression workflow); setup records regression_runs, mac for a private repo", "regression.yml"))
    if os.path.exists(os.path.join(flows, "health.yml")):
        out.append(row("WARN", "adoption", "health.yml", "scheduled", "has no job: health runs on the Mac now",
                       "git rm .github/workflows/health.yml", "health.yml"))
    return out


FUNCTIONS = {"nightly": nightly, "unreleased": unreleased, "finding-age": finding_age, "skipped": skipped,
             "network": network, "config": config, "checks-run-tests": checks_run_tests,
             "template-version": lambda root: template_version(root) + behind(root), "scheduled": scheduled, "no-fit": _report.no_fit, "agent-tools": _report.agent_tools}


def _c():
    import controls
    return controls


def f_nightly(root):
    c = _c(); c.repo(root)
    c.write(root, ".loop/regression.tsv", "# id\tlevel\tcommand\nn1\tnightly\ttrue\n")
    c.write(root, ".loop/regression-runs.tsv", "# id\tstatus\tdate\nn1\tPASS\t2000-01-01\n")


def f_unreleased(root):
    c = _c(); c.repo(root)
    c.git(root, "tag", "v0.1.0")
    c.write(root, "x.txt", "later\n")
    c.commit(root, "later", date="2000-01-02T00:00:00+0000")


def f_finding_age(root):
    c = _c(); c.repo(root)
    c.write(root, ".gh.json", json.dumps([{"number": 3, "title": "old", "state": "open", "labels": ["health"],
                                          "milestone": "Health", "created_at": "2000-01-01T00:00:00Z"}]))
    os.environ["LOOP_HEALTH_GH_FIXTURE"] = os.path.join(root, ".gh.json")
    IS.CACHE.clear()


def f_skipped(root):
    c = _c(); c.repo(root)
    c.write(root, ".loop/regression-runs.tsv", "# id\tstatus\tdate\nr1\tSKIPPED\t2000-01-01\n")


def f_network(root):
    c = _c(); c.repo(root)
    c.write(root, ".loop/regression.tsv", "# id\tlevel\tcommand\nr1\tland\tcurl https://example.test\n")


def f_config(root):
    c = _c(); c.repo(root)
    c.write(root, ".loop/config.json", "{not json")


def f_checks_run_tests(root):
    c = _c(); c.repo(root)
    c.write(root, ".github/workflows/regression.yml", "on:\n  schedule: []\n")


def f_template_version(root):
    c = _c(); c.repo(root)
    c.write(root, "VERSION", "1.0.1\n")
    c.write(root, "CHANGELOG.md", "# Changelog\n\n## v1.0.0 - 2000-01-01\n")


def f_scheduled(root):
    c = _c(); c.repo(root)
    c.write(root, ".github/workflows/health.yml", "name: health\n")


CONTROLS = {"nightly": ("freshness", "nightly", f_nightly), "unreleased": ("freshness", "unreleased", f_unreleased),
            "finding-age": ("freshness", "finding-age", f_finding_age), "skipped": ("tests", "skipped", f_skipped),
            "network": ("tests", "network", f_network), "config": ("adoption", "config", f_config),
            "checks-run-tests": ("adoption", "checks-run-tests", f_checks_run_tests),
            "template-version": ("adoption", "template-version", f_template_version),
            "scheduled": ("adoption", "scheduled", f_scheduled)}




SKILL_LINES = 150
CHECK_SECONDS = 60


def git_raw(root, *args):
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
        hits = git_raw(root, "grep", "-n", "-I", "-E", "-e", pattern, "--", ".", ":(exclude).git")
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
    hooks = (git_raw(root, "config", "core.hooksPath") or "").strip()
    common = (git_raw(root, "rev-parse", "--git-common-dir") or ".git").strip()
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
        with open(path, "rb") as handle:  # LF lines, as git holds them
            count = len(handle.read().replace(b"\r\n", b"\n").splitlines())
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
    common = (git_raw(root, "rev-parse", "--git-common-dir") or ".git").strip()
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


GUARD_FUNCTIONS = {"private": private, "scan-hook": scan_hook, "workflow-permissions": workflow_permissions,
             "skill-lines": skill_lines, "requirements-per-page": requirements_per_page, "check-time": check_time,
             "idle-sessions": idle_sessions}


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


GUARD_CONTROLS = {"private": ("security", "private", f_private), "scan-hook": ("security", "scan-hook", f_scan_hook),
            "workflow-permissions": ("security", "workflow-permissions", f_workflow_permissions),
            "skill-lines": ("size", "skill-lines", f_skill_lines),
            "requirements-per-page": ("size", "requirements-per-page", f_requirements_per_page),
            "check-time": ("performance", "check-time", f_check_time),
            "idle-sessions": ("hygiene", "idle-sessions", f_idle_sessions)}
FUNCTIONS.update(GUARD_FUNCTIONS)
CONTROLS.update(GUARD_CONTROLS)
