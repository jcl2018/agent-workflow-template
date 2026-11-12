#!/bin/bash
# reads: skills/workflow-delivery/references/commands.md skills/workflow-delivery/scripts/flow.py
# reads: skills/workflow-delivery/scripts/goal.py skills/workflow-delivery/scripts/guards.py skills/workflow-delivery/scripts/role.py
# reads: skills/workflow-monitoring/scripts/monitor.py
# reads: skills/workflow-monitoring/scripts/watch.py skills/workflow-release/scripts/merge.py
# reads: skills/workflow-setup/scripts/setup.py
# Test the skill flow, the queue command, version bumps and the governing watch with a fake agent. No model is called.
# usage: test-goal.sh [DIR]
set -u
unset LOOP_SESSION_TOOL LOOP_OPERATION_SESSION  # a toy test never reaches a real session tool
export LOOP_ROLE=worker  # goal.py and flow.py run only in a worker
here=$(cd "$(dirname "$0")/../.." && pwd)
. "$here/dev/toy/reap.sh"
export HOME=$(mktemp -d)  # setup.py writes the private settings under HOME
d=${1:-$(mktemp -d)}; rm -rf "$d"; mkdir -p "$d"
"$here/dev/toy/make.sh" "$d" || exit 1
goal="python3 $here/skills/workflow-delivery/scripts/goal.py"
W="python3 $here/skills/workflow-monitoring/scripts/watch.py"
M="python3 $here/skills/workflow-monitoring/scripts/monitor.py"
export PATH="$here/dev/toy/fakegh:$PATH" FAKE_GH_DIR="$d/gh"
cd "$d/repo" || exit 1
python3 "$here/skills/workflow-setup/scripts/setup.py" --bare >/dev/null
git switch -q main; git merge -q --no-edit workflow-setup; git push -q origin main
fails=0
ok() { echo "PASS: $1"; }
bad() { echo "FAIL: $1"; fails=$((fails + 1)); }
C=$(cd "$(git rev-parse --git-common-dir)" && pwd)
field() { python3 -c "import json,sys;print(json.load(open(sys.argv[1])).get(sys.argv[2]))" "$C/loop/runs/$1.json" "$2"; }
cfg() { python3 - "$@" <<'PY'
import json, sys
c = json.load(open(".loop/config.json"))
for pair in sys.argv[1:]:
    key, _, value = pair.partition("=")
    c[key] = json.loads(value)
json.dump(c, open(".loop/config.json", "w"), indent=2)
PY
}

# A stand-in skill flow: the "skills" print what FAKE_SKILL_OUT says, or STEP: done, and the probe proves the env.
F="python3 $here/skills/workflow-delivery/scripts/flow.py"
cat > "$d/skill.sh" <<'A'
#!/bin/bash
printf '%s' "${!#}" > "$FAKE_SKILL_DIR/prompt-$(date +%s%N)"
printf '%b\n' "${FAKE_SKILL_OUT:-DEPTH: full\nSTEP: done}"
A
mkdir -p "$d/skills-seen"; export FAKE_SKILL_DIR="$d/skills-seen"
python3 - "$d" <<'PY'
import json, sys
d = sys.argv[1]
spec = {"command": ["bash", d + "/skill.sh"], "env": {"FAKE_MODE": "unattended"}, "probe": ["bash", "-c", "echo $FAKE_MODE"],
        "probe_expect": "unattended", "steps": {"idea": "my-idea", "plan": "my-plan", "review": "my-review", "qa": "my-qa",
        "ship": "my-ship"}}
json.dump(spec, open(d + "/flow.json", "w"))
spec["env"] = {"FAKE_MODE": "interactive"}
json.dump(spec, open(d + "/flow-interactive.json", "w"))
PY
export LOOP_FLOW="$d/flow.json"
step() { $F "$1" "$2" --wait 5 >/dev/null; $F "$1" "$2" --wait 10 >/dev/null; $goal record "$1" "$2" --file "$C/loop/runs/$1.$2.txt"; }
flowall() { for s in idea plan review qa ship; do step "$1" $s >/dev/null; done; }

echo "== with no skill flow set, delivery refuses with one line saying how to set it"
for cmd in "$goal new nof --here --goal No --done no" "$goal queue nof --goal No --done no" "$W go No --done no --slug nof" "$F nof idea"; do
  LOOP_FLOW="$d/none.json" $cmd 2>&1 | grep -q "no skill flow is set. Fix: write ~/.workflow-loop/flow.json" || bad "no flow: $cmd"
