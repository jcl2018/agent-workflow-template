#!/bin/bash
# Proves review_depth: full is the default, condensed runs only when set, every recorded step names its depth, private
# full_markers are required of a full plan or review, and setup writes the setting with its explanation. No model is called.
# usage: test-review-depth.sh [DIR]
set -u
unset LOOP_SESSION_TOOL LOOP_OPERATION_SESSION  # a toy test never reaches a real session tool
export LOOP_ROLE=worker  # goal.py and flow.py run only in a worker
here=$(cd "$(dirname "$0")/../.." && pwd)
export HOME=$(mktemp -d)
d=${1:-$(mktemp -d)}; rm -rf "$d"; mkdir -p "$d"
"$here/dev/toy/make.sh" "$d" >/dev/null || exit 1
goal="python3 $here/skills/workflow-delivery/scripts/goal.py"; F="python3 $here/skills/workflow-delivery/scripts/flow.py"
SET="python3 $here/skills/workflow-setup/scripts/settings.py"; LB="python3 $here/skills/workflow-monitoring/scripts/live_board.py"
export PATH="$here/dev/toy/fakegh:$PATH" FAKE_GH_DIR="$d/gh" LOOP_FLOW="$d/flow.json" LOOP_BOARD_HEALTH=green
cd "$d/repo" || exit 1
python3 "$here/skills/workflow-setup/scripts/setup.py" --bare >/dev/null
git switch -q main; git merge -q --no-edit workflow-setup; git push -q origin main
fails=0
ok() { echo "PASS: $1"; }
bad() { echo "FAIL: $1"; fails=$((fails + 1)); }
check() { if eval "$2"; then ok "$1"; else bad "$1"; fi; }
C=$(cd "$(git rev-parse --git-common-dir)" && pwd)
field() { python3 -c "import json,sys;d=json.load(open(sys.argv[1]));v=d;exec('for k in sys.argv[2].split(\".\"): v=(v or {}).get(k)');print(v)" "$C/loop/runs/$1.json" "$2"; }
cfg() { python3 - "$@" <<'PY'
import json, sys
c = json.load(open(".loop/config.json"))
for pair in sys.argv[1:]:
    key, _, value = pair.partition("=")
    c[key] = json.loads(value)
json.dump(c, open(".loop/config.json", "w"), indent=2)
PY
}
step() { $F "$1" "$2" --wait 5 >/dev/null; $F "$1" "$2" --wait 10 > "$d/flow-$1-$2" 2>&1; $goal record "$1" "$2" --file "$C/loop/runs/$1.$2.txt" 2>&1; }
new() { git switch -q main; $goal new "$1" --here --goal "Goal $1" --done "Line $1" >/dev/null 2>&1; }

echo "== setup writes the setting"
check "setup writes review_depth full with its one-line explanation" '[ "$(python3 -c "import json;c=json.load(open(\".loop/config.json\"));print(c[\"review_depth\"], bool(c[\"_help\"][\"review_depth\"]))")" = "full True" ]'
check "the settings reference lists review_depth with its default and a line" '$SET reference | grep -q "^| .review_depth. | .full. | full runs the plan and review skills"'
check "the private half lists full_markers, and fill-private writes it" '$SET reference | grep -q "^| .full_markers. |" && $SET fill-private --file "$d/private.json" >/dev/null && grep -q "\"full_markers\"" "$d/private.json"'
cfg 'review_depth="Full"'
check "fill-repo refuses an unknown review_depth and names the fix" '$SET fill-repo --repo . 2>&1 | grep -q "REFUSED: review_depth is .Full. in .* Fix: full or condensed"'
cfg 'review_depth="full"'
python3 - <<PY && ok "the config loaders read a config holding _help" || bad "loaders and _help"
import sys
sys.path.insert(0, "$here/skills/workflow-monitoring/scripts"); sys.path.insert(0, "$here/skills/workflow-delivery/scripts")
import importlib, json
c = json.load(open(".loop/config.json")); assert "_help" in c
import watch, board_status
assert watch.config().get("review_depth") == "full"
assert board_status.read_json(".loop/config.json")["_help"]
PY

echo "== full is the default"
cfg 'auto_approve=false'
new full1
for s in idea plan review qa ship; do step full1 $s >/dev/null; done
check "with no setting change, every step records depth full" '[ "$(field full1 depth.review)" = full ] && [ "$(field full1 depth.idea)" = full ] && [ "$(field full1 flow.review)" = "done (depth full)" ]'
python3 - "$here" <<'PY' > "$d/prompt"
import sys; sys.path.insert(0, sys.argv[1] + "/skills/workflow-delivery/scripts")
import flow; print(flow.PROMPT.format(skill="s", step="review", slug="x", branch="b", purpose="p", note="", depth=flow.depth_rule("review")))
PY
check "the review prompt says run the full pipeline, never condense, and write a DEPTH line" 'grep -q "review_depth is full: run the skill.s full pipeline" "$d/prompt" && grep -q "DEPTH: full. or .DEPTH: condensed" "$d/prompt"'

