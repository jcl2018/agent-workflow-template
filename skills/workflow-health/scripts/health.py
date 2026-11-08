#!/usr/bin/env python3
"""Check a repo's health with fixed rules. Same repo, same answer. Read-only: it writes no file and calls no model.

usage: health.py check [--json] [--family NAME]
       health.py run [--live] [--family NAME]
       health.py suggest

check prints a fixed template: HEALTH REPORT, each group (size, criteria, docs, hygiene, Mine) with its lines, then the
verdict. Mine runs the owner's own rules from ~/.workflow-loop/health.json (see mine.py); one that cannot run is UNREAD.
suggest is a separate, advisory step (see suggest.py); the rule check stays model-free and gives the same answer twice.

One line per finding:  STATE family subject rule: detail -> fix: what to run
STATE is PASS, WARN, FAIL, UNREAD (a rule could not read its data) or INFO. The last line is
  HEALTH: green (...)  or  HEALTH: not green (...)
Only FAIL and UNREAD turn it red, and the exit code is then 1. --json prints the same rows as records.

Rules (at most MAX_RULES, asserted when the script loads; retire one before adding another):
  size      scripts under skills/*/scripts against 20 KB: WARN from 90%, FAIL over
  criteria  composes regression.py sync: a criterion with no row FAILs, a draft or never-failed row FAILs,
            done lines with no row WARN as one row; a closed issue or finding with no defect test FAILs (defects.py)
  docs      composes docs.py check: a stale page WARNs, any other gap FAILs
  hygiene   open findings over 5, runs waiting over 24 hours, merged loop branches nobody has checked out

run  files each WARN, FAIL or UNREAD row as one issue on the Backlog milestone, labelled health, found again by a
hidden marker in its body: a repeat updates it, a fixed finding closes it, a returning one reopens it, and a moved
issue stays where it was moved. With no --live, GH_TOKEN or GITHUB_TOKEN it prints WOULD lines and writes nothing.
It runs git, gh and the two sibling scripts, and nothing else.
"""
import argparse
import datetime
import glob
import json
import os
import re
import subprocess
import sys

# No terminal, no waiting: a prompt from git or gh must fail, not block.
os.environ.update(GIT_TERMINAL_PROMPT="0", GH_PROMPT_DISABLED="1", GIT_EDITOR="true", GIT_ASKPASS="true", SSH_ASKPASS="true")
if not sys.stdin or not sys.stdin.isatty():
    os.dup2(os.open(os.devnull, os.O_RDONLY), 0)

LIMIT = 20 * 1024
WARN_AT = LIMIT * 9 // 10
FINDINGS_WARN = 5
WAITING_HOURS = 24
RULES = ("size", "criteria-rows", "criteria-done", "defect-tests", "docs-check", "findings", "waiting", "branches")
MAX_RULES = 8
assert len(RULES) <= MAX_RULES, "too many rules: retire one first"
FAMILY = {"size": "size", "criteria": "criteria", "docs": "docs", "hygiene": "hygiene", "mine": "mine"}
ORDER = ("size", "criteria", "docs", "hygiene", "mine")  # the fixed order of the groups in the report
HERE = os.path.dirname(os.path.abspath(sys.argv[0]))


def run(args, cwd):
    try:
        return subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.SubprocessError) as error:
        return subprocess.CompletedProcess(args, 127, "", str(error))


def row(state, family, subject, rule, detail, fix=""):
    return {"state": state, "family": family, "subject": subject, "rule": rule, "detail": detail, "fix": fix}


def sibling(skill, script):
    path = os.path.join(HERE, "..", "..", skill, "scripts", script)
    return path if os.path.exists(path) else ""


