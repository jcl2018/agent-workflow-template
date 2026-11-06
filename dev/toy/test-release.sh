#!/bin/bash
# Test workflow-release on a throwaway toy repo with a fake gh. usage: test-release.sh [DIR]
# env: AGENT_TEST=1 also runs a headless agent (MODEL, default haiku) that follows SKILL.md to ask and cut.
set -e
here=$(cd "$(dirname "$0")/../.." && pwd)
d=${1:-$(mktemp -d)}; rm -rf "$d"; mkdir -p "$d"
"$here/dev/toy/make.sh" "$d"
export PATH="$here/dev/toy/fakegh:$PATH" FAKE_GH_DIR="$d/gh"
goal="python3 $here/skills/workflow-delivery/scripts/goal.py"
rel="python3 $here/skills/workflow-release/scripts/release.py"
cd "$d/repo"
python3 "$here/skills/workflow-setup/scripts/setup.py" >/dev/null
git switch -q main; git merge -q --no-edit workflow-setup; git push -q origin main
fails=0
ok() { echo "PASS: $1"; }
bad() { echo "FAIL: $1"; fails=$((fails + 1)); }

finish() {  # finish SLUG [extra goal.py new args]: a done quick goal with a pull request
  local slug=$1; shift
  git switch -q main
  $goal new "$slug" --goal "Add $slug" --done "calc has $slug" --level quick "$@" >/dev/null
  printf '\n\ndef %s():\n    return 1\n' "${slug//-/_}" >> calc.py
  git commit -qam "Add ${slug} to calc"
  $goal check "$slug" >/dev/null && $goal pr "$slug" >/dev/null
}

echo "== 1. ask asks and prints the exact words"
finish one
out=$($rel ask one); echo "$out"
grep -qx "  cut one" <<<"$out" && grep -qx "  leave one" <<<"$out" && ok "ask printed exact words" || bad "ask words"
$goal show one | grep -q '"status": "waiting"' && ok "status waiting" || bad "status waiting"

echo "== 2. leave changes nothing versioned"
s0=$(git status --porcelain); h0=$(git rev-parse HEAD); b0=$(git branch --show-current); t0=$(git tag)
$rel leave one
s1=$(git status --porcelain); h1=$(git rev-parse HEAD); b1=$(git branch --show-current); t1=$(git tag)
echo "status before=[$s0] after=[$s1]  HEAD $h0 -> $h1  branch $b0 -> $b1"
[ -z "$s1" ] && [ "$s0" = "$s1" ] && [ "$h0" = "$h1" ] && [ "$b0" = "$b1" ] && [ "$t0" = "$t1" ] \
  && ok "leave left the tree, HEAD, branch and tags alone" || bad "leave changed something"
$rel show one | grep -qx "release=leave" && ok "release=leave recorded" || bad "release=leave"

echo "== 3. cut bumps VERSION, writes CHANGELOG, commits, makes a draft only"
finish two
$rel ask two >/dev/null
$rel cut two
echo "VERSION: $(cat VERSION)"; echo "--- CHANGELOG.md"; cat CHANGELOG.md; echo "---"
[ "$(cat VERSION)" = "0.1.1" ] && ok "VERSION 0.1.0 -> 0.1.1" || bad "VERSION"
grep -q "^## v0.1.1 - $(date -u +%F)" CHANGELOG.md && grep -q "^- Add two to calc" CHANGELOG.md \
  && ! grep -q "Goal: two" CHANGELOG.md && ok "CHANGELOG entry, .loop-only commit left out" || bad "CHANGELOG"
[ "$(git log -1 --format=%s)" = "Release v0.1.1" ] && ok "commit Release v0.1.1" || bad "commit"
[ "$(git rev-parse HEAD)" = "$(git rev-parse origin/loop/two)" ] && ok "branch pushed" || bad "push"
echo "--- gh calls.log"; cat "$FAKE_GH_DIR/calls.log"; echo "---"
grep -q "^release create v0.1.1 --draft " "$FAKE_GH_DIR/calls.log" && ok "draft release create" || bad "draft call"
grep -Eq "draft=false|release edit|release upload" "$FAKE_GH_DIR/calls.log" && bad "a publish call" || ok "no publish call"
[ -z "$(git ls-remote --tags origin)" ] && ok "no tag on origin" || bad "tag pushed"
git ls-remote --heads origin main | grep -q "$(git rev-parse main)" && ok "main not moved (nothing merged)" || bad "main moved"

echo "== 4. batch rules"
LOOP_BATCH=1 finish three
$rel cut three && bad "batch cut without --user" || ok "batch cut refused without --user"
out=$($rel ask three); echo "$out"
grep -q "answered by the batch" <<<"$out" && $rel show three | grep -qx "release=leave" \
  && ok "batch with release!=ask answered leave" || bad "batch auto leave"
LOOP_BATCH=1 finish four --release ask
out=$($rel ask four); grep -q "WAITING four" <<<"$out" && ok "batch with release=ask waits" || bad "batch ask"
$rel cut four --user >/dev/null && [ "$(cat VERSION)" = "0.1.1" ] && ok "batch cut with --user" || bad "batch --user"

if [ -n "$AGENT_TEST" ]; then
  echo "== 5. headless agent follows SKILL.md"
  finish five
  prompt="Follow the skill at $here/skills/workflow-release/SKILL.md. Its script is $here/skills/workflow-release/scripts/release.py. The goal five in this repo is finished. Run the ask step. The human's answer is: cut five"
  claude -p --model "${MODEL:-haiku}" --allowedTools "Bash,Read,Write,Edit" --add-dir "$here/skills" <<<"$prompt"
  $rel show five
  grep -Eq "^release create v[0-9.]+ --draft .*--target loop/five$" "$FAKE_GH_DIR/calls.log" && ok "agent made a draft" || bad "agent cut"
fi

echo "repo: $d/repo"
[ "$fails" = 0 ] && echo "ALL PASS" || { echo "$fails FAILED"; exit 1; }
