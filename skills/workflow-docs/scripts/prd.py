#!/usr/bin/env python3
"""The PRD layer of feature pages: the owner's review line and its lock, converting old pages, drafting new ones.

usage: prd.py <command> [options]

  new NAME "<idea>" --paths A,B [--prefix XX]
                               draft a new feature's PRD from a one-line idea, marked Unreviewed, and map it
  convert [--write]            turn old pages (Summary, Criteria, Tests) into PRD pages; without --write only says what
                               it would do
  skeleton PATH --title T --problem P --requirement LINE
                               write one PRD page (the one page writer; workflow-setup uses it)

The review line sits under the title (or the Milestone line): 'Review: **Unreviewed**', or
'Review: **Reviewed DATE** <!-- prd P=.. R=.. N=.. M=.. U=.. -->', one 8-hex fingerprint each for Problem,
Requirements, Non-goals, Success metrics and Usage, written by criteria.py review PAGE --user. Each fingerprint covers the
section's name and its paragraphs, with whitespace collapsed and requirement stamps removed. While the PRD is Reviewed,
a change to any of the first four is LOCKED (the check fails); a change to Usage alone is CHANGED (the check fails, the
audit and publish ignore it) until the owner reviews the PRD again.

convert recognizes these partial pages and completes them: Summary+Criteria (old), Problem+Criteria,
Summary+Requirements, a missing Review line, a missing Non-goals and/or Success metrics section. A page already in
PRD form is skipped; any other page is refused with what is missing. New Non-goals and Success metrics sections get one
placeholder line, so the docs check says UNWRITTEN until real drafts replace it. It runs git and nothing else.
"""
import argparse
import os
import re
import sys

import criteria

MARKER = "<!-- workflow-docs -->"
PLACEHOLDER = "Write this page from what is really in the repo."
REVIEW = re.compile(r"^Review: \*\*(Unreviewed|Reviewed (\d{4}-\d\d-\d\d))\*\*"
                    r"(?: <!-- prd P=(\w{8}) R=(\w{8}) N=(\w{8}) M=(\w{8}) U=(\w{8}) -->)?$")
KEYS = "PRNMU"


def names(rule):
    """Section names in fingerprint order: Problem, Requirements, Non-goals, Success metrics, Usage."""
    return rule["sections"][:4] + [rule["usage"]]


def paras(lines):
    """A section's lines: blank lines and list items each start a new one; a wrapped line joins the one before."""
    out = []
    for block in re.split(r"\n[ \t]*\n", "\n".join(lines or []).replace("\r\n", "\n").replace("\r", "\n")):
        new = True
        for line in block.split("\n"):
            if new or re.match(r"\s*([-*+]|\d+\.)\s", line):
                out.append(line)
            else:
                out[-1] += "\n" + line
            new = False
    return [para for para in out if para.strip()]


def norm(name, lines):
    """A section as hashed: its name, then each line with whitespace collapsed and requirement stamps removed."""
    found = []
    for para in paras(lines):
        out = []
        for line in para.split("\n"):
            match = criteria.LINE.match(line.rstrip())
            out.append("- %s: %s" % (match.group(1), match.group(4)) if match else line)
        found.append(" ".join(" ".join(out).split()))
    return name + "\n" + "\n".join(found)


def prints(parts, rule):
    body = dict(parts)
    return dict((key, criteria.seal(norm(name, body.get(name)))) for key, name in zip(KEYS, names(rule)))


def head(text):
    """The page's lines before its first section."""
    out = []
    for line in text.replace("\r\n", "\n").split("\n"):
        if line.startswith("## "):
            break
        out.append(line)
    return out


