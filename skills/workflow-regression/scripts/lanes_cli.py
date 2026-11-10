#!/usr/bin/env python3
"""Ask lanes.py which regression rows a change can affect, what a row depends on, and whether test headers hold.

usage: lanes_cli.py affected [--root DIR] [--level land|nightly|all] PATH...
       lanes_cli.py deps [--root DIR] COMMAND [--why PATH]
       lanes_cli.py check [--root DIR] [SCRIPT...]

affected  dependency impact of a change to PATH: `AFFECTED n of m rows (ids)`, plus `ALWAYS <id>: <reason>` for rows
          that run on every change, `UNMAPPED <path>` or `DELETED <path>` when the change means a full run. No record is
          read, so failed rows, ancestry and edited table rows (which a reuse run also reruns) are outside it.
deps      a row command's dependency paths, sorted, then `ALWAYS <command>: <reason>`; --why prints the chain of files
          from the command to PATH, or NOT REACHED.
check     every `# reads:` problem of the test scripts (default: each dev/toy/test-*.sh a row of the table names), one
          `<CODE> <file>:<line>: <what>` line and a `fix:` line each. Exit 0 clean, 1 problems.
The root is the git top level of the current directory unless --root is given. Usage errors exit 2 on stderr;
LANES_DEBUG=1 shows the full trace of an unexpected error. Read-only.
"""
import argparse
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lanes  # noqa: E402
import narrow  # noqa: E402

os.environ.update(GIT_TERMINAL_PROMPT="0", GH_PROMPT_DISABLED="1", GIT_EDITOR="true", GIT_ASKPASS="true", SSH_ASKPASS="true")

FIX = {
    "LANES-DECL-NONE": "add '# reads: <the skill files it runs>' to the comment block at the top of {file}",
    "LANES-DECL-PLACE": "move the # reads: line into the comment block at the top of {file}",
    "LANES-DECL-PATTERN": "declare each file, or the skill folder the script globs (e.g. skills/x/scripts/)",
    "LANES-DECL-ESCAPE": "declare repo-relative paths only",
    "LANES-DECL-MISSING": "fix the path or remove it from # reads: in {file}",
    "LANES-DECL-FOLDER-UNBACKED": "declare the files {file} runs instead of the folder",
    "LANES-DECL-GLOB": "declare the globbed folder itself in {file}'s # reads: line (a new file there must rerun it)",
    "LANES-DECL-FOLDER": "add the files {file} runs from that folder to its # reads: line",
    "LANES-DECL-TREE": "add skills/ to the # reads: line of {file} (it stays wide: it reads every skill)",
}
TEST = re.compile(r"(?<![\w./-])(dev/toy/test-[\w-]+\.sh)")


def usage(message):
    sys.stderr.write("lanes_cli.py: %s\n" % message)
    sys.exit(2)


def top(given):
    if given:
        return os.path.abspath(given)
    done = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    if done.returncode:
        usage("not inside a git repo; run from the repo or pass --root DIR")
    return done.stdout.strip()


def rows_of(root, level):
    path = os.path.join(root, ".loop", "regression.tsv")
    if not os.path.isfile(path):
        usage("no .loop/regression.tsv under %s; run from the repo or pass --root" % root)
    rows = []
    with open(path) as handle:
        for number, line in enumerate(handle, 1):
            cells = line.rstrip("\n").split("\t")
            if not line.strip() or line.startswith("#"):
                continue
            if len(cells) < 3:
                raise ValueError(".loop/regression.tsv:%d has fewer than 3 columns" % number)
            if level == "all" or cells[1] == level:
                rows.append({"id": cells[0], "level": cells[1], "command": cells[2]})
    return rows


def relative(root, path):
    here = os.path.realpath(os.getcwd())
    base = here if (here + "/").startswith(os.path.realpath(root) + "/") else root  # relative to --root from outside it
    full = os.path.realpath(os.path.join(base, path))
    rel = os.path.relpath(full, os.path.realpath(root))
    if rel.startswith(".."):
        usage("path outside the repo: %s" % path)
    return rel


