#!/usr/bin/env python3
# windows: ok
# reads: skills/workflow-health/scripts/health.py skills/workflow-health/scripts/enforce.py skills/workflow-health/scripts/controls.py
# reads: skills/workflow-health/scripts/report.py skills/workflow-health/scripts/rules.py skills/workflow-health/scripts/defects.py
# reads: skills/workflow-setup/scripts/settings.py
"""HLT repo rules: a repo extends health with .loop/health-rules.json, sets default thresholds and turns a default rule off.

Each case builds a throwaway git repo, writes the repo's own rules and runs the real health.py (and settings.py) on it:
run (rows land in their group with their feature), control (a rule's break makes Controls see it fail), refuse (a rule with
no break exits 2), off (a default turned off shows its reason, one without a reason stays on and is UNREAD), threshold
(health_script_bytes), setup (fill-repo writes the file once and keeps an edited one). usage: test-health-repo-rules.py [CASE ...] [--break]
CASE is one of run, control, refuse, off, threshold or setup (default all). --break leaves the rules file out of every repo, to see the rows red."""
import json
import os
import subprocess
import sys
import tempfile

here = os.path.dirname(os.path.abspath(__file__))
root = os.path.abspath(os.path.join(here, "..", ".."))
health = os.path.join(root, "skills", "workflow-health", "scripts", "health.py")
settings = os.path.join(root, "skills", "workflow-setup", "scripts", "settings.py")
breaking = "--break" in sys.argv
cases = [a for a in sys.argv[1:] if not a.startswith("--")]
run_it = lambda name: not cases or name in cases
py = sys.executable
failed = []
ENV = dict(os.environ, GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1", GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.invalid",
           GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.invalid", LOOP_HEALTH=os.devnull, HOME=tempfile.gettempdir())


def check(ok, text):
    print(("PASS: " if ok else "FAIL: ") + text)
    if not ok:
        failed.append(text)


def sh(args, cwd):
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True, env=ENV, timeout=300)


def repo(folder, rules=None, off=None, config=None, scripts=None):
    sh(["git", "init", "-q", "-b", "main"], folder)
    for rel, text in {".loop/config.json": json.dumps(dict({"base": "main"}, **(config or {}))),
                      ".loop/regression.tsv": "# id\tlevel\tcommand\n", "flag": "1"}.items():
        os.makedirs(os.path.dirname(os.path.join(folder, rel)), exist_ok=True)
        with open(os.path.join(folder, rel), "w") as handle:
            handle.write(text)
    for rel, size in (scripts or {}).items():
        os.makedirs(os.path.dirname(os.path.join(folder, rel)), exist_ok=True)
        with open(os.path.join(folder, rel), "w") as handle:
            handle.write("#" * size + "\n")
    if (rules is not None or off is not None) and not breaking:
        with open(os.path.join(folder, ".loop", "health-rules.json"), "w") as handle:
            json.dump({"rules": rules or [], "off": off or {}}, handle)
    sh(["git", "add", "-A"], folder)
    sh(["git", "commit", "-q", "-m", "toy"], folder)


def words(code):
    return [py, "-c", code]


def rule(name, group, code, brk="pass", **more):
    return dict({"name": name, "group": group, "command": words(code), "fix": "fix " + name, "break": words(brk)}, **more)


def rows(folder, groups):
    done = sh([py, health, "check", "--json", "--group", groups], folder)
    try:
        return json.loads(done.stdout)["rows"], done
    except ValueError:
        return [], done


def find(found, name):
    return next((r for r in found if r["subject"] == name or r["rule"] == name), None)


