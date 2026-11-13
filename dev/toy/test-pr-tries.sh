#!/bin/bash
# reads: skills/workflow-delivery/scripts/goal.py skills/workflow-delivery/scripts/guards.py skills/workflow-delivery/scripts/role.py
# reads: skills/workflow-delivery/scripts/private.py skills/workflow-delivery/scripts/lane.py
# Proves that goal.py pr never spends one of its 3 tries on something that is not the goal's fault: a conflict caused only by main
# moving in generated files (a Tests page, the regression rows) is mended and merged with no try; a real conflict still costs one;
# a lane that died with no exit status (killed from outside) reruns free, bounded at 3, and a real failure still costs a try; and
# the text goal.py writes carries no absolute path. No model is called, no network.
# usage: test-pr-tries.sh [DIR] [mend|lane|paths]   (no part: all)
set -u
unset LOOP_SESSION_TOOL LOOP_OPERATION_SESSION LOOP_BATCH GITHUB_ACTIONS
export LOOP_ROLE=worker
here=$(cd "$(dirname "$0")/../.." && pwd)
. "$here/dev/toy/reap.sh"
T=${1:-$(mktemp -d)}; part=${2:-all}; rm -rf "${T:?}"; mkdir -p "$T"
want() { [ "$part" = all ] || [ "$part" = "$1" ]; }
D="$here/skills/workflow-delivery/scripts"
goal="python3 $D/goal.py"; F="python3 $D/flow.py"
export HOME="$T/home" FAKE_AGENT="$T/fake" FAKE_GH_DIR="$T/gh"; mkdir -p "$HOME" "$FAKE_AGENT"
fails=0
ok() { echo "PASS: $1"; }
bad() { echo "FAIL: $1"; fails=$((fails + 1)); }
check() { if eval "$2"; then ok "$1"; else bad "$1"; fi; }
"$here/dev/toy/make.sh" "$T" >/dev/null || exit 1
export LOOP_FLOW="$T/flow.json" PATH="$here/dev/toy/fakegh:$PATH" LOOP_LANES_DIR="$T/lanes"
cd "$T/repo" || exit 1
python3 "$here/skills/workflow-setup/scripts/setup.py" --bare >/dev/null
git switch -q main; git merge -q --no-edit workflow-setup
HEAD_ROW=$(printf '# id\tlevel\tcommand\tgoal\tseen_red\tdescription\tcategory\tlink')
row() { printf '%s\tnightly\ttrue\tX-1\t%s\t%s\tcriterion\t\n' "$1" "${2:-}" "${3:-a row}"; }
printf '%s\n' "$HEAD_ROW" > .loop/regression.tsv; row base-row >> .loop/regression.tsv
git add -A; git commit -qm "rows" ; git push -q origin main
C=$(cd "$(git rev-parse --git-common-dir)" && pwd); R="$C/loop/runs"
field() { python3 -c "import json,sys;print(json.load(open(sys.argv[1])).get(sys.argv[2]))" "$R/$1.json" "$2"; }
step() { $F "$1" "$2" --wait 5 >/dev/null; $F "$1" "$2" --wait 10 >/dev/null; $goal record "$1" "$2" --file "$R/$1.$2.txt"; }
flowall() { for s in idea plan review qa ship; do step "$1" $s >/dev/null; done; }
other="$T/other"; git clone -q "$T/origin.git" "$other"; git -C "$other" config user.email t@example.test; git -C "$other" config user.name Toy
mainmoves() { ( cd "$other" && git pull -q origin main && "$@" && git add -A && git commit -qm "Main moves" && git push -q origin main ); }

