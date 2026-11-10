#!/bin/bash
# reads: skills/workflow-delivery/scripts/goal.py skills/workflow-delivery/scripts/flow.py skills/workflow-delivery/scripts/fit.py
# reads: skills/workflow-delivery/scripts/prbody.py skills/workflow-delivery/scripts/private.py skills/workflow-delivery/scripts/guards.py
# reads: skills/workflow-delivery/scripts/guards_ops.py skills/workflow-delivery/scripts/role.py skills/workflow-setup/scripts/setup.py
# reads: skills/workflow-release/scripts/ skills/workflow-monitoring/scripts/
# Proves the Delivery PRD's delivery side: depth by size with the owner's override (DEL-6), resume from the last
# recorded step after a kill (DEL-7), the goal's budget (DEL-8), the private-name scan before goal.py pr pushes (DEL-9),
# verdicts in the pull request (issue 38) and GitHub touches, regeneration warnings and set (issue 117). No model.
# usage: test-delivery-prd.sh [depth|resume|budget|private|defects|hold|sites|all]
set -u
unset LOOP_SESSION_TOOL LOOP_OPERATION_SESSION LOOP_PRIVATE_NAMES LOOP_BATCH
here=$(cd "$(dirname "$0")/../.." && pwd); case=${1:-all}
export HOME=$(mktemp -d)
d=$(mktemp -d); trap 'rm -rf "$d" "$HOME"' EXIT
"$here/dev/toy/make.sh" "$d" >/dev/null || exit 1
S="$here/skills/workflow-delivery/scripts"
goal="python3 $S/goal.py"; F="python3 $S/flow.py"
export PATH="$here/dev/toy/fakegh:$PATH" FAKE_GH_DIR="$d/gh" LOOP_FLOW="$d/flow.json"
cd "$d/repo" || exit 1
python3 "$here/skills/workflow-setup/scripts/setup.py" --bare >/dev/null
git switch -q main; git merge -q --no-edit workflow-setup; git push -q origin main
fails=0
ok() { echo "PASS: $1"; }
bad() { echo "FAIL: $1"; fails=$((fails + 1)); }
check() { if eval "$2"; then ok "$1"; else bad "$1"; fi; }
C=$(cd "$(git rev-parse --git-common-dir)" && pwd); R="$C/loop/runs"
field() { python3 -c "import json,sys;d=json.load(open(sys.argv[1]));v=d;exec('for k in sys.argv[2].split(\".\"): v=(v or {}).get(k) if isinstance(v, dict) else None');print(v)" "$R/$1.json" "$2"; }
base() { git switch -q main; python3 - "$@" <<'PY'
import json, sys
c = json.load(open(".loop/config.json"))
for pair in sys.argv[1:]:
    key, _, value = pair.partition("=")
    c[key] = json.loads(value)
json.dump(c, open(".loop/config.json", "w"), indent=2)
PY
git commit -qam "Config: $*"; git push -q origin main; }
w() { LOOP_ROLE=worker "$@"; }  # goal steps run in a worker; set and touches run as the operation
step() { git switch -q "loop/$1" 2>/dev/null; w $F "$1" "$2" --wait 5 >/dev/null 2>&1; w $F "$1" "$2" --wait 10 > "$d/flow-$1-$2" 2>&1; w $goal record "$1" "$2" --file "$R/$1.$2.txt" 2>&1; }
new() { git switch -q main; w $goal new "$1" --here --goal "Goal $1" --done "Line $1" ${2:+--touches "$2"} 2>&1; }
run_all() { for s in idea plan review qa ship; do step "$1" $s >/dev/null; done; }
on() { [ "$case" = all ] || [ "$case" = "$1" ]; }