done
ok "new, queue, go and flow.py each refuse with no flow"

echo "== new needs --here: one session governs"
$goal new blocked --goal "No" --done "no" 2>&1 | grep -q "one session governs" && ok "new refused without --here" || bad "new refused"

echo "== one flow, no levels: a goal starts at the idea step"
out=$($goal new low --here --goal "Add low" --done "calc has low"); echo "$out"
grep -q "step=idea" <<<"$out" && ! grep -qi "level" .loop/goals/low.md && ok "starts at idea, with no level" || bad "start"
$goal new lvl --here --goal "L" --done "l" --level 1 2>&1 | grep -q "unrecognized arguments: --level" && ok "--level is gone" || bad "level flag"

echo "== a step runs only in the flow's unattended mode"
LOOP_FLOW="$d/flow-interactive.json" $F low idea 2>&1 | grep -q "wouldn't run unattended" && [ ! -e "$C/loop/runs/low.idea.txt" ] && ok "a probe that isn't unattended starts nothing" || bad "probe guard"
step low idea | grep -q "NEXT: flow.py low plan" && ok "idea recorded, plan next" || bad "idea"
p=$(ls -t "$FAKE_SKILL_DIR"/prompt-* | head -1)
grep -q "Use the my-idea skill" "$p" && grep -q "Approve nothing, merge nothing and push nothing" "$p" && ok "the step names the private skill and approves nothing" || bad "prompt"
grep -rq "my-idea" .loop && bad "skill name in the repo" || ok "the skill's name stays out of the repo"
echo "STEP: done" > "$d/forged.txt"
$goal record low plan --file "$d/forged.txt" 2>&1 | grep -q "wasn't run by flow.py" && ok "record refuses a reply flow.py didn't run" || bad "forged reply"
step low plan | grep -q "NEXT: build, then flow.py low review" && ok "plan recorded, build next" || bad "plan"
printf '\n\ndef low():\n    return 1\n' >> calc.py; git commit -qam "Add low"
$goal pr low 2>&1 | grep -q "the flow hasn't finished: review, qa, ship" && ok "pr refuses until the flow ends" || bad "pr early"

echo "== what a step leaves for the owner waits on the owner; a failed step is a try"
FAKE_SKILL_OUT='PENDING: approve the plan as written\nSTEP: pending' step low review | grep -q "WAITING low" && [ "$(field low status)" = waiting ] && ok "a pending decision waits" || bad "pending"
python3 -c "import json,sys;w=json.load(open(sys.argv[1]))['waiting'];assert 'approve the plan' in w['ask'] and w['words']==['go on low','stop low']" "$C/loop/runs/low.json" && ok "Waiting on you gets the decision and the words" || bad "waiting fields"
$goal answer low >/dev/null
FAKE_SKILL_OUT='STEP: failed the tests would not run' step low review | grep -q "TRY 1 OF 3 FAILED: review failed" && ok "a failed step costs a try" || bad "failed step"
FAKE_SKILL_OUT='nothing useful' step low review | grep -q "gave no STEP line" && ok "no STEP line costs a try" || bad "no step line"
step low review >/dev/null
FAKE_SKILL_OUT='DEPTH: full\nSTEP: skipped no browser on this machine' step low qa | grep -q "RECORDED qa skipped: no browser" && ok "a skipped step says why" || bad "skipped"
step low ship >/dev/null
$goal pr low | grep -q "^PR " && ok "pr once every step is done or skipped" || bad "pr"
grep -q -- "- qa: skipped: no browser on this machine" "$FAKE_GH_DIR/calls.log" && ok "the pull request lists each step's result" || bad "pr body"
git switch -q main

echo "== PENDING: none, nothing, n/a and an empty PENDING line never make a goal wait; a real item still does"
pnall=1; pn=0
for reply in 'PENDING: none' 'PENDING: nothing' 'PENDING: **none**' 'PENDING: n/a' 'PENDING:'; do
  pn=$((pn + 1)); git switch -q main; $goal new pn$pn --here --goal "Add pn$pn" --done "calc has pn$pn" >/dev/null
  out=$(FAKE_SKILL_OUT="$reply\nDEPTH: full\nSTEP: done" step pn$pn idea 2>&1)
  if grep -q "^RECORDED idea" <<<"$out" && grep -q "^NEXT: flow.py pn$pn plan" <<<"$out" && [ "$(field pn$pn status)" = running ] \
     && [ "$(field pn$pn waiting)" = None ] && python3 -c "import json,sys;f=json.load(open(sys.argv[1]))['flow']['idea'];assert f.startswith('done') and 'DEPTH' not in f and 'STEP' not in f" "$C/loop/runs/pn$pn.json"; then :; else
    pnall=0; bad "PENDING reply [$reply] made the goal wait or swallowed the next line: ${out:0:160}"; fi
