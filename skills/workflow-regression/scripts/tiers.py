#!/usr/bin/env python3
"""The goal tier of `regression.py run land --reuse --tier goal` (REG-4), and `--kind`.

Imported by regression.py, not run. A goal lane plans from the branch's lane record only when that record's merge-base
with the base branch equals the current one, else from the merge-base. It runs the rows whose closure reaches a file
changed since then (lanes.py's closure), the rows added or changed in .loop/regression.tsv since then, the rows that
run tools on the repo root (lanes.ROOT_RUN, when anything changed), a usable record's FAIL rows and any flaky row
(flaky_apply below: never reused). After a base merge
the record is not usable, and the rows the merge changed (since each row's recorded commit) run too. A path no row
maps, or a deleted one, is a Note at every lane: it picks the rows that name it and the runners (REG-7), never a full
run. With no merge-base every row is a candidate (printed FULL); a lane with no plan takes a lane slot. The run stays
within test_budget_minutes (runs.py): rows past it are left to the scheduled full suite. Each selected row's reason is
printed (SELECTED lines) and summed in one ROWS line for the LANE line.

FLAKY (REG-9), flaky_apply: a row whose result flipped on the same clean commit, runner and python version. Each result
keeps its raw PASS/FAIL; the mark is a separate sticky `flaky` flag (the commit it flipped on). The previous result is the
row in the branch's lane record (<git common dir>/loop/tests/, lanes.py), which keeps commit, clean, host (the runner)
and python per row. Only two results on the same commit, both on a clean tree, from the same host and python version
count: either order (FAIL then PASS, PASS then FAIL) marks the row, and the mark stays on that commit (FAIL, PASS, PASS
is still flaky), until a later commit's clean run passes. A dirty tree, `regression.py red`, another runner, or an older
record or regression-runs.tsv without these fields never marks. The exit status follows the actual result, and a flaky
row is never reused (lanes.plan, tiers.reason). workflow-regression/references/commands.md.

PLAN CACHE: each row's closure is kept per branch in <git common dir>/loop/plans/, keyed by HEAD, .loop/regression.tsv, the
planner's code and LANES_WIDE (key, narrow.warm, narrow.store). A dirty tree never uses it; LANES_NO_CACHE=1 turns it off. The
first output line, `PLAN_CACHE: <state>`, names what happened (commands.md `## Plan cache`).
"""
import hashlib
import json
import os
import platform
import socket

import lanes
import narrow

KNOWN = ".loop/regression-known.tsv"
KINDS = {"requirement": "criterion", "workflow": "workflow", "defect": "defect"}
BASE = None  # the merge-base this run planned from: lanes.save writes it into the record


def kinds(rows, kind):
    """A1e: only the rows of one kind; requirement means category criterion."""
    return rows if not kind else [row for row in rows if row["category"] == KINDS[kind]]


def target(root, args):
    """S23: a goal lane plans from goal_levels: land (default), or nightly for land and nightly rows."""
    return "nightly" if args.tier and args.target == "land" and config(root).get("goal_levels") == "nightly" else args.target


def config(root):
    try:
        data = json.load(open(os.path.join(root, ".loop", "config.json")))
    except (OSError, ValueError):
        data = {}
    return data if isinstance(data, dict) else {}


def merge_base(root, base):
    for ref in ("origin/" + base, base):
        out = lanes.git(root, "merge-base", "HEAD", ref)
        if out and out.strip():
            return out.strip()
    return None


def usable(root, record, base):
    """F4 record usability: (record or None, usable); usable only when its merge-base equals the current one."""
    old, _ = lanes.load(record, root)
    return old, bool(old and base and old.get("merge_base") == base)


def current(root, name):
    try:
        lines = open(os.path.join(root, ".loop", name)).read().splitlines()
    except OSError:
        return {}
    return {line.split("\t")[0]: line for line in lines if line.strip() and line[0] != "#"}