if on depth; then
  echo "== DEL-6 depth by size"
  base 'review_depth="condensed"' 'auto_approve=false'
  new small1 "src/api" >/dev/null; new large1 "src/api,src/web" >/dev/null; new bare1 >/dev/null; new wide1 "src/api,docs/wiki/Page.md,.loop/regression.tsv,dev/toy" >/dev/null
  check "a small goal (one area, up to 3 done lines) is sized small at freeze" '[ "$(field small1 size.small)" = True ] && grep -q "small: 1 done line, one area" "$R/small1.json"'
  check "two areas make a goal large, in a repo with no skills tree" '[ "$(field large1 size.small)" = False ] && grep -q "2 areas (src/api, src/web)" "$R/large1.json"'
  check "no touches declared counts as large; docs, .loop and toy paths are no area" '[ "$(field bare1 size.small)" = False ] && [ "$(field wide1 size.small)" = True ]'
  step small1 idea >/dev/null; w $F small1 plan --wait 1 > "$d/p-small" 2>&1
  python3 - "$S" "$R" > "$d/prompt-small" <<'PY'
import json, sys
sys.path.insert(0, sys.argv[1]); import flow
print(flow.depth_rule("review", json.load(open(sys.argv[2] + "/small1.json")), sys.argv[2]))
print(flow.depth_rule("review", json.load(open(sys.argv[2] + "/large1.json")), sys.argv[2]))
PY
  check "under review_depth condensed a small goal is told to run condensed, a large one full" 'sed -n 1p "$d/prompt-small" | grep -q "depth is condensed (small: 1 done line, one area): run a condensed pass" && sed -n 2p "$d/prompt-small" | grep -q "depth is full (large: 1 done line, 2 areas"'
  step small1 plan >/dev/null
  out=$(FAKE_SKILL_OUT='DEPTH: condensed\nSTEP: done' step small1 review)
  check "a small goal's condensed review is recorded under condensed" 'grep -q "^RECORDED review done (depth condensed)" <<<"$out"'
  step large1 idea >/dev/null; step large1 plan >/dev/null
  out=$(FAKE_SKILL_OUT='DEPTH: condensed\nSTEP: done' step large1 review)
  check "a large goal's condensed review is refused with no try under condensed" 'grep -q "REFUSED (no try used): the review step ran condensed" <<<"$out" && [ "$(field large1 tries)" = 0 ]'
  out=$(w $goal set large1 --depth condensed --why "worker tries" 2>&1)
  check "a worker can't set a goal's depth (operation-only)" 'grep -q "a worker can.t set its own goal" <<<"$out" && [ ! -e "$R/large1.extra.json" ] || ! grep -q depth_override "$R/large1.extra.json"'
  out=$($goal set large1 --depth condensed --why "owner: fine" 2>&1)
  check "set refuses a depth after the plan is recorded, pointing to --again" 'grep -q "plan is already recorded.*flow.py large1 plan --again (SET_AFTER_RECORD)" <<<"$out"'
  new ovr1 "src/api,src/web" >/dev/null
  $goal set ovr1 --depth condensed --why "owner: small enough" >/dev/null 2>&1
  step ovr1 idea >/dev/null; step ovr1 plan >/dev/null
  out=$(FAKE_SKILL_OUT='DEPTH: condensed\nSTEP: done' step ovr1 review)
  check "the owner's per-goal override beats the size" 'grep -q "^RECORDED review done (depth condensed)" <<<"$out" && grep -q "owner: small enough" "$R/ovr1.extra.json"'
  base 'review_depth="full"'
  new full2 "src/api" >/dev/null; $goal set full2 --depth condensed --why "owner override under full" >/dev/null 2>&1
  step full2 idea >/dev/null; step full2 plan >/dev/null
  out=$(FAKE_SKILL_OUT='DEPTH: condensed\nSTEP: done' step full2 review)
  check "under review_depth full a small goal is full, and the owner's override still wins" 'grep -q "^RECORDED review done (depth condensed)" <<<"$out"'
  new full3 "src/api" >/dev/null; step full3 idea >/dev/null; step full3 plan >/dev/null
  out=$(FAKE_SKILL_OUT='DEPTH: condensed\nSTEP: done' step full3 review)
  check "under review_depth full a small goal with no override is held to full" 'grep -q "ran condensed while review_depth is full" <<<"$out"'
  git switch -q loop/full2; w $F full2 qa --wait 60 > "$d/qa1" 2>&1; step full2 qa >/dev/null
  check "a condensed goal still runs the full land lane in qa" 'grep -qi "lane" "$d/qa1" && [ "$(field full2 flow.qa)" != None ]'
  python3 - "$S" <<'PY' && ok "the lane command never depends on depth" || bad "lane and depth"
