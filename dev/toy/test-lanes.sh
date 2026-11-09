#!/bin/bash
# Proves regression.py run --reuse: a goal's suite runs once, then later runs reuse it, rerun only the rows a change can
# affect, and never reuse a failing or missing run. Then delivery's lanes: qa runs the lane before the qa skill (through
# the flow file's test_record prefix), record refuses qa without it, and pr reruns only what a base merge affected.
# No model is called. usage: test-lanes.sh [DIR] [regression|delivery]
set -u
unset LOOP_SESSION_TOOL LOOP_OPERATION_SESSION GH_TOKEN GITHUB_TOKEN
here=$(cd "$(dirname "$0")/../.." && pwd)
export HOME=$(mktemp -d)
d=${1:-$(mktemp -d)}; rm -rf "$d"; mkdir -p "$d"
part=${2:-all}
"$here/dev/toy/make.sh" "$d" >/dev/null || exit 1
export LOOP_FLOW="$d/flow.json" PATH="$here/dev/toy/fakegh:$PATH" FAKE_GH_DIR="$d/gh" TOY_LOG="$d/ran.log"
reg="python3 $here/skills/workflow-regression/scripts/regression.py"
cd "$d/repo" || exit 1
python3 "$here/skills/workflow-setup/scripts/setup.py" --bare >/dev/null
git switch -q main; git merge -q --no-edit workflow-setup
fails=0
ok() { echo "PASS: $1"; }
bad() { echo "FAIL: $1"; fails=$((fails + 1)); }
check() { if eval "$2"; then ok "$1"; else bad "$1"; fi; }
ran() { sort "$TOY_LOG" 2>/dev/null | tr '\n' ' '; }
fresh() { : > "$TOY_LOG"; }
common=$(cd "$(git rev-parse --git-common-dir)" && pwd)

# Three rows: a reads src/a.txt, b sources dev/lib.sh which reads src/b.txt, c names no repo path (always runs).
mkdir -p dev src
printf 'ok\n' > src/a.txt; printf 'ok\n' > src/b.txt
printf 'echo a >> "$TOY_LOG"; grep -q ok src/a.txt\n' > dev/a.sh
printf '. dev/lib.sh\necho b >> "$TOY_LOG"\n' > dev/b.sh
printf 'grep -q ok src/b.txt || exit 1\n' > dev/lib.sh
printf '# id\tlevel\tcommand\tgoal\tseen_red\tdescription\tcategory\tlink\n' > .loop/regression.tsv
printf 'a\tland\tbash dev/a.sh\tX-1\t2026-01-01\tA works.\tcriterion\t\n' >> .loop/regression.tsv
printf 'b\tland\tbash dev/b.sh\tX-1\t2026-01-01\tB works.\tcriterion\t\n' >> .loop/regression.tsv
printf 'c\tnightly\techo c >> "$TOY_LOG"\tX-1\t2026-01-01\tC works.\tcriterion\t\n' >> .loop/regression.tsv
git add -A; git commit -qm "Rows"; git push -q origin main

if [ "$part" != delivery ]; then
echo "== the first run runs everything and records it"
fresh; out=$($reg run land --reuse); rc=$?; echo "$out"
check "first run is full (no record)" '[ $rc = 0 ] && grep -q "^FULL: no record" <<<"$out" && [ "$(ran)" = "a b " ]'
check "the record holds each row with its commit" 'ls "$common"/loop/tests/main-*.json >/dev/null 2>&1 && grep -q "\"commit\"" "$common"/loop/tests/main-*.json'
before=$(git status --porcelain)
fresh; out=$($reg run land --reuse); rc=$?; echo "$out"
check "unchanged content reuses every row and runs none" '[ $rc = 0 ] && grep -q "^REUSED 2 rows from" <<<"$out" && [ -z "$(ran)" ]'
check "the result line counts reused rows, never zero tests" 'grep -q "^RESULT 2 passed (2 reused)" <<<"$out"'
check "a reusing run leaves git status unchanged" '[ "$(git status --porcelain)" = "$before" ]'

