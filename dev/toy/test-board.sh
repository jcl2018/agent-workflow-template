#!/bin/bash
# Proves the operation board with fixtures. No model is called and no network is used. usage: test-board.sh [DIR]
set -u
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
cd "$T/repo" || exit 1
# a fake gh: pull/1 merged, pull/2 closed, pull/3 open, anything else cannot be answered
mkdir -p "$T/bin"
cat > "$T/bin/gh" <<'GH'
#!/bin/bash
case "$*" in
  *pull/1*) echo MERGED;; *pull/2*) echo CLOSED;; *pull/3*) echo OPEN;; *) echo "gh: no answer" >&2; exit 1;;
esac
GH
chmod +x "$T/bin/gh"; export PATH="$T/bin:$PATH"
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
rec propen running standard pr 2026-01-01T11:55:00Z 'pr="https://x/pull/3"'
rec prlost running standard pr 2026-01-01T11:55:00Z 'pr="https://x/pull/9"'
rec failb failed minimum build 2026-01-01T11:00:00Z 'finding="boom <script>alert(1)</script>"'
rec ext1 running quick build 2026-01-01T11:00:00Z 'external=true' 'pid=999999'
cat >> .loop/queue.md <<'Q'
- slug: nextq | level: quick | touches: f_runa.py | goal: Next | done: Something
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
assert w["waita"]["words"] == ["cut waita", "leave waita"] and w["waita"]["where"] == "the governing session, which owns repo/waita" and "/wt/" not in w["waita"]["where"]
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
python3 - "$H" "$O/board-artifact.html" <<'PY' && ok "artifact page has no outer tags and both pages honor data-theme" || bad "artifact page"
import re, sys
full, art = open(sys.argv[1]).read(), open(sys.argv[2]).read()
assert art.startswith("<title>Operation board</title><style>")
assert not re.search(r"<(!doctype|html|head|body)\b|</(html|head|body)>", art, re.I)
assert "<script" not in art and "&lt;script&gt;alert" in art and "Waiting on you" in art
for page in (full, art):
    assert "prefers-color-scheme:dark" in page and ":root:not([data-theme=light])" in page and ":root[data-theme=dark]" in page
