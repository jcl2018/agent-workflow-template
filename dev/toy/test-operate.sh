#!/bin/bash
# Proves the operation loop with a stand-in agent: the dependency-graph planner, the base merge before a pull request, the one
# operate command, the worker guard, live reports and follow-ups, the status block and token records. No model is called.
# usage: test-operate.sh [DIR]
set -u
unset LOOP_ROLE  # these tests act as the operation session; workers get LOOP_ROLE=worker where they need it
here=$(cd "$(dirname "$0")/../.." && pwd)
T=${1:-$(mktemp -d)}; rm -rf "${T:?}"; mkdir -p "$T"
M="$here/skills/workflow-monitoring/scripts"; D="$here/skills/workflow-delivery/scripts"
W="python3 $M/watch.py"; OP="python3 $M/operate.py"; BO="python3 $M/board.py"; BA="python3 $M/batch.py"
goal="env LOOP_ROLE=worker python3 $D/goal.py"; F="env LOOP_ROLE=worker python3 $D/flow.py"
export HOME="$T/home" FAKE_AGENT="$T/fake" FAKE_GH_DIR="$T/gh" GOAL="$D/goal.py"; mkdir -p "$HOME" "$FAKE_AGENT"
fails=0
ok() { echo "PASS: $1"; }
bad() { echo "FAIL: $1"; fails=$((fails + 1)); }
check() { if eval "$2"; then ok "$1"; else bad "$1"; fi; }
"$here/dev/toy/make.sh" "$T" >/dev/null || exit 1
export LOOP_FLOW="$T/flow.json" PATH="$here/dev/toy/fakegh:$PATH"
cd "$T/repo" || exit 1
python3 "$here/skills/workflow-setup/scripts/setup.py" --bare >/dev/null
git switch -q main; git merge -q --no-edit workflow-setup; git push -q origin main
C=$(cd "$(git rev-parse --git-common-dir)" && pwd); export COMMON="$C"
field() { python3 -c "import json,sys;print(json.load(open(sys.argv[1])).get(sys.argv[2]))" "$C/loop/runs/$1.json" "$2"; }
sets() { python3 - "$C/loop/runs/$1.json" "${@:2}" <<'PY'
import json, sys
s = json.load(open(sys.argv[1]))
for pair in sys.argv[2:]:
    key, _, value = pair.partition("=")
    s[key] = json.loads(value)
json.dump(s, open(sys.argv[1], "w"))
PY
}
until_file() { for _ in $(seq 150); do [ -e "$1" ] && return 0; sleep 0.1; done; return 1; }
until_status() { for _ in $(seq 150); do [ "$(field "$1" status)" = "$2" ] && return 0; sleep 0.1; done; return 1; }
until_text() { for _ in $(seq 150); do grep -q -- "$2" "$1" 2>/dev/null && return 0; sleep 0.1; done; return 1; }

