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

# A toy repo adopted fully (setup, merged), at $1; its folder is named $2 so the propose scrub has a real name to find.
adopted() {
  "$here/dev/toy/make.sh" "$1" >/dev/null || exit 1
  mv "$1/repo" "$1/$2"; (cd "$1/$2" && mkdir -p engine && printf 'def run():\n    return 1\n' > engine/core.py && git add -A && git commit -qm code \
    && python3 "$S/workflow-setup/scripts/setup.py" >/dev/null; git switch -q main; git merge -q --no-edit workflow-setup)
}
E="python3 $S/workflow-docs/scripts/entry.py"

if want entry; then
  adopted "$T/e" brightfield; cd "$T/e/brightfield" || exit 1
  check "setup writes .loop/START.md with the opener and every named part" \
    "grep -q '^## First five minutes' .loop/START.md && for h in Loop Release 'Operation and workers' Docs Regression Health Settings Features 'Settings table'; do grep -qx \"## \$h\" .loop/START.md || exit 1; done"
  check "START.md lists every feature page with how to use it and every repo setting with its value" \
    "grep -q '^| Engine |' .loop/START.md && grep -q '^| \`parallel\` | 0 |' .loop/START.md && ! grep -q '$HOME' .loop/START.md"
  check "entry check passes right after setup" "$E check >/dev/null"
  printf -- '- a new way to use it\n' > /dev/null
  python3 - <<'EOF'
import re
p = "docs/wiki/Engine.md"; t = open(p).read()
t = re.sub(r"(## Usage\n\n)", r"\1- `engine run` runs the engine. It is new.\n", t, count=1) if "## Usage" in t else t.replace("## Requirements", "## Usage\n\n- `engine run` runs the engine. It is new.\n\n## Requirements", 1)
open(p, "w").write(t)
EOF
  git commit -qam "Usage changed"
  out=$($E check); code=$?
  check "a Usage change makes entry check fail STALE (ENTRY_STALE)" "[ $code = 1 ] && grep -q '^STALE .loop/START.md: .*ENTRY_STALE' <<<\"\$out\""
  check "docs.py check fails with it" "! python3 $S/workflow-docs/scripts/docs.py check >/dev/null 2>&1 && python3 $S/workflow-docs/scripts/docs.py check 2>&1 | grep -q '^STALE .loop/START.md'"
  python3 $S/workflow-docs/scripts/docs.py audit >/dev/null 2>&1
  check "docs.py audit regenerates it mechanically, and the check passes again" "$E check >/dev/null && grep -q 'engine run' .loop/START.md"
  rm .loop/START.md
  check "a repo set up before the entry point existed (no template_version) is not failed for lacking one" "$E check >/dev/null"
  python3 -c "import json;p='.loop/config.json';d=json.load(open(p));d['template_version']='0.0.1';json.dump(d,open(p,'w'),indent=2)"
  check "a stamped repo with no entry point fails the check (ENTRY_MISSING)" "$E check | grep -q '^MISSING .loop/START.md'"
  $E write >/dev/null
  mkdir -p "$T/inst"; cp -R "$S/." "$T/inst/"; find "$T/inst" -name __pycache__ -prune -exec rm -rf {} +
  echo '{"version": "9.9.9", "files": {}}' > "$T/inst/workflow-package.json"
  sed -i.bak 's/One session governs and the others build:/One session governs; the others build:/' "$T/inst/workflow-docs/references/start.md"
  out=$(python3 "$T/inst/workflow-docs/scripts/entry.py" check); code=$?
  check "skills newer than the repo's template_version: a narrative difference is LAG and does not fail (ENTRY_LAG)" "[ $code = 0 ] && grep -q '^LAG .loop/START.md: installed v9.9.9, repo v0.0.1' <<<\"\$out\""
  sed -i.bak 's/runs the engine/starts the engine/' docs/wiki/Engine.md
  check "a lagging repo still fails STALE when its own pages change" "! python3 $T/inst/workflow-docs/scripts/entry.py check >/dev/null"
  git checkout -q -- . ; cd "$T"