with tempfile.TemporaryDirectory() as tmp:
    if run_it('run'):
        # run: one rule per state, in a default group and in the repo group, each with its feature
        a = os.path.join(tmp, "a")
        os.makedirs(a)
        repo(a, [rule("r-pass", "docs", "print('fine')", feature="Docs"), rule("r-warn", "repo", "import sys;sys.exit(2)", feature="Health"),
                 rule("r-fail", "size", "import sys;sys.exit(1)", feature="Health"), rule("r-unread", "hygiene", "import sys;sys.exit(7)")])
        found, _ = rows(a, "docs,size,hygiene,repo")
        got = {n: find(found, n) for n in ("r-pass", "r-warn", "r-fail", "r-unread")}
        check(all(got.values()) and [(got[n]["state"], got[n]["family"]) for n in got] ==
              [("PASS", "docs"), ("WARN", "repo"), ("FAIL", "size"), ("UNREAD", "hygiene")],
              "a repo rule runs in the report with its group and its exit as PASS, WARN, FAIL or UNREAD")
        check(bool(got["r-warn"]) and got["r-warn"].get("feature") == "Health" and got["r-pass"].get("feature") == "Docs",
              "a repo rule's row carries its feature")
    if run_it('control'):
        # control: the break runs on a copy, and the control fires only when the command then fails
        b = os.path.join(tmp, "b")
        os.makedirs(b)
        repo(b, [rule("works", "repo", "import os,sys;sys.exit(0 if os.path.exists('flag') else 1)", "import os;os.remove('flag')"),
                 rule("noop", "repo", "print('ok')", "pass")])
        found, _ = rows(b, "controls")
        works, noop = find(found, "works"), find(found, "noop")
        check(bool(works) and works["state"] == "PASS" and bool(noop) and noop["state"] == "FAIL" and "cannot fire" in noop["detail"],
              "a rule whose break makes it fail passes its control; one whose break changes nothing is reported as unable to fire")
        check(os.path.exists(os.path.join(b, "flag")), "the break ran on a copy: the repo's own files are untouched")
    if run_it('refuse'):
        # refuse: no break
        c = os.path.join(tmp, "c")
        os.makedirs(c)
        repo(c, [dict(rule("nobreak", "repo", "pass"), **{"break": None})])
        done = sh([py, health, "check", "--group", "repo"], c)
        check(done.returncode == 2 and "nobreak" in done.stdout and "no break command" in done.stdout,
              "a repo rule with no break makes health refuse (exit 2) naming the rule")
    if run_it('off'):
        # off: a default turned off shows its reason; an empty reason leaves the rule on and is UNREAD
        d = os.path.join(tmp, "d")
        os.makedirs(d)
        repo(d, [], off={"hooks": "CI runs no git hooks", "scripts": ""})
        found, _ = rows(d, "security,size,repo")
        off = find(found, "hooks")
        check(bool(off) and off["state"] == "INFO" and off["family"] == "security" and "turned off: CI runs no git hooks" in off["detail"],
              "a default rule turned off prints its reason in its own group")
        bare = find(found, "scripts")
        check(any(r["state"] == "UNREAD" and r["subject"] == "scripts" and r["family"] == "repo" for r in found) and bool(bare) and bare["family"] == "size",
              "a default turned off with no reason stays on and is reported UNREAD")
    if run_it('threshold'):
        # threshold: health_script_bytes
        e1, e2 = os.path.join(tmp, "e1"), os.path.join(tmp, "e2")
        for e, config in ((e1, None), (e2, {"health_script_bytes": 2000})):
            os.makedirs(e)
            repo(e, config=config, scripts={"skills/x/scripts/big.py": 3000})
        one, two = find(rows(e1, "size")[0], "scripts"), [r for r in rows(e2, "size")[0] if r["rule"] == "scripts" and r["state"] == "FAIL"]
        check(bool(one) and one["state"] == "PASS" and bool(two) and "over 2000" in two[0]["detail"],
              "health_script_bytes in config.json lowers the script cap for that repo, the default leaves it at 20480")
    if run_it('setup'):
        # setup: fill-repo writes the file once and keeps an edited one
        f = os.path.join(tmp, "f")
        os.makedirs(f)
        repo(f)
        sh([py, settings, "fill-repo", "--repo", f], f)
        target = os.path.join(f, ".loop", "health-rules.json")
        first = json.load(open(target)) if os.path.exists(target) else {}
        with open(target, "w") as handle:
            json.dump({"rules": [], "off": {"hooks": "kept"}}, handle)
        sh([py, settings, "fill-repo", "--repo", f], f)
        check(first.get("rules") == [] and first.get("off") == {} and "_comment" in first and json.load(open(target))["off"] == {"hooks": "kept"},
              "setup writes an empty commented .loop/health-rules.json once and keeps an edited one")
        check(json.load(open(os.path.join(f, ".loop", "config.json"))).get("health_script_bytes") == 20480,
              "setup fills the health_script_bytes and health_skill_lines settings with their defaults")

print("ALL PASS" if not failed else "%d FAILED" % len(failed))
sys.exit(1 if failed else 0)
