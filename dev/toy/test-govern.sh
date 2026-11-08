#!/bin/bash
# Real proof of one governing process: two level 0 goals, started by one process, each built by a real headless agent in
# its own worktree. WARNING: this calls the real claude CLI (haiku by default). gh is faked. usage: test-govern.sh [DIR]
set -u
unset LOOP_ROLE  # these tests act as the operation session
here=$(cd "$(dirname "$0")/../.." && pwd)
T=${1:-$(mktemp -d)}; rm -rf "$T"; mkdir -p "$T"; MODEL=${MODEL:-haiku}
W="python3 $here/skills/workflow-monitoring/scripts/watch.py"
M="python3 $here/skills/workflow-monitoring/scripts/monitor.py"
export PATH="$here/dev/toy/fakegh:$PATH" FAKE_GH_DIR="$T/gh"
"$here/dev/toy/make.sh" "$T" || exit 1
export LOOP_FLOW="$T/flow.json"
cd "$T/repo" || exit 1
python3 "$here/skills/workflow-setup/scripts/setup.py" --bare >/dev/null
git switch -q main; git merge -q --ff-only workflow-setup
python3 - "$here/skills" "$MODEL" <<'PY'
import json, sys
c = json.load(open(".loop/config.json"))
c["agent_command"] = ["claude", "-p", "--model=" + sys.argv[2], "--allowedTools=Bash,Read,Write,Edit", "--add-dir=" + sys.argv[1]]
json.dump(c, open(".loop/config.json", "w"), indent=2)
PY
git commit -qam "Agent command"; git push -q origin main
C=$(cd "$(git rev-parse --git-common-dir)" && pwd)
fails=0
ok() { echo "PASS: $1"; }
bad() { echo "FAIL: $1"; fails=$((fails + 1)); }
field() { python3 -c "import json,sys;print(json.load(open(sys.argv[1])).get(sys.argv[2]))" "$C/loop/runs/$1.json" "$2"; }

head0=$(git rev-parse HEAD); files0=$(git ls-files -o --exclude-standard | sort | grep -v '^.loop/')
$W go "Add stats_a.py with median(values)" --done "stats_a.median([3, 1, 2]) returns 2, proved by test_stats_a.py" --touches "stats_a.py,test_stats_a.py" --slug stats-a --skill-dir "$here/skills"
$W go "Add stats_b.py with mode(values)" --done "stats_b.mode([1, 2, 2]) returns 2, proved by test_stats_b.py" --touches "stats_b.py,test_stats_b.py" --slug stats-b --skill-dir "$here/skills"
$W watch --interval 5 --skill-dir "$here/skills" | tee "$T/watch.out"
$M report

for s in stats-a stats-b; do
  [ "$(field $s status)" = done ] && ok "$s done" || bad "$s is $(field $s status)"
  [ "$(field $s level)" = None ] && ok "$s has no level" || bad "$s level"
  [ -n "$(field $s pr)" ] && [ "$(field $s pr)" != None ] && ok "$s has a pull request" || bad "$s pr"
  [ "$(field $s judge)" = None ] && ok "$s ran no judge" || bad "$s judged"
  [ -f "$C/loop/worktrees/$s/${s/-/_}.py" ] && ok "$s built in its own worktree" || bad "$s worktree"
done
[ "$(field stats-a worktree)" != "$(field stats-b worktree)" ] && ok "two worktrees" || bad "same worktree"
[ "$(git rev-parse HEAD)" = "$head0" ] && ok "governing checkout: no commit" || bad "governor committed"
[ ! -e stats_a.py ] && [ ! -e stats_b.py ] && [ -z "$(git status --porcelain -- '*.py')" ] && ok "governing checkout: no code" || bad "governor wrote code"
[ "$(grep -c '^pr create' "$FAKE_GH_DIR/calls.log")" = 2 ] && ok "two pull requests, each from its branch" || bad "pr count"
started=$(grep -c 'launched agent' "$T/watch.out"); echo "launched in watch output: $started (go launched them)"
[ "$fails" = 0 ] && echo "ALL PASS" || { echo "$fails FAILED"; exit 1; }