def review_of(text, rule):
    """(review line or None, trouble or None) from the page head: marker, title, Milestone line, Review line."""
    seq = [line.strip() for line in head(text) if line.strip()]
    at = 1 if seq[:1] == [MARKER] else 0
    at += 1 if seq[at:at + 1] and seq[at].startswith("# ") else 0
    at += 1 if seq[at:at + 1] and seq[at].startswith(rule["milestone"] + ":") else 0
    line = seq[at] if at < len(seq) and seq[at].startswith(rule["review"] + ":") else None
    rest = seq[at + (1 if line else 0):]
    if line is None:
        if any(item.startswith(rule["review"] + ":") for item in seq):
            return None, ("REVIEW", "the Review line must come right after the title or the Milestone line. Fix: move it there")
        return None, ("REVIEW", "has no Review line. Fix: add 'Review: **Unreviewed**' under the title (or its Milestone "
                                "line), or run prd.py convert --write (workflow-docs)")
    if rest:
        return line, ("SECTIONS", "has text between the Review line and the first section: %s. Fix: move it into Problem, "
                                  "or remove it" % rest[0][:60])
    if not REVIEW.match(line) or (REVIEW.match(line).group(2) and not REVIEW.match(line).group(3)):
        return line, ("REVIEW", "a malformed Review line: %s. Fix: write 'Review: **Unreviewed**'; only the owner's "
                                "/workflow-docs review PAGE --user writes a Reviewed one" % line[:60])
    return line, None


def trouble(root, page, text, parts, rule):
    """The PRD contract lines for one page whose sections are already in order, as (kind, page, detail)."""
    found, body = [], dict(parts)
    line, why = review_of(text, rule)
    if why:
        found.append((why[0], page, why[1]))
    if not paras(body.get(rule["sections"][2])):
        found.append(("NONGOALS", page, "%s is empty. Fix: write at least one line on what the feature deliberately "
                                        "won't do" % rule["sections"][2]))
    count = len(paras(body.get(rule["sections"][3])))
    if not 1 <= count <= rule["metrics_lines"]:
        found.append(("METRICS", page, "%s has %d lines, want 1 to %d. Fix: write one to %d measurable lines on how we "
                      "know it works" % (rule["sections"][3], count, rule["metrics_lines"], rule["metrics_lines"])))
    match = REVIEW.match(line or "")
    if why or not match or not match.group(2):
        return found
    was, now = dict(zip(KEYS, match.group(3, 4, 5, 6, 7))), prints(parts, rule)
    moved = [key for key in KEYS[:4] if was[key] != now[key]]
    rel = "%s/%s.md" % (criteria.folder_of(root), page)
    if moved:
        found.append(("LOCKED", page, "the reviewed PRD changed in %s (reviewed lock %s, now %s). Fix: git log -p -- %s to "
                      "find the reviewed text and restore it, or the owner runs /workflow-docs unreview %s --user (and "
                      "/workflow-docs unreview ID --user for a reviewed requirement)" % (
                          ", ".join(dict(zip(KEYS, names(rule)))[key] for key in moved),
                          " ".join("%s=%s" % (key, was[key]) for key in moved),
                          " ".join("%s=%s" % (key, now[key]) for key in moved), rel, page)))
    elif was["U"] != now["U"]:
        empty = criteria.seal(norm(rule["usage"], []))
        how = "added" if was["U"] == empty else "removed" if now["U"] == empty else "edited"
        found.append(("CHANGED", page, "%s %s since the owner's review on %s (reviewed U=%s, now U=%s). Fix: the owner "
                      "runs /workflow-docs review %s --user; an agent cannot clear this" % (
                          rule["usage"], how, match.group(2), was["U"], now["U"], page)))
    return found


def set_review(text, line):
    """The text with its Review line replaced."""
    lines, size = text.split("\n"), len(head(text))
    for number in range(size):
        if lines[number].startswith("Review:"):
            lines[number] = line
            return "\n".join(lines)
    return text


def review_text(text, day, page):
    """(new text, None) with the PRD Reviewed on day and its fingerprints, or (text, why) when it can't be reviewed."""
    rule = criteria.rules()
    parts = criteria.sections(text)
    have = [name for name, _ in parts if name != rule["usage"]]
    if have != rule["sections"]:
        return text, "its sections are %s, not a PRD. Fix: run prd.py convert --write (workflow-docs) first" % (", ".join(have) or "none")
    line, why = review_of(text, rule)
    if line is None or (why and why[0] == "SECTIONS"):
        return text, why[1]
    sums = prints(parts, rule)
    return set_review(text, "Review: **Reviewed %s** <!-- prd %s -->" % (day, " ".join("%s=%s" % (k, sums[k]) for k in KEYS))), None


