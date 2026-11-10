#!/usr/bin/env python3
"""Reuse a branch's last regression run: the test record, and which rows a change since then can affect.

Imported by regression.py (`run ... --reuse`) and lanes_cli.py (`affected`, `deps`, `check`). The record lives in
<git common dir>/loop/tests/<branch>-<sha8>.json: {schema, runner, worktree, command, at, commit,
rows: {id: {status: PASS|FAIL|KNOWN, seconds, commit}}}. A row is reused only when it passed (or is a known failure)
on HEAD or an ancestor of HEAD and nothing it reads changed since; anything this file can't map reruns everything.
A test script whose leading comment block has `# reads: <path>...` lines is mapped narrowly (declared entry points plus
what they reach, no folder widening); a script without one keeps the wide mapping; LANES_WIDE=1 forces wide everywhere.
"""
import fcntl
import hashlib
import json
import os
import re
import subprocess
import sys

import narrow

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
RUNNER = "skills/workflow-regression/scripts/regression.py"  # rows that reach it may read .loop/regression.tsv
TABLE = ".loop/regression.tsv"
SKILL_NAME = re.compile(r"\bworkflow-[a-z]+\b")
IMPORT = re.compile(r"^\s*(?:from\s+([A-Za-z_]\w*)|import\s+([\w, ]+))", re.M)
ROOT_RUN = re.compile(r'(?:cd|pushd)\s+"?\$\{?here\}?/?"?(?=[\s;&|)]|$)|-C\s+"?\$\{?here\}?/?"?\s|--root[= ]"?\$\{?here\}?/?"?(?=[\s;&|)]|$)', re.M)
HERE_FORMS = re.compile(r'"\$\{?here\}?"/|\$\{here\}/')  # "$here"/x, "${here}"/x and ${here}/x all mean $here/x
CD_SKILLS = re.compile(r"cd\s+\"?\$\{?here\}?\"?\s*[;&|\n][^\n]*?(?<![\w./$-])skills(?:/\.)?(?=[\s\"')]|$)")


def modules(text):
    """Module names a Python text imports: `from x import ...`, and every name of `import a, b as c`."""
    return {name.split()[0] for frm, imp in IMPORT.findall(text) for name in ([frm] if frm else imp.split(",")) if name.strip()}


def git(root, *args):
    done = subprocess.run(["git"] + list(args), cwd=root, capture_output=True, text=True)
    return done.stdout if done.returncode == 0 else None


def runner():
    here = os.path.dirname(os.path.abspath(__file__))
    digest = hashlib.sha256()
    for name in ("regression.py", "lanes.py", "narrow.py"):
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


def references(root, text, folder, wide=True):
    """Repo paths a text names (folders end /) and whether it names the whole repo; wide=False: no widening, no
    skill-name words."""
    text = HERE_FORMS.sub("$here/", text)
    text = text if wide else re.sub(r"""(["'])/(skills|dev)/""", r"\1\2/", text)  # root + "/skills/x" -> skills/x
    found, whole = set(), bool(ROOT.search(text))
    if BARE.search(text) or (not wide and CD_SKILLS.search(text)):
        found.add("skills/")
    for name in SKILL_NAME.findall(text) if wide else ():
        found.add("skills/%s/" % name)
    for raw in PATH.findall(text):
        raw = raw.rstrip(".")
        for cand in {raw, os.path.normpath(os.path.join(folder, raw))}:
            full = os.path.join(root, cand)
            if os.path.isdir(full):
                cand = cand.rstrip("/") + "/"
                found.add(widen(cand) if wide else cand)
            elif os.path.isfile(full):
                found.add(widen(cand) if wide else cand)
    return found, whole


def read(root, rel, cache):
    texts = cache.setdefault("text", {})
    if rel not in texts:
        try:
            with open(os.path.join(root, rel), errors="replace") as handle:
                texts[rel] = handle.read(400000)
        except OSError:
            texts[rel] = None
    return texts[rel]


def scan(root, rel, cache):
    """The repo paths one file names (wide); each file is read once per plan."""
    files = cache.setdefault(None, {})
    if rel not in files:
        text = read(root, rel, cache) or ""
        more, _ = references(root, text, os.path.dirname(rel))  # a script's own `cd "$here"` reads nothing by itself
        if rel.endswith(".py"):
            more |= {os.path.join(os.path.dirname(rel), m + ".py") for m in modules(text)
                     if os.path.isfile(os.path.join(root, os.path.dirname(rel), m + ".py"))}
        files[rel] = more
    return files[rel]


def walk(root, prefix):
    return [os.path.relpath(os.path.join(here, n), root) for here, _, names in os.walk(os.path.join(root, prefix))
            for n in names if "__pycache__" not in here]


def wide_closure(root, command, cache):
    """(dependency paths, always-run) for a row command, following every file it reaches, folders widened."""
    if ("wide", command) in cache:
        return cache["wide", command]
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
    cache["wide", command] = (deps, always)
    return cache["wide", command]


