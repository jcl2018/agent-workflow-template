#!/usr/bin/env python3
"""Keep a repo's regression tests visible and enforced.

usage: regression.py <command> [options]

  add ID --level L --command C [--goal SLUG:N] [--describe TEXT] [--category C --link L]
                                add or replace a row. L is land, nightly, draft or covered;
                                TEXT says in plain words what the test checks; C is criterion (default), workflow (an
                                end-to-end run of a whole flow on a toy repo) or defect, and a defect row needs L, the
                                issue URL or finding:SLUG it keeps fixed
  sync [--write]                list done lines and criteria with no row, rows with no description, rows never seen
                                failing; --write drafts rows (a criterion's row has its id as id or goal)
  criteria                      run each wiki criterion's row; print one UNMET line for each missing, draft or failing
  red ID --break CMD            copy HEAD, run CMD to break it, and record that the test fails there
  run [land|nightly|ID] [--timeout S] [--live] [--reuse [--tier goal]] [--kind requirement|workflow|defect]
                                run the rows (of one kind), then open, update or close one issue per failing row;
                                --tier goal plans a goal lane (tiers.py); a plain run nightly records its time (SUITE_TIME)
  workflow [--visibility V]     a public repo: write regression.yml (schedule in regression_cron) and regression-pr.yml (the rows
                                a change reaches, on pull_request and push); a private repo's regression runs on the Mac: nothing
  reads ROW                     suggest a # reads: header for ROW's script from the newest check-reads trace

Rows live in .loop/regression.tsv: id, level, command, goal, seen_red, description, category, link. Each run records its rows' last status and
date and run (Actions URL or commit sha) in .loop/regression-runs.tsv (runs.py), which the wiki Tests tables show. Known failures live in .loop/regression-known.tsv: id, reason. A known failure never blocks. A row never seen failing does.
Issues dry-run unless GH_TOKEN or GITHUB_TOKEN is set, or you pass --live. It runs git, gh and your test
commands, and nothing else.
"""
import argparse
import datetime
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.dont_write_bytecode = True  # no __pycache__ in the skill folder: the package check refuses one
import actions, lanes, lanes_cli, runs, slots, tiers  # noqa: E401,E402
from runs import chosen, clean, criteria_ids, criterion_rows, done_lines, lines_of, today  # noqa: E402,F401

# No terminal, no waiting: a prompt from git or gh must fail, not block.
os.environ.update(GIT_TERMINAL_PROMPT="0", GH_PROMPT_DISABLED="1", GIT_EDITOR="true", GIT_ASKPASS="true", SSH_ASKPASS="true")
if not sys.stdin or not sys.stdin.isatty():
    os.dup2(os.open(os.devnull, os.O_RDONLY), 0)

LEVELS = ("land", "nightly", "draft", "covered")
ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,60}$")
FIELDS = ("id", "level", "command", "goal", "seen_red", "description", "category", "link")
SEEN = re.compile(r"\d{4}-\d{2}-\d{2}$")  # seen_red counts only as a date; "", "-" or any other text is never seen failing
HEADER = "# " + "\t".join(FIELDS) + "\n"
CRON = "17 */4 * * *"
def run(args, cwd=None):
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True)


def git(*args, cwd=None):
    done = run(["git"] + list(args), cwd=cwd)
    if done.returncode:
        sys.exit("REFUSED: git %s: %s" % (" ".join(args), done.stderr.strip()[:300]))
    return done.stdout.strip()


def top():
    return git("rev-parse", "--show-toplevel")


def path_of(root, name):
    return os.path.join(root, ".loop", name)


def cells_of(root, name):
    try:
        with open(path_of(root, name)) as handle:
            return [line.rstrip("\n").split("\t") + [""] * 8 for line in handle if line.strip() and line[0] != "#"]
    except OSError:
        return []


def read_rows(root):
    rows = {cells[0]: dict(zip(FIELDS, cells)) for cells in cells_of(root, "regression.tsv")}
    for row in rows.values():
        row["category"] = row["category"] or "criterion"
    return rows


def edit_rows(root, change):
    """Re-read the rows, apply this command's change and write, under the table's lock (slots.edit)."""
    def apply():
        rows = read_rows(root)
        change(rows)
        os.makedirs(os.path.join(root, ".loop"), exist_ok=True)
        slots.write_table(path_of(root, "regression.tsv"), HEADER, ["\t".join(r[n] for n in FIELDS) for r in rows.values()])
    slots.edit(root, "regression.tsv", apply)