def unreview_text(text, page):
    line, why = review_of(text, criteria.rules())
    if line is None:
        return text, why[1]
    return set_review(text, "Review: **Unreviewed**"), None


def skeleton(title, problem, requirement, milestone=""):
    """The one PRD page writer: an Unreviewed page with placeholder Non-goals and Success metrics."""
    return "%s\n%s\n\n%sReview: **Unreviewed**\n\n## Problem\n\n%s\n\n## Requirements\n\n%s\n\n## Non-goals\n\n- %s\n\n" \
           "## Success metrics\n\n- %s\n\n## Tests\n\n" % (MARKER, title, milestone + "\n\n" if milestone else "",
                                                           problem.strip(), requirement, PLACEHOLDER, PLACEHOLDER)


def convert_text(text, rule):
    """(outcome, new text): outcome is skipped, converted, completed, or 'refused: why'."""
    parts = criteria.sections(text)
    have = [name for name, _ in parts if name != rule["usage"]]
    first, second, third, fourth = rule["sections"][:4]
    shapes = ([first, "Summary"], [second, "Criteria"], [third, None], [fourth, None], ["Tests"])
    at, plan = 0, []
    for allowed in shapes:
        if at < len(have) and have[at] in allowed:
            plan.append(have[at])
            at += 1
        elif None in allowed:
            plan.append(None)
        else:
            return "refused: sections are %s; want %s (Summary and Criteria are read as Problem and Requirements)" % (
                ", ".join(have) or "none", ", ".join(rule["sections"])), text
    if at != len(have):
        return "refused: unknown section %s; want %s" % (have[at], ", ".join(rule["sections"])), text
    line, _ = review_of(text, rule)
    if plan == rule["sections"] and line:
        return "skipped", text
    lines, fenced, out = text.split("\n"), False, []
    for raw in lines:
        if raw.startswith("```"):
            fenced = not fenced
        if not fenced and raw.strip() == "## Summary":
            raw = "## " + first
        elif not fenced and raw.strip() == "## Criteria":
            raw = "## " + second
        elif not fenced and raw.strip() == "## Tests":
            for name, there in ((third, plan[2]), (fourth, plan[3])):
                if not there:
                    out += ["## " + name, "", "- " + PLACEHOLDER, ""]
        out.append(raw)
    fresh = "\n".join(out)
    if not line:
        pre = head(fresh)
        spot = max([n for n, item in enumerate(pre) if item.startswith(("# ", rule["milestone"] + ":"))] or [0])
        fresh = "\n".join(pre[:spot + 1] + ["", "Review: **Unreviewed**"] + fresh.split("\n")[spot + 1:])
    return ("converted" if "Summary" in have and "Criteria" in have else "completed"), fresh


def feature_pages(root):
    import docs
    folder = criteria.folder_of(root)
    return [page for page in sorted(docs.read_map(root)) if page != "Home" and os.path.isfile(os.path.join(root, folder, page + ".md"))]


def cmd_convert(args):
    root = criteria.git("rev-parse", "--show-toplevel")
    rule, bad = criteria.rules(), 0
    for page in feature_pages(root):
        path = os.path.join(root, criteria.folder_of(root), page + ".md")
        with open(path) as handle:
            text = handle.read()
        outcome, fresh = convert_text(text, rule)
        bad += outcome.startswith("refused")
        if args.write and fresh != text:
            with open(path, "w") as handle:
                handle.write(fresh)
        print("%s %s%s" % (page, outcome, "" if args.write or outcome in ("skipped",) or outcome.startswith("refused") else " (dry run)"))
    if not args.write:
        print("DRY RUN: nothing written. Fix: run prd.py convert --write")
    elif bad:
        print("REFUSED %d page(s). Fix: give each the sections Problem (or Summary), Requirements (or Criteria) and Tests, "
              "then run prd.py convert --write again" % bad)
    return 1 if bad else 0


