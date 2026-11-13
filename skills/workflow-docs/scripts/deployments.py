#!/usr/bin/env python3
"""The optional Deployments section of a feature page (DOC-14): a Page table and/or a Delivery table, nothing else.
template.md's rules block names the section, the two headers and the Access words, and says each column's rule. Pure:
lines in, FORMAT findings out (the shape pageformat.bad makes); a value that may hold a secret is never echoed: links
read <link> and addresses <address>. The live-link and promoted-build check runs in the deploying repo for now. The page rules of criteria.py (rules, criteria_max, SHEET) sit at the end, moved here unchanged.
"""
import json
import os
import re
import subprocess
import sys
import urllib.request

import pageformat as pf
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
    """DOC-16: each routine's Serves field (its indented continuation lines too) names at least one requirement id, and
    every id it names is on some page."""
    out = []
    for page, lines in books.items():
        fields, cur = [], None
        for number, line in lines:
            head = re.match(r"^- \*\*Serves:\*\*(.*)$", line)
            if head:
                cur = [number, head.group(1)]
                fields.append(cur)
            elif line.startswith(("- ", "#")):
                cur = None
            elif line[:1].isspace() and cur:
                cur[1] += " " + line.strip()
        for number, text in fields:
            ids = re.findall(r"[A-Z]{2,5}-\d+", text)
            if not ids:
                out.append(bad(page, number, name, 16, "a Serves field naming a requirement id such as DOC-14", short(text), "name the ids the routine serves"))
            for key in ids:
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


# --- link-form feature pages (DOC-1, DOC-2) and Home's Topic column (DOC-4) ---

LINK = re.compile(r"^PRD:\s*(\S+)\s*$")
READER = "LOOP_PRD_READER"  # a command run as `COMMAND URL`; its stdout is the linked PRD (an agent's Notion connector sets it)


def link_of(text, listed=""):
    """Where a link-form page's PRD lives, else None: the docs.tsv source (`url:<link>` or `mcp:<server>:<resource>`; `page`
    or empty means the PRD is on the page) or, with no entry there, the page's own 'PRD: <source>' line before its first
    section. A bare link on that line is a url."""
    if listed and listed != "page":
        return listed
    found = next((m.group(1) for m in (LINK.match(x.strip()) for x in __import__("prd").head(text)) if m), None)
    return found if found is None or found.startswith(("url:", "mcp:")) else "url:" + found


def read_link(url):
    """(text, None) of the PRD at a source (`url:<link>` or `mcp:<server>:<resource>`), or (None, why) when it cannot be
    read: never a guess, never a cached copy. A reader command in $LOOP_PRD_READER (given the whole source) wins, and is
    how an MCP connector is reached; else a url that is a file path or file: link or an http(s) page. An mcp source, or a
    Notion link, needs the reader, because a script cannot sign in."""
    try:
        source, url = url, url[4:] if url.startswith("url:") else url
        if os.environ.get(READER):
            done = subprocess.run(os.environ[READER].split() + [source], capture_output=True, text=True, timeout=120)
            return (done.stdout, None) if done.returncode == 0 and done.stdout.strip() else (None, "the reader %s printed nothing (exit %d)" % (os.environ[READER].split()[0], done.returncode))
        if url.startswith("file:"):
            url = urllib.request.url2pathname(url[5:].lstrip("/") if re.match(r"file:/+\w:", url) else url[5:])
        if os.path.exists(url):
            with open(url, encoding="utf-8") as handle:
                return handle.read(), None
        if source.startswith("mcp:") or re.search(r"notion\.(so|site)/", url):
            return None, "this source needs its MCP connector: set %s to a command that prints the document" % READER
        if url.startswith(("http://", "https://")):
            with urllib.request.urlopen(url, timeout=20) as page:
                return page.read().decode("utf-8", "replace"), None
        return None, "not a path or an http(s) link"
    except Exception as error:  # an unreadable link is UNREAD, never a crash
        return None, "%s: %s" % (type(error).__name__, str(error)[:80])