# A stand-in agent: it steps through plan and build as a worker, polls for a message while held, then finishes.
cat > "$T/agent.sh" <<'A'
#!/bin/bash
prompt=${!#}
slug=$(grep -oE 'Slug: [a-z0-9-]+' <<<"$prompt" | head -1 | cut -d' ' -f2)
echo "$$ ${LOOP_ROLE:-} $(pwd)" > "$FAKE_AGENT/ran-$slug"
python3 "$GOAL" step "$slug" plan >/dev/null
python3 "$GOAL" step "$slug" build --tokens 1500 >/dev/null
while [ -e "$FAKE_AGENT/hold-$slug" ]; do
  if [ -e "$FAKE_AGENT/pick-$slug" ]; then rm "$FAKE_AGENT/pick-$slug"; python3 "$GOAL" step "$slug" build >> "$FAKE_AGENT/seen-$slug" 2>&1; fi
  sleep 0.1
done
python3 - "$COMMON/loop/runs/$slug.json" <<'PY'
import json, sys
s = json.load(open(sys.argv[1])); s.update(status="done", step="release")
json.dump(s, open(sys.argv[1], "w"))
PY
A
python3 - "$T/agent.sh" <<'PY'
import json, sys
c = json.load(open(".loop/config.json")); c["agent_command"] = ["bash", sys.argv[1]]; c["parallel"] = 2; c["mend"] = False
json.dump(c, open(".loop/config.json", "w"), indent=2)
PY
printf 'Shared\tshared.py\n' > .loop/docs.tsv
git add -A; git commit -qm "Agent"; git push -q origin main

echo "== MON-1 carries the owner's wording, reviewed"
check "MON-1 is the dependency-graph wording and Reviewed 2026-11-08" 'grep -q "^- MON-1: \*\*Reviewed 2026-11-08\*\* Roles, start and planning. One command starts the operation session and drives the whole process the same way every time. The operation session plans queued goals as a dependency graph and runs every goal whose dependencies are met in parallel, each in its own worker and worktree, and never builds. A goal waits only on goals it truly depends on; sharing files is not a reason to wait: the later goal brings in the earlier one.s merged changes and runs its checks again, and only a real conflict sends it back to fix. <!-- reviewed [0-9a-f]\{8\} -->$" "$here/docs/wiki/Monitoring.md"'

echo "== a goal waits only for the goals it depends on"
touch "$FAKE_AGENT/hold-a" "$FAKE_AGENT/hold-c"
$W go "Add a" --done "a works" --touches shared.py --slug a > "$T/ga"
$W go "Add b" --done "b works" --touches shared.py --depends-on a --slug b > "$T/gb"
$W go "Add c" --done "c works" --touches shared.py --slug c > "$T/gc"
$W go "Add d" --done "d works" --slug d > "$T/gd"
until_file "$FAKE_AGENT/ran-a" && until_file "$FAKE_AGENT/ran-c"
check "a goal with a dependency queues, saying what it waits on" 'grep -q "QUEUED b: waits on a (running)" "$T/gb" && [ ! -e "$C/loop/runs/b.json" ]'
check "a goal that shares its files with a running goal still starts" 'grep -q "^STARTED c" "$T/gc" && [ "$(field c status)" = running ]'
check "the parallel limit in config.json holds the next goal" 'grep -q "QUEUED d: slots full (2 of 2)" "$T/gd"'
check "queue lines carry depends-on" 'grep -q "^- slug: b | touches: shared.py | depends-on: a | goal: Add b" .loop/queue.md'
$W go "Add x" --done "x" --depends-on nosuch --slug x 2>&1 | grep -q "depends-on nosuch is not a goal" && ok "an unknown dependency is refused" || bad "unknown dependency"
rm "$FAKE_AGENT/hold-a"; until_status a done
$OP run --once > "$T/op1" 2>&1
check "done is not merged: the dependent goal still waits" '[ ! -e "$C/loop/runs/b.json" ]'
check "a free slot starts the goal that was waiting for one" 'until_status d done || [ -e "$C/loop/runs/d.json" ]'
until_status d done

echo "== the status block"
python3 "$M/board_status.py" > "$T/block"
nxt=$(sed -n '/== Roadmap ==/,/== Total ==/p' "$T/block")
check "Roadmap holds queued goals with what they wait on, and goals waiting to merge" 'grep -q "\[queued\] b .*<- waits on a" <<<"$nxt" && grep -q "\[awaiting merge\] a " <<<"$nxt" && grep -q "waiting to merge" <<<"$nxt"'
check "Roadmap marks a running goal" 'grep -q "\[running\] c " <<<"$nxt"'
sets a 'release="merged"'; sets d 'release="merged"'
python3 "$M/board_status.py" > "$T/block2"
check "Roadmap counts merged goals per feature" 'sed -n "/== Roadmap ==/,/== Total ==/p" "$T/block2" | grep -q -- "- Shared: 1 merged goal$" && sed -n "/== Roadmap ==/,/== Total ==/p" "$T/block2" | grep -q -- "- other: 1 merged goal$"'
check "merged goals leave the waiting-to-merge list" 'grep -q "\[merged\] a " "$T/block2" && ! grep -q "waiting to merge" "$T/block2"'

echo "== workers report as they go"
check "each change of step is reported as it happens" 'python3 -c "import json,sys;r=json.load(open(sys.argv[1]))[\"reports\"];assert [x[\"step\"] for x in r][-2:]==[\"plan\",\"build\"] and \"worker c: step build\" in r[-1][\"text\"] and r[-1][\"at\"],r" "$C/loop/runs/c.json"'
(cd "$C/loop/worktrees/c" && $goal wait c --ask "Which database?" --words "use sqlite" >/dev/null)
check "a change of status is reported too" 'python3 -c "import json,sys;r=json.load(open(sys.argv[1]))[\"reports\"];assert r[-1][\"status\"]==\"waiting\",r" "$C/loop/runs/c.json"'
(cd "$C/loop/worktrees/c" && $goal answer c >/dev/null)
check "and the answer" 'python3 -c "import json,sys;r=json.load(open(sys.argv[1]))[\"reports\"];assert r[-1][\"status\"]==\"running\",r" "$C/loop/runs/c.json"'
check "the agent's tokens are recorded against its step" 'python3 -c "import json,sys;assert json.load(open(sys.argv[1]))[\"tokens\"][\"build\"]==1500" "$C/loop/runs/c.json" && python3 "$M/board_status.py" | grep -Eq "build .*\| actual .*, 2k tokens"'

echo "== the operation session sends a worker a follow-up"
$OP send c "use sqlite, then add the index" > "$T/send"
check "send files the message for the worker" 'grep -q "^SENT to c: use sqlite" "$T/send" && grep -q "use sqlite, then add the index" "$C/loop/inbox/c.txt"'
touch "$FAKE_AGENT/pick-c"; until_file "$FAKE_AGENT/seen-c"; until_text "$FAKE_AGENT/seen-c" "MESSAGE FROM THE OPERATION SESSION"
check "the worker's agent sees it the next time goal.py runs, once" 'grep -q "^MESSAGE FROM THE OPERATION SESSION.*use sqlite, then add the index" "$FAKE_AGENT/seen-c" && [ ! -e "$C/loop/inbox/c.txt" ] && grep -q "add the index" "$C/loop/inbox/c.read"'
$OP send nosuch hi 2>&1 | grep -q "no run named nosuch" && ok "send refuses a goal that doesn't exist" || bad "send nosuch"

echo "== goal steps refuse outside a worker"
for verb in "step c build" "check c" "record c idea --file x" "pr c"; do
  out=$(python3 "$D/goal.py" $verb 2>&1)
  check "goal.py ${verb%% *} refuses, naming the worker command" '[ "$out" = "REFUSED: ${verb%% *} is worker work; the operation session only assigns, watches and reports. Use: batch.py start NAME" ]'
done
for step in idea plan review qa ship; do
  out=$(python3 "$D/flow.py" c $step 2>&1)
  check "flow.py $step refuses, naming the worker command" '[ "$out" = "REFUSED: flow.py $step is worker work; the operation session only assigns, watches and reports. Use: batch.py start NAME" ]'
done
check "a worker is not refused" 'env LOOP_ROLE=worker python3 "$D/goal.py" step nosuch build 2>&1 | grep -q "no goal named nosuch"'

echo "== one operate command runs the loop"
$BO cadence 2 >/dev/null
$BA add night --goal "Add g" --done "g works" --slug g >/dev/null
$W go "Add f" --done "f works" --depends-on c --slug f >/dev/null
$OP run --poll 0.1 > "$T/op.out" 2>&1 & oppid=$!
until_text "$T/op.out" "== Needs you =="
check "it starts a batch line by itself" 'until_file "$C/loop/runs/g.json"'
check "the first pass prints the status block, on the cadence from board.py cadence" 'grep -q "== Total ==" "$T/op.out" && grep -q "^NEXT_DELAY 120$" "$T/op.out"'
sleep 4  # the pass's own starts are seen once more, then it is quiet
lines=$(wc -l < "$T/op.out"); quiet=$(grep -c "^NO_CHANGE" "$T/op.out"); blocks=$(grep -c "== Needs you ==" "$T/op.out"); sleep 1.5
check "nothing is printed while nothing changes" '[ "$(wc -l < "$T/op.out")" = "$lines" ]'
touch "$C/loop/runs/c.json"
until_text "$T/op.out" "^NO_CHANGE" ; for _ in $(seq 50); do [ "$(grep -c "^NO_CHANGE" "$T/op.out")" -gt "$quiet" ] && break; sleep 0.1; done
check "a worker's report wakes it before the cadence, and one line says nothing changed" '[ "$(grep -c "^NO_CHANGE" "$T/op.out")" = $((quiet + 1)) ] && [ "$(grep -c "== Needs you ==" "$T/op.out")" = "$blocks" ]'
(cd "$C/loop/worktrees/c" && $goal step c review >/dev/null)
until_text "$T/op.out" "step: build -> review"
check "a change prints the status block and the CHANGE line" 'grep -q "^CHANGE .*c step: build -> review" "$T/op.out" && [ "$(grep -c "== Needs you ==" "$T/op.out")" -ge 2 ]'
rm "$FAKE_AGENT/hold-c"; until_status c done
sets c 'release="merged"'
for _ in $(seq 200); do kill -0 $oppid 2>/dev/null || break; sleep 0.1; done
check "a merged dependency starts the goal that waited, and it ends when nothing is left" '! kill -0 $oppid 2>/dev/null && [ -e "$C/loop/runs/f.json" ] && grep -q "^NOTHING LEFT TO OPERATE" "$T/op.out"'
kill $oppid 2>/dev/null
touch "$FAKE_AGENT/hold-h"; $W go "Add h" --done "h works" --slug h >/dev/null; $BO cadence off >/dev/null
timeout 30 $OP run --poll 0.1 2>&1 | grep -q "^CADENCE OFF" && ok "with the cadence off it stops and says so" || bad "cadence off"
rm "$FAKE_AGENT/hold-h"; $BO cadence 10 >/dev/null
check "the operation checkout never ran a goal step" '[ "$(cut -d" " -f2 "$FAKE_AGENT/ran-a")" = worker ] && [ "$(cut -d" " -f3 "$FAKE_AGENT/ran-a")" != "$T/repo" ]'

echo "== the latest base is merged before the pull request"
git switch -q main
flowall() { for s in idea plan review qa ship; do step "$1" $s >/dev/null; $goal check "$1" >/dev/null; done; }
step() { $F "$1" "$2" --wait 5 >/dev/null; $F "$1" "$2" --wait 10 >/dev/null; $goal record "$1" "$2" --file "$C/loop/runs/$1.$2.txt"; }
$goal new s1 --here --goal "S1" --done "s1" >/dev/null; echo s1 > s1.txt; git add s1.txt; git commit -qm s1
FAKE_SKILL_OUT='used 4,200 tokens\nSTEP: done' step s1 idea >/dev/null
check "a flow step records the tokens its agent reported" 'python3 -c "import json,sys;assert json.load(open(sys.argv[1]))[\"tokens\"][\"idea\"]==4200" "$C/loop/runs/s1.json"'
flowall s1; git switch -q main
$goal new s2 --here --goal "S2" --done "s2" >/dev/null; printf '# from s2\n' >> calc.py; git commit -qam s2; flowall s2; git switch -q main
other="$T/other"; git clone -q "$T/origin.git" "$other"
( cd "$other" && git config user.email t@example.test && git config user.name Toy && echo n1 > n1.txt && printf '# from main\n' >> calc.py && git add -A && git commit -qm "Main moves" && git push -q origin main )
git switch -q loop/s1
out=$($goal pr s1 2>&1); echo "$out" | sed 's/^/  /'
check "a clean merge reruns the checks and goes on, costing no try" 'grep -q "^MERGED origin/main into the branch; running the checks again" <<<"$out" && grep -q "^PR " <<<"$out" && [ "$(field s1 tries)" = 0 ] && [ -e n1.txt ]'
git switch -q loop/s2
out=$($goal pr s2 2>&1); echo "$out" | sed 's/^/  /'
check "a real conflict costs a try, names the files and leaves the tree clean" 'grep -q "^TRY 1 OF 3 FAILED: merging main conflicts in: calc.py" <<<"$out" && [ "$(field s2 tries)" = 1 ] && [ ! -e "$(git rev-parse --git-dir)/MERGE_HEAD" ] && [ -z "$(git status --porcelain --untracked-files=no)" ]'
git merge -q -X theirs --no-edit origin/main >/dev/null 2>&1; $goal check s2 >/dev/null
out=$($goal pr s2 2>&1)
check "once the conflict is merged by hand it goes on without another try" 'grep -q "^PR " <<<"$out" && [ "$(field s2 tries)" = 1 ]'
git switch -q main

echo "== sizes"
check "every script is under 20 KB" '[ -z "$(find "$here/skills" -name "*.py" -size +20479c)" ]'
echo; [ "$fails" = 0 ] && echo "ALL PASS" || { echo "$fails FAILED"; exit 1; }
