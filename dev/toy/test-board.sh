#!/bin/bash
# reads: skills/workflow-monitoring/SKILL.md skills/workflow-monitoring/references/operation.md
# reads: skills/workflow-monitoring/scripts/board.py skills/workflow-monitoring/scripts/board_page.py
# reads: skills/workflow-monitoring/scripts/watch.py skills/workflow-setup/scripts/setup.py
# reads: skills/workflow-monitoring/scripts/
# Proves the operation board with fixtures. No model is called and no network is used. usage: test-board.sh [DIR]
set -u
unset LOOP_SESSION_TOOL LOOP_OPERATION_SESSION  # a toy test never reaches a real session tool
unset LOOP_ROLE  # these tests act as the operation session
here=$(cd "$(dirname "$0")/../.." && pwd)
T=${1:-$(mktemp -d)}; rm -rf "${T:?}"; mkdir -p "$T"
B="python3 $here/skills/workflow-monitoring/scripts/board.py"
W="python3 $here/skills/workflow-monitoring/scripts/watch.py"
P="python3 $here/skills/workflow-monitoring/scripts/board_page.py"
export HOME="$T/home"; mkdir -p "$HOME"
fails=0
ok() { echo "PASS: $1"; }
bad() { echo "FAIL: $1"; fails=$((fails + 1)); }
has() { grep -qiF -- "$2" "$1" && ok "$3" || bad "$3"; }
"$here/dev/toy/make.sh" "$T" >/dev/null || exit 1
export LOOP_FLOW="$T/flow.json"
cd "$T/repo" || exit 1
# a fake gh: pull/1 merged, pull/2 closed, pull/3 open, anything else cannot be answered
mkdir -p "$T/bin"
cat > "$T/bin/gh" <<'GH'
#!/bin/bash
case "$*" in
  api*milestones*) [ -n "${NO_MILESTONES:-}" ] && exit 1; echo '[{"title":"Backlog","open_issues":2,"closed_issues":1},{"title":"Health","open_issues":0,"closed_issues":3}]';;
  "issue list"*) echo '[{"createdAt":"2025-12-25T00:00:00Z"},{"createdAt":"2025-12-30T00:00:00Z"}]';;
  *pull/1*) echo MERGED;; *pull/2*) echo CLOSED;; *pull/3*) echo OPEN;; *) echo "gh: no answer" >&2; exit 1;;