echo "== a change reruns only the rows it can affect"
printf 'ok now\n' > src/a.txt; git commit -qam "Change a"
fresh; out=$($reg run land --reuse); echo "$out"
check "a change to a's input reruns only a" 'grep -q "^AFFECTED 1 of 2 rows (a)" <<<"$out" && [ "$(ran)" = "a " ]'
printf 'grep -q ok src/b.txt || exit 1\n# touched\n' > dev/lib.sh; git commit -qam "Change lib"
fresh; out=$($reg run land --reuse); echo "$out"
check "a change to a file reached only through a sourced script reruns that row" '[ "$(ran)" = "b " ]'
fresh; out=$($reg run c --reuse); out2=$($reg run c --reuse)
check "a row whose command names no repo path always reruns" '[ "$(ran)" = "c c " ]'

echo "== a run on top of a partial run: each row keeps its own commit"
printf 'ok again\n' > src/b.txt; git commit -qam "Change b"
fresh; $reg run a --reuse >/dev/null; fresh; out=$($reg run land --reuse); echo "$out"
check "b reruns after a partial run of a moved the record's commit" 'grep -q "b" <<<"$(ran)"'

echo "== a failing or missing run is never reused"
printf 'bad\n' > src/a.txt; git commit -qam "Break a"
fresh; out=$($reg run land --reuse 2>&1); rc=$?; echo "$out"
check "a failing row fails the run and prints its output" '[ $rc = 1 ] && grep -q "^FAIL a" <<<"$out"'
printf 'ok\n' > src/a.txt; git commit -qam "Fix a"
fresh; out=$($reg run land --reuse); echo "$out"
check "a record with a FAIL row means a full run" 'grep -q "^FULL: record has FAIL rows a" <<<"$out" && [ "$(ran)" = "a b " ]'
rm -f "$common"/loop/tests/main-*.json
fresh; out=$($reg run land --reuse); echo "$out"
check "a missing record means a full run" 'grep -q "^FULL: no record" <<<"$out" && [ "$(ran)" = "a b " ]'
echo "{broken" > "$(ls "$common"/loop/tests/main-*.json)"
fresh; out=$($reg run land --reuse); echo "$out"
check "an unreadable record means a full run" 'grep -q "^FULL: record unreadable" <<<"$out" && [ "$(ran)" = "a b " ]'

echo "== uncommitted work is tested but never recorded"
rec=$(ls "$common"/loop/tests/main-*.json); sum=$(cksum < "$rec")
printf 'ok dirty\n' > src/a.txt
fresh; out=$($reg run land --reuse); echo "$out"
check "a dirty tree reruns its changed rows and is not recorded" 'grep -q "^NOT RECORDED: uncommitted changes" <<<"$out" && [ "$(ran)" = "a " ] && [ "$(cksum < "$rec")" = "$sum" ]'
git checkout -q -- src/a.txt

echo "== unmapped files, new rows, the known list and unproven rows"
printf 'echo new\n' > dev/new.sh; git add dev/new.sh; git commit -qm "New dev file"
fresh; out=$($reg run land --reuse); echo "$out"
check "a new file under dev/ no row reads forces a full run" 'grep -q "^UNMAPPED dev/new.sh: full run" <<<"$out" && [ "$(ran)" = "a b " ]'
printf 'd\tland\techo d >> "$TOY_LOG"; cat dev/a.sh >/dev/null\tX-1\t2026-01-01\tD works.\tcriterion\t\n' >> .loop/regression.tsv
git commit -qam "Row d"
fresh; out=$($reg run land --reuse); echo "$out"
check "a row absent from the record runs; the others are reused" '[ "$(ran)" = "d " ]'
printf 'b\tbeing fixed\n' > .loop/regression-known.tsv; git add -A; git commit -qm "Known b"
fresh; out=$($reg run land --reuse); echo "$out"
check "a changed known-list entry reruns that row" '[ "$(ran)" = "b " ]'
printf 'e\tland\tbash dev/a.sh\tX-1\t\tE works.\tcriterion\t\n' >> .loop/regression.tsv; git commit -qam "Row e"
$reg run land --reuse >/dev/null; fresh; out=$($reg run land --reuse); rc=$?; echo "$out"
check "a row never seen failing fails the run even when reused" '[ $rc = 1 ] && grep -q "^UNPROVEN e: never seen failing. Fix: python3 .* red e --break" <<<"$out"'
grep -v "^e	" .loop/regression.tsv > "$d/rows" && cat "$d/rows" > .loop/regression.tsv && git commit -qam "Drop row e"
fi

