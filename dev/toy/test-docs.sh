#!/bin/bash
# Test workflow-docs on a throwaway toy repo with a bare wiki. usage: test-docs.sh [DIR]
unset LOOP_BATCH
set -e
export LOOP_ROLE=worker  # goal.py and flow.py run only in a worker
here=$(cd "$(dirname "$0")/../.." && pwd)
export HOME=$(mktemp -d)  # setup.py writes the private settings under HOME
d=${1:-$(mktemp -d)}; rm -rf "$d"; mkdir -p "$d"
"$here/dev/toy/make.sh" "$d"
export LOOP_FLOW="$d/flow.json"
docs="python3 $here/skills/workflow-docs/scripts/docs.py"
cd "$d/repo"
python3 "$here/skills/workflow-setup/scripts/setup.py" --bare >/dev/null
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

echo "== a merge never makes a page stale, whichever way it was merged, and unseen work still does"
git switch -q -c side-a; printf '\n# side a\n' >> calc.py; git commit -qam "Side a"
git switch -q -c side-b; echo "Now covers side a too, with a little more text." >> docs/wiki/Using-the-toy.md; git commit -qam "Page sees side a"
git switch -q main; echo x > other.txt; git add other.txt; git commit -qm "Main moves"
git merge -q --no-ff --no-edit side-a
git switch -q side-b; git merge -q --no-edit main
$docs check | grep -q "DOCS OK" && ok "clean on the branch before it merges" || bad "branch before merge"
git switch -q main; git merge -q --no-ff --no-edit side-b
$docs check | grep -q "DOCS OK" && ok "clean after the merge, with the parents the other way round" || bad "stale after a merge"
git switch -q -c side-c HEAD~1; printf '\n# side c\n' >> calc.py; git commit -qam "Side c"
git switch -q main; git merge -q --no-ff --no-edit side-c -X ours 2>/dev/null || git commit -qam "Merge side c"
$docs check | grep -q "^STALE Using-the-toy" && ok "work the page never saw is stale after a merge" || bad "unseen work"
echo "Now covers side c too, with a little more text." >> docs/wiki/Using-the-toy.md; git commit -qam "Page sees side c"
$docs check | grep -q "DOCS OK" && ok "and clean once the page sees it" || bad "after page"

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
$goal new stale --here --goal "Change calc" --done "calc changed" >/dev/null
printf '\n# again\n' >> calc.py; git commit -qam "Change calc again"
python3 - <<'PY'
p = ".loop/goals/stale.md"; t = open(p).read().replace("## Verify by hand\n", "## Verify by hand\n\n1. Open calc.py.\n   Expect: the change.\n", 1); open(p, "w").write(t)
PY
git commit -qam "Verify steps"
bash "$here/dev/toy/flow-done.sh" stale; $goal pr stale >/dev/null
$rel ask stale | grep -q "STALE" && ok "ask warns about stale" || bad "ask stale"
$rel cut stale 2>&1 | grep -q "docs audit found trouble" && ok "cut refused stale" || bad "cut stale"
echo "Covers that change too, with a sentence about it." >> docs/wiki/Using-the-toy.md; git add -A; git commit -qm "Update docs"
$rel cut stale | grep -q "^DRAFT" && ok "cut after the docs update" || bad "cut after update"

