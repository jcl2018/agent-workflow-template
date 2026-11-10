#!/usr/bin/env python3
"""List every regression test in one fixed format, grouped by feature.

usage: tests.py <command> [--root DIR]

  list [--markdown|--tsv]           every test from the recorded runs, one group per feature
  summary --results FILE --took S   a GitHub run summary: one header with totals and the run time, then one table per
                                    feature, from that run's results file (id<TAB>state lines; # lines are skipped)
  issues [--write]                  read each defect test's issue or pull request state with gh; --write records them in
                                    .loop/regression-issues.tsv (link, state, date) for the wiki and the health report

A feature is the wiki page that holds the requirement a row guards (its goal, or its id); a row that guards none is in
Other. Each test shows: test, kind (requirement or defect), what it guards (the requirement's ID and words, or the
issue's link and state), what it checks, when it runs, its last result and date, and when it was seen failing.
Stdlib only and self-contained: the regression workflow carries a copy of this file.
"""
import argparse
import datetime
import glob
import json
import os
import re
import subprocess
import sys

# No terminal, no waiting: a prompt from git or gh must fail, not block.
os.environ.update(GIT_TERMINAL_PROMPT="0", GH_PROMPT_DISABLED="1", GIT_EDITOR="true", GIT_ASKPASS="true", SSH_ASKPASS="true")
if not sys.stdin or not sys.stdin.isatty():
    os.dup2(os.open(os.devnull, os.O_RDONLY), 0)

ID = re.compile(r"^[A-Z]{2,5}-\d+$")
SEEN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
KIND = {"criterion": "requirement", "defect": "defect"}
RUNS = {"land": "both", "nightly": "nightly", "covered": "by a person"}
STATES = ("PASS", "FAIL", "SKIPPED", "KNOWN")
COLUMNS = ("Test", "Kind", "Guards", "Checks", "Runs", "Last result", "Seen failing")
OTHER = "Other"


def tsv(root, name):
    path = os.path.join(root, ".loop", name)
    if not os.path.exists(path):
        return []
    with open(path) as handle:
        return [line.rstrip("\n").split("\t") for line in handle if line.strip() and not line.startswith("#")]


def cell(text):
    """One table cell: whitespace runs (newlines too) collapsed, and | escaped so it can't split a column."""
    return " ".join(str(text).split()).replace("|", "\\|") or "-"


def features(root):
    """(page titles in page order, {requirement id: (title, words)}); an id on two pages stays with the first."""
    try:
        with open(os.path.join(root, ".loop", "config.json")) as handle:
            folder = json.load(handle).get("wiki_dir") or "docs/wiki"
    except (OSError, ValueError):
        folder = "docs/wiki"
    titles, found = [], {}
    for name in sorted(glob.glob(os.path.join(root, folder, "*.md"))):
        with open(name) as handle:
            text = re.sub(r"(?ms)^```.*?^```[^\n]*$", "", handle.read())
        head = re.search(r"^# (.+)$", text, re.M)
        title = head.group(1).strip() if head else os.path.basename(name)[:-3]
        part = re.split(r"\n## (?:Requirements|Criteria)[ \t]*\n", text, maxsplit=1)
        if len(part) < 2:
            continue
        titles.append(title)
        for key, words in re.findall(r"^- ([A-Z]{2,5}-\d+): (.*)$", part[1].split("\n## ", 1)[0], re.M):
            words = re.sub(r"<!--.*?-->", "", re.sub(r"^\*\*(?:Reviewed|Unreviewed)[^*]*\*\*\s*", "", words)).strip()
            found.setdefault(key, (title, words))
    return titles, found


def key_of(row):
    """The requirement a row guards: its goal, or its own id, when either is an ID; '-' guards none."""
    return "" if row[3] == "-" else next((item for item in (row[3], row[0]) if ID.match(item)), "")


def issues_of(root):
    return {row[0]: (row[1], row[2] if len(row) > 2 else "") for row in tsv(root, "regression-issues.tsv") if len(row) > 1}


def guard(row, found, issues, markdown):
    """What a test guards: the issue link and its recorded state for a defect, else the requirement's ID and words."""
    link = row[7]
    if row[6] == "defect" and link:
        number = re.search(r"/(issues|pull)/(\d+)$", link)
        if not number:
            return link.replace("finding:", "finding ", 1)
        state, day = issues.get(link, ("state unknown", ""))
        name = ("#" if number.group(1) == "issues" else "PR ") + number.group(2)
        shown = "[%s](%s)" % (name, link) if markdown else "%s %s" % (name, link)
        return "%s %s%s" % (shown, state.lower(), " (%s)" % day if day else "")
    key = key_of(row)
    if key:
        return "%s: %s" % (key, found[key][1]) if key in found else key
    return "done line " + row[3] if re.match(r"^[\w-]+:\d+$", row[3]) else "-"


def fields(row, found, ran, issues, markdown=False):
    """The one fixed format for one row (all 8 columns of regression.tsv): test, kind, guards, checks, runs, last
    result and date, seen failing."""
    status, day = ran.get(row[0], ("not run", ""))
    return [cell(item) for item in (row[0], KIND.get(row[6] or "criterion", row[6]), guard(row, found, issues, markdown),
                                    row[5] or "-", RUNS.get(row[1], row[1] or "-"), (status + " " + day).strip(),
                                    row[4] if SEEN.match(row[4]) else "no")]