def changed(root, commit, memo):
    seen = memo.setdefault("from", {})
    if commit not in seen:
        seen[commit] = lanes.changed(root, commit) or []
    return seen[commit]


def key(root):
    """(sha256 hex, parts) of the plan cache's key: schema, planner code, HEAD, the row file, LANES_WIDE."""
    try:
        with open(os.path.join(root, lanes.TABLE), "rb") as handle:
            rows = hashlib.sha256(handle.read()).hexdigest()
    except OSError:
        rows = ""
    parts = ["1", lanes.runner(), (lanes.git(root, "rev-parse", "HEAD") or "").strip(), rows,
             "1" if os.environ.get("LANES_WIDE") == "1" else "0"]
    return hashlib.sha256(json.dumps(parts).encode()).hexdigest(), parts


def plan_file(record):
    """The record's path with its tests folder swapped for plans: the cache file of that branch."""
    folder, name = os.path.split(record)
    return os.path.join(os.path.dirname(folder), "plans", name)


def lead(root, picked, record, cache):
    """Decide the cache state, print its PLAN_CACHE line first and seed cache; (file, key) when a miss may be saved."""
    off, now, path, left = os.environ.get("LANES_NO_CACHE", "").lower() in ("1", "true", "yes"), None, None, []
    if not off and record:
        left = lanes.dirty(root)
        path, now = plan_file(record), key(root)
    line = "off (LANES_NO_CACHE=1)" if off else "none (no branch)" if not record else \
        "dirty (%d paths, cache not used)" % len(left) if left else narrow.warm(path, now, picked, cache)
    print("PLAN_CACHE: " + line)
    return (path, now) if line.startswith("miss") else (None, None)


def moved(root, old, base):
    """What the base brought in since the record's merge-base (a base merge): those rows rerun on the merged result."""
    was = (old or {}).get("merge_base")
    out = lanes.git(root, "diff", "--name-only", "--no-renames", was, base) if was and base and was != base else ""
    return (out or "").split()


def ancestor(root, commit, memo):
    """lanes.ancestor once per commit per plan: most rows of a full record share one commit."""
    cache = memo.setdefault("anc", {})
    if commit not in cache:
        cache[commit] = lanes.ancestor(root, commit)
    return cache[commit]


def since(root, row, old, ok, base, memo):
    """(commit to compare the row's table line with, paths changed for this row)."""
    prior = (old or {}).get("rows", {}).get(row["id"])
    seen = bool(prior) and ancestor(root, prior["commit"], memo)
    if seen and ok:  # a usable record: only what changed since this row last ran
        return prior["commit"], changed(root, prior["commit"], memo)
    extra = changed(root, prior["commit"], memo) if seen else []
    return base, sorted(set(changed(root, base, memo)) | set(extra) | set(memo["moved"]))


def hit(root, row, path, at, cache, memo):
    if path == lanes.TABLE:
        return lanes.reads_table(root, row["command"], cache)
    if path == KNOWN:
        return lanes.table(root, at, "regression-known.tsv", memo).get(row["id"]) != memo["known"].get(row["id"])
    return lanes.touches(root, row["command"], path, cache)


def reason(root, row, old, ok, base, cache, memo):
    """F4 closure rows: why this row runs, or '' (failure rerun, new row, reaches <file>, root runner)."""
    if ok and old["rows"].get(row["id"], {}).get("status") == "FAIL":
        return "failure rerun"
    at, paths = since(root, row, old, ok, base, memo)
    if lanes.table(root, at, "regression.tsv", memo).get(row["id"]) != memo["tsv"].get(row["id"]):
        return "new row"
    found = next((p for p in paths if hit(root, row, p, at, cache, memo)), None)
    if found:
        return "reaches " + found
    if paths and lanes.closure(root, row["command"], cache)[1]:
        return "root runner"
    return "failure rerun (flaky: never reused)" if (old or {}).get("rows", {}).get(row["id"], {}).get("flaky") else ""


