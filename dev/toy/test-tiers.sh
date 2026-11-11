#!/bin/bash
# reads: skills/workflow-regression/scripts/regression.py skills/workflow-regression/scripts/tiers.py
# reads: skills/workflow-regression/scripts/lanes.py skills/workflow-regression/scripts/slots.py
# reads: skills/workflow-delivery/scripts/lane.py skills/workflow-setup/scripts/setup.py skills/workflow-delivery/scripts/ skills/workflow-regression/scripts/
# Proves the goal tier (REG-4, tiers.py) and `run --kind` (A1e): a goal lane runs only the rows the branch's change
# reaches, new rows, root runners and a usable record's failures; an unmapped or deleted path is a Note at every lane and
# picks the rows that name it and the runners, never a full run; no merge-base is FULL (the budget cuts it); a record is
# reused only on the same merge-base; the LANE line's ROWS counts match its log; the lane's own limit follows
# test_budget_minutes. A toy repo with a bare origin; the real
# regression.py and lane run. No model is called. usage: test-tiers.sh [DIR]
set -u
here=$(cd "$(dirname "$0")/../.." && pwd)
. "$here/dev/toy/reap.sh"
unset GITHUB_SERVER_URL GITHUB_REPOSITORY GITHUB_RUN_ID LOOP_SESSION_TOOL LOOP_OPERATION_SESSION GH_TOKEN GITHUB_TOKEN
unset _LOOP_LANE_LABEL _LOOP_LANE_HELD _LOOP_LANE_STARTED _LOOP_LANE_QUEUED _LOOP_LANE_NOTE LOOP_LANE_LIMIT LANES_WIDE
export HOME=$(mktemp -d)
d=${1:-$(mktemp -d)}; rm -rf "$d"; mkdir -p "$d"
[ -n "${1:-}" ] || toy_on_exit 'rm -rf "$d" "$HOME"'
"$here/dev/toy/make.sh" "$d" >/dev/null || exit 1
export LOOP_FLOW="$d/flow.json" LOOP_LANES_DIR="$d/lanes" PATH="$here/dev/toy/fakegh:$PATH" FAKE_GH_DIR="$d/gh" TOY_LOG="$d/ran.log"
export LOOP_ROLE=worker
echo '{"limit": 600}' > "$LOOP_FLOW"
S="$here/skills/workflow-delivery/scripts"; reg="python3 $here/skills/workflow-regression/scripts/regression.py"
cd "$d/repo" || exit 1
python3 "$here/skills/workflow-setup/scripts/setup.py" --bare >/dev/null
git switch -q main; git merge -q --no-edit workflow-setup
RUNS="$(git rev-parse --git-common-dir)/loop/runs"; mkdir -p "$RUNS"; RUNS=$(cd "$RUNS" && pwd)
common=$(cd "$(git rev-parse --git-common-dir)" && pwd)
fails=0
ok() { echo "PASS: $1"; }
bad() { echo "FAIL: $1"; fails=$((fails + 1)); }
check() { if eval "$2" 2>/dev/null; then ok "$1"; else bad "$1"; [ -z "${out:-}" ] || head -8 <<<"$out" | sed "s/^/    out: /"; fi; }
ran() { sort "$TOY_LOG" 2>/dev/null | tr '\n' ' '; }
fresh() { : > "$TOY_LOG"; }
goal() { fresh; _LOOP_LANE_LABEL="repo/$1 $2" $reg run land --reuse --tier goal 2>&1; }
branch() { git switch -q main; git switch -q -c "$1"; }

# a reads src/a.txt; b, k (defect) and w (workflow) read src/b.txt; c names no path (a root runner); old.txt no row reads.
mkdir -p dev src
printf 'ok\n' > src/a.txt; printf 'ok\n' > src/b.txt; printf 'old\n' > old.txt
printf 'echo a >> "$TOY_LOG"; grep -q ok src/a.txt  # old.txt\n' > dev/a.sh
printf 'grep -q ok src/b.txt && echo "$1" >> "$TOY_LOG"\n' > dev/b.sh
printf '# id\tlevel\tcommand\tgoal\tseen_red\tdescription\tcategory\tlink\n' > .loop/regression.tsv
printf 'a\tland\tbash dev/a.sh\tX-1\t2026-01-01\tA works.\tcriterion\t\n' >> .loop/regression.tsv
printf 'b\tland\tbash dev/b.sh b\tX-1\t2026-01-01\tB works.\tcriterion\t\n' >> .loop/regression.tsv
printf 'c\tland\techo c >> "$TOY_LOG"\tX-1\t2026-01-01\tC works.\tcriterion\t\n' >> .loop/regression.tsv
printf 'k\tland\tbash dev/b.sh k\t\t2026-01-01\tK stays fixed.\tdefect\tfinding:k\n' >> .loop/regression.tsv
printf 'w\tland\tbash dev/b.sh w\tX-1\t2026-01-01\tW flows.\tworkflow\t\n' >> .loop/regression.tsv
git add -A; git commit -qm "Rows"; git push -q origin main