import sys; sys.path.insert(0, sys.argv[1]); import role
assert role.lane_argv()[-3:] == ["run", "land", "--reuse"]
PY
  $goal touches small1 --add src/web --why "needs the web side" > "$d/tw" 2>&1
  check "widening a small goal's touches to a second area re-sizes it large" 'grep -q "^RESIZED small1: large" "$d/tw" && grep -q "\"small\": false" "$R/small1.extra.json"'
  base 'review_depth="full"' 'auto_approve=false'
fi

if on resume; then
  echo "== DEL-7 resume from the last recorded step"
  printf '#!/bin/bash\nif [ -n "${FAKE_SLEEP:-}" ]; then sleep "$FAKE_SLEEP"; fi\nprintf "%%b\\n" "${FAKE_SKILL_OUT:-DEPTH: full\\nSTEP: done}"\n' > "$d/skill.sh"
  new kill1 "src/api" >/dev/null; step kill1 idea >/dev/null; step kill1 plan >/dev/null
  git commit -q --allow-empty -m "build kill1"
  FAKE_SLEEP=60 w $F kill1 review --wait 1 > "$d/k1" 2>&1
  pid=$(python3 -c "import json;print(json.load(open('$R/kill1.review.job'))['pid'])")
  kill -9 -- -"$pid" 2>/dev/null || kill -9 "$pid"; sleep 1
  w $F kill1 review --wait 2 > "$d/k2" 2>&1; out=$(w $goal record kill1 review --file "$R/kill1.review.txt" 2>&1)
  check "a review killed mid-step counts exactly one failed try" 'grep -q "RUNNING" "$d/k1" && grep -q "STEP: it gave no STEP line" "$d/k2" && grep -q "TRY 1 OF 3 FAILED" <<<"$out" && [ "$(field kill1 tries)" = 1 ]'
  check "the killed goal keeps its recorded idea and plan" '[ "$(field kill1 flow.idea)" = "done (depth full)" ] && [ "$(field kill1 flow.plan)" = "done (depth full)" ]'
  check "goal.py show names review as where it resumes" '$goal show kill1 | grep -q "\"resume_at\": \"review\""'
  out=$(w $F kill1 idea 2>&1); rc=$?; echo "$out" > "$d/rerun"
  check "rerunning a recorded step is refused with no try and names the resume step" '[ $rc = 2 ] && grep -q "idea is already recorded.*go on with flow.py kill1 review.*(ALREADY_RECORDED)" <<<"$out" && [ "$(field kill1 tries)" = 1 ]'
  out=$(step kill1 review)
  check "the resumed review runs and records, and the goal moves on to qa" 'grep -q "^RECORDED review done" <<<"$out" && $goal show kill1 | grep -q "\"resume_at\": \"qa\""'
  new res2 "src/api" >/dev/null; step res2 idea >/dev/null; step res2 plan >/dev/null
  check "with idea and plan recorded and no commit since, the goal resumes at build" '$goal show res2 | grep -q "\"resume_at\": \"build\""'
  step res2 review >/dev/null
  python3 - "$R/res2.json" <<'PY'
import json, sys
s = json.load(open(sys.argv[1])); s["tokens"] = {"plan": 100, "review": 50}; json.dump(s, open(sys.argv[1], "w"))
PY
  out=$(w $F res2 plan --again --wait 5 2>&1); w $F res2 plan --wait 10 >/dev/null 2>&1
  check "--again reruns a step on purpose: it clears that step and every later one, keeping tries and tokens" 'grep -q "AGAIN plan: cleared plan, review" <<<"$out" && [ "$(field res2 flow.review)" = None ] && [ "$(field res2 tries)" = 0 ] && [ "$(field res2 tokens.review)" = 50 ]'
  python3 - "$R/sess1.json" "$S" <<'PY' 2>/dev/null