done
[ $pnall = 1 ] && ok "PENDING none, nothing, **none**, n/a and empty record and go on"
git switch -q main; $goal new pnmix --here --goal "Add pnmix" --done "calc has pnmix" >/dev/null
out=$(FAKE_SKILL_OUT='PENDING: none\nPENDING: approve the plan\nDEPTH: full\nSTEP: done' step pnmix idea 2>&1)
python3 -c "import json,sys;w=json.load(open(sys.argv[1]))['waiting'];assert 'approve the plan' in w['ask'] and 'none' not in w['ask'].lower()" "$C/loop/runs/pnmix.json" && grep -q "WAITING pnmix" <<<"$out" \
  && ok "a real PENDING item among none lines still waits, with its own ask" || bad "mixed none and real item: ${out:0:160}"
git switch -q main; $goal new pnedge --here --goal "Add pnedge" --done "calc has pnedge" >/dev/null
FAKE_SKILL_OUT='PENDING: none\nDEPTH: full' step pnedge idea 2>&1 | grep -q "gave no STEP line" && ok "PENDING: none with no STEP line is a failed try, not a wait" || bad "none with no STEP line"
FAKE_SKILL_OUT='PENDING: none\nDEPTH: full\nSTEP: pending' step pnedge idea 2>&1 | grep -q "WAITING pnedge" && ok "PENDING: none with STEP: pending still waits (the step asked to)" || bad "none with STEP: pending"
python3 - "$here/skills/workflow-delivery/scripts" <<'PY' && ok "pending_items drops none, n/a, no decisions and bare punctuation and keeps none left" || bad "pending_items values"
import sys
sys.path.insert(0, sys.argv[1]); import guards as g
cases = {"PENDING: none left": ["none left"], "PENDING: N/A.": [], "PENDING: No decisions": [], "PENDING: --": [], "PENDING:": [],
         "PENDING: approve the plan": ["approve the plan"], "  - PENDING: pick a name": ["pick a name"], "PENDING: none\r\nSTEP: done": [],
         "PENDING:\nDEPTH: full": []}
bad = {k: g.pending_items(k) for k, v in cases.items() if g.pending_items(k) != v}
assert not bad, bad
PY
git switch -q main
for s in pn1 pn2 pn3 pn4 pn5 pnmix pnedge; do rm -f "$C/loop/runs/$s".*; git branch -q -D "loop/$s" 2>/dev/null; done  # the goals above were only for the cases; later cases count running goals

echo "== goal.py keeps room under 20 KB, and has no checks step"
[ "$(wc -c < "$here/skills/workflow-delivery/scripts/goal.py")" -lt 19500 ] && ok "goal.py keeps room under 20 KB" || bad "goal.py size"
$goal check low 2>&1 | grep -q "invalid choice" && ok "goal.py has no check command" || bad "check command"
git switch -q main

echo "== queue adds a line a watcher can read"
$goal queue fix-a --goal "Fix a" --done "a is fixed" --touches "a.py" | grep -q QUEUED && ok "queued" || bad "queue"
grep -q '^- slug: fix-a | touches: a.py | goal: Fix a | done: a is fixed$' .loop/queue.md && ok "valid line" || bad "queue line"
$goal queue fix-a --goal "Fix a" --done "x" 2>&1 | grep -q "already exists" && ok "duplicate refused" || bad "duplicate"
$goal queue pipe --goal "a|b" --done "x" 2>&1 | grep -q "no |" && ok "pipe refused" || bad "pipe"
$M report | grep -q "fix-a" && ok "report reads it" || bad "report queue"
git checkout -q -- .loop/queue.md

