#!/usr/bin/env python3
"""The goal tier of `regression.py run land --reuse --tier goal` (REG-4), and `--kind`.

Imported by regression.py, not run. A goal lane plans from the branch's lane record only when that record's merge-base
with the base branch equals the current one, else from the merge-base. It runs the rows whose closure reaches a file
changed since then (lanes.py's closure), the rows added or changed in .loop/regression.tsv since then, the rows that
run tools on the repo root (lanes.ROOT_RUN, when anything changed), a usable record's FAIL rows and any flaky row
(flaky_apply below: never reused). After a base merge
the record is not usable, and the rows the merge changed (since each row's recorded commit) run too. A path no row
maps, or a deleted one, is a Note at qa and ship (the scheduled full run covers it) and makes the pr lane FULL; with no
merge-base the lane is FULL. A FULL goal lane takes a lane slot and gets full_suite_minutes (repo setting, default 30)
as its time limit. Each selected row's reason is printed (SELECTED lines) and summed in one ROWS line for the LANE line.

FLAKY (REG-9), flaky_apply: a row whose result flipped on the same clean commit, runner and python version. Each result
keeps its raw PASS/FAIL; the mark is a separate sticky `flaky` flag (the commit it flipped on). The previous result is the
row in the branch's lane record (<git common dir>/loop/tests/, lanes.py), which keeps commit, clean, host (the runner)
and python per row. Only two results on the same commit, both on a clean tree, from the same host and python version
count: either order (FAIL then PASS, PASS then FAIL) marks the row, and the mark stays on that commit (FAIL, PASS, PASS
is still flaky), until a later commit's clean run passes. A dirty tree, `regression.py red`, another runner, or an older
record or regression-runs.tsv without these fields never marks. The exit status follows the actual result, and a flaky
row is never reused (lanes.plan, tiers.reason). workflow-regression/references/commands.md.
"""
import json
import os
import platform
import socket

import lanes

KNOWN = ".loop/regression-known.tsv"
KINDS = {"requirement": "criterion", "workflow": "workflow", "defect": "defect"}
BASE = None  # the merge-base this run planned from: lanes.save writes it into the record


def kinds(rows, kind):
    """A1e: only the rows of one kind; requirement means category criterion."""
    return rows if not kind else [row for row in rows if row["category"] == KINDS[kind]]


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
    return memo.setdefault("from", {}).setdefault(commit, lanes.changed(root, commit) or [])


def moved(root, old, base):
    """What the base brought in since the record's merge-base (a base merge): those rows rerun on the merged result."""
    was = (old or {}).get("merge_base")
    out = lanes.git(root, "diff", "--name-only", "--no-renames", was, base) if was and base and was != base else ""
    return (out or "").split()


def since(root, row, old, ok, base, memo):
    """(commit to compare the row's table line with, paths changed for this row)."""
    prior = (old or {}).get("rows", {}).get(row["id"])
    seen = bool(prior) and lanes.ancestor(root, prior["commit"])
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


def full_limit(root):
    """A FULL goal lane's time limit: full_suite_minutes, written next to the lane's started marker for lane.py."""
    marker = os.environ.get("_LOOP_LANE_STARTED")
    if marker and not os.path.exists(marker):  # an existing marker is an outer lane's: a row's nested run never sets it
        with open(marker.rsplit(".started", 1)[0] + ".limit", "w") as handle:
            handle.write("%s\n" % (float(config(root).get("full_suite_minutes") or 30) * 60))


def notes(lane, loose, gone):
    """((FULL reason or '', its text), advisory UNMAPPED lines): FULL at pr, a Note at qa and ship (DX-15, DX-18)."""
    if lane == "pr" and loose:
        return ("unmapped %s at pr" % loose[0], "no row declares %s, so the pr lane runs the full suite once" % loose[0]), []
    if lane == "pr" and gone:
        return ("deleted %s" % gone[0], "a deleted file can't be declared, so the pr lane runs the full suite once"), []
    lines = ["UNMAPPED %s: no row declares it. Note: the pr lane runs the full suite once for it; declare it in the "
             "# reads: header of the row that tests it to avoid that" % p for p in loose]
    return ("", ""), lines + ["UNMAPPED %s: deleted. Note: the pr lane runs the full suite once for it" % p for p in gone]


def plan(root, picked, record):
    """(to run ids, reused ids, usable record or None, FULL reason or '') for a goal lane; prints its plan lines."""
    global BASE
    name = config(root).get("base") or "main"
    BASE = merge_base(root, name)
    cache, memo = {}, {"tsv": current(root, "regression.tsv"), "known": current(root, "regression-known.tsv")}
    old, ok = usable(root, record, BASE)
    memo["moved"] = moved(root, old, BASE)
    loose, gone, why = [], [], {}
    (full, text), lines = ("no merge-base with %s" % name, "can't tell what this branch changed (a shallow clone or a "
                           "missing base ref), so every row runs"), []
    if BASE:
        loose, gone = unmapped(root, picked, BASE, cache)
        why = {row["id"]: reason(root, row, old, ok, BASE, cache, memo) for row in picked}
        (full, text), lines = notes((os.environ.get("_LOOP_LANE_LABEL") or "hand").split()[-1], loose, gone)
    why = {row["id"]: why.get(row["id"]) or ("FULL" if full else "") for row in picked}
    todo = [row["id"] for row in picked if why[row["id"]]]
    reused = [rid for rid in why if ok and rid in old["rows"] and not why[rid]]
    print("\n".join(lines)) if lines else None
    summary(picked, todo, why, len(loose) + len(gone), (full, text), old if ok else None)
    if full:
        full_limit(root)
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
            now = item["state"] == "PASS"
            lines.append("FLAKY %s: %s then %s on %s (same clean tree; runner %s, python %s). Note: the result counts as %s; "
                         "the row is never reused while flaky" % (item["id"], word(not now), word(now), head[:12], host,
                                                                 python, word(now)))
    return lines