echo "== docs check: a stated count must match the repo"
mkdir -p skills/a skills/b; touch skills/a/SKILL.md skills/b/SKILL.md
echo "The toy has three skills." >> docs/wiki/Using-the-toy.md
out=$($docs check || true); echo "$out" | grep COUNT
grep -q "^COUNT docs/wiki/Using-the-toy.md: says three skills, the repo has 2$" <<<"$out" && ok "a page with the wrong number of skills fails, naming the file and both numbers" || bad "wrong skill count"
out=$($docs publish --dry-run 2>&1) && bad "published a wrong count" || { grep -q "^COUNT docs/wiki/Using-the-toy.md: says three skills" <<<"$out" && ok "publish refuses a wrong count" || bad "publish refused for another reason"; }
$docs audit --dry-run 2>&1 | grep -q "^COUNT docs/wiki/Using-the-toy.md: says three skills" && ok "audit reports a wrong count" || bad "audit count"
sed -i.bak 's/The toy has three skills\./The toy has 2 skills./' docs/wiki/Using-the-toy.md; rm docs/wiki/Using-the-toy.md.bak
$docs check | grep -q "^COUNT" && bad "the right number failed" || ok "the right number of skills passes"
printf '\n```text\nthree skills\n```\n~~~\nfour skills\n~~~\n   ```\nfive skills\n   ```\nInline `six skills` is code. A single page can say one skill.\nThese nine skills are an example. <!-- not-a-count -->\nThere are 9 feature pages.\n' >> docs/wiki/Using-the-toy.md
out=$($docs check || true); grep -q "^COUNT" <<<"$out" && bad "a skipped number counted: $out" || ok "code blocks, inline code, 'one', marked lines and feature pages with criteria off are not counted"
echo "The toy has twenty-two skills, and 1 skill more." >> docs/wiki/Using-the-toy.md
out=$($docs check || true)
grep -q "says two skills" <<<"$out" && bad "twenty-two read as two" || ok "a hyphenated number is not read as its last word"
grep -q "^COUNT docs/wiki/Using-the-toy.md: says 1 skill, the repo has 2$" <<<"$out" && ok "the digit 1 is still a count" || bad "digit 1"
echo "The README says four skills." >> README.md
$docs check | grep -q "^COUNT README.md: says four skills, the repo has 2$" && ok "the README is checked too" || bad "readme count"
git checkout -q -- docs/wiki/Using-the-toy.md README.md
echo "There are three skills, all UTF-8." >> docs/wiki/Using-the-toy.md
$docs check | grep -q "^COUNT docs/wiki/Using-the-toy.md: says three skills" && ok "an id-like word (UTF-8) does not hide a count" || bad "UTF-8 hid a count"
git checkout -q -- docs/wiki/Using-the-toy.md
printf '\n````text\n```\nfour skills\n```\n````\nAfter the block the toy has three skills.\n' >> docs/wiki/Using-the-toy.md
out=$($docs check || true); grep -q "says four skills" <<<"$out" && bad "a nested fence leaked" || ok "a longer fence holds a shorter one"
grep -q "says three skills" <<<"$out" && ok "a count after a long fence is still read" || bad "count after long fence"
git checkout -q -- docs/wiki/Using-the-toy.md
printf '\n<!-- nine skills -->\nUse 2.9 skills of effort and two test doubles.\n' >> docs/wiki/Using-the-toy.md
$docs check | grep -q "^COUNT" && bad "a comment, decimal or compound counted" || ok "comments, decimals and compound nouns are not counts"
printf '\n```text\nnever closed\nnine skills later\n' >> docs/wiki/Using-the-toy.md
$docs check | grep -q "^COUNT docs/wiki/Using-the-toy.md: a code fence never closes" && ok "an unclosed fence is reported, not silently skipped" || bad "unclosed fence"
git checkout -q -- docs/wiki/Using-the-toy.md
echo 'This line is marked `<!-- not-a-count -->` and says nine skills. <!-- not-a-count -->' >> docs/wiki/Using-the-toy.md
$docs check | grep -q "^COUNT" && bad "the marker was ignored" || ok "a marked line is skipped"
git checkout -q -- docs/wiki/Using-the-toy.md
echo "The guide covers three skills." > skills/guide.md
$docs check | grep -q "^COUNT skills/guide.md: says three skills, the repo has 2$" && ok "a top-level doc in skills is checked" || bad "skills doc count"
git checkout -q -- docs/wiki/Using-the-toy.md README.md; rm -rf skills
$docs check | grep -q "^COUNT" && bad "a repo with no skills folder checked skills" || ok "no skills folder, no skills check"

[ "$fails" = 0 ] && echo "ALL PASS" || { echo "$fails FAILED"; exit 1; }