fi

if want agents; then
  adopted "$T/a" moonbeam; cd "$T/a/moonbeam" || exit 1
  blk() { sed -n '/^<!-- workflow-loop -->/,/^<!-- \/workflow-loop -->/p' "$1" | tr -d '\r'; }
  check "setup wires the same block into CLAUDE.md and AGENTS.md" "[ -n \"\$(blk CLAUDE.md)\" ] && [ \"\$(blk CLAUDE.md)\" = \"\$(blk AGENTS.md)\" ]"
  check "the block points at START.md and names every installed skill" \
    "grep -q 'Read \`.loop/START.md\` first' AGENTS.md && for s in $S/workflow-*; do grep -q \"\\\`\$(basename \$s)\\\`\" AGENTS.md || exit 1; done"
  printf 'My own rules.\r\n\r\n<!-- workflow-loop -->\r\nold\r\n<!-- /workflow-loop -->\r\nAfter the block.\r\n' > CLAUDE.md
  git add -A; git commit -qm "hand edits"
  python3 $S/workflow-setup/scripts/agents.py wire >/dev/null
  check "wire replaces only the block: text outside it and CRLF endings are kept" \
    "head -1 CLAUDE.md | grep -q \$'^My own rules.\r$' && tail -1 CLAUDE.md | grep -q 'After the block.' && [ \"\$(blk CLAUDE.md)\" = \"\$(blk AGENTS.md)\" ]"
  git commit -qam rewired
  check "a second wire changes nothing" "python3 $S/workflow-setup/scripts/agents.py wire | grep -q 'NO CHANGE' && [ -z \"\$(git status --short)\" ]"
  python3 -c "import json;p='.loop/config.json';d=json.load(open(p));d['agent_files']=['AGENTS.md'];json.dump(d,open(p,'w'),indent=2)"
  rm CLAUDE.md; $E write >/dev/null; git add -A; git commit -qm "only AGENTS.md"
  check "agent_files: [AGENTS.md] wires only AGENTS.md and the check ignores CLAUDE.md" \
    "python3 $S/workflow-setup/scripts/agents.py wire | grep -q 'NO CHANGE' && [ ! -e CLAUDE.md ] && $E check >/dev/null"
  cd "$T"
fi

# A template tree at version $2 in $1, its package ZIP $1.zip, and its GitHub-style source archive $1-src.zip.
tmpl() {
  mkdir -p "$1"; cp -R "$here/skills" "$here/listing.json" "$here/README.md" "$here/LICENSE" "$1/"
  find "$1" -name __pycache__ -prune -exec rm -rf {} +
  echo "$2" > "$1/VERSION"; printf '# Changelog\n\n## v%s - 2026-01-01\n\n- change %s\n\n## v1.0.0 - 2026-01-01\n\n- first\n' "$2" "$2" > "$1/CHANGELOG.md"
  [ -n "${3:-}" ] && printf '%s\n' "$3" >> "$1/skills/workflow-setup/SKILL.md"
  python3 "$here/dev/package.py" --root "$1" --out "$1.zip" >/dev/null || exit 1
  (cd "$(dirname "$1")" && rm -rf "src/tmpl-v$2" && mkdir -p src && cp -R "$1" "src/tmpl-v$2" && cd src && zip -qr "$1-src.zip" "tmpl-v$2")
}
install() { rm -rf "$1"; mkdir -p "$1" "$1.x"; unzip -qo "$2" -d "$1.x"; cp -R "$1.x/skills/." "$1/"; cp -R "$1.x/shared/." "$1/"; }