echo "== run --kind (A1e)"
# Value: protects=the owner runs one kind of test (A1e); fails_when=--kind is ignored or requirement is not category criterion; why_new=no kind filter existed; seam=none; no_claim=the workflow kind's add/sync support (A2)
fresh; $reg run land --kind defect >/dev/null 2>&1; k=$(ran)
fresh; $reg run land --kind workflow >/dev/null 2>&1; w=$(ran)
fresh; $reg run land --kind requirement >/dev/null 2>&1; r=$(ran)
check "run --kind filters rows by kind: defect, workflow, requirement (category criterion)" '[ "$k" = "k " ] && [ "$w" = "w " ] && [ "$r" = "a b c " ]'
git checkout -q -- .loop 2>/dev/null; git clean -fdq .loop

echo "== an unmapped change: a Note, and the rows that name it and the runners, at qa and at pr alike"
branch t1; printf 'ok, t1\n' > src/a.txt; mkdir -p notes; echo x > notes/x.txt; git add -A; git commit -qm "t1"
out=$(goal t1 qa); qa_ran=$(ran)
# Value: protects=a goal lane is never FULL for an unmapped path and says so as a Note (A1a, S17, DX-15, REG-7); fails_when=tiers forces FULL or prints Fix:; why_new=no tier test existed; seam=none; no_claim=real CI's scheduled full run
check "an unmapped change at qa runs AFFECTED rows only, with the UNMAPPED Note and no Fix" 'grep -q "^AFFECTED 2 of 5 rows (a, c)" <<<"$out" && grep -qx "UNMAPPED notes/x.txt: no row declares it. Note: the rows that name it and the runners run; declare it in the # reads: header of the row that tests it to map it" <<<"$out" && ! grep -q "Fix:" <<<"$out" && grep -q "^SELECTED a: reaches src/a.txt" <<<"$out" && grep -q "^SELECTED c: root runner" <<<"$out" && [ "$qa_ran" = "a c " ]'
out=$(goal t1 pr)
# Value: protects=the pr lane never runs the full suite for an unmapped path (REG-7); fails_when=tiers makes the pr lane FULL again; why_new=the pr lane was FULL for it; seam=none; no_claim=real CI (a local bare origin stands in)
check "the same unmapped change at pr is never FULL: it still names the Note and reuses what qa just ran" '! grep -q "^FULL" <<<"$out" && grep -q "^UNMAPPED notes/x.txt" <<<"$out" && grep -q "^REUSED 5 rows" <<<"$out" && [ -z "$(ran)" ]'

echo "== a deleted path: a Note, and the rows that name it and the runners, at qa and at pr"
branch t2; git rm -q old.txt; git commit -qm "t2"
out=$(goal t2 qa); qa_out=$out; qa_ran=$(ran); out2=$(goal t2 pr); pr_ran=$(ran); out=$out2
# Value: protects=a deleted file picks the rows that name it plus the runners at every lane, never a full run (V1, DX-11, REG-7); fails_when=a deleted path forces FULL, or the row that names it is skipped; why_new=deleted paths forced FULL at pr; seam=none; no_claim=renames (git diff --no-renames lists them as delete plus add)
check "a deleted path at qa and at pr: AFFECTED with the deleted UNMAPPED Note; the row that names it and the runner run, no FULL at pr either" '! grep -q "^FULL" <<<"$qa_out$out2" && grep -q "^REUSED 5 rows" <<<"$out2" && grep -q "^AFFECTED 2 of 5" <<<"$qa_out" && grep -qx "UNMAPPED old.txt: deleted. Note: the rows that name it and the runners run" <<<"$qa_out" && grep -q "^SELECTED a: names an unmapped path" <<<"$qa_out" && [ "$qa_ran" = "a c " ] && [ -z "$pr_ran" ]'

