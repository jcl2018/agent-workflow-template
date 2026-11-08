#!/bin/bash
# Proves assign -> worker loop -> report-back -> board with a stand-in agent. No model is called. usage: test-workers.sh [DIR]
# The operation session only assigns, watches and reports; each worker runs its own loop and sends its result back.
set -u
here=$(cd "$(dirname "$0")/../.." && pwd)
T=${1:-$(mktemp -d)}; rm -rf "${T:?}"; mkdir -p "$T"
S="$here/skills/workflow-monitoring/scripts"
BA="python3 $S/batch.py"; W="python3 $S/watch.py"; M="python3 $S/monitor.py"; BO="python3 $S/board.py"
export HOME="$T/home" FAKE_AGENT="$T/fake"; mkdir -p "$HOME" "$FAKE_AGENT"
fails=0
ok() { echo "PASS: $1"; }
bad() { echo "FAIL: $1"; fails=$((fails + 1)); }
check() { if eval "$2"; then ok "$1"; else bad "$1"; fi; }
"$here/dev/toy/make.sh" "$T" >/dev/null || exit 1
export LOOP_FLOW="$T/flow.json"
mkdir -p "$T/bin"; cat > "$T/bin/gh" <<'GH'
#!/bin/bash
case "$*" in
  api*milestones*) echo '[{"title":"Alpha","open_issues":1,"closed_issues":3},{"title":"Beta","open_issues":3,"closed_issues":1}]';;
  *pull/1*) echo MERGED;; *) echo "gh: no answer" >&2; exit 1;;
