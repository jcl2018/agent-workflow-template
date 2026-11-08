#!/usr/bin/env python3
"""The roadmap as a dependency graph, and the time the whole graph still needs. Shared by the status block and the board.

A node is a dict: slug, mark, depends (slugs it waits on), stage (0 to 8, steps begun), left (seconds still needed, 0 when
nothing is, None when there is no estimate yet). Marks: merged, awaiting merge, running, waiting, failed, queued, and
unknown for a dependency that is no goal here. The total is the longest chain of what is left through the dependencies,
because goals that don't wait on each other run side by side; it is never the sum. Pure functions, nothing read from disk.
Imported, not run.
"""
STAGES = 8
DONE = ("merged", "awaiting merge")
MARKS = {"done": "awaiting merge", "stopped": "failed"}


def span(seconds):
    seconds = int(seconds)
    return "%dh%02dm" % divmod(seconds // 60, 60) if seconds >= 3600 else "%dm" % (seconds // 60) if seconds >= 60 else "<1m"


def mark(status, merged=False):
    """The mark for a run's status."""
    return "merged" if merged else MARKS.get(status, status)


def completed(items):
    """Nodes plus a visible node for every dependency that is not a goal here."""
    known = {node["slug"] for node in items}
    extra = [dict(slug=dep, mark="unknown", depends=[], stage=0, left=0) for node in items for dep in node["depends"]
             if dep not in known and not known.add(dep)]
    return items + extra


def chain(items):
    """(seconds, path, cycles): the longest chain of what is left, the goals on it, and the goals where a cycle was cut."""
    by, memo, cut = {node["slug"]: node for node in items}, {}, []

    def walk(slug, stack):
        if slug in memo:
            return memo[slug]
        if slug in stack:
            cut.append(slug)
            return 0, []
        node = by[slug]
        best = max([walk(dep, stack + (slug,)) for dep in node["depends"] if dep in by] + [(0, [])], key=lambda found: found[0])
        memo[slug] = (best[0] + (node["left"] or 0), best[1] + [slug])
        return memo[slug]

    found = max([walk(node["slug"], ()) for node in items] + [(0, [])], key=lambda found: found[0])
    return found[0], found[1], sorted(set(cut))


def unknown(items):
    """Goals not finished that have no estimate yet."""
    return [node["slug"] for node in items if node["left"] is None and node["mark"] not in DONE]


def total(items):
    """The total line: the longest chain, 'at least' when some goal has no estimate, and a note for a cut cycle."""
    seconds, path, cycles = chain(items)
    missing = unknown(items)
    if not seconds and missing:
        line = "no estimate yet (%d goal%s without one)" % (len(missing), "" if len(missing) == 1 else "s")
    elif not seconds:
        line = "nothing left"
    else:
        line = "%s%s, the longest chain: %s" % ("at least " if missing else "about ", span(seconds), " > ".join(path))
        line += " (%d goal%s without an estimate)" % (len(missing), "" if len(missing) == 1 else "s") if missing else ""
    return line + ("; cycle cut at " + ", ".join(cycles) if cycles else "")


def levels(items):
    """Nodes grouped by depth: goals that wait on nothing first, then those that wait on them. A cycle is cut, not followed."""
    by, depth = {node["slug"]: node for node in items}, {}

    def deep(slug, stack):
        if slug not in depth:
            depth[slug] = 1 + max([deep(dep, stack + (slug,)) for dep in by[slug]["depends"] if dep in by and dep not in stack + (slug,)] + [0])
        return depth[slug]

    for node in items:
        deep(node["slug"], ())
    return [[node for node in items if depth[node["slug"]] == level] for level in range(1, max(depth.values(), default=0) + 1)]


def bar(stage):
    return "[%s%s]" % ("#" * stage, "-" * (STAGES - stage))


def line(node):
    """One node: its mark, stage, bar, time to finish and what it waits on."""
    stage = STAGES if node["mark"] in DONE else node["stage"]
    time = "done" if node["mark"] in DONE else "no estimate yet" if node["left"] is None else "~%s left" % span(node["left"])
    if node["mark"] == "unknown":
        return "- [? not a goal here] %s" % node["slug"]
    return "- [%s] %s  stage %d of %d %s  %s%s" % (node["mark"], node["slug"], stage, STAGES, bar(stage), time,
                                                "  <- waits on " + ", ".join(node["depends"]) if node["depends"] else "")


def render_text(items, under=None):
    """The graph as text: a heading per level, a line per node, anything in under[slug] indented beneath its node."""
    items, out = completed(items), []
    for number, level in enumerate(levels(items), 1):
        out.append("level %d%s" % (number, " (waits on nothing)" if number == 1 else ""))
        for node in level:
            out.append(line(node))
            out += (under or {}).get(node["slug"], [])
    return out or ["(no goals)"]
