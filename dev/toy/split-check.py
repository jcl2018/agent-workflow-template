#!/usr/bin/env python3
"""Prove a script was split by a pure move. usage: split-check.py REPO OLD.py NEW NAMES [PRIMITIVE ...]

OLD.py is a skill script (repo-relative), NEW an existing module beside it that its block moved into (the package has
no room for new files), NAMES the moved names, comma separated; PRIMITIVEs are small helpers copied into NEW unchanged
(run, git, path_of). It checks, each failing with a fix line:
  1. size: health's own size rule gives OLD.py and NEW.py no WARN or FAIL row;
  2. names: OLD imports back exactly NAMES from NEW, NEW defines each, and each is the same object on both modules;
  3. leftovers: OLD defines none of the moved names itself;
  4. primitives: each copied PRIMITIVE has the same source in both files;
  5. no dev/toy test sets OLD.<moved name> (a patch there would no longer reach the moved code);
Then a negative control: on a temp copy with one name dropped from the import-back line and one def left behind,
checks 2 and 3 must both fail.
"""
import ast
import glob
import os
import re
import shutil
import subprocess
import sys
import tempfile


class NoSplit(Exception):
    """The split itself is missing; checks 2 and 3 already say so."""


def top_names(tree):
    names = {}
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            names[node.name] = node
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    names[target.id] = node
    return names


def imported_back(tree, new):
    return {alias.asname or alias.name for node in tree.body if isinstance(node, ast.ImportFrom) and node.module == new
            for alias in node.names}


def static(old_text, new_text, new, moved):
    """The trouble checks 2 (names) and 3 (leftovers) find without importing anything."""
    trouble = []
    old_tree, new_tree = ast.parse(old_text), ast.parse(new_text)
    back = imported_back(old_tree, new)
    if moved != back:
        trouble.append("names: the moved names are %s but the import-back line names %s. fix: import every moved name back"
                       % (sorted(moved), sorted(back)))
    missing = sorted(moved - set(top_names(new_tree)))
    if missing:
        trouble.append("names: %s.py does not define %s. fix: move the block there" % (new, missing))
    left = sorted(moved & set(top_names(old_tree)))
    if left:
        trouble.append("leftovers: the old script still defines %s. fix: delete the copy left behind" % left)
    return trouble, moved


def main():
    repo, old_rel, new, primitives = os.path.abspath(sys.argv[1]), sys.argv[2], sys.argv[3], sys.argv[5:]
    moved = {n.strip() for n in sys.argv[4].split(",") if n.strip()}
    folder = os.path.join(repo, os.path.dirname(old_rel))
    old_path, new_path = os.path.join(repo, old_rel), os.path.join(folder, new + ".py")
    old_name = os.path.basename(old_rel)[:-3]
    if not os.path.isfile(new_path):
        sys.exit("split: %s.py is missing beside %s. fix: move the block out of it" % (new, old_rel))
    old_text, new_text = open(old_path).read(), open(new_path).read()
    trouble = []
    temp = tempfile.mkdtemp()
    try:
        # 1. size, by health's own rule, on a root holding only these two files
        place = os.path.join(temp, "root", os.path.dirname(old_rel))
        os.makedirs(place)
        for path in (old_path, new_path):
            shutil.copy(path, place)
        sys.path.insert(0, os.path.join(repo, "skills", "workflow-health", "scripts"))
        import health
        for row in health.size_rows(os.path.join(temp, "root")):
            if row["state"] != "PASS":
                trouble.append("size: %s %s. fix: move another leaf block out" % (row["subject"], row["detail"]))
        # 2 and 3
        found = static(old_text, new_text, new, moved)[0]
        trouble += found
        probe = ("import sys; sys.path.insert(0, %r); import %s as old; new = sys.modules[%r]; "
                 "bad = [n for n in %r if getattr(old, n, None) is not getattr(new, n)]; print(bad); sys.exit(bool(bad))"
                 % (folder, old_name, new, sorted(moved)))
        done = subprocess.run([sys.executable, "-B", "-c", probe], capture_output=True, text=True, cwd=temp,
                              stdin=subprocess.DEVNULL)
        if done.returncode:
            trouble.append("names: not the same object on %s and %s: %s. fix: import the name back, don't redefine it"
                           % (old_name, new, (done.stdout + done.stderr).strip()[-300:]))
        # 4. copied primitives are identical
        old_defs, new_defs = top_names(ast.parse(old_text)), top_names(ast.parse(new_text))
        for name in primitives:
            if name not in old_defs or name not in new_defs:
                trouble.append("primitives: %s is not defined in both files. fix: copy it unchanged" % name)
            elif ast.get_source_segment(old_text, old_defs[name]) != ast.get_source_segment(new_text, new_defs[name]):
                trouble.append("primitives: %s differs between the two files. fix: keep the copy identical" % name)
        # 5. no toy test patches a moved name on the old module
        for test in sorted(glob.glob(os.path.join(repo, "dev", "toy", "*.sh"))):
            text = open(test).read()
            for name in moved:
                if re.search(r"\b%s\.%s\s*=[^=]" % (old_name, re.escape(name)), text):
                    trouble.append("patch: %s sets %s.%s, which the moved code no longer sees. fix: patch %s.%s"
                                   % (os.path.relpath(test, repo), old_name, name, new, name))
        # negative control: a dropped name and a leftover def must both be caught
        defs = top_names(ast.parse(new_text))
        funcs = sorted(n for n in moved if isinstance(defs.get(n), ast.FunctionDef))
        node = next((n for n in ast.parse(old_text).body if isinstance(n, ast.ImportFrom) and n.module == new), None)
        if not funcs or node is None:  # the split itself is missing; checks 2 and 3 above already say so
            raise NoSplit
        name, line = funcs[0], ast.get_source_segment(old_text, node)
        names = [alias.name for alias in node.names]
        broken = old_text.replace(line, "from %s import %s  # noqa" % (new, ", ".join(n for n in names if n != name)))
        broken += "\n\ndef %s():\n    pass\n" % name
        caught, _ = static(broken, new_text, new, moved)
        if not (any(t.startswith("names:") for t in caught) and any(t.startswith("leftovers:") for t in caught)):
            trouble.append("control: a dropped name and a leftover def were not both caught. fix: repair split-check.py")
    except NoSplit:
        pass
    finally:
        shutil.rmtree(temp, ignore_errors=True)
    for line in trouble:
        print("%s: %s" % (old_rel, line))
    sys.exit(1 if trouble else 0)


if __name__ == "__main__":
    main()
