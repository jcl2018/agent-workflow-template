#!/bin/bash
# Test workflow-docs on a throwaway toy repo with a bare wiki. usage: test-docs.sh [DIR]
unset LOOP_BATCH
set -e
here=$(cd "$(dirname "$0")/../.." && pwd)
d=${1:-$(mktemp -d)}; rm -rf "$d"; mkdir -p "$d"
"$here/dev/toy/make.sh" "$d"
docs="python3 $here/skills/workflow-docs/scripts/docs.py"
cd "$d/repo"
python3 "$here/skills/workflow-setup/scripts/setup.py" >/dev/null
git switch -q main; git merge -q --no-edit workflow-setup; git push -q origin main
fails=0
ok() { echo "PASS: $1"; }
bad() { echo "FAIL: $1"; fails=$((fails + 1)); }
wikifile() { git --git-dir="$d/origin.wiki.git" show "main:$1" 2>/dev/null; }

echo "== survey sees the other page"
$docs survey | grep -q "WIKI other Home" && ok "survey" || bad "survey"

echo "== an unwritten page fails check and publish"
$docs add Using-the-toy --paths calc.py >/dev/null
git add -A; git commit -qm "Add docs page"
$docs check | grep -q "^UNWRITTEN Using-the-toy" && ok "unwritten found" || bad "unwritten"
$docs publish >/dev/null 2>&1 && bad "published an unwritten page" || ok "publish refused unwritten"

echo "== a written page publishes and leaves other pages alone"
cat > docs/wiki/Using-the-toy.md <<'P'
<!-- workflow-docs -->
# Using the toy

Run `python3 calc.py` to use the toy calculator. Its tests sit beside it.
P
git add -A; git commit -qm "Write the page"
$docs check | grep -q "DOCS OK" && ok "check clean" || bad "check clean"
$docs publish --dry-run | grep -q "WOULD WRITE Using-the-toy" && ok "dry run" || bad "dry run"
[ -z "$(wikifile Using-the-toy.md)" ] && ok "dry run pushed nothing" || bad "dry run pushed"
$docs publish | grep -q PUBLISHED && ok "published" || bad "publish"
wikifile Using-the-toy.md | grep -q "toy calculator" && ok "page on the wiki" || bad "page missing"
[ "$(wikifile Home.md)" = "# Written by someone else" ] && ok "other page untouched" || bad "other page changed"
$docs publish | grep -q "NO CHANGE" && ok "second publish is no change" || bad "second publish"

echo "== a code change makes the page stale"
printf '\n# changed\n' >> calc.py; git commit -qam "Change calc"
out=$($docs check || true); echo "$out"
grep -q "^STALE Using-the-toy" <<<"$out" && ok "stale found" || bad "stale"
$docs publish >/dev/null 2>&1 && bad "published a stale page" || ok "publish refused stale"
$docs check --base HEAD | grep -q "DOCS OK" && ok "base ignores older changes" || bad "base"
echo "Now covers the change too, with a little more text." >> docs/wiki/Using-the-toy.md; git commit -qam "Update the page"
$docs check | grep -q "DOCS OK" && ok "updated page clean" || bad "updated"

echo "== publish refuses to replace a page it didn't write"
$docs add Home --paths README.md >/dev/null
cat > docs/wiki/Home.md <<'P'
<!-- workflow-docs -->
# Home

This would replace a page that someone else wrote on the wiki.
P
git add -A; git commit -qm "Add a Home page"
before=$(git --git-dir="$d/origin.wiki.git" rev-parse main)
$docs publish >/dev/null 2>&1 && bad "replaced another page" || ok "refused to replace"
[ "$(git --git-dir="$d/origin.wiki.git" rev-parse main)" = "$before" ] && ok "nothing pushed on refusal" || bad "pushed on refusal"

echo "== adopt replaces it, restore reverts it"
$docs publish --adopt Home | grep -q PUBLISHED && ok "adopt" || bad "adopt"
wikifile Home.md | grep -q "workflow-docs" && ok "page replaced" || bad "not replaced"
$docs restore | grep -q RESTORED && ok "restore" || bad "restore"
[ "$(wikifile Home.md)" = "# Written by someone else" ] && ok "restored original" || bad "not restored"

echo "== cut refuses stale docs"
export PATH="$here/dev/toy/fakegh:$PATH" FAKE_GH_DIR="$d/gh"
goal="python3 $here/skills/workflow-delivery/scripts/goal.py"; rel="python3 $here/skills/workflow-release/scripts/release.py"
git push -q origin main
$goal new stale --here --goal "Change calc" --done "calc changed" --level 0 >/dev/null
printf '\n# again\n' >> calc.py; git commit -qam "Change calc again"
python3 - <<'PY'
p = ".loop/goals/stale.md"; t = open(p).read().replace("## Verify by hand\n", "## Verify by hand\n\n1. Open calc.py.\n   Expect: the change.\n", 1); open(p, "w").write(t)
PY
git commit -qam "Verify steps"
$goal check stale >/dev/null; $goal pr stale >/dev/null
$rel ask stale | grep -q "STALE pages" && ok "ask warns about stale" || bad "ask stale"
$rel cut stale 2>&1 | grep -q "pages are stale" && ok "cut refused stale" || bad "cut stale"
echo "Covers that change too, with a sentence about it." >> docs/wiki/Using-the-toy.md; git add -A; git commit -qm "Update docs"
$goal check stale >/dev/null
$rel cut stale | grep -q "^DRAFT" && ok "cut after the docs update" || bad "cut after update"

[ "$fails" = 0 ] && echo "ALL PASS" || { echo "$fails FAILED"; exit 1; }
