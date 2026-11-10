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
    module = sys.modules.get("ghcache")
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
    repo(root, {"test_budget_seconds": 60})
    write(root, ".loop/regression.tsv", "# id\tlevel\tcommand\n" + "".join(
        "r%d\tland\tbash dev/toy/test-x.sh\n" % n for n in range(3)))
    commit(root, "rows")
    folder = os.path.join(root, ".git", "loop", "tests")
    os.makedirs(folder, exist_ok=True)
    rows = {"r%d" % n: {"status": "PASS", "seconds": 40, "commit": "x"} for n in range(3)}
    with open(os.path.join(folder, "main-%s.json" % hashlib.sha1(b"main").hexdigest()[:8]), "w") as handle:  # main's own
        json.dump({"at": OLD, "rows": rows}, handle)


def f_worktrees(root):
    repo(root)
    git(root, "worktree", "add", "-q", "-b", "loop/gone", os.path.join(root, ".git", "loop", "worktrees", "gone"))


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
}
for _module in ("rules_trace", "rules_fresh", "rules_guard"):
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
    kept = {k: os.environ.get(k) for k in ("LOOP_FLOW", "LOOP_HEALTH_GH_FIXTURE", "LOOP_HEALTH_T0", "CI", "GITHUB_ACTIONS")}
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
    result, kept = one(args.rule, health.rule_functions()[args.rule], HERE, keep=args.keep)
    print("%(state)s controls %(subject)s: %(detail)s" % result + (" -> fix: " + result["fix"] if result["fix"] else ""))
    if kept:
        print("KEPT " + kept)
    return 0 if result["state"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
