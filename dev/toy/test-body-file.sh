#!/bin/bash
here=$(cd "$(dirname "$0")/../.." && pwd)
. "$here/dev/toy/reap.sh"
# windows: ok
# reads: skills/workflow-release/scripts/autorelease.py skills/workflow-health/scripts/rounds.py skills/workflow-health/scripts/file.py skills/workflow-regression/scripts/runs.py skills/workflow-regression/scripts/actions.py skills/workflow-regression/scripts/actions_summary.py
# Issue 2879: a long gh text (a pull request body, an issue body or comment, release notes) goes in a temp file and
# --body-file or --notes-file, never on the command line, which native Windows caps near 32,767 characters
# (goal.py pr crashed with WinError 206). Python only, so it runs the same on Linux, macOS and Windows.
# Value: protects=merge.py, release notes and the health and regression issue writes work with a body over 32,000
# characters on native Windows (issue 2879); fails_when=a gh call passes a body or notes text as an argument again;
# why_new=the other rows use a fake gh that reads a short --body; seam=none; no_claim=a real gh on Windows
set -u
S="$here/skills"
fails=0
ok() { echo "PASS: $1"; }
bad() { echo "FAIL: $1"; fails=$((fails + 1)); }
left=$(cd "$S" && grep -rn -e '"--body"' -e '"--notes"' --include=*.py .)
[ -z "$left" ] && ok "no gh call in skills/ passes a --body or --notes text as an argument" || bad "text arguments left: $left"
out=$(python3 - "$S" <<'PY' 2>&1
import os, subprocess, sys, tempfile
S = sys.argv[1]
for skill in ("workflow-delivery", "workflow-release", "workflow-health", "workflow-regression"):
    sys.path.insert(0, os.path.join(S, skill, "scripts"))
import actions, autorelease, rounds, runs
sys.modules.pop("file", None)
import importlib.util
spec = importlib.util.spec_from_file_location("health_file", os.path.join(S, "workflow-health", "scripts", "file.py"))
health_file = importlib.util.module_from_spec(spec); spec.loader.exec_module(health_file)

BODY = "line with ünïcode and `ticks`\n" * 1500  # over 40,000 characters
assert len(BODY) > 40000
seen = []
real_run = subprocess.run

def fake_run(args, *a, **k):
    args = list(args)
    flag = next((f for f in ("--body-file", "--notes-file") if f in args), None)
    assert flag, "no file flag in %r" % args[:6]
    path = args[args.index(flag) + 1]
    assert not any(len(x) > 2000 for x in args), "a long argument on the command line"
    assert len(" ".join(args)) < 4000, "command line too long"
    with open(path, encoding="utf-8", newline="") as handle:
        seen.append((path, handle.read()))
    return subprocess.CompletedProcess(args, 0, "https://example.test/pull/1\n", "")

subprocess.run = fake_run
try:
    rounds.gh("issue", "edit", "1", body=BODY)
    health_file.run(["issue", "create", "--title", "t"], os.getcwd(), BODY)
    runs.gh("issue", "comment", "1", body=BODY)
    autorelease.sh_text(["gh", "pr", "create", "--title", "t"], BODY)
    autorelease.sh_text(["gh", "release", "create", "v1"], BODY, "--notes-file")
    # the script the regression workflow runs, cut from actions.py with its gh() function
    text = open(os.path.join(S, "workflow-regression", "scripts", "actions.py"), encoding="utf-8").read().splitlines()
    start = next(i for i, line in enumerate(text) if line.strip().startswith("def gh(*args, body=None)"))
    indent = len(text[start]) - len(text[start].lstrip())
    end = next(i for i in range(start + 1, len(text)) if text[i].strip() and len(text[i]) - len(text[i].lstrip()) <= indent)
    block = "\n".join(line[indent:] for line in text[start:end])
    space = {"subprocess": subprocess, "os": os, "tempfile": tempfile}
    exec(block, space)
    space["gh"]("issue", "create", "--title", "t", body=BODY)
finally:
    subprocess.run = real_run
assert len(seen) == 6, len(seen)
assert all(body == BODY for _, body in seen), "a body changed on its way into the file"
assert not any(os.path.exists(path) for path, _ in seen), "a temp file was left behind"
print("CHECKED %d" % len(seen))
PY
)
echo "$out" | tail -1 | grep -qx "CHECKED 6" \
  && ok "pr create, issue create, edit and comment, and release notes carry a 40,000-character text in a temp file that is removed" \
  || bad "wrappers: $(echo "$out" | tail -4)"
[ "$fails" = 0 ] && echo "ALL PASS" || { echo "FAILED $fails"; exit 1; }
