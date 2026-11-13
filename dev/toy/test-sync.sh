#!/bin/bash
# reads: skills/workflow-delivery/scripts/goal.py skills/workflow-delivery/scripts/flow.py
# reads: skills/workflow-delivery/references/default-flow.md
# reads: skills/workflow-setup/scripts/setup.py skills/workflow-setup/scripts/settings.py skills/workflow-setup/scripts/agents.py
# reads: skills/workflow-setup/references/settings.md skills/workflow-docs/scripts/entry.py skills/workflow-docs/scripts/docs.py
# reads: skills/workflow-docs/scripts/audit.py skills/workflow-docs/references/start.md skills/workflow-docs/SKILL.md
# reads: skills/workflow-delivery/SKILL.md skills/workflow-health/SKILL.md skills/workflow-monitoring/SKILL.md
# reads: skills/workflow-regression/SKILL.md skills/workflow-release/SKILL.md skills/workflow-setup/SKILL.md
# reads: dev/toy/make.sh dev/toy/reap.sh
# setup-sync: the built-in flow (issue 47), the generated entry point (SET-5) and the agent files (SET-10); update both
# ways and the board's lag line are in test-sync-update.sh. No model is called.
# usage: test-sync.sh [builtin|entry|agents]   no part runs every part; update, propose and board are in test-sync-update.sh.
set -u
unset LOOP_ROLE LOOP_SESSION LOOP_SESSION_TOOL LOOP_OPERATION_SESSION LOOP_FLOW
here=$(cd "$(dirname "$0")/../.." && pwd)
. "$here/dev/toy/reap.sh"
only=${1:-}
case "$only" in  # an unknown part would run nothing and still say ALL PASS
  ""|builtin|entry|agents) ;;
  update|propose|board) echo "test-sync.sh: the $only part is in dev/toy/test-sync-update.sh; run that instead" >&2; exit 2 ;;
  *) echo "test-sync.sh: no part '$only'; usage: test-sync.sh [builtin|entry|agents]" >&2; exit 2 ;;
esac
T=$(mktemp -d); toy_on_exit 'rm -rf "$T"'
export HOME="$T/home" LOOP_BOARD_HEALTH=green; mkdir -p "$HOME"
fails=0
ok() { echo "PASS: $1"; }
bad() { echo "FAIL: $1"; fails=$((fails + 1)); }
check() { if eval "$2"; then ok "$1"; else bad "$1"; fi; }
want() { [ -z "$only" ] || [ "$only" = "$1" ]; }
DL="$here/skills/workflow-delivery"; SU="$here/skills/workflow-setup"; DO="$here/skills/workflow-docs"; 
G="python3 $DL/scripts/goal.py"; F="python3 $DL/scripts/flow.py"

# A fresh toy repo, set up bare and merged, at $1.
toy() {
  "$here/dev/toy/make.sh" "$1" >/dev/null || exit 1
  (cd "$1/repo" && python3 "$SU/scripts/setup.py" --bare >/dev/null; git switch -q main; git merge -q --no-edit workflow-setup)
}