def quiet(path, gone):
    """Paths the unmapped rule ignores: deleted ones (listed apart), the loop's tables and files no row reads."""
    return path in gone or path in (lanes.TABLE, KNOWN) or path.startswith(lanes.BOOKKEEPING) or any(
        path == n or (n.endswith("/") and path.startswith(n)) for n in lanes.NO_EFFECT)


def unmapped(root, picked, base, cache):
    """F4 unmapped rule: (paths no row maps, deleted paths) the goal changed since the merge-base."""
    gone = lanes.deleted(root, base)
    deps = [lanes.closure(root, row["command"], cache)[0] for row in picked]
    return [p for p in lanes.changed(root, base) or [] if not quiet(p, gone) and not any(lanes.hits(p, d) for d in deps)], gone


def notes(loose, gone):
    """The advisory UNMAPPED lines (DX-15, DX-18): a path no row maps, or a deleted one, picks the rows that name it and the
    runners, never a full run (REG-7); whatever the time budget leaves is the scheduled full suite's."""
    return ["UNMAPPED %s: no row declares it. Note: the rows that name it and the runners run; declare it in the "
            "# reads: header of the row that tests it to map it" % p for p in loose] + [
            "UNMAPPED %s: deleted. Note: the rows that name it and the runners run" % p for p in gone]


def picks(root, picked, paths, old, ok, cache, memo):
    """{row id: why} for the rows a path no row maps (or a deleted one) selects: those naming it, and the runners. A row
    picks it up only while that path is among its changes since it last ran, so a lane after it reuses the result."""
    found = {}
    for row in picked:
        mine = [p for p in paths if p in since(root, row, old, ok, BASE, memo)[1]]
        if mine and lanes.hits(lanes.RUNNER, lanes.closure(root, row["command"], cache)[0]):
            found[row["id"]] = "root runner (unmapped path)"
        elif mine and lanes.names_any(root, row["command"], mine, cache):
            found[row["id"]] = "names an unmapped path"
    return found


def plan(root, picked, record):
    """(to run ids in tier order, reused ids, usable record or None, why no plan or ''); prints its plan lines."""
    global BASE
    name = config(root).get("base") or "main"
    BASE = merge_base(root, name)
    cache, memo = {}, {"tsv": current(root, "regression.tsv"), "known": current(root, "regression-known.tsv")}
    saved, now = lead(root, picked, record, cache)
    old, ok = usable(root, record, BASE)
    memo["moved"] = moved(root, old, BASE)
    loose, gone, why = [], [], {}
    full, text, lines = "no merge-base with %s" % name, "can't tell what this branch changed (a shallow clone or a " \
        "missing base ref), so every row is a candidate and the time budget keeps what fits", []
    if BASE:
        loose, gone = unmapped(root, picked, BASE, cache)
        why = {row["id"]: reason(root, row, old, ok, BASE, cache, memo) for row in picked}
        lines, full = notes(loose, gone), ""
        for rid, because in (picks(root, picked, loose + gone, old, ok, cache, memo) if loose or gone else {}).items():
            why[rid] = why[rid] or because
    why = {row["id"]: why.get(row["id"]) or ("FULL" if full else "") for row in picked}
    todo = [row["id"] for row in picked if why[row["id"]]]
    todo.sort(key=lambda rid: why[rid].startswith(("root runner", "names")))  # the goal's own rows first, the picks after
    reused = [rid for rid in why if ok and rid in old["rows"] and not why[rid]]
    print("\n".join(lines)) if lines else None
    summary(picked, todo, why, len(loose) + len(gone), (full, text), old if ok else None)
    failed = narrow.store(saved, now, cache) if saved and key(root) == now else None
    print("PLAN_CACHE: not saved (%s)" % failed) if failed else None
    return todo, reused, old if ok else None, full