echo "== no merge-base: FULL"
git switch -q main; git checkout -q --orphan lone; git commit -qm "No shared history"
out=$(goal lone qa)
# Value: protects=a goal lane that can't compute a merge-base runs everything (S22); fails_when=tiers plans from nothing and runs no row; why_new=goal tier is new; seam=none; no_claim=a real shallow clone (an orphan branch stands in)
check "no merge-base with the base branch is FULL (no merge-base with <base>) and runs every row" 'grep -q "^FULL (no merge-base with main): " <<<"$out" && [ "$(ran)" = "a b c k w " ]'

echo "== a record is reused only on the same merge-base"
branch t3; printf 'ok, t3\n' > src/a.txt; git commit -qam "t3"
goal t3 qa >/dev/null; out=$(goal t3 ship)
rec=$(ls "$common"/loop/tests/t3-*.json)
# Value: protects=a usable record (same merge-base) reuses every row (S10); fails_when=the record's merge_base is not saved or not compared; why_new=records had no merge-base; seam=none; no_claim=none beyond protects
check "a record on the same merge-base reuses every row and runs none" 'grep -q "^REUSED 5 rows from" <<<"$out" && [ -z "$(ran)" ] && [ "$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))[\"merge_base\"])" "$rec")" = "$(git merge-base HEAD origin/main)" ]'
python3 -c "import json,sys;p=sys.argv[1];d=json.load(open(p));d['rows']['a']['status']='FAIL';json.dump(d,open(p,'w'))" "$rec"
out=$(goal t3 ship)
check "a usable record's FAIL row reruns alone (failure rerun)" 'grep -q "^SELECTED a: failure rerun" <<<"$out" && [ "$(ran)" = "a " ]'
git clone -q "$d/origin.git" "$d/other"; (cd "$d/other" && git config user.email t@example.test && git config user.name Toy \
  && printf 'ok from base\n' > src/b.txt && git commit -qam "Base changes b" && git push -q origin main)
git fetch -q origin; git merge -q --no-edit origin/main
out=$(goal t3 pr)
# Value: protects=a record from before a base merge is not reused; the rows the merge changed and the goal's rows rerun (S10, A1c); fails_when=the record is reused across a merge-base change; why_new=records had no merge-base; seam=none; no_claim=GitHub's merge (a local merge stands in)
check "a record from before a base merge is not reused: the rows the base changed and the goal's rows rerun" '! grep -q "^REUSED" <<<"$out" && grep -q "^SELECTED b: reaches src/b.txt" <<<"$out" && grep -q "^SELECTED a: reaches src/a.txt" <<<"$out" && [ "$(ran)" = "a b c k w " ] && [ "$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))[\"merge_base\"])" "$rec")" = "$(git merge-base HEAD origin/main)" ]'

echo "== the LANE line's ROWS summary matches its log"
cat > "$d/h.py" <<'PY'
# Call the real lane, polling until it ends; print its status and LANE line.
import json, sys, time
sys.path.insert(0, sys.argv[1]); import lane
for _ in range(600):
    status, line, _ = lane.lane(sys.argv[2], sys.argv[3], sys.argv[4], lane.flow_spec(), json.load(open(".loop/config.json")), 1)
    if status != "running":
        break
print(status); print(line)
PY
git switch -q main; git pull -q --no-edit origin main; branch t5; printf 'ok, t5\n' > src/a.txt; mkdir -p notes; echo y > notes/y.txt
printf 'n\tland\techo n >> "$TOY_LOG"\tX-1\t2026-01-01\tN is new.\tcriterion\t\n' >> .loop/regression.tsv
git add -A; git commit -qm "t5"
out=$(python3 "$d/h.py" "$S" "$RUNS" t5 qa 2>&1); log="$RUNS/t5.qa-lane.txt"
line=$(grep -m1 "^LANE qa" <<<"$out")
want="rows: $(grep -c "^SELECTED" "$log") selected ($(grep -c "^SELECTED [^:]*: reaches" "$log") affected, $(grep -c "^SELECTED [^:]*: new row" "$log") new, $(grep -c "^SELECTED [^:]*: root runner" "$log") root runners, $(grep -c "^SELECTED [^:]*: failure rerun" "$log") failure reruns), 3 reused, 0 unfinished; unmapped: $(grep -c "^UNMAPPED" "$log"); log: $log"
# Value: protects=the LANE line says what ran and why, with the log path (DX-12, DX-18 ROWS); fails_when=the summary is missing or its counts drift from the log's per-row reasons; why_new=LANE lines had no row summary; seam=none; no_claim=none beyond protects
check "the LANE line ends with the ROWS summary and log path, and its counts match the log's SELECTED reasons" 'grep -qx pass <<<"$out" && [ "${line#*; rows: }" = "${want#rows: }" ] && grep -q "rows: 3 selected (1 affected, 1 new, 1 root runners, 0 failure reruns), 3 reused, 0 unfinished; unmapped: 1; log: " <<<"$line"'