PY
  new sess1 "src/api" >/dev/null; step sess1 idea >/dev/null
  python3 - "$R/sess1.json" <<'PY'
import json, sys
s = json.load(open(sys.argv[1])); s["worker"] = "session"; s["session"] = {"id": "local_toy"}; json.dump(s, open(sys.argv[1], "w"))
PY
  w $F sess1 plan > "$d/s1" 2>&1; w $F sess1 plan > "$d/s2" 2>&1  # the session died before replying: asked again
  printf 'half a reply\n' > "$R/sess1.plan.txt"; out=$(w $goal record sess1 plan --file "$R/sess1.plan.txt" --in-session 2>&1)
  check "a session worker killed mid-step keeps its record, is asked again, and a reply with no STEP line uses no try" 'grep -q "^IN SESSION plan" "$d/s2" && [ "$(field sess1 flow.idea)" = "done (depth full)" ] && grep -q "NO_STEP_LINE" <<<"$out" && [ "$(field sess1 tries)" = 0 ]'
  printf '#!/bin/bash\nprintf "%%b\\n" "${FAKE_SKILL_OUT:-DEPTH: full\\nSTEP: done}"\n' > "$d/skill.sh"
fi

if on budget; then
  echo "== DEL-8 the goal carries a budget"
  base 'time_budget_minutes=90' 'token_budget=1000'
  new bud1 "src/api" >/dev/null
  check "a new goal carries the repo's time and token budget" '[ "$(field bud1 budget.minutes)" = 90 ] && [ "$(field bud1 budget.tokens)" = 1000 ]'
  python3 - "$R/bud1.json" <<'PY'
import json, sys
s = json.load(open(sys.argv[1])); s["tokens"] = {"idea": 700, "plan": 400}; json.dump(s, open(sys.argv[1], "w"))
PY
  s=$(git rev-parse HEAD); out=$(w $F bud1 review 2>&1)
  check "at its token budget no new step starts, naming the budget and the fix" 'grep -q "1100 tokens spent, at the token budget of 1000 (the goal.s budget).*goal.py set bud1 --budget-tokens N.*(BUDGET_TOKENS)" <<<"$out"'
  $goal set bud1 --budget-tokens 5000 --why "owner: more" >/dev/null 2>&1
  check "the owner raises one goal's budget with set" 'grep -q "\"tokens\": 5000" "$R/bud1.extra.json"'
  base 'time_budget_minutes=0' 'token_budget=0'
  new bud2 "src/api" >/dev/null
  check "a goal frozen with no budget carries an explicit none" '[ "$(field bud2 budget.minutes)" = 0 ] && [ "$(field bud2 budget.tokens)" = 0 ]'
fi

