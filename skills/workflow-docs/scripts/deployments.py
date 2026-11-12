#!/usr/bin/env python3
"""The optional Deployments section of a feature page (DOC-14): a Page table and/or a Delivery table, nothing else.
template.md's rules block names the section, the two headers and the Access words, and says each column's rule. Pure:
lines in, FORMAT findings out (the shape pageformat.bad makes); a value that may hold a secret is never echoed: links
read <link> and addresses <address>. The live-link and promoted-build check runs in the deploying repo for now. The page rules of criteria.py (rules, criteria_max, SHEET) sit at the end, moved here unchanged.
"""
import json
import os
import re
import sys

from pageformat import RULE, bad, short, tables

PAGE_COLS = ("Page", "Link", "Access", "Shows", "Live build")
DELIVERY_COLS = ("Delivery", "Channel", "Recipients", "What's sent", "Status")
URL = re.compile(r"^https://[^\s@/?#;]+(/[^\s?#;]*)?(\?[^\s#=]*)?(#[^\s=]*)?$")  # a plain link: no user, no key=value in query or fragment
SHA = re.compile(r"^`[0-9a-f]{7,40}`$")
EMAIL = re.compile(r"[\w.+-]+@[\w-]+(\.[\w-]+)*")


def deployments(page, name, lines, page_cols=PAGE_COLS, delivery_cols=DELIVERY_COLS, access=("public", "sign-in")):
    """DOC-14: a Page table and/or a Delivery table, nothing else (template.md says each column's rule)."""
    hide = lambda text: short(re.sub(r"\S*://\S*", "<link>", EMAIL.sub("<address>", str(text))))  # never echo a secret
    runs, other = tables(lines)
    text = dict(lines)
    found = []  # a header row inside a run starts a new table
    for number, header, rows in runs:
        found.append([number, header, [], bool(RULE.match(text.get(number + 1, "").strip()))])  # tables() drops that separator
        for row_no, row in rows:
            if tuple(row) in (tuple(page_cols), tuple(delivery_cols)):
                found.append([row_no, row, [], False])
            elif all(re.match(r"^:?-+:?$", c) for c in row) and not found[-1][2] and not found[-1][3]:
                found[-1][3] = True  # the separator right under its header
            else:
                found[-1][2].append((row_no, row))
    fix_head = "use '%s' or '%s'" % (" | ".join(page_cols), " | ".join(delivery_cols))
    out = [bad(page, number, name, 14, "only a Page table, a Delivery table and blank lines", hide(line), "remove it")
           for number, line in other]
    if not found and not other:
        out.append(bad(page, lines[0][0] if lines else 1, name, 14, "a Page or Delivery table with at least one row",
                       "an empty section", "add a table, or remove the section"))
    seen = set()
    for number, header, rows, ruled in found:
        kind = "Page" if tuple(header) == tuple(page_cols) else "Delivery" if tuple(header) == tuple(delivery_cols) else ""
        if not kind:
            out.append(bad(page, number, name, 14, "a table header of exactly the Page or Delivery columns", hide(" | ".join(header)), fix_head))
            continue
        if kind in seen:
            out.append(bad(page, number, name, 14, "at most one %s table" % kind, "a second one", "merge its rows into the first"))
        seen.add(kind)
        if not ruled:
            out.append(bad(page, number, name, 14, "a separator row under the %s header" % kind, "none", "add |---|---|---|---|---|"))
        if not rows:
            out.append(bad(page, number, name, 14, "at least one row in the %s table" % kind, "none", "add a row, or remove the table"))
        cols = page_cols if kind == "Page" else delivery_cols
        for row_no, row in rows:
            if len(row) != len(cols):
                out.append(bad(page, row_no, name, 14, "%d cells in each %s row" % (len(cols), kind), len(row),
                               "one cell per column; escape a | inside a cell as \\|"))
                continue
            cell = dict(zip(cols, row))
            empty = [c for c in cols if not cell[c]]
            if empty:
                out.append(bad(page, row_no, name, 14, "every %s cell filled" % kind, "empty %s" % ", ".join(empty), "fill it"))
            elif kind == "Page":
                if not URL.match(cell[cols[1]]):  # never echoed: it may hold a secret
                    out.append(bad(page, row_no, name, 14, "Page Link a full https URL with no user, password or token", "another link",
                                   "give the plain https:// link"))
                if cell[cols[2]] not in access:
                    out.append(bad(page, row_no, name, 14, "Page Access %s" % " or ".join(access), hide(cell[cols[2]]),
                                   "say who can open it: %s" % " or ".join(access)))
                if not SHA.match(cell[cols[4]]):
                    out.append(bad(page, row_no, name, 14, "Page Live build a 7 to 40 hex sha in backticks", hide(cell[cols[4]]),
                                   "write the sha from the page's build.txt in backticks"))
            elif any(EMAIL.search(c) for c in row):
                out.append(bad(page, row_no, name, 14, "Delivery Recipients a group, never an address", "an email address",
                               "name the group instead"))
    return out


