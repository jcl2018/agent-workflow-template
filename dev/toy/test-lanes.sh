#!/bin/bash
# reads: skills/workflow-delivery/scripts/flow.py skills/workflow-delivery/scripts/goal.py
# reads: skills/workflow-delivery/scripts/role.py skills/workflow-regression/scripts/regression.py
# reads: skills/workflow-setup/scripts/setup.py skills/workflow-regression/scripts/lanes_cli.py
# reads: skills/workflow-regression/scripts/lanes.py skills/workflow-regression/scripts/narrow.py
# Proves regression.py run --reuse: a goal's suite runs once, then later runs reuse it, rerun only the rows a change can
# affect, and never reuse a failing or missing run. Then delivery's lanes: qa runs the lane before the qa skill (through
# the flow file's test_record prefix), record refuses qa without it, and pr reruns only what a base merge affected.
# Then narrow rows: # reads: headers map a change to only the rows whose closure reaches it, and anything the mapping
# cannot work out reruns every time. No model is called. usage: test-lanes.sh [DIR] [regression|delivery|narrow]
set -u
unset LOOP_SESSION_TOOL LOOP_OPERATION_SESSION GH_TOKEN GITHUB_TOKEN
here=$(cd "$(dirname "$0")/../.." && pwd)
export HOME=$(mktemp -d)
d=${1:-$(mktemp -d)}; rm -rf "$d"; mkdir -p "$d"
[ -n "${1:-}" ] || trap 'rm -rf "$d" "$HOME"' EXIT
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
# Value: protects=a lane on a repo with no rows passes; fails_when=--reuse with no rows exits non-zero like a plain run;
# why_new=every other run has rows; seam=none; no_claim=none beyond protects
out=$($reg run land --reuse); rc=$?
check "a reusing run with no rows passes (NO ROWS, exit 0)" '[ $rc = 0 ] && grep -q "^NO ROWS: nothing to run" <<<"$out"'

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