if [ "$part" != regression ]; then
echo "== delivery: qa runs the lane before the qa skill, through the flow file's test_record"
export LOOP_ROLE=worker TOY_RECEIPTS="$d/receipts"
goal="python3 $here/skills/workflow-delivery/scripts/goal.py"; F="python3 $here/skills/workflow-delivery/scripts/flow.py"
lane=$(python3 -c "import sys; sys.path.insert(0, sys.argv[1]); import role; print(role.lane_text())" "$here/skills/workflow-delivery/scripts")
cat > "$d/recorder.sh" <<'A'
#!/bin/bash
# A stand-in receipt recorder: it notes the label, the commit and the exact command, then runs it and passes its status.
printf 'label=regression\tcommit=%s\tcommand=%s\n' "$(git rev-parse HEAD)" "$*" >> "$TOY_RECEIPTS"
"$@"
A
python3 - "$d/flow.json" "$d/recorder.sh" <<'PY'
import json, sys
spec = json.load(open(sys.argv[1])); spec["test_record"] = ["bash", sys.argv[2]]; json.dump(spec, open(sys.argv[1], "w"))
PY
git switch -q main; git push -q origin main
step() { all=""; for _ in $(seq 20); do out=$($F "$1" "$2" --wait 10 2>&1); all="$all$out"$'\n'; grep -q "^NEXT:" <<<"$out" && break; done
         echo "$all"; $goal record "$1" "$2" --file "$common/loop/runs/$1.$2.txt" 2>&1; }
$goal new lg --here --goal "Lane goal" --done "lanes work" >/dev/null
for s in idea plan review; do step lg $s >/dev/null; done
out=$($goal record lg qa --file "$d/flow.json" 2>&1)
check "record refuses qa before the qa lane passed on HEAD" 'grep -q "the qa lane has not passed on .* (LANE_MISSING)" <<<"$out"'
check "the lane command resolves from the installed package, not the repo (no skills/ here)" '[ ! -e skills ] && grep -q "^python3 $here/skills/workflow-regression/scripts/regression.py run land --reuse$" <<<"$lane"'
out=$(step lg qa); echo "$out"
check "qa runs the lane first: a full run on a branch with no record" 'grep -q "^LANE qa FULL \([0-9]*\)/\1 " <<<"$out" && grep -q "^FULL: no record" "$common/loop/runs/lg.qa-lane.txt"'
check "the recorder got the exact lane command on the tested commit" 'grep -qF "commit=$(git rev-parse HEAD)	command=$lane" "$TOY_RECEIPTS"'
check "qa is recorded once its lane passed" 'grep -q "^RECORDED qa" <<<"$out"'
out=$(step lg ship); echo "$out"
check "ship reuses qa's run on unchanged content and runs no row" 'grep -q "^LANE ship REUSED 0/" <<<"$out" && grep -q "^REUSED [0-9]* rows" "$common/loop/runs/lg.ship-lane.txt"'

echo "== pr: a base merge reruns only the rows it affected"
git clone -q "$d/origin.git" "$d/other"; (cd "$d/other" && git config user.email t@example.test && git config user.name Toy \
  && printf 'ok from base\n' > src/b.txt && git commit -qam "Base changes b" && git push -q origin main)
out=$($goal pr lg 2>&1); echo "$out"
check "pr merges the base and reruns only the row the merge affected" 'grep -q "^MERGED" <<<"$out" && grep -q "^AFFECTED 1 of [0-9]* rows (b)" "$common/loop/runs/lg.pr-lane.txt" && grep -q "^PR " <<<"$out"'

echo "== a red lane never starts the skill and costs a try"
git switch -q main; $goal new lf --here --goal "Red goal" --done "red" >/dev/null
printf 'bad\n' > src/a.txt; git commit -qam "Break a"
for s in idea plan review; do step lf $s >/dev/null; done
out=$(step lf qa); echo "$out"
check "a failing qa lane fails the step with its row ids, before any skill ran" 'grep -q "LANE_FAIL a" <<<"$out" && grep -q "TRY 1 OF 3 FAILED: qa failed: regression lane: a" <<<"$out" && grep -q "^STEP: failed regression lane: a" "$common/loop/runs/lf.qa.txt"'
touch stray.txt
out=$(python3 "$here/skills/workflow-delivery/scripts/role.py" lane lf qa 2>&1)
check "the lane refuses an unclean tree" 'grep -q "LANE_DIRTY at start: stray.txt" <<<"$out"'
rm -f stray.txt
fi

[ $fails = 0 ] && echo "ALL PASS" || { echo "$fails FAILED"; exit 1; }