if on private; then
  echo "== DEL-9 nothing private ships"
  printf '# private names\nsecretword\n' > "$d/names"; export LOOP_PRIVATE_NAMES="$d/names"
  check "private.py check counts the patterns and never prints one" 'python3 $S/private.py check | grep -q "^PRIVATE LIST: 1 pattern from \$LOOP_PRIVATE_NAMES$" && ! python3 $S/private.py check | grep -q secretword'
  prgoal() { new "$1" "src/api" >/dev/null; run_all "$1"; }
  prgoal priv1; echo "a secretword here" > notes.txt; git add notes.txt; git commit -qm "notes"
  out=$(w $goal pr priv1 2>&1); rc=$?
  check "goal.py pr refuses to push a private name, with no try, naming the place, never the text" '[ $rc = 2 ] && grep -q "REFUSED (no try used): a private name would be pushed: notes.txt:1 (commit:[0-9a-f]*) matches list line 2; nothing was pushed" <<<"$out" && grep -q "(PRIVATE_NAME)" <<<"$out" && ! git ls-remote --exit-code origin loop/priv1 >/dev/null && [ "$(field priv1 tries)" = 0 ]'
  check "the refusal never shows the matched text" '! grep -q secretword <<<"$out"'
  git rm -q notes.txt; git commit -qm "drop notes"
  out=$(w $goal pr priv1 2>&1)
  check "a name added then removed in a later commit still refuses" 'grep -q "PRIVATE_NAME" <<<"$out" && grep -q "git reset --soft" <<<"$out"'
  prgoal priv2; git commit -q --allow-empty -m "mention secretword in a message"
  out=$(w $goal pr priv2 2>&1)
  check "a private name only in a commit message refuses" 'grep -q "commit:[0-9a-f]* message matches list line 2" <<<"$out"'
  git switch -q main; echo "old secretword" > legacy.txt; git add legacy.txt; git commit -qm legacy; git push -q origin main
  prgoal priv3; git rm -q legacy.txt; git commit -qm "remove the leaked name"
  out=$(w $goal pr priv3 2>&1)
  check "a goal that only removes a leaked name is not refused" 'grep -q "^PR " <<<"$out"'
  prgoal priv4; FAKE_SKILL_OUT='VERDICT: outside voice: secretword approves\nDEPTH: full\nSTEP: done' step priv4 ship >/dev/null 2>&1
  w $F priv4 ship --again >/dev/null 2>&1; FAKE_SKILL_OUT='VERDICT: outside voice: secretword approves\nDEPTH: full\nSTEP: done' step priv4 ship >/dev/null
  out=$(w $goal pr priv4 2>&1)
  check "a private name only in the pull request body refuses" 'grep -q "pr-body:[0-9]* matches list line 2" <<<"$out"'
  printf 'good\n(unclosed\n' > "$d/names"; prgoal priv5
  out=$(w $goal pr priv5 2>&1)
  check "a broken list refuses every push, naming the file and line, never the pattern" 'grep -q "\$LOOP_PRIVATE_NAMES line 2 isn.t a valid pattern.*(PRIVATE_LIST)" <<<"$out" && ! git ls-remote --exit-code origin loop/priv5 >/dev/null'
  unset LOOP_PRIVATE_NAMES; prgoal priv6; w $goal pr priv6 >/dev/null 2>&1
  check "with no list the pull request says nothing was checked, naming the list unexpanded" 'grep -q "Private-name scan: no list at ~/.workflow-loop/private-names, nothing was checked" "$FAKE_GH_DIR/calls.log" && ! grep -q "$HOME" "$FAKE_GH_DIR/calls.log"'
  mkdir -p "$HOME/.workflow-loop"; printf '# nothing private here\n' > "$HOME/.workflow-loop/private-names"
  check "a list holding only comments is off on purpose" 'python3 $S/private.py check | grep -q "off on purpose"'
  rm -rf "$HOME/.workflow-loop"
  python3 - "$here" <<'PY' && ok "every push or GitHub write in delivery, release and monitoring calls the scan first" || bad "an unscanned push site"
import ast, os, sys
here = sys.argv[1]
skip = {"private.py"}
bad = []
for skill in ("workflow-delivery", "workflow-release", "workflow-monitoring"):
    folder = os.path.join(here, "skills", skill, "scripts")
    for name in sorted(os.listdir(folder)):
        if not name.endswith(".py") or name in skip:
            continue
        tree = ast.parse(open(os.path.join(folder, name)).read())
        for fn in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
            text = ast.unparse(fn)
            writes = ('"push"' in text and '"git"' in text) or ('"pr", "create"' in text) or ('"release", "create"' in text) \
                or ('"pr", "merge"' in text) or ('"pr", "comment"' in text)
            if writes and "scan" not in text and "private" not in text:
                bad.append("%s:%s" % (name, fn.name))
if bad:
    print("unscanned: " + ", ".join(bad)); sys.exit(1)
PY
fi

