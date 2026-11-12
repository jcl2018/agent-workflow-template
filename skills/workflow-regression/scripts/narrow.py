#!/usr/bin/env python3
"""The narrow half of lanes.py's row mapping: a test script's `# reads:` header and what its entry points reach.

Imported by lanes.py, not run. A header is one or more `# reads: <path> [<path>...]` lines in the file's leading
comment block: repo-relative paths, whitespace-separated, a trailing / for a folder. Narrow means no folder widening:
shell files add the paths they name, Python files their same-folder imports and quoted file names (and, in a file that
imports by name with importlib.import_module, each quoted same-folder module name), and anything this cannot resolve
becomes a problem that makes the row run on every change.
"""
import os
import re
import time

import lanes

READS = re.compile(r"^#\s*reads:(.*)$")
QUOTED = re.compile(r"""["']([\w./-]*\w)["']""")
NOREAD = "# lanes: no read"
ASSIGN = re.compile(r"""(?:^|[;\s])(\w+)=["']?(?:\$here/)?(skills/[\w./-]+?)/?["']?(?=\s*(?:;|$))""")
SYSPATH_ARG = "sys.path.insert(0, sys.argv["  # python3 - "$folder": the folder only goes on sys.path
ENTER = re.compile(r"\s*(?:\w+=)?\$?\(?\s*(?:cd|pushd|mkdir)\s")  # a command that names a folder and reads nothing
NAMES_ONLY = re.compile(r"PYTHONPATH=\S+|sys\.path\.(?:insert|append)\([^)]*\)")  # put a folder on a search path
LISTING = re.compile(r"\b(?:ls|find|grep\s+-\w*[rR]|rg|tar|zip|cp\s+-\w*[rRa]|rsync|du|wc)\b|\s\.(?:\s|/|$)")
GLOB = re.compile(r"(?:\$here/)?((?:skills|dev|docs)/[\w./-]*?)/?\*")
FILEISH = re.compile(r"\.(?:py|md|json|sh|tsv|txt|yml|yaml|toml)$")


def header(root, rel, cache):
    """(declared paths or None, problems (code, file, line, what)) of a file's `# reads:` lines (leading comments only)."""
    key = ("header", rel)
    if key in cache:
        return cache[key]
    text, paths, problems, lead = lanes.read(root, rel, cache), [], [], True
    if text is None or not (rel.endswith(".sh") or "." not in os.path.basename(rel)):  # headers live in shell files
        cache[key] = (None, [])
        return cache[key]
    code = "\n".join(line for line in text.split("\n") if not line.lstrip().startswith("#"))
    mentioned = {p for p in lanes.references(root, code, os.path.dirname(rel), wide=False)[0] if p.endswith("/")}
    found = False
    for number, line in enumerate(text.splitlines(), 1):
        lead = lead and (line.startswith("#") or (number == 1 and line.startswith("#!")))
        match = READS.match(line)
        if not match:
            continue
        found = True
        if not lead:
            problems.append(("LANES-DECL-PLACE", rel, number, "# reads: outside the leading comment block"))
            continue
        for word in match.group(1).split():
            norm = os.path.normpath(word) + ("/" if word.endswith("/") else "")
            if any(c in word for c in "$*?"):
                problems.append(("LANES-DECL-PATTERN", rel, number, "variable or glob in a declared path: " + word))
            elif os.path.isabs(word) or norm.startswith(".."):
                problems.append(("LANES-DECL-ESCAPE", rel, number, "declared path leaves the repo: " + word))
            elif not os.path.exists(os.path.join(root, norm)):
                problems.append(("LANES-DECL-MISSING", rel, number, "declared path does not exist: " + word))
            else:
                if os.path.isdir(os.path.join(root, norm)):
                    norm = norm.rstrip("/") + "/"
                    if norm.startswith("skills/") and not any(m.startswith(norm) for m in mentioned):
                        problems.append(("LANES-DECL-FOLDER-UNBACKED", rel, number,
                                         "declares %s but never globs or reads it whole" % norm))
                        continue
                paths.append(norm)
    cache[key] = (paths if found else None, problems)
    return cache[key]