def summary(picked, todo, why, count, full, old):
    """The kind line (FULL (<reason>), REUSED or AFFECTED), one SELECTED line per row and the ROWS line (DX-12, DX-20)."""
    if full[0]:
        print("FULL (%s): %s" % full)
    elif not todo and old:
        print("REUSED %d rows from %s (%s)" % (len(picked), old["commit"][:12], old["at"]))
    else:
        ids = ", ".join(todo[:10]) + (", +%d more" % (len(todo) - 10) if len(todo) > 10 else "")
        print("AFFECTED %d of %d rows (%s): changed since %s" % (len(todo), len(picked), ids or "none", BASE[:12]))
    for rid in todo:
        print("SELECTED %s: %s" % (rid, why[rid]))
    first = [why[rid].split()[0] for rid in todo]
    print("ROWS: %d selected (%d affected, %d new, %d root runners, %d failure reruns), %d reused; unmapped: %d" % (
        len(todo), first.count("reaches"), first.count("new"), first.count("root"), first.count("failure"),
        len(picked) - len(todo), count))


def suite_time(root, args, head, results, day):
    """REG-7 (S14, S25): only the plain full run `regression.py run nightly` (no row id, --reuse, --tier or --kind)
    appends `<sha> TAB full TAB <seconds> TAB <date>` to <git common dir>/loop/suite-times.tsv, outside the worktree so
    it never dirties a lane, and prints SUITE_TIME; health's cost.py reads the newest line."""
    if args.target != "nightly" or args.reuse or args.tier or args.kind or not results:
        return
    seconds = int(round(sum(item["seconds"] for item in results)))
    folder = os.path.join(root, (lanes.git(root, "rev-parse", "--git-common-dir") or ".git").strip(), "loop")
    os.makedirs(folder, exist_ok=True)
    with open(os.path.join(folder, "suite-times.tsv"), "a") as handle:
        handle.write("%s\tfull\t%d\t%s\n" % (head, seconds, day))
    print("SUITE_TIME %d" % seconds)


def runner():
    return socket.gethostname(), platform.python_version()


def previous(record):
    """The lane record's rows as written, with no schema or code check: the same commit means the same code."""
    try:
        with open(record) as handle:
            rows = json.load(handle).get("rows")
        return rows if isinstance(rows, dict) else {}
    except (OSError, ValueError, TypeError, AttributeError):
        return {}


def compare(prev, state, head, clean):
    """The row's flaky flag after this result: the commit it flipped on, or ''."""
    prev = prev if isinstance(prev, dict) else {}
    mark = str(prev.get("flaky") or "")
    if not clean:
        return mark
    if prev.get("commit") == head and prev.get("clean") == "yes" and (prev.get("host"), prev.get("python")) == runner():
        if mark == head or (prev.get("status") == "PASS") != (state == "PASS"):
            return head
    return "" if state == "PASS" and mark != head else mark


def word(passed):
    return "passed" if passed else "failed"


def flaky_apply(record, results, head, clean):
    """Give each result its commit, clean, host, python and (on a clean tree) flaky fields; return the FLAKY lines."""
    rows, (host, python), lines = previous(record) if record else {}, runner(), []
    for item in results:
        item.update(commit=head, clean="yes" if clean else "no", host=host, python=python)
        if not clean:
            continue
        item["flaky"] = compare(rows.get(item["id"]), item["state"], head, clean)
        if item["flaky"] == head:
            now, was = item["state"] == "PASS", (rows.get(item["id"]) or {}).get("status") == "PASS"
            seen = "%s then %s" % (word(was), word(now)) if was != now else "%s again, still flaky" % word(now)
            lines.append("FLAKY %s: %s on %s (same clean tree; runner %s, python %s). Note: the result counts as %s; "
                         "the row is never reused while flaky" % (item["id"], seen, head[:12], host, python, word(now)))
    return lines
