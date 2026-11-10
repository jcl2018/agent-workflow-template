#!/usr/bin/env python3
"""The optional Deployments section of a feature page (DOC-14): a Page table and/or a Delivery table, nothing else.
template.md's rules block names the section, the two headers and the Access words, and says each column's rule. Pure:
lines in, FORMAT findings out (the shape pageformat.bad makes); a value that may hold a secret is never echoed: links
read <link> and addresses <address>. The live-link and promoted-build check runs in the deploying repo for now.
"""
import re

from pageformat import bad, short, tables

PAGE_COLS = ("Page", "Link", "Access", "Shows", "Live build")
DELIVERY_COLS = ("Delivery", "Channel", "Recipients", "What's sent", "Status")
URL = re.compile(r"^https://[^\s@/?#;]+(/[^\s?#;]*)?(\?[^\s#=]*)?(#[^\s=]*)?$")  # a plain link: no user, no key=value in query or fragment
SHA = re.compile(r"^`[0-9a-f]{7,40}`$")
EMAIL = re.compile(r"[\w.+-]+@[\w-]+(\.[\w-]+)*")


def deployments(page, name, lines, page_cols=PAGE_COLS, delivery_cols=DELIVERY_COLS, access=("public", "sign-in")):
    """DOC-14: a Page table and/or a Delivery table, nothing else (template.md says each column's rule)."""
    hide = lambda text: short(re.sub(r"\S*://\S*", "<link>", EMAIL.sub("<address>", str(text))))  # never echo a secret
    runs, other = tables(lines)
    found = []  # a header row inside a run starts a new table
    for number, header, rows in runs:
        found.append([number, header, [], False])
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