def scan(root, rel, cache):
    """(files, folders) one file reaches, unwidened. Shell: named paths. Python: same-folder imports, quoted file names
    (every file of that base name under skills/ or beside it) and quoted folders of its own skill. Else a leaf."""
    key = ("narrow", rel)
    if key in cache:
        return cache[key]
    text, base = lanes.read(root, rel, cache) or "", os.path.dirname(rel)
    files, folders = set(), set()
    if rel.endswith(".py"):
        index = cache.get("names")
        if index is None:
            index = cache["names"] = {}
            for path in lanes.walk(root, "skills", cache):
                index.setdefault(os.path.basename(path), set()).add(path)
        skill = "/".join(rel.split("/")[:2]) + "/" if rel.startswith("skills/") else None
        files |= {os.path.join(base, m + ".py") for m in lanes.modules(text)
                  if os.path.isfile(os.path.join(root, base, m + ".py"))}
        dynamic = "import_module(" in text  # importlib by name (health.py's sibling_module("enforce")): no import line
        for lit in set(QUOTED.findall(text)):
            name = os.path.basename(lit)
            if dynamic and "/" not in lit and os.path.isfile(os.path.join(root, base, lit + ".py")):
                files.add(os.path.join(base, lit + ".py"))  # each quoted same-folder module name is a module it may load
            if FILEISH.search(name):
                files |= index.get(name, set())
                if os.path.isfile(os.path.join(root, base, name)):
                    files.add(os.path.join(base, name))
            elif "/" in lit and os.path.isdir(os.path.join(root, os.path.normpath(lit))) and not lit.startswith(".."):
                folders.add(os.path.normpath(lit) + "/")  # Path("skills/a/scripts").glob(...)
            elif skill and "/" not in lit:
                for here in [os.path.join(skill, lit)] + [os.path.join(skill, d, lit) for d in ("scripts", "references")]:
                    if os.path.isdir(os.path.join(root, here)) and os.path.normpath(here) != base:
                        folders.add(os.path.normpath(here) + "/")
    elif "." not in os.path.basename(rel) or rel.endswith(".sh"):  # comments and `# lanes: no read` lines read nothing
        text = "\n".join(line for line in text.split("\n") if not line.lstrip().startswith("#") and NOREAD not in line)
        found, _ = lanes.references(root, text, base, wide=False)
        files = {p for p in found if not p.endswith("/")}
        folders = {p for p in found if p.endswith("/")}
        globs = {m.rstrip("/") + "/" for m in GLOB.findall(lanes.HERE_FORMS.sub("$here/", text))
                 if os.path.isdir(os.path.join(root, m))}  # a glob needs its folder declared, not one file in it
        bound = {}  # VAR=<skill folder>, from this file and the shell files it sources (merged in narrow())
        for line in text.split("\n"):
            for var, folder in ASSIGN.findall(lanes.HERE_FORMS.sub("$here/", line)):
                bound[var] = folder.rstrip("/") + "/"
        cache["bind", rel] = bound
        globs |= wholes(root, text, base, bound)
        cache["globs", rel] = {g for g in globs if g.startswith("skills/")}
    cache[key] = (files, folders)
    return cache[key]


def wholes(root, text, base, bound):
    """Skill folders a shell text reads as a whole: named bare by a command (ls, grep -r, cp -R, "$d", "$d/sub")
    rather than as the prefix of a named file. Per command: cd, pushd and mkdir read nothing, nor does putting a folder
    on PYTHONPATH or sys.path; a cd into a skill folder followed by a listing or recursive read reads it whole."""
    out = set()
    for line in lanes.HERE_FORMS.sub("$here/", text).split("\n"):
        entered = set()
        for cmd in re.split(r"&&|\|\||;|\|", line):
            cmd = NAMES_ONLY.sub(" ", cmd)
            here = {p for p in lanes.references(root, cmd, base, wide=False)[0] if p.endswith("/") and p.startswith("skills/")}
            for var, folder in bound.items():
                for rest in re.findall(r"\$\{?%s\}?(?![\w}])(/[\w./-]*)?" % var, cmd):
                    path = os.path.normpath(folder + rest.lstrip("/")) + "/" if rest.strip("/") else folder
                    if os.path.isdir(os.path.join(root, path)):
                        here.add(path)
            if ENTER.match(cmd):
                entered |= here
            elif ASSIGN.search(cmd) or SYSPATH_ARG in line or (SYSPATH_ARG in text and re.match(r"\s*python3\s+-\s", cmd)):
                continue
            else:
                out |= here | (entered if LISTING.search(cmd) else set())
    return out


