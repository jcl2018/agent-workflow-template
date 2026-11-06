#!/usr/bin/env python3
"""Keep a repo's regression tests visible and enforced.

usage: regression.py <command> [options]

  seed                          add one land row for each check in .loop/config.json
  add ID --level L --command C [--goal SLUG:N]
                                add or replace a row. L is land, nightly, draft or covered
  sync [--write]                list done lines with no row and rows never seen failing; --write drafts rows
  red ID --break CMD            copy HEAD, run CMD to break it, and record that the test fails there
  run [land|nightly|ID] [--timeout S] [--live]
                                run the rows, then open, update or close one issue per failing row
  workflow                      write .github/workflows/regression.yml

Rows live in .loop/regression.tsv: id, level, command, goal, seen_red. Known failures live in
.loop/regression-known.tsv: id, reason. A known failure never blocks. A row never seen failing does.
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

LEVELS = ("land", "nightly", "draft", "covered")
ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,60}$")
HEADER = "# id\tlevel\tcommand\tgoal\tseen_red\n"
MARK = "<!-- loop-regression %s -->"
WORKFLOW = r"""# Written by workflow-regression. It reads .loop/regression.tsv and .loop/regression-known.tsv.
name: regression
on:
  schedule:
    - cron: "17 9 * * *"
  push:
    tags: ["v*"]
  workflow_dispatch:
permissions:
  contents: read
  issues: write
concurrency:
  group: regression
  cancel-in-progress: false
jobs:
  regression:
    runs-on: ubuntu-latest
    timeout-minutes: 40
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Run the rows, and keep one issue per failing row
        env:
          GH_TOKEN: ${{ github.token }}
        run: |
          python3 - <<'PY'
          import json, os, subprocess, sys
          def rows(path):
              if not os.path.exists(path):
                  return []
              return [line.rstrip("\n").split("\t") for line in open(path) if line.strip() and not line.startswith("#")]
          known = {row[0] for row in rows(".loop/regression-known.tsv")}
          def gh(*args):
              return subprocess.run(("gh",) + args, capture_output=True, text=True)
          gh("label", "create", "regression", "--force", "--description", "A regression row is failing")
          out = gh("issue", "list", "--label", "regression", "--state", "all", "--limit", "200", "--json", "number,state,body")
          issues = json.loads(out.stdout or "[]")
          red = []
          for row in rows(".loop/regression.tsv"):
              if len(row) < 3 or row[1] not in ("land", "nightly"):
                  continue
              done = subprocess.run(row[2], shell=True, capture_output=True, text=True, timeout=900)
              mark = "<!-- loop-regression %s -->" % row[0]
              hits = [item for item in issues if mark in item["body"]]
              hit = next((item for item in hits if item["state"] == "OPEN"), hits[0] if hits else None)
              print("%s %s" % ("PASS" if done.returncode == 0 else "FAIL", row[0]))
              if done.returncode == 0:
                  for item in hits:
                      if item["state"] == "OPEN":
                          gh("issue", "close", str(item["number"]), "--comment", "Passing again.")
              elif row[0] not in known:
                  red.append(row[0])
                  body = "%s\nThe row `%s` fails.\n\n```\n%s\n```\n" % (mark, row[0], (done.stdout + done.stderr)[-1500:])
                  if not hit:
                      gh("issue", "create", "--title", "Regression: " + row[0], "--label", "regression", "--body", body)
                  else:
                      if hit["state"] != "OPEN":
                          gh("issue", "reopen", str(hit["number"]))
                      gh("issue", "comment", str(hit["number"]), "--body", "Still failing.")
          sys.exit(1 if red else 0)
          PY
