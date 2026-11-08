#!/bin/bash
# Test the one docs command (docs.py audit) on a throwaway toy repo with a fake gh. usage: test-docs-command.sh [DIR]
set -u
here=$(cd "$(dirname "$0")/../.." && pwd)
export HOME=$(mktemp -d)  # setup.py writes the private settings under HOME
d=${1:-$(mktemp -d)}; rm -rf "$d"; mkdir -p "$d"
"$here/dev/toy/make.sh" "$d" || exit 1
export LOOP_FLOW="$d/flow.json"
export PATH="$here/dev/toy/fakegh:$PATH" FAKE_GH_DIR="$d/gh"
unset GH_TOKEN GITHUB_TOKEN
docs="python3 $here/skills/workflow-docs/scripts/docs.py"
cri="python3 $here/skills/workflow-docs/scripts/criteria.py"
reg="python3 $here/skills/workflow-regression/scripts/regression.py"
ms="python3 $here/skills/workflow-health/scripts/milestone.py"
cd "$d/repo" || exit 1
python3 "$here/skills/workflow-setup/scripts/setup.py" --bare >/dev/null
git switch -q main; git merge -q --no-edit workflow-setup
python3 - <<'PY'
import json
c = json.load(open(".loop/config.json")); c["criteria"] = True
json.dump(c, open(".loop/config.json", "w"), indent=2)
PY
mkdir -p "$FAKE_GH_DIR"
printf 'Delivery\tcalc.py\nHome\tREADME.md\n' > .loop/docs.tsv
mkdir -p docs/wiki
printf '<!-- workflow-docs -->\n# Home\n\nThe home page of the toy repo, with enough words to count as written.\n' > docs/wiki/Home.md
page() {  # page SUMMARY CRITERIA
  printf '<!-- workflow-docs -->\n# Delivery\n\n## Summary\n\n%s\n\n## Criteria\n\n%s\n\n## Tests\n\n' "$1" "$2" > docs/wiki/Delivery.md
}
page "The toy calculator, with enough words to count as a written page." "- DEL-1: **Unreviewed** It prints a median."
git add -A; git commit -qm "Toy docs"
repo=$PWD; fails=0
ok() { echo "PASS: $1"; }
bad() { echo "FAIL: $1"; fails=$((fails + 1)); }

echo "== 1. the template sheet holds the rules and the check reads them"
sheet=$here/skills/workflow-docs/references/template.md
grep -q '^```rules' "$sheet" && grep -q "Last result" "$sheet" && grep -q "not enforced" "$sheet" && ok "the sheet defines the page and each Tests column" || bad "sheet"
cp -r "$here/skills/workflow-docs" "$d/skill"
page "Short." "- DEL-1: **Unreviewed** One.
- CAL-2: **Unreviewed** Two."
$cri render >/dev/null
python3 "$d/skill/scripts/docs.py" check | grep -q "^CAP" && bad "two criteria are over the cap of five" || ok "the sheet's cap of 5 lets two criteria pass"
sed -i.bak 's/^max_criteria: 5/max_criteria: 1/' "$d/skill/references/template.md"
python3 "$d/skill/scripts/docs.py" check | grep -q "^CAP Delivery: has 2 criteria, over the cap of 1" && ok "changing the cap in the sheet changes the check" || bad "cap from sheet"
sed -i.bak '/^```rules/,/^```$/d' "$d/skill/references/template.md"
python3 "$d/skill/scripts/docs.py" check 2>&1 | grep -q "REFUSED: the rules block" && ok "no rules block: the check refuses" || bad "refuse without sheet"

echo "== 2. one command fixes the mechanical, lists the wording, and the release step runs it"
page "One.

Two.

Three.