def narrow(root, seeds, cache):
    """(deps, problems, parent) reached from the seeds. Fail-wide: a named skill folder needs a declared path in it,
    `skills/` needs `skills/` declared, and its files whose names appear in reached shell text are followed too."""
    deps, problems, parent, declared, marks, shell, sh = set(), [], {}, [], set(), [], []
    todo = [(s, None) for s in seeds]
    while True:
        while todo:
            rel, via = todo.pop()
            if rel in deps:
                continue
            deps.add(rel)
            parent.setdefault(rel, via)
            paths, probs = header(root, rel, cache)
            problems += probs
            for path in paths or []:
                declared.append(path)
                if path.endswith("/"):
                    deps.add(path)
                    todo += [(f, rel) for f in lanes.walk(root, path, cache)]
                else:
                    todo.append((path, rel))
            files, folders = scan(root, rel, cache)
            todo += [(f, rel) for f in files]
            marks |= {(g, rel) for g in cache.get(("globs", rel), ())}
            for folder in folders:
                if folder.startswith("skills/") and not rel.endswith(".py"):
                    marks.add((folder, rel))
                else:  # a folder holding the file that names it (dev/, dev/toy/) is a prefix, not walked
                    deps.add(folder)
                    todo += [] if rel.startswith(folder) else [(f, rel) for f in lanes.walk(root, folder, cache)]
            if rel.endswith(".sh") or "." not in os.path.basename(rel):
                shell.append(lanes.read(root, rel, cache) or "")
                sh.append(rel)
        for rel in sh:  # a VAR=<folder> set in a file this one sources counts here too
            text = "\n".join(x for x in (lanes.read(root, rel, cache) or "").split("\n")
                             if not x.lstrip().startswith("#") and NOREAD not in x)
            sourced = {os.path.basename(s) for s in re.findall(r"(?m)^\s*(?:\.|source)\s+\"?([^\s\";]+)", text)}
            bound = {k: v for o in sh if o != rel and os.path.basename(o) in sourced
                     for k, v in cache.get(("bind", o), {}).items()}
            if not bound:
                continue
            extra = wholes(root, text, os.path.dirname(rel), bound) - cache.get(("globs", rel), set())
            cache["globs", rel] = cache.get(("globs", rel), set()) | extra
            marks |= {(f, rel) for f in extra}
        added = False
        for folder, via in sorted(marks):
            for path in lanes.walk(root, folder, cache):
                name, stem = (re.escape(x) for x in (os.path.basename(path), os.path.splitext(os.path.basename(path))[0]))
                used = r"(?<![\w.-])%s(?![\w-])|\b(?:import|from)\s+%s\b" % (name, stem) if path.endswith(".py") else \
                    r"(?<![\w.-])%s(?![\w-])" % name
                if path not in deps and any(re.search(used, s) for s in shell):
                    todo.append((path, via))
                    added = True
        if not added:
            break
    for folder, via in sorted(marks):
        lines = (lanes.read(root, via, cache) or "").split("\n")
        at = next((i for i, line in enumerate(lines, 1) if folder.rstrip("/") in line and not line.startswith("#")), 0)
        if folder == "skills/" and "skills/" not in declared:
            problems.append(("LANES-DECL-TREE", via, at, "reads all of skills/ but does not declare skills/"))
        elif folder in cache.get(("globs", via), ()) and not any(folder.startswith(p) for p in declared):
            problems.append(("LANES-DECL-GLOB", via, at, "reads %s as a whole but does not declare it" % folder))
        elif folder != "skills/" and not any(p.startswith(folder) or folder.startswith(p) for p in declared):
            problems.append(("LANES-DECL-FOLDER", via, at, "names %s but declares no file in it" % folder))
    return deps, problems, parent


def suggest(root, rid):
    """regression.py reads ROW: a `# reads:` header for the row's script from the newest check-reads trace of it, kept in
    <git dir>/lanes-trace.tsv (id, epoch, path). The trace sees Python reads only; bash reads stay the author's."""
    rows = [line.split("\t") for line in (lanes.read(root, lanes.TABLE, {}) or "").splitlines() if line[:1] != "#"]
    command = next((cells[2] for cells in rows if len(cells) > 2 and cells[0] == rid), None)
    if command is None:
        print("REFUSED: no row %s in %s" % (rid, lanes.TABLE))
        return 2
    store = (lanes.git(root, "rev-parse", "--absolute-git-dir") or "").strip()
    trace = os.path.join(store, "lanes-trace.tsv")
    text = open(trace, errors="replace").read() if store and os.path.isfile(trace) else ""
    mine = [cells for cells in (line.split("\t") for line in text.splitlines()) if len(cells) == 3 and cells[0] == rid]
    if not mine:
        print("NO TRACE %s: run bash dev/toy/check-reads.sh %s (it records each row's skill reads), then regression.py "
              "reads %s again" % (rid, rid, rid))
        return 1
    newest = max(cells[1] for cells in mine)
    scripts = sorted(p for p in lanes.references(root, command, "", wide=False)[0] if p.endswith(".sh")) or ["its command"]
    print("READS %s: for %s, from the check-reads trace of %s (Python reads only; keep what its bash reads)" % (
        rid, " ".join(scripts), time.strftime("%Y-%m-%d %H:%M", time.localtime(int(newest)))))
    out = ["# reads:"]
    for path in sorted({cells[2] for cells in mine if cells[1] == newest and cells[2]}):
        if len(out[-1]) + len(path) > 118 and out[-1] != "# reads:":
            out.append("# reads:")
        out[-1] += " " + path
    print("\n".join(out) if out != ["# reads:"] else "# reads: (the trace saw no skill file read)")
    return 0