"""


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


def read_rows(root):
    rows = {}
    try:
        with open(path_of(root, "regression.tsv")) as handle:
            for line in handle:
                if line.strip() and not line.startswith("#"):
                    cells = line.rstrip("\n").split("\t") + [""] * 5
                    rows[cells[0]] = {"id": cells[0], "level": cells[1], "command": cells[2], "goal": cells[3],
                                      "seen_red": cells[4]}
    except OSError:
        pass
    return rows


def write_rows(root, rows):
    os.makedirs(os.path.join(root, ".loop"), exist_ok=True)
    temp = path_of(root, "regression.tsv.tmp")
    with open(temp, "w") as handle:
        handle.write(HEADER)
        for key in rows:
            row = rows[key]
            handle.write("\t".join(row[name] for name in ("id", "level", "command", "goal", "seen_red")) + "\n")
    os.replace(temp, path_of(root, "regression.tsv"))


def known(root):
    held = {}
    try:
        with open(path_of(root, "regression-known.tsv")) as handle:
            for line in handle:
                if line.strip() and not line.startswith("#"):
                    key, _, reason = line.rstrip("\n").partition("\t")
                    held[key] = reason
    except OSError:
        pass
    return held


def clean(text):
    if "\t" in text or "\n" in text:
        sys.exit("REFUSED: a row can't hold a tab or a new line. Fix: put it in a script.")
    return text


def cmd_seed(_args):
    root = top()
    try:
        with open(path_of(root, "config.json")) as handle:
            checks = json.load(handle).get("checks") or []
    except (OSError, ValueError):
        sys.exit("REFUSED: no readable .loop/config.json. Fix: run workflow-setup and merge its branch.")
    rows = read_rows(root)
    held = {row["command"] for row in rows.values()}
    added = 0
    for index, command in enumerate(checks, 1):
        if command not in held:
            key = "check-%d" % index
            rows[key] = {"id": key, "level": "land", "command": clean(command), "goal": "", "seen_red": ""}
            print("ADDED %s: %s" % (key, command))
            added += 1
    write_rows(root, rows)
    print("SEEDED %d rows. Prove each with red." % added)
    return 0


def cmd_add(args):
    if not ID.match(args.id):
        sys.exit("REFUSED: bad id. Fix: letters, digits, dots, dashes.")
    root = top()
    rows = read_rows(root)
    old = rows.get(args.id, {})
    same = old.get("command") == args.command
    rows[args.id] = {"id": args.id, "level": args.level, "command": clean(args.command), "goal": clean(args.goal),
                     "seen_red": old.get("seen_red", "") if same else ""}
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


def untrusted(rows):
    return [row["id"] for row in rows.values() if row["level"] in ("land", "nightly") and not row["seen_red"]]


def cmd_sync(args):
    root = top()
    rows = read_rows(root)
    missing = gaps(root)
    for slug, number, line in missing:
        print("GAP %s:%s %s" % (slug, number, line[:100]))
        if args.write:
            key = "%s-%s" % (slug, number)
            rows[key] = {"id": key, "level": "draft", "command": "echo write a test", "goal": "%s:%s" % (slug, number),
                         "seen_red": ""}
    if args.write:
        write_rows(root, rows)
    drafts = [row["id"] for row in rows.values() if row["level"] == "draft"]
    for key in drafts:
        print("DRAFT %s: not run until you give it a command and a level" % key)
    never = untrusted(rows)
    for key in never:
        print("UNPROVEN %s: never seen failing. Run red." % key)
    if missing or drafts or never:
        return 1
    print("SYNC OK: %d rows" % len(rows))
    return 0


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
        done = subprocess.run(row["command"], shell=True, cwd=tree, capture_output=True, text=True,
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
            print("NOTE: can't read issues, so none were changed: " + out.stderr.strip()[:200])
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
        elif item["state"] == "PASS" and live and hits:
            for issue in hits:
                if issue.get("state") == "OPEN":
                    gh("issue", "close", str(issue["number"]), "--comment", "Passing again on %s." % day)
                    print("CLOSED issue %s" % issue["number"])
        elif item["state"] == "PASS" and not live:
            print("WOULD close any open issue for " + item["id"])


def cmd_run(args):
    root = top()
    rows = read_rows(root)
    if not rows:
        print("NO ROWS: run seed or add first")
        return 1
    expected = known(root)
    results = []
    for row in chosen(rows, args.target):
        if row["level"] in ("draft", "covered"):
            print("SKIP %s: %s" % (row["id"], row["level"]))
            continue
        try:
            done = subprocess.run(row["command"], shell=True, cwd=root, capture_output=True, text=True,
                                  timeout=args.timeout)
            code, text = done.returncode, done.stdout + done.stderr
        except subprocess.TimeoutExpired:
            code, text = 124, "timed out after %s seconds" % args.timeout
        state = "PASS" if code == 0 else ("KNOWN" if row["id"] in expected else "FAIL")
        if code == 0 and row["id"] in expected:
            print("FIXED %s: remove it from the known list" % row["id"])
        reason = " (%s)" % expected[row["id"]] if state == "KNOWN" else ""
        print("%s %s%s" % (state, row["id"], reason), flush=True)
        results.append({"id": row["id"], "state": state, "tail": text[-1500:]})
    never = [item["id"] for item in results if not rows[item["id"]]["seen_red"]]
    for key in never:
        print("UNPROVEN %s: never seen failing. Run red." % key)
    live = args.live or bool(os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN"))
    sync_issues(results, live)
    failed = [item["id"] for item in results if item["state"] == "FAIL"]
    print("RESULT %d passed, %d known, %d failed, %d unproven" % (
        sum(item["state"] == "PASS" for item in results), sum(item["state"] == "KNOWN" for item in results),
        len(failed), len(never)))
    return 1 if failed or never else 0


def cmd_workflow(_args):
    path = os.path.join(top(), ".github", "workflows", "regression.yml")
    if os.path.exists(path):
        with open(path) as handle:
            if not handle.read().startswith("# Written by workflow-regression"):
                sys.exit("REFUSED: %s exists, and this tool didn't write it. Fix: merge by hand." % path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as handle:
        handle.write(WORKFLOW)
    print("WROTE " + path)
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command_name", required=True)
    sub.add_parser("seed").set_defaults(func=cmd_seed)
    item = sub.add_parser("add")
    item.add_argument("id")
    item.add_argument("--level", choices=LEVELS, default="nightly")
    item.add_argument("--command", required=True)
    item.add_argument("--goal", default="")
    item.set_defaults(func=cmd_add)
    item = sub.add_parser("sync")
    item.add_argument("--write", action="store_true")
    item.set_defaults(func=cmd_sync)
    item = sub.add_parser("red")
    item.add_argument("id")
    item.add_argument("--break", dest="break_it", required=True)
    item.add_argument("--timeout", type=int, default=900)
    item.set_defaults(func=cmd_red)
    item = sub.add_parser("run")
    item.add_argument("target", nargs="?", default="land")
    item.add_argument("--timeout", type=int, default=900)
    item.add_argument("--live", action="store_true")
    item.set_defaults(func=cmd_run)
    sub.add_parser("workflow").set_defaults(func=cmd_workflow)
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