def used_prefixes(root):
    """Every ID prefix in use: page requirements, regression ids and goal columns, defect rows."""
    used = set()
    for rel in criteria.pages(root):
        with open(os.path.join(root, rel)) as handle:
            used |= set(re.findall(r"^- ([A-Z]{2,5})-\d+: ", handle.read(), re.M))
    for row in criteria.tsv(root, "regression.tsv"):
        used |= {item.split("-")[0] for item in (row[0], row[3]) if criteria.ID.match(item)}
    return used


def cmd_new(args):
    import docs
    example = 'prd.py new Billing "charge cards once a month" --paths src/billing'
    if criteria.ID.match(args.name):
        sys.exit("REFUSED: %s looks like a requirement ID (^[A-Z]{2,5}-\\d+$), so review could not name the page. "
                 "Fix: pick another name, e.g. %s" % (args.name, example))
    if not docs.PAGE.match(args.name) or args.name == "Home":
        sys.exit("REFUSED: bad page name %s. Fix: letters, digits and dashes, not Home, e.g. %s" % (args.name, example))
    if not args.paths or not [p for p in args.paths.split(",") if p.strip()]:
        sys.exit("REFUSED: no --paths, and an unmapped page fails the docs check. Fix: name what the page describes, e.g. %s" % example)
    idea = " ".join(args.idea.split())
    if not idea:
        sys.exit("REFUSED: no idea. Fix: give one line, e.g. %s" % example)
    root = criteria.git("rev-parse", "--show-toplevel")
    rel = "%s/%s.md" % (criteria.folder_of(root), args.name)
    if os.path.exists(os.path.join(root, rel)):
        sys.exit("REFUSED: %s already exists. Fix: edit it, or pick a new name, e.g. %s" % (rel, example))
    used = used_prefixes(root)
    if args.prefix:
        if not re.match(r"^[A-Z]{2,5}$", args.prefix) or args.prefix in used:
            sys.exit("REFUSED: --prefix %s must be 2 to 5 capital letters not already in use. Fix: --prefix %s" % (
                args.prefix, next(("ZZ" + c for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ" if "ZZ" + c not in used), "QQQ")))
        tag = args.prefix
    else:
        letters = re.sub(r"[^A-Za-z]", "", args.name).upper()
        tag = next((x for x in dict.fromkeys(letters[:n] for n in (3, 4, 5)) if len(x) >= 2 and x not in used), None)
        if not tag:
            sys.exit("REFUSED: no free ID prefix from the name %s. Fix: add --prefix XX (2 to 5 capital letters, unused)" % args.name)
    key = "%s-1" % tag
    text = skeleton("# " + args.name.replace("-", " "), idea, "- %s: **Unreviewed** %s" % (key, idea))
    linked, _ = criteria.test_rows(root)
    text += "\n".join(criteria.table(root, [(key, idea)], linked)) + "\n"
    os.makedirs(os.path.dirname(os.path.join(root, rel)), exist_ok=True)
    with open(os.path.join(root, rel), "w") as handle:
        handle.write(text)
    docs.cmd_add(argparse.Namespace(page=args.name, paths=args.paths))
    print("DRAFTED %s: Review **Unreviewed**, requirement %s" % (rel, key))
    print("NEXT replace the two placeholder lines (Non-goals, Success metrics) with real drafts; the docs check says "
          "UNWRITTEN until then")
    print("NEXT add %s's regression row in this same pull request (it needs one before the next release): "
          "regression.py add <row-id> --level land --command \"<test>\" --goal %s --describe \"Given ..., when ..., then ...\"" % (key, key))
    print("NEXT then run: docs.py check")
    return 0


def cmd_skeleton(args):
    with open(args.path, "w") as handle:
        handle.write(skeleton(args.title, args.problem, args.requirement))
    print("WROTE " + args.path)
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    item = sub.add_parser("new")
    item.add_argument("name")
    item.add_argument("idea")
    item.add_argument("--paths", default="")
    item.add_argument("--prefix", default="")
    item.set_defaults(func=cmd_new)
    item = sub.add_parser("convert")
    item.add_argument("--write", action="store_true")
    item.set_defaults(func=cmd_convert)
    item = sub.add_parser("skeleton")
    item.add_argument("path")
    for name in ("--title", "--problem", "--requirement"):
        item.add_argument(name, required=True)
    item.set_defaults(func=cmd_skeleton)
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