if want builtin; then
  B="$T/b"; toy "$B"; cd "$B/repo" || exit 1
  # setup's private half fills an empty suite with built-in; a stand-in agent records each prompt and says done.
  printf '#!/bin/bash\nprintf "%%s" "${!#}" > "%s/prompt.$(grep -oE "for the [a-z]+ step" <<<"${!#}" | head -1 | cut -d" " -f3)"\nprintf "DEPTH: full\\nSTEP: done\\n"\n' "$B" > "$B/agent.sh"
  python3 -c "import json;json.dump({'suite':{s:'' for s in ('idea','plan','review','qa','ship')},'command':['bash','$B/agent.sh']},open('$B/flow.json','w'))"
  export LOOP_FLOW="$B/flow.json"
  python3 -c "import sys;sys.path.insert(0,'$SU/scripts');import settings;settings.fill_private('$B/flow.json')"
  check "setup fills a never-configured suite with built-in and leaves no probe" \
    "python3 -c \"import json;d=json.load(open('$B/flow.json'));assert set(d['suite'].values())=={'built-in'} and not d['probe']\""
  check "goal.py new starts a goal with an all-built-in flow and no probe" "$G new bf --here --goal 'Built in' --done 'It works' >/dev/null 2>&1"
  python3 -c "import json;d=json.load(open('$B/flow.json'));d['suite']['plan']='mine';d['steps']={'plan':'mine'};json.dump(d,open('$B/flow.json','w'))"
  out=$(cd "$B/repo" && LOOP_ROLE=worker $F bf idea 2>&1)
  check "a mixed flow whose named-skill step has no probe refuses up front, before any step starts (FLOW_UNRUNNABLE)" \
    "grep -q 'FLOW_UNRUNNABLE' <<<\"\$out\" && grep -q 'plan (mine) has no probe' <<<\"\$out\" && [ ! -e '$B/prompt.idea' ]"
  python3 -c "import json;d=json.load(open('$B/flow.json'));d['suite']['plan']='built-in';d['steps']={};json.dump(d,open('$B/flow.json','w'))"
  for step in idea plan review qa ship; do
    for _ in $(seq 30); do out=$(LOOP_ROLE=worker $F bf $step --wait 5 2>&1); grep -q "^NEXT:" <<<"$out" && break; done
    LOOP_ROLE=worker $G record bf $step --file "$(cd "$(git rev-parse --git-common-dir)" && pwd)/loop/runs/bf.$step.txt" >/dev/null 2>&1
  done
  heads=0; for step in idea plan review qa ship; do
    sec=$(awk -v s="## $step" '$0==s{f=1;next} /^## /{f=0} f&&NF{print;exit}' "$DL/references/default-flow.md")
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

# A toy repo adopted fully (setup, merged), at $1; its folder is named $2 so the propose scrub has a real name to find.
adopted() {
  "$here/dev/toy/make.sh" "$1" >/dev/null || exit 1
  mv "$1/repo" "$1/$2"; (cd "$1/$2" && mkdir -p engine && printf 'def run():\n    return 1\n' > engine/core.py && git add -A && git commit -qm code \
    && python3 "$SU/scripts/setup.py" >/dev/null; git switch -q main; git merge -q --no-edit workflow-setup)
}
E="python3 $DO/scripts/entry.py"

if want entry; then
  adopted "$T/e" brightfield; cd "$T/e/brightfield" || exit 1
  check "setup writes .loop/START.md with the opener and every named part" \
    "grep -q '^## First five minutes' .loop/START.md && for h in Loop Release 'Operation and workers' Docs Regression Health Settings Features 'Settings table'; do grep -qx \"## \$h\" .loop/START.md || exit 1; done"
  check "START.md lists every feature page with how to use it and every repo setting with its value" \
    "grep -q '^| Engine |' .loop/START.md && grep -q '^| \`parallel\` | 0 |' .loop/START.md && ! grep -q '$HOME' .loop/START.md"
  check "entry check passes right after setup" "$E check >/dev/null"
  printf -- '- a new way to use it\n' > /dev/null
  python3 - <<'EOF'
