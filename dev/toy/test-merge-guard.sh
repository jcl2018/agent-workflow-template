#!/bin/bash
# reads: skills/workflow-release/scripts/merge.py skills/workflow-release/scripts/autorelease.py
# reads: skills/workflow-release/scripts/release.py skills/workflow-release/scripts/wiki.py
# reads: skills/workflow-regression/scripts/lanes_cli.py skills/workflow-regression/scripts/lanes.py
# reads: skills/workflow-regression/scripts/narrow.py skills/workflow-delivery/scripts/prsteps.py dev/toy/fakegh/gh
here=$(cd "$(dirname "$0")/../.." && pwd)
. "$here/dev/toy/reap.sh"
# REG-4 (Amendment A1c, V2, E-8): before merging, merge.py refuses when the pull request head moved since the pr lane
# (HEAD_MOVED, exit 4) or the base moved in paths this goal's rows reach (BASE_MOVED, exit 2); a base move elsewhere
# only notes it; a base it can't fetch refuses (BASE_FETCH, exit 3).
# Value: protects=a merge never lands on a base or head its affected rows didn't run on; fails_when=merge.py merges
# without checking pr_head/pr_base or refuses every base move; why_new=merge.py checked only the PR state; seam=none;
# no_claim=GitHub's own merge (fakegh) and the race after the check (documented)
set -u
unset LOOP_SESSION_TOOL LOOP_OPERATION_SESSION
export HOME=$(mktemp -d) PATH="$here/dev/toy/fakegh:$PATH"
d=$(mktemp -d); toy_on_exit 'rm -rf "$d" "$HOME"'
export FAKE_GH_DIR="$d/gh"; mkdir -p "$FAKE_GH_DIR"
fails=0
ok() { echo "PASS: $1"; }
bad() { echo "FAIL: $1"; fails=$((fails + 1)); }
git init -q --bare -b main "$d/origin.git"
n="$d/repo"; git clone -q "$d/origin.git" "$n" 2>/dev/null; cd "$n"
mkdir -p src dev .loop
printf 'a\n' > src/a.txt; printf 'b\n' > src/b.txt
printf '#!/bin/bash\n# reads: src/a.txt\ncat src/a.txt\n' > dev/ta.sh  # lanes: no read (toy repo file)
printf '#!/bin/bash\n# reads: src/b.txt\ncat src/b.txt\n' > dev/tb.sh  # lanes: no read (toy repo file)
printf '# id\tlevel\tcommand\nta\tland\tbash dev/ta.sh\ntb\tland\tbash dev/tb.sh\n' > .loop/regression.tsv
git add -A; git commit -qm base; git push -q origin main
base=$(git rev-parse HEAD)
git switch -qc loop/g; echo a2 >> src/a.txt; git commit -qam "goal changes a"; head=$(git rev-parse HEAD)
M="$here/skills/workflow-release/scripts"
moved() {  # STATE-JSON: print "<code>|<line>" from base_moved, or "none"
  python3 - "$M" "$1" <<'PY'
import json, sys
sys.path.insert(0, sys.argv[1]); import merge
got = merge.base_moved(json.loads(sys.argv[2]), {"base": "main"}, ".")
print("none" if got is None else "%d|%s" % got)
PY
}
st="{\"slug\": \"g\", \"pr_base\": \"$base\", \"pr_head\": \"$head\"}"
check() { if eval "$2"; then ok "$1"; else bad "$1"; echo "    out: $out"; fi; }
out=$(moved "$st"); check "an unmoved base merges" '[ "$out" = none ]'
git switch -q main; echo b2 >> src/b.txt; git commit -qam "base changes b"; git push -q origin main; git switch -q loop/g
out=$(moved "$st"); check "a base move in paths the goal's rows don't reach notes it and merges" 'grep -q "^NOTE: main moved in paths this goal.s rows don.t reach; merging" <<<"$out" && tail -1 <<<"$out" | grep -qx none'
git switch -q main; echo a3 >> src/a.txt; git commit -qam "base changes a"; git push -q origin main; git switch -q loop/g
out=$(moved "$st"); check "a base move in a path the goal's rows reach refuses BASE_MOVED with its fix (exit 2)" 'grep -q "^2|REFUSED (BASE_MOVED): main moved in paths this goal.s rows reach (lane on .*, base now .*). Fix: goal.py pr g, then merge.py g" <<<"$out"'
git remote set-url origin "$d/nowhere.git"
out=$(moved "$st"); check "a base that can't be fetched refuses BASE_FETCH and merges nothing (exit 3)" 'grep -q "^3|REFUSED (BASE_FETCH): cannot fetch origin/main: .*nothing merged" <<<"$out"'
git remote set-url origin "$d/origin.git"
# the head check, through merge.py itself
common=$(git rev-parse --git-common-dir); mkdir -p "$common/loop/runs"
printf '{"auto_merge": true, "base": "main"}\n' > .loop/config.json
echo "{\"slug\": \"g\", \"status\": \"done\", \"pr\": \"https://example.test/pull/1\", \"pr_base\": \"$base\", \"pr_head\": \"$head\"}" > "$common/loop/runs/g.json"
out=$(FAKE_GH_PR_STATE=OPEN FAKE_GH_PR_HEAD=0000000000000000000000000000000000000000 python3 "$M/merge.py" g 2>&1); rc=$?
check "a pull request head that moved since the pr lane refuses HEAD_MOVED with its fix (exit 4), nothing merged" '[ $rc = 4 ] && grep -q "^REFUSED (HEAD_MOVED): the pull request head moved since the pr lane passed (lane on .*, PR head 000000000000). Fix: goal.py pr g, then merge.py g" <<<"$out" && [ ! -e "$FAKE_GH_DIR/merged" ]'
[ "$fails" = 0 ] && echo "ALL PASS" || { echo "$fails FAILED"; exit 1; }
