#!/bin/bash
# Proves batch.py with a stand-in agent. No model is called. usage: test-batch.sh [DIR]
# The governing session only adds and starts; every POC and goal runs in its own process, in its own worktree.
set -u
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
cd "$T/repo" || exit 1
python3 "$here/skills/workflow-setup/scripts/setup.py" >/dev/null
git switch -q main; git merge -q --no-edit workflow-setup
C=$(cd "$(git rev-parse --git-common-dir)" && pwd); export COMMON="$C"
field() { python3 -c "import json,sys;print(json.load(open(sys.argv[1])).get(sys.argv[2]))" "$C/loop/runs/$1.json" "$2"; }
# A stand-in agent: a POC prints its answer and a go line (and writes a file if the question says WRITE); a goal marks itself done.
cat > "$T/agent.sh" <<'A'
#!/bin/bash
prompt=${!#}
if grep -q 'answering a POC' <<<"$prompt"; then
  slug=$(sed -n 's/.* POC \([a-z0-9-]*\)\.$/\1/p' <<<"$prompt" | head -1)
  echo "$$ $(pwd)" > "$FAKE_AGENT/poc-$slug"
  grep -q 'WRITE' <<<"$prompt" && echo oops > oops.txt
  echo "It works if you add one line."
  echo 'go "Do the thing" --done "The thing works" --done "A test shows it" --level 1 --touches a.py,b.py'
  exit 0
fi
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
$BA add nightly --poc "Can we add one line?" --slug p1 >/dev/null
$BA add nightly --goal "Add g" --done "g works" --slug g1 >/dev/null
$BA add nightly --poc "Does WRITE break it?" --slug p2 >/dev/null
check "add: a named batch heading holds poc and goal lines" 'grep -q "^## Batch: nightly" .loop/queue.md && grep -q "^- poc: p1 |" .loop/queue.md && grep -q "^- slug: g1 |" .loop/queue.md'
check "add: a repeated slug is refused" '$BA add nightly --poc "again" --slug p1 2>&1 | grep -q "^REFUSED"'

echo "== start"
$BA start nightly > "$T/s1"
until_status p1 done && until_status g1 done && until_status p2 failed && ok "start: every line ran" || bad "start: every line ran ($(field p1 status) $(field g1 status) $(field p2 status))"
ppid=; pdir=; gpid=; gdir=
read -r ppid pdir < "$FAKE_AGENT/poc-p1"; read -r gpid gdir < "$FAKE_AGENT/goal-g1"
check "start: no line runs in the governing session" '[ "$ppid" != "$$" ] && [ "$gpid" != "$$" ] && [ "$pdir" != "$T/repo" ] && [ "$gdir" != "$T/repo" ]'
check "start: a poc and a goal run in their own worktrees" '[ "$pdir" != "$gdir" ] && [ -n "$pdir" ] && [ -n "$gdir" ]'

echo "== poc"
check "a POC leaves the repo's files and HEAD alone" '[ "$(git rev-parse HEAD)" = "$head" ] && [ -z "$(git status --porcelain | grep -v queue.md)" ] && [ ! -e oops.txt ]'
check "a POC that writes is marked failed" 'field p2 finding | grep -qi "changed"'
check "a POC saves its answer outside the repo" 'grep -q "add one line" "$C/loop/pocs/p1.md" && [ ! -e .loop/pocs ]'
check "a POC saves its go line outside the repo" 'grep -q "^go \"Do the thing\"" "$C/loop/pocs/p1.go"'
check "a finished POC's worktree is removed" '[ ! -d "$pdir" ]'
check "the board shows the POC finished with its answer" '[ "$(field p1 status)" = done ] && $BO board --out "$T/board" >/dev/null && grep -q "add one line" "$T/board/board.json"'

echo "== promote"
$BA promote p1 --batch nightly > "$T/pr1"
check "promote queues a goal line from the saved go line" 'grep -q "^- slug: p1-go | level: 1 | touches: a.py,b.py | goal: Do the thing | done: The thing works | done: A test shows it" .loop/queue.md'
check "promote under the same heading" 'awk "/^## Batch: nightly/{f=1;next} /^## /{f=0} f&&/p1-go/{found=1} END{exit !found}" .loop/queue.md'
check "promote refuses a POC that has not finished" '$BA promote p2 2>&1 | grep -q "^REFUSED"'
$BA start nightly >/dev/null
until_status p1-go done && ok "a promoted goal runs in its own agent" || bad "a promoted goal runs"

echo "== text and sizes"
for f in skills/workflow-monitoring/references/operation.md skills/workflow-monitoring/SKILL.md skills/workflow-delivery/SKILL.md; do
  check "$f says the operation session governs only" 'grep -qi "governance only" "$here/$f" && grep -qi "runs neither" "$here/$f"'
done
check "every script is under 20 KB" '[ -z "$(find "$here/skills" -name "*.py" -size +20480c)" ]'
check "the test is listed in checks" 'grep -q "test-batch.sh" "$here/.loop/config.json"'
page="$here/docs/wiki/Monitoring.md"
for id in MON-4 MON-5 MON-6 MON-7 MON-8; do
  check "$id is a draft criterion with an Enforced by row" 'grep -q "^- $id: (draft)" "$page" && grep -q "^- $id: $id\$" "$page"'
done
[ "$fails" = 0 ] && echo "ALL PASS" || { echo "$fails FAILED"; exit 1; }