if [ "$part" = all ] || [ "$part" = regression ]; then
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
python3 -c "import json,sys;p=sys.argv[1];r=json.load(open(p));r['worktree']='/elsewhere';json.dump(r,open(p,'w'))" "$(ls "$common"/loop/tests/main-*.json)"
fresh; out=$($reg run land --reuse); echo "$out"
check "a record from another worktree means a full run" 'grep -q "^FULL: record from another worktree" <<<"$out" && [ "$(ran)" = "a b " ]'
# Value: protects=a record made by another regression.py/lanes.py is never reused; fails_when=the runner hash check is
# dropped; why_new=no check edits the runner field; seam=none; no_claim=a real code change to the runner (field edited)
python3 -c "import json,sys;p=sys.argv[1];r=json.load(open(p));r['runner']='older';json.dump(r,open(p,'w'))" "$(ls "$common"/loop/tests/main-*.json)"
fresh; out=$($reg run land --reuse); echo "$out"
check "a record from another runner version means a full run" 'grep -q "^FULL: record schema/runner changed" <<<"$out" && [ "$(ran)" = "a b " ]'

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
# Value: protects=editing an existing row's line reruns that row only; fails_when=regression.tsv is diffed by id only or
# treated as no change; why_new=only an added row is tested; seam=none; no_claim=rows that reach regression.py itself
awk -F'\t' 'BEGIN {OFS = FS} $1 == "b" {$6 = "B still works."} {print}' .loop/regression.tsv > "$d/rows" && cat "$d/rows" > .loop/regression.tsv
git commit -qam "Edit row b"
fresh; out=$($reg run land --reuse); echo "$out"
check "an edited row reruns only that row" '[ "$(ran)" = "b " ]'
# Value: protects=any regression.tsv edit reruns rows that reach regression.py; fails_when=the RUNNER clause is dropped
# from the regression.tsv rule; why_new=no toy row reached the runner; seam=none; no_claim=the real runner (toy stand-in)
mkdir -p skills/workflow-regression/scripts; echo 'print(1)' > skills/workflow-regression/scripts/regression.py
printf 'f\tland\tpython3 skills/workflow-regression/scripts/regression.py; echo f >> "$TOY_LOG"\tX-1\t2026-01-01\tF.\tcriterion\t\n' >> .loop/regression.tsv
git add -A; git commit -qm "Row f"; $reg run land --reuse >/dev/null
awk -F'\t' 'BEGIN {OFS = FS} $1 == "b" {$6 = "B again."} {print}' .loop/regression.tsv > "$d/rows" && cat "$d/rows" > .loop/regression.tsv
git commit -qam "Edit row b again"
fresh; out=$($reg run land --reuse); echo "$out"
check "a regression.tsv edit also reruns a row that reaches regression.py" '[ "$(ran)" = "b f " ]'
grep -v "^f	" .loop/regression.tsv > "$d/rows" && cat "$d/rows" > .loop/regression.tsv && git rm -rqf skills && git commit -qam "Drop row f"
# Value: protects=a python row reruns when a module it imports changes, not everything; fails_when=scan stops following
# imports; why_new=only shell sourcing is tested; seam=none; no_claim=packages or relative imports (same-folder module only)
printf 'X = 1\n' > dev/helper.py; printf 'import helper\nimport os\nopen(os.environ["TOY_LOG"], "a").write("p\\n")\n' > dev/p.py
printf 'p\tland\tpython3 -B dev/p.py\tX-1\t2026-01-01\tP.\tcriterion\t\n' >> .loop/regression.tsv
git add -A; git commit -qm "Row p"; $reg run land --reuse >/dev/null
printf 'X = 2\n' > dev/helper.py; git commit -qam "Change helper"
fresh; out=$($reg run land --reuse); echo "$out"
check "a change to an imported python module reruns only the row importing it" '[ "$(ran)" = "p " ]'
grep -v "^p	" .loop/regression.tsv > "$d/rows" && cat "$d/rows" > .loop/regression.tsv && git commit -qam "Drop row p"
printf 'e\tland\tbash dev/a.sh\tX-1\t\tE works.\tcriterion\t\n' >> .loop/regression.tsv; git commit -qam "Row e"
$reg run land --reuse >/dev/null; fresh; out=$($reg run land --reuse); rc=$?; echo "$out"
check "a row never seen failing fails the run even when reused" '[ $rc = 1 ] && grep -q "^UNPROVEN e: never seen failing. Fix: python3 .* red e --break" <<<"$out"'
grep -v "^e	" .loop/regression.tsv > "$d/rows" && cat "$d/rows" > .loop/regression.tsv && git commit -qam "Drop row e"

echo "== release and loop files no row's own scripts name are no change"
printf '# notes go to CHANGELOG.md\n' >> dev/lib.sh; printf 'v1\n' > CHANGELOG.md; git add -A; git commit -qm "Lib names the changelog"
$reg run land --reuse >/dev/null; printf 'v2\n' > CHANGELOG.md; git commit -qam "Changelog"
fresh; out=$($reg run land --reuse); echo "$out"
check "a changelog-only commit reuses every row, even one reaching a file that names it" 'grep -q "^REUSED" <<<"$out" && [ -z "$(ran)" ]'
printf 'cat CHANGELOG.md >/dev/null\necho a >> "$TOY_LOG"; grep -q ok src/a.txt\n' > dev/a.sh; git commit -qam "a reads the changelog"
$reg run land --reuse >/dev/null; printf 'v3\n' > CHANGELOG.md; git commit -qam "Changelog again"
fresh; out=$($reg run land --reuse); echo "$out"
check "a row whose own script names a release file reruns when it changes" '[ "$(ran)" = "a d " ]'

