#!/usr/bin/env python3
"""Keep the requirements and Tests of PRD wiki pages honest.

usage: criteria.py <command> [options]

  review ID|PAGE [...] --user [--date D]
                               mark requirements, or a whole PRD, Reviewed with today's date (or D); --user means the
                               owner's own words said so
  unreview ID|PAGE [...] --user
                               mark them Unreviewed again, so their wording may change
  render [--check]             rewrite each feature page's Tests from the regression rows and their last runs;
                               --check only says which pages are stale

A feature page is a short PRD (references/template.md): a Review line, then Problem, an optional Usage, Requirements,
Non-goals, Success metrics and Tests. Requirements hold up to criteria_max lines (default 6, .loop/config.json). A
requirement is '- ID: **Unreviewed** text' or '- ID: **Reviewed DATE** text', and a Reviewed line ends with
<!-- reviewed HASH -->, a hash of its text; docs.py check fails when the text no longer matches. An argument shaped like
an ID (two to five capitals, a dash, a number) is a requirement; any other is a page, whose PRD review prd.py writes.
A regression row whose goal column is '-' proves no requirement yet and is left out. Tests lists, under each
requirement, one Given/When/Then scenario per row: the row's description, the row, when it runs, its last status and
date from .loop/regression-runs.tsv and when it was seen failing, and marks a requirement with no passing row as not
enforced. A row with category defect is listed under 'Defect tests' on the page of the requirement in its goal column.
It runs git and nothing else.
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
SCENARIO = re.compile(r"^Given .+, when .+, then .+", re.I)
DAY = re.compile(r"^\d{4}-\d\d-\d\d$")
SCRIPT_FILE = re.compile(r"[\w./-]*\w\.(?:py|sh|bash|zsh|js|mjs|cjs|ts|rb|pl|php|ps1|bat)\b", re.I)
SHEET = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "references", "template.md")
FORMAT = os.path.join(os.path.dirname(SHEET), "..", "..", "workflow-regression", "scripts", "tests.py")  # the one test format


def rules():
    """The page rules from the fenced rules block of the template sheet. Refuses when it is missing or incomplete."""
    try:
        with open(SHEET) as handle:
            block = re.search(r"^```rules\n(.*?)^```", handle.read(), re.M | re.S)
        found = dict(line.split(":", 1) for line in block.group(1).splitlines() if ":" in line)
        found = {key.strip(): value.strip() for key, value in found.items()}
        return {"sections": [x.strip() for x in found["sections"].split(",")], "problem_lines": int(found["problem_lines"]),
                "metrics_lines": int(found["metrics_lines"]), "usage": found.get("usage_section", "Usage"),
                "review": found["review_line"], "milestone": found["milestone_line"]}
    except (OSError, AttributeError, KeyError, ValueError):
        sys.exit("REFUSED: the rules block of skills/workflow-docs/references/template.md is missing or broken.")


def criteria_max(root):
    """The criteria limit: `criteria_max` in .loop/config.json, 6 when absent. A bad value refuses, never falls back."""
    path = os.path.join(root, ".loop", "config.json")
    try:
        with open(path) as handle:
            value = json.load(handle).get("criteria_max", 6)
    except (OSError, ValueError, AttributeError):
        value = 6
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 50:
        sys.exit("REFUSED: criteria_max is %r in %s. Fix: set it to a whole number from 1 to 50, or remove it for the default 6."
                 % (value, path))
    return value


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
            return [line.rstrip("\n").split("\t") + [""] * 8 for line in handle if line.strip() and line[0] != "#"]
    except OSError:
        return []


def test_rows(root):
    """Real tests as {criterion: [row id]}, plus ids linked to none."""
    linked, loose = {}, []
    for row in tsv(root, "regression.tsv"):
        if row[6] == "defect":
            continue
        key = "" if row[3] == "-" else next((item for item in (row[3], row[0]) if ID.match(item)), "")
        if row[1] == "draft":
            continue
        if key:
            linked.setdefault(key, []).append(row[0])
        elif row[3] != "-":
            loose.append(row[0])
    return linked, loose


def defect_rows(root):
    """Defect tests as {criterion whose page they guard: [row id]}; a row with goal '-' belongs to no page."""
    found = {}
    for row in tsv(root, "regression.tsv"):
        if row[6] == "defect" and row[1] != "draft" and ID.match(row[3]):
            found.setdefault(row[3], []).append(row[0])
    return found


def issue_cell(link):
    """A defect's link as a table cell: the issue number linked to its URL, or the finding's id."""
    number = re.search(r"/(?:issues|pull)/(\d+)$", link)
    return "[#%s](%s)" % (number.group(1), link) if number else link.replace("finding:", "finding ", 1)


RUNS = {"land": "both", "nightly": "nightly", "covered": "by a person"}
SEEN = re.compile(r"\d{4}-\d{2}-\d{2}$")  # seen_red counts only as a date; anything else shows "no"


def tests_format(held={}):
    """workflow-regression's tests.py, which owns the test format, loaded once; None, with a NOTE, when it isn't installed."""
    import importlib.util
    if "m" in held:
        return held["m"]
    sys.dont_write_bytecode, held["m"] = True, None  # no __pycache__ in a skill folder: the package check refuses one
    if not os.path.exists(FORMAT):
        sys.stderr.write("NOTE: %s not found; Tests lines use the old shape\n" % os.path.normpath(FORMAT))
        return None
    spec = importlib.util.spec_from_file_location("regression_tests", FORMAT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    held["m"] = module
    return module


def scenario(row, ran, link, cell="", fmt=None, issues=None):
    """One Tests line: the row's Given/When/Then description, then tests.py's fields: the row, its kind, what it
    guards, when it runs, its last result and when it was seen failing."""
    status, date = ran.get(row[0], ("not run", ""))
    words = row[5] or "-"
    if not SCENARIO.match(words):
        words += " (not yet Given/When/Then)"
    if fmt:
        f = fmt.fields((row + [""] * 8)[:8], {}, ran, issues or {}, True)
        return "- %s — [%s](%s), %s, guards %s, %s, %s, seen failing %s" % (words, row[0], link, *f[1:3], *f[4:])
    return "- %s — %s[%s](%s), %s, %s, seen failing %s" % (words, cell, row[0], link, RUNS.get(row[1], row[1]),
                                                       (status + " " + date).strip(), row[4] if SEEN.match(row[4]) else "no")


def table(root, ids, linked):
    """The Tests section: per requirement a '#### ID' heading, its words and one scenario line per row; 'not enforced'
    when no row passes; then the defect tests. `ids` is (id, text) pairs. Blank lines separate the parts."""
    ran = {row[0]: (row[1], row[2]) for row in tsv(root, "regression-runs.tsv")}
    rows = {row[0]: row for row in tsv(root, "regression.tsv")}
    link = "../" * (folder_of(root).count("/") + 1) + ".loop/regression.tsv"
    out, fmt = [], tests_format()
    issues = fmt.issues_of(root) if fmt else {}
    for key, text in ids:
        out += ["#### " + key, "", text, ""]
        passing = False
        for name in linked.get(key, []):
            passing = passing or ran.get(name, ("",))[0] == "PASS"
            out.append(scenario(rows[name], ran, link, "", fmt, issues))
        if not passing:
            out.append("- **not enforced**: no passing test")
        out.append("")
    guards = defect_rows(root)
    names = [name for key, _ in ids for name in guards.get(key, [])]
    if names:
        out += ["### Defect tests", ""]
    for name in names:
        out.append(scenario(rows[name], ran, link, issue_cell(rows[name][7]) + ", ", fmt, issues))
    return out[:-1] if out and out[-1] == "" else out


def criteria_of(lines):
    return [(line, LINE.match(line)) for line in lines if line.strip()]


def usage_trouble(root, lines):
    """Problems in a Usage block: a script file or python/bash command named, or a `/skill verb` missing from that skill's Command map."""
    out, base = [], os.path.join(root, "skills")
    for command in re.findall(r"`([^`]+)`", "\n".join(lines)):
        script = re.search(r"\b([\w-]+\.(?:py|sh))\b", command)
        if script or re.match(r"(python3?|bash|sh)\s", command):
            out.append("`%s` names a script. Fix: write it as an agent request or a /skill verb" % command)
            continue
        ask = re.match(r"/([\w-]+)\s+([\w-]+)", command)
        path = os.path.join(base, ask.group(1) if ask else "", "SKILL.md")
        if ask and os.path.isfile(path):
            with open(path) as handle:
                if not re.search(r"^\| `/%s %s[ `]" % (re.escape(ask.group(1)), re.escape(ask.group(2))), handle.read(), re.M):
                    out.append("`%s` is not in the Command map of skills/%s/SKILL.md. Fix: use a mapped verb" % (command, ask.group(1)))
    return out


