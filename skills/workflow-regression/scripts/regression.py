#!/usr/bin/env python3
"""Keep a repo's regression tests visible and enforced.

usage: regression.py <command> [options]

  add ID --level L --command C [--goal SLUG:N] [--describe TEXT] [--category C --link L]
                                add or replace a row. L is land, nightly, draft or covered;
                                TEXT says in plain words what the test checks; C is criterion (default) or defect, and
                                a defect row needs L, the issue URL or finding:SLUG it keeps fixed
  sync [--write]                list done lines and criteria with no row, rows with no description, rows never seen
                                failing; --write drafts rows (a criterion's row has its id as id or goal)
  criteria                      run each wiki criterion's row; print one UNMET line for each missing, draft or failing
  red ID --break CMD            copy HEAD, run CMD to break it, and record that the test fails there
  run [land|nightly|ID] [--timeout S] [--live] [--reuse]
                                run the rows, then open, update or close one issue per failing row
  workflow                      write .github/workflows/regression.yml, on the schedule in regression_cron

Rows live in .loop/regression.tsv: id, level, command, goal, seen_red, description, category, link. Each run records its rows' last status and
date in .loop/regression-runs.tsv, which the wiki Tests tables show. Known failures live in .loop/regression-known.tsv: id, reason. A known failure never blocks. A row never seen failing does.
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
import actions, lanes  # noqa: E401,E402

# No terminal, no waiting: a prompt from git or gh must fail, not block.
os.environ.update(GIT_TERMINAL_PROMPT="0", GH_PROMPT_DISABLED="1", GIT_EDITOR="true", GIT_ASKPASS="true", SSH_ASKPASS="true")
if not sys.stdin or not sys.stdin.isatty():
    os.dup2(os.open(os.devnull, os.O_RDONLY), 0)

LEVELS = ("land", "nightly", "draft", "covered")
ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,60}$")
FIELDS = ("id", "level", "command", "goal", "seen_red", "description", "category", "link")
SEEN = re.compile(r"\d{4}-\d{2}-\d{2}$")  # seen_red counts only as a date; "", "-" or any other text is never seen failing
HEADER = "# " + "\t".join(FIELDS) + "\n"
CRON = "17 9 * * *"
MARK = "<!-- loop-regression %s -->"
def run(args, cwd=None):
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True)


def git(*args, cwd=None):
    done = run(["git"] + list(args), cwd=cwd)
    if done.returncode:
        sys.exit("REFUSED: git %s: %s" % (" ".join(args), done.stderr.strip()[:300]))
    return done.stdout.strip()


def top():
    return git("rev-parse", "--show-toplevel")


def today():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")


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


def write_rows(root, rows):
    os.makedirs(os.path.join(root, ".loop"), exist_ok=True)
    temp = path_of(root, "regression.tsv.tmp")
    with open(temp, "w") as handle:
        handle.write(HEADER)
        for key in rows:
            row = rows[key]
            handle.write("\t".join(row[name] for name in FIELDS) + "\n")
    os.replace(temp, path_of(root, "regression.tsv"))


def new(**kw):
    return {name: kw.get(name, "") for name in FIELDS}


def known(root):
    return {cells[0]: cells[1] for cells in cells_of(root, "regression-known.tsv")}


def clean(text):
    if "\t" in text or "\n" in text:
        sys.exit("REFUSED: a row can't hold a tab or new line. Fix: use a script.")
    return text


def cmd_add(args):
    if not ID.match(args.id):
        sys.exit("REFUSED: bad id. Fix: letters, digits, dots, dashes.")
    root = top()
    rows = read_rows(root)
    old = rows.get(args.id, {})
    same = old.get("command") == args.command
    if args.category == "defect" and not args.link:
        sys.exit("REFUSED: a defect row links to its issue or finding. Fix: add --link URL or finding:SLUG.")
    rows[args.id] = new(id=args.id, level=args.level, command=clean(args.command), goal=clean(args.goal),
                        category=args.category, link=clean(args.link),
                        seen_red=old.get("seen_red", "") if same else "",
                        description=clean(args.describe if args.describe is not None else old.get("description", "")))
    write_rows(root, rows)
    print("ROW %s %s: %s" % (args.id, args.level, args.command))
    return 0


def done_lines(path):
    with open(path) as handle:
        part = handle.read().split("## Done lines", 1)[-1].split("\n## ", 1)[0]
    return re.findall(r"^(\d+)\.\s+(.+)$", part, re.M)


def gaps(root):
    rows = read_rows(root)
    covered = {row["goal"] for row in rows.values() if row["goal"]}
    out = []
    for path in sorted(glob.glob(path_of(root, "goals/*.md"))):
        slug = os.path.basename(path)[:-3]
        for number, line in done_lines(path):
            if "%s:%s" % (slug, number) not in covered:
                out.append((slug, number, line))
    return out


def criteria_ids(root):
    """Requirement ids written under ## Requirements (or the old ## Criteria) in the wiki pages, outside code fences."""
    try:
        with open(path_of(root, "config.json")) as handle:
            folder = json.load(handle).get("wiki_dir") or "docs/wiki"
    except (OSError, ValueError):
        folder = "docs/wiki"
    ids = []
    for name in sorted(glob.glob(os.path.join(root, folder, "*.md"))):
        with open(name) as handle:
            text = re.sub(r"(?ms)^```.*?^```[^\n]*$", "", handle.read())
        if re.search(r"\n## (?:Requirements|Criteria)[ \t]*\n", text):
            part = re.split(r"\n## (?:Requirements|Criteria)[ \t]*\n", text, maxsplit=1)[1].split("\n## ", 1)[0]
            ids += re.findall(r"^- ([A-Z]{2,5}-\d+): \S", part, re.M)
    return ids


