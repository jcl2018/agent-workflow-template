#!/usr/bin/env python3
"""Keep the criteria and test tables of wiki pages honest.

usage: criteria.py <command> [options]

  review ID [ID ...] --user    mark criteria Reviewed with today's date; --user means the owner's own words said so
  unreview ID [ID ...] --user  mark them Unreviewed again, so their wording may change
  render [--check]             rewrite each feature page's Tests table from the regression rows and their last runs;
                               --check only says which pages are stale

A page is Summary, Criteria and Tests. A criterion is '- ID: **Unreviewed** text' or '- ID: **Reviewed DATE** text',
and a Reviewed line ends with <!-- reviewed HASH -->, a hash of its text. docs.py check fails when the text no longer
matches its hash. A regression row whose goal column is '-' proves no criterion yet and is left out. The Tests table lists each criterion's regression rows with the criterion's words, what the
test checks, when it runs, its last status and date from .loop/regression-runs.tsv and whether it was seen failing,
and marks a criterion with no passing row as not enforced. It runs git and nothing else.
"""
import argparse
import datetime
import hashlib
import json
import os
import re
import subprocess
import sys

# No terminal, no waiting: a prompt from git or gh must fail, not block.
os.environ.update(GIT_TERMINAL_PROMPT="0", GH_PROMPT_DISABLED="1", GIT_EDITOR="true", GIT_ASKPASS="true", SSH_ASKPASS="true")
if not sys.stdin or not sys.stdin.isatty():
    os.dup2(os.open(os.devnull, os.O_RDONLY), 0)


LINE = re.compile(r"^- ([A-Z]{2,5}-\d+): \*\*(Unreviewed|Reviewed (\d{4}-\d\d-\d\d))\*\* (\S.*?)(?: <!-- reviewed (\w+) -->)?$")
ID = re.compile(r"^[A-Z]{2,5}-\d+$")
SCRIPT_FILE = re.compile(r"[\w./-]*\w\.(?:py|sh|bash|zsh|js|mjs|cjs|ts|rb|pl|php|ps1|bat)\b", re.I)
SHEET = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "references", "template.md")


def rules():
    """The page rules from the fenced rules block of the template sheet. Refuses when it is missing or incomplete."""
    try:
        with open(SHEET) as handle:
            block = re.search(r"^```rules\n(.*?)^```", handle.read(), re.M | re.S)
        found = dict(line.split(":", 1) for line in block.group(1).splitlines() if ":" in line)
        found = {key.strip(): value.strip() for key, value in found.items()}
        return {"sections": [x.strip() for x in found["sections"].split(",")], "summary_lines": int(found["summary_lines"]),
                "max_criteria": int(found["max_criteria"]), "columns": [x.strip() for x in found["tests_columns"].split(",")],
                "milestone": found["milestone_line"]}
    except (OSError, AttributeError, KeyError, ValueError):
        sys.exit("REFUSED: the rules block of skills/workflow-docs/references/template.md is missing or broken.")


def git(*args, check=True):
    done = subprocess.run(["git"] + list(args), capture_output=True, text=True)
    if check and done.returncode:
        sys.exit("REFUSED: git %s: %s" % (" ".join(args), done.stderr.strip()[:300]))
    return done.stdout.strip()


def seal(text):
    return hashlib.sha256(text.encode()).hexdigest()[:8]


def folder_of(root):
    try:
        with open(os.path.join(root, ".loop", "config.json")) as handle:
            return json.load(handle).get("wiki_dir") or "docs/wiki"
    except (OSError, ValueError):
        sys.exit("REFUSED: no readable .loop/config.json. Fix: run workflow-setup and merge its branch.")


def pages(root):
    folder = folder_of(root)
    try:
        names = sorted(name for name in os.listdir(os.path.join(root, folder)) if name.endswith(".md"))
    except OSError:
        return []
    return [os.path.join(folder, name) for name in names]


