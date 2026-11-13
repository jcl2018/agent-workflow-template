#!/bin/bash
# reads: skills/
# Adopt a fresh toy repo, then update its skills. usage: test-adopt.sh [SET-1..SET-5]   no ID runs every part. No model is called.
set -u
unset GITHUB_SERVER_URL GITHUB_REPOSITORY GITHUB_RUN_ID  # run cells and rendered Tests never depend on the runner
unset LOOP_SESSION_TOOL LOOP_OPERATION_SESSION  # a toy test never reaches a real session tool
here=$(cd "$(dirname "$0")/../.." && pwd); only=${1:-}
. "$here/dev/toy/reap.sh"
d=$(mktemp -d); toy_on_exit 'rm -rf "$d"'
no() { echo "FAIL ${only:-adopt}: $1"; exit 1; }
want() { [ -z "$only" ] || [ "$only" = "$1" ]; }
setup="python3 $here/skills/workflow-setup/scripts/setup.py"

"$here/dev/toy/make.sh" "$d/toy" >/dev/null || exit 1
cd "$d/toy/repo" || exit 1
mkdir engine docs docs/wiki
printf 'def run():\n    return 1\n' > engine/core.py
printf 'This page was written by hand and has no sections.\n\nIt keeps every word.\n' > docs/wiki/Home.md
printf '# Guide\n\n## Steps\n\nHand-made sections.\n' > docs/wiki/Guide.md
git add -A; git commit -qm "Existing docs and a code folder"

# SET-1 and SET-2: dry run prints the findings and the plan and writes nothing; the run writes on a branch and adapts pages.
if want SET-1 || want SET-2; then
  out=$($setup --dry-run) || no "dry run failed"
  for want in "FOUND: existing repo" "add: docs/wiki/Engine.md" "convert: docs/wiki/Home.md" "no fit: docs/wiki/Guide.md" "add: .github/workflows/regression.yml" "DRY RUN"; do
    echo "$out" | grep -q "$want" || no "dry run does not say '$want'"
  done
  [ -z "$(git status --short)" ] && [ "$(git branch --show-current)" = main ] && [ ! -d .loop ] || no "dry run wrote something"
  $setup >/dev/null; [ -d .loop ] || no "setup failed"  # a bare agent_command is a gap (exit 0), never a refusal
  [ "$(git branch --show-current)" = workflow-setup ] || no "not on the setup branch"
  for f in .loop/config.json .loop/docs.tsv .loop/regression.tsv .github/workflows/regression.yml docs/wiki/Engine.md docs/wiki/Home.md; do
    [ -f "$f" ] || no "missing $f"
  done
  grep -q '"criteria": true' .loop/config.json || no "criteria not on in the config"
  head -1 docs/wiki/Home.md | grep -q 'workflow-docs' || no "Home has no marker"
  grep -q 'It keeps every word.' docs/wiki/Home.md || no "Home lost its words"
  [ "$(head -1 docs/wiki/Guide.md)" = "# Guide" ] || no "Guide was touched"
  grep -q 'ENG-1' docs/wiki/Engine.md && grep -q 'eng-checks' .loop/regression.tsv || no "Engine has no criterion and row"
  grep -q 'Tests' docs/wiki/Engine.md && grep -q 'hom-checks' docs/wiki/Home.md || no "Tests tables not rendered"
  [ -z "$(git status --short)" ] || no "setup left the tree dirty"
  again=$($setup)
  echo "$again" | grep -q "NO CHANGE" && [ -z "$(git status --short)" ] || no "second run changed something"
  echo "PASS SET-1 SET-2: adopted and adapted, second run changes nothing"
fi