def criterion_rows(rows, key):
    return [row for row in rows.values() if key in (row["id"], row["goal"]) and row["category"] != "defect"]


def cmd_sync(args):
    root = top()
    rows = read_rows(root)
    missing = gaps(root)
    for key in criteria_ids(root):
        found = criterion_rows(rows, key)
        if found and not any(row["level"] in ("land", "nightly") for row in found):
            missing.append((key, "", "criterion has no row the workflow runs (land or nightly)"))
        if not found:
            missing.append((key, "", "criterion has no regression row"))
            if args.write:
                rows[key] = new(id=key, level="draft", command="echo write a test", goal=key)
    for slug, number, line in missing:
        if not number:
            print("GAP %s %s" % (slug, line))
            continue
        print("GAP %s:%s %s" % (slug, number, line[:100]))
        if args.write:
            key = "%s-%s" % (slug, number)
            rows[key] = new(id=key, level="draft", command="echo write a test", goal="%s:%s" % (slug, number))
    if args.write:
        write_rows(root, rows)
    drafts = [row["id"] for row in rows.values() if row["level"] == "draft"]
    for key in drafts:
        print("DRAFT %s: not run until it has a command and level" % key)
    never = [row["id"] for row in rows.values() if row["level"] in ("land", "nightly") and not SEEN.match(row["seen_red"])]
    for key in never:
        print("UNPROVEN %s: never seen failing. Run red." % key)
    bare = [row["id"] for row in rows.values() if row["level"] != "covered" and not row["description"]]
    for key in bare:
        print("NODESC %s: no description. Fix: add --describe." % key)
    odd = [row["id"] for row in rows.values() if row["category"] not in ("criterion", "defect")
           or (row["category"] == "defect" and not row["link"])]
    for key in odd:
        print("NOCATEGORY %s: a category of criterion or defect, and a link for a defect. Fix: add --category, --link." % key)
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
            if row["level"] == "draft" or (row["level"] != "covered" and run(["sh", "-c", row["command"]], cwd=root).returncode):
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
    if done.returncode == 0:
        print("STILL GREEN %s: the test passed on broken code, so it proves nothing." % args.id)
        return 1
    row["seen_red"] = today()
    write_rows(root, rows)
    print("SEEN RED %s on %s" % (args.id, row["seen_red"]))
    return 0


def chosen(rows, target):
    if target in rows:
        return [rows[target]]
    if target == "land":
        return [row for row in rows.values() if row["level"] == "land"]
    if target == "nightly":
        return [row for row in rows.values() if row["level"] in ("land", "nightly")]
    sys.exit("REFUSED: no row or level called %s." % target)


def gh(*args):
    return run(["gh"] + list(args))


def sync_issues(results, live):
    """One issue per failing row, keyed by a marker in its body."""
    issues = []
    if live:
        gh("label", "create", "regression", "--force", "--description", "A regression row is failing")
        out = gh("issue", "list", "--label", "regression", "--state", "all", "--limit", "200",
                 "--json", "number,state,body,comments")
        if out.returncode:
            print("NOTE: can't read issues, so none changed: " + out.stderr.strip()[:200])
            return
        issues = json.loads(out.stdout or "[]")
    day = today()
    for item in results:
        mark = MARK % item["id"]
        hits = [issue for issue in issues if mark in issue.get("body", "")]
        hit = next((issue for issue in hits if issue.get("state") == "OPEN"), hits[0] if hits else None)
        number = str(hit["number"]) if hit else ""
        if item["state"] == "FAIL":
            line = "Failing on %s." % day
            body = "%s\nThe row `%s` fails.\n\n```\n%s\n```\n" % (mark, item["id"], item["tail"])
            if not live:
                print("WOULD open or update the issue for " + item["id"])
            elif not hit:
                gh("issue", "create", "--title", "Regression: " + item["id"], "--label", "regression", "--body", body)
                print("OPENED issue for " + item["id"])
            else:
                if hit.get("state") != "OPEN":
                    gh("issue", "reopen", number)
                    print("REOPENED issue %s" % number)
                said = [note.get("body", "") for note in hit.get("comments") or []]
                if line not in said:
                    gh("issue", "comment", number, "--body", line)
                    print("UPDATED issue %s" % number)
        elif item["state"] == "PASS" and not live:
            print("WOULD close any open issue for " + item["id"])
        elif item["state"] == "PASS":
            for issue in hits:
                if issue.get("state") == "OPEN":
                    gh("issue", "close", str(issue["number"]), "--comment", "Passing again on %s." % day)
                    print("CLOSED issue %s" % issue["number"])


