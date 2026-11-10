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
Non-goals, Success metrics and Tests. Requirements hold up to criteria_max lines (default CRITERIA_MAX_DEFAULT,
.loop/config.json). A requirement is '- ID: **Unreviewed** text' or '- ID: **Reviewed DATE** text', with '  - '
sub-bullets under it that are not requirements; a Reviewed line ends with <!-- reviewed HASH -->, a hash of its own text
(never its sub-bullets), and docs.py check fails when the text no longer matches. An argument shaped like an ID (two to
five capitals, a dash, a number) is a requirement; any other is a page, whose PRD review prd.py writes. A regression row
whose goal column is '-' proves no requirement yet and is left out. render writes each page's Tests table and the full
Tests page (render.py), each to a temp file renamed into place, printing WROTE per file.
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
CRITERIA_MAX_DEFAULT = 10  # the owner: "make that cap as like a config as well, and probably do that as 10 as default"
SHEET = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "references", "template.md")


def rules():
    """The page rules from the fenced rules block of the template sheet. Refuses when it is missing or incomplete."""
    try:
        with open(SHEET) as handle:
            block = re.search(r"^```rules\n(.*?)^```", handle.read(), re.M | re.S)
        found = dict(line.split(":", 1) for line in block.group(1).splitlines() if ":" in line)
        found = {key.strip(): value.strip() for key, value in found.items()}
        import pageformat
        listed = lambda key, default: [x.strip() for x in found.get(key, default).split(",") if x.strip()]
        on = listed("format", ",".join(pageformat.CHECKS))
        if set(on) - set(pageformat.CHECKS):
            raise ValueError
        return {"sections": listed("sections", found["sections"]), "problem_lines": int(found["problem_lines"]),
                "metrics_lines": int(found["metrics_lines"]), "usage": found.get("usage_section", "Usage"),
                "review": found["review_line"], "milestone": found["milestone_line"], "format": on,
                "banned": listed("problem_banned", pageformat.BANNED),
                "groups": listed("requirement_groups", ", ".join(pageformat.GROUPS))}
    except (OSError, AttributeError, KeyError, ValueError):
        sys.exit("REFUSED: the rules block of skills/workflow-docs/references/template.md is missing or broken.")


def criteria_max(root):
    """The criteria limit: `criteria_max` in .loop/config.json, CRITERIA_MAX_DEFAULT when absent. A bad value refuses."""
    path = os.path.join(root, ".loop", "config.json")
    try:
        with open(path) as handle:
            value = json.load(handle).get("criteria_max", CRITERIA_MAX_DEFAULT)
    except (OSError, ValueError, AttributeError):
        value = CRITERIA_MAX_DEFAULT
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 50:
        sys.exit("REFUSED: criteria_max is %r in %s. Fix: set it to a whole number from 1 to 50, or remove it for the default %d."
                 % (value, path, CRITERIA_MAX_DEFAULT))
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


def table(root, ids, linked):
    import render
    return render.table(root, ids, linked)


def cmd_render(args):
    import render
    return render.render(args)


def criteria_of(lines):
    """(line, LINE match or None) per requirement line: indented lines (sub-bullets) belong to the line above, and the
    group headings (### Functional, ### Non-functional) and a group's 'None' are not requirements."""
    return [(line, LINE.match(line)) for line in lines
            if line.strip() and not line[:1].isspace() and not line.startswith("### ") and line.strip() != "None"]


def contract(root, names, seen):
    """Page contract trouble for these feature pages, as (kind, page, detail). `seen` maps ids to their page."""
    import pageformat as pf
    import prd
    import render
    found, rule = [], rules()
    limit, on, held = criteria_max(root), rule["format"], render.maps(root)
    owns = {row[0]: re.findall(r"(?:^|,)skills/([\w-]+)", row[1]) for row in tsv(root, "docs.tsv")}
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
        numbered = {name: (start, lines) for name, start, lines in pf.parts(text)}
        found += prd.trouble(root, page, text, parts, rule)
        if rule["usage"] in body:
            if not [x for x in body[rule["usage"]] if x.strip()]:
                found.append(("USAGE", page, "has an empty %s section. Fix: list its commands, or remove the section" % rule["usage"]))
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
        found += pf.bullets(page, head[1], numbered[head[1]][1], LINE, "bullets" in on, rule["groups"])
        if "usage" in on and rule["usage"] in numbered:
            found += pf.usage(page, rule["usage"], numbered[rule["usage"]][1], held, owns.get(page, []))
        if "problem" in on:
            found += pf.problem(page, head[0], numbered[head[0]][1], rule["problem_lines"], rule["banned"])
        if "tests" in on:
            found += [x for x in [pf.stale(page, "Tests", numbered["Tests"][0], numbered["Tests"][1], table(root, ids, linked))] if x]
    if "tests" in on:
        found += [("FORMAT", "Tests:1", "Tests: DOC-9 one anchor per row (got %s). Fix: rename one row id" % x)
                  for x in render.clashes([row[0] for row in tsv(root, "regression.tsv") if row[1] != "draft"])]
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