# The page rules of criteria.py, moved here unchanged (size); criteria.py imports them back.
CRITERIA_MAX_DEFAULT = 10  # the owner: "make that cap as like a config as well, and probably do that as 10 as default"
SHEET = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "references", "template.md")


def owed(root, books, name):
    """DOC-16: every routine in .loop/routines.tsv (`routine<TAB>page`, # lines are comments) has its '### routine' runbook on
    its page. `books` maps every page to the lines of its Runbook section ([] when none). No file means no registry."""
    out, path = [], os.path.join(root, ".loop", "routines.tsv")
    try:
        with open(path, encoding="utf-8-sig") as handle:
            rows = [(n, line.rstrip("\n").split("\t")) for n, line in enumerate(handle, 1) if line.strip() and not line.lstrip().startswith("#")]
    except FileNotFoundError:
        return out
    except (OSError, ValueError) as error:
        return [bad("routines.tsv", 1, "Runbook", 16, "a readable routine registry", short(getattr(error, "strerror", None) or "not UTF-8 text"), "fix .loop/routines.tsv")]
    seen = set()
    for number, row in rows:
        routine, page = (row + ["", ""])[:2]
        if routine in seen:
            out.append(bad("routines.tsv", number, "Runbook", 16, "each routine once", short(routine), "remove the duplicate row"))
        seen.add(routine)
        if page not in books:
            out.append(bad("routines.tsv", number, "Runbook", 16, "a routine on a feature page", short(routine), "name a page from .loop/docs.tsv in .loop/routines.tsv"))
        elif not any(line.rstrip() == "### " + routine for _, line in books[page]):
            out.append(bad(page, 1, name, 16, "a '### %s' runbook, the routine .loop/routines.tsv gives this page" % routine, "none",
                           "add the Runbook section with '### %s' and its fields" % routine))
    return out


def unserved(books, seen, name):
    """DOC-16: each routine's Serves field names at least one requirement id, and every id it names is on some page."""
    out = []
    for page, lines in books.items():
        for number, line in lines:
            head = re.match(r"^- \*\*Serves:\*\*(.*)$", line)
            ids = re.findall(r"[A-Z]{2,5}-\d+", head.group(1)) if head else None
            if head and not ids:
                out.append(bad(page, number, name, 16, "a Serves field naming a requirement id such as DOC-14", short(head.group(1)), "name the ids the routine serves"))
            for key in ids or []:
                if key not in seen:
                    out.append(bad(page, number, name, 16, "a Serves id that a page defines", key, "name a requirement from a feature page"))
    return out


def rules():
    """The page rules from the fenced rules block of the template sheet. Refuses when it is missing or incomplete."""
    try:
        with open(SHEET) as handle:
            block = re.search(r"^```rules\n(.*?)^```", handle.read(), re.M | re.S)
        found = dict(line.split(":", 1) for line in block.group(1).splitlines() if ":" in line)
        found = {key.strip(): value.strip() for key, value in found.items()}
        import deployments
        import pageformat
        listed = lambda key, default: [x.strip() for x in found.get(key, default).split(",") if x.strip()]
        on = listed("format", ",".join(pageformat.CHECKS))
        if set(on) - set(pageformat.CHECKS):
            raise ValueError
        return {"sections": listed("sections", found["sections"]), "problem_lines": int(found["problem_lines"]),
                "metrics_lines": int(found["metrics_lines"]), "usage": found.get("usage_section", "Usage"),
                "review": found["review_line"], "milestone": found["milestone_line"], "format": on,
                "banned": listed("problem_banned", pageformat.BANNED),
                "groups": listed("requirement_groups", ", ".join(pageformat.GROUPS)),
                "runbook": found.get("runbook_section", "Runbook"),
                "fields": listed("runbook_fields", "Serves, Schedule, Steps, Full run, Output, Never, Check"),
                "deploy": found.get("deployments_section", "Deployments"), "access": listed("deployments_access", "public, sign-in"),
                "page_cols": listed("deployments_page", ", ".join(deployments.PAGE_COLS)),
                "delivery_cols": listed("deployments_delivery", ", ".join(deployments.DELIVERY_COLS))}
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