def size_rows(root):
    rows, good = [], 0
    for path in sorted(glob.glob(os.path.join(root, "skills", "*", "scripts", "*.*"))):
        if not path.endswith((".py", ".sh")):
            continue
        size, name = os.path.getsize(path), os.path.relpath(path, root)
        if size > LIMIT:
            rows.append(row("FAIL", "size", name, "limit", "%d bytes, over %d" % (size, LIMIT), "split it into modules"))
        elif size >= WARN_AT:
            rows.append(row("WARN", "size", name, "limit", "%d bytes, %d%% of %d" % (size, size * 100 // LIMIT, LIMIT),
                            "trim or split before it passes the limit"))
        else:
            good += 1
    if not rows:
        rows.append(row("PASS", "size", "scripts", "limit", "%d scripts under %d bytes" % (good, WARN_AT)))
    return rows


def criteria_rows(root):
    script = sibling("workflow-regression", "regression.py")
    if not script:
        return [row("UNREAD", "criteria", "regression", "sync", "regression.py is not installed beside this skill")]
    done = run([sys.executable, script, "sync"], root)
    lines = done.stdout.splitlines()
    if not lines and done.returncode:
        return [row("UNREAD", "criteria", "regression", "sync", (done.stderr.strip() or "no output")[:120])]
    rows, loose = [], 0
    for line in lines:
        gap = re.match(r"^GAP (\S+) (.*)$", line)
        if gap and re.match(r"^[A-Za-z0-9-]+:\d+$", gap.group(1)):
            loose += 1
        elif gap and "criterion has no regression row" in gap.group(2):
            rows.append(row("FAIL", "criteria", gap.group(1), "rows", "criterion has no regression row",
                            "add a row with regression.py add"))
        elif line.startswith(("DRAFT ", "UNPROVEN ")):
            word, key = line.split()[:2]
            rows.append(row("FAIL", "criteria", key.rstrip(":"), "proof", "a draft row, or one never seen failing"
                            if word == "DRAFT" else "never seen failing", "run regression.py red"))
    if loose:
        rows.append(row("WARN", "criteria", "done-lines", "rows", "%d done lines have no regression row" % loose,
                        "regression.py sync --write drafts rows"))
    if not rows and not any(line.startswith("SYNC OK") for line in lines):
        return [row("UNREAD", "criteria", "regression", "sync", (done.stderr.strip() or "no SYNC OK line")[:120])]
    return rows or [row("PASS", "criteria", "rows", "sync", "every criterion and done line has a proven row")]


def docs_rows(root):
    script = sibling("workflow-docs", "docs.py")
    if not script:
        return [row("UNREAD", "docs", "docs", "check", "docs.py is not installed beside this skill")]
    done = run([sys.executable, script, "check"], root)
    lines = [line for line in done.stdout.splitlines() if line.strip()]
    if lines and lines[0].startswith("NO PAGES"):
        return [row("UNREAD", "docs", "wiki", "check", "no pages mapped", "run docs.py add")]
    if lines and lines[0].startswith("DOCS OK"):
        return [row("PASS", "docs", "wiki", "check", lines[0].lower())]
    if not lines:
        return [row("UNREAD", "docs", "docs", "check", (done.stderr.strip() or "no output")[:120])]
    rows = []
    for line in lines:
        kind, _, rest = line.partition(" ")
        page, _, detail = rest.partition(": ")
        rows.append(row("WARN" if kind == "STALE" else "FAIL", "docs", page, kind.lower(), detail[:120],
                        "update the page with workflow-docs"))
    return rows


def defect_rows(root):
    sys.path.insert(0, HERE)
    try:
        import defects
    except ImportError:
        return [row("UNREAD", "criteria", "defects", "defect-tests", "defects.py is not installed beside health.py")]
    finally:
        sys.path.pop(0)
    return [row("FAIL", "criteria", ref, "defect-tests", "closed by %s with no defect test" % source,
                "regression.py add --category defect --link ...") for ref, source in defects.missing(root)]


def hours_old(stamp):
    try:
        when = datetime.datetime.strptime(stamp, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)
    except (TypeError, ValueError):
        return 0
    return (datetime.datetime.now(datetime.timezone.utc) - when).total_seconds() / 3600


def hygiene_rows(root):
    rows = []
    try:
        with open(os.path.join(root, ".loop", "findings.md")) as handle:
            open_findings = [line for line in handle if line.startswith("- ")]
    except OSError:
        open_findings = []
    if len(open_findings) > FINDINGS_WARN:
        rows.append(row("WARN", "hygiene", "findings", "open", "%d open findings, over %d" % (len(open_findings), FINDINGS_WARN),
                        "resolve or remove them in .loop/findings.md"))
    common = run(["git", "rev-parse", "--git-common-dir"], root).stdout.strip()
    common = os.path.abspath(os.path.join(root, common))
    for path in sorted(glob.glob(os.path.join(common, "loop", "runs", "*.json"))):
        try:
            with open(path) as handle:
                state = json.load(handle)
        except (OSError, ValueError):
            rows.append(row("UNREAD", "hygiene", os.path.basename(path)[:-5], "run", "run record cannot be read"))
            continue
        if isinstance(state, dict) and state.get("status") == "waiting" and hours_old(state.get("updated")) > WAITING_HOURS:
            rows.append(row("WARN", "hygiene", state.get("slug") or os.path.basename(path)[:-5], "waiting",
                            "waiting over %d hours" % WAITING_HOURS, "answer it or retire it on the board"))
    base = "origin/main" if run(["git", "rev-parse", "--verify", "--quiet", "origin/main"], root).returncode == 0 else "main"
    merged = run(["git", "branch", "--merged", base], root)
    if merged.returncode:
        rows.append(row("UNREAD", "hygiene", "branches", "merged", (merged.stderr.strip() or "git branch failed")[:120]))
    else:
        for line in sorted(merged.stdout.splitlines()):
            name = line[2:].strip()
            if line.startswith("  ") and name.startswith("loop/"):
                rows.append(row("WARN", "hygiene", name, "branch", "already merged into %s" % base,
                                "git branch -d %s" % name))
    return rows or [row("PASS", "hygiene", "repo", "clean", "no stale findings, runs or merged branches")]


def line_of(item):
    text = "%s %s %s %s: %s" % (item["state"], item["family"], item["subject"], item["rule"], item["detail"])
    return text + (" -> fix: " + item["fix"] if item["fix"] else "")


def mine_rows(root):
    sys.path.insert(0, HERE)
    try:
        import mine
    except ImportError:
        return [row("UNREAD", "mine", "mine.py", "mine", "mine.py is not installed beside health.py")]
    finally:
        sys.path.pop(0)
    return mine.mine_rows(root)


def gather(root, family):
    rules = {"size": size_rows, "criteria": lambda root: criteria_rows(root) + defect_rows(root), "docs": docs_rows, "hygiene": hygiene_rows, "mine": mine_rows}
    rows = []
    for name in (family and [family] or ORDER):
        rows += rules[name](root)
    return rows


def report(rows):
    """The fixed template: a title, each group with its lines (state, subject, detail, fix), one verdict line."""
    counts = {state: sum(1 for item in rows if item["state"] == state) for state in ("PASS", "WARN", "FAIL", "UNREAD")}
    green = not counts["FAIL"] and not counts["UNREAD"]
    verdict = "HEALTH: %s (%d pass, %d warn, %d fail, %d unread)" % (
        "green" if green else "not green", counts["PASS"], counts["WARN"], counts["FAIL"], counts["UNREAD"])
    out = ["HEALTH REPORT"]
    for name in ORDER:
        group = [item for item in rows if item["family"] == name]
        if group:
            out.append("== %s ==" % ("Mine" if name == "mine" else name))
            out += [line_of(item) for item in group]
    return out + [verdict], counts, green, verdict


def repo_root():
    top = run(["git", "rev-parse", "--show-toplevel"], os.getcwd())
    if top.returncode:
        sys.exit("REFUSED: not inside a git repo.")
    return top.stdout.strip()


def cmd_check(args):
    root = repo_root()
    rows = gather(root, args.family)
    text, counts, green, verdict = report(rows)
    if args.json:
        print(json.dumps({"green": green, "counts": counts, "rows": rows, "verdict": verdict}, indent=2))
    else:
        print("\n".join(text))
    return 0 if green else 1


def cmd_suggest(args):
    """Advisory only: reads the same rows as check, never changes the verdict or the exit code."""
    root = repo_root()
    sys.path.insert(0, HERE)
    try:
        import suggest
    except ImportError:
        sys.exit("REFUSED: suggest.py is not installed beside health.py.")
    finally:
        sys.path.pop(0)
    lines, steps = suggest.suggestions(root, gather(root, None))
    print("SUGGESTIONS (advisory, not findings: they do not change the verdict)")
    print("== criteria ==")
    print("\n".join(lines) or "none")
    print("== next steps ==")
    print("\n".join(steps) or "none")
    return 0


MARK = "<!-- loop-health %s -->"
BACKLOG = "Backlog"


def key_of(item):
    return "%s:%s:%s" % (item["family"], item["subject"], item["rule"])


def body_of(item):
    return "%s\n\n%s\n\n%s\n" % (MARK % key_of(item), line_of(item),
                                    "Filed by health.py run. Move it to a feature with milestone.py move.")


def cmd_run(args):
    root = repo_root()
    live = bool(args.live or os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN"))
    rows = gather(root, args.family)
    found = [item for item in rows if item["state"] in ("WARN", "FAIL", "UNREAD") and item["family"] != "mine"]
    got = run(["gh", "issue", "list", "--label", "health", "--state", "all", "--limit", "500", "--json",
               "number,state,body"], root)
    try:
        issues = json.loads(got.stdout)
    except ValueError:
        issues = None
    if issues is None:
        if live:
            sys.exit("REFUSED: could not read the health issues: %s" % (got.stderr.strip() or "no answer")[:200])
        print("NOTE: could not read the health issues, so every finding looks new")
        issues = []
    held = {}
    for issue in sorted(issues, key=lambda one: one["number"]):
        match = re.search(r"<!-- loop-health (\S+) -->", issue.get("body") or "")
        if match:
            held.setdefault(match.group(1), issue)

    def act(words, args_, number=0):
        if live:
            done = run(["gh"] + args_, root)
            if done.returncode:
                print("FAILED %s: %s" % (words, done.stderr.strip()[:160]))
                return
            print("DONE %s" % words)
        else:
            print("WOULD %s" % words)

    if live and found:
        run(["gh", "label", "create", "health", "--description", "Filed by health.py run", "--force"], root)
    current = set()
    for item in found:
        key = key_of(item)
        current.add(key)
        title, body, issue = "health: %s %s %s" % (item["family"], item["subject"], item["rule"]), body_of(item), held.get(key)
        if not issue:
            act("create issue %r on %s" % (title, BACKLOG), ["issue", "create", "--title", title, "--body", body,
                                                           "--label", "health", "--milestone", BACKLOG])
            continue
        number = str(issue["number"])
        if issue["state"].upper() != "OPEN":
            act("reopen #%s %s" % (number, key), ["issue", "reopen", number])
        if (issue.get("body") or "") != body:
            act("update #%s %s" % (number, key), ["issue", "edit", number, "--body", body])
        elif issue["state"].upper() == "OPEN":
            print("SAME #%s %s" % (number, key))
    unread = {item["family"] for item in rows if item["state"] == "UNREAD"}
    ran = {item["family"] for item in rows} - unread  # an issue closes only when its rule ran and read its data
    for key, issue in sorted(held.items()):
        if key not in current and key.split(":")[0] in ran and issue["state"].upper() == "OPEN":
            number = str(issue["number"])
            act("close #%s %s, no longer found" % (number, key),
                ["issue", "close", number, "--comment", "No longer found by health.py run."])
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    item = sub.add_parser("check", help="run the fixed rules")
    item.add_argument("--json", action="store_true")
    item.add_argument("--family", choices=sorted(FAMILY))
    item.set_defaults(func=cmd_check)
    item = sub.add_parser("suggest", help="advisory suggestions, apart from the check")
    item.set_defaults(func=cmd_suggest)
    item = sub.add_parser("run", help="file findings as issues on the Backlog milestone")
    item.add_argument("--live", action="store_true")
    item.add_argument("--family", choices=sorted(FAMILY))
    item.set_defaults(func=cmd_run)
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