echo "== the lane's own limit follows test_budget_minutes"
branch t4; mkdir -p notes; echo z > notes/z.txt; git add -A; git commit -qm "t4"
echo '{}' > "$LOOP_FLOW"
python3 - "$S" "$RUNS" <<'PY' > "$d/t4.out" 2>&1
import json, sys
sys.path.insert(0, sys.argv[1]); import lane
lane.lane(sys.argv[2], "t4", "qa", lane.flow_spec(), json.load(open(".loop/config.json")), 0)
held = json.load(open(sys.argv[2] + "/t4.qa-lane.job"))
print("LIMIT %d %s" % (held["limit"], held.get("source")))
PY
echo '{"limit": 600}' > "$LOOP_FLOW"
out=$(cat "$d/t4.out")
# Value: protects=the lane's own time limit is test_budget_minutes plus five minutes when no flow file limit is shorter (REG-7); fails_when=the lane keeps the 45-minute default or ignores the setting; why_new=the lane limit ignored test_budget_minutes; seam=none; no_claim=a real 15-minute lane
check "with no flow file limit the lane limit is test_budget_minutes + 300 s, sourced to the setting" 'grep -qx "LIMIT 1200 test_budget_minutes" <<<"$out"'

echo "== goal_levels and goal_lane_minutes (S23, S21)"
git switch -q main; branch t6
python3 -c "import json;c=json.load(open('.loop/config.json'));c.update(goal_levels='nightly',goal_lane_minutes=0.0001);json.dump(c,open('.loop/config.json','w'),indent=2)"
printf 'm\tnightly\tgrep -q ok src/a.txt && echo m >> "$TOY_LOG"\tX-1\t2026-01-01\tM runs nightly.\tcriterion\t\n' >> .loop/regression.tsv
git add -A; git commit -qm "t6 rows"; printf 'ok, t6\n' > src/a.txt; git commit -qam "t6"
out=$(python3 "$d/h.py" "$S" "$RUNS" t6 qa 2>&1)
# Value: protects=goal_levels nightly makes a goal lane plan from land and nightly rows (S23) and a lane over goal_lane_minutes says so on its LANE line (S21); fails_when=the setting is ignored or the note is missing; why_new=both settings are new; seam=none; no_claim=a real 10-minute lane (0.0001 min stands in)
check "goal_levels nightly: a goal lane selects the nightly row a change reaches" 'grep -q "^SELECTED m: " "$RUNS/t6.qa-lane.txt"'
check "a goal lane over goal_lane_minutes adds '; over N min (goal_lane_minutes)' to its LANE line" 'grep -q "^LANE qa AFFECTED .*; over 0.0001 min (goal_lane_minutes)" <<<"$out"'
t0=$(date +%s); rr=$(python3 -c "import sys;sys.path.insert(0,sys.argv[1]);import lanes;print(lanes.run_row('sleep 20 & echo \$! > $d/left.pid; exec sleep 20','.',None,1)[0])" "$here/skills/workflow-regression/scripts"); took=$(( $(date +%s) - t0 ))
# Value: protects=a row's timeout holds even when its shell left a child holding the output (red team); fails_when=run_row waits for the pipe to close; why_new=run_row is new; seam=none; no_claim=none beyond protects
check "a row past its timeout returns 124 within seconds and its whole tree is killed, the child it started too" '[ "$rr" = 124 ] && [ $took -lt 10 ] && ! kill -0 "$(cat "$d/left.pid")" 2>/dev/null'
kill "$(cat "$d/left.pid")" 2>/dev/null  # only the child this check left, if it survived

[ "$fails" = 0 ] && echo "ALL PASS" || { echo "$fails FAILED"; exit 1; }