def contract(root, names, seen):
    """Page contract trouble for these feature pages, as (kind, page, detail). `seen` maps ids to their page."""
    import prd
    found, rule = [], rules()
    limit = criteria_max(root)
    linked, loose = test_rows(root)
    head = rule["sections"]
    for page in names:
        with open(os.path.join(root, folder_of(root), page + ".md")) as handle:
            text = handle.read()
        parts = sections(text)
        have = [name for name, _ in parts]
        want = head[:1] + [rule["usage"]] + head[1:] if rule["usage"] in have else head
        if have != want:
            hint = ""
            if "Commands" in have:
                hint = ". Fix: rename Commands to %s and place it between %s and %s" % (rule["usage"], head[0], head[1])
            elif "Summary" in have or "Criteria" in have:
                hint = ". Fix: run prd.py convert --write (workflow-docs), then write the Non-goals and Success metrics drafts"
            else:
                hint = ". Fix: use exactly these sections, in this order, and nothing else"
            found.append(("SECTIONS", page, "have %s, want %s%s" % (", ".join(have) or "none", ", ".join(want), hint)))
            continue
        body, ids = dict(parts), []
        found += prd.trouble(root, page, text, parts, rule)
        if rule["usage"] in body:
            if not [x for x in body[rule["usage"]] if x.strip()]:
                found.append(("USAGE", page, "has an empty %s section. Fix: list its commands, or remove the section" % rule["usage"]))
            for trouble in usage_trouble(root, body[rule["usage"]]):
                found.append(("USAGE", page, trouble))
        for line, match in criteria_of(body[head[1]]):
            if not match:
                found.append(("CRITERION", page, "not one line '- ID: **Unreviewed** text' under %s: %s" % (head[1], line.strip()[:60])))
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
        if len(ids) > limit:
            found.append(("CAP", page, "has %d requirements, over the limit of %d (criteria_max in .loop/config.json). Fix: merge "
                          "requirements, or raise criteria_max" % (len(ids), limit)))
        if len(prd.paras(body[head[0]])) > rule["problem_lines"]:
            found.append(("PROBLEM", page, "is over %d lines. Fix: say who it is for and what it solves in %d lines or fewer"
                          % (rule["problem_lines"], rule["problem_lines"])))
        if [line for line in body["Tests"] if line.strip()] != [line for line in table(root, ids, linked) if line.strip()]:
            found.append(("TESTS", page, "the Tests section is stale. Fix: run criteria.py render"))
    for name in loose:
        found.append(("LINK", "regression", "row %s links to no requirement" % name))
    for key in sorted(set(defect_rows(root)) - set(seen)):
        found.append(("LINK", "regression", "defect tests guard %s, which no page has" % key))
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


