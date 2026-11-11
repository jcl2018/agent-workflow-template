#!/bin/bash
# reads: skills/workflow-regression/scripts/regression.py skills/workflow-regression/scripts/tiers.py
# reads: skills/workflow-regression/scripts/lanes.py skills/workflow-regression/scripts/slots.py
# reads: skills/workflow-delivery/scripts/lane.py skills/workflow-setup/scripts/setup.py skills/workflow-delivery/scripts/
# Proves the goal tier (REG-4, tiers.py) and `run --kind` (A1e): a goal lane runs only the rows the branch's change
# reaches, new rows, root runners and a usable record's failures; an unmapped or deleted path is a Note at qa and FULL
# at pr; no merge-base is FULL; a record is reused only on the same merge-base; the LANE line's ROWS counts match its
# log; a FULL goal lane times out on full_suite_minutes with FULL_TIMEOUT. A toy repo with a bare origin; the real
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
printf 'echo a >> "$TOY_LOG"; grep -q ok src/a.txt\n' > dev/a.sh
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

echo "== an unmapped change: a Note at qa, FULL at pr"
branch t1; printf 'ok, t1\n' > src/a.txt; mkdir -p notes; echo x > notes/x.txt; git add -A; git commit -qm "t1"
out=$(goal t1 qa); qa_ran=$(ran)
# Value: protects=a goal lane at qa is never FULL for an unmapped path, and says so as a Note (A1a, S17, DX-15); fails_when=tiers forces FULL at qa or prints Fix:; why_new=no tier test existed; seam=none; no_claim=real CI's scheduled full run
check "an unmapped change at qa runs AFFECTED rows only, with the UNMAPPED Note and no Fix" 'grep -q "^AFFECTED 2 of 5 rows (a, c)" <<<"$out" && grep -qx "UNMAPPED notes/x.txt: no row declares it. Note: the pr lane runs the full suite once for it; declare it in the # reads: header of the row that tests it to avoid that" <<<"$out" && ! grep -q "Fix:" <<<"$out" && grep -q "^SELECTED a: reaches src/a.txt" <<<"$out" && grep -q "^SELECTED c: root runner" <<<"$out" && [ "$qa_ran" = "a c " ]'
out=$(goal t1 pr)
# Value: protects=pr lane runs FULL for an unmapped path (V1); fails_when=tiers drops the V1 rule; why_new=no tier test exists; seam=none; no_claim=real CI (a local bare origin stands in)
check "the same unmapped change at pr is FULL (unmapped <path> at pr) and runs every row" 'grep -qx "FULL (unmapped notes/x.txt at pr): no row declares notes/x.txt, so the pr lane runs the full suite once" <<<"$out" && [ "$(ran)" = "a b c k w " ]'

echo "== a deleted path: a Note at qa, FULL at pr"
branch t2; git rm -q old.txt; git commit -qm "t2"
out=$(goal t2 qa); qa_out=$out; out2=$(goal t2 pr)
# Value: protects=a deleted file is advisory at qa and FULL at pr (V1, DX-11); fails_when=deleted paths force FULL at qa or are skipped at pr; why_new=deleted paths had only the old FULL rule; seam=none; no_claim=renames (git diff --no-renames lists them as delete plus add)
check "a deleted path at qa: AFFECTED with the deleted UNMAPPED Note; at pr: FULL (deleted <path>)" 'grep -q "^AFFECTED" <<<"$qa_out" && grep -qx "UNMAPPED old.txt: deleted. Note: the pr lane runs the full suite once for it" <<<"$qa_out" && grep -q "^FULL (deleted old.txt): " <<<"$out2"'

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

echo "== a FULL goal lane times out on full_suite_minutes"
branch t4; python3 -c "import json;c=json.load(open('.loop/config.json'));c['full_suite_minutes']=0.05;json.dump(c,open('.loop/config.json','w'),indent=2)"
printf 's\tland\tsleep 27; echo s >> "$TOY_LOG"\tX-1\t2026-01-01\tS is slow.\tcriterion\t\n' >> .loop/regression.tsv
mkdir -p notes; echo z > notes/z.txt; git add -A; git commit -qm "t4"
began=$(date +%s); python3 "$S/lane.py" lane t4 pr > "$d/t4.out" 2> "$d/t4.err"; rc=$?; took=$(( $(date +%s) - began )); sleep 1
out=$(cat "$d/t4.out" "$d/t4.err")
# Value: protects=a FULL goal lane runs on full_suite_minutes and its timeout is FULL_TIMEOUT, not retried (DX-16); fails_when=the lane keeps the flow file limit or prints the retryable LANE_TIMEOUT; why_new=FULL goal lanes are new; seam=none; no_claim=a real 30-minute suite (0.05 min stands in)
check "a FULL goal lane past full_suite_minutes fails with FULL_TIMEOUT (exit 124), long before the flow limit" '[ $rc = 124 ] && grep -q "^LANE pr FULL (unmapped [^)]* at pr) " "$d/t4.err" && grep -qx "LANE_TIMEOUT (FULL_TIMEOUT): the full suite passed its 0.05 min limit; not retryable by the worker. Fix: the owner raises full_suite_minutes or narrows rows; rerunning times out again" "$d/t4.err" && grep -q "[1-9][0-9]* unfinished" "$d/t4.err" && [ $took -lt 60 ] && ! pgrep -f "^sleep 27$" >/dev/null'

[ "$fails" = 0 ] && echo "ALL PASS" || { echo "$fails FAILED"; exit 1; }
