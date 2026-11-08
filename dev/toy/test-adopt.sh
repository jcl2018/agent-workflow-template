#!/bin/bash
# Adopt a fresh toy repo, then update its skills. usage: test-adopt.sh [SET-1..SET-5]   no ID runs every part. No model is called.
set -u
here=$(cd "$(dirname "$0")/../.." && pwd); only=${1:-}
d=$(mktemp -d); trap 'rm -rf "$d"' EXIT
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
  $setup >/dev/null || no "setup failed"
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
  again=$($setup) || no "second run failed"
  echo "$again" | grep -q "NO CHANGE" && [ -z "$(git status --short)" ] || no "second run changed something"
  echo "PASS SET-1 SET-2: adopted and adapted, second run changes nothing"
fi

mk() { # mk DIR VERSION: a package tree at that version
  mkdir -p "$1"; cp -R "$here/skills" "$here/listing.json" "$here/README.md" "$here/LICENSE" "$1/"
  find "$1" -name __pycache__ -prune -exec rm -rf {} +  # earlier tests may have left bytecode in the checkout
  echo "$2" > "$1/VERSION"; printf '# Changelog\n\n## v%s - 2026-01-01\n\n- change %s\n\n## v1.0.0 - 2026-01-01\n\n- first\n' "$2" "$2" > "$1/CHANGELOG.md"
}
pk="python3 $here/dev/package.py"
mk "$d/v1" 1.0.0; $pk --root "$d/v1" --out "$d/v1.zip" >/dev/null || no "v1 package refused"

# SET-3: the package carries its version, every skill and the guide; it installs by copying.
if want SET-3; then
  unzip -p "$d/v1.zip" PACKAGE.json | grep -q '"version": "1.0.0"' || no "no version in the package"
  for skill in "$here"/skills/workflow-*; do unzip -l "$d/v1.zip" | grep -q "skills/$(basename $skill)/SKILL.md" || no "$(basename $skill) missing"; done
  unzip -l "$d/v1.zip" | grep -q "shared/design-guide.md" || no "no design guide"
  big=$(find "$here/skills" -name '*.py' -size +20479c); [ -z "$big" ] || no "script over 20 KB: $big"
  echo "PASS SET-3: versioned package, every skill, scripts under 20 KB"
fi

# SET-4 and SET-5: update changes skills only, and the guide is installed.
if want SET-4 || want SET-5; then
  mkdir -p "$d/agent/skills" "$d/x1"; unzip -q "$d/v1.zip" -d "$d/x1"
  cp -R "$d/x1/skills/." "$d/agent/skills/"; cp -R "$d/x1/shared/." "$d/agent/skills/"
  [ -f "$d/agent/skills/design-guide.md" ] && grep -q "Operation and workers" "$d/agent/skills/design-guide.md" || no "the guide is missing or empty"
  mkdir -p .claude; echo '{"private": true}' > .claude/settings.local.json; git add -A; git commit -qm "Private settings" >/dev/null 2>&1
  data() { (cd "$d/toy/repo" && find .loop docs .claude -type f | sort | xargs shasum | shasum); }
  before=$(data)
  mk "$d/v2" 1.1.0; echo "# extra" >> "$d/v2/skills/workflow-setup/SKILL.md"; $pk --root "$d/v2" --out "$d/v2.zip" >/dev/null || no "v2 package refused"
  up="python3 $d/agent/skills/workflow-setup/scripts/update.py --from $d/v2.zip"
  out=$($up) || no "preview failed"
  echo "$out" | grep -q "INSTALLED: 1.0.0" && echo "$out" | grep -q "AVAILABLE: 1.1.0" && echo "$out" | grep -q "change 1.1.0" && echo "$out" | grep -q "update: workflow-setup/SKILL.md" || no "preview does not show the version and the change"
  echo "$out" | grep -q "change 1.0.0" && no "preview shows an entry the repo already has"
  cmp -s "$d/agent/skills/workflow-setup/SKILL.md" "$here/skills/workflow-setup/SKILL.md" || no "preview wrote a skill file"
  $up --apply >/dev/null || no "update failed"
  tail -1 "$d/agent/skills/workflow-setup/SKILL.md" | grep -q "# extra" || no "skill not updated"
  grep -q '"version": "1.1.0"' "$d/agent/skills/workflow-package.json" || no "stamp not moved"
  [ "$(data)" = "$before" ] || no "update touched config, criteria, docs or private settings"
  $up | grep -q "UP TO DATE" || no "second update not a no-op"
  ln -s "$d/v2/skills/workflow-setup" "$d/agent/skills/workflow-linked"
  python3 "$d/agent/skills/workflow-setup/scripts/update.py" --from "$d/v2.zip" --apply 2>&1 | grep -q REFUSED || no "a skills folder with a link was updated"
  echo "PASS SET-4 SET-5: update shows the change, touches skills only, guide installed"
fi
[ -n "$only" ] || echo "ALL PASS"
