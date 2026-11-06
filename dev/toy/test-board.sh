#!/bin/bash
# Proves the operation board with fixtures. No model is called and no network is used. usage: test-board.sh [DIR]
set -u
here=$(cd "$(dirname "$0")/../.." && pwd)
T=${1:-$(mktemp -d)}; rm -rf "${T:?}"; mkdir -p "$T"
B="python3 $here/skills/workflow-monitoring/scripts/board.py"
W="python3 $here/skills/workflow-monitoring/scripts/watch.py"
export HOME="$T/home"; mkdir -p "$HOME"
fails=0
ok() { echo "PASS: $1"; }
bad() { echo "FAIL: $1"; fails=$((fails + 1)); }
has() { grep -qiF -- "$2" "$1" && ok "$3" || bad "$3"; }
"$here/dev/toy/make.sh" "$T" >/dev/null || exit 1
cd "$T/repo" || exit 1
python3 "$here/skills/workflow-setup/scripts/setup.py" >/dev/null
git switch -q main; git merge -q --ff-only workflow-setup
C=$(cd "$(git rev-parse --git-common-dir)" && pwd); R="$C/loop/runs"; mkdir -p "$R"
rec() { python3 - "$R/$1.json" "$@" <<'PY'
import json, sys
path, slug, status, level, step, updated, extra = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5], sys.argv[6], sys.argv[7:]
state = {"slug": slug, "goal": "Goal " + slug, "level": level, "status": status, "step": step, "tries": 1, "worktree": "/wt/" + slug,
         "touches": ["f_" + slug + ".py"], "pr": "", "checks": "", "judge": "", "updated": updated,
         "log": ["2026-01-01T08:00:00Z queued"]}
for item in extra:
    key, _, value = item.partition("=")
    state[key] = json.loads(value)
json.dump(state, open(path, "w"))
PY
}
rec old1 done standard pr 2026-01-01T09:00:00Z 'pr="https://x/pull/1"' 'checks="pass"'
rec old2 done standard release 2026-01-01T10:00:00Z 'pr="https://x/pull/2"'
rec runa running standard build 2026-01-01T11:50:00Z 'checks="pass"' 'note={"text":"<b>hi</b> building","at":"x"}'
rec waita waiting quick plan 2026-01-01T11:00:00Z 'waiting={"ask":"Cut <i>it</i>?","words":["cut waita","leave waita"]}'
rec failb failed minimum build 2026-01-01T11:00:00Z 'finding="boom <script>alert(1)</script>"'
rec ext1 running quick build 2026-01-01T11:00:00Z 'external=true' 'pid=999999'
cat >> .loop/queue.md <<'Q'
- slug: nextq | level: quick | touches: f_runa.py | goal: Next | done: Something
Q
AT=2026-01-01T12:00:00Z
O="$T/out"; mkdir -p "$O"
$B board --at $AT --out "$O" > "$T/b1"; $B board --at $AT --out "$T/out2" > "$T/b2"
sed "s#$T/out2#$O#" "$T/b2" | diff -q - "$T/b1" >/dev/null && cmp -s "$O/board.json" "$T/out2/board.json" && ok "same inputs, same output" || bad "determinism"
for k in DIGEST CHANGED NEXT_DELAY JSON HTML; do grep -q "^$k " "$T/b1" && ok "prints $k" || bad "prints $k"; done
has "$T/b1" "CHANGED yes" "first board has changes"
has "$T/b1" "CHANGE " "prints CHANGE lines"
$B board --at $AT --since "$O/board.json" --out "$T/out3" > "$T/b3"
has "$T/b3" "CHANGED no" "same state since the last board: CHANGED no"
rec runa running standard checks 2026-01-01T11:55:00Z 'checks="pass"' 'note={"text":"<b>hi</b> building","at":"x"}'
$B board --at $AT --since "$O/board.json" --out "$T/out3" > "$T/b4"
grep -q "^CHANGE .*runa step: build -> checks" "$T/b4" && ok "CHANGE line names the changed field" || bad "CHANGE line"
[ "$(grep -c '^CHANGE ' "$T/b4")" = 1 ] && ok "only the changed field is listed" || bad "changed field count: $(grep -c '^CHANGE ' "$T/b4")"
rec runa running standard build 2026-01-01T11:50:00Z 'checks="pass"' 'note={"text":"<b>hi</b> building","at":"x"}'
H="$O/board.html"
python3 - "$O/board.json" "$H" <<'PY' && ok "six sections in order, with content" || bad "sections"
import json, sys
d = json.load(open(sys.argv[1])); h = open(sys.argv[2]).read()
names = d["sections"]
assert names == ["Waiting on you", "Dependency map", "Runs", "Expected finish", "Finished today", "Every step"], names
pos = [h.index("<h2>" + n) for n in names]
assert pos == sorted(pos), pos
w = {x["slug"]: x for x in d["waiting"]}
assert w["waita"]["words"] == ["cut waita", "leave waita"] and "/wt/waita" in w["waita"]["where"]
assert "failb" in w and w["failb"]["words"] == ["resume failb"]
assert any(x["slug"] == "nextq" and "runa" in x["waits_on"] and "f_runa.py" in x["waits_on"] for x in d["dependencies"])
r = {x["slug"]: x for x in d["runs"]}
for k in ("goal", "level", "step", "elapsed", "tries", "pr", "checks", "status", "note"):
    assert k in r["runa"], k
