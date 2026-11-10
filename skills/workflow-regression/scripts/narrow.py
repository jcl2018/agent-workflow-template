#!/usr/bin/env python3
"""The narrow half of lanes.py's row mapping: a test script's `# reads:` header and what its entry points reach.

Imported by lanes.py, not run. A header is one or more `# reads: <path> [<path>...]` lines in the file's leading
comment block: repo-relative paths, whitespace-separated, a trailing / for a folder. Narrow means no folder widening:
shell files add the paths they name, Python files their same-folder imports and quoted file names, and anything this
cannot resolve becomes a problem that makes the row run on every change.
"""
import os
import re

import lanes

READS = re.compile(r"^#\s*reads:(.*)$")
QUOTED = re.compile(r"""["']([\w./-]*\w)["']""")
NOREAD = "# lanes: no read"
GLOB = re.compile(r"(?:\$here/)?((?:skills|dev|docs)/[\w./-]*?)/?\*")
FILEISH = re.compile(r"\.(?:py|md|json|sh|tsv|txt|yml|yaml|toml)$")


def header(root, rel, cache):
    """(declared paths or None, problems (code, file, line, what)) of a file's `# reads:` lines (leading comments only)."""
    key = ("header", rel)
    if key in cache:
        return cache[key]
    text, paths, problems, lead = lanes.read(root, rel, cache), [], [], True
    if text is None:
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
            for path in lanes.walk(root, "skills"):
                index.setdefault(os.path.basename(path), set()).add(path)
        skill = "/".join(rel.split("/")[:2]) + "/" if rel.startswith("skills/") else None
        files |= {os.path.join(base, m + ".py") for m in lanes.IMPORT.findall(text)
                  if os.path.isfile(os.path.join(root, base, m + ".py"))}
        for lit in set(QUOTED.findall(text)):
            name = os.path.basename(lit)
            if FILEISH.search(name):
                files |= index.get(name, set())
                if os.path.isfile(os.path.join(root, base, name)):
                    files.add(os.path.join(base, name))
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
        cache["globs", rel] = {g for g in globs if g.startswith("skills/")}
    cache[key] = (files, folders)
    return cache[key]


def narrow(root, seeds, cache):
    """(deps, problems, parent) reached from the seeds. Fail-wide: a named skill folder needs a declared path in it,
    `skills/` needs `skills/` declared, and its files whose names appear in reached shell text are followed too."""
    deps, problems, parent, declared, marks, shell = set(), [], {}, [], set(), []
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
                    todo += [(f, rel) for f in lanes.walk(root, path)]
                else:
                    todo.append((path, rel))
            files, folders = scan(root, rel, cache)
            todo += [(f, rel) for f in files]
            for folder in folders:
                if folder.startswith("skills/") and not rel.endswith(".py"):
                    marks.add((folder, rel))
                else:  # a folder holding the file that names it (dev/, dev/toy/) is a prefix, not walked
                    deps.add(folder)
                    todo += [] if rel.startswith(folder) else [(f, rel) for f in lanes.walk(root, folder)]
            if rel.endswith(".sh") or "." not in os.path.basename(rel):
                shell.append(lanes.read(root, rel, cache) or "")
        added = False
        for folder, via in sorted(marks):
            for path in lanes.walk(root, folder):
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
            problems.append(("LANES-DECL-GLOB", via, at, "globs %s but does not declare that folder" % folder))
        elif folder != "skills/" and not any(p.startswith(folder) or folder.startswith(p) for p in declared):
            problems.append(("LANES-DECL-FOLDER", via, at, "names %s but declares no file in it" % folder))
    return deps, problems, parent