echo "== rewritten history: a recorded commit that is no longer an ancestor of HEAD is never reused"
# Value: protects=results from a commit dropped by reset/rebase are rerun; fails_when=the ancestor check is removed or
# inverted; why_new=every other case moves HEAD forward; seam=none; no_claim=a real rebase (reset + new commit instead)
rm -f "$common"/loop/tests/main-*.json; $reg run land --reuse >/dev/null
git reset -q --hard HEAD~1; printf 'v4\n' > CHANGELOG.md; git commit -qam "Changelog, rewritten"
fresh; out=$($reg run land --reuse); echo "$out"
check "rows recorded on a commit no longer in HEAD's history rerun" '[ "$(ran)" = "a b d " ]'
# Value: protects=a detached HEAD runs every row and writes no record; fails_when=record_path stops returning None with no
# branch; why_new=every other run is on a branch; seam=none; no_claim=none beyond protects
n=$(ls "$common"/loop/tests | wc -l); git switch -q --detach
fresh; out=$($reg run land --reuse); echo "$out"
check "a detached HEAD is a full run and is not recorded" 'grep -q "^NOT RECORDED: detached HEAD" <<<"$out" && [ "$(ran)" = "a b d " ] && [ "$(ls "$common"/loop/tests | wc -l)" = "$n" ]'
git switch -q main
fi

if [ "$part" = all ] || [ "$part" = delivery ]; then
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
# Value: protects=only a reply record counts as a failed try skips the qa lane; fails_when=need_lane skips on any failed
# line or ignores PENDING; why_new=the refusal above has no STEP line; seam=none; no_claim=a real skill's reply
printf 'STEP: failed old\nSTEP: done\n' > "$d/q1"; printf 'PENDING: x\nSTEP: failed\n' > "$d/q2"
out=$($goal record lg qa --file "$d/q1" 2>&1; $goal record lg qa --file "$d/q2" 2>&1)
check "an earlier STEP: failed or a PENDING line never skips the qa lane" '[ "$(grep -c "(LANE_MISSING)" <<<"$out")" = 2 ]'
check "the lane command resolves from the installed package, not the repo (no skills folder here)" '[ ! -e skills ] && grep -q "^python3 $here/skills/workflow-regression/scripts/regression.py run land --reuse$" <<<"$lane"'
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
# Value: protects=a red pr lane counts a try and pushes nothing; fails_when=goal.py pr ignores or inverts the lane's fail
# status; why_new=only a green pr lane is tested; seam=none; no_claim=a real GitHub remote (fake gh, local origin)
printf 'bad\n' > src/a.txt; git commit -qam "Break a after the PR"
out=$($goal pr lg 2>&1); rc=$?; echo "$out"
check "a red pr lane fails pr with its row ids and pushes nothing" '[ $rc = 1 ] && grep -q "LANE_FAIL a" <<<"$out" && grep -q "FAILED: regression lane failed: a" <<<"$out" && [ "$(git ls-remote origin "refs/heads/$(git branch --show-current)" | cut -f1)" != "$(git rev-parse HEAD)" ]'
printf 'ok\n' > src/a.txt; git commit -qam "Fix a after the PR"

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
# Value: protects=a row that leaves files fails its lane; fails_when=the end-of-run unclean check is dropped; why_new=only
# the start check is tested; seam=none; no_claim=files a row writes outside the worktree
printf 'ok\n' > src/a.txt; printf 'litter\tland\ttouch litter.txt\tX-1\t2026-01-01\tL.\tcriterion\t\n' >> .loop/regression.tsv
git commit -qam "A littering row"; out=$(python3 "$here/skills/workflow-delivery/scripts/role.py" lane lf pr 2>&1)
check "a row that leaves a file fails the lane (LANE_DIRTY at end)" 'grep -q "^LANE_DIRTY at end: a row left litter.txt" <<<"$out"'
# Value: protects=a littering row is never saved as a pass for later reuse; fails_when=regression.py records without
# rechecking the tree after the rows; why_new=the lane check above reads only the lane line; seam=none; no_claim=none beyond protects
check "the littering run is not recorded and its old record is dropped" 'grep -q "^NOT RECORDED: the rows left uncommitted files: litter.txt; record dropped" "$common/loop/runs/lf.pr-lane.txt" && ! ls "$common"/loop/tests/*lf-*.json'
rm -f litter.txt; grep -v "^litter	" .loop/regression.tsv > "$d/rows" && cat "$d/rows" > .loop/regression.tsv