if want update || want propose; then
  tmpl "$T/t1" 1.0.0; tmpl "$T/t2" 1.1.0 "# new in 1.1.0"
  install "$T/inst/skills" "$T/t1.zip"
  U="python3 $T/inst/skills/workflow-setup/scripts/update.py"
  "$here/dev/toy/make.sh" "$T/u" >/dev/null; mv "$T/u/repo" "$T/u/quartzline"; cd "$T/u/quartzline" || exit 1
  python3 "$T/inst/skills/workflow-setup/scripts/setup.py" >/dev/null; git switch -q main; git merge -q --no-edit workflow-setup
  export FAKE_GH_DIR="$T/gh" PATH="$here/dev/toy/fakegh:$PATH"
fi

if want update; then
  check "setup from an installed package stamps template_version" "grep -q '\"template_version\": \"1.0.0\"' .loop/config.json"
  out=$($U --check 2>&1); code=$?
  check "with no template known, the default source refuses with the fix (UPDATE_NO_TEMPLATE)" "[ $code = 2 ] && grep -q 'UPDATE_NO_TEMPLATE' <<<\"\$out\""
  python3 -c "import json;p='.loop/config.json';d=json.load(open(p));d['template_repo']='acme/tmpl';json.dump(d,open(p,'w'),indent=2)"
  python3 $S/workflow-docs/scripts/entry.py write >/dev/null; git commit -qam "template_repo"
  export FAKE_GH_LATEST_TAG=v1.1.0 FAKE_GH_ARCHIVE="$T/t2-src.zip"
  out=$($U --check 2>&1); code=$?
  check "check reads the latest release's source archive: INSTALLED, AVAILABLE, REPO, what's new, the changed file, exit 1" \
    "[ $code = 1 ] && grep -q '^INSTALLED: 1.0.0' <<<\"\$out\" && grep -q '^AVAILABLE: 1.1.0' <<<\"\$out\" && grep -q '^REPO: template_version 1.0.0, older than 1.1.0' <<<\"\$out\" && grep -q 'change 1.1.0' <<<\"\$out\" && grep -q '^update: workflow-setup/SKILL.md' <<<\"\$out\""
  check "check writes nothing" "[ -z \"\$(git status --short)\" ] && ! grep -q 'new in 1.1.0' $T/inst/skills/workflow-setup/SKILL.md"
  echo "my own note" >> CLAUDE.md
  out=$($U --apply 2>&1); code=$?
  check "apply updates the skills and writes the repo half on workflow-update-v1.1.0" \
    "[ $code = 0 ] && grep -q 'new in 1.1.0' $T/inst/skills/workflow-setup/SKILL.md && git show workflow-update-v1.1.0:.loop/config.json | grep -q '\"template_version\": \"1.1.0\"'"
  check "a dirty CLAUDE.md in the checkout stays dirty and out of the update commit" \
    "git status --short | grep -q 'CLAUDE.md' && ! git show workflow-update-v1.1.0:CLAUDE.md | grep -q 'my own note'"
  check "apply writes the template into the installed stamp, so the next default check still finds it" \
    "grep -q '\"repo\": \"acme/tmpl\"' $T/inst/skills/workflow-package.json"
  git checkout -q CLAUDE.md; git merge -q --no-edit workflow-update-v1.1.0
  python3 -c "import json;p='.loop/config.json';d=json.load(open(p));d['template_repo']='';json.dump(d,open(p,'w'),indent=2)"; git commit -qam "no template_repo"
  out=$($U --check 2>&1); code=$?
  check "a second default check, with only the stamp's repo, is UP TO DATE" "[ $code = 0 ] && grep -q 'UP TO DATE' <<<\"\$out\""
  python3 -c "import json;p='.loop/config.json';d=json.load(open(p));d['template_repo']='evil/fork';json.dump(d,open(p,'w'),indent=2)"; git commit -qam "redirect"
  out=$($U --check 2>&1); code=$?
  check "a committed template_repo that differs from the installed stamp's repo is refused (UPDATE_TEMPLATE_MISMATCH)" "[ $code = 2 ] && grep -q 'UPDATE_TEMPLATE_MISMATCH' <<<\"\$out\""
  out=$($U --check --from "$T/t1.zip" --template acme/tmpl 2>&1)
  check "an older AVAILABLE is never a downgrade" "grep -q 'AVAILABLE v1.0.0 is older than INSTALLED v1.1.0: nothing to do' <<<\"\$out\""
  python3 - "$T" <<'EOF'
