#!/bin/bash
# End-to-end test of workflow-monitoring on a throwaway toy repo. usage: test-monitoring.sh [DIR]
# WARNING: this calls the REAL claude CLI (model haiku by default, set MODEL=...) for about six short goals, which costs
# money and takes several minutes. gh is faked by dev/toy/fakegh; the real gh is never called. Dev only; never packaged.
# Proves: (1) 3 goals run in parallel, one is killed and fails, two end done with pull requests; (2) a goal whose
# touches overlap a running goal waits for it; (3) report and dashboard match the records, with a goal waiting on you;
# (4) resume relaunches the failed goal and it finishes.
set -u
here=$(cd "$(dirname "$0")/../.." && pwd)
T=${1:-$(mktemp -d)}; MODEL=${MODEL:-haiku}
M="python3 $here/skills/workflow-monitoring/scripts/monitor.py"
W="python3 $here/skills/workflow-monitoring/scripts/watch.py"
export PATH="$here/dev/toy/fakegh:$PATH" FAKE_GH_DIR="$T/gh"
say() { printf '\n=== %s\n' "$*"; }
field() { python3 -c "import json,sys;print(json.load(open(sys.argv[1])).get(sys.argv[2]))" "$C/loop/runs/$1.json" "$2" 2>/dev/null; }
creates() { grep -c '^pr create' "$FAKE_GH_DIR/calls.log" 2>/dev/null || echo 0; }
logs() { for s in "$@"; do python3 -c "import json,sys;[print(sys.argv[2], l) for l in json.load(open(sys.argv[1]))['log']]" "$C/loop/runs/$s.json" "$s"; done | sort -k2; }

say "toy repo in $T"
bash "$here/dev/toy/make.sh" "$T" || exit 1
cd "$T/repo" || exit 1
python3 "$here/skills/workflow-setup/scripts/setup.py" >/dev/null || exit 1
git switch -q main && git merge -q --ff-only workflow-setup
python3 - "$here/skills" "$MODEL" <<'EOF'
import json, sys
path = ".loop/config.json"
cfg = json.load(open(path))
cfg["agent_command"] = ["claude", "-p", "--model", sys.argv[2], "--allowedTools=Bash,Read,Write,Edit", "--add-dir=" + sys.argv[1]]
json.dump(cfg, open(path, "w"), indent=2)
EOF
cat >> .loop/queue.md <<'EOF'
- slug: stats-a | level: quick | touches: stats_a.py, test_stats_a.py | goal: Add stats_a.py with median(values) | done: stats_a.median([3, 1, 2]) returns 2 | done: test_stats_a.py tests median and passes
- slug: stats-b | level: quick | touches: stats_b.py, test_stats_b.py | goal: Add stats_b.py with mode(values) | done: stats_b.mode([1, 2, 2, 3]) returns 2 | done: test_stats_b.py tests mode and passes
- slug: stats-c | level: quick | touches: stats_c.py, test_stats_c.py | goal: Add stats_c.py with range_of(values) | done: stats_c.range_of([4, 1, 9]) returns 8 | done: test_stats_c.py tests range_of and passes
EOF
git commit -qam "Queue three goals" && git push -q origin main
C=$(cd "$(git rev-parse --git-common-dir)" && pwd)

say "(1) watch with three goals; stats-c is killed mid-run"
$W watch --interval 2 --skill-dir "$here/skills" > "$T/start1.out" 2>&1 &
mon=$!
for _ in $(seq 60); do [ "$(field stats-c status)" = running ] && break; sleep 1; done
sleep 25
pid=$(field stats-c pid); echo "stats-c status=$(field stats-c status) pid=$pid; kill -9 its process group"
kill -9 -- "-$pid" 2>/dev/null || kill -9 "$pid"
wait $mon
cat "$T/start1.out"
logs stats-a stats-b stats-c | grep -E 'launched|failed|pull request'
echo "pr create calls: $(creates)"

say "(2) a goal overlapping a running goal waits; (3) one goal ends waiting on you"
cat >> .loop/queue.md <<'EOF'
- slug: pkg-d | level: quick | touches: pkg/ | goal: Add pkg/__init__.py and pkg/greet.py with hello() returning "hello" | done: pkg.greet.hello() returns "hello" | done: test_greet.py tests hello and passes
- slug: pkg-e | level: quick | touches: pkg/shout.py | goal: Add pkg/shout.py with shout(text) returning text upper-cased | done: pkg.shout.shout("hi") returns "HI" | done: test_shout.py tests shout and passes | release: ask
EOF
git commit -qam "Queue two overlapping goals" && git push -q origin main
$W watch --interval 2 --skill-dir "$here/skills" 2>&1 | tee "$T/start2.out"
logs pkg-d pkg-e | grep -E 'queued|launched|pull request|waiting'
if [ "$(field pkg-e status)" != waiting ]; then
  echo "NOTE: the agent did not wait by itself (status $(field pkg-e status)); recording the wait with goal.py"
  (cd "$(field pkg-e worktree)" && python3 "$here/skills/workflow-delivery/scripts/goal.py" wait pkg-e \
    --ask "Cut a release or leave it unreleased?" --words "cut pkg-e" --words "leave pkg-e")
fi
echo "pr create calls: $(creates)"

say "(3) report and dashboard"
$M report
for s in stats-a stats-b stats-c pkg-d pkg-e; do echo "record $s: status=$(field $s status) step=$(field $s step) pr=$(field $s pr)"; done
html=$($M dashboard); echo "dashboard: $html"
grep -o 'leave pkg-e\|cut pkg-e' "$html" | sort -u
grep -c '<script' "$html" | sed 's/^/script tags: /'
grep -Eo '(src|href)=|https?://[a-z]' "$html" | grep -v 'https://example.test' | sort | uniq -c | sed 's/^/external refs: /'

say "(4) resume the failed goal"
$W resume stats-a 2>&1 | tail -1
$W resume stats-c --skill-dir "$here/skills"
for _ in $(seq 300); do [ "$(field stats-c status)" != running ] && break; sleep 2; $M report >/dev/null; done
logs stats-c | grep -E 'resumed|launched|failed|pull request'
$M report
echo "pr create calls: $(creates)"
