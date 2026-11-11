#!/bin/bash
# reads: skills/workflow-delivery/scripts/flow.py skills/workflow-delivery/scripts/goal.py
# reads: skills/workflow-delivery/scripts/role.py skills/workflow-regression/scripts/regression.py
# reads: skills/workflow-setup/scripts/setup.py skills/workflow-regression/scripts/lanes.py skills/workflow-regression/scripts/tiers.py
# Proves regression.py run --reuse: a goal's suite runs once, then later runs reuse it, rerun only the rows a change can
# affect, and never reuse a failing or missing run. Then delivery's lanes: qa runs the lane before the qa skill (through
# the flow file's test_record prefix), record refuses qa without it, and pr reruns only what a base merge and the goal
# affected (the goal tier, tiers.py).
# No model is called. usage: test-lanes.sh [DIR] [regression|delivery]
set -u
unset GITHUB_SERVER_URL GITHUB_REPOSITORY GITHUB_RUN_ID  # run cells and rendered Tests never depend on the runner
unset LOOP_SESSION_TOOL LOOP_OPERATION_SESSION GH_TOKEN GITHUB_TOKEN
here=$(cd "$(dirname "$0")/../.." && pwd)
. "$here/dev/toy/reap.sh"
export HOME=$(mktemp -d)
d=${1:-$(mktemp -d)}; rm -rf "$d"; mkdir -p "$d"
[ -n "${1:-}" ] || toy_on_exit 'rm -rf "$d" "$HOME"'
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
check "a new file under dev/ no row reads no longer forces a full run" 'grep -q "^UNMAPPED dev/new.sh: ran the rows that name them" <<<"$out" && ! grep -q "^FULL" <<<"$out" && [ -z "$(ran)" ]'
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
check "the lane command resolves from the installed package, not the repo (no skills folder here)" '[ ! -e skills ] && grep -q "^python3 $here/skills/workflow-regression/scripts/regression.py run land --reuse --tier goal$" <<<"$lane"'
printf '# the goal was here\n' >> dev/lib.sh; git commit -qam "The goal changes b's helper"
out=$(step lg qa); echo "$out"
check "qa runs the lane first: a goal lane with no record runs the rows the goal's change reaches, never FULL" 'grep -q "^LANE qa AFFECTED 1/1 " <<<"$out" && grep -q "^SELECTED b: reaches dev/lib.sh" "$common/loop/runs/lg.qa-lane.txt" && ! grep -q "^FULL" "$common/loop/runs/lg.qa-lane.txt"'
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

[ $fails = 0 ] && echo "ALL PASS" || { echo "$fails FAILED"; exit 1; }