def new(**kw):
    return {name: kw.get(name, "") for name in FIELDS}


def known(root):
    return {cells[0]: cells[1] for cells in cells_of(root, "regression-known.tsv")}


def cmd_add(args):
    if not ID.match(args.id):
        sys.exit("REFUSED: bad id. Fix: letters, digits, dots, dashes.")
    root = top()
    if args.category == "defect" and not args.link:
        sys.exit("REFUSED: a defect row links to its issue or finding. Fix: add --link URL or finding:SLUG.")

    def change(rows):
        old = rows.get(args.id, {})
        rows[args.id] = new(id=args.id, level=args.level, command=clean(args.command), goal=clean(args.goal),
                            category=args.category, link=clean(args.link),
                            seen_red=old.get("seen_red", "") if old.get("command") == args.command else "",
                            description=clean(args.describe if args.describe is not None else old.get("description", "")))
    edit_rows(root, change)
    print("ROW %s %s: %s" % (args.id, args.level, args.command))
    return 0


def active(root, slug):
    """A goal still being built: its run record (git common dir) exists and is not done, failed, retired or stopped."""
    common = os.path.join(root, git("rev-parse", "--git-common-dir", cwd=root) or ".git")
    try:
        with open(os.path.join(common, "loop", "runs", slug + ".json")) as handle:
            return json.load(handle).get("status") not in ("done", "failed", "retired", "stopped")
    except (OSError, ValueError, AttributeError):
        return False


def gaps(root):
    rows = read_rows(root)
    covered = {row["goal"] for row in rows.values() if row["goal"]}
    out = []
    for path in sorted(glob.glob(path_of(root, "goals/*.md"))):
        slug = os.path.basename(path)[:-3]
        if not active(root, slug):  # issue 143: a finished goal's done lines are history, its criteria rows guard them
            continue
        for number, line in done_lines(path):
            if "%s:%s" % (slug, number) not in covered:
                out.append((slug, number, line))
    return out


def cmd_sync(args):
    root = top()
    rows, drafted = read_rows(root), {}
    missing = gaps(root)
    for key in criteria_ids(root):
        found = criterion_rows(rows, key)
        if found and not any(row["level"] in ("land", "nightly") for row in found):
            missing.append((key, "", "criterion has no row the workflow runs (land or nightly)"))
        if not found:
            missing.append((key, "", "criterion has no regression row"))
            if args.write:
                rows[key] = drafted[key] = new(id=key, level="draft", command="echo write a test", goal=key)
    for slug, number, line in missing:
        if not number:
            print("GAP %s %s" % (slug, line))
            continue
        print("GAP %s:%s %s" % (slug, number, line[:100]))
        if args.write:
            key = "%s-%s" % (slug, number)
            rows[key] = drafted[key] = new(id=key, level="draft", command="echo write a test", goal="%s:%s" % (slug, number))
    if drafted:
        edit_rows(root, lambda current: [current.setdefault(k, v) for k, v in drafted.items()])
    drafts = [row["id"] for row in rows.values() if row["level"] == "draft"]
    for key in drafts:
        print("DRAFT %s: not run until it has a command and level" % key)
    never = [row["id"] for row in rows.values() if row["level"] in ("land", "nightly") and not SEEN.match(row["seen_red"])]
    for key in never:
        print("UNPROVEN %s: never seen failing. Run red." % key)
    bare = [row["id"] for row in rows.values() if row["level"] != "covered" and not row["description"]]
    for key in bare:
        print("NODESC %s: no description. Fix: add --describe." % key)
    odd = [row["id"] for row in rows.values() if row["category"] not in tiers.KINDS.values()
           or (row["category"] == "defect" and not row["link"])]
    for key in odd:
        print("NOCATEGORY %s: a category of criterion, workflow or defect, and a link for a defect. Fix: add --category, --link." % key)
    if missing or drafts or never or bare or odd:
        return 1
    print("SYNC OK: %d rows" % len(rows))
    return 0