import sys, zipfile
t = sys.argv[1]
for name, member in (("abs", "/etc/x"), ("dots", "a/../../x")):
    with zipfile.ZipFile("%s/%s.zip" % (t, name), "w") as z:
        z.writestr(member, "x")
with zipfile.ZipFile(t + "/link.zip", "w") as z:
    info = zipfile.ZipInfo("tmpl/skills/workflow-x/SKILL.md"); info.external_attr = 0o120777 << 16; z.writestr(info, "/etc/passwd")
EOF
  bads=0; for z in abs dots link; do $U --check --from "$T/$z.zip" --template acme/tmpl 2>&1 | grep -q UPDATE_BAD_ARCHIVE && bads=$((bads + 1)); done
  check "archives with an absolute path, a .. part or a link are refused before anything is written (UPDATE_BAD_ARCHIVE)" "[ $bads = 3 ]"
  "$here/dev/toy/make.sh" "$T/n" >/dev/null; cd "$T/n/repo"
  out=$($U --apply --from "$T/t2.zip" --template acme/tmpl 2>&1)
  check "a repo whose base branch has no .loop/config.json is skipped (UPDATE_SKIPPED_REPO)" "grep -q 'UPDATE_SKIPPED_REPO' <<<\"\$out\" && [ -z \"\$(git branch --list 'workflow-update-*')\" ]"
  adopted "$T/c" cobaltreef; cd "$T/c/cobaltreef"
  out=$(python3 $S/workflow-setup/scripts/update.py --apply 2>&1)
  check "against a checkout the skills half is skipped (UPDATE_CHECKOUT) and the repo half stamps the checkout's VERSION" \
    "grep -q UPDATE_CHECKOUT <<<\"\$out\" && git show workflow-update-v$(cat $here/VERSION):.loop/config.json | grep -q '\"template_version\": \"$(cat $here/VERSION)\"'"
  cd "$T"
fi

if want propose; then
  cd "$T/u/quartzline"
  check "with no local fix there is nothing to propose (PROPOSE_NONE)" "$U --propose 2>&1 | grep -q PROPOSE_NONE"
  echo "# a local fix" >> "$T/inst/skills/workflow-delivery/SKILL.md"
  out=$($U --check --from "$T/t2.zip" 2>&1)
  check "a skill file edited here shows as LOCAL FIX" "grep -q '^LOCAL FIX: workflow-delivery/SKILL.md' <<<\"\$out\""
  tmpl "$T/t3" 1.2.0
  out=$($U --apply --from "$T/t3.zip" --template acme/tmpl 2>&1)
  check "apply keeps the local fix (KEPT) and saves the package copy it was made on" \
    "grep -q '^KEPT' <<<\"\$out\" && tail -1 $T/inst/skills/workflow-delivery/SKILL.md | grep -q 'a local fix' && [ -f $T/inst/skills/.workflow-kept/workflow-delivery/SKILL.md ]"
  out=$($U --propose --template acme/tmpl 2>&1)
  check "propose previews the issue: the diff of the fix alone, the version, no repo name, nothing filed" \
    "grep -q '^TITLE: Fix from an adopted repo: workflow-delivery/SKILL.md (' <<<\"\$out\" && grep -q '^+# a local fix' <<<\"\$out\" && [ \$(grep -c '^[+-][^+-]' <<<\"\$out\") = 1 ] && ! grep -qi quartzline <<<\"\$out\" && [ ! -f $T/gh/issues.json ]"
  out=$($U --propose --file-issue --template acme/tmpl 2>&1)
  check "--file-issue files one issue on the template with the diff" \
    "grep -q '^FILED: ' <<<\"\$out\" && python3 -c \"import json;i=json.load(open('$T/gh/issues.json'));assert len(i)==1 and i[0]['repo']=='acme/tmpl' and '# a local fix' in i[0]['body']\""
  out=$($U --propose --file-issue --template acme/tmpl 2>&1); code=$?
  check "a second --file-issue files nothing (ALREADY FILED)" "[ $code = 1 ] && grep -q '^ALREADY FILED' <<<\"\$out\" && python3 -c \"import json;assert len(json.load(open('$T/gh/issues.json')))==1\""
  echo "# see quartzline/notes" >> "$T/inst/skills/workflow-delivery/SKILL.md"
  out=$($U --propose --template acme/tmpl 2>&1); code=$?
  check "a fix that names the repo is refused, naming only the kind of match (PROPOSE_SCRUB)" \
    "[ $code = 2 ] && grep -q 'PROPOSE_SCRUB' <<<\"\$out\" && grep -q 'repo folder name' <<<\"\$out\" && ! grep -q 'quartzline' <<<\"\$(grep REFUSED <<<\"\$out\" | sed 's|/[^ ]*propose-[0-9a-f]*.md||')\""
  out=$($U --apply --from "$T/t3.zip" --template acme/tmpl --take workflow-delivery/SKILL.md 2>&1)
  check "--take FILE replaces the local fix with the package copy" "! grep -q 'a local fix' $T/inst/skills/workflow-delivery/SKILL.md && ! $U --check --from $T/t3.zip --template acme/tmpl 2>&1 | grep -q 'LOCAL FIX: workflow'"
  cd "$T"