esac
GH
chmod +x "$T/bin/gh"; export PATH="$T/bin:$PATH"
python3 "$here/skills/workflow-setup/scripts/setup.py" --bare >/dev/null
git switch -q main; git merge -q --ff-only workflow-setup
# A stand-in agent, so the test needs no agent on this machine and never starts a real one.
python3 -c "import json;c=json.load(open('.loop/config.json'));c['agent_command']=['true'];json.dump(c,open('.loop/config.json','w'),indent=2)"
git commit -qam "Stand-in agent"
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
rec old1 done 1 pr 2026-01-01T09:00:00Z 'pr="https://x/pull/1"' 'checks="pass"'
rec old2 done 1 release 2026-01-01T10:00:00Z 'pr="https://x/pull/2"'
rec runa running 1 build 2026-01-01T11:50:00Z 'checks="pass"' 'note={"text":"<b>hi</b> building","at":"x"}'
rec waita waiting 0 plan 2026-01-01T11:00:00Z 'waiting={"ask":"Cut <i>it</i>?","words":["cut waita","leave waita"]}'
rec propen running 1 pr 2026-01-01T11:55:00Z 'pr="https://x/pull/3"'
rec prlost running 1 pr 2026-01-01T11:55:00Z 'pr="https://x/pull/9"'
rec failb failed 0 build 2026-01-01T11:00:00Z 'finding="boom <script>alert(1)</script>"'
rec ext1 running 0 build 2026-01-01T11:00:00Z
cat >> .loop/queue.md <<'Q'
- slug: nextq | level: 0 | touches: f_runa.py | depends-on: runa | goal: Next | done: Something
Q
AT=2026-01-01T12:00:00Z
O="$T/out"; mkdir -p "$O"
$B board --at $AT --out "$O" > "$T/b1"; $B board --at $AT --out "$T/out2" > "$T/b2"
$P --in "$O/board.json" >> "$T/b1"; $P --in "$T/out2/board.json" >> "$T/b2"
sed "s#$T/out2#$O#" "$T/b2" | diff -q - "$T/b1" >/dev/null && cmp -s "$O/board.json" "$T/out2/board.json" && ok "same inputs, same output" || bad "determinism"
for k in DIGEST CHANGED NEXT_DELAY JSON HTML ARTIFACT; do grep -q "^$k " "$T/b1" && ok "prints $k" || bad "prints $k"; done
has "$T/b1" "CHANGED yes" "first board has changes"
has "$T/b1" "CHANGE " "prints CHANGE lines"
$B board --at $AT --since "$O/board.json" --out "$T/out3" > "$T/b3"
has "$T/b3" "CHANGED no" "same state since the last board: CHANGED no"
rec runa running 1 review 2026-01-01T11:55:00Z 'checks="pass"' 'note={"text":"<b>hi</b> building","at":"x"}'
$B board --at $AT --since "$O/board.json" --out "$T/out3" > "$T/b4"
grep -q "^CHANGE .*runa step: build -> review" "$T/b4" && ok "CHANGE line names the changed field" || bad "CHANGE line"
[ "$(grep -c '^CHANGE ' "$T/b4")" = 1 ] && ok "only the changed field is listed" || bad "changed field count: $(grep -c '^CHANGE ' "$T/b4")"
rec runa running 1 build 2026-01-01T11:50:00Z 'checks="pass"' 'note={"text":"<b>hi</b> building","at":"x"}'
H="$O/board.html"
python3 - "$O/board.json" <<'PY' && ok "board.json holds waiting, dependencies and runs" || bad "board data"
import json, sys
d = json.load(open(sys.argv[1]))
assert "sections" not in d and "milestones" not in d and "dependency_map" not in d, sorted(d)
w = {x["slug"]: x for x in d["waiting"]}
assert w["waita"]["words"] == ["cut waita", "leave waita"] and w["waita"]["where"] == "the operation session, which owns repo/waita" and "/wt/" not in w["waita"]["where"]
assert "failb" in w and w["failb"]["words"] == ["resume failb"]
assert any(x["slug"] == "nextq" and "goal runa (running)" in x["waits_on"] and x["on"] == "runa" for x in d["dependencies"])
r = {x["slug"]: x for x in d["runs"]}
for k in ("goal", "level", "step", "elapsed", "tries", "pr", "checks", "status", "note"):
    assert k in r["runa"], k
assert r["runa"]["note"] == "<b>hi</b> building" and r["old1"]["pr"] == "https://x/pull/1"
PY
$P --in "$O/board.json" >/dev/null
python3 - "$H" "$O/board-artifact.html" <<'PY' && ok "the page shows the live board, escaped, themed, phone-wide, with no tags on the artifact page" || bad "html"
import re, sys
h, art = open(sys.argv[1]).read(), open(sys.argv[2]).read()
for page in (h, art):
    assert "<script" not in page and "http://" not in page
    assert "<pre>LIVE BOARD" in page and "Issues" in page and "Running goals" in page and "Finish" in page
    assert "prefers-color-scheme:dark" in page and ":root:not([data-theme=light])" in page and ":root[data-theme=dark]" in page
assert "name=viewport" in h
assert art.startswith("<title>Operation board</title><style>")
assert not re.search(r"<(!doctype|html|head|body)\b|</(html|head|body)>", art, re.I)
assert "Milestone" not in h and "<table" not in h
PY