def cmd_criteria(_args):
    root = top()
    rows = read_rows(root)
    unmet = []
    for key in criteria_ids(root):
        found = criterion_rows(rows, key)
        if not found:
            unmet.append("%s (no regression row)" % key)
        for row in found:
            if row["level"] == "draft" or (row["level"] != "covered" and subprocess.run(["sh", "-c", row["command"]], cwd=root,
                                                                                   capture_output=True, env=actions.row_env()).returncode not in (0, runs.SKIP_CODE)):
                unmet.append("%s (row %s is a draft or failing)" % (key, row["id"]))
    print("\n".join(unmet))
    return 1 if unmet else 0


def cmd_red(args):
    root = top()
    rows = read_rows(root)
    row = rows.get(args.id)
    if not row:
        sys.exit("REFUSED: no row %s. Fix: add it first." % args.id)
    temp = tempfile.mkdtemp(prefix="regression-red-")
    tree = os.path.join(temp, "tree")
    git("worktree", "add", "--detach", "--quiet", tree, "HEAD", cwd=root)
    try:
        broke = subprocess.run(args.break_it, shell=True, cwd=tree, capture_output=True, text=True)
        if broke.returncode:
            sys.exit("REFUSED: the break command failed: " + broke.stderr.strip()[:300])
        done = subprocess.run(row["command"], shell=True, cwd=tree, capture_output=True, text=True, env=actions.row_env(),
                              timeout=args.timeout)
    finally:
        run(["git", "worktree", "remove", "--force", tree], cwd=root)
        shutil.rmtree(temp, ignore_errors=True)
    if done.returncode == runs.SKIP_CODE:
        print("REFUSED: the row exited %d (cannot run here), which is a skip, not a failure. Fix: run red where the row can run." % runs.SKIP_CODE,
              file=sys.stderr)
        return 1
    if done.returncode == 0:
        print("STILL GREEN %s: the test passed on broken code, so it proves nothing." % args.id)
        return 1
    edit_rows(root, lambda current: current[args.id].update(seen_red=today()) if args.id in current else None)
    print("SEEN RED %s on %s" % (args.id, today()))
    return 0