mk() { # mk DIR VERSION: a package tree at that version
  mkdir -p "$1"; cp -R "$here/skills" "$here/listing.json" "$here/README.md" "$here/LICENSE" "$1/"
  find "$1" -name __pycache__ -prune -exec rm -rf {} +  # earlier tests may have left bytecode in the checkout
  echo "$2" > "$1/VERSION"; printf '# Changelog\n\n## v%s - 2026-01-01\n\n- change %s\n\n## v1.0.0 - 2026-01-01\n\n- first\n' "$2" "$2" > "$1/CHANGELOG.md"
}
pk="python3 $here/dev/package.py"
# Only SET-3 (the package's contents) and SET-4/SET-5 (installing from it) read v1.zip. SET-1 and SET-2 adopt from this
# checkout's skills directly, so they never build the package and never fail on its rules.
if want SET-3 || want SET-4 || want SET-5; then
  mk "$d/v1" 1.0.0; $pk --root "$d/v1" --out "$d/v1.zip" >/dev/null || no "v1 package refused"
fi

# SET-3: the package carries its version, every skill and the guide; it installs by copying.
if want SET-3; then
  unzip -p "$d/v1.zip" PACKAGE.json | grep -q '"version": "1.0.0"' || no "no version in the package"
  for skill in "$here"/skills/workflow-*; do unzip -l "$d/v1.zip" | grep -q "skills/$(basename $skill)/SKILL.md" || no "$(basename $skill) missing"; done
  unzip -l "$d/v1.zip" | grep -q "shared/loop-files.md" || no "no design guide"
  big=$(find "$here/skills" -name '*.py' -size +20479c); [ -z "$big" ] || no "script over 20 KB: $big"
  # installed by copying, then a skill runs from the copy: every skill's scripts compile, and setup plans a dry run
  mkdir -p "$d/x3" "$d/agent3"; unzip -q "$d/v1.zip" -d "$d/x3"; cp -R "$d/x3/skills/." "$d/agent3/"
  for py in "$d"/agent3/workflow-*/scripts/*.py; do python3 -c "import sys;compile(open(sys.argv[1],'rb').read(),sys.argv[1],'exec')" "$py" 2>/dev/null || no "an installed script does not compile: $py"; done
  dry=$(python3 "$d/agent3/workflow-setup/scripts/setup.py" --dry-run 2>&1) && echo "$dry" | grep -q "DRY RUN" || no "the installed setup skill does not run: $dry"
  echo "PASS SET-3: versioned package, every skill, scripts under 20 KB, installs by copying and a skill runs"
fi

# SET-4: update --check shows what is new and writes nothing; update applies the skills, then the repo half on its own
# branch, keeping config values, pages and private settings. SET-5: the guide is installed and setup wrote START.md.
if want SET-4 || want SET-5; then
  [ -d .loop ] || $setup >/dev/null  # run alone, SET-4 and SET-5 adopt first
  git switch -q main && git merge -q --no-edit workflow-setup || no "setup branch did not merge"
  mkdir -p "$d/agent/skills" "$d/x1"; unzip -q "$d/v1.zip" -d "$d/x1"
  cp -R "$d/x1/skills/." "$d/agent/skills/"; cp -R "$d/x1/shared/." "$d/agent/skills/"
  if want SET-5; then
    [ -f "$d/agent/skills/loop-files.md" ] && grep -q "Operation and workers" "$d/agent/skills/loop-files.md" || no "the guide is missing or empty"
    [ -f .loop/START.md ] && grep -q "^## First five minutes" .loop/START.md || no "setup wrote no START.md with its opener"
    for h in Loop Release "Operation and workers" Docs Regression Health Settings Features; do grep -qx "## $h" .loop/START.md || no "START.md has no $h part"; done
    echo "PASS SET-5: guide installed, START.md with the opener and every part"
  fi
fi
if want SET-4; then
  mkdir -p .claude; echo '{"private": true}' > .claude/settings.local.json; git add -f .claude/settings.local.json; git commit -qm "Private settings" >/dev/null 2>&1
  pages() { (cd "$d/toy/repo" && git show "$1":docs/wiki/Home.md; git show "$1":docs/wiki/Engine.md; git show "$1":.claude/settings.local.json) | shasum; }
  keys() { (cd "$d/toy/repo" && git show "$1":.loop/config.json) | python3 -c "import json,sys;d=json.load(sys.stdin);d.pop('template_version',None);d.pop('_help',None);print(json.dumps(d,sort_keys=True))"; }
  before=$(pages main); kbefore=$(keys main)
  mk "$d/v2" 1.1.0; echo "# extra" >> "$d/v2/skills/workflow-setup/SKILL.md"; $pk --root "$d/v2" --out "$d/v2.zip" >/dev/null || no "v2 package refused"
  up="python3 $d/agent/skills/workflow-setup/scripts/update.py --from $d/v2.zip"
  out=$($up --check); [ $? = 1 ] || no "check of a newer version does not exit 1"; echo "$out" > "$d/check.out"
  echo "$out" | grep -q "INSTALLED: 1.0.0" && echo "$out" | grep -q "AVAILABLE: 1.1.0" && echo "$out" | grep -q "change 1.1.0" && echo "$out" | grep -q "update: workflow-setup/SKILL.md" || no "check does not show the version and the change"
  echo "$out" | grep -q "^REPO: template_version unknown, older than 1.1.0" || no "check does not show the repo version: $(cat $d/check.out)"
  echo "$out" | grep -q "change 1.0.0" && no "check shows an entry the repo already has"
  cmp -s "$d/agent/skills/workflow-setup/SKILL.md" "$here/skills/workflow-setup/SKILL.md" && [ -z "$(git status --short)" ] || no "check wrote something"
  out=$($up --apply) || no "update failed: $out"
  tail -1 "$d/agent/skills/workflow-setup/SKILL.md" | grep -q "# extra" || no "skill not updated"
  grep -q '"version": "1.1.0"' "$d/agent/skills/workflow-package.json" || no "stamp not moved"
  [ "$(git branch --show-current)" = main ] && [ -z "$(git status --short)" ] || no "update changed the checkout"
  git rev-parse -q --verify workflow-update-v1.1.0 >/dev/null || no "no commit on workflow-update-v1.1.0"
  [ "$(pages workflow-update-v1.1.0)" = "$before" ] && [ "$(keys workflow-update-v1.1.0)" = "$kbefore" ] || no "update changed a page, a config value or private settings"
  git show workflow-update-v1.1.0:.loop/config.json | grep -q '"template_version": "1.1.0"' || no "template_version not stamped"
  extra=$(git diff --name-only main workflow-update-v1.1.0 | grep -vxE '\.loop/config\.json|\.loop/START\.md|CLAUDE\.md|AGENTS\.md')
  [ -z "$extra" ] || no "the update branch changed hand-written data: $extra"
  git show workflow-update-v1.1.0:.loop/START.md >/dev/null 2>&1 || no "no START.md on the update branch"
  echo "$out" | grep -q "^NEXT: merge workflow-update-v1.1.0 into main" || no "no NEXT merge line"
  tip=$(git rev-parse workflow-update-v1.1.0)
  $up --apply | grep -q "^PENDING: workflow-update-v1.1.0 is not merged into main" && [ "$(git rev-parse workflow-update-v1.1.0)" = "$tip" ] || no "second apply before the merge is not PENDING"
  git merge -q --no-edit workflow-update-v1.1.0
  out=$($up --check); [ $? = 0 ] && echo "$out" | grep -q "UP TO DATE" || no "after the merge check is not UP TO DATE"
  ln -s "$d/v2/skills/workflow-setup" "$d/agent/skills/workflow-linked"
  linked=$(cd "$d/v2/skills/workflow-setup" && find . -type f | sort | xargs shasum | shasum)
  python3 "$d/agent/skills/workflow-setup/scripts/update.py" --from "$d/v2.zip" --apply 2>&1 | grep -q "UPDATE_CHECKOUT" || no "a skills folder with a link was updated"
  [ "$(cd "$d/v2/skills/workflow-setup" && find . -type f | sort | xargs shasum | shasum)" = "$linked" ] && [ -z "$(git branch --list 'workflow-update-vunknown')" ] || no "a linked skills folder was written to"
  echo "PASS SET-4: check shows the change, apply updates skills and the repo half on its branch, keeps data, PENDING then UP TO DATE"
fi
[ -n "$only" ] || echo "ALL PASS"