if want mend; then
echo "== a conflict caused only by main moving is mended: no try"
git switch -q main; $goal new m1 --here --goal "M1" --done "m1" >/dev/null; row m1-row >> .loop/regression.tsv; git commit -qam m1; flowall m1; git switch -q main
mainmoves bash -c "$(declare -f row); row main-row >> .loop/regression.tsv"
git switch -q loop/m1
out=$($goal pr m1 2>&1); echo "$out" | sed 's/^/  /'
check "main appended rows to the regression file: pr mends the merge, says so, opens the PR, spends no try" 'grep -q "^MENDED .loop/regression.tsv" <<<"$out" && grep -q "^PR " <<<"$out" && [ "$(field m1 tries)" = 0 ]'
check "both sides rows survive, nothing duplicated, no conflict markers" '[ "$(grep -c "^m1-row" .loop/regression.tsv)" = 1 ] && [ "$(grep -c "^main-row" .loop/regression.tsv)" = 1 ] && [ "$(grep -c "^base-row" .loop/regression.tsv)" = 1 ] && ! grep -q "^[<>=]\{7\}" .loop/regression.tsv && [ ! -e "$(git rev-parse --git-dir)/MERGE_HEAD" ]'

echo "== a real conflict is a try lost to main moving: not counted, with its own cap (#3877)"
git switch -q main; $goal new m2 --here --goal "M2" --done "m2" >/dev/null; printf '# from m2\n' >> calc.py; row m2-row >> .loop/regression.tsv; git commit -qam m2; flowall m2; git switch -q main
mainmoves bash -c "printf '# from main\n' >> calc.py; $(declare -f row); row main-row2 >> .loop/regression.tsv"
git switch -q loop/m2
out=$($goal pr m2 2>&1); echo "$out" | sed 's/^/  /'
check "a code file in the conflict is a real conflict: it is reported and not counted against max_tries, and the tree stays clean" 'grep -q "^TRY NOT COUNTED (main moved: 1 of 5; .*calc.py" <<<"$out" && [ "$(field m2 tries)" = 0 ] && [ "$(field m2 moved)" = 1 ] && [ ! -e "$(git rev-parse --git-dir)/MERGE_HEAD" ] && [ -z "$(git status --porcelain --untracked-files=no)" ]'
git switch -q main

echo "== the mend itself, on a merge in progress"
mend() { python3 - "$D" "$1" <<'PY'
import subprocess, sys
sys.path.insert(0, sys.argv[1]); import private, role
files = subprocess.run(["git", "diff", "--name-only", "--diff-filter=U"], capture_output=True, text=True).stdout.split()
print("MEND", private.mend(role.git, files, "origin/main"), " ".join(files))
PY
}
mk() { cd "$T" && rm -rf "$T/s"; git clone -q "$T/origin.git" "$T/s"; cd "$T/s"; git config user.email t@example.test; git config user.name Toy; git switch -q -c side; }
mk; sed -i.bak 's/^base-row\(.*\)\ta row\t/base-row\1\tours edit\t/' .loop/regression.tsv; rm .loop/regression.tsv.bak; git commit -qam ours
( cd "$other" && git pull -q origin main && sed -i.bak 's/^base-row\(.*\)\ta row\t/base-row\1\ttheirs edit\t/' .loop/regression.tsv && rm .loop/regression.tsv.bak && git commit -qam theirs && git push -q origin main )
git fetch -q origin; git merge -q --no-edit origin/main >/dev/null 2>&1; out=$(mend x)
check "a row both sides changed differently stays a real conflict: nothing is chosen for the owner" 'grep -q "^MEND False" <<<"$out"'
git merge --abort 2>/dev/null
mk; sed -i.bak '/^base-row/d' .loop/regression.tsv; rm .loop/regression.tsv.bak; git commit -qam "ours deletes"
( cd "$other" && git pull -q origin main && row more-row >> .loop/regression.tsv && git add -A && git commit -qm "theirs adds next to it" && git push -q origin main )
git fetch -q origin; git merge -q --no-edit origin/main >/dev/null 2>&1; out=$(mend x)
check "a row the branch deleted is never brought back by a mend" '! grep -q "^MEND True" <<<"$out"'
git merge --abort 2>/dev/null
mk; mkdir -p docs/wiki .loop; printf '# Tests\n\nours\n' > docs/wiki/Tests.md; printf 'x\n' > .loop/docs.tsv; git add -A; git commit -qm ours-tests
( cd "$other" && git pull -q origin main && mkdir -p docs/wiki && printf '# Tests\n\ntheirs\n' > docs/wiki/Tests.md && git add -A && git commit -qm theirs-tests && git push -q origin main )
git fetch -q origin; git merge -q --no-edit origin/main >/dev/null 2>&1; out=$(mend x)
check "a Tests page conflict, with the docs registry present, takes the base's page and commits the merge" 'grep -q "^MEND True docs/wiki/Tests.md" <<<"$out" && grep -q theirs docs/wiki/Tests.md && [ ! -e .git/MERGE_HEAD ]'
mk; mkdir -p docs/wiki .loop; git rm -q .loop/docs.tsv 2>/dev/null; printf '# Tests\n\nours2\n' > docs/wiki/Tests.md; git add -A; git commit -qm ours-tests2
( cd "$other" && git pull -q origin main && printf '# Tests\n\ntheirs2\n' > docs/wiki/Tests.md && git add -A && git commit -qm theirs-tests2 && git push -q origin main )
git fetch -q origin; git merge -q --no-edit origin/main >/dev/null 2>&1; rm -f .loop/docs.tsv; out=$(mend x)
check "with no docs registry the lane prep would not re-render our rows, so a Tests conflict is not mended" 'grep -q "^MEND False" <<<"$out"'
git merge --abort 2>/dev/null
out=$(python3 - "$D" <<'PY'
import sys
sys.path.insert(0, sys.argv[1]); import private, role
print(private.mend(role.git, [], "origin/main"))
PY
)
check "an empty conflict list (a dirty tree refusing the merge, say) is never mended" '[ "$out" = False ]'
cd "$T/repo"

