#!/usr/bin/env python3
"""Reuse a branch's last regression run: the test record, and which rows a change since then can affect.

Imported by regression.py (`run ... --reuse`), not run. The record lives outside the worktree, in
<git common dir>/loop/tests/<branch>-<sha8>.json: {schema, runner, worktree, command, at, commit,
rows: {id: {status: PASS|FAIL|KNOWN, seconds, commit}}}. A row is reused only when it passed (or is a known failure)
on HEAD or an ancestor of HEAD and nothing it reads changed since; anything this file can't map reruns everything.
"""
import fcntl
import hashlib
import json
import os
import re
import subprocess
import sys

# No terminal, no waiting: a prompt from git must fail, not block.
os.environ.update(GIT_TERMINAL_PROMPT="0", GH_PROMPT_DISABLED="1", GIT_EDITOR="true", GIT_ASKPASS="true", SSH_ASKPASS="true")
if not sys.stdin or not sys.stdin.isatty():
    os.dup2(os.open(os.devnull, os.O_RDONLY), 0)

SCHEMA = 1
RUNS_FILE = ".loop/regression-runs.tsv"
BOOKKEEPING = (RUNS_FILE, ".loop/goals/", ".loop/queue.md", ".loop/findings.md")  # the loop's own files: no row reads them
NO_EFFECT = ("CHANGELOG.md", "VERSION", "README.md", "FINDINGS.md", "DECISIONS.md", "LICENSE", "docs/ROADMAP.md",
             "docs/designs/", ".loop/goals/", ".loop/findings.md", ".loop/queue.md", RUNS_FILE)
PATH = re.compile(r"(?<![\w.@+/-])(?:\$\{?here\}?/|\./)?((?:\.?[A-Za-z0-9_@+-][A-Za-z0-9._@+-]*/)+[A-Za-z0-9._@+-]*"
                  r"|[A-Za-z0-9_-]+\.[A-Za-z0-9]+)")
BARE = re.compile(r"\$\{?here\}?/skills\b(?!/)")
ROOT = re.compile(r"\$\{?here\}?/?(?=[\s\"')]|$)")
RUNNER = "skills/workflow-regression/scripts/regression.py"  # rows that reach it read .loop/regression.tsv
TOKEN = re.compile(r"\bworkflow-[a-z]+\b")
IMPORT = re.compile(r"^\s*(?:import|from)\s+([A-Za-z_]\w*)", re.M)


def git(root, *args):
    done = subprocess.run(["git"] + list(args), cwd=root, capture_output=True, text=True)
    return done.stdout if done.returncode == 0 else None


def runner():
    here = os.path.dirname(os.path.abspath(__file__))
    digest = hashlib.sha256()
    for name in ("regression.py", "lanes.py"):
        with open(os.path.join(here, name), "rb") as handle:
            digest.update(handle.read())
    return digest.hexdigest()[:12]


def record_path(root):
    branch = (git(root, "symbolic-ref", "--quiet", "--short", "HEAD") or "").strip()
    if not branch:
        return None
    common = os.path.abspath(os.path.join(root, git(root, "rev-parse", "--git-common-dir").strip()))
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", branch)
    return os.path.join(common, "loop", "tests", "%s-%s.json" % (safe, hashlib.sha1(branch.encode()).hexdigest()[:8]))


def load(path, root):
    """(record, why it can't be used) — why is '' for a usable record, else the FULL reason."""
    if not path or not os.path.exists(path):
        return None, "no record"
    try:
        with open(path) as handle:
            data = json.load(handle)
        rows = data["rows"]
        assert all(row["status"] in ("PASS", "FAIL", "KNOWN") and row["commit"] for row in rows.values())
    except (OSError, ValueError, KeyError, TypeError, AssertionError) as error:
        return None, "record unreadable (%s)" % (type(error).__name__,)
    if data.get("schema") != SCHEMA or data.get("runner") != runner():
        return None, "record schema/runner changed"
    if data.get("worktree") != root:
        return None, "record from another worktree %s" % data.get("worktree")
    return data, ""


def save(path, root, command, results, head, at, fresh):
    """Merge the rows this run ran into the record, under a lock; a fresh (full) run first drops the old rows."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path + ".lock", "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        old, _ = load(path, root)
        rows = {} if fresh or not old else old["rows"]
        for item in results:
            rows[item["id"]] = {"status": item["state"], "seconds": item["seconds"], "commit": head}
        data = {"schema": SCHEMA, "runner": runner(), "worktree": root, "command": command, "at": at,
                "commit": head, "rows": rows}
        temp = "%s.%d.tmp" % (path, os.getpid())
        with open(temp, "w") as handle:
            json.dump(data, handle, indent=1, sort_keys=True)
        os.replace(temp, path)


def dirty(root):
    """Paths git status lists, the loop's bookkeeping files aside."""
    out = git(root, "status", "--porcelain", "--no-renames", "--untracked-files=all") or ""
    paths = [line[3:].strip('"') for line in out.splitlines()]
    return [p for p in paths if not p.startswith(BOOKKEEPING)]


def changed(root, commit):
    out = git(root, "diff", "--name-only", "--no-renames", "%s..HEAD" % commit)
    if out is None:
        return None
    return sorted({p for p in out.split() if p != RUNS_FILE} | set(dirty(root)))