echo "== done lines stay frozen, 3 failed tries stop a goal, nothing merges"
git switch -q main
$goal new frz --here --goal "Add frz" --done "calc has frz" >/dev/null
sed -i.bak 's/calc has frz/calc has something else/' .loop/goals/frz.md; rm .loop/goals/frz.md.bak; git commit -qam "Change a done line"
$goal pr frz >/dev/null 2>&1; rc=$?
[ "$rc" = 3 ] && [ "$(field frz status)" = stopped ] && ok "a changed done line stops the goal" || bad "frozen done line ($rc $(field frz status))"
git checkout -q -- . ; git switch -q main
$goal new tries --here --goal "Add tries" --done "calc has tries" >/dev/null
for n in 1 2 3; do FAKE_SKILL_OUT='STEP: failed no' step tries idea >/dev/null 2>&1; rc=$?; done
[ "$rc" = 3 ] && [ "$(field tries status)" = stopped ] && grep -q "tries: Failed 3 tries" .loop/findings.md && ok "three failed tries stop the goal with a finding" || bad "3 tries ($rc $(field tries status))"
git checkout -q -- . ; git switch -q main
MG="python3 $here/skills/workflow-release/scripts/merge.py"
$MG low 2>&1 | grep -q "REFUSED: auto_merge is off in this repo, so the owner merges" && ! grep -q "^pr merge" "$FAKE_GH_DIR/calls.log" && ok "with auto_merge off, merge.py refuses and nothing merges" || bad "merge gate"

echo "== no gates: auto_approve and auto_merge on, in this repo only"
git switch -q main
cp .loop/config.json "$d/cfg.gated"
cfg 'auto_approve=true' 'auto_merge=true'; git commit -qam "No gates"; git push -q origin main
$goal new open --here --goal "Add open" --done "calc has open" >/dev/null
FAKE_SKILL_OUT='PENDING: approve the design\nDEPTH: full\nSTEP: pending' step open idea | grep -q "AUTO-APPROVED open idea: approve the design" && ok "a pending decision is auto-approved" || bad "auto-approve"
[ "$(field open status)" = running ] && grep -q "auto-approved" "$C/loop/runs/open.json" && python3 -c "import json,sys;s=json.load(open(sys.argv[1]));assert s['note']['text'].startswith('auto-approved at idea')" "$C/loop/runs/open.json" && ok "logged and on the board as auto-approved, nothing waits" || bad "auto-approve log"
for s2 in plan review qa ship; do step open $s2 >/dev/null; done
printf '\n\ndef open_():\n    return 1\n' >> calc.py; git commit -qam "Add open"; verify open
out=$($goal pr open); grep -q "^PR " <<<"$out" && grep -q "NEXT: workflow-release merges it: merge.py open" <<<"$out" && ok "pr opens with no checks and names the merge step" || bad "pr no gates: $out"
FAKE_GH_PR_STATE=OPEN python3 "$here/skills/workflow-release/scripts/merge.py" open | grep -q "^MERGED" && grep -q "^pr merge .* --merge" "$FAKE_GH_DIR/calls.log" && [ "$(field open release)" = cut ] && ok "auto_merge: the release step merges the pull request and releases it" || bad "auto merge"
git fetch -q origin; git switch -q main; git merge -q --ff-only origin/main
FAKE_GH_PR_STATE=CLOSED python3 "$here/skills/workflow-release/scripts/merge.py" open 2>&1 | grep -q "is CLOSED, not open" && ok "a closed pull request is not merged" || bad "closed pr"
git switch -q main; $goal new ng --here --goal "Add ng" --done "calc has ng" >/dev/null
out=$(FAKE_SKILL_OUT='PENDING: none\nDEPTH: full\nSTEP: done' step ng idea 2>&1)
grep -q "^RECORDED idea" <<<"$out" && ! grep -q "AUTO-APPROVED" <<<"$out" && ok "auto_approve: PENDING none records and is never reported as auto-approved" || bad "auto_approve with PENDING none: ${out:0:160}"
git switch -q main; rm -f "$C/loop/runs/ng".*; git branch -q -D loop/ng 2>/dev/null
cp "$d/cfg.gated" .loop/config.json; git commit -qam "Gates back on" >/dev/null; git push -q origin main

echo "== the Delivery commands reference names every goal.py command and flag"
missing=""
for word in $(python3 "$here/skills/workflow-delivery/scripts/goal.py" -h | sed -n '/^  new /,/^  show /p' | awk '{print $1}') $(grep -oE 'add_argument\("--[a-z]+"' "$here/skills/workflow-delivery/scripts/goal.py" | cut -d'"' -f2 | sort -u); do
  grep -q -- "$word" "$here/skills/workflow-delivery/references/commands.md" || missing="$missing $word"
done
[ -z "$missing" ] && ok "page lists them" || bad "page lacks:$missing"