p = "docs/wiki/Engine.md"; t = open(p).read()
open(p, "w").write(t.replace("## Problem\n\n- ", "## Problem\n\n- A new reason to run the engine. ", 1))
EOF
  git commit -qam "Problem changed"
  out=$($E check); code=$?
  check "a Problem change makes entry check fail STALE (ENTRY_STALE)" "[ $code = 1 ] && grep -q '^STALE .loop/START.md: .*ENTRY_STALE' <<<\"\$out\""
  check "docs.py check fails with it" "! python3 $DO/scripts/docs.py check >/dev/null 2>&1 && python3 $DO/scripts/docs.py check 2>&1 | grep -q '^STALE .loop/START.md'"
  python3 $DO/scripts/docs.py audit >/dev/null 2>&1
  check "docs.py audit regenerates it mechanically, and the check passes again" "$E check >/dev/null && grep -q 'A new reason to run the engine' .loop/START.md"
  rm .loop/START.md
  check "a repo set up before the entry point existed (no template_version) is not failed for lacking one" "$E check >/dev/null"
  python3 -c "import json;p='.loop/config.json';d=json.load(open(p));d['template_version']='0.0.1';json.dump(d,open(p,'w'),indent=2)"
  check "a stamped repo with no entry point fails the check (ENTRY_MISSING)" "$E check | grep -q '^MISSING .loop/START.md'"
  $E write >/dev/null
  mkdir -p "$T/inst/workflow-docs/scripts" "$T/inst/workflow-docs/references" "$T/inst/workflow-setup/references"
  cp "$DO/scripts/entry.py" "$T/inst/workflow-docs/scripts/"; cp "$DO/references/start.md" "$T/inst/workflow-docs/references/"
  cp "$DO/SKILL.md" "$T/inst/workflow-docs/"; cp "$SU/references/settings.md" "$T/inst/workflow-setup/references/"
  echo '{"version": "9.9.9", "files": {}}' > "$T/inst/workflow-package.json"
  sed -i.bak 's/One session governs and the others build:/One session governs; the others build:/' "$T/inst/workflow-docs/references/start.md"
  out=$(python3 "$T/inst/workflow-docs/scripts/entry.py" check); code=$?
  check "skills newer than the repo's template_version: a narrative difference is LAG and does not fail (ENTRY_LAG)" "[ $code = 0 ] && grep -q '^LAG .loop/START.md: this repo is at v0.0.1, the template is at v9.9.9' <<<\"\$out\""
  sed -i.bak 's/runs the engine/starts the engine/' docs/wiki/Engine.md
  check "a lagging repo still fails STALE when its own pages change" "! python3 $T/inst/workflow-docs/scripts/entry.py check >/dev/null"
  git checkout -q -- . ; cd "$T"
fi

if want agents; then
  adopted "$T/a" moonbeam; cd "$T/a/moonbeam" || exit 1
  blk() { sed -n '/^<!-- workflow-loop -->/,/^<!-- \/workflow-loop -->/p' "$1" | tr -d '\r'; }
  check "setup wires the same block into CLAUDE.md and AGENTS.md" "[ -n \"\$(blk CLAUDE.md)\" ] && [ \"\$(blk CLAUDE.md)\" = \"\$(blk AGENTS.md)\" ]"
  check "the block points at START.md and names every installed skill" \
    "grep -q 'Read \`.loop/START.md\` first' AGENTS.md && for s in delivery docs health monitoring regression release setup; do grep -q \"\\\`workflow-\$s\\\`\" AGENTS.md || exit 1; done"
  printf 'My own rules.\r\n\r\n<!-- workflow-loop -->\r\nold\r\n<!-- /workflow-loop -->\r\nAfter the block.\r\n' > CLAUDE.md
  git add -A; git commit -qm "hand edits"
  python3 $SU/scripts/agents.py wire >/dev/null
  check "wire replaces only the block: text outside it and CRLF endings are kept" \
    "head -1 CLAUDE.md | grep -q \$'^My own rules.\r$' && tail -1 CLAUDE.md | grep -q 'After the block.' && [ \"\$(blk CLAUDE.md)\" = \"\$(blk AGENTS.md)\" ]"
  git commit -qam rewired
  check "a second wire changes nothing" "python3 $SU/scripts/agents.py wire | grep -q 'NO CHANGE' && [ -z \"\$(git status --short)\" ]"
  python3 -c "import json;p='.loop/config.json';d=json.load(open(p));d['agent_files']=['AGENTS.md'];json.dump(d,open(p,'w'),indent=2)"
  rm CLAUDE.md; $E write >/dev/null; git add -A; git commit -qm "only AGENTS.md"
  check "agent_files: [AGENTS.md] wires only AGENTS.md and the check ignores CLAUDE.md" \
    "python3 $SU/scripts/agents.py wire | grep -q 'NO CHANGE' && [ ! -e CLAUDE.md ] && $E check >/dev/null"
  cd "$T"
fi

[ "$fails" = 0 ] && echo "ALL PASS${only:+ ($only)}" || { echo "FAILED: $fails"; exit 1; }