fi
if want lane; then
echo "== a lane killed from outside reruns free, bounded; a real failure still costs one"
git switch -q main; $goal new d1 --here --goal "D1" --done "d1" >/dev/null; echo d1 > d1.txt; git add d1.txt; git commit -qm d1; flowall d1
dead() { python3 - "$R" "$(git rev-parse HEAD)" "$1" <<'PY'
import json, sys, time
runs, head, slug = sys.argv[1:]
base = runs + "/%s.pr-lane" % slug
json.dump({"head": head, "attempt": "o-1", "started": time.time(), "limit": 60, "rc": base + ".rc", "pid": 999999, "markers": 1, "pool": "/nonexistent"}, open(base + ".job", "w"))
open(base + ".txt", "w").write("AFFECTED 1 of 1 rows (r1): x\nPASS r1\n")
PY
}
git switch -q loop/d1; git merge -q --no-edit origin/main >/dev/null 2>&1
for i in 1 2 3; do git fetch -q origin; git merge -q --no-edit origin/main >/dev/null 2>&1; dead d1; out=$($goal pr d1 2>&1); echo "$out" | sed "s/^/  [$i] /" | head -3
  check "dead lane $i: not counted, says how many free reruns are left, tries stay 0" 'grep -q "^TRY NOT COUNTED (free rerun '"$i"' of 3; the next death counts)" <<<"$out" && [ "$(field d1 tries)" = 0 ] && [ "$(field d1 free)" = '"$i"' ]'