def link_page(root, page, text, link, parts, numbered, rule, seen, linked, on):
    """Trouble for a link-form page, as (kind, page, detail). The requirement ids come from the linked PRD, read fresh
    each time and never copied into the repo; an unreadable link is UNREAD, never a pass, and its ids count as unknown."""
    import criteria
    import pageformat as pf
    import render
    found, mine = [], [x for x in (rule["runbook"], rule["deploy"], "Tests") if x]
    shown = link_of(text)  # what the page itself says; the docs.tsv source, when there is one, must be the same
    if shown != link:
        found.append(("FORMAT", page, "DOC-1 the 'PRD: <source>' line must show where the PRD lives (got %s, docs.tsv says %s). "
                      "Fix: write 'PRD: %s' under the title" % (shown or "no line", link, link)))
    have = [name for name, _ in parts]
    if have != [x for x in mine if x in have] or "Tests" not in have:
        found.append(("SECTIONS", page, "have %s, want only %s, in that order, after the 'PRD: <link>' line. Fix: move the PRD "
                      "text to the linked document" % (", ".join(have) or "none", ", ".join(mine))))
        return found
    body, why = read_link(link)
    if body is None:
        return [("UNREAD", page, "the linked PRD %s cannot be read (%s). Fix: make the link readable here; its ids and the "
                 "Tests table stay unchecked, so this is not a pass" % (link, why))]
    ids = []
    for name, lines in criteria.sections(body):
        if name == rule["sections"][1]:
            for line, match, _ in criteria.blocks(lines):
                if match and match.group(1) in seen:
                    found.append(("DUPLICATE", page, "%s is also in %s" % (match.group(1), seen[match.group(1)])))
                elif match:
                    seen[match.group(1)] = page
                    ids.append((match.group(1), match.group(4)))
    if not ids:
        found.append(("CRITERION", page, "the linked PRD has no '- ID: **Unreviewed** text' line under %s" % rule["sections"][1]))
    if "deployments" in on and rule["deploy"] in numbered:
        found += deployments(page, rule["deploy"], numbered[rule["deploy"]][1], rule["page_cols"], rule["delivery_cols"], rule["access"])
    if "runbook" in on and rule["runbook"] in numbered:
        found += pf.runbook(page, rule["runbook"], numbered[rule["runbook"]][1], rule["fields"])
    if "tests" in on:
        found += [x for x in [pf.stale(page, "Tests", numbered["Tests"][0], numbered["Tests"][1], criteria.table(root, ids, linked))] if x]
    return found


UNREAD = set()  # link-form pages whose link could not be read in this run: rows linking to their ids are not judged


def linked(root, page, text):
    import counting
    return link_of(text, counting.sources(root).get(page, ""))


def topics_of(root):
    import counting
    """The `topics` setting as {topic: [pages]}, or {} when the repo sets none (Home then has no Topic column)."""
    topics = counting.config_of(root).get("topics")
    return {str(k): [str(x) for x in v] for k, v in topics.items() if isinstance(v, list)} if isinstance(topics, dict) else {}


def regroup(text, topics):
    """Home's features table with a leading Topic column, its rows grouped by topic (the setting's order, then Other) and
    by feature name inside one; text unchanged when there is no such table or no topics."""
    lines = text.split("\n")
    start = next((i for i, x in enumerate(lines) if x.startswith("| Feature") or x.startswith("| Topic")), None)
    if not topics or start is None:
        return text
    end = start
    while end < len(lines) and lines[end].startswith("|"):
        end += 1
    rows = [pf.cells(x) for x in lines[start + 2:end]]
    rows = [r[-4:] for r in rows if len(r) in (4, 5)]
    name = lambda r: r[0].strip("[]").split("](")[0]
    order = pf.topic_order(topics)
    rows.sort(key=lambda r: (order.index(pf.topic_of(name(r), topics)), name(r)))
    table = pf.table(("Topic",) + pf.HOME, [[pf.topic_of(name(r), topics)] + r for r in rows])
    return "\n".join(lines[:start] + table + lines[end:])