if on defects; then
  echo "== issue 38: verdicts and run results on record"
  new v38 "src/api" >/dev/null; step v38 idea >/dev/null
  FAKE_SKILL_OUT='VERDICT: outside voice: approve with two notes\nVERDICT: spec review: PASS at round 2\nDEPTH: full\nSTEP: done' step v38 plan >/dev/null
  for s in review qa ship; do step v38 $s >/dev/null; done
  w $goal pr v38 >/dev/null 2>&1
  check "a step's VERDICT lines are kept on the run record and listed in the pull request (#38)" 'grep -q "outside voice: approve with two notes" "$R/v38.json" && grep -q "verdict: outside voice: approve with two notes" "$FAKE_GH_DIR/calls.log" && grep -q "verdict: spec review: PASS at round 2" "$FAKE_GH_DIR/calls.log"'
  check "the pull request names the decided review depth and the budget (#38)" 'grep -q "^Review depth: full (review_depth full holds every goal to full)." "$FAKE_GH_DIR/calls.log" && grep -q "^Budget: " "$FAKE_GH_DIR/calls.log" && grep -q "Skill flow:" "$FAKE_GH_DIR/calls.log"'
  echo "== issue 117: GitHub surfaces, regeneration warnings, set"
  out=$(new bad117 "github:pages" 2>&1)
  check "a github: touch that isn't a known surface is refused at freeze (#117)" 'grep -q "github:pages isn.t a GitHub surface" <<<"$out" && [ ! -e "$R/bad117.json" ]'
  git switch -q main; mkdir -p tools; printf '#!/bin/sh\necho "# Toy" > README.md\n' > tools/gen.sh; git add tools; git commit -qm "a script that writes README.md"; git push -q origin main
  new g117 "github:wiki,README.md" >/dev/null
  check "a goal may name GitHub surfaces in its touches and is sized large for them (#117)" 'grep -q "github:wiki" "$R/g117.json" && [ "$(field g117 size.small)" = False ]'
  check "the operation widens touches with a GitHub surface (#117)" '$goal touches g117 --add github:milestones --why "release milestone" | grep -q "^TOUCHES g117 +github:milestones"'
  git rm -q README.md; git commit -qm "drop README"; run_all g117; w $goal pr g117 >/dev/null 2>&1
  check "a deleted file a repo script writes back is warned about in the pull request (#117)" 'grep -q "WARN: tools/gen.sh names README.md, which this goal deletes; it may write it back" "$FAKE_GH_DIR/calls.log" && grep -q "GitHub surfaces this goal changes: github:wiki" "$FAKE_GH_DIR/calls.log"'
fi

if on hold; then
  echo "== the merge hold: criterion rows need their requirement text on the base"
  git switch -q main; mkdir -p docs/wiki; printf '# Page\n\n- ABC-1: the first one\n' > docs/wiki/Page.md
  git add docs/wiki/Page.md; git commit -qm "page"; git push -q origin main
  git switch -q -c loop/hold1
  printf 'r1\tland\ttrue\tABC-1\t\td\tcriterion\t\nr2\tland\ttrue\tABC-2\t\td\tcriterion\t\nr3\tland\ttrue\tXYZ-1\t\td\tcriterion\t\n' >> .loop/regression.tsv
  git add .loop/regression.tsv; git commit -qm "rows"
  python3 - "$here/skills/workflow-release/scripts" > "$d/hold" <<'PY'
import json, sys
sys.path.insert(0, sys.argv[1]); import merge
print(merge.missing_ids(".", json.load(open(".loop/config.json"))))
PY
  check "merge.py holds a row whose requirement ID no base page names where the pages use that prefix, and only notes a new prefix" 'grep -q "^(\[.ABC-2.\], \[.XYZ-1.\])$" "$d/hold"'
fi

if on sites; then
  echo "== sizes"
  for f in "$here"/skills/workflow-delivery/scripts/*.py "$here"/skills/workflow-release/scripts/*.py "$here"/skills/workflow-monitoring/scripts/*.py; do
    [ "$(wc -c < "$f")" -lt 20480 ] || bad "$(basename "$f") is over 20 KB"
  done
  ok "every script the goal touches stays under 20 KB"
fi
[ "$fails" = 0 ] || { echo "$fails failed"; exit 1; }
echo "ALL PASS"