fi

if want board; then
  tmpl "$T/b1" 1.1.0; install "$T/op/skills" "$T/b1.zip"
  "$here/dev/toy/make.sh" "$T/o" >/dev/null; mv "$T/o/repo" "$T/o/oldharbor"; cd "$T/o/oldharbor" || exit 1
  python3 "$S/workflow-setup/scripts/setup.py" --bare >/dev/null; git switch -q main; git merge -q --no-edit workflow-setup
  python3 -c "import json;p='.loop/config.json';d=json.load(open(p));d['template_version']='1.0.0';json.dump(d,open(p,'w'),indent=2)"; git commit -qam stamp
  "$here/dev/toy/make.sh" "$T/o2" >/dev/null; mv "$T/o2/repo" "$T/o2/newharbor"
  (cd "$T/o2/newharbor" && python3 "$S/workflow-setup/scripts/setup.py" --bare >/dev/null; git switch -q main; git merge -q --no-edit workflow-setup
   python3 -c "import json;p='.loop/config.json';d=json.load(open(p));d['template_version']='1.1.0';json.dump(d,open(p,'w'),indent=2)"; git commit -qam stamp)
  "$here/dev/toy/make.sh" "$T/o3" >/dev/null; mv "$T/o3/repo" "$T/o3/nostamp"
  (cd "$T/o3/nostamp" && python3 "$S/workflow-setup/scripts/setup.py" --bare >/dev/null; git switch -q main; git merge -q --no-edit workflow-setup)
  mkdir -p "$HOME/.workflow-loop"; printf '%s\n%s\n' "$T/o2/newharbor" "$T/o3/nostamp" > "$HOME/.workflow-loop/repos"
  out=$(python3 "$T/op/skills/workflow-monitoring/scripts/live_board.py" 2>&1)
  check "the live board lists a followed repo on an older template under Issues, with the fix" \
    "grep -q '^- oldharbor runs template v1.0.0, older than v1.1.0' <<<\"\$out\" && grep -A1 '^- oldharbor runs' <<<\"\$out\" | grep -q 'fix: ask for workflow-setup update in that repo'"
  check "a repo with no stamp reads template version unknown; one on the current version is not listed" \
    "grep -q '^- nostamp: template version unknown' <<<\"\$out\" && ! grep -q newharbor <<<\"\$out\""
  rm -f "$HOME/.workflow-loop/repos"; cd "$T"
fi

[ "$fails" = 0 ] && echo "ALL PASS${only:+ ($only)}" || { echo "FAILED: $fails"; exit 1; }