echo "== condensed under full is refused"
new cond1
step cond1 idea >/dev/null; step cond1 plan >/dev/null
out=$(FAKE_SKILL_OUT='DEPTH: condensed\nSTEP: done' step cond1 review)
check "a condensed review under full fails the try and names review_depth and the fix" 'grep -q "TRY 1 OF .* FAILED: review failed: the review step ran condensed while review_depth is full in .loop/config.json. Fix:" <<<"$out" && [ "$(field cond1 depth.review)" = None ]'
out=$(FAKE_SKILL_OUT='STEP: done' step cond1 review)
check "a review with no DEPTH line fails and says what line to add" 'grep -q "review failed: no DEPTH line. Fix: end the reply with .DEPTH: full. or .DEPTH: condensed." <<<"$out"'
cfg 'auto_approve=true'
out=$(FAKE_SKILL_OUT='PENDING: a gate\nDEPTH: condensed\nSTEP: pending' step cond1 review)
check "an auto-approved condensed review under full is refused too" 'grep -q "review failed: the review step ran condensed" <<<"$out" && ! grep -q AUTO-APPROVED <<<"$out"'
out=$(FAKE_SKILL_OUT='DEPTH: condensed\nSTEP: failed tests broke' step cond1 review)
check "a failed reply keeps its own reason, never a depth reason" 'grep -q "review failed: tests broke" <<<"$out" && ! grep -q "condensed while" <<<"$out"'
cfg 'auto_approve=false'

echo "== condensed runs only when set"
cfg 'review_depth="condensed"'
new cond2
step cond2 idea >/dev/null; step cond2 plan >/dev/null
out=$(FAKE_SKILL_OUT='DEPTH: condensed\nSTEP: done' step cond2 review)
check "with review_depth condensed, a condensed review is recorded and named" 'grep -q "^RECORDED review done (depth condensed)" <<<"$out" && [ "$(field cond2 depth.review)" = condensed ]'
python3 - "$here" <<'PY' > "$d/prompt2"
import sys; sys.path.insert(0, sys.argv[1] + "/skills/workflow-delivery/scripts")
import flow; print(flow.depth_rule("review"))
PY
check "the prompt allows a condensed run only when the setting says so" 'grep -q "review_depth is condensed: a condensed run of this step is allowed" "$d/prompt2"'
cfg 'review_depth="full"'

echo "== private full_markers"
python3 - "$d" <<'PY'
import json, sys
p = sys.argv[1] + "/flow.json"; s = json.load(open(p)); s["full_markers"] = {"review": ["Secret-Evidence-7"]}; json.dump(s, open(p, "w"))
PY
new mark1
step mark1 idea >/dev/null; step mark1 plan >/dev/null
out=$(FAKE_SKILL_OUT='DEPTH: full\nSTEP: done' step mark1 review)
check "a full review missing a configured marker fails, and the error never shows the marker" 'grep -q "a configured full_markers evidence string for review is missing" <<<"$out" && ! grep -q "Secret-Evidence-7" <<<"$out"'
out=$(FAKE_SKILL_OUT='ran secret-evidence-7 pass\nDEPTH: full\nSTEP: done' step mark1 review)
check "a full review carrying the marker (any case) is recorded full" 'grep -q "^RECORDED review done (depth full)" <<<"$out"'
cfg 'review_depth="condensed"'
new mark2
step mark2 idea >/dev/null; step mark2 plan >/dev/null
out=$(FAKE_SKILL_OUT='DEPTH: full\nSTEP: done' step mark2 review)
check "a claimed full review is held to the markers under condensed too" 'grep -q "full_markers evidence string for review is missing" <<<"$out"'
cfg 'review_depth="full"'
python3 - "$d" <<'PY'
import json, sys
p = sys.argv[1] + "/flow.json"; s = json.load(open(p)); s["full_markers"] = {"review": "not-a-list"}; json.dump(s, open(p, "w"))
PY
new mark3
step mark3 idea >/dev/null; step mark3 plan >/dev/null
out=$(step mark3 review)
check "full_markers that are not a list of strings are ignored with a NOTE, never a crash" 'grep -q "NOTE: full_markers for review is not a list" <<<"$out" && grep -q "^RECORDED review done (depth full)" <<<"$out"'

echo "== the board and the pull request body show the depth"
python3 - "$C/loop/runs/full1.json" <<'PY'
import json, sys
s = json.load(open(sys.argv[1])); s["status"] = "running"; json.dump(s, open(sys.argv[1], "w"))
PY
$LB > "$d/board"
check "the live board shows each recorded step's depth and the setting" 'grep -q "^    depth: idea full, plan full, review full, qa full, ship full (setting full)$" "$d/board"'
check "the pull request body lists every step with its depth (from the flow results)" 'python3 -c "import json;f=json.load(open(\"$C/loop/runs/full1.json\"))[\"flow\"];assert all(\"(depth full)\" in f[s] for s in (\"idea\",\"plan\",\"review\",\"qa\",\"ship\")),f"'

[ "$fails" = 0 ] && echo "ALL PASS" || { echo "$fails FAILED"; exit 1; }