echo "== pr_bumps_version moves the last number once"
echo 1.3.3.3 > VERSION; git add -A; git commit -qm "Version"; git push -q origin main
cfg 'pr_bumps_version=true'; git commit -qam "Bump config"; git push -q origin main
$goal new bump --here --goal "Add bump" --done "calc has bump" >/dev/null
printf '\n\ndef bump():\n    return 1\n' >> calc.py; git commit -qam "Add bump"
flowall bump; $goal pr bump >/dev/null
[ "$(cat VERSION)" = "1.3.3.4" ] && ok "VERSION bumped" || bad "bump: $(cat VERSION)"
[ "$(git log -1 --format=%s)" = "Bump version to 1.3.3.4" ] && ok "bump commit" || bad "bump commit"
[ "$(git show origin/loop/bump:VERSION)" = "1.3.3.4" ] && ok "bump pushed" || bad "bump push"
$goal pr bump >/dev/null; [ "$(cat VERSION)" = "1.3.3.4" ] && ok "second pr doesn't bump again" || bad "double bump"
git switch -q main
cfg 'pr_bumps_version=false'; git commit -qam "Bump off"; git push -q origin main

echo "== a failed push is retried, and a final failure prints git's error"
hook="$d/origin.git/hooks/pre-receive"
printf '#!/bin/bash\n[ -e "%s/pushed-once" ] && exit 0\ntouch "%s/pushed-once"\necho "busy, try again" >&2\nexit 1\n' "$d" "$d" > "$hook"
chmod +x "$hook"
$goal new retry --here --goal "Add retry" --done "calc has retry" >/dev/null
printf '\n\ndef retry():\n    return 1\n' >> calc.py; git commit -qam "Add retry"
flowall retry
$goal pr retry | grep -q "^PR " && ok "second push worked" || bad "retry"
git switch -q main
printf '#!/bin/bash\necho "the remote said no" >&2\nexit 1\n' > "$hook"
$goal new nopush --here --goal "Add nopush" --done "calc has nopush" >/dev/null
printf '\n\ndef nopush():\n    return 1\n' >> calc.py; git commit -qam "Add nopush"
flowall nopush
$goal pr nopush > "$d/np" 2>&1; rc=$?
[ $rc != 0 ] && grep -q "the remote said no" "$d/np" && ok "final failure prints git's error" || bad "push error"
rm -f "$hook"; git switch -q main

echo "== go starts a background agent; the governing process writes no code"
cat > "$d/agent.sh" <<'A'
#!/bin/bash
# A stand-in agent. It records its prompt, then does what the files in $d say.
prompt=${!#}
slug=$(grep -oE 'Slug: [a-z0-9-]+' <<<"$prompt" | head -1 | cut -d' ' -f2)
[ -n "$slug" ] || slug=$(grep -oE 'goal [a-z0-9-]+ in this git' <<<"$prompt" | head -1 | cut -d' ' -f2)
n=$(ls "$FAKE_AGENT"/prompt-"$slug"-* 2>/dev/null | wc -l | tr -d ' ')
printf '%s' "$prompt" > "$FAKE_AGENT/prompt-$slug-$n"
pwd > "$FAKE_AGENT/pwd-$slug"
b="$FAKE_AGENT/behave-$slug"
if [ -f "$b" ] && [ "$(sed -n "$((n + 1))p" "$b")" = fail ]; then echo "agent crashed: it could not find calc"; exit 1; fi
if [ -f "$b" ] && [ "$(sed -n "$((n + 1))p" "$b")" = limit ]; then echo "error: usage limit reached"; exit 1; fi
python3 - "$COMMON/loop/runs/$slug.json" <<'PY'
import json, sys
s = json.load(open(sys.argv[1])); s["status"] = "done"; s["step"] = "release"; s["pr"] = "https://example.test/pull/1"
json.dump(s, open(sys.argv[1], "w"))
PY
A
export FAKE_AGENT="$d/fake" COMMON="$C"; mkdir -p "$FAKE_AGENT"
cfg "agent_command=[\"bash\", \"$d/agent.sh\"]" 'parallel=2'
git commit -qam "Agent"; git push -q origin main
head0=$(git rev-parse HEAD)
$W go "Add alpha" --done "alpha works" --touches a.py --slug alpha | tee "$d/g1"
grep -q "STARTED alpha" "$d/g1" && ok "go started it" || bad "go"
$W go "Add beta" --done "beta works" --touches b.py --slug beta >/dev/null
$W go "Add gamma" --done "gamma works" --touches c.py --slug gamma >/dev/null
$W go "Add delta please" --done "delta works" --touches c.py >/dev/null
grep -q '^- slug: add-delta-please |' .loop/queue.md && ok "slug made from the goal" || bad "slug"
$W go "Bad" 2>&1 | grep -q "REFUSED" && ok "go needs a done line" || bad "go done"
$W watch --interval 0.2 --skill-dir "$here/skills" | tee "$d/w1"  # lanes: no read (watch only prints the path)
grep -q "NOTHING LEFT" "$d/w1" && ok "watch ended by itself" || bad "watch end"
for s in alpha beta gamma add-delta-please; do [ "$(field $s status)" = done ] || bad "$s status"; done
ok "every goal finished"
[ "$(git rev-parse HEAD)" = "$head0" ] && [ -z "$(git status --porcelain -- calc.py)" ] && ok "governing checkout wrote no code" || bad "governor wrote code"
[ "$(cat "$FAKE_AGENT/pwd-alpha")" != "$(cat "$FAKE_AGENT/pwd-beta")" ] && ok "each goal has its own worktree" || bad "worktree"
case "$(cat "$FAKE_AGENT/pwd-alpha")" in */loop/worktrees/alpha) ok "worktree under loop/";; *) bad "worktree path";; esac
grep -q "Start at step 2, the idea step" "$FAKE_AGENT/prompt-alpha-0" && ok "a goal starts at the idea step" || bad "prompt step"

