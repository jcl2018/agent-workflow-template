#!/bin/bash
# reads: skills/ dev/
# setup-sync: the built-in flow (issue 47), the generated entry point (SET-5), the agent files (SET-10), update both
# ways and the board's lag line (SET-4). No model is called; gh is the toy fake.
# usage: test-sync.sh [builtin|entry|agents|update|propose|board]   no part runs every part.
set -u
unset LOOP_ROLE LOOP_SESSION LOOP_SESSION_TOOL LOOP_OPERATION_SESSION LOOP_FLOW
here=$(cd "$(dirname "$0")/../.." && pwd)
. "$here/dev/toy/reap.sh"
only=${1:-}
T=$(mktemp -d); toy_on_exit 'rm -rf "$T"'
export HOME="$T/home" LOOP_BOARD_HEALTH=green; mkdir -p "$HOME"
fails=0
ok() { echo "PASS: $1"; }
bad() { echo "FAIL: $1"; fails=$((fails + 1)); }
check() { if eval "$2"; then ok "$1"; else bad "$1"; fi; }
want() { [ -z "$only" ] || [ "$only" = "$1" ]; }
S="$here/skills"
G="python3 $S/workflow-delivery/scripts/goal.py"; F="python3 $S/workflow-delivery/scripts/flow.py"

# A fresh toy repo, set up bare and merged, at $1.
toy() {
  "$here/dev/toy/make.sh" "$1" >/dev/null || exit 1
  (cd "$1/repo" && python3 "$S/workflow-setup/scripts/setup.py" --bare >/dev/null; git switch -q main; git merge -q --no-edit workflow-setup)
}

if want builtin; then
  B="$T/b"; toy "$B"; cd "$B/repo" || exit 1
  # setup's private half fills an empty suite with built-in; a stand-in agent records each prompt and says done.
  printf '#!/bin/bash\nprintf "%%s" "${!#}" > "%s/prompt.$(grep -oE "for the [a-z]+ step" <<<"${!#}" | head -1 | cut -d" " -f3)"\nprintf "DEPTH: full\\nSTEP: done\\n"\n' "$B" > "$B/agent.sh"
  python3 -c "import json;json.dump({'suite':{s:'' for s in ('idea','plan','review','qa','ship')},'command':['bash','$B/agent.sh']},open('$B/flow.json','w'))"
  export LOOP_FLOW="$B/flow.json"
  python3 -c "import sys;sys.path.insert(0,'$S/workflow-setup/scripts');import settings;settings.fill_private('$B/flow.json')"
  check "setup fills a never-configured suite with built-in and leaves no probe" \
    "python3 -c \"import json;d=json.load(open('$B/flow.json'));assert set(d['suite'].values())=={'built-in'} and not d['probe']\""
  check "goal.py new starts a goal with an all-built-in flow and no probe" "$G new bf --here --goal 'Built in' --done 'It works' >/dev/null 2>&1"
  python3 -c "import json;d=json.load(open('$B/flow.json'));d['suite']['plan']='mine';d['steps']={'plan':'mine'};json.dump(d,open('$B/flow.json','w'))"
  check "watch reads the suite too: an all-built-in suite with no steps is a flow that is set" \
    "python3 -c \"import sys;sys.path.insert(0,'$S/workflow-monitoring/scripts');import os;os.environ['LOOP_FLOW']='$B/flow.json';import watch;assert watch.flow_set()\""
  out=$(cd "$B/repo" && LOOP_ROLE=worker $F bf idea 2>&1)
  check "a mixed flow whose named-skill step has no probe refuses up front, before any step starts (FLOW_UNRUNNABLE)" \
    "grep -q 'FLOW_UNRUNNABLE' <<<\"\$out\" && grep -q 'plan (mine) has no probe' <<<\"\$out\" && [ ! -e '$B/prompt.idea' ]"
  python3 -c "import json;d=json.load(open('$B/flow.json'));d['suite']['plan']='built-in';d['steps']={};json.dump(d,open('$B/flow.json','w'))"
  for step in idea plan review qa ship; do
    for _ in $(seq 30); do out=$(LOOP_ROLE=worker $F bf $step --wait 5 2>&1); grep -q "^NEXT:" <<<"$out" && break; done
    LOOP_ROLE=worker $G record bf $step --file "$(cd "$(git rev-parse --git-common-dir)" && pwd)/loop/runs/bf.$step.txt" >/dev/null 2>&1
  done
  heads=0; for step in idea plan review qa ship; do
    sec=$(awk -v s="## $step" '$0==s{f=1;next} /^## /{f=0} f&&NF{print;exit}' "$S/workflow-delivery/references/default-flow.md")
    grep -qF "$sec" "$B/prompt.$step" 2>/dev/null && grep -q "built-in routine for the $step step" "$B/prompt.$step" && heads=$((heads + 1))
  done
  check "each headless built-in step's prompt carries its routine from default-flow.md in place of a skill name" "[ $heads = 5 ]"
  R="$(cd "$(git rev-parse --git-common-dir)" && pwd)/loop/runs/bf.json"
  check "an all-built-in goal records every flow step done" \
    "python3 -c \"import json;f=json.load(open('$R'))['flow'];assert all(str(f.get(s,'')).startswith('done') for s in ('idea','plan','review','qa','ship')),f\""
  git switch -q main; $G new bs --here --goal 'In session' --done 'It works' >/dev/null 2>&1
  python3 -c "import json;p='$(dirname "$R")/bs.json';d=json.load(open(p));d['worker']='session';json.dump(d,open(p,'w'))"
  out=$(LOOP_ROLE=worker $F bs idea 2>&1)
  check "in a worker session a built-in step prints IN SESSION with the routine and needs no command" \
    "grep -q \"^IN SESSION idea: no headless agent; run delivery's built-in routine\" <<<\"\$out\" && grep -q 'design.md' <<<\"\$out\""
  rm -f "$B/flow.json"
  git switch -q main; out=$($G new nf --here --goal 'No flow' --done 'x' 2>&1)
  check "with no flow file a goal still refuses to start" "grep -q 'no skill flow is set' <<<\"\$out\""
  unset LOOP_FLOW
fi

[ "$fails" = 0 ] && echo "ALL PASS${only:+ ($only)}" || { echo "FAILED: $fails"; exit 1; }
