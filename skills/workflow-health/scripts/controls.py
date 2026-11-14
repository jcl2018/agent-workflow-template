#!/usr/bin/env python3
"""Negative controls: each health rule has a small fixture that must make it report a finding.

usage: controls.py run RULE [--keep]   run one control and print its result (--keep keeps the fixture and prints its path)

health.py passes its rule functions to run(): every control builds a throwaway git repo in a private temporary folder,
the one file or record that breaks its rule, and calls the real rule on it. The control fires only when that rule
reports a WARN or FAIL row of its own group and rule (report.py's rule_of), never an UNREAD row or a sibling rule's.
A rule whose control stays green is reported as a rule that cannot fire. Git runs with no inherited GIT_DIR, no global
or system config and a fixed identity, so no hook, signing or setting applies and the real repo is never touched.
Rows carry no temporary path and no time, so two runs print the same lines. run() imports nothing from health.py;
only the run command line loads it, for its rule functions.
"""
import hashlib
import importlib
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(sys.argv[0]))
GIT_ENV = {"GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1", "GIT_AUTHOR_NAME": "health-control",
           "GIT_AUTHOR_EMAIL": "health-control@example.invalid", "GIT_COMMITTER_NAME": "health-control",
           "GIT_COMMITTER_EMAIL": "health-control@example.invalid", "GIT_TERMINAL_PROMPT": "0"}
OLD = "2026-01-01T00:00:00Z"


class Leaked(Exception):
    """A row showed text a control planted as private."""


def clear_cache():
    module = sys.modules.get("issues")
    if module:
        module.CACHE.clear()


class Unbuilt(Exception):
    """A fixture could not be built: the command, its exit code and the last line it printed on stderr."""


def env(extra=None):
    out = {k: v for k, v in os.environ.items() if not k.startswith("GIT_") or k in ("GIT_TERMINAL_PROMPT",)}
    out.update(GIT_ENV)
    out.update(extra or {})
    return out


def git(root, *args, extra=None):
    done = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, env=env(extra))
    if done.returncode:
        last = (done.stderr.strip().splitlines() or ["no stderr"])[-1]
        raise Unbuilt("git %s exited %d: %s" % (" ".join(args[:3]), done.returncode, last[:100]))
    return done.stdout


