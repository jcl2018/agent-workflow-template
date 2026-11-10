#!/usr/bin/env python3
"""The live board's Dependencies section as a graph a phone can read (issues 94 and 123): running and queued goals, top
to bottom, one band per depth, at most 60 columns, with a legend. Pure functions; imported, not run.

  [>] running   [=] holding or paused   [ ] queued   [?] waiting on you   [!] stuck

Goals that wait on nothing come first, packed side by side; each later band lists one goal a line with what it waits on
(`[ ] c <- a, b`), so a goal that waits on several is drawn once with every arrow. A `|` / `v` joins the bands. A goal in
a cycle carries `(cycle)` and the cycle is drawn once, never followed. No goals: `- (none)`.
"""
import status_graph

WIDTH = 60
MARKS = {"running": ">", "held": "=", "paused": "=", "holding": "=", "awaiting merge": "=", "done": "=", "queued": " ",
         "waiting": "?", "failed": "!", "stopped": "!", "stuck": "!", "silent": "!", "freezing": ">"}
LEGEND = "[>] running [=] holding [ ] queued [?] you [!] stuck"


def box(node, cut):
    return "[%s] %s%s" % (MARKS.get(node.get("mark"), " "), node["slug"], " (cycle)" if node["slug"] in cut else "")


def pack(pieces, width, gap="  "):
    """Pieces side by side, wrapped at width; a piece longer than width stands alone (the caller's fit wraps it)."""
    lines, line = [], ""
    for piece in pieces:
        if line and len(line) + len(gap) + len(piece) > width:
            lines.append(line)
            line = ""
        line = piece if not line else line + gap + piece
    return lines + ([line] if line else [])


def cycled(nodes):
    """Slugs that can reach themselves through what they wait on."""
    by = {node["slug"]: node["depends"] for node in nodes}

    def reach(start):
        seen, todo = set(), list(by[start])
        while todo:
            slug = todo.pop()
            if slug not in seen:
                seen.add(slug)
                todo += by.get(slug, [])
        return seen

    return {slug for slug in by if slug in reach(slug)}


def render(items, width=WIDTH):
    """Lines for the Dependencies section. items: dicts with slug, mark and depends (slugs it waits on)."""
    if not items:
        return ["- (none)"]
    known = {node["slug"] for node in items}
    nodes = [dict(node, depends=[d for d in node.get("depends") or [] if d in known]) for node in items]
    cut = cycled(nodes)
    bands = status_graph.levels(nodes)
    out = pack([box(node, cut) for node in bands[0]], width) if bands else []
    for band in bands[1:]:
        out += ["  |", "  v"]
        for node in band:
            line = "%s <- %s" % (box(node, cut), ", ".join(node["depends"]))
            out += pack([line], width)
    return out + ["", LEGEND]
