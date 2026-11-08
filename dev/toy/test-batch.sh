#!/bin/bash
# Proves batch.py with a stand-in agent. No model is called. usage: test-batch.sh [DIR]
# The governing session only adds and starts; every goal runs in its own process, in its own worktree.
set -u
unset LOOP_ROLE  # these tests act as the operation session
here=$(cd "$(dirname "$0")/../.." && pwd)
T=${1:-$(mktemp -d)}; rm -rf "${T:?}"; mkdir -p "$T"
BA="python3 $here/skills/workflow-monitoring/scripts/batch.py"
BO="python3 $here/skills/workflow-monitoring/scripts/board.py"
export HOME="$T/home" FAKE_AGENT="$T/fake"; mkdir -p "$HOME" "$FAKE_AGENT"
fails=0
ok() { echo "PASS: $1"; }
bad() { echo "FAIL: $1"; fails=$((fails + 1)); }
check() { if eval "$2"; then ok "$1"; else bad "$1"; fi; }
"$here/dev/toy/make.sh" "$T" >/dev/null || exit 1
export LOOP_FLOW="$T/flow.json"
cd "$T/repo" || exit 1
python3 "$here/skills/workflow-setup/scripts/setup.py" --bare >/dev/null
git switch -q main; git merge -q --no-edit workflow-setup
C=$(cd "$(git rev-parse --git-common-dir)" && pwd); export COMMON="$C"
field() { python3 -c "import json,sys;print(json.load(open(sys.argv[1])).get(sys.argv[2]))" "$C/loop/runs/$1.json" "$2"; }
# A stand-in agent: a goal marks itself done.
cat > "$T/agent.sh" <<'A'
#!/bin/bash
prompt=${!#}
slug=$(grep -oE 'Slug: [a-z0-9-]+' <<<"$prompt" | head -1 | cut -d' ' -f2)
echo "$$ $(pwd)" > "$FAKE_AGENT/goal-$slug"
python3 - "$COMMON/loop/runs/$slug.json" <<'PY'
import json, sys
s = json.load(open(sys.argv[1])); s["status"] = "done"; s["step"] = "release"
json.dump(s, open(sys.argv[1], "w"))
PY
A
python3 - "$T/agent.sh" <<'PY'
import json, sys
c = json.load(open(".loop/config.json")); c["agent_command"] = ["bash", sys.argv[1]]; c["parallel"] = 4
json.dump(c, open(".loop/config.json", "w"), indent=2)
PY
git commit -qam "Agent"; git push -q origin main
until_status() { for _ in $(seq 150); do [ "$(field "$1" status)" = "$2" ] && return 0; sleep 0.1; done; return 1; }
head=$(git rev-parse HEAD)

echo "== add"
$BA add nightly --goal "Add g" --done "g works" --slug g1 >/dev/null
$BA add nightly --goal "Add h" --done "h works" --slug h1 --touches h.py >/dev/null
check "add: a named batch heading holds goal lines" 'grep -q "^## Batch: nightly" .loop/queue.md && grep -q "^- slug: g1 | goal: Add g | done: g works$" .loop/queue.md && grep -q "^- slug: h1 |" .loop/queue.md'
check "add: a repeated slug is refused" '$BA add nightly --goal "again" --done x --slug g1 2>&1 | grep -q "^REFUSED"'
check "add: POCs are gone" '$BA add nightly --poc "Can we?" 2>&1 | grep -q "unrecognized arguments: --poc"'
check "add: no level" '$BA add nightly --goal "L" --done x --level 1 2>&1 | grep -q "unrecognized arguments: --level"'

echo "== start"
$BA start nightly > "$T/s1"
until_status g1 done && until_status h1 done && ok "start: every goal ran" || bad "start: every goal ran ($(field g1 status) $(field h1 status))"
gpid=; gdir=; hpid=; hdir=
read -r gpid gdir < "$FAKE_AGENT/goal-g1"; read -r hpid hdir < "$FAKE_AGENT/goal-h1"
check "start: no line runs in the governing session" '[ "$gpid" != "$$" ] && [ "$hpid" != "$$" ] && [ "$gdir" != "$T/repo" ] && [ "$hdir" != "$T/repo" ]'
check "start: each goal runs in its own worktree" '[ "$gdir" != "$hdir" ] && [ -n "$gdir" ] && [ -n "$hdir" ]'
check "start: the governing checkout is unchanged" '[ "$(git rev-parse HEAD)" = "$head" ] && [ -z "$(git status --porcelain | grep -v queue.md)" ]'
$BA status nightly > "$T/st"
check "status: one line a goal" 'grep -q "^goal g1: done" "$T/st" && grep -q "^goal h1: done" "$T/st"'

echo "== alone"
mkdir -p "$T/lone"; cp "$here/skills/workflow-monitoring/scripts/batch.py" "$T/lone/"
$BA add solo --goal "Add s" --done "s works" --slug s1 >/dev/null
python3 "$T/lone/batch.py" start solo > "$T/lone/out" 2>&1
check "batch.py alone says how to start goal lines" 'grep -q "NEXT: run watch.py watch --once" "$T/lone/out"'

echo "== text and sizes"
for f in skills/workflow-monitoring/references/operation.md skills/workflow-monitoring/SKILL.md skills/workflow-delivery/SKILL.md; do
  check "$f says the operation session governs only" 'grep -qi "governance only" "$here/$f" && grep -qiE "runs neither|never runs" "$here/$f"'
done
check "every script is under 20 KB" '[ -z "$(find "$here/skills" -name "*.py" -size +20480c)" ]'
check "the test runs as a regression row" 'grep -q "test-batch.sh" "$here/.loop/regression.tsv"'
page="$here/docs/wiki/Monitoring.md"
for id in no-line-in-governor skill-says-governs; do
  check "$id is a test named in the Tests table" 'sed -n "/^## Tests/,\$p" "$page" | grep -q "| \[$id\]("'
done
[ "$fails" = 0 ] && echo "ALL PASS" || { echo "$fails FAILED"; exit 1; }