def sections(text):
    """The page's level-2 sections, as (name, lines), outside code fences."""
    found, fenced = [], False
    for line in text.splitlines():
        if line.startswith("```"):
            fenced = not fenced
        if not fenced and line.startswith("## "):
            found.append((line[3:].strip(), []))
        elif found:
            found[-1][1].append(line)
    return found


def tsv(root, name):
    try:
        with open(os.path.join(root, ".loop", name)) as handle:
            return [line.rstrip("\n").split("\t") + [""] * 5 for line in handle if line.strip() and line[0] != "#"]
    except OSError:
        return []


def test_rows(root):
    """Real tests as {criterion: [row id]}, plus ids linked to none."""
    linked, loose = {}, []
    for row in tsv(root, "regression.tsv"):
        key = "" if row[3] == "-" else next((item for item in (row[3], row[0]) if ID.match(item)), "")
        if row[1] == "draft":
            continue
        if key:
            linked.setdefault(key, []).append(row[0])
        elif row[3] != "-":
            loose.append(row[0])
    return linked, loose


RUNS = {"land": "both", "nightly": "nightly", "covered": "by a person"}


def table(root, ids, linked):
    """The Tests table: each criterion's rows with the criterion's words, what the test checks, when it runs, its
    last result and whether it was seen failing; 'not enforced' when no row passes. `ids` is (id, text) pairs."""
    ran = {row[0]: (row[1], row[2]) for row in tsv(root, "regression-runs.tsv")}
    rows = {row[0]: row for row in tsv(root, "regression.tsv")}
    link = "../" * (folder_of(root).count("/") + 1) + ".loop/regression.tsv"
    head = rules()["columns"]
    out = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    for key, text in ids:
        words = ("**%s** %s" % (key, text)).replace("|", "\\|")
        passing = False
        for name in linked.get(key, []):
            status, date = ran.get(name, ("not run", ""))
            passing = passing or status == "PASS"
            row = rows[name]
            out.append("| %s | [%s](%s) | %s | %s | %s | %s |" % (words, name, link, row[5].replace("|", "\\|") or "-",
                       RUNS.get(row[1], row[1]), (status + " " + date).strip(), row[4] or "no"))
        if not passing:
            out.append("| %s | **not enforced** | | | | |" % words)
    return out


def criteria_of(lines):
    return [(line, LINE.match(line)) for line in lines if line.strip()]


def contract(root, names, seen):
    """Page contract trouble for these feature pages, as (kind, page, detail). `seen` maps ids to their page."""
    found, rule = [], rules()
    linked, loose = test_rows(root)
    for page in names:
        with open(os.path.join(root, folder_of(root), page + ".md")) as handle:
            parts = sections(handle.read())
        if [name for name, _ in parts] != rule["sections"]:
            found.append(("SECTIONS", page, "have %s, want %s" % (", ".join(n for n, _ in parts) or "none", ", ".join(rule["sections"]))))
            continue
        body, ids = dict(parts), []
        for line, match in criteria_of(body["Criteria"]):
            if not match:
                found.append(("CRITERION", page, "not one line '- ID: **Unreviewed** text': " + line.strip()[:60]))
                continue
            key, mark, text, mine = match.group(1), match.group(2), match.group(4), match.group(5)
            if key in seen:
                found.append(("DUPLICATE", page, "%s is also in %s" % (key, seen[key])))
                continue
            seen[key] = page
            ids.append((key, text))
            named = SCRIPT_FILE.findall(text)
            if named:
                found.append(("SCRIPT", page, "%s names %s. Fix: say what it does, not the file" % (key, ", ".join(named))))
            if mark != "Unreviewed" and mine != seal(text):
                found.append(("LOCKED", page, "%s was reviewed and its wording changed. Fix: restore it, or the owner "
                              "marks it Unreviewed first" % key))
        if len(ids) > rule["max_criteria"]:
            found.append(("CAP", page, "has %d criteria, over the cap of %d" % (len(ids), rule["max_criteria"])))
        if len([x for x in "\n".join(body["Summary"]).split("\n\n") if x.strip()]) > rule["summary_lines"]:
            found.append(("SUMMARY", page, "is over %d lines" % rule["summary_lines"]))
        if [line for line in body["Tests"] if line.strip()] != table(root, ids, linked):
            found.append(("TESTS", page, "the Tests table is stale. Fix: run criteria.py render"))
    for name in loose:
        found.append(("LINK", "regression", "row %s links to no criterion" % name))
    for key in sorted(set(linked) - set(seen)):
        found.append(("LINK", "regression", "rows link to %s, which no page has" % key))
    return found