def today():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")


def mark_all(args, make, page_change):
    """Validate every argument, then change the requirement lines (make) and the PRD review lines (page_change).
    Nothing is written unless every argument is good."""
    if not args.user:
        sys.exit("REFUSED: only the owner changes a review. Fix: pass --user when their own words said to.")
    day = getattr(args, "date", None) or today()
    if not DAY.match(day) or day > today():
        sys.exit("REFUSED: --date %s is not a YYYY-MM-DD date on or before today (%s, UTC). Fix: --date 2026-11-08." % (day, today()))
    root = git("rev-parse", "--show-toplevel")
    keys = [key for key in args.ids if ID.match(key)]
    names = [key for key in args.ids if not ID.match(key)]
    touched, found = rewrite(root, lambda match: make(match, day) if match.group(1) in keys else None)
    missing = sorted(set(keys) - set(found))
    if missing:
        sys.exit("REFUSED: no requirement %s (an ID matches ^[A-Z]{2,5}-\\d+$). Nothing was changed. Fix: use an ID "
                 "from a page's Requirements." % ", ".join(missing))
    held = dict(touched)
    known = {os.path.basename(rel)[:-3]: rel for rel in pages(root)}  # exact names, keyed like rewrite()'s
    for name in names:
        rel = known.get(name)
        if name == "Home" or not rel:
            sys.exit("REFUSED: %s is not a feature page (a page is a file in %s other than Home; an ID matches "
                     "^[A-Z]{2,5}-\\d+$). Nothing was changed. Fix: name a page such as Delivery, or a requirement ID."
                     % (name, folder_of(root)))
        if rel not in held:
            with open(os.path.join(root, rel)) as handle:
                held[rel] = handle.read()
        fresh, why = page_change(held[rel], day, name)
        if why:
            sys.exit("REFUSED: %s: %s. Nothing was changed." % (name, why))
        held[rel] = fresh
    write(root, held.items())
    return found, names


def cmd_review(args):
    import prd
    keys, names = mark_all(args, lambda m, day: "- %s: **Reviewed %s** %s <!-- reviewed %s -->" % (
        m.group(1), day, m.group(4), seal(m.group(4))), prd.review_text)
    for key in keys:
        print("REVIEWED " + key)
    for name in names:
        print("REVIEWED PAGE " + name)
    return 0


def cmd_unreview(args):
    import prd
    keys, names = mark_all(args, lambda m, day: "- %s: **Unreviewed** %s" % (m.group(1), m.group(4)),
                           lambda text, day, name: prd.unreview_text(text, name))
    for key in keys:
        print("UNREVIEWED " + key)
    for name in names:
        print("UNREVIEWED PAGE " + name)
    return 0


def cmd_render(args):
    root = git("rev-parse", "--show-toplevel")
    linked, _ = test_rows(root)
    stale = []
    for rel in pages(root):
        with open(os.path.join(root, rel)) as handle:
            text = handle.read()
        parts = sections(text)
        if [n for n, _ in parts if n != rules()["usage"]] != rules()["sections"]:
            continue
        ids = [(m.group(1), m.group(4)) for _, m in criteria_of(dict(parts)[rules()["sections"][1]]) if m]
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
        if name == "review":
            item.add_argument("--date", help="YYYY-MM-DD, on or before today; default today (UTC)")
        item.set_defaults(func=func)
    item = sub.add_parser("render")
    item.add_argument("--check", action="store_true")
    item.set_defaults(func=cmd_render)
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