def affected(root, rows, paths, cache):
    """(rerun ids, notes) for a change to paths: plan()'s per-path rules without a record (dependency impact only)."""
    ids, notes, every = set(), [], [r["id"] for r in rows]
    for row in rows:
        lanes.closure(root, row["command"], cache)
        if cache.get(("why", row["command"])):
            notes.append("ALWAYS %s: %s" % (row["id"], cache["why", row["command"]]))
    for path in paths:
        if not os.path.exists(os.path.join(root, path)) and not any(
                path == n or (n.endswith("/") and path.startswith(n)) for n in lanes.NO_EFFECT):
            return every, notes + ["DELETED %s: full run" % path]
        if path in (lanes.TABLE, ".loop/regression-known.tsv"):  # never unmapped; a record would add the edited rows
            hit = {r["id"] for r in rows if lanes.reads_table(root, r["command"], cache)}  # plus edited rows (needs a record)
        else:
            hit = {r["id"] for r in rows if lanes.touches(root, r["command"], path, cache)}
        no_effect = path in (lanes.TABLE, ".loop/regression-known.tsv") or any(
            path == n or (n.endswith("/") and path.startswith(n)) for n in lanes.NO_EFFECT)
        if not hit and not no_effect and not any(lanes.hits(path, lanes.closure(root, r["command"], cache)[0])
                                                 for r in rows):
            return every, notes + ["UNMAPPED %s: full run; no row reads it (add it to a script's # reads: if one "
                                   "should)" % path]
        ids |= hit
    ids |= {r["id"] for r in rows if lanes.closure(root, r["command"], cache)[1]}
    return sorted(ids), notes


def check(root, scripts, cache):
    """Every header problem of the test scripts as (code, file, line, what), LANES-DECL-NONE for a missing header."""
    out = []
    for rel in scripts:
        paths, problems = narrow.header(root, rel, cache)
        if paths is None and not problems:
            out.append(("LANES-DECL-NONE", rel, 1, "test script has no # reads: header"))
            continue
        out += problems + narrow.narrow(root, [rel], cache)[1]
    return sorted(set(out), key=lambda p: (p[1], p[2], p[0], p[3]))


def chain(parent, path):
    links = [path]
    while parent.get(links[-1]) and parent[links[-1]] not in links:
        links.append(parent[links[-1]])
    return " -> ".join(reversed(links))


def main():
    parser = argparse.ArgumentParser(prog="lanes_cli.py")
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name in ("affected", "deps", "check"):
        item = sub.add_parser(name)
        item.add_argument("--root")
    sub.choices["affected"].add_argument("--level", default="land", choices=("land", "nightly", "all"))
    sub.choices["affected"].add_argument("paths", nargs="+", metavar="PATH")
    sub.choices["deps"].add_argument("command")
    sub.choices["deps"].add_argument("--why", metavar="PATH")
    sub.choices["check"].add_argument("scripts", nargs="*", metavar="SCRIPT")
    args = parser.parse_args()
    root, cache = top(args.root), {}
    if args.cmd == "affected":
        rows = rows_of(root, args.level)
        ids, notes = affected(root, rows, [relative(root, p) for p in args.paths], cache)
        print("AFFECTED %d of %d rows (%s)" % (len(ids), len(rows), ", ".join(ids)))
        print("\n".join(sorted(set(notes)))) if notes else None
        return 0
    if args.cmd == "deps":
        deps, always = lanes.closure(root, args.command, cache)
        if args.why:
            target = relative(root, args.why)
            parent = cache.get(("chain", args.command), {})
            reached = lanes.hits(target, deps)
            print(chain(parent, target) if reached and target in parent else
                  ("%s (wide mapping)" % target if reached else "NOT REACHED %s" % target))
            return 0
        print("\n".join(sorted(deps)))
        if always:
            print("ALWAYS %s: %s" % (args.command, cache.get(("why", args.command)) or "names no repo path or the "
                                                                                      "whole repo"))
        return 0
    scripts = [relative(root, s) for s in args.scripts] or sorted(
        {m for r in rows_of(root, "all") for m in TEST.findall(r["command"])})
    problems = check(root, scripts, cache)
    for code, rel, line, what in problems:
        print("%s %s:%d: %s\nfix: %s" % (code, rel, line, what, FIX.get(code, "").format(file=rel)))
    return 1 if problems else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError) as error:
        if os.environ.get("LANES_DEBUG") == "1":
            raise
        sys.stderr.write("lanes_cli.py: unexpected error: %s (LANES_DEBUG=1 for the trace)\n" % error)
        sys.exit(1)
