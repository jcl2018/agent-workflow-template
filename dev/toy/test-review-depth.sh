#!/bin/bash
# reads: skills/workflow-delivery/scripts/flow.py skills/workflow-delivery/scripts/goal.py
# reads: skills/workflow-monitoring/scripts/live_board.py skills/workflow-setup/scripts/settings.py
# reads: skills/workflow-setup/scripts/setup.py
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
base() { git switch -q main; cfg "$@"; git commit -qam "Config: $*"; git push -q origin main; }  # the setting is read from the base branch
cfg 'review_depth="Full"'
check "fill-repo refuses an unknown review_depth and names the fix" '$SET fill-repo --repo . 2>&1 | grep -q "REFUSED: review_depth is .Full. in .* Fix: full or condensed"'
git commit -qam "bad depth"
check "setup refuses an unknown review_depth too" 'python3 "$here/skills/workflow-setup/scripts/setup.py" --bare --dry-run 2>&1 | grep -q "REFUSED: review_depth is .Full."'
git reset -q --hard HEAD~1
check "fill-repo fills a config that already holds _help" '$SET fill-repo --repo . 2>&1 | grep -q "^FILLED" && python3 -c "import json;assert json.load(open(\".loop/config.json\"))[\"_help\"][\"review_depth\"]"'
git checkout -q -- .loop/config.json
python3 - <<PY && ok "the config loaders read a config holding _help" || bad "loaders and _help"
import sys
sys.path.insert(0, "$here/skills/workflow-monitoring/scripts"); sys.path.insert(0, "$here/skills/workflow-delivery/scripts")
import json
c = json.load(open(".loop/config.json")); assert "_help" in c
import watch, board_status
assert watch.config().get("review_depth") == "full"
assert board_status.read_json(".loop/config.json")["_help"]
PY

echo "== full is the default"
base 'auto_approve=false'
new full1
for s in idea plan review qa ship; do step full1 $s >/dev/null; done
check "with no setting change, every step records depth full" '[ "$(field full1 depth.review)" = full ] && [ "$(field full1 depth.idea)" = full ] && [ "$(field full1 flow.review)" = "done (depth full)" ]'
python3 - "$here" <<'PY' > "$d/prompt"
import sys; sys.path.insert(0, sys.argv[1] + "/skills/workflow-delivery/scripts")
import flow; print(flow.PROMPT.format(skill="s", step="review", slug="x", branch="b", purpose="p", note="", depth=flow.depth_rule("review")))
PY
check "the review prompt says run the full pipeline, never condense, and write a DEPTH line" 'grep -q "review_depth is full: run the skill.s full pipeline" "$d/prompt" && grep -q "DEPTH: full. or .DEPTH: condensed" "$d/prompt"'
out=$($goal pr full1 2>&1)
check "the pull request body lists every step with its depth" 'grep -q -- "- review: done (depth full)" "$FAKE_GH_DIR/calls.log" && grep -q -- "- idea: done (depth full)" "$FAKE_GH_DIR/calls.log"'

echo "== condensed under full is refused"
new cond1
out=$(FAKE_SKILL_OUT='STEP: done' step cond1 idea)
check "an idea reply with no DEPTH line is refused, uses no try, and names the rule, its release and the line to add" 'grep -q "REFUSED (no try used): idea refused: no DEPTH line (rule depth-line, added in v0.12.1). Fix: write .DEPTH: full. or .DEPTH: condensed. on a line of its own" <<<"$out" && [ "$(field cond1 tries)" = 0 ] && [ "$(field cond1 status)" = running ]'
step cond1 idea >/dev/null; step cond1 plan >/dev/null
out=$(FAKE_SKILL_OUT='DEPTH: condensed\nSTEP: done' step cond1 review)
check "a condensed review under full is refused with no try, naming review_depth and the fix" 'grep -q "REFUSED (no try used): the review step ran condensed while review_depth is full (rule depth-condensed, added in v0.12.1). Fix: rerun the review step at full depth" <<<"$out" && [ "$(field cond1 depth.review)" = None ] && [ "$(field cond1 tries)" = 0 ]'
check "the refusal never tells the worker to change the setting" '! grep -qi "set review_depth" <<<"$out"'
out=$(FAKE_SKILL_OUT='STEP: done' step cond1 review)
check "a review with no DEPTH line is refused and says what line to add" 'grep -q "review refused: no DEPTH line (rule depth-line, added in v0.12.1). Fix: write .DEPTH: full. or .DEPTH: condensed." <<<"$out"'
out=$(FAKE_SKILL_OUT='> DEPTH: full\nI did a quick Depth: full review\nSTEP: done' step cond1 review)
check "a quoted or prose depth is no DEPTH line" 'grep -q "review refused: no DEPTH line" <<<"$out"'
cfg 'review_depth="condensed"'
out=$(FAKE_SKILL_OUT='DEPTH: condensed\nSTEP: done' step cond1 review)
check "a worker that sets condensed in its own worktree is still held to the base branch's full" 'grep -q "the review step ran condensed while review_depth is full" <<<"$out"'
cfg 'review_depth="full"' 'auto_approve=true'
out=$(FAKE_SKILL_OUT='PENDING: a gate\nDEPTH: condensed\nSTEP: pending' step cond1 review)
check "an auto-approved condensed review under full is refused too" 'grep -q "REFUSED (no try used): the review step ran condensed" <<<"$out" && ! grep -q AUTO-APPROVED <<<"$out"'
out=$(FAKE_SKILL_OUT='DEPTH: condensed\nSTEP: failed tests broke' step cond1 review)
check "a failed reply keeps its own reason, never a depth reason" 'grep -q "review failed: tests broke" <<<"$out" && ! grep -q "condensed while" <<<"$out"'
git checkout -q -- .loop/config.json