echo "== mender: one fresh agent, told only the finding and the log"
printf 'fail\nfail\nfail\n' > "$FAKE_AGENT/behave-mendme"
cfg 'mend=true' 'mend_wait=0'
$W go "Mend me" --done "mended" --slug mendme >/dev/null
$W watch --interval 0.2 --skill-dir "$here/skills" | tee "$d/w2"  # lanes: no read (watch only prints the path)
[ "$(ls "$FAKE_AGENT"/prompt-mendme-* | wc -l | tr -d ' ')" = 2 ] && ok "one mend, then it stops" || bad "mend count"
grep -q "could not find calc" "$FAKE_AGENT/prompt-mendme-1" && grep -q "WHY IT STOPPED" "$FAKE_AGENT/prompt-mendme-1" && ok "mender got the finding and log" || bad "mend prompt"
grep -q "NEEDS YOU mendme" "$d/w2" && ok "still failed goal reported" || bad "needs you"
printf 'fail\nok\n' > "$FAKE_AGENT/behave-mendok"
$W go "Mend ok" --done "mended" --slug mendok >/dev/null
$W watch --interval 0.2 --skill-dir "$here/skills" >/dev/null  # lanes: no read (watch only prints the path)
[ "$(field mendok status)" = done ] && [ "$(field mendok mended)" = True ] && ok "mended goal finished" || bad "mend ok"

echo "== usage limit: waits, resumes, and doesn't use up the mend"
printf 'limit\nok\n' > "$FAKE_AGENT/behave-limited"
cfg 'mend=false' 'resume_on_limit=true' 'limit_wait=2'
$W go "Limited" --done "resumed" --slug limited >/dev/null
sleep 1
$W watch --once --skill-dir "$here/skills" | tee "$d/w3"  # lanes: no read (watch only prints the path)
[ "$(field limited status)" = failed ] && grep -q "usage limit" "$d/w3" && ok "first pass waits" || bad "limit wait"
$W watch --interval 0.3 --skill-dir "$here/skills" | tee "$d/w4"  # lanes: no read (watch only prints the path)
[ "$(field limited status)" = done ] && [ "$(field limited limit_resumes)" = 1 ] && ok "resumed after the wait" || bad "limit resume"
[ "$(field limited mended)" = None ] && ok "limit didn't use the mend" || bad "limit mend"
printf 'fail\n' > "$FAKE_AGENT/behave-off"
cfg 'resume_on_limit=false'
$W go "Off" --done "x" --slug off >/dev/null
$W watch --interval 0.2 --skill-dir "$here/skills" >/dev/null  # lanes: no read (watch only prints the path)
[ "$(ls "$FAKE_AGENT"/prompt-off-* | wc -l | tr -d ' ')" = 1 ] && ok "both off: no relaunch" || bad "off"

echo "== report still works beside watch"
$M report | grep -q "alpha" && ok "report" || bad "report"
$M dashboard >/dev/null && ok "dashboard" || bad "dashboard"

[ "$fails" = 0 ] && echo "ALL PASS" || { echo "$fails FAILED"; exit 1; }