Four, which is one too many." "- DEL-1: **Unreviewed** It prints a median."
git add -A; git commit -qm "Long summary"
out=$($docs audit --dry-run); echo "$out"
grep -q "^WOULD FIX docs/wiki/Delivery.md: re-render the Tests table" <<<"$out" && [ -z "$(git status --porcelain)" ] && ok "dry run says what it would fix and writes nothing" || bad "dry run"
out=$($docs audit); rc=$?; echo "$out"
grep -q "^FIXED docs/wiki/Delivery.md: re-render" <<<"$out" && grep -q '^| \*\*DEL-1\*\* .* | \*\*not enforced\*\*' docs/wiki/Delivery.md && ok "the Tests table is fixed" || bad "fix tables"
grep -q "^REWRITE Delivery: SUMMARY is over 3 lines" <<<"$out" && [ "$rc" = 1 ] && ok "wording to rewrite is listed and the exit is 1" || bad "rewrite"
[ -f docs/wiki/Delivery.md ] && grep -q "Four, which" docs/wiki/Delivery.md && ok "it deletes and rewrites no page" || bad "kept page"
git add -A; git commit -qm "Rendered" >/dev/null
trouble=$(cd "$here/skills/workflow-release/scripts" && python3 -c "import release; print(release.docs_trouble('$repo', 'main'))")
grep -q "SUMMARY" <<<"$trouble" && ok "the release step reads the audit and sees the trouble" || bad "release hook"
page "Short." "- DEL-1: **Unreviewed** It prints a median."; $cri render >/dev/null; git add -A; git commit -qm "Short" >/dev/null
trouble=$(cd "$here/skills/workflow-release/scripts" && python3 -c "import release; print(release.docs_trouble('$repo', 'main'))")
[ "$trouble" = "[]" ] && ok "a clean page passes the release step" || bad "release clean: $trouble"

echo "== 3. Reviewed criteria with no test, or tests that no longer match, are listed"
$cri review DEL-1 --user >/dev/null; $cri render >/dev/null; git add -A; git commit -qm "Reviewed" >/dev/null
out=$($docs audit); echo "$out"
grep -q "^UNTESTED DEL-1: no test" <<<"$out" && ok "a Reviewed criterion with no test is listed" || bad "no test"
list=$(git rev-parse --git-common-dir)/loop/untested.tsv
grep -q "^DEL-1	no test" "$list" && ok "the list is written for the loop to queue goals from" || bad "untested.tsv"
$reg add del-1 --level land --command "bash gone.sh" --goal DEL-1 >/dev/null
$cri render >/dev/null; git add -A; git commit -qm "Row" >/dev/null
$docs audit | grep -q "^UNTESTED DEL-1: test no longer matches" && ok "a test whose target is gone no longer matches" || bad "no longer matches"
$reg add del-1 --level land --command "true" --goal DEL-1 >/dev/null; $reg run del-1 >/dev/null || true
$cri render >/dev/null; git add -A; git commit -qm "Passing" >/dev/null
$docs audit | grep -q "^UNTESTED" && bad "a passing test still listed" || ok "a passing test clears the line"

echo "== 4. milestone links, the Backlog and release notes"
out=$($docs audit); echo "$out"
grep -q "^MILESTONE Backlog: missing" <<<"$out" && grep -q "^MILESTONE Delivery: no milestone" <<<"$out" && ok "a missing Backlog and feature milestone are found" || bad "missing milestones"
$ms new --all --live | grep -q "^LINKED Delivery" && grep -q "^Milestone: https://example.test/milestone/" docs/wiki/Delivery.md && ok "milestone.py links the feature page to its milestone" || bad "link"
git add -A; git commit -qm "Linked" >/dev/null
$docs audit | grep -q "^MILESTONE" && bad "milestones still missing" || ok "with the Backlog and the link, the milestone check is clean"
sed -i.bak '/^Milestone: /d' docs/wiki/Delivery.md; rm -f docs/wiki/Delivery.md.bak; git commit -qam "Drop link"
$docs audit | grep -q "^FIXED Delivery: add the Milestone line" && grep -q "^Milestone: " docs/wiki/Delivery.md && ok "a missing link is fixed" || bad "fix link"
git commit -qam "Relinked"
git tag v9.9.9
$docs audit | grep -q "^RELEASE v9.9.9: has no release note" && ok "a tag with no release note is found" || bad "release note"
printf '# Changelog\n\n## v9.9.9 - 2026-11-08\n\n- Toy release\n' > CHANGELOG.md; git add -A; git commit -qm "Changelog" >/dev/null
$docs audit | grep -q "^RELEASE" && bad "release note still missing" || ok "its CHANGELOG section is the release note"

echo "== 5. every script stays under 20 KB"
big=$(find "$here/skills" -name '*.py' -size +20480c | head -1)
[ -z "$big" ] && ok "scripts under 20 KB" || bad "over 20 KB: $big"

[ "$fails" = 0 ] && echo "ALL PASS" || { echo "$fails FAILED"; exit 1; }
