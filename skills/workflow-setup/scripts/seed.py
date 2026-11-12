#!/usr/bin/env python3
"""Plan and write the rest of an adoption: feature pages, criteria, regression rows and workflow.

usage: seed.py [--repo DIR]     (setup.py imports this; run alone it prints the plan)

Every decision is add (new file), convert (an existing page gets the marker and the missing sections, its words untouched),
skip (already done) or no fit (left alone, for a person). It calls the sibling docs and regression scripts, which own
those file formats, and runs git and nothing else.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys

import survey

# No terminal, no waiting: a prompt from git or gh must fail, not block.
os.environ.update(GIT_TERMINAL_PROMPT="0", GH_PROMPT_DISABLED="1", GIT_EDITOR="true", GIT_ASKPASS="true", SSH_ASKPASS="true")
if not sys.stdin or not sys.stdin.isatty():
    os.dup2(os.open(os.devnull, os.O_RDONLY), 0)

HERE = os.path.dirname(os.path.abspath(__file__))
PLACEHOLDER = "Write this page from what is really in the repo."
CRITERION = re.compile(r"[A-Z]{2,5}(?=-\d+:)")


MARK = "workflow-loop-hook"
# hook -> the `private.py hook` lines its stub runs, in order; the pre-push stub reads git's ref lines once and feeds each line
GUARD = {"pre-commit": ["staged"], "commit-msg": ['message "$1"'], "pre-push": ["push"]}
STUB = """#!/bin/sh
# %(mark)s: %(name)s (python3 '%(setup)s' --git-hooks writes it; --git-hooks --remove takes it out)
P='%(py)s' S='%(priv)s' U='%(setup)s'
fix() { echo "%(name)s hook: $1. Fix: python3 '$U' --git-hooks (to skip once, git's own --no-verify is yours to decide)" >&2; exit 1; }
[ -x "$P" ] || P=$(command -v python3) || fix "python3 is not on PATH, so the private-name scan cannot run"
[ -f "$S" ] || fix "private.py is gone (the skills moved?)"
run() { "$P" "$S" hook "$@"; case $? in 0) ;; 1|2) exit 1;; 142) echo "%(name)s hook: the scan took too long and was killed: a pattern in the private-name list is too slow" >&2; exit 1;; 64) fix "the hook is wired wrong";; *) fix "the scan failed unexpectedly";; esac; }
%(body)s"""
READ = 'T=$(mktemp) || fix "no temp file"; trap \'rm -f "$T"\' EXIT; cat > "$T"\n'


def stub(name, py, priv, setup):
    push = name == "pre-push"
    body = (READ if push else "") + "".join("run %s%s\n" % (line, ' < "$T"' if push else "") for line in GUARD[name])
    return STUB % {"mark": MARK, "name": name, "py": py, "priv": priv, "setup": setup, "body": body}


def call_of(text):
    """The private.py path a hook's text names (ours or the owner's own call), else None."""
    found = MARK in text and re.search(r"S='([^']*)'", text) or re.search(r"([^'\"\s]*private\.py)['\"]? +hook ", text)
    return found.group(1) if found else None


def hook_state(path):
    """installed (calls an existing private.py), stale (calls one that is gone), foreign (no call) or missing."""
    try:
        with open(path, errors="replace") as handle:
            target = call_of(handle.read())
    except OSError:
        return "missing"
    return "foreign" if target is None else "installed" if os.path.exists(target) else "stale"


def hooks_dir(repo):
    """(the folder git reads hooks from, whether core.hooksPath chose it)."""
    out = lambda *a: subprocess.run(["git", "-C", repo] + list(a), capture_output=True, text=True).stdout.strip()
    custom = out("config", "--get", "core.hooksPath")
    if custom:
        return os.path.join(repo, os.path.expanduser(custom)), True
    return os.path.join(os.path.realpath(os.path.join(repo, out("rev-parse", "--git-common-dir"))), "hooks"), False


def list_state(priv):
    """(state word, private.py check's own line): the list's words, never a pattern."""
    if not priv:
        return "unknown", "PRIVATE LIST: unknown, workflow-delivery is not beside workflow-setup"
    done = subprocess.run([sys.executable, priv, "check"], capture_output=True, text=True)
    line = done.stdout.strip()
    return ("broken" if done.returncode else "none" if ": none at" in line else "off" if "off on" in line else "on"), line


def show(repo, as_json):
    """--git-hooks --check: the list and each hook, as text or schema-1 JSON. Exit 1 when a hook or the list needs a fix."""
    folder, custom = hooks_dir(repo)
    word, line = list_state(sibling("workflow-delivery", "private.py"))
    states = {name: hook_state(os.path.join(folder, name)) for name in GUARD}
    if as_json:
        print(json.dumps({"version": 1, "list": word, "list_note": line, "hooks_path": custom, "hooks": states}))
    else:
        print("list: " + line)
        print("\n".join("hook %s: %s" % pair for pair in states.items()))
        if custom:
            print("NOTE: core.hooksPath is set, so setup writes no hooks; add the call lines to the hooks you use")
    return int(word == "broken" or any(v != "installed" for v in states.values()))


def git_hooks(repo, remove=False, adopting=False):
    """Install (or remove) the stubs in the git common dir's hooks. A refusal is exit 1, or a NOTE when adopting."""
    priv, setup = sibling("workflow-delivery", "private.py"), os.path.join(HERE, "setup.py")
    folder, custom = hooks_dir(repo)
    py = shutil.which("python3") or ""

    def refuse(what, fix):
        print("%s: %s. Fix: %s" % ("NOTE" if adopting else "REFUSED", what, fix))
        return 0 if adopting else 1
    if not remove:
        priv = os.path.realpath(priv) if priv else None
        lines = "\n".join("  %s: python3 '%s' hook %s" % (n, priv, v[0]) for n, v in GUARD.items())
        if custom:
            return refuse("core.hooksPath is set, so setup writes no hooks", "add these lines to the hooks you use:\n" + lines)
        if not priv:
            return refuse("workflow-delivery (private.py) is not beside workflow-setup", "install the skills together")
        if any(ch in priv + setup + py for ch in "'\n%"):
            return refuse("a path holds a quote, newline or percent sign", "move the skills to a folder without one")
        inside = os.path.join(os.sep + "loop", "worktrees") + os.sep  # a goal's worktree goes away when the goal ends
        if inside in priv + os.sep or inside in os.path.realpath(repo) + os.sep:
            return refuse("private.py or the repo is inside a goal's worktree", "run setup.py --git-hooks from an installed copy of the skills")
        os.makedirs(folder, exist_ok=True)
    bad = 0
    for name in GUARD:
        path, state = os.path.join(folder, name), hook_state(os.path.join(folder, name))
        text = open(path, errors="replace").read() if state != "missing" else ""
        mine = re.search(r"P='([^']*)' S='([^']*)' U='([^']*)'", text) if MARK in text else None
        ours = mine and text == stub(name, *mine.groups())
        if remove:
            if ours:
                os.remove(path)
            print("HOOK %s: %s" % (name, "removed" if ours else "not installed" if not text else "kept, it is not the stub setup writes"))
        elif text and not ours:  # the owner's own hook, or a stub the owner edited: never overwritten
            bad += state != "installed"
            print("HOOK %s: %s" % (name, "already calls the scan" if state == "installed" else
                                   "left alone, it is not ours. Add: python3 '%s' hook %s" % (priv, GUARD[name][0])))
        else:
            with open(path, "w") as handle:
                handle.write(stub(name, py, priv, setup))
            os.chmod(path, 0o755)
            print("HOOK %s: written" % name)
    return 0 if adopting else int(bool(bad))


def sibling(skill, script):
    path = os.path.join(HERE, "..", "..", skill, "scripts", script)
    return path if os.path.exists(path) else None


def prefixes(repo, found):
    used = set()
    for rel in found["pages"].values():
        used |= set(CRITERION.findall(survey.read(repo, rel) or ""))
    return used


def pick(name, used):
    letters = re.sub(r"[^A-Za-z]", "", name).upper() or "FT"
    for size in (3, 4, 5):
        if letters[:size] not in used and len(letters[:size]) >= 2:
            used.add(letters[:size])
            return letters[:size]
    used.add("FT")
    return "FT"


def summary_of(found, name):
    if name == "Home" and found["readme"]:
        for line in found["readme"].splitlines():
            if line.strip() and not line.startswith(("#", "!", "[", "<", "|", "```")):
                return line.strip()[:240]
    return PLACEHOLDER


def mapping(found):
    rows = {"Home": ["README.md"]}
    rows.update({name: [folder] for name, folder in found["areas"].items()})
    return rows


def decide(repo, config, found):
    """The plan: a list of (verb, path, note, action) with action None for skip and no fit."""
    acts, wiki = [], found["wiki"]
    seen, old = out(repo, "workflow-delivery", "private.py", "visibility"), survey.read(repo, ".loop/config.json")  # one live answer
    kept = json.loads(old or "{}").get("regression_runs")  # recorded as regression_runs; unreadable is never taken as public
    if {"private": "mac", "public": "actions"}.get(seen) or kept:
        config["regression_runs"] = {"private": "mac", "public": "actions"}.get(seen) or kept
    else:
        config.pop("regression_runs", None)
    if old is None or json.loads(old) != {k: v for k, v in config.items() if k != "checks"}:
        acts.append(("add" if old is None else "convert", ".loop/config.json", "keys added; yours kept", "config"))
    for name in ("queue.md", "findings.md"):
        if survey.read(repo, ".loop/" + name) is None:
            acts.append(("add", ".loop/" + name, "", "file"))
    have = {}
    for line in (survey.read(repo, ".loop/docs.tsv") or "").splitlines():
        if line.strip() and not line.startswith("#"):
            have[line.split("\t")[0]] = line
    new_rows = [n for n in mapping(found) if n not in have]
    if new_rows:
        acts.append(("add" if not have else "convert", ".loop/docs.tsv", "pages " + ", ".join(new_rows), "map"))
    for name in mapping(found):
        rel = "%s/%s.md" % (wiki, name)
        text = survey.read(repo, rel)
        if text is None:
            acts.append(("add", rel, "PRD page with a requirement and Tests", ("page", name)))
        elif text.startswith(survey.MARKER):
            acts.append(("skip", rel, "already ours", None))
        elif "\n## " in text:
            acts.append(("no fit", rel, "has its own sections; add the marker and the contract sections by hand", None))
        else:
            acts.append(("convert", rel, "marker and the PRD sections added; words kept as its Problem", ("convert", name)))
    for name in sorted(set(found["pages"]) - set(mapping(found))):
        acts.append(("no fit", found["pages"][name], "not a feature of this repo's top-level folders; left alone", None))
    if config["checks"]:
        if not any("regression.tsv" in a[1] for a in acts) and survey.read(repo, ".loop/regression.tsv") is None:
            acts.append(("add", ".loop/regression.tsv", "one land row per page's first criterion", "rows"))
        if config.get("regression_runs") != "actions":
            acts.append(("note", "regression workflow", "not written: " + ("a private repo's regression runs on the Mac" if seen == "private"
                                                                      else "visibility unreadable (run gh auth login, then setup again)"), None))
        elif survey.read(repo, ".github/workflows/regression.yml") is None:
            acts.append(("add", ".github/workflows/regression.yml", "regression run on " + config.get("regression_cron", ""), "workflow"))
    else:
        acts.append(("no fit", ".loop/regression.tsv", "no check command found, so no test row can be seeded", None))
    if sibling("workflow-health", "automation.py"):
        acts.append(("add", "local schedule", "launch agent file and registry entry outside the repo; you load it by hand", "local"))
    for line in out(repo, "workflow-delivery", "private.py", "required", "--base", config["base"]).splitlines() if seen == "private" else []:
        if line.startswith("BLOCKS: "):
            acts.append(("BLOCKS", line[8:-9], "no commit status can satisfy it; remove it from the ruleset or branch protection (BLOCKS)", None))
    acts.append(("note", "health", "workflow-health check works with these files; its rules are fixed", None))
    return acts


def out(repo, skill, script, *argv):
    path = sibling(skill, script)
    return subprocess.run([sys.executable, path] + list(argv), cwd=repo, capture_output=True, text=True).stdout.strip() if path else ""


def tool(repo, skill, script, *argv):
    path = sibling(skill, script)
    if not path:
        print("SKIP: %s is not installed beside this skill" % skill)
        return
    done = subprocess.run([sys.executable, path] + list(argv), cwd=repo, capture_output=True, text=True)
    if done.returncode:
        print("NOTE: %s %s: %s" % (script, argv[0], (done.stdout + done.stderr).strip()[-200:]))


def apply(repo, config, found, acts):
    """Write what decide() planned. Returns the paths to commit."""
    touched, wiki = [], found["wiki"]
    used = prefixes(repo, found)
    rows = []
    for verb, path, _, action in acts:
        if action in ("file",):
            with open(os.path.join(repo, path), "w") as handle:
                handle.write("# Findings\n\nOpen findings, one line each.\n" if "findings" in path else "# Goal queue\n\nOne goal a line.\n")
        elif isinstance(action, tuple):
            name = action[1]
            full = os.path.join(repo, path)
            if (survey.read(repo, path) or "").startswith(survey.MARKER):
                continue  # already adopted on the setup branch
            os.makedirs(os.path.dirname(full), exist_ok=True)
            tag = pick(name, used)
            criterion = "- %s-1: **Unreviewed** The repo checks pass with the %s change in." % (tag, name)
            rows.append((tag, name))
            title, problem = "# " + name, summary_of(found, name)
            if action[0] == "convert":
                text = survey.read(repo, path).rstrip("\n")
                title, _, problem = text.partition("\n")
                if not title.startswith("# "):
                    title, problem = "# " + name, text
            # one PRD page writer, owned by workflow-docs
            tool(repo, "workflow-docs", "prd.py", "skeleton", path, "--title", title, "--problem", problem.strip() or PLACEHOLDER,
                 "--requirement", criterion)
        touched.append(path)
    if any(a[3] == "map" for a in acts):
        for name, paths in mapping(found).items():
            tool(repo, "workflow-docs", "docs.py", "add", name, "--paths", ",".join(paths))
        touched.append(".loop/docs.tsv")
    if config["checks"]:
        for tag, name in rows:
            tool(repo, "workflow-regression", "regression.py", "add", "%s-checks" % tag.lower(), "--level", "land", "--command",
                 config["checks"][0], "--goal", "%s-1" % tag, "--describe",
                 "Given the %s change, when the repo's checks run, then they pass." % name)
        touched.append(".loop/regression.tsv")
        if any(a[3] == "workflow" for a in acts):
            tool(repo, "workflow-regression", "regression.py", "workflow")
    if any(a[3] == "local" for a in acts):
        tool(repo, "workflow-health", "automation.py", "local", "install")
    tool(repo, "workflow-docs", "criteria.py", "render")
    return touched


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo", default=".")
    args = parser.parse_args()
    repo = survey.git(args.repo, "rev-parse", "--show-toplevel")
    config = json.loads(survey.read(repo, ".loop/config.json") or "{}")
    config.setdefault("base", "main")
    config.setdefault("checks", [])
    found = survey.survey(repo, config)
    for verb, path, note, _ in decide(repo, config, found):
        print("%s: %s %s" % (verb, path, ("(" + note + ")") if note else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