assert r["runa"]["note"] == "<b>hi</b> building" and r["old1"]["pr"] == "https://x/pull/1"
e = {x["slug"]: x["estimate"] for x in d["expected"]}
assert e["runa"].startswith("estimate:"), e
f = d["finished"]
assert {x["slug"] for x in f["items"]} == {"old1", "old2"} and all(x["result"] == "delivered" for x in f["items"])
assert "archived" in f["note"] or "archive" in f["note"]
steps = [(s["slug"], s["step"], s["status"]) for s in d["steps"]]
assert ("runa", "design", "done") in steps and ("runa", "build", "running") in steps and ("runa", "pr", "pending") in steps
assert d["runs"][0].get("repo") and d["steps"][0].get("repo")
PY
python3 - "$H" <<'PY' && ok "html is self-contained, escaped, themed, phone-wide" || bad "html"
import sys
h = open(sys.argv[1]).read()
assert "<script" not in h and "http://" not in h and "https://" not in h.replace("https://x/pull", "")
assert "&lt;b&gt;hi&lt;/b&gt;" in h and "<b>hi</b>" not in h and "&lt;script&gt;alert" in h and "<i>it" not in h
assert "prefers-color-scheme:dark" in h and "name=viewport" in h and "max-width:600px" in h
assert h.index("Waiting on you") < h.index("<h2>Runs")
assert "(quiet)" in h
PY
python3 - "$O/board.json" <<'PY' && ok "no estimate without history of the same level" || bad "no-history estimate"
import json, sys
d = json.load(open(sys.argv[1]))
assert all(x["estimate"].startswith(("estimate:", "no estimate")) for x in d["expected"])
PY
python3 - "$O/board.json" <<'PY' && ok "quiet external goal shown quiet after 30 minutes; fresh one is not" || bad "quiet"
import json, sys
r = {x["slug"]: x for x in json.load(open(sys.argv[1]))["runs"]}
assert r["ext1"]["quiet"] == "yes" and r["runa"]["quiet"] == "no" and r["ext1"]["status"] == "running"
PY
$B board --at 2026-01-01T11:20:00Z --out "$T/out4" >/dev/null
python3 -c "import json,sys;r={x['slug']:x for x in json.load(open(sys.argv[1]))['runs']};assert r['ext1']['quiet']=='no'" "$T/out4/board.json" && ok "external not quiet inside 30 minutes" || bad "not quiet early"
nd() { $B board --at $AT --out "$T/out5" | grep '^NEXT_DELAY' | cut -d' ' -f2; }
[ "$($B cadence)" = "CADENCE 10" ] && ok "default cadence 10" || bad "default cadence"
[ "$(nd)" = 600 ] && ok "NEXT_DELAY is the cadence while goals run" || bad "delay 600: $(nd)"
$B cadence 1 >/dev/null; [ "$(nd)" = 60 ] && ok "cadence 1 gives 60" || bad "delay 60"
$B cadence 60 >/dev/null; [ "$(nd)" = 3600 ] && ok "cadence 60 gives 3600" || bad "delay 3600"
$B cadence 0 >/dev/null 2>&1 && bad "cadence 0 refused" || ok "cadence 0 refused"
$B cadence 61 >/dev/null 2>&1 && bad "cadence 61 refused" || ok "cadence 61 refused"
[ -f "$C/loop/cadence" ] && ok "cadence kept in the git common loop folder" || bad "cadence file"
$B cadence off >/dev/null; [ "$(nd)" = none ] && ok "NEXT_DELAY none after off" || bad "delay none"
$B cadence 5 >/dev/null
for s in runa waita failb ext1; do rm "${R:?}/$s.json"; done
[ "$(nd)" = 3600 ] && ok "NEXT_DELAY 3600 when nothing runs or waits" || bad "idle delay: $(nd)"
$B cadence 7 >/dev/null; [ "$($B cadence)" = "CADENCE 7" ] && ok "cadence is kept" || bad "cadence kept"
# several repos
cd "$T" && mkdir other && cd other && git init -q -b main && git config user.email a@b.c && git config user.name A && git commit -q --allow-empty -m i
mkdir -p .git/loop/runs
echo '{"slug":"othergoal","goal":"G","level":"quick","status":"running","step":"build","updated":"2026-01-01T11:59:00Z","log":["2026-01-01T11:00:00Z q"]}' > .git/loop/runs/othergoal.json
cd "$T/repo"
$B repos add "$T/other" | grep -q FOLLOWING && ok "repos add" || bad "repos add"
[ -f "$HOME/.workflow-loop/repos" ] && ok "repo list kept under the home folder" || bad "repo list file"
$B board --at $AT --out "$T/out6" >/dev/null
python3 -c "import json,sys;d=json.load(open(sys.argv[1]));r=[x for x in d['runs'] if x['slug']=='othergoal'];assert r and r[0]['repo']=='other' and 'other' in d['repos'] and 'repo' in d['repos']" "$T/out6/board.json" && ok "board reads every listed repo and names the repo" || bad "multi repo"
# note
$B note old1 'line one
<script>x</script>   line two' >/dev/null
$B board --at $AT --out "$T/out7" >/dev/null
python3 -c "import json,sys;r={x['slug']:x for x in json.load(open(sys.argv[1]))['runs']};assert r['old1']['note']=='line one <script>x</script> line two'" "$T/out7/board.json" && ok "note shows as last message, kept as data" || bad "note"
grep -q '<script>x' "$T/out7/board.html" && bad "note escaped" || ok "note escaped in html"
$B note nosuch hi >/dev/null 2>&1 && bad "note on unknown run refused" || ok "note on unknown run refused"
# a visible session goal
$W go "Visible session goal" --done "It works" --level quick --slug vis --session > "$T/go.out" 2>&1
grep -q '^WORKTREE ' "$T/go.out" && grep -q '^PROMPT ' "$T/go.out" && ok "go --session prints WORKTREE and PROMPT" || { bad "go --session output"; cat "$T/go.out"; }
tree=$(sed -n 's/^WORKTREE //p' "$T/go.out")
[ -f "$tree/.loop/goals/vis.md" ] && git -C "$tree" log --oneline | grep -q "Goal: vis" && ok "goal frozen in its worktree" || bad "frozen goal"
python3 -c "import json,sys;d=json.load(open(sys.argv[1]));assert d['external'] is True and d['status']=='running' and not d.get('pid')" "$R/vis.json" && ok "record marked external, no process started" || bad "external record"
$W watch --once > /dev/null 2>&1
[ "$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['status'])" "$R/vis.json")" = running ] && ok "a missing process never marks an external goal failed" || bad "external survived watch"
# handoff
$B handoff --at $AT > "$T/h.out"; hf=$(sed -n 's/^HANDOFF //p' "$T/h.out")
for k in "## Repos" "## Cadence" "## Open goals" "## Waiting on the owner" "## Next check-in steps" "other" "vis"; do has "$hf" "$k" "handoff has $k"; done
# repo checks
op="$here/skills/workflow-monitoring/references/operation.md"
for k in "watch.py watch --once" "latest report" "board.py board" "Artifact" "one chat line" "6 lines" "NEXT_DELAY" "Never answer a gate" "exact words" "information" "merge only when told" "never archive"; do has "$op" "$k" "operation.md: $k"; done
has "$here/skills/workflow-monitoring/SKILL.md" "references/operation.md" "SKILL.md links operation.md"
for f in "$here"/skills/*/scripts/*.py; do [ "$(wc -c < "$f")" -lt 20480 ] && ok "under 20 KB: $(basename "$f")" || bad "over 20 KB: $f"; done
for f in "$here"/skills/*/SKILL.md; do [ "$(wc -l < "$f")" -lt 150 ] && ok "under 150 lines: $(basename "$(dirname "$f")")" || bad "over 150 lines: $f"; done
for k in '"board"' '"cadence"' '"handoff"' '"note"' 'board.json' 'repos'; do has "$here/listing.json" "$k" "listing.json discloses $k"; done
echo; [ "$fails" = 0 ] && echo "ALL PASS" || { echo "$fails FAILED"; exit 1; }
