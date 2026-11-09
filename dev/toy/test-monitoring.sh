#!/bin/bash
# Proves workflow-monitoring on a throwaway toy repo with a fake agent. No model is called and gh is faked.
# usage: test-monitoring.sh [DIR]
# test-goal.sh covers go, watch, mend and usage limits. This covers what it doesn't: a killed agent, overlapping goals,
# what report and dashboard show, and resume.
set -u
export LOOP_ROLE=worker  # goal.py and flow.py run only in a worker
here=$(cd "$(dirname "$0")/../.." && pwd)
T=${1:-$(mktemp -d)}; rm -rf "${T:?}"; mkdir -p "$T"
W="python3 $here/skills/workflow-monitoring/scripts/watch.py"
M="python3 $here/skills/workflow-monitoring/scripts/monitor.py"
B="python3 $here/skills/workflow-monitoring/scripts/board.py"
P="python3 $here/skills/workflow-monitoring/scripts/board_page.py"
goal="python3 $here/skills/workflow-delivery/scripts/goal.py"
export PATH="$here/dev/toy/fakegh:$PATH" FAKE_GH_DIR="$T/gh" HOME="$T/home" FAKE_AGENT="$T/fake"
mkdir -p "$HOME" "$FAKE_AGENT"
trap 'rm -f "$FAKE_AGENT"/hold-*' EXIT  # a held stand-in agent ends when its file goes
fails=0
ok() { echo "PASS: $1"; }
bad() { echo "FAIL: $1"; fails=$((fails + 1)); }
check() { if eval "$2"; then ok "$1"; else bad "$1"; fi; }
"$here/dev/toy/make.sh" "$T" >/dev/null || exit 1
export LOOP_FLOW="$T/flow.json"
cd "$T/repo" || exit 1
python3 "$here/skills/workflow-setup/scripts/setup.py" --bare >/dev/null
git switch -q main; git merge -q --no-edit workflow-setup
C=$(cd "$(git rev-parse --git-common-dir)" && pwd); export COMMON="$C"
field() { python3 -c "import json,sys;print(json.load(open(sys.argv[1])).get(sys.argv[2]))" "$C/loop/runs/$1.json" "$2"; }
sets() { python3 - "$C/loop/runs/$1.json" "${@:2}" <<'PY'
import json, sys
s = json.load(open(sys.argv[1]))
for pair in sys.argv[2:]:
    key, _, value = pair.partition("=")
    s[key] = json.loads(value)
json.dump(s, open(sys.argv[1], "w"))
PY
}
# A stand-in agent: it waits if told to, or marks its goal done.
cat > "$T/agent.sh" <<'A'
#!/bin/bash
prompt=${!#}
slug=$(grep -oE 'Slug: [a-z0-9-]+' <<<"$prompt" | head -1 | cut -d' ' -f2)
[ -n "$slug" ] || slug=$(grep -oE 'goal [a-z0-9-]+ in this git' <<<"$prompt" | head -1 | cut -d' ' -f2)
printf '%s' "$prompt" > "$FAKE_AGENT/prompt-$slug"
while [ -e "$FAKE_AGENT/hold-$slug" ]; do sleep 0.1; done
python3 - "$COMMON/loop/runs/$slug.json" <<'PY'
import json, sys
s = json.load(open(sys.argv[1])); s["status"] = "done"; s["step"] = "release"; s["pr"] = "https://example.test/pull/1"
json.dump(s, open(sys.argv[1], "w"))
PY
A
python3 - "$T/agent.sh" <<'PY'
import json, sys
c = json.load(open(".loop/config.json"))
c["agent_command"] = ["bash", sys.argv[1]]; c["parallel"] = 3
json.dump(c, open(".loop/config.json", "w"), indent=2)
PY
git commit -qam "Agent"; git push -q origin main
until_status() { for _ in $(seq 100); do [ "$(field "$1" status)" = "$2" ] && return 0; sleep 0.1; done; return 1; }

echo "== a killed agent fails; the other goals carry on"
touch "$FAKE_AGENT/hold-doomed" "$FAKE_AGENT/hold-first" "$FAKE_AGENT/hold-other"
$W go "Add doomed" --done "doomed works" --touches doomed.py --slug doomed >/dev/null
$W go "Add other" --done "other works" --touches other.py --slug other >/dev/null
$W go "Add first" --done "first works" --touches pkg/ --slug first >/dev/null
for _ in $(seq 100); do [ -f "$FAKE_AGENT/prompt-doomed" ] && break; sleep 0.1; done
kill -9 -- "-$(field doomed pid)" 2>/dev/null || kill -9 "$(field doomed pid)"
sleep 0.3
$M report > "$T/r1"
check "report marks a dead agent failed" '[ "$(field doomed status)" = failed ]'
check "report lists the finding" 'grep -q "^- doomed (failed)" "$T/r1"'
check "a failed goal leaves the others running" '[ "$(field other status)" = running ]'
rm "$FAKE_AGENT/hold-other"
until_status other done && ok "another goal still finished" || bad "other goal"

echo "== a goal waits only for the goals it depends on"
$W go "Add shout" --done "shout works" --touches pkg/shout.py --depends-on first --slug shout > "$T/g1"
check "go says the dependency holds it" 'grep -q "QUEUED shout: waits on first (running)" "$T/g1"'
$W go "Add shared" --done "shared works" --touches pkg/shared.py --slug shared >/dev/null
check "a goal sharing the running goal's files still starts" '[ -e "$C/loop/runs/shared.json" ]'
$W watch --once > "$T/w1"
check "watch keeps it queued" 'grep -q "STILL QUEUED shout: waits on first (running)" "$T/w1"'
check "watch names the failed goal" 'grep -q "NEEDS YOU doomed" "$T/w1"'
$M report | grep -q "^- shout: waits on first (running)" && ok "report says what holds it" || bad "report holds"
rm "$FAKE_AGENT/hold-first"; until_status first done || bad "first finished"
$W watch --once >/dev/null
check "done is not merged: the dependent goal still waits" '[ ! -e "$C/loop/runs/shout.json" ]'
sets first 'release="merged"'
$W watch --interval 0.2 > "$T/w2"
check "watch started it after the other ended" '[ "$(field shout status)" = done ]'
check "watch ended by itself" 'grep -q "NOTHING LEFT" "$T/w2"'

echo "== report and dashboard show what waits on you"
touch "$FAKE_AGENT/hold-asks"
$W go "Add <asks>" --done "asks works" --touches asks.py --slug asks --release ask >/dev/null
sets asks 'status="waiting"' 'waiting={"ask":"Cut <i>it</i>?","words":["cut asks","leave asks"]}'
$M report > "$T/r2"
check "report gives the question" 'grep -q "^- asks: Cut <i>it</i>?" "$T/r2"'
check "report gives the exact words" 'grep -q "type: cut asks" "$T/r2" && grep -q "type: leave asks" "$T/r2"'
html=$($M dashboard)
check "dashboard shows the words" 'grep -q "<code>leave asks</code>" "$html"'
check "dashboard escapes and has no scripts" 'grep -q "Cut &lt;i&gt;it" "$html" && ! grep -q "<script\|<i>it" "$html"'
rm "$FAKE_AGENT/hold-asks"; sleep 0.3; sets asks 'status="done"' 'waiting=null'

echo "== resume"
$W resume other 2>&1 | grep -q "REFUSED: other is done" && ok "resume refuses a done goal" || bad "resume refuse"
$W resume nosuch 2>&1 | grep -q "REFUSED: no run named nosuch" && ok "resume refuses an unknown goal" || bad "resume unknown"
rm -rf "$(field doomed worktree)"; rm "$FAKE_AGENT/hold-doomed"
$W resume doomed > "$T/res1"
check "resume makes a lost worktree again" 'grep -q "RECREATED worktree" "$T/res1" && [ -d "$(field doomed worktree)" ]'
until_status doomed done && ok "the resumed goal finished" || bad "resume finish"
sets doomed 'status="stopped"' 'tries=3'
$W resume doomed >/dev/null
check "resume puts a stopped goal's tries back to 0" 'until_status doomed done && [ "$(field doomed tries)" = 0 ]'

echo "== a quiet check-in still prints the full live board"
touch "$FAKE_AGENT/hold-quiet"
$W go "Add quiet" --done "quiet" --slug quiet >/dev/null
AT=2026-01-01T12:00:00Z
$B cadence 10 >/dev/null
$B board --at $AT --out "$T/b" >/dev/null
$B board --at $AT --since "$T/b/board.json" --out "$T/b" > "$T/b1"
check "no change while a goal is open still prints the live board and CHANGED no, never NO_CHANGE" 'grep -q "^LIVE BOARD" "$T/b1" && grep -qx "CHANGED no" "$T/b1" && ! grep -q "NO_CHANGE\|Nothing changed" "$T/b1"'
$P --in "$T/b/board.json" >/dev/null
check "the page shows the next check-in too" 'grep -q "Next check-in 12:10 UTC." "$T/b/board.html"'
$B board --at $AT --since "$T/b/board.json" --out "$T/b" | grep -q "^LIVE BOARD" && ok "and again on the next quiet check-in" || bad "repeat"
rm "$FAKE_AGENT/hold-quiet"; until_status quiet done || bad "quiet finished"
$B board --at $AT --out "$T/b" >/dev/null
$B board --at $AT --since "$T/nofile" --out "$T/b" | grep -q "NO_CHANGE" && bad "no one-line mode" || ok "no one-line mode"

echo "== the mender leaves landed goals alone"
# A gh that answers MERGED for any branch or pull request named in $FAKE_AGENT/merged.
mkdir -p "$T/bin"; cat > "$T/bin/gh" <<'GH'
#!/bin/bash
if [ "$1 $2" = "pr view" ] && grep -qxF -- "$3" "$FAKE_AGENT/merged" 2>/dev/null; then
  echo '{"state":"MERGED","url":"https://example.test/pull/16"}'; exit 0
fi
exit 1
GH
chmod +x "$T/bin/gh"; export PATH="$T/bin:$PATH"; : > "$FAKE_AGENT/merged"
python3 - <<'PY'
import json
c = json.load(open(".loop/config.json")); c["mend"] = True; json.dump(c, open(".loop/config.json", "w"), indent=2)
PY
git commit -qam "Mend on"
touch "$FAKE_AGENT/hold-landed"
$W go "Add landed" --done "landed" --touches landed.py --slug landed >/dev/null
kill -9 -- "-$(field landed pid)" 2>/dev/null; sleep 0.3
echo loop/landed >> "$FAKE_AGENT/merged"; rm -f "$FAKE_AGENT/prompt-landed"
$W watch --once > "$T/m1"
check "a landed goal with an empty pr field is done, not mended" '[ "$(field landed status)" = done ] && [ "$(field landed pr)" = https://example.test/pull/16 ] && [ "$(field landed mended)" = None ]'
check "and no agent was launched for it" 'sleep 0.3; [ ! -e "$FAKE_AGENT/prompt-landed" ]'
touch "$FAKE_AGENT/hold-late"
$W go "Add late" --done "late" --touches late.py --slug late >/dev/null
python3 -c "import os;print(os.spawnlp(os.P_NOWAIT,'sh','sh','-c','exec python3 -c \"import os,time;os.setsid();time.sleep(60)\"'))" > "$T/mpid"; sleep 0.3
kill -9 -- "-$(field late pid)" 2>/dev/null; mender=$(cat "$T/mpid")
sets late "pid=$mender" 'mended=true' 'status="running"'
echo loop/late >> "$FAKE_AGENT/merged"
python3 "$here/skills/workflow-monitoring/scripts/mend.py" > "$T/m2"
check "a mender running after its goal lands is stopped" 'sleep 0.3; ! kill -0 "$mender" 2>/dev/null && [ "$(field late status)" = done ]'
sets late 'status="done"'
touch "$FAKE_AGENT/hold-slow"
$W go "Add slow" --done "slow" --touches slow.py --slug slow >/dev/null
for _ in $(seq 100); do [ -f "$FAKE_AGENT/prompt-slow" ] && break; sleep 0.1; done
kill -9 -- "-$(field slow pid)" 2>/dev/null; sleep 0.3; rm -f "$FAKE_AGENT/prompt-slow"
$W watch --once >/dev/null
check "a failed goal waits before a mender starts" 'sleep 0.3; [ ! -e "$FAKE_AGENT/prompt-slow" ] && [ "$(field slow status)" = failed ] && [ "$(field slow mended)" = None ]'
sets slow 'status="done"' 
mkdir -p "$T/lone"; cp "$here/skills/workflow-monitoring/scripts/watch.py" "$here/skills/workflow-monitoring/scripts/graph.py" "$T/lone/"
check "watch.py alone runs, and says it mended nothing" 'python3 "$T/lone/watch.py" watch --once | grep -q "mend.py isn.t beside"'
check "watch.py alone refuses resume, and says why" 'python3 "$T/lone/watch.py" resume late 2>&1 | grep -q "needs mend.py"'
cp "$here/skills/workflow-monitoring/scripts/board.py" "$T/lone/"  # graph.py is beside it already
check "board.py alone refuses a run command, and says why" 'python3 "$T/lone/board.py" note late hi 2>&1 | grep -q "needs board_runs.py"'
check "board.py alone still writes a board" 'python3 "$T/lone/board.py" board --out "$T/lone/b" | grep -q "^JSON "'

echo "== a goal with no pid is left alone"
python3 - "$C/loop/runs/own.json" <<'PY'
import json, sys
json.dump({"slug": "own", "goal": "Own", "level": "0", "status": "running", "step": "build", "branch": "loop/own", "worktree": "/nowhere",
           "pid": None, "tries": 0, "touches": [], "updated": "2026-01-01T00:00:00Z", "log": []}, open(sys.argv[1], "w"))
PY
$M report >/dev/null; $M dashboard >/dev/null
check "report never marks a goal with no pid failed" '[ "$(field own status)" = running ]'
$W watch --once >/dev/null
check "watch never marks a goal with no pid failed" '[ "$(field own status)" = running ]'
timeout_watch() { python3 -c "import subprocess,sys;sys.exit(subprocess.run(sys.argv[1:],timeout=20,stdout=subprocess.DEVNULL).returncode)" "$@"; }
check "a plain watch still ends beside a goal with no pid" 'timeout_watch python3 "$here/skills/workflow-monitoring/scripts/watch.py" watch --interval 0.2'
$W go "Add free" --done "free" --touches free.py --slug free >/dev/null
check "a goal with no pid uses no agent slot" '[ -n "$(field free pid)" ] && [ "$(field free pid)" != None ]'
sets own 'touches=["held.py"]'
$W go "Add held" --done "held" --touches held.py --slug heldby >/dev/null
check "and it holds back no goal touching the same files" '[ -e "$C/loop/runs/heldby.json" ]'
sed -i.bak '/slug: heldby /d' .loop/queue.md
sets own 'status="stopped"'
$W watch --once >/dev/null
check "a goal with no pid is never mended" 'sleep 0.3; [ "$(field own status)" = stopped ] && [ "$(field own mended)" = None ]'
sets own 'status="done"'

echo; [ "$fails" = 0 ] && echo "ALL PASS" || { echo "$fails FAILED"; exit 1; }