PY
python3 - "$O/board.json" "$H" <<'PY' && ok "pull request states: open, merged, closed, and unknown when gh cannot answer" || bad "pr states"
import json, sys
d = json.load(open(sys.argv[1])); h = open(sys.argv[2]).read()
r = {x["slug"]: x["prstate"] for x in d["runs"]}
assert r["old1"] == "merged" and r["old2"] == "closed" and r["propen"] == "open" and r["prlost"] == "unknown" and r["runa"] == "", r
assert {x["slug"]: x["prstate"] for x in d["finished"]["items"]} == {"old1": "merged", "old2": "closed"}
assert "https://x/pull/3 (open)" in h and "https://x/pull/9 (unknown)" in h and "https://x/pull/1 (merged)" in h
PY
PATH=/usr/bin:/bin $B board --at $AT --out "$T/out8" >/dev/null
python3 -c "import json,sys;d=json.load(open(sys.argv[1]));assert {x['prstate'] for x in d['runs'] if x['pr']}=={'unknown'}" "$T/out8/board.json" && ok "no gh at all shows unknown" || bad "no gh"
python3 - "$O/board.json" <<'PY' && ok "a level with no finished goals gets exactly no estimate" || bad "no-history estimate"
import json, sys
d = json.load(open(sys.argv[1]))
e = {x["slug"]: x["estimate"] for x in d["expected"]}
assert e["ext1"] == "no estimate: no finished quick goals yet", e
assert e["runa"].startswith("estimate:"), e
assert all(v.startswith("estimate:") or v.startswith("no estimate: no finished ") for v in e.values()), e
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
for s in runa waita failb ext1 propen prlost; do rm "${R:?}/$s.json"; done
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
$B board --at $AT --out "$T/out7" >/dev/null; $P --in "$T/out7/board.json" >/dev/null
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
rec waita waiting quick plan 2026-01-01T11:00:00Z 'waiting={"ask":"Cut <i>it</i>?","words":["cut waita","leave waita"]}'
$B handoff --at $AT > "$T/h.out"; hf=$(sed -n 's/^HANDOFF //p' "$T/h.out")
python3 - "$hf" <<'PY' && ok "handoff Waiting on the owner holds the question, exact words and where to type" || bad "handoff waiting line"
import sys
t = open(sys.argv[1]).read()
sec = t.split("## Waiting on the owner", 1)[1].split("\n## ", 1)[0]
line = [l for l in sec.splitlines() if "/waita:" in l]
assert line, sec
l = line[0]
assert "Cut <i>it</i>?" in l and "cut waita or leave waita" in l and "Type in the governing session, which owns repo/waita: " in l and "/wt/" not in l, l
PY
for k in "## Repos" "## Cadence" "## Open goals" "## Waiting on the owner" "## Next check-in steps" "other" "vis"; do has "$hf" "$k" "handoff has $k"; done
# the dependency map, drawn from fixtures
rm -f "$R"/*.json; : > "$HOME/.workflow-loop/repos"; git checkout -q -- .loop/queue.md
map() { rm -rf "$T/m"; $B board --at $AT --out "$T/m" >/dev/null; $P --in "$T/m/board.json" >/dev/null; }
rec first running quick build 2026-01-01T11:30:00Z 'touches=["pkg/"]'
rec donelong done quick pr 2026-01-01T09:30:00Z 'pr="https://x/pull/3"'
cat >> .loop/queue.md <<'Q'
- slug: shout | level: quick | touches: pkg/shout.py | goal: Shout | done: It shouts
Q
map
python3 - "$T/m/board.json" "$T/m/board.html" <<'PY' && ok "one lane a run, one box a step, solid inside a run, dashed across with its reason" || bad "lanes and arrows"
import json, re, sys
d = json.load(open(sys.argv[1]))["dependency_map"]; h = open(sys.argv[2]).read()
l = {x["run"]: x for x in d["lanes"]}
assert set(l) == {"repo/first", "repo/donelong", "repo/shout"}, set(l)
assert [b["step"] for b in l["repo/first"]["boxes"]] == ["plan", "build", "checks", "pr"]
assert [b["status"] for b in l["repo/first"]["boxes"]] == ["done", "running", "pending", "pending"]
assert [b["status"] for b in l["repo/shout"]["boxes"]] == ["queued"] * 4
cross = [a for a in d["arrows"] if a["on"]]
assert cross == [{"from": "repo/first:pr", "to": "repo/shout:plan", "on": "goal first, shared pkg/shout.py"}], cross
assert len([a for a in d["arrows"] if not a["on"]]) == 3 + 3 + 3 + 1  # donelong also has a release box
names = [x["run"] for x in d["lanes"]]
assert names.index("repo/first") < names.index("repo/shout")
assert h.count("<a class='box ") == sum(len(x["boxes"]) for x in d["lanes"])
assert h.count("<path class=wire ") == 1 and h.count("<path class=step ") == 10
assert "goal first, shared pkg/shout.py</text>" in h and "s-running" in h and "s-done" in h
assert re.search(r"<title>.*Done: .*\nNext: .*\nUnblocks: ", h, re.S)
PY
python3 - "$T/m/board.json" <<'PY' && ok "the finish time is on each box, from finished goals of that level" || bad "box times"
import json, sys
l = {x["run"]: x for x in json.load(open(sys.argv[1]))["dependency_map"]["lanes"]}
assert l["repo/donelong"]["boxes"][0]["eta"] == "done"
# one quick goal took 1h30; first began at 08:00, so it is overdue and ends at the board's time
assert l["repo/first"]["boxes"][-1]["eta"] == "~12:00 UTC", l["repo/first"]["boxes"][-1]
assert l["repo/shout"]["boxes"][-1]["eta"] == "~13:30 UTC", l["repo/shout"]["boxes"][-1]
PY
python3 - "$T/m/board.json" "$T/m/board.html" "$T/m/board-artifact.html" <<'PY' && ok "hover and tap say what it is, what is done, what is next, what it unblocks" || bad "hover and tap"
import json, re, sys
b = {x["id"]: x for l in json.load(open(sys.argv[1]))["dependency_map"]["lanes"] for x in l["boxes"]}
assert b["repo/first:pr"]["unblocks"] == ["repo/shout (goal first, shared pkg/shout.py)"]
assert b["repo/first:build"]["next"] == "Then checks" and b["repo/first:build"]["done"] == "plan"
assert b["repo/shout:plan"]["next"].startswith("Waits on goal first")
for page in sys.argv[2:]:
    h = open(page).read()
    assert "<script" not in h and "Each lane is a run" in h
    for link in re.findall(r"href='#(b\d+)'", h):
        assert re.search(r"<details><summary>[^<]*</summary><dl id=%s>" % link, h), link
    for label in ("What it is", "Done so far", "What&#x27;s next", "What it unblocks"):
        assert label in h
    assert "max-width:600px" in h and "class='scroll map'" in h
PY
# the goal starts, then finishes: its dependency stays drawn. watch.py records it while the goal is held.
python3 - "$R/shout.json" <<'PY'
import json, sys
json.dump({"slug": "shout", "goal": "Shout", "level": "quick", "status": "running", "step": "plan", "touches": ["pkg/shout.py"], "waits_on": ["first"],
           "updated": "2026-01-01T11:59:00Z", "log": ["2026-01-01T11:50:00Z queued"]}, open(sys.argv[1], "w"))
PY
git checkout -q -- .loop/queue.md
rec first done quick pr 2026-01-01T11:50:00Z 'touches=["pkg/"]'
wired='import json,sys;d=json.load(open(sys.argv[1]))["dependency_map"];assert [a["on"] for a in d["arrows"] if a["on"]]==["goal first, shared pkg/shout.py"],d["arrows"]'
map; python3 -c "$wired" "$T/m/board.json" && ok "a dependency survives its goal starting" || bad "dependency lost on start"
rec shout done quick pr 2026-01-01T11:58:00Z 'touches=["pkg/shout.py"]' 'waits_on=["first"]'
map; python3 -c "$wired" "$T/m/board.json" && ok "and stays drawn through today's finished goals" || bad "dependency lost on finish"
$B board --at 2026-01-03T12:00:00Z --out "$T/m" >/dev/null; $P --in "$T/m/board.json" >/dev/null
python3 -c "import json,sys;assert json.load(open(sys.argv[1]))['dependency_map']['lanes']==[]" "$T/m/board.json" && ok "goals finished on another day leave the map" || bad "old goals"
# watch.py records what held a goal
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
$W go "Held" --done "x" --touches lib/a.py --slug held >/dev/null
[ ! -e "$R/held.json" ] && ok "the overlapping goal is held" || bad "held goal started"
rm "$HOLD"
rec holder done minimum pr 2026-01-01T11:50:00Z 'touches=["lib/"]'
$W watch --once >/dev/null
python3 -c "import json,sys;assert json.load(open(sys.argv[1]))['waits_on']==['holder']" "$R/held.json" && ok "watch records waits_on on the run when the goal starts" || bad "waits_on not recorded"
git revert --no-edit HEAD >/dev/null; git checkout -q -- .loop/queue.md 2>/dev/null; rm -f "$R/holder.json" "$R/held.json"
# tracked sessions
$B session add docs-work --repo repo --branch claude/docs > "$T/s1" && grep -q "SESSION ADD docs-work" "$T/s1" && ok "session add" || bad "session add"
$B session add loop-work --repo repo --branch claude/loop --waits-on docs-work >/dev/null
$B session add other --repo elsewhere --waits-on no-such-thing >/dev/null
$B session add a-late --repo repo --waits-on loop-work >/dev/null
$B session add docs-work --repo repo 2>&1 | grep -q REFUSED && ok "a second add is refused" || bad "second add"
$B session add noreap 2>&1 | grep -q "needs --repo" && ok "add needs --repo" || bad "add repo"
$B session update nosuch --note x 2>&1 | grep -q REFUSED && ok "update of an unknown session refused" || bad "update unknown"
$B session update docs-work --note "wiki pages done" --next "Open the pull request" --eta 2026-01-01T13:00:00Z --pr https://x/pull/3 >/dev/null
map
python3 - "$T/m/board.json" "$T/m/board.html" <<'PY' && ok "a tracked session has a lane, a box, an arrow and a row in Runs" || bad "tracked session"
import json, sys
j = json.load(open(sys.argv[1])); d = j["dependency_map"]; h = open(sys.argv[2]).read()
l = {x["run"]: x for x in d["lanes"]}
assert "repo/docs-work" in l and "repo/loop-work" in l and "elsewhere/other" in l, set(l)
names = list(l)
assert names.index("repo/docs-work") < names.index("repo/loop-work") < names.index("repo/a-late"), names
box = l["repo/docs-work"]["boxes"][0]
assert box["status"] == "running" and box["eta"] == "~13:00 UTC" and box["done"] == "wiki pages done" and box["next"] == "Open the pull request", box
assert l["repo/docs-work"]["branch"] == "claude/docs"
assert {"from": "repo/docs-work:session", "to": "repo/loop-work:session", "on": "session docs-work"} in d["arrows"]
assert l["elsewhere/no-such-thing"]["boxes"][0]["status"] == "unknown" and "not tracked" in h
r = {x["slug"]: x for x in j["runs"]}
assert r["docs-work"]["tracked"] and r["docs-work"]["pr"] == "https://x/pull/3" and r["docs-work"]["prstate"] == "open"
assert "<td>docs-work</td>" in h or "wiki pages done" in h
PY
$B session update loop-work --status waiting --next "Choose a branch" >/dev/null; map
python3 -c "import json,sys;w={x['slug']:x for x in json.load(open(sys.argv[1]))['waiting']};assert w['loop-work']['ask']=='Choose a branch' and w['loop-work']['words']==[]" "$T/m/board.json" && ok "a tracked session can wait on you" || bad "tracked waiting"
$B session remove other | grep -q "SESSION REMOVE other" && $B session remove loop-work >/dev/null; $B session remove docs-work >/dev/null; $B session remove a-late >/dev/null; map
python3 -c "import json,sys;assert [x for x in json.load(open(sys.argv[1]))['dependency_map']['lanes'] if x['run'].endswith('docs-work')]==[]" "$T/m/board.json" && ok "session remove takes the lane away" || bad "session remove"
# retire
rec stale failed standard build 2026-01-01T11:00:00Z 'finding="old attempt"' 'touches=["z.py"]'
rec fresh running standard build 2026-01-01T11:00:00Z 'pid=1'
map
python3 -c "import json,sys;assert 'stale' in [x['slug'] for x in json.load(open(sys.argv[1]))['waiting']]" "$T/m/board.json" && ok "before retire it waits on you" || bad "before retire"
$B retire stale 2>&1 | grep -q "required: --reason" && ok "retire needs a reason" || bad "retire reason"
$B retire nosuch --reason x 2>&1 | grep -q REFUSED && ok "retire of an unknown run refused" || bad "retire unknown"
$B retire fresh --reason x 2>&1 | grep -q "is running" && ok "retire refuses a running agent" || bad "retire running"
$B retire stale --reason "Superseded by goal fresh" | grep -q "RETIRED stale" && ok "retire" || bad "retire"
map
python3 - "$T/m/board.json" "$T/m/board.html" <<'PY' && ok "a retired goal leaves Waiting on you and the map, and stays marked in Runs" || bad "retired"
import json, sys
d = json.load(open(sys.argv[1])); h = open(sys.argv[2]).read()
assert "stale" not in [x["slug"] for x in d["waiting"]]
assert "repo/stale" not in [x["run"] for x in d["dependency_map"]["lanes"]]
assert {x["slug"]: x for x in d["runs"]}["stale"]["status"] == "retired"
assert "retired: Superseded by goal fresh" in h and "1 retired" in d["digest"]
PY
$W resume stale 2>&1 | grep -q "REFUSED" && ok "resume refuses a retired goal" || bad "resume retired"
rm "$R/fresh.json" "$R/stale.json"
# repo checks
op="$here/skills/workflow-monitoring/references/operation.md"
for k in "watch.py watch --once" "latest report" "board.py board" "board_page.py" "main project folder" "Artifact" "one chat line" "6 lines" "NEXT_DELAY" "Never answer a gate" "exact words" "information" "merge only when told" "never archive"; do has "$op" "$k" "operation.md: $k"; done
has "$here/skills/workflow-monitoring/SKILL.md" "references/operation.md" "SKILL.md links operation.md"
for f in "$here"/skills/*/scripts/*.py; do [ "$(wc -c < "$f")" -lt 20480 ] && ok "under 20 KB: $(basename "$f")" || bad "over 20 KB: $f"; done
for f in "$here"/skills/*/SKILL.md; do [ "$(wc -l < "$f")" -lt 150 ] && ok "under 150 lines: $(basename "$(dirname "$f")")" || bad "over 150 lines: $f"; done
for k in '"board"' '"cadence"' '"handoff"' '"note"' '"session"' '"retire"' 'board.json' 'repos'; do has "$here/listing.json" "$k" "listing.json discloses $k"; done
echo; [ "$fails" = 0 ] && echo "ALL PASS" || { echo "$fails FAILED"; exit 1; }