def entries(root, results=None, markdown=False):
    """[(feature, [fields])] in page order, then Other; rows in file order, draft rows left out. With results, only
    the rows that run reported, each with that run's state."""
    titles, found = features(root)
    ran = {row[0]: (row[1], row[2] if len(row) > 2 else "") for row in tsv(root, "regression-runs.tsv") if len(row) > 1}
    if results is not None:
        ran = {name: (state, "") for name, state in results.items()}
    issues, groups = issues_of(root), {}
    rows = {row[0]: (row + [""] * 8)[:8] for row in tsv(root, "regression.tsv")}
    order = [name for name in rows if rows[name][1] != "draft"] if results is None else list(results)
    for name in order:
        row = rows.get(name) or [name, "", "", "-", "", "", "", ""]
        key = key_of(row)
        groups.setdefault(found[key][0] if key in found else OTHER, []).append(fields(row, found, ran, issues, markdown))
    return [(title, groups[title]) for title in titles + [OTHER] if title in groups]


def table(header, lines):
    return ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)] + ["| " + " | ".join(x) + " |" for x in lines]


def cmd_list(args):
    out = []
    for feature, lines in entries(args.root, markdown=args.markdown):
        if args.tsv:
            out += ["\t".join([feature] + each) for each in lines]
        elif args.markdown:
            out += ["### " + feature, ""] + table(COLUMNS, lines) + [""]
        else:
            out += ["FEATURE " + feature] + [" | ".join(each[:6]) + " | seen failing " + each[6] for each in lines]
    print("\n".join(out).rstrip("\n") if out else "NO TESTS")
    return 0


def refuse(text):
    sys.stderr.write("REFUSED: %s\n" % text)
    return 2


def cmd_summary(args):
    try:
        took = float(args.took)
        if took < 0:
            raise ValueError
    except ValueError:
        return refuse("--took %r is not a number of seconds. Fix: pass the run's seconds, e.g. --took 95" % args.took)
    try:
        with open(args.results) as handle:
            raw = handle.read().splitlines()
    except OSError as err:
        return refuse("can't read the results file %s: %s. Fix: pass the file the run wrote" % (args.results, err.strerror))
    results = {}
    for number, line in enumerate(raw, 1):
        if not line.strip() or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) != 2 or parts[1] not in STATES:
            return refuse("%s:%d is %r, not id<TAB>state with a state in %s. Fix: correct that line"
                          % (args.results, number, line[:80], ", ".join(STATES)))
        results[parts[0]] = parts[1]
    count = {state: sum(1 for value in results.values() if value == state) for state in STATES}
    minutes, seconds = divmod(int(round(took)), 60)
    out = ["## Regression: %d passed, %d failed, %d known, %d skipped of %d, in %dm %02ds"
           % (count["PASS"], count["FAIL"], count["KNOWN"], count["SKIPPED"], len(results), minutes, seconds), ""]
    for feature, lines in entries(args.root, results, markdown=True):
        out += ["### " + feature, ""] + table(("Test", "Kind", "Guards", "Checks", "Result"),
                                              [x[:4] + [x[5]] for x in lines]) + [""]
    print("\n".join(out).rstrip("\n"))
    return 0


def gh(*args):
    try:
        return subprocess.run(("gh",) + args, capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError) as err:
        return subprocess.CompletedProcess(args, 1, "", str(err))


def cmd_issues(args):
    probe = gh("auth", "status")
    if probe.returncode:
        cause = (probe.stderr or probe.stdout).strip().splitlines()
        sys.stderr.write("ISSUES: cannot read issues (gh: %s). Fix: gh auth login, or set GH_TOKEN\n"
                         % (cause[0][:120] if cause else "not available"))
        return 1
    old, day, out = issues_of(args.root), datetime.date.today().isoformat(), {}
    for row in tsv(args.root, "regression.tsv"):
        link = row[7] if len(row) > 7 else ""
        kind = re.search(r"/(issues|pull)/\d+$", link)
        if row[6:7] != ["defect"] or not kind:
            continue
        done = gh("issue" if kind.group(1) == "issues" else "pr", "view", link, "--json", "state", "-q", ".state")
        state = done.stdout.strip().lower()
        out[link] = (state, day) if not done.returncode and state else old.get(link, ("unknown", day))
        print("ISSUE %s %s" % (link, out[link][0]))
    if args.write:
        with open(os.path.join(args.root, ".loop", "regression-issues.tsv"), "w") as handle:
            handle.write("# link\tstate\tdate\n" + "".join("%s\t%s\t%s\n" % (k, *v) for k, v in sorted(out.items())))
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    item = sub.add_parser("list")
    shape = item.add_mutually_exclusive_group()
    shape.add_argument("--markdown", action="store_true")
    shape.add_argument("--tsv", action="store_true")
    item.set_defaults(func=cmd_list)
    item = sub.add_parser("summary")
    item.add_argument("--results", required=True)
    item.add_argument("--took", required=True)
    item.set_defaults(func=cmd_summary)
    item = sub.add_parser("issues")
    item.add_argument("--write", action="store_true")
    item.set_defaults(func=cmd_issues)
    for each in sub.choices.values():
        each.add_argument("--root", default="")
    args = parser.parse_args()
    if not args.root:
        top = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True)
        args.root = top.stdout.strip() or os.getcwd()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
