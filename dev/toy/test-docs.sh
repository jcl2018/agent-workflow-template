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
nocount() { local out; out=$($docs check 2>&1); ! grep -q "Traceback" <<<"$out" && ! grep -q "^COUNT" <<<"$out"; }  # no COUNT line, and the check finished
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
nocount && ok "the right number of skills passes" || bad "the right number failed"
printf '\n```text\nthree skills\n```\n~~~\nfour skills\n~~~\n   ```\nfive skills\n   ```\nInline `six skills` is code. A single page can say one skill.\nThese nine skills are an example. <!-- not-a-count -->\nThere are 9 feature pages.\n' >> docs/wiki/Using-the-toy.md
out=$($docs check || true); grep -q "^COUNT" <<<"$out" && bad "a skipped number counted: $out" || ok "code blocks, inline code, 'one', marked lines and feature pages with criteria off are not counted"
printf '\nThe toy has twenty-two skills, and 1 skill more.\n' >> docs/wiki/Using-the-toy.md  # its own paragraph
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
nocount && ok "comments, decimals and compound nouns are not counts" || bad "a comment, decimal or compound counted"
printf '\n```text\nnever closed\nnine skills later\n' >> docs/wiki/Using-the-toy.md
$docs check | grep -q "^COUNT docs/wiki/Using-the-toy.md: a code fence never closes" && ok "an unclosed fence is reported, not silently skipped" || bad "unclosed fence"
git checkout -q -- docs/wiki/Using-the-toy.md
echo 'This line is marked `<!-- not-a-count -->` and says nine skills. <!-- not-a-count -->' >> docs/wiki/Using-the-toy.md
nocount && ok "a marked line is skipped" || bad "the marker was ignored"
git checkout -q -- docs/wiki/Using-the-toy.md
echo 'Mark a line `<!-- not-a-count -->` here; the toy has nine skills.' >> docs/wiki/Using-the-toy.md
$docs check | grep -q "^COUNT docs/wiki/Using-the-toy.md: says nine skills" && ok "a marker inside inline code does not hide a count" || bad "in-code marker hid a count"
git checkout -q -- docs/wiki/Using-the-toy.md
printf '\nThe suite runs 1,200 tests, and 7 \xc5\xbfkills is not a word.\nA ``nine skills`` span is code.\n> ```\n> eight skills\n> ```\nUse `<!--` in prose, and the toy has three skills.\n' >> docs/wiki/Using-the-toy.md
out=$($docs check 2>&1 || true)
grep -q "Traceback" <<<"$out" && bad "a non-ASCII letter crashed the check" || ok "a non-ASCII letter does not crash the check"
grep -q "says 200 tests\|says nine skills\|says eight skills" <<<"$out" && bad "a separator, double-backtick span or quoted fence counted: $out" || ok "separators, double-backtick spans and quoted fences are not counts"
grep -q "says three skills" <<<"$out" && ok "a comment opener in code doesn't swallow later text" || bad "comment opener swallowed text"
git checkout -q -- docs/wiki/Using-the-toy.md
printf '\n<!-- an unclosed comment\nnine skills hidden\n' >> docs/wiki/Using-the-toy.md
$docs check | grep -q "says nine skills" && bad "an unclosed comment was read" || ok "an unclosed comment hides what follows, as Markdown does"
git checkout -q -- docs/wiki/Using-the-toy.md
# Generated by /ship coverage audit.
# Value: protects=a comment closed on a later line hides only its inside, and a fence inside it opens nothing; fails_when=the
#   comment state never resets, or a fence opens inside a comment; why_new=only one-line and unclosed comments were tested;
#   seam=none; no_claim=none beyond protects
printf '\n<!-- a comment\nnine skills inside\n```\nstill the comment -->After it the toy has three skills.\n' >> docs/wiki/Using-the-toy.md
out=$($docs check 2>&1 || true)
grep -q "says nine skills" <<<"$out" && bad "text inside a closed comment counted" || ok "a comment closed on a later line hides its inside"
grep -q "says three skills" <<<"$out" && ok "text after a comment closes on a later line is read" || bad "text after a closed comment lost"
grep -q "never closes" <<<"$out" && bad "a fence inside a comment opened a block" || ok "a fence inside a comment opens no block"
git checkout -q -- docs/wiki/Using-the-toy.md
# Generated by /ship coverage audit.
# Value: protects=counts() reads only regular files inside the repo; fails_when=the realpath/isfile guard is dropped, so a
#   symlink out of the repo is read or a folder named *.md crashes; why_new=no test used a symlink or folder; seam=none;
#   no_claim=only a skills/ top-level link is tried, not a wiki-page link
echo "The outside file says nine skills." > "$d/outside.md"; ln -s "$d/outside.md" skills/link.md; mkdir skills/folder.md
out=$($docs check 2>&1 || true)
grep -q "Traceback" <<<"$out" && bad "a folder named .md crashed the check" || ok "a folder named .md is not read"
grep -q "says nine skills" <<<"$out" && bad "a symlink out of the repo was read" || ok "a symlink out of the repo is not read"
rm -rf skills/link.md skills/folder.md "$d/outside.md"
# Generated by /ship coverage audit.
# Value: protects="N workflow skills" is a skill count; fails_when=the optional "workflow" word is dropped from the pattern;
#   why_new=every test said "N skills"; seam=none; no_claim=none beyond protects
echo "The toy ships three workflow skills." >> docs/wiki/Using-the-toy.md
$docs check | grep -q "^COUNT docs/wiki/Using-the-toy.md: says three workflow skills, the repo has 2$" && ok "'N workflow skills' is a count" || bad "workflow skills count"
git checkout -q -- docs/wiki/Using-the-toy.md
printf '\nA page holds up to 9 skills, and at most 8 skills run at once.\n```python``` opens no block here.\n' >> docs/wiki/Using-the-toy.md
nocount && ok "limits and a backtick line with a backtick after it are not counts" || bad "a limit or inline backticks counted"
git checkout -q -- docs/wiki/Using-the-toy.md
printf '\nThe toy ships the nine\nskills listed below.\n' >> docs/wiki/Using-the-toy.md
$docs check | grep -q "^COUNT docs/wiki/Using-the-toy.md: says nine skills, the repo has 2$" && ok "a claim wrapped across a line break is read" || bad "wrapped claim missed"
git checkout -q -- docs/wiki/Using-the-toy.md
echo "The README says four skills." >> README.md  # uncommitted, so no page goes stale
out=$($docs publish --dry-run --adopt Home 2>&1 || true); grep -q "^COUNT\|REFUSED" <<<"$out" && bad "README drift blocked publish: $out" || ok "a wrong count outside the wiki doesn't block publish"
git checkout -q -- README.md
echo "The guide covers three skills." > skills/guide.md
$docs check | grep -q "^COUNT skills/guide.md: says three skills, the repo has 2$" && ok "a top-level doc in skills is checked" || bad "skills doc count"
git checkout -q -- docs/wiki/Using-the-toy.md README.md; rm -rf skills
nocount && ok "no skills folder, no skills check" || bad "a repo with no skills folder checked skills"

[ "$fails" = 0 ] && echo "ALL PASS" || { echo "$fails FAILED"; exit 1; }