def write(root, rel, text):
    path = os.path.join(root, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as handle:
        handle.write(text)


def repo(root, config=None):
    """A repo on main with one commit, a .loop/config.json and an empty regression table."""
    git(root, "init", "-q", "-b", "main")
    write(root, ".loop/config.json", json.dumps(dict({"base": "main", "wiki_dir": "docs/wiki"}, **(config or {}))))
    write(root, ".loop/regression.tsv", "# id\tlevel\tcommand\tgoal\tseen_red\tdescription\tcategory\tlink\n")
    write(root, "README.md", "toy\n")
    commit(root, "toy")


def commit(root, message, date=None):
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", message, extra={"GIT_COMMITTER_DATE": date, "GIT_AUTHOR_DATE": date} if date else None)


def runs_dir(root):
    path = os.path.join(root, ".git", "loop", "runs")
    os.makedirs(path, exist_ok=True)
    return path


def run_record(root, slug, state):
    with open(os.path.join(runs_dir(root), slug + ".json"), "w") as handle:
        json.dump(dict({"slug": slug}, **state), handle)


# Each fixture builds the smallest repo that must make its rule fire.
def f_size(root):
    repo(root)
    write(root, "skills/x/scripts/big.py", "# pad\n" * 3600)


def f_criteria_rows(root):
    repo(root)
    write(root, "docs/wiki/Calc.md", "# Calc\n\n## Requirements\n\n- CAL-1: **Unreviewed** calc adds.\n")


def f_criteria_done(root):
    repo(root)
    write(root, ".loop/goals/old.md", "# Old\n\n## Done lines\n\nFrozen.\n\n1. Calc adds.\n\n## Design\n")
    write(root, ".git/loop/runs/old.json", '{"status": "running"}')  # done lines count while the goal runs


def f_defect_tests(root):
    repo(root)
    write(root, ".loop/findings.md", "# Findings\n\n- old-bug: it broke [closed]\n")


def f_docs_check(root):
    repo(root)
    write(root, ".loop/docs.tsv", "Ghost\tghost.py\n")
    commit(root, "map a page that is missing")


def f_findings(root):
    repo(root)
    write(root, ".loop/findings.md", "# Findings\n\n" + "".join("- f%d: open\n" % n for n in range(6)))


def f_waiting(root):
    repo(root)
    run_record(root, "stuck", {"status": "waiting", "updated": OLD, "log": [OLD + " waiting"]})


def f_branches(root):
    repo(root)
    git(root, "branch", "loop/old")


def f_cost(root):
    repo(root, {"time_budget_minutes": 1})
    run_record(root, "slow", {"status": "done", "updated": OLD, "tokens": {"build": 10},
                              "log": ["2026-01-01T00:00:00Z queued", "2026-01-01T02:00:00Z build"]})


def f_test_time(root):
    repo(root, {"test_budget_minutes": 15})
    write(root, ".loop/regression.tsv", "# id\tlevel\tcommand\n" + "".join(
        "r%d\tland\tbash dev/toy/test-x.sh\n" % n for n in range(3)))
    commit(root, "rows")
    folder = os.path.join(root, ".git", "loop", "tests")
    os.makedirs(folder, exist_ok=True)
    rows = {"r%d" % n: {"status": "PASS", "seconds": 400, "commit": "x"} for n in range(3)}
    with open(os.path.join(folder, "main-%s.json" % hashlib.sha1(b"main").hexdigest()[:8]), "w") as handle:  # main's own
        json.dump({"at": OLD, "rows": rows}, handle)


def f_worktrees(root):
    repo(root)
    git(root, "worktree", "add", "-q", "-b", "loop/gone", os.path.join(root, ".git", "loop", "worktrees", "gone"))


def f_prompt_pointer(root):
    repo(root)
    write(root, ".loop/config.json", '{"base": "main", "automation": [{"name": "digest", "runs": "claude:t1"}]}')
    write(root, "tasks/t1/SKILL.md", "---" + "\n" + "name: t1" + "\n" + "---" + "\n" + "Run the digest steps: 1. fetch, 2. mail." + "\n")
    os.environ["LOOP_SCHEDULED_TASKS_DIR"] = os.path.join(root, "tasks")


def f_hooks(root):
    """A repo with no hooks; the environment makes it fire on Actions and never read the real HOME or list."""
    repo(root)
    folder = os.path.dirname(root)
    write(folder, "list", "# a control\nzq-control\n")
    os.environ.update(LOOP_HEALTH_HOOKS="1", HOME=folder, LOOP_PRIVATE_NAMES=os.path.join(folder, "list"))


def f_local_branches(root):
    repo(root)
    git(root, "checkout", "-q", "-b", "side")
    write(root, "side.txt", "only here\n")
    commit(root, "only here", date="2026-01-01T00:00:00+0000")
    git(root, "checkout", "-q", "main")


def f_proof(root):
    repo(root)
    write(root, ".loop/regression.tsv", "# id\tlevel\tcommand\tgoal\tseen_red\tdescription\tcategory\tlink\n"
          "d1\tdraft\techo write a test\t-\t-\ta draft\tcriterion\t\n")


def f_seen_red(root):
    repo(root)
    write(root, ".loop/regression.tsv", "# id\tlevel\tcommand\tgoal\tseen_red\tdescription\tcategory\tlink\n"
          "r1\tland\ttrue\t-\t-\tnever red\tcriterion\t\n")


def f_no_fit(root):
    repo(root)
    write(root, ".loop/findings.md", "# Findings\n\n- [adoption] own-sections: docs/wiki/A.md. Fix: add the contract sections by hand\n")


def f_matrix(root):
    repo(root)
    write(root, ".loop/matrix-runs.tsv", "# date\tagent\tos\tmachine\tcommit\tresult\n")


def f_agent_tools(root):
    repo(root)
    write(root, ".loop/config.json", '{"base": "main", "agent_command": ["claude", "-p"]}\n')
    os.environ["LOOP_FLOW"] = os.path.join(root, "no-flow.json")


def f_nightly(root):
    repo(root)
    write(root, ".loop/regression.tsv", "# id\tlevel\tcommand\nn1\tnightly\ttrue\n")
    write(root, ".loop/regression-runs.tsv", "# id\tstatus\tdate\nn1\tPASS\t2000-01-01\n")


def f_unreleased(root):
    repo(root)
    git(root, "tag", "v0.1.0")
    write(root, "x.txt", "later\n")
    commit(root, "later", date="2000-01-02T00:00:00+0000")


def f_finding_age(root):
    repo(root)
    write(root, ".gh.json", json.dumps([{"number": 3, "title": "old", "state": "open", "labels": ["health"],
                                          "milestone": "Health", "created_at": "2000-01-01T00:00:00Z"}]))
    os.environ["LOOP_HEALTH_GH_FIXTURE"] = os.path.join(root, ".gh.json")
    clear_cache()


def f_skipped(root):
    repo(root)
    write(root, ".loop/regression-runs.tsv", "# id\tstatus\tdate\nr1\tSKIPPED\t2000-01-01\n")


def f_network(root):
    repo(root)
    write(root, ".loop/regression.tsv", "# id\tlevel\tcommand\nr1\tland\tcurl https://example.test\n")


def f_config(root):
    repo(root)
    write(root, ".loop/config.json", "{not json")


def f_checks_run_tests(root):
    repo(root)
    write(root, ".github/workflows/regression.yml", "on:\n  schedule: []\n")


def f_template_version(root):
    repo(root)
    write(root, "VERSION", "1.0.1\n")
    write(root, "CHANGELOG.md", "# Changelog\n\n## v1.0.0 - 2000-01-01\n")


def f_scheduled(root):
    repo(root)
    write(root, ".github/workflows/health.yml", "name: health\n")


def f_milestones(root):
    repo(root)
    write(root, ".loop/docs.tsv", "A\tsrc\n")
    git(root, "remote", "add", "origin", "https://github.com/o/r.git")
    os.environ["LOOP_BACKLOG_MILESTONES"] = "[]"


def f_private(root):
    repo(root)
    write(root, "flow.json", json.dumps({"leak_patterns": ["PLANTED-SECRET-[0-9]+"]}))
    os.environ["LOOP_FLOW"] = os.path.join(root, "flow.json")
    write(root, "notes.txt", "see PLANTED-SECRET-42\n")
    commit(root, "plant")


def f_scan_hook(root):
    repo(root)
    os.environ.pop("CI", None); os.environ.pop("GITHUB_ACTIONS", None)


def f_workflow_permissions(root):
    repo(root)
    write(root, ".github/workflows/x.yml", "on: push\njobs: {}\n")


def f_skill_lines(root):
    repo(root)
    write(root, "skills/x/SKILL.md", "line\n" * 150)


def f_requirements_per_page(root):
    repo(root, {"criteria_max": 1})
    write(root, "docs/wiki/One.md", "# One\n\n## Requirements\n\n- AB-1: **Unreviewed** a.\n- AB-2: **Unreviewed** b.\n")


def f_check_time(root):
    repo(root)
    os.environ["LOOP_HEALTH_T0"] = "1"


def f_idle_sessions(root):
    repo(root)
    run_record(root, "gone", {"status": "done"})
    with open(os.path.join(root, ".git", "loop", "session-pool.json"), "w") as handle:
        json.dump({"s1": {"name": "worker · gone", "slug": "gone", "state": "busy"}}, handle)


# rule name in groups.RULES -> (group, the rule groups.rule_of gives its rows, fixture); the rule modules add theirs
CONTROLS = {
    "scripts": ("size", "scripts", f_size),
    "rows": ("requirements", "rows", f_criteria_rows),
    "proof": ("requirements", "proof", f_proof),
    "done": ("requirements", "done", f_criteria_done),
    "seen-red": ("tests", "seen-red", f_seen_red),
    "defect-tests": ("traceability", "defect-tests", f_defect_tests),
    "docs-check": ("docs", "docs-check", f_docs_check),
    "findings": ("hygiene", "findings", f_findings),
    "waiting": ("hygiene", "waiting", f_waiting),
    "branches": ("hygiene", "branches", f_branches),
    "cost": ("performance", "cost", f_cost),
    "test-time": ("performance", "test-time", f_test_time),
    "worktrees": ("hygiene", "worktrees", f_worktrees),
    "local-branches": ("hygiene", "local-branches", f_local_branches),
    "hooks": ("security", "hooks", f_hooks),
    "no-fit": ("adoption", "no-fit", f_no_fit),
    "agent-tools": ("adoption", "agent-tools", f_agent_tools),
    "matrix": ("adoption", "matrix", f_matrix),
    "nightly": ("freshness", "nightly", f_nightly), "unreleased": ("freshness", "unreleased", f_unreleased),
    "finding-age": ("freshness", "finding-age", f_finding_age), "skipped": ("tests", "skipped", f_skipped),
    "network": ("tests", "network", f_network), "config": ("adoption", "config", f_config),
    "checks-run-tests": ("adoption", "checks-run-tests", f_checks_run_tests),
    "template-version": ("adoption", "template-version", f_template_version),
    "scheduled": ("adoption", "scheduled", f_scheduled), "milestones": ("adoption", "milestones", f_milestones),
    "prompt-pointer": ("adoption", "prompt-pointer", f_prompt_pointer),
    "private": ("security", "private", f_private), "scan-hook": ("security", "scan-hook", f_scan_hook),
    "workflow-permissions": ("security", "workflow-permissions", f_workflow_permissions),
    "skill-lines": ("size", "skill-lines", f_skill_lines),
    "requirements-per-page": ("size", "requirements-per-page", f_requirements_per_page),
    "check-time": ("performance", "check-time", f_check_time),
    "idle-sessions": ("hygiene", "idle-sessions", f_idle_sessions),
}
for _module in ("defects",):
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    try:
        CONTROLS.update(importlib.import_module(_module).CONTROLS)
    except ImportError:
        pass
    finally:
        sys.path.pop(0)
LEAK = "PLANTED-SECRET"  # the private rule's control plants this text; no row may show it


def label(item, here):
    sys.path.insert(0, here)
    try:
        import report
        return report.rule_of(item)
    except ImportError:
        raise Unbuilt("report.py is not installed beside controls.py")
    finally:
        sys.path.pop(0)


def row(state, rule, detail, fix=""):
    return {"state": state, "family": "controls", "subject": rule, "rule": "control", "detail": detail, "fix": fix}


def one(rule, function, here, keep=False):
    """(row, kept path or ''): run one control through the real rule function."""
    group, wanted, fixture = CONTROLS[rule]
    folder = tempfile.mkdtemp(prefix="health-control-")
    root = os.path.join(folder, "repo")
    os.makedirs(root)
    saved = {k: os.environ.pop(k) for k in list(os.environ) if k.startswith("GIT_")}  # all restored in finally
    kept = {k: os.environ.get(k) for k in ("LOOP_FLOW", "LOOP_HEALTH_GH_FIXTURE", "LOOP_HEALTH_T0", "CI", "GITHUB_ACTIONS", "LOOP_HEALTH_HOOKS", "HOME", "LOOP_PRIVATE_NAMES", "LOOP_SCHEDULED_TASKS_DIR")}
    os.environ.pop("LOOP_HEALTH_GH_FIXTURE", None)
    os.environ.pop("LOOP_HEALTH_T0", None)
    clear_cache()
    os.environ.update(GIT_ENV)
    try:
        fixture(root)
        found = function(root)
        fired = any(item["state"] in ("WARN", "FAIL") and item["family"] == group and label(item, here) == wanted
                    for item in found)
        if any(LEAK in "%s %s %s" % (i.get("subject"), i.get("detail"), i.get("evidence")) for i in found):
            raise Leaked()
        mine = [item for item in found if item["family"] == group]
        blind = mine and all(item["state"] == "UNREAD" for item in mine)
        result = row("PASS", rule, "fires on its fixture") if fired else row(
            "UNREAD", rule, "its rule could not read its data on the fixture", "install the skills it reads beside it") if blind else row(
            "FAIL", rule, "cannot fire: it reported nothing on a fixture made to break it",
            "run: python3 controls.py run %s --keep, then fix the rule or its control" % rule)
    except Leaked:
        result = row("FAIL", rule, "a row shows the matched private text", "show file:line and the pattern number only")
    except Unbuilt as error:
        result = row("UNREAD", rule, "the control could not build its fixture: %s" % str(error).replace(os.path.realpath(folder), "<fixture>").replace(folder, "<fixture>"),
                     "run: python3 controls.py run %s --keep" % rule)
    except Exception as error:  # one broken control is UNREAD, never a crash of the whole check
        result = row("UNREAD", rule, "the control stopped with %s" % type(error).__name__, "run: python3 controls.py run %s --keep" % rule)
    finally:
        for key in GIT_ENV:
            os.environ.pop(key, None)
        os.environ.update(saved)
        for key, value in kept.items():
            os.environ.pop(key, None)
            if value is not None:
                os.environ[key] = value
        clear_cache()
        if not keep:
            subprocess.run(["rm", "-rf", folder], capture_output=True)
            if os.path.exists(folder):
                result = row("UNREAD", rule, "could not remove its temporary fixture", "remove the health-control-* folder")
    return result, (root if keep else "")


def run(rules, here):
    """One controls row per rule, in the order of rules (a dict: rule name -> function(root) -> rows)."""
    return [one(rule, function, here)[0] for rule, function in rules.items()]


def repo_control(root, rule):
    """The Controls row for one repo rule (.loop/health-rules.json): its break runs on a private copy of the repo's files,
    tracked and new, then its command runs there, and it must exit 1 or 2. The real repo is never touched."""
    name, folder = rule["name"], tempfile.mkdtemp(prefix="health-control-")
    copy, fix = os.path.join(folder, "repo"), "fix the rule's break in .loop/health-rules.json"
    try:
        os.makedirs(copy)
        for rel in filter(None, git(root, "ls-files", "-z", "--cached", "--others", "--exclude-standard").split("\0")):
            if os.path.isfile(os.path.join(root, rel)):
                os.makedirs(os.path.dirname(os.path.join(copy, rel)), exist_ok=True)
                shutil.copy2(os.path.join(root, rel), os.path.join(copy, rel))
        broke = subprocess.run(rule["break"], cwd=copy, capture_output=True, text=True, timeout=120)
        if broke.returncode:
            return row("UNREAD", name, "its break command exited %d" % broke.returncode, fix)
        code = subprocess.run(rule["command"], cwd=copy, capture_output=True, text=True, timeout=int(rule.get("timeout") or 120)).returncode
    except (OSError, ValueError, Unbuilt, subprocess.SubprocessError) as error:
        return row("UNREAD", name, "the control could not run: %s" % type(error).__name__, fix)
    finally:
        shutil.rmtree(folder, ignore_errors=True)
    if code in (1, 2):
        return row("PASS", name, "fires on its fixture")
    if code:
        return row("UNREAD", name, "its command exited %d after the break, not 1 or 2" % code, fix)
    return row("FAIL", name, "cannot fire: it passed after its break command", fix)


def repo_controls(root):
    """One Controls row per repo rule (.loop/health-rules.json)."""
    import enforce
    return [repo_control(root, rule) for rule in enforce.repo_load(root)[0]]


def refuse_repo():
    """Exit 2 before any report when a repo rule has no break, no known group or no name of its own."""
    import enforce
    top = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    problems = enforce.repo_load(top.stdout.strip())[2] if not top.returncode else []
    if problems:
        print("REFUSED: " + problems[0])
        sys.exit(2)


def missing(names):
    return [name for name in names if name not in CONTROLS]


def refuse(names):
    """Exit 2 before any report when a rule has no negative control."""
    gap = missing(names)
    if gap:
        print("REFUSED: rule %s has no negative control. Fix: add CONTROLS[\"%s\"] in controls.py" % (", ".join(gap), gap[0]))
        sys.exit(2)


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    item = sub.add_parser("run")
    item.add_argument("rule", choices=sorted(CONTROLS))
    item.add_argument("--keep", action="store_true")
    args = parser.parse_args()
    sys.path.insert(0, HERE)
    import health
    functions = health.rule_functions()
    result, kept = one(args.rule, functions[args.rule], HERE, keep=args.keep)
    print("%(state)s controls %(subject)s: %(detail)s" % result + (" -> fix: " + result["fix"] if result["fix"] else ""))
    if kept:
        print("KEPT " + kept)
    return 0 if result["state"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