echo "== condensed runs only when set"
base 'review_depth="condensed"'
new cond2
step cond2 idea >/dev/null; step cond2 plan >/dev/null
out=$(FAKE_SKILL_OUT='DEPTH: condensed\nSTEP: done' step cond2 review)
check "with review_depth condensed, a condensed review is recorded and named" 'grep -q "^RECORDED review done (depth condensed)" <<<"$out" && [ "$(field cond2 depth.review)" = condensed ]'
python3 - "$here" <<'PY' > "$d/prompt2"
import sys; sys.path.insert(0, sys.argv[1] + "/skills/workflow-delivery/scripts")
import flow; print(flow.depth_rule("review"))
PY
check "the prompt allows a condensed run only when the setting says so" 'grep -q "review_depth is condensed: a condensed run of this step is allowed" "$d/prompt2"'
base 'review_depth="full"'

echo "== private full_markers"
mk() { python3 - "$1" "$2" <<'PY'
import json, os, sys
p = os.path.expanduser(sys.argv[1]); s = json.load(open(p)) if os.path.exists(p) else {}; s["full_markers"] = json.loads(sys.argv[2])
os.makedirs(os.path.dirname(p), exist_ok=True); json.dump(s, open(p, "w"))
PY
}
mk "$d/flow.json" '{"review": ["Secret-Evidence-7"]}'
new mark1
step mark1 idea >/dev/null; step mark1 plan >/dev/null
out=$(FAKE_SKILL_OUT='DEPTH: full\nSTEP: done' step mark1 review)
check "a full review missing a configured marker fails, and the error never shows the marker" 'grep -q "a configured full_markers evidence string for review is missing" <<<"$out" && ! grep -q "Secret-Evidence-7" <<<"$out"'
out=$(FAKE_SKILL_OUT='ran secret-evidence-7 pass\nDEPTH: full\nSTEP: done' step mark1 review)
check "a full review carrying the marker (any case) is recorded full" 'grep -q "^RECORDED review done (depth full)" <<<"$out"'
new skip1
step skip1 idea >/dev/null; step skip1 plan >/dev/null
out=$(FAKE_SKILL_OUT='DEPTH: full\nSTEP: skipped nothing to review' step skip1 review)
check "a skipped review is held to no marker and is stamped skipped" 'grep -q "^RECORDED review skipped: nothing to review (depth full, skipped)" <<<"$out"'
base 'review_depth="condensed"'
new mark2
step mark2 idea >/dev/null; step mark2 plan >/dev/null
out=$(FAKE_SKILL_OUT='DEPTH: full\nSTEP: done' step mark2 review)
check "a claimed full review is held to the markers under condensed too" 'grep -q "full_markers evidence string for review is missing" <<<"$out"'
base 'review_depth="full"'
mk "$d/flow.json" '{}'; mk "~/.workflow-loop/flow.json" '{"review": ["Home-Evidence"]}'
new mark4
step mark4 idea >/dev/null; step mark4 plan >/dev/null
out=$(LOOP_FLOW="$d/flow.json" FAKE_SKILL_OUT='DEPTH: full\nSTEP: done' step mark4 review)
check "pointing LOOP_FLOW elsewhere never drops the markers in the default flow file" 'grep -q "full_markers evidence string for review is missing" <<<"$out"'
rm -f "$HOME/.workflow-loop/flow.json"
mk "$d/flow.json" '{"review": "not-a-list"}'
new mark3
step mark3 idea >/dev/null; step mark3 plan >/dev/null
out=$(step mark3 review)
check "full_markers that are not a list of strings put the goal in waiting for the owner, with no try, never pass silently" 'grep -q "WAITING mark3 (no try used): review: full_markers for review in the flow file is not a list of non-empty strings. Fix: the owner corrects it" <<<"$out" && [ "$(field mark3 status)" = waiting ] && [ "$(field mark3 tries)" = 0 ]'
out=$($goal record mark3 review --file "$C/loop/runs/mark3.review.txt" 2>&1)
check "a waiting goal's record is refused until the owner answers (WAITING_OWNER)" 'grep -q "mark3 waits for the owner: .*(WAITING_OWNER)" <<<"$out" && [ "$(field mark3 tries)" = 0 ]'
mk "$d/flow.json" '{}'
$goal answer mark3 >/dev/null
out=$(step mark3 review)
check "once the owner fixes the flow file and answers, the step records" 'grep -q "^RECORDED review done (depth full)" <<<"$out" && [ "$(field mark3 status)" = running ]'

echo "== the board shows the depth"
python3 - "$C/loop/runs/full1.json" <<'PY'
import json, sys
s = json.load(open(sys.argv[1])); s["status"] = "running"; s.pop("pr", None); json.dump(s, open(sys.argv[1], "w"))
PY
$LB > "$d/board"
check "the live board shows each recorded step's depth and the setting" 'grep -A1 -x "    depth: idea full, plan full, review full, qa full, ship" "$d/board" | grep -qx "      full (setting full)"'

[ "$fails" = 0 ] && echo "ALL PASS" || { echo "$fails FAILED"; exit 1; }