def rewrite(root, change):
    """Run change(match) over every criterion line. It returns a new line, or None to leave it."""
    touched, names = [], []
    for rel in pages(root):
        with open(os.path.join(root, rel)) as handle:
            text = handle.read()
        lines = text.split("\n")
        for number, line in enumerate(lines):
            match = LINE.match(line)
            fresh = change(match) if match else None
            if fresh:
                lines[number] = fresh
                names.append(match.group(1))
        if "\n".join(lines) != text:
            touched.append((rel, "\n".join(lines)))
    return touched, names


def write(root, touched):
    for rel, text in touched:
        with open(os.path.join(root, rel), "w") as handle:
            handle.write(text)


def mark_all(args, make):
    if not args.user:
        sys.exit("REFUSED: only the owner changes a criterion's review. Fix: pass --user when their own words said to.")
    bad = [key for key in args.ids if not ID.match(key)]
    if bad:
        sys.exit("REFUSED: not a criterion id: %s." % ", ".join(bad))
    root = git("rev-parse", "--show-toplevel")
    touched, names = rewrite(root, lambda match: make(match) if match.group(1) in args.ids else None)
    missing = sorted(set(args.ids) - {match for match in names})
    if missing:
        sys.exit("REFUSED: no criterion %s. Nothing was changed." % ", ".join(missing))
    write(root, touched)
    return names


def cmd_review(args):
    day = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    for key in mark_all(args, lambda m: "- %s: **Reviewed %s** %s <!-- reviewed %s -->" % (m.group(1), day, m.group(4), seal(m.group(4)))):
        print("REVIEWED " + key)
    return 0


def cmd_unreview(args):
    for key in mark_all(args, lambda m: "- %s: **Unreviewed** %s" % (m.group(1), m.group(4))):
        print("UNREVIEWED " + key)
    return 0


def cmd_render(args):
    root = git("rev-parse", "--show-toplevel")
    linked, _ = test_rows(root)
    stale = []
    for rel in pages(root):
        with open(os.path.join(root, rel)) as handle:
            text = handle.read()
        parts = sections(text)
        if [name for name, _ in parts] != rules()["sections"]:
            continue
        ids = [(m.group(1), m.group(4)) for _, m in criteria_of(dict(parts)["Criteria"]) if m]
        head, _, _ = text.partition("\n## Tests")
        fresh = head + "\n## Tests\n\n" + "\n".join(table(root, ids, linked)) + "\n"
        if fresh != text:
            stale.append(rel)
            if not args.check:
                with open(os.path.join(root, rel), "w") as handle:
                    handle.write(fresh)
    for rel in stale:
        print("%s %s" % ("STALE" if args.check else "RENDERED", rel))
    if not stale:
        print("TABLES OK")
    return 1 if stale and args.check else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    for name, func in (("review", cmd_review), ("unreview", cmd_unreview)):
        item = sub.add_parser(name)
        item.add_argument("ids", nargs="+")
        item.add_argument("--user", action="store_true", help="the owner's own words said so")
        item.set_defaults(func=func)
    item = sub.add_parser("render")
    item.add_argument("--check", action="store_true")
    item.set_defaults(func=cmd_render)
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