esac
GH
chmod +x "$T/bin/gh"; export PATH="$T/bin:$PATH"
cd "$T/repo" || exit 1
python3 "$here/skills/workflow-setup/scripts/setup.py" >/dev/null
git switch -q main; git merge -q --no-edit workflow-setup
C=$(cd "$(git rev-parse --git-common-dir)" && pwd); export COMMON="$C"
field() { python3 -c "import json,sys;d=json.load(open(sys.argv[1])).get(sys.argv[2]);print(d)" "$C/loop/runs/$1.json" "$2"; }
inner() { python3 -c "import json,sys;d=json.load(open(sys.argv[1])).get(sys.argv[2]) or {};print(d.get(sys.argv[3]))" "$C/loop/runs/$1.json" "$2" "$3"; }
# A stand-in agent: g1 lands its pull request, h1 ends without finishing, w1 waits on the owner.
cat > "$T/agent.sh" <<'A'
#!/bin/bash
prompt=${!#}
slug=$(grep -oE 'Slug: [a-z0-9-]+' <<<"$prompt" | head -1 | cut -d' ' -f2)
echo "$$ ${LOOP_ROLE:-} $(pwd)" > "$FAKE_AGENT/goal-$slug"
python3 - "$COMMON/loop/runs/$slug.json" "$slug" <<'PY'
import json, sys
s = json.load(open(sys.argv[1])); slug = sys.argv[2]
if slug == "g1":
    s.update(status="done", step="release", pr="https://x/pull/1")
elif slug == "w1":
    s.update(status="waiting", step="plan", waiting={"ask": "Which database?", "words": ["use sqlite", "use postgres"]})
json.dump(s, open(sys.argv[1], "w"))
PY
A
python3 - "$T/agent.sh" <<'PY'
import json, sys
c = json.load(open(".loop/config.json")); c["agent_command"] = ["bash", sys.argv[1]]; c["parallel"] = 4; c["mend"] = False
json.dump(c, open(".loop/config.json", "w"), indent=2)
PY
git commit -qam "Agent"; git push -q origin main
until_report() { for _ in $(seq 150); do [ "$(inner "$1" report status)" = "$2" ] && return 0; sleep 0.1; done; return 1; }

echo "== the operation session refuses to work"
for verb in build plan idea review qa ship step check pr; do
  check "watch.py $verb refuses with one line naming the worker command" '[ "$($W $verb x 2>&1)" = "REFUSED: $verb is worker work; the operation session only assigns, watches and reports. Use: batch.py start NAME" ]'
done
check "batch.py plan refuses the same way" '$BA plan x 2>&1 | grep -q "^REFUSED: plan is worker work.*batch.py start NAME$"'
check "a worker is not refused" 'LOOP_ROLE=worker $W build x 2>&1 | grep -q "invalid choice"'

echo "== assign a batch, one worker each"
$BA add night --goal "Add g" --done "g works" --slug g1 >/dev/null
$BA add night --goal "Add h" --done "h works" --slug h1 >/dev/null
$BA add night --goal "Add w" --done "w works" --slug w1 >/dev/null
head=$(git rev-parse HEAD)
$BA start night > "$T/start"
until_report g1 merged && until_report h1 failed && until_report w1 waiting && ok "every worker reported back" || bad "every worker reported back ($(inner g1 report status) $(inner h1 report status) $(inner w1 report status))"
for g in g1 h1 w1; do read -r pid role dir < "$FAKE_AGENT/goal-$g"; eval "pid_$g=$pid role_$g=$role dir_$g=$dir"; done
check "each goal ran in its own process and worktree, as a worker" '[ "$pid_g1" != "$pid_h1" ] && [ "$pid_h1" != "$pid_w1" ] && [ "$dir_g1" != "$dir_h1" ] && [ "$dir_h1" != "$dir_w1" ] && [ "$role_g1$role_h1$role_w1" = workerworkerworker ] && [ "$pid_g1" != "$$" ]'
check "the operation checkout is unchanged" '[ "$(git rev-parse HEAD)" = "$head" ] && [ -z "$(git status --porcelain | grep -v queue.md)" ]'
check "merged carries its pull request" '[ "$(inner g1 report pr)" = "https://x/pull/1" ] && inner g1 report text | grep -q "worker g1 reports merged (https://x/pull/1)"'
check "failed says why, and waiting carries the words" 'inner h1 report text | grep -q "worker h1 reports failed" && inner w1 report text | grep -q "use sqlite or use postgres"'
$BO board --out "$T/b" > "$T/board.out"
check "the board shows each report as the run's message" 'python3 -c "import sys,json
import json,sys
r={x[\"slug\"]:x for x in json.load(open(sys.argv[1]))[\"runs\"]}
assert \"reports merged\" in r[\"g1\"][\"report\"] and \"reports failed\" in r[\"h1\"][\"report\"] and \"reports waiting\" in r[\"w1\"][\"report\"]" "$T/b/board.json"'

echo "== the status block"
$M report > "$T/report"
check "five sections in the fixed order" 'python3 -c "import sys,json
t=open(sys.argv[1]).read()
at=[t.index(\"== %s ==\" % n) for n in (\"Needs you\",\"Now\",\"Next\",\"Roadmap\",\"Goals\")]
assert at==sorted(at) and at[0] < t.index(\"SLUG\")" "$T/report"'
needs=$(sed -n '/== Needs you ==/,/== Now ==/p' "$T/report")
check "Needs you holds the failed and the waiting worker, with the exact words" 'grep -q "h1 (failed)" <<<"$needs" && grep -q "answer: resume h1" <<<"$needs" && grep -q "w1 (waiting): Which database?" <<<"$needs" && grep -q "answer: use sqlite" <<<"$needs" && grep -q "answer: use postgres" <<<"$needs" && ! grep -q "g1" <<<"$needs"'
check "board prints the same block" 'grep -q "== Needs you ==" "$T/board.out" && grep -q "answer: use sqlite" "$T/board.out"'
$M dashboard > "$T/dash.path"; dash=$(cat "$T/dash.path")
check "the dashboard carries the same block, Needs you first" 'python3 -c "import sys,json
h=open(sys.argv[1]).read()
at=[h.index(\"<h2>%s</h2>\" % n) for n in (\"Needs you\",\"Now\",\"Next\",\"Roadmap\",\"Goals\")]
assert at==sorted(at) and \"answer: use sqlite\" in h and \"h1 (failed)\" in h" "$dash"'
check "a stuck worker stays at the top until it is answered" '$M report | sed -n "/== Needs you ==/,/== Now ==/p" | grep -q "w1 (waiting)"'
python3 - "$C/loop/runs/w1.json" <<'PY'
import json, sys
s = json.load(open(sys.argv[1])); s["status"], s["waiting"], s["pid"] = "running", None, None
json.dump(s, open(sys.argv[1], "w"))
PY
after=$($M report | sed -n '/== Needs you ==/,/== Now ==/p')
check "answered, it leaves Needs you; the failed one stays" '! grep -q "w1" <<<"$after" && grep -q "h1 (failed)" <<<"$after"'
check "Roadmap has a bar for each milestone and overall" 'grep -q "Alpha \[########--\] 3 of 4" "$T/report" && grep -q "Beta \[##--------\] 1 of 4" "$T/report" && grep -q "overall \[#####-----\] 4 of 8" "$T/report"'
check "Goals lists the done lines met so far" 'grep -q "g1: 1 of 1 done lines met" "$T/report" && grep -q "h1: 0 of 1 done lines met" "$T/report"'
python3 "$S/worker.py" met h1 1 >/dev/null
check "a worker marks a done line met" '$M report | grep -q "h1: 1 of 1 done lines met"'

echo "== estimates"
python3 - "$C/loop/runs" $$ <<'PY'
import json, os, sys
d = sys.argv[1]
def stamp(m): return "2026-01-01T%02d:%02dZ" % divmod(m, 60) if False else "2026-01-01T10:%02d:00Z" % m
past = {"slug": "past", "goal": "Past", "status": "done", "step": "release", "pr": "", "tries": 0, "updated": stamp(40), "log": [
    stamp(0) + " queued", stamp(10) + " idea auto-approved: x", stamp(30) + " plan auto-approved: x", stamp(40) + " build"]}
json.dump(past, open(os.path.join(d, "past.json"), "w"))
now = {"slug": "cur", "goal": "Cur", "status": "running", "step": "idea", "pid": int(sys.argv[2]), "pr": "", "tries": 0, "updated": "2026-01-01T10:00:00Z",
       "log": [stamp(0) + " queued"]}
json.dump(now, open(os.path.join(d, "cur.json"), "w"))
PY
$M report > "$T/report2"
cur=$(sed -n '/- cur:/,/== Next ==/p' "$T/report2")
check "a running goal shows each step with an estimate from past runs" 'grep -q "idea   est 10m, no estimate yet tokens" <<<"$cur" && grep -q "plan   est 20m" <<<"$cur"'
check "a step nobody has finished says no estimate yet" 'grep -q "review est no estimate yet" <<<"$cur"'
check "actual time and tokens so far are shown, unknown when unrecorded" 'grep -Eq "idea .*\| actual [0-9<].*, unknown tokens" <<<"$cur"'
check "the remaining steps have an estimate" 'grep -q "remaining steps: est" <<<"$cur"'
rm "$C/loop/runs/past.json"
check "with no past runs the remaining estimate reads no estimate yet" '$M report | grep -q "remaining steps: no estimate yet"'
rm "$C/loop/runs/cur.json"

echo "== one way to run"
check "go has no --session" '$W go "x" --done y --session 2>&1 | grep -q "unrecognized arguments: --session"'
check "batch add has no --session" '$BA add night --goal x --done y --session 2>&1 | grep -q "unrecognized arguments: --session"'
check "board.py has no take or session" '! $BO take g1 2>&1 | grep -q TAKEN && $BO session add x --repo r 2>&1 | grep -q "invalid choice"'
check "a grep finds nothing for the old upgrade paths" '[ -z "$(grep -rniE --exclude=test-workers.sh -- "--session|board.py take|session (add|update|remove) |visible session|hand_over|sessions\.json|taken over" "$here/skills" "$here/docs/wiki" "$here/README.md" "$here/listing.json" "$here/dev/toy")" ]'
check "every script is under 20 KB" '[ -z "$(find "$here/skills" -name "*.py" -size +20479c)" ]'
echo; [ "$fails" = 0 ] && echo "ALL PASS" || { echo "$fails FAILED"; exit 1; }