def ancestor(root, commit):
    return subprocess.run(["git", "merge-base", "--is-ancestor", commit, "HEAD"], cwd=root,
                          capture_output=True).returncode == 0


def widen(path):
    parts = path.rstrip("/").split("/")
    return "skills/%s/" % parts[1] if parts[0] == "skills" and len(parts) > 1 else path


def references(root, text, folder):
    """Repo paths a text names: files, folders (as prefixes ending /), and whether it names the whole repo."""
    found, whole = set(), bool(ROOT.search(text))
    if BARE.search(text):
        found.add("skills/")
    for name in TOKEN.findall(text):
        found.add("skills/%s/" % name)
    for raw in PATH.findall(text):
        raw = raw.rstrip(".")
        for cand in {raw, os.path.normpath(os.path.join(folder, raw))}:
            full = os.path.join(root, cand)
            if os.path.isdir(full):
                found.add(widen(cand.rstrip("/") + "/"))
            elif os.path.isfile(full):
                found.add(widen(cand))
    return found, whole


def scan(root, rel, cache):
    """The repo paths one file names; each file is read once per plan."""
    files = cache.setdefault(None, {})
    if rel not in files:
        try:
            with open(os.path.join(root, rel), errors="replace") as handle:
                text = handle.read(400000)
        except OSError:
            text = ""
        more, _ = references(root, text, os.path.dirname(rel))  # a script's own `cd "$here"` reads nothing by itself
        if rel.endswith(".py"):
            more |= {os.path.join(os.path.dirname(rel), m + ".py") for m in IMPORT.findall(text)
                     if os.path.isfile(os.path.join(root, os.path.dirname(rel), m + ".py"))}
        files[rel] = more
    return files[rel]


def walk(root, prefix):
    return [os.path.relpath(os.path.join(here, n), root) for here, _, names in os.walk(os.path.join(root, prefix))
            for n in names if "__pycache__" not in here]


def closure(root, command, cache):
    """(dependency paths, always-run) for a row command, following every file it reaches."""
    if command in cache:
        return cache[command]
    deps, whole = references(root, command, "")
    always = whole or not deps
    todo, seen = [p for p in deps if not p.endswith("/")], set()
    for prefix in [p for p in deps if p.endswith("/")]:
        todo += walk(root, prefix)
    while todo:
        rel = todo.pop()
        if rel in seen:
            continue
        seen.add(rel)
        for path in scan(root, rel, cache) - deps:
            deps.add(path)
            todo += walk(root, path) if path.endswith("/") else [path]
    cache[command] = (deps, always)
    return cache[command]


def named(root, command, cache):
    """The paths a row names itself: its command's paths and what the files it names name (not the whole closure)."""
    key = ("named", command)
    if key not in cache:
        found, _ = references(root, command, "")
        cache[key] = set(found).union(*[scan(root, p, cache) for p in found if not p.endswith("/")])
    return cache[key]


def hits(path, deps):
    return path in deps or any(d.endswith("/") and path.startswith(d) for d in deps)


def table(root, commit, name, memo):
    """The rows of a .loop table at a commit, as {id: line}."""
    if (commit, name) not in memo:
        text = git(root, "show", "%s:.loop/%s" % (commit, name)) or ""
        memo[commit, name] = {line.split("\t")[0]: line for line in text.splitlines() if line.strip() and line[0] != "#"}
    return memo[commit, name]


def plan(root, selected, record, current_tsv, current_known):
    """Decide each selected row: (to_run ids, reused ids, notes, full reason or '')."""
    rows, cache, notes, memo = record["rows"], {}, [], {}
    failed = [r["id"] for r in selected if rows.get(r["id"], {}).get("status") == "FAIL"]
    if failed:
        return [r["id"] for r in selected], [], notes, "record has FAIL rows %s" % ", ".join(failed[:10])
    run, reuse, since, kin = [], [], {}, {}
    for row in selected:
        rid, prior = row["id"], rows.get(row["id"])
        deps, always = closure(root, row["command"], cache)
        if prior and prior["commit"] not in kin:
            kin[prior["commit"]] = ancestor(root, prior["commit"])
        if always or not prior or not kin[prior["commit"]]:
            run.append(rid)
            continue
        if prior["commit"] not in since:
            since[prior["commit"]] = changed(root, prior["commit"])
        stale = since[prior["commit"]] is None  # git couldn't say what changed: run it
        for path in since[prior["commit"]] or []:
            if path == ".loop/regression.tsv":
                stale = table(root, prior["commit"], "regression.tsv", memo).get(rid) != current_tsv.get(rid) \
                    or hits(RUNNER, deps)
            elif path == ".loop/regression-known.tsv":
                stale = table(root, prior["commit"], "regression-known.tsv", memo).get(rid) != current_known.get(rid)
            elif any(path == n or (n.endswith("/") and path.startswith(n)) for n in NO_EFFECT):
                stale = hits(path, named(root, row["command"], cache))  # release and loop files: only a row naming one
            elif hits(path, deps):
                stale = True
            elif not any(hits(path, closure(root, other["command"], cache)[0]) for other in selected):
                notes.append("UNMAPPED %s: full run" % path)
                return [r["id"] for r in selected], [], notes, "unmapped change %s" % path
            if stale:
                break
        (run if stale else reuse).append(rid)
    return run, reuse, notes, ""