python3 - "$O/board.json" "$H" <<'PY' && ok "pull request states: open, merged, closed, and unknown when gh cannot answer" || bad "pr states"
import json, sys
d = json.load(open(sys.argv[1])); h = open(sys.argv[2]).read()
r = {x["slug"]: x["prstate"] for x in d["runs"]}
assert r["old1"] == "merged" and r["old2"] == "closed" and r["propen"] == "open" and r["prlost"] == "unknown" and r["runa"] == "", r
PY
PATH=/usr/bin:/bin $B board --at $AT --out "$T/out8" >/dev/null
python3 -c "import json,sys;d=json.load(open(sys.argv[1]));assert {x['prstate'] for x in d['runs'] if x['pr']}=={'unknown'}" "$T/out8/board.json" && ok "no gh at all shows unknown" || bad "no gh"
python3 - "$O/board.json" <<'PY' && ok "quiet goal with no pid shown quiet after 30 minutes; fresh one is not" || bad "quiet"
import json, sys
r = {x["slug"]: x for x in json.load(open(sys.argv[1]))["runs"]}
assert r["ext1"]["quiet"] == "yes" and r["runa"]["quiet"] == "no" and r["ext1"]["status"] == "running"
PY
$B board --at 2026-01-01T11:20:00Z --out "$T/out4" >/dev/null
python3 -c "import json,sys;r={x['slug']:x for x in json.load(open(sys.argv[1]))['runs']};assert r['ext1']['quiet']=='no'" "$T/out4/board.json" && ok "a goal with no pid is not quiet inside 30 minutes" || bad "not quiet early"
nd() { $B board --at $AT --out "$T/out5" | grep '^NEXT_DELAY' | cut -d' ' -f2; }
[ "$($B cadence)" = "CADENCE 30" ] && ok "default cadence 30" || bad "default cadence"
[ "$(nd)" = 1800 ] && ok "NEXT_DELAY is the cadence while goals run" || bad "delay 1800: $(nd)"
$B cadence 1 >/dev/null; [ "$(nd)" = 60 ] && ok "cadence 1 gives 60" || bad "delay 60"
$B cadence 60 >/dev/null; [ "$(nd)" = 3600 ] && ok "cadence 60 gives 3600" || bad "delay 3600"
$B cadence 0 >/dev/null 2>&1 && bad "cadence 0 refused" || ok "cadence 0 refused"
$B cadence 61 >/dev/null 2>&1 && bad "cadence 61 refused" || ok "cadence 61 refused"
[ -f "$C/loop/cadence" ] && ok "cadence kept in the git common loop folder" || bad "cadence file"
$B cadence off >/dev/null; [ "$(nd)" = none ] && ok "NEXT_DELAY none after off" || bad "delay none"
$B cadence 5 >/dev/null
for s in runa waita failb ext1 propen prlost; do rm "${R:?}/$s.json"; done
[ "$(nd)" = 3600 ] && ok "NEXT_DELAY 3600 when nothing runs or waits" || bad "idle delay: $(nd)"
$B cadence 7 >/dev/null; [ "$($B cadence)" = "CADENCE 7" ] && ok "cadence is kept" || bad "cadence kept"
# several repos
cd "$T" && mkdir other && cd other && git init -q -b main && git config user.email a@b.c && git config user.name A && git commit -q --allow-empty -m i
mkdir -p .git/loop/runs
echo '{"slug":"othergoal","goal":"G","level": "0","status":"running","step":"build","updated":"2026-01-01T11:59:00Z","log":["2026-01-01T11:00:00Z q"]}' > .git/loop/runs/othergoal.json
cd "$T/repo"
$B repos add "$T/other" | grep -q FOLLOWING && ok "repos add" || bad "repos add"
[ -f "$HOME/.workflow-loop/repos" ] && ok "repo list kept under the home folder" || bad "repo list file"
$B board --at $AT --out "$T/out6" >/dev/null
python3 -c "import json,sys;d=json.load(open(sys.argv[1]));r=[x for x in d['runs'] if x['slug']=='othergoal'];assert r and r[0]['repo']=='other' and 'other' in d['repos'] and 'repo' in d['repos']" "$T/out6/board.json" && ok "board reads every listed repo and names the repo" || bad "multi repo"
# note
$B note old1 'line one
<script>x</script>   line two' >/dev/null
$B board --at $AT --out "$T/out7" >/dev/null; $P --in "$T/out7/board.json" >/dev/null
python3 -c "import json,sys;r={x['slug']:x for x in json.load(open(sys.argv[1]))['runs']};assert r['old1']['note']=='line one <script>x</script> line two'" "$T/out7/board.json" && ok "note shows as last message, kept as data" || bad "note"
grep -q '<script>x' "$T/out7/board.html" && bad "note escaped" || ok "note escaped in html"
$B note nosuch hi >/dev/null 2>&1 && bad "note on unknown run refused" || ok "note on unknown run refused"
# handoff
rec waita waiting 0 plan 2026-01-01T11:00:00Z 'waiting={"ask":"Cut <i>it</i>?","words":["cut waita","leave waita"]}'
$B handoff --at $AT > "$T/h.out"; hf=$(sed -n 's/^HANDOFF //p' "$T/h.out")
python3 - "$hf" <<'PY' && ok "handoff Waiting on the owner holds the question, exact words and where to type" || bad "handoff waiting line"
import sys
t = open(sys.argv[1]).read()
sec = t.split("## Waiting on the owner", 1)[1].split("\n## ", 1)[0]
line = [l for l in sec.splitlines() if "/waita:" in l]
assert line, sec
l = line[0]
assert "Cut <i>it</i>?" in l and "cut waita or leave waita" in l and "Type in the operation session, which owns repo/waita: " in l and "/wt/" not in l, l
PY
for k in "## Repos" "## Cadence" "## Open goals" "## Waiting on the owner" "## Next check-in steps" "other"; do has "$hf" "$k" "handoff has $k"; done
rm -f "$R"/*.json; : > "$HOME/.workflow-loop/repos"; git checkout -q -- .loop/queue.md
map() { rm -rf "$T/m"; $B board --at $AT --out "$T/m" >/dev/null; $P --in "$T/m/board.json" >/dev/null; }
# watch.py records what a goal depends on
cat > "$T/hold.sh" <<'A'
#!/bin/bash
while [ -e "$HOLD" ]; do sleep 0.1; done
A
cp .loop/config.json "$T/cfg.bak"
python3 - "$T/hold.sh" <<'PY'
import json, sys
c = json.load(open(".loop/config.json")); c["agent_command"] = ["bash", sys.argv[1]]; json.dump(c, open(".loop/config.json", "w"))
PY
git commit -qam "Hold agent"; export HOLD="$T/hold"; touch "$HOLD"
$W go "Holder" --done "x" --touches lib/ --slug holder >/dev/null
$W go "Held" --done "x" --touches lib/a.py --depends-on holder --slug held >/dev/null
[ ! -e "$R/held.json" ] && ok "the dependent goal is held until its dependency is merged" || bad "held goal started"
rm "$HOLD"
rec holder done 0 pr 2026-01-01T11:50:00Z 'touches=["lib/"]' 'release="merged"'
$W watch --once >/dev/null
python3 -c "import json,sys;assert json.load(open(sys.argv[1]))['waits_on']==['holder']" "$R/held.json" && ok "watch records waits_on on the run when the goal starts" || bad "waits_on not recorded"
git revert --no-edit HEAD >/dev/null; git checkout -q -- .loop/queue.md 2>/dev/null; rm -f "$R/holder.json" "$R/held.json"
# retire
rec stale failed 1 build 2026-01-01T11:00:00Z 'finding="old attempt"' 'touches=["z.py"]'
rec fresh running 1 build 2026-01-01T11:00:00Z 'pid=1'
map
python3 -c "import json,sys;assert 'stale' in [x['slug'] for x in json.load(open(sys.argv[1]))['waiting']]" "$T/m/board.json" && ok "before retire it waits on you" || bad "before retire"
$B retire stale 2>&1 | grep -q "required: --reason" && ok "retire needs a reason" || bad "retire reason"
$B retire nosuch --reason x 2>&1 | grep -q REFUSED && ok "retire of an unknown run refused" || bad "retire unknown"
$B retire fresh --reason x 2>&1 | grep -q "is running" && ok "retire refuses a running agent" || bad "retire running"
$B retire stale --reason "Superseded by goal fresh" | grep -q "RETIRED stale" && ok "retire" || bad "retire"
map
python3 - "$T/m/board.json" <<'PY' && ok "a retired goal leaves Issues and stays marked in Runs" || bad "retired"
import json, sys
d = json.load(open(sys.argv[1]))
assert "stale" not in [x["slug"] for x in d["waiting"]]
assert {x["slug"]: x for x in d["runs"]}["stale"]["status"] == "retired"
assert "1 retired" in d["digest"]
PY
$W resume stale 2>&1 | grep -q "REFUSED" && ok "resume refuses a retired goal" || bad "resume retired"
rm "$R/fresh.json" "$R/stale.json"
# CHANGED only on a real change
rec chg1 running 1 build 2026-01-01T11:50:00Z 'pr="https://x/pull/3"'
rm -rf "$T/c"; $B board --at $AT --out "$T/c" >/dev/null
python3 - "$T/c/board.json" <<'PY'
import json, sys
d = json.load(open(sys.argv[1]))
for item in d["state"].values():
    if not item.get("waits_on"):
        item.pop("waits_on", None)
json.dump(d, open(sys.argv[1], "w"))
PY
$B board --at $AT --since "$T/c/board.json" --out "$T/c2" > "$T/c.out"
grep -q "CHANGED no" "$T/c.out" && ! grep -q -- "- -> -" "$T/c.out" && ok "a field the old board lacks is no change" || bad "missing field counted as a change"
PATH=/usr/bin:/bin $B board --at $AT --since "$T/c2/board.json" --out "$T/c3" > "$T/c.out"
grep -q "CHANGED no" "$T/c.out" && ok "gh failing to answer is no change" || bad "unknown pull request state counted as a change"
$B board --at $AT --since "$T/c3/board.json" --out "$T/c4" > "$T/c.out"
grep -q "CHANGED no" "$T/c.out" && ok "and gh answering again is no change" || bad "pull request state flapped"
rec chg1 running 1 review 2026-01-01T11:50:00Z 'pr="https://x/pull/3"'
$B board --at $AT --since "$T/c4/board.json" --out "$T/c5" > "$T/c.out"
grep -q "^CHANGE repo/chg1 step: build -> review" "$T/c.out" && [ "$(grep -c '^CHANGE ' "$T/c.out")" = 1 ] && ok "a real change is still reported, alone" || bad "real change"
rm "$R/chg1.json"
# board_page.py alone draws a finished board.json
mkdir -p "$T/lone"; cp "$here/skills/workflow-monitoring/scripts/board_page.py" "$T/lone/"; $B board --at $AT --out "$T/c6" >/dev/null
python3 "$T/lone/board_page.py" --in "$T/c6/board.json" --out "$T/c7" | grep -q "^HTML " && ok "board_page.py alone draws the board header" || bad "page alone draws"
# a stalled session with no pid still shows
rec nopid running 0 build 2026-01-01T11:00:00Z
$B board --at $AT --out "$T/q" >/dev/null
python3 -c "import json,sys;r={x['slug']:x for x in json.load(open(sys.argv[1]))['runs']};assert r['nopid']['quiet']=='yes'" "$T/q/board.json" && ok "a quiet goal with no pid shows quiet" || bad "no pid quiet"
rm "$R/nopid.json"
# repo checks
op="$here/skills/workflow-monitoring/references/operation.md"
for k in "watch.py watch --once" "latest report" "board.py board" "board_page.py" "main project folder" "Artifact" "one chat line" "6 lines" "NEXT_DELAY" "Never answer a gate" "exact words" "information" "merge only when told" "never archive"; do has "$op" "$k" "operation.md: $k"; done
has "$here/skills/workflow-monitoring/SKILL.md" "references/operation.md" "SKILL.md links operation.md"
for f in watch board board_page; do [ "$(wc -c < "$here/skills/workflow-monitoring/scripts/$f.py")" -lt 19000 ] && ok "$f.py keeps room under 19 KB" || bad "$f.py has no room"; done
for k in '"board"' '"cadence"' '"handoff"' '"note"' '"retire"' 'board.json' 'repos'; do has "$here/listing.json" "$k" "listing.json discloses $k"; done
echo; [ "$fails" = 0 ] && echo "ALL PASS" || { echo "$fails FAILED"; exit 1; }
