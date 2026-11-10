#!/bin/bash
# Proves a flow step records the tokens its agent used, read from the agent's JSON output. A fake `claude` prints the JSON;
# no model is called. usage: test-tokens.sh [DIR]
set -u
unset LOOP_SESSION_TOOL LOOP_OPERATION_SESSION  # a toy test never reaches a real session tool
unset LOOP_ROLE
here=$(cd "$(dirname "$0")/../.." && pwd)
T=${1:-$(mktemp -d)}; rm -rf "${T:?}"; mkdir -p "$T"
D="$here/skills/workflow-delivery/scripts"; M="$here/skills/workflow-monitoring/scripts"
goal="env LOOP_ROLE=worker python3 $D/goal.py"; F="env LOOP_ROLE=worker python3 $D/flow.py"
export HOME="$T/home"; mkdir -p "$HOME"
fails=0
ok() { echo "PASS: $1"; }
bad() { echo "FAIL: $1"; fails=$((fails + 1)); }
check() { if eval "$2"; then ok "$1"; else bad "$1"; fi; }
"$here/dev/toy/make.sh" "$T" >/dev/null || exit 1
cd "$T/repo" || exit 1
python3 "$here/skills/workflow-setup/scripts/setup.py" >/dev/null
git switch -q main; git merge -q --no-edit workflow-setup; git push -q origin main
mkdir -p "$T/bin"
cat > "$T/bin/claude" <<'SH'
#!/bin/bash
echo "noise on stderr" >&2
printf '{"type":"result","result":"PENDING: a choice\\nDEPTH: full\\nSTEP: done","usage":{"input_tokens":100,"output_tokens":50,"cache_creation_input_tokens":25,"cache_read_input_tokens":9000}}\n'
SH
chmod +x "$T/bin/claude"
python3 - "$T" <<'PY'
import json, sys
d = sys.argv[1]
json.dump({"command": [d + "/bin/claude", "-p"], "env": {"FAKE_MODE": "unattended"}, "probe": ["bash", "-c", "echo $FAKE_MODE"],
           "probe_expect": "unattended", "steps": {s: "x" for s in ("idea", "plan", "review", "qa", "ship")}}, open(d + "/flow.json", "w"))
PY
export LOOP_FLOW="$T/flow.json"
$goal new tok --here --goal "Count tokens" --done "tokens are counted" >/dev/null
C=$(cd "$(git rev-parse --git-common-dir)" && pwd)
$F tok idea --wait 5 >/dev/null; out=$($F tok idea --wait 10)
echo "$out"
check "the step prints the agent's own STEP and PENDING lines" 'grep -q "^STEP: done" <<<"$out" && grep -q "^PENDING: a choice" <<<"$out"'
check "tokens are input + output + cache-creation, never cache reads" '[ "$(python3 -c "import json; print(json.load(open(\"$C/loop/runs/tok.json\"))[\"tokens\"][\"idea\"])")" = 175 ]'
check "the reply file holds the result text, the raw JSON is kept beside it" 'grep -q "^STEP: done" "$C/loop/runs/tok.idea.txt" && grep -q usage "$C/loop/runs/tok.idea.txt.raw"'
check "the live board leaves tokens off" '! python3 "$M/board_status.py" | grep -qi "token"'
[ $fails = 0 ] && echo "ALL PASS" || { echo "$fails FAILED"; exit 1; }