def closure(root, command, cache):
    """(deps, always) for a row command: narrow when a file it names has a header, else wide; a problem means always."""
    if ("closure", command) in cache:
        return cache["closure", command]
    found, whole = references(root, command, "", wide=False)
    named = [p for p in found if not p.endswith("/")]
    seeds = [p for p in named if narrow.header(root, p, cache)[0] is not None or narrow.header(root, p, cache)[1]]
    if os.environ.get("LANES_WIDE") == "1" or not seeds:
        cache["closure", command] = wide_closure(root, command, cache)
        return cache["closure", command]
    deps, problems, parent = narrow.narrow(root, seeds, cache)
    for path in [p for p in found if p not in deps and p not in seeds]:
        deps |= wide_closure(root, path, cache)[0] | {path}
    cache["why", command] = " ".join(map(str, problems[0][:1] + problems[0][3:])) if problems else ""
    cache["chain", command] = parent
    shell = [p for p in deps if p.endswith(".sh") or "." not in os.path.basename(p)]
    texts = ["\n".join(x for x in (read(root, p, cache) or "").split("\n") if narrow.NOREAD not in x) for p in shell]
    root_run = any(ROOT_RUN.search(x) for x in texts)
    if root_run and not problems:  # it runs tools on this repo's own files: any of them may matter
        cache["why", command] = "runs tools on this repo's own files"
    cache["table", command] = hits(TABLE, deps) or RUNNER in found or (hits(RUNNER, deps) and any(  # run from the root
        not re.search(r"(?m)^[^#\n]*\bcd\s", x) for x in texts))
    cache["closure", command] = (deps, whole or bool(problems) or root_run)
    return cache["closure", command]


def named(root, command, cache):
    """The paths a row names itself: its command's paths and what the files it names name (not the whole closure)."""
    key = ("named", command)
    if key not in cache:
        found, _ = references(root, command, "")
        cache[key] = set(found).union(*[scan(root, p, cache) for p in found if not p.endswith("/")])
    return cache[key]


def hits(path, deps):
    return path in deps or any(d.endswith("/") and path.startswith(d) for d in deps)


def touches(root, command, path, cache):
    """Whether a change to path can affect a row (shared by plan() and affected())."""
    deps, _ = closure(root, command, cache)
    if any(path == n or (n.endswith("/") and path.startswith(n)) for n in NO_EFFECT):
        return hits(path, named(root, command, cache))  # release and loop files: only a row naming one
    return hits(path, deps)


def reads_table(root, command, cache):
    """Whether a row reads this repo's .loop/regression.tsv: a narrow row only when its closure names the table, its
    command runs regression.py itself, or a script it reaches runs tools from the repo root; a wide row when it reaches
    regression.py at all. Otherwise a table edit reruns only the rows whose own line changed."""
    deps, _ = closure(root, command, cache)
    return cache.get(("table", command), hits(RUNNER, deps))


def deleted(root, commit):
    """Deleted paths (release and loop files aside) since commit or in the worktree: a vanished file drops edges."""
    out = (git(root, "diff", "--name-status", "--no-renames", "%s..HEAD" % commit) or "").splitlines()
    out += (git(root, "status", "--porcelain", "--no-renames") or "").splitlines()
    gone = [line.split("\t")[-1] if "\t" in line else line[3:].strip('"') for line in out
            if line.startswith("D") or line[1:2] == "D"]  # D\tpath, "D  path", " D path", "MD path"
    return sorted({p for p in gone if not any(p == n or (n.endswith("/") and p.startswith(n)) for n in NO_EFFECT)})


def table(root, commit, name, memo):
    """The rows of a .loop table at a commit, as {id: line}."""
    if (commit, name) not in memo:
        text = git(root, "show", "%s:.loop/%s" % (commit, name)) or ""
        memo[commit, name] = {line.split("\t")[0]: line for line in text.splitlines() if line.strip() and line[0] != "#"}
    return memo[commit, name]


def plan(root, selected, record, current_tsv, current_known):
    """Decide each selected row: (to_run ids, reused ids, notes, full reason or '')."""
    rows, cache, notes, memo = record["rows"], {}, [], {}
    every = [r["id"] for r in selected]
    failed = [r["id"] for r in selected if rows.get(r["id"], {}).get("status") == "FAIL"]
    if failed:
        return every, [], notes, "record has FAIL rows %s" % ", ".join(failed[:10])
    run, reuse, since, kin = [], [], {}, {}
    for row in selected:
        rid, prior = row["id"], rows.get(row["id"])
        deps, always = closure(root, row["command"], cache)
        if cache.get(("why", row["command"])):
            notes.append("ALWAYS %s: %s" % (rid, cache["why", row["command"]]))
        if prior and prior["commit"] not in kin:
            kin[prior["commit"]] = ancestor(root, prior["commit"])
            gone = deleted(root, prior["commit"]) if kin[prior["commit"]] else []
            if gone:
                return every, [], notes, "deleted %s" % " ".join(gone[:5])
        if always or not prior or not kin[prior["commit"]]:
            run.append(rid)
            continue
        if prior["commit"] not in since:
            since[prior["commit"]] = changed(root, prior["commit"])
        stale = since[prior["commit"]] is None  # git couldn't say what changed: run it
        for path in since[prior["commit"]] or []:
            if path == TABLE:
                stale = table(root, prior["commit"], "regression.tsv", memo).get(rid) != current_tsv.get(rid) \
                    or reads_table(root, row["command"], cache)
            elif path == ".loop/regression-known.tsv":
                stale = table(root, prior["commit"], "regression-known.tsv", memo).get(rid) != current_known.get(rid)
            elif touches(root, row["command"], path, cache):
                stale = True
            elif not any(hits(path, closure(root, other["command"], cache)[0]) for other in selected):
                notes.append("UNMAPPED %s: full run" % path)
                return every, [], notes, "unmapped change %s" % path
            if stale:
                break
        (run if stale else reuse).append(rid)
    return run, reuse, notes, ""