echo "== a lane's recorder, time limit and a moved HEAD"
R="python3 $here/skills/workflow-delivery/scripts/role.py"
setflow() { python3 - "$d/flow.json" "$1" <<'PY2'
import json, sys
spec = json.load(open(sys.argv[1])); spec.update(json.loads(sys.argv[2])); json.dump(spec, open(sys.argv[1], "w"))
PY2
}
slow() { pgrep -f '^sleep 23$' | wc -l | tr -d ' '; }
printf 'ok\n' > src/a.txt
printf 'slow\tland\tsleep 23; echo slow >> "$TOY_LOG"\tX-1\t2026-01-01\tSlow.\tcriterion\t\n' >> .loop/regression.tsv
git commit -qam "A slow row"
setflow '{"test_record": ["/nonexistent/recorder"]}'
out=$($R lane lf pr 2>&1)
check "a test_record command that isn't on this machine fails the lane before it starts" 'grep -q "^LANE_RECORDER" <<<"$out" && [ ! -e "$common/loop/runs/lf.pr-lane.job" ]'
setflow "{\"test_record\": [\"bash\", \"$d/recorder.sh\"], \"limit\": 2}"
out=$($R lane lf pr 2>&1); sleep 1
check "a lane past its limit fails as LANE_TIMEOUT and its whole run is stopped" 'grep -q "^LANE_TIMEOUT" <<<"$out" && [ "$(slow)" = 0 ]'
setflow '{"limit": 600}'
out=$($F lf qa --wait 1 2>&1); sleep 2
check "a slow qa lane runs in the background" 'grep -q "^RUNNING" <<<"$out" && [ "$(slow)" = 1 ]'
git commit -q --allow-empty -m "Move HEAD"
out=$($F lf qa --wait 1 2>&1); sleep 2
check "a moved HEAD stops the old lane's whole run and starts one new lane" 'grep -q "^RUNNING" <<<"$out" && [ "$(slow)" = 1 ]'
kill -TERM -- "-$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['pid'])" "$common/loop/runs/lf.qa-lane.job")" 2>/dev/null; sleep 1
fi