def cmd_run(args):
    root = top()
    rows = read_rows(root)
    if not rows:
        print("NO ROWS: nothing to run" if args.reuse else "NO ROWS: run add first")
        return 0 if args.reuse else 1
    expected, picked = known(root), []
    for row in tiers.kinds(chosen(rows, tiers.target(root, args)), args.kind):
        if row["level"] in ("draft", "covered"):
            print("SKIP %s: %s" % (row["id"], row["level"]))
        else:
            picked.append(row)
    head, record, unclean = git("rev-parse", "HEAD"), lanes.record_path(root), lanes.dirty(root)
    todo, reused, why = [row["id"] for row in picked], [], ""
    if args.reuse and picked and args.tier:
        todo, reused, old, why = tiers.plan(root, picked, record)
    elif args.reuse and picked:
        old, why = lanes.load(record, root)
        if old:
            todo, reused, notes, why = lanes.plan(root, picked, old, lines_of(root, "regression.tsv"),
                                                  lines_of(root, "regression-known.tsv"))
            print("\n".join(notes)) if notes else None
        if why:
            print("FULL: " + why)
        elif not todo:
            print("REUSED %d rows from %s (%s)" % (len(reused), old["commit"][:12], old["at"]))
        else:
            ids = ", ".join(todo[:10]) + (", +%d more" % (len(todo) - 10) if len(todo) > 10 else "")
            print("AFFECTED %d of %d rows (%s): %s" % (len(todo), len(picked), ids,
                                                       " ".join(lanes.changed(root, old["commit"]) or [])[:400]))
    if todo and args.target in ("land", "nightly") and (why or not args.reuse):  # a lane with no plan to follow waits for a slot
        slot = slots.acquire(root, os.environ.get("_LOOP_LANE_LABEL") or os.path.basename(root) + " by hand", head, unclean)
    else:
        slots.started()
    est = {key: item.get("seconds") or 0 for key, item in (old["rows"] if args.reuse and picked and old else {}).items()}
    limit = (args.budget or runs.budget(root)) if args.reuse else None  # CI's plain run is the full suite: no budget
    results, cut = runs.execute(root, picked, todo, est, limit, args.timeout, expected, args.reuse)
    for line in tiers.flaky_apply(record, results, head, not unclean):  # REG-9: advisory; the result decides
        print(line)
    if not args.reuse and results:  # a reusing run writes nothing in the worktree and opens no issue: CI's plain run owns both
        slots.edit(root, "regression-runs.tsv", lambda: runs.write(root, results, today(), head))
    tiers.suite_time(root, args, head, results, today())
    left = sorted(set(lanes.dirty(root)) - set(unclean)) if record and not unclean else []
    if not record:
        print("NOT RECORDED: detached HEAD")
    elif unclean:
        print("NOT RECORDED: uncommitted changes")
    elif left:  # a row that leaves files must not pass by reuse once they're tidied: drop the record, next run is full
        print("NOT RECORDED: the rows left uncommitted files: %s; record dropped" % ", ".join(left[:10]))
        if os.path.exists(record):
            os.remove(record)
    elif results or cut:
        lanes.save(record, root, "regression.py run %s%s" % (args.target, " --reuse" if args.reuse else ""),
                   results + [{"id": key, "state": "LEFT", "seconds": 0} for key in cut],
                   head, datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                   fresh=bool(args.reuse and why), base=tiers.BASE)
    never = [row["id"] for row in picked if not SEEN.match(row["seen_red"])]
    for key in never:
        print("UNPROVEN %s: never seen failing. Fix: python3 %s red %s --break \"<a command that breaks it>\"" % (
            key, os.path.abspath(__file__), key))
    if not args.reuse:
        live = args.live or bool(os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN"))
        runs.sync_issues(results, live, today())
    failed = [item["id"] for item in results if item["state"] == "FAIL"]
    kept = [old["rows"][key]["status"] for key in reused]  # a reused known failure still counts as known
    passed = sum(item["state"] == "PASS" for item in results) + kept.count("PASS")
    print("RESULT %d passed%s, %d known, %d failed, %d unproven%s" % (
        passed, " (%d reused)" % len(reused) if args.reuse else "",
        sum(item["state"] == "KNOWN" for item in results) + kept.count("KNOWN"), len(failed), len(never),
        ", %d skipped" % sum(item["state"] == "SKIPPED" for item in results) if any(item["state"] == "SKIPPED" for item in results) else ""))
    return 1 if failed or never else 0


def cmd_workflow(args):
    return lanes_cli.workflow(top(), args.visibility, lambda: actions.write(top(), CRON))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command_name", required=True)
    item = sub.add_parser("add")
    item.add_argument("id")
    item.add_argument("--level", choices=LEVELS, default="nightly")
    item.add_argument("--command", required=True)
    item.add_argument("--goal", default="")
    item.add_argument("--describe")
    item.add_argument("--category", choices=tuple(tiers.KINDS.values()), default="criterion")
    item.add_argument("--link", default="")
    item.set_defaults(func=cmd_add)
    item = sub.add_parser("sync")
    item.add_argument("--write", action="store_true")
    item.set_defaults(func=cmd_sync)
    sub.add_parser("criteria").set_defaults(func=cmd_criteria)
    item = sub.add_parser("red")
    item.add_argument("id")
    item.add_argument("--break", dest="break_it", required=True)
    item.add_argument("--timeout", type=int, default=900)
    item.set_defaults(func=cmd_red)
    item = sub.add_parser("run")
    item.add_argument("target", nargs="?", default="land")
    item.add_argument("--timeout", type=int, default=900)
    item.add_argument("--reuse", action="store_true", help="reuse this branch's last run; run only the rows a change can affect")
    item.add_argument("--live", action="store_true")
    item.add_argument("--tier", choices=("goal",), help="a goal lane: the rows the branch's change reaches, in tier order, within the time budget (tiers.py)")
    item.add_argument("--kind", choices=tuple(tiers.KINDS))
    item.add_argument("--budget", type=int, default=0, help="seconds a --reuse run may take (default: test_budget_minutes)")
    item.set_defaults(func=cmd_run)
    item = sub.add_parser("workflow")
    item.add_argument("--visibility", choices=("public", "private"), help="skip the probe (the regression_runs setting says it too)")
    item.set_defaults(func=cmd_workflow)
    item = sub.add_parser("reads")
    item.add_argument("id")
    item.set_defaults(func=lambda a: lanes.narrow.suggest(top(), a.id))
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