def lines_of(root, name):
    return {line.split("\t")[0]: line.rstrip("\n") for line in open(path_of(root, name)) if line.strip() and line[0] != "#"} \
        if os.path.exists(path_of(root, name)) else {}


def cmd_run(args):
    root = top()
    rows = read_rows(root)
    if not rows:
        print("NO ROWS: nothing to run" if args.reuse else "NO ROWS: run add first")
        return 0 if args.reuse else 1
    expected, picked = known(root), []
    for row in chosen(rows, args.target):
        if row["level"] in ("draft", "covered"):
            print("SKIP %s: %s" % (row["id"], row["level"]))
        else:
            picked.append(row)
    head, record, unclean = git("rev-parse", "HEAD"), lanes.record_path(root), lanes.dirty(root)
    todo, reused, why = [row["id"] for row in picked], [], ""
    if args.reuse and picked:
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
    results = []
    for row in [r for r in picked if r["id"] in todo]:
        began = time.time()
        try:
            done = subprocess.run(row["command"], shell=True, cwd=root, capture_output=True, text=True, env=actions.row_env(),
                                  timeout=args.timeout)
            code, text = done.returncode, done.stdout + done.stderr
        except subprocess.TimeoutExpired:
            code, text = 124, "timed out after %s seconds" % args.timeout
        state = "PASS" if code == 0 else ("KNOWN" if row["id"] in expected else "FAIL")
        if code == 0 and row["id"] in expected:
            print("FIXED %s: remove it from the known list" % row["id"])
        reason = " (%s)" % expected[row["id"]] if state == "KNOWN" else ""
        print("%s %s%s" % (state, row["id"], reason), flush=True)
        if state == "FAIL" and args.reuse:
            print("\n".join("    " + line for line in text.rstrip().splitlines()[-20:]), file=sys.stderr)
        results.append({"id": row["id"], "state": state, "tail": text[-1500:], "seconds": round(time.time() - began, 1)})
    if not args.reuse:  # a reusing run writes nothing in the worktree and opens no issue: CI's plain run owns both
        ran = {cells[0]: cells[:3] for cells in cells_of(root, "regression-runs.tsv")}
        for item in results:
            ran[item["id"]] = [item["id"], "PASS" if item["state"] == "PASS" else "FAIL", today()]
        if results:
            with open(path_of(root, "regression-runs.tsv"), "w") as handle:
                handle.write("# id\tstatus\tdate\n" + "".join("\t".join(ran[key]) + "\n" for key in sorted(ran)))
    left = sorted(set(lanes.dirty(root)) - set(unclean)) if record and not unclean else []
    if not record:
        print("NOT RECORDED: detached HEAD")
    elif unclean:
        print("NOT RECORDED: uncommitted changes")
    elif left:  # a row that leaves files must not pass by reuse once they're tidied: drop the record, next run is full
        print("NOT RECORDED: the rows left uncommitted files: %s; record dropped" % ", ".join(left[:10]))
        if os.path.exists(record):
            os.remove(record)
    elif results:
        lanes.save(record, root, "regression.py run %s%s" % (args.target, " --reuse" if args.reuse else ""), results,
                   head, datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                   fresh=bool(args.reuse and why))
    never = [row["id"] for row in picked if not SEEN.match(row["seen_red"])]
    for key in never:
        print("UNPROVEN %s: never seen failing. Fix: python3 %s red %s --break \"<a command that breaks it>\"" % (
            key, os.path.abspath(__file__), key))
    if not args.reuse:
        live = args.live or bool(os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN"))
        sync_issues(results, live)
        if live:  # the issue states the wiki and health show, each with its date
            run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "tests.py"), "issues", "--write"], root)
    failed = [item["id"] for item in results if item["state"] == "FAIL"]
    kept = [old["rows"][key]["status"] for key in reused]  # a reused known failure still counts as known
    passed = sum(item["state"] == "PASS" for item in results) + kept.count("PASS")
    print("RESULT %d passed%s, %d known, %d failed, %d unproven" % (
        passed, " (%d reused)" % len(reused) if args.reuse else "",
        sum(item["state"] == "KNOWN" for item in results) + kept.count("KNOWN"), len(failed), len(never)))
    return 1 if failed or never else 0


def cmd_workflow(_args):
    return actions.write(top(), CRON)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command_name", required=True)
    item = sub.add_parser("add")
    item.add_argument("id")
    item.add_argument("--level", choices=LEVELS, default="nightly")
    item.add_argument("--command", required=True)
    item.add_argument("--goal", default="")
    item.add_argument("--describe")
    item.add_argument("--category", choices=("criterion", "defect"), default="criterion")
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
    item.set_defaults(func=cmd_run)
    sub.add_parser("workflow").set_defaults(func=cmd_workflow)
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
