#!/bin/bash
here=$(cd "$(dirname "$0")/../.." && pwd)
. "$here/dev/toy/reap.sh"
# windows: ok
# reads: skills/workflow-health/scripts/issues.py
# The health commands read only the issues they need, a page of 100 at a time, so a repo with thousands of issues lists
# within the timeout: triage reads the open health issues in one filtered page, file reads the health issues and the open
# ones page by page, and a page that fails refuses with one line naming it. Python only, with gh stood in by a function,
# so it runs the same on Linux, macOS and Windows.
# Value: protects=triage --close and file work on a repo with over 3,000 open issues (the full listing took 30 s against a
#   20 s limit); fails_when=a command lists every issue in one call, a page holds more than 100, or a failed page gives no
#   line naming it; why_new=every other health toy has under 100 issues, so none pages; seam=none; no_claim=real gh speed
set -u
fails=0
ok() { echo "PASS: $1"; }
bad() { echo "FAIL: $1"; fails=$((fails + 1)); }
S="$here/skills/workflow-health/scripts"
out=$(python3 - "$S" <<'PY' 2>&1
import json, os, re, subprocess, sys, types
sys.path.insert(0, sys.argv[1])
import issues
OPEN, HEALTH_OPEN, HEALTH_CLOSED = 3200, 30, 5
ALL = []
for n in range(1, OPEN + 1):
    ALL.append({"number": n, "title": "issue %d" % n, "body": "", "state": "open", "labels": [], "created_at": "2026-01-01T00:00:00Z"})
for n in range(OPEN + 1, OPEN + HEALTH_OPEN + 1):
    ALL.append({"number": n, "title": "finding %d" % n, "body": "", "state": "open", "labels": [{"name": "health"}, {"name": "health:size"}], "created_at": "2026-01-01T00:00:00Z"})
for n in range(OPEN + HEALTH_OPEN + 1, OPEN + HEALTH_OPEN + HEALTH_CLOSED + 1):
    ALL.append({"number": n, "title": "old %d" % n, "body": "", "state": "closed", "labels": [{"name": "health"}], "created_at": "2026-01-01T00:00:00Z"})
calls, fail_page = [], [None]


def fake(args, **kw):
    assert args[:2] == ["gh", "api"] and "--paginate" not in args, args
    assert kw.get("timeout"), "every page needs its own time limit"
    query = dict(p.split("=") for p in args[2].split("?", 1)[1].split("&"))
    page, size = int(query["page"]), int(query["per_page"])
    calls.append((query.get("state"), query.get("labels"), page, size))
    if fail_page[0] == page and query["state"] == "open" and "labels" not in query:
        return types.SimpleNamespace(returncode=1, stdout="", stderr="HTTP 502 Bad Gateway\nmore text")
    rows = [i for i in ALL if query["state"] in ("all", i["state"]) and (query.get("labels") is None or query["labels"] in [l["name"] for l in i["labels"]])]
    return types.SimpleNamespace(returncode=0, stdout=json.dumps(rows[(page - 1) * size: page * size]), stderr="")


issues.subprocess = types.SimpleNamespace(run=fake, SubprocessError=subprocess.SubprocessError)
found, why = issues.fetch("r1", "health")
print("health", len(found), len(calls), calls[0] == ("open", "health", 1, 100))
calls.clear()
found, why = issues.fetch("r2", "open")
print("open", len(found), len(calls), [c[2] for c in calls] == list(range(1, 34)), max(c[3] for c in calls))
calls.clear()
found, why = issues.fetch("r3", "held")
print("held", len(found), sum(1 for c in calls if c[1] == "health"), len(calls))
fail_page[0] = 2
found, why = issues.fetch("r4", "open")
print("fail", found is None, "page 2" in why, "\n" not in why, why.startswith("gh not available here"))
import io, contextlib
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    rc = issues.close("r5", "size", "fixed", yes=False)
fail_page[0] = None
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    rc = issues.close("r6", "size", "fixed by 3776", yes=False, most=50)
print("triage", rc, "DRY RUN: 30 would close" in buf.getvalue())
for name in ("issues.py",):
    size = len(open(os.path.join(sys.argv[1], name), "rb").read().replace(b"\r\n", b"\n"))
    print(name, size < 18432, size)
PY
)
echo "$out" | grep -qx "health 30 1 True" && ok "triage reads the open health issues from one filtered page" || bad "health: $out"
echo "$out" | grep -qx "open 3230 33 True 100" && ok "the open issues are read as 33 pages of at most 100, in order" || bad "open: $out"
echo "$out" | grep -qx "held 3235 1 34" && ok "file's listing adds the health issues of every state to the open ones, still paged" || bad "held: $out"
echo "$out" | grep -qx "fail True True True True" && ok "a failed page refuses with one line naming the page" || bad "fail: $out"
echo "$out" | grep -qx "triage 0 True" && ok "triage --close previews 30 findings on a repo with over 3,000 open issues" || bad "triage: $out"
echo "$out" | grep -q "^issues.py True " && ok "issues.py is under 90% of the 20,480-byte cap" || bad "size: $out"
[ "$fails" = 0 ] && echo "ALL PASS" || { echo "FAILED $fails"; exit 1; }