done
git fetch -q origin; git merge -q --no-edit origin/main >/dev/null 2>&1; dead d1; out=$($goal pr d1 2>&1); echo "$out" | sed 's/^/  [4] /' | head -3
check "the fourth death counts as a try" 'grep -q "^TRY 1 OF 3 FAILED" <<<"$out" && [ "$(field d1 tries)" = 1 ]'
check "the try line it prints and the journal it keeps hold no absolute path" '! grep "^TRY" <<<"$out" | grep -q "$T/" && python3 -c "import json,sys;s=json.load(open(sys.argv[1]));assert not any(sys.argv[2] in l for l in s[\"log\"])" "$R/d1.json" "$T/"'
out=$(python3 - "$D" d1 <<'PY'
import sys
sys.path.insert(0, sys.argv[1]); import goal
st = goal.load(sys.argv[2]); st["tries"] = 0
goal.failed_try(st, "regression lane failed: r1, r2", "build", "fix it")
print(st["tries"])
PY
)
check "a real failure (failing rows) still costs a try" '[ "$(tail -1 <<<"$out")" = 1 ]'
out=$(python3 - "$D" d1 <<'PY'
import sys
sys.path.insert(0, sys.argv[1]); import goal
st = goal.load(sys.argv[2]); st["tries"] = 0; st["free"] = 0
goal.failed_try(st, "qa failed: regression lane: LANE_DIED: the lane ended", "qa", "again")
print(st["tries"], st["free"])
PY
)
check "a dead qa or ship lane, which reaches the same place through record, is free too" '[ "$(tail -1 <<<"$out")" = "0 1" ]'
out=$(python3 - "$D" d1 <<'PY'
import sys
sys.path.insert(0, sys.argv[1]); import goal
st = goal.load(sys.argv[2]); st["tries"] = 0; st["free"] = 0
goal.failed_try(st, "qa failed: the tests are red; see lane x: LANE_DIED: not really", "qa", "again")
print(st["tries"], st["free"])
PY
)
check "words an agent wrote that merely mention LANE_DIED are not a dead lane: they cost a try" '[ "$(tail -1 <<<"$out")" = "1 0" ]'
git switch -q main
echo x >> calc.py
( cd "$other" && git pull -q origin main && echo y >> calc.py && git add -A && git commit -qm "main edits calc" && git push -q origin main )
git fetch -q origin
out=$(python3 - "$D" <<'PY'
import sys
sys.path.insert(0, sys.argv[1]); import role
print(role.sync("main")[0])
PY
)
check "a dirty tree that stops the merge is not a conflict: sync says dirty, so no try is spent" '[ "$(tail -1 <<<"$out")" = dirty ]'
git checkout -q -- calc.py

fi
if want paths; then
echo "== finding and report text carries no absolute path"
git switch -q main; $goal new d1 --here --goal "D1" --done "d1" >/dev/null
out=$(python3 - "$D" d1 "$T" <<'PY'
import sys
sys.path.insert(0, sys.argv[1]); import goal, private
st = goal.load(sys.argv[2])
try:
    goal.fail_stop(st, "Failed 3 tries. Last: LANE_FAIL r1 (log %s/loop/runs/d1.pr-lane.txt). Reproduce: python3 %s/skills/x/run.py run r1" % (sys.argv[3], sys.argv[3]))
except SystemExit:
    pass
p = private.plain
print(p("/mnt/x/a/b/log.txt"), "|", p("/mnt/x"), "|", p("see https://github.com/o/r/issues/436 and skills/a/b.py and ./x and #436"))
PY
)
check "a finding keeps the file name and the row id but no absolute path" 'python3 -c "import json,sys;s=json.load(open(sys.argv[1]));f=s[\"finding\"];assert \"d1.pr-lane.txt\" in f and \"LANE_FAIL r1\" in f and sys.argv[2] not in f and not any(sys.argv[2] in l for l in s[\"log\"])" "$R/d1.json" "$T/" && ! grep -q "$T/" .loop/findings.md && grep -q "LANE_FAIL r1" .loop/findings.md'
check "plain() cuts a path to its last part, a bare top folder to ~, and leaves URLs, relative paths and issue refs alone" '[ "$(tail -1 <<<"$out")" = "log.txt | ~ | see https://github.com/o/r/issues/436 and skills/a/b.py and ./x and #436" ]'
fi

echo; [ "$fails" = 0 ] && echo "ALL PASS" || { echo "$fails FAILED"; exit 1; }