if [ "$part" = all ] || [ "$part" = narrow ]; then
echo "== narrow: # reads: headers map a change to the rows whose closure reaches it"
L="python3 $here/skills/workflow-regression/scripts/lanes_cli.py"
n="$d/narrow"; mkdir -p "$n/skills/a/scripts" "$n/skills/b/scripts" "$n/dev" "$n/tools" "$n/.loop"
printf 'open("data.md")\n' > "$n/skills/a/scripts/a.py"; printf 'data\n' > "$n/skills/a/scripts/data.md"
printf 'import helper\n' > "$n/skills/b/scripts/b.py"; printf 'X = 1\n' > "$n/skills/b/scripts/helper.py"
printf 'Y = 1\n' > "$n/skills/b/scripts/solo.py"; printf 'x\n' > "$n/tools/x.txt"
printf 'echo common\n' > "$n/dev/common.sh"; printf 'm=skills/b/scripts\n' > "$n/dev/tm-lib.sh"
printf '#!/bin/bash\n# reads: skills/a/scripts/a.py\n. dev/common.sh; python3 skills/a/scripts/a.py\n' > "$n/dev/ta.sh"
printf '#!/bin/bash\n# reads: skills/b/scripts/b.py\n. dev/common.sh; python3 skills/b/scripts/b.py\n' > "$n/dev/tb.sh"
printf '#!/bin/bash\n# reads: skills/b/scripts/b.py\n. dev/common.sh; . dev/tm-lib.sh\npython3 $m/b.py; python3 $m/solo.py\n' > "$n/dev/tm.sh"
printf '#!/bin/bash\n# reads: skills/a/scripts/gone.py\n. dev/common.sh\n' > "$n/dev/tx.sh"
printf '#!/bin/bash\n# reads: skills/a/scripts/a.py\n. dev/common.sh; ls skills/b/scripts >/dev/null; python3 skills/a/scripts/a.py\n' > "$n/dev/tf.sh"
printf '#!/bin/bash\n. dev/common.sh; python3 skills/a/scripts/a.py\n' > "$n/dev/tu.sh"
printf '#!/bin/bash\n# reads: skills/a/scripts/data.md\n. dev/common.sh; for f in tools/*; do cat "$f"; done\n' > "$n/dev/th.sh"
printf '# id\tlevel\tcommand\n' > "$n/.loop/regression.tsv"
for r in ta tb tm tx tf tu th; do printf '%s\tland\tbash dev/%s.sh\n' $r $r >> "$n/.loop/regression.tsv"; done
aff() { $L affected --root "$n" "$@" | head -1 | sed 's/^AFFECTED [0-9]* of [0-9]* rows (\(.*\))$/\1/'; }
# Value: protects=a declared script's rows rerun on its declared file and not on another skill's file; fails_when=the
# narrow closure widens to the skill folder or drops declared files; why_new=every earlier lanes check is wide; seam=none;
# no_claim=real repo scripts (toy stand-ins)
check "a change to a declared skill file reruns only the rows whose closure reaches it" '[ "$(aff skills/a/scripts/a.py)" = "ta, tf, tu, tx" ] && [ "$(aff skills/a/scripts/data.md)" = "ta, tf, th, tu, tx" ]'
check "a change to another skill's file does not rerun a declared script's rows" '! aff skills/b/scripts/helper.py | grep -qw ta && [ "$(aff skills/b/scripts/helper.py)" = "tb, tf, tm, tx" ]'
# Value: protects=a file used through a folder variable set in another file still reruns its row; fails_when=the
# base-name rule is dropped or reads only the declaring script; why_new=no folder-variable case; seam=none; no_claim=names built at run time
check "an undeclared file used through a folder variable set in another file reruns its row" '[ "$(aff skills/b/scripts/solo.py)" = "tf, tm, tx" ]'
# Value: protects=a row whose declaration cannot be resolved reruns on a mapped change that does not touch it;
# fails_when=a declaration problem stops making the row always; why_new=new rule; seam=none; no_claim=none beyond protects
check "a row whose declaration cannot be resolved reruns on a change that does not touch it" 'out=$($L affected --root "$n" tools/x.txt); [ "$(aff tools/x.txt)" = "tf, th, tx" ] && grep -q "^ALWAYS tx: LANES-DECL-MISSING" <<<"$out" && grep -q "^ALWAYS tf: LANES-DECL-FOLDER" <<<"$out"'
# Value: protects=a change every row reaches reruns all, an unread file is a full run; fails_when=the narrow branch
# drops sourced helpers or the UNMAPPED rule; why_new=only the wide branch had these; seam=none; no_claim=none beyond protects
check "a narrow change reruns only its rows and a change every row reaches reruns all" '[ "$(aff skills/b/scripts/solo.py)" = "tf, tm, tx" ] && [ "$(aff dev/common.sh)" = "ta, tb, tf, th, tm, tu, tx" ]'
printf 'new\n' > "$n/src.txt"
check "a file no row reads is a full run (UNMAPPED)" '$L affected --root "$n" src.txt | grep -q "^UNMAPPED src.txt: full run"'
out=$($L check --root "$n" dev/tx.sh dev/tf.sh dev/tu.sh); rc=$?
check "lanes_cli.py check names each problem with its code, file:line and a fix line" '[ $rc = 1 ] && grep -q "^LANES-DECL-MISSING dev/tx.sh:2: declared path does not exist: skills/a/scripts/gone.py" <<<"$out" && grep -q "^LANES-DECL-FOLDER dev/tf.sh:3: names skills/b/scripts/" <<<"$out" && grep -q "^LANES-DECL-NONE dev/tu.sh:1" <<<"$out" && [ "$(grep -c "^fix: " <<<"$out")" = 3 ]'
check "deps --why prints the chain from the command to a file" '[ "$($L deps --root "$n" "bash dev/tm.sh" --why skills/b/scripts/helper.py)" = "dev/tm.sh -> skills/b/scripts/b.py -> skills/b/scripts/helper.py" ]'
# Value: protects=glob reads and split quoting are seen; fails_when=the "$here"/ form or the glob rule is dropped;
# why_new=no test used them; seam=none; no_claim=bash reads by names built at run time
printf '#!/bin/bash\n# reads: skills/b/scripts/b.py\nhere=.; for f in "$here"/skills/b/scripts/*.py; do wc -c < "$f"; done\n' > "$n/dev/tg.sh"
printf '#!/bin/bash\n# reads: skills/a/scripts/\npython3 skills/a/scripts/a.py\n' > "$n/dev/tv.sh"
printf '#!/bin/bash\n. dev/common.sh\n# reads: skills/a/scripts/a.py\n' > "$n/dev/tp.sh"
out=$($L check --root "$n" dev/tg.sh dev/tv.sh dev/tp.sh)
check "a glob over a skill folder must declare that folder; an unbacked folder or a late header is refused" 'grep -q "^LANES-DECL-GLOB dev/tg.sh" <<<"$out" && grep -q "^LANES-DECL-FOLDER-UNBACKED dev/tv.sh:2" <<<"$out" && grep -q "^LANES-DECL-PLACE dev/tp.sh:3" <<<"$out"'
printf '#!/bin/bash\n# reads: skills/b/scripts/\nhere=.; for f in "$here"/skills/b/scripts/*.py; do wc -c < "$f"; done\n' > "$n/dev/tg.sh"
check "a declared globbed folder is a prefix: a new file in it is a dependency" '$L deps --root "$n" "bash dev/tg.sh" | grep -qx "skills/b/scripts/" && [ -z "$($L check --root "$n" dev/tg.sh)" ]'
# Value: protects=headerless rows keep today's mapping exactly; fails_when=the shared helpers change wide behavior;
# why_new=parity oracle for the refactor (E7); seam=LANES_WIDE; no_claim=none beyond protects
w2=$(LANES_WIDE=1 $L affected --root "$n" skills/a/scripts/a.py 2>&1)
check "LANES_WIDE=1 maps every row wide, as before headers" '[ "$(aff skills/a/scripts/a.py)" = "ta, tf, tu, tx" ] && grep -q "^AFFECTED 4 of 7 rows (ta, tf, th, tu)$" <<<"$w2"'
cd "$d/repo" 2>/dev/null && git switch -q main 2>/dev/null
p1=$($L affected src/a.txt 2>&1); p2=$(LANES_WIDE=1 $L affected src/a.txt 2>&1)
check "with no headers, affected is the same with and without LANES_WIDE (wide mapping unchanged)" '[ -n "$p1" ] && [ "$p1" = "$p2" ]'
# Value: protects=a deleted helper forces a full run even when a broad row maps it; fails_when=deletions are treated as
# edits; why_new=no deletion case existed; seam=none; no_claim=renames outside skills/ and dev/
mkdir -p skills/k/scripts; printf 'import kh\n' > skills/k/scripts/k.py; printf 'Z = 1\n' > skills/k/scripts/kh.py
printf '#!/bin/bash\n# reads: skills/k/scripts/k.py\nprintf "k\\n" >> "$TOY_LOG"\n' > dev/k.sh
printf '#!/bin/bash\n# reads: skills/\nfor f in skills/*; do :; done; printf "w\\n" >> "$TOY_LOG"\n' > dev/w.sh  # lanes: no read (toy repo file)
printf 'k\tland\tbash dev/k.sh\tX-1\t2026-01-01\tK.\tcriterion\t\nw\tland\tbash dev/w.sh\tX-1\t2026-01-01\tW.\tcriterion\t\n' >> .loop/regression.tsv
git add -A; git commit -qm "Rows k and w"; $reg run land --reuse >/dev/null
fresh; out=$($reg run land --reuse); echo "$out"
check "a reusing run reuses declared rows when nothing changed" 'grep -q "^REUSED" <<<"$out" && [ -z "$(ran)" ]'
printf 'Z = 2\n' > skills/k/scripts/kh.py; git commit -qam "Change kh"
fresh; out=$($reg run land --reuse); echo "$out"
check "a run reruns a declared row whose imported module changed, and the broad row" 'grep -q "^AFFECTED 2 of" <<<"$out" && [ "$(ran)" = "k w " ]'
git rm -q skills/k/scripts/kh.py; git commit -qm "Delete kh"
fresh; out=$($reg run land --reuse); echo "$out"
check "a deleted skill file forces a full run even when a broad row maps it" 'grep -q "^FULL: deleted skills/k/scripts/kh.py" <<<"$out"'
echo "== check-reads.sh: runtime reads outside a row's closure fail the trace"
c="$d/trace"; mkdir -p "$c/dev/toy" "$c/skills/workflow-regression/scripts" "$c/skills/a/scripts" "$c/.loop"
cp "$here/dev/toy/check-reads.sh" "$c/dev/toy/"; cp "$here"/skills/workflow-regression/scripts/{lanes,narrow,lanes_cli}.py "$c/skills/workflow-regression/scripts/"
for f in a b c e; do printf 'NAME = "%s"\nopen(__file__).read()\n' "$f" > "$c/skills/a/scripts/$f.py"; done
printf '#!/bin/bash\n# reads: skills/a/scripts/a.py\npython3 skills/a/scripts/a.py\n' > "$c/dev/t1.sh"
printf '#!/bin/bash\n# reads: skills/a/scripts/a.py\nn=c; python3 skills/a/scripts/a.py; python3 skills/a/scripts/$n.py\n' > "$c/dev/t2.sh"
printf '#!/bin/bash\n# reads: skills/a/scripts/a.py skills/a/scripts/b.py\npython3 skills/a/scripts/a.py; python3 -I skills/a/scripts/b.py\n' > "$c/dev/t3.sh"
printf '#!/bin/bash\n# reads: skills/a/scripts/a.py\nt=$(mktemp -d); cp -R skills/a "$t/flat"; python3 skills/a/scripts/a.py; n=e; python3 "$t/flat/scripts/$n.py"; rm -rf "$t"\n' > "$c/dev/t4.sh"
printf '# id\tlevel\tcommand\n' > "$c/.loop/regression.tsv"
for r in 1 2 3 4; do printf 'r%s\tland\tbash dev/t%s.sh\n' $r $r >> "$c/.loop/regression.tsv"; done
out=$(bash "$c/dev/toy/check-reads.sh" 2>&1); rc=$?; echo "$out"
# Value: protects=a row's runtime Python reads outside its closure fail the nightly trace; fails_when=the hook or the
# closure comparison is dropped; why_new=new tool; seam=sitecustomize + PATH shim; no_claim=bash-only reads
check "check-reads passes a row whose runtime reads are inside its closure" 'grep -q "^PASS r1" <<<"$out"'
check "check-reads fails a row that reads a skill file its closure misses, with the line to add" '[ $rc = 1 ] && grep -q "^LANES-TRACE-UNDECLARED r2 skills/a/scripts/c.py" <<<"$out" && grep -q "^fix: # reads: skills/a/scripts/c.py" <<<"$out"'
check "check-reads fails a row with a Python launch the hook never saw (python3 -I)" 'grep -q "^LANES-TRACE-NOHOOK r3: 2 Python launches, 1 hooked" <<<"$out"'
check "check-reads maps a read of a copied skill file back to the repo file" 'grep -q "^LANES-TRACE-UNDECLARED r4 skills/a/scripts/e.py" <<<"$out"'
fi

[ $fails = 0 ] && echo "ALL PASS" || { echo "$fails FAILED"; exit 1; }
