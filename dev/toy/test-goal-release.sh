#!/bin/bash
# reads: skills/workflow-delivery/scripts/goal.py skills/workflow-delivery/scripts/defect.py
# reads: skills/workflow-delivery/scripts/flow.py skills/workflow-regression/scripts/regression.py
# reads: skills/workflow-regression/scripts/tests.py skills/workflow-release/scripts/merge.py
# reads: skills/workflow-release/scripts/autorelease.py skills/workflow-release/scripts/fixes.py
# reads: skills/workflow-setup/scripts/setup.py
here=$(cd "$(dirname "$0")/../.." && pwd)
. "$here/dev/toy/reap.sh"
# REG-1 workflow test (C-A3): one toy goal that fixes an issue goes from goal.py new through its skill flow (the fake
# agent), its defect row seen failing, goal.py pr, merge.py and the automatic release, with a local bare origin and
# fakegh; the published release note and the CHANGELOG list the fixed issue with its defect test (REG-6, S24), and an
# old defect row the branch did not prove pays nothing (E-10). usage: test-goal-release.sh [DIR]
set -u
unset LOOP_SESSION_TOOL LOOP_OPERATION_SESSION LOOP_BATCH GH_TOKEN GITHUB_TOKEN
unset GITHUB_SERVER_URL GITHUB_REPOSITORY GITHUB_RUN_ID  # run cells never depend on the runner
export LOOP_ROLE=worker  # goal.py and flow.py run only in a worker
export HOME=$(mktemp -d)  # setup.py writes the private settings under HOME
d=${1:-$(mktemp -d)}; rm -rf "$d"; mkdir -p "$d"; [ -n "${1:-}" ] || toy_on_exit 'rm -rf "$d"'
toy_on_exit 'rm -rf "$HOME"'
"$here/dev/toy/make.sh" "$d" >/dev/null || exit 1
export LOOP_FLOW="$d/flow.json"
export PATH="$here/dev/toy/fakegh:$PATH" FAKE_GH_DIR="$d/gh" FAKE_GH_ORIGIN="$d/origin.git"
goal="python3 $here/skills/workflow-delivery/scripts/goal.py"
reg="python3 $here/skills/workflow-regression/scripts/regression.py"
fails=0
ok() { echo "PASS: $1"; }
bad() { echo "FAIL: $1"; fails=$((fails + 1)); }
cd "$d/repo" || exit 1
python3 "$here/skills/workflow-setup/scripts/setup.py" --bare >/dev/null
git switch -q main; git merge -q --no-edit workflow-setup
python3 - <<'PY'
import json
c = json.load(open(".loop/config.json")); c["auto_merge"] = True
json.dump(c, open(".loop/config.json", "w"), indent=2)
PY
issue=https://example.test/o/r/issues/5
# An old defect row for the same issue, proved before this goal: it must not pay the goal's debt (E-10).
$reg add old-5 --level land --command true --goal - --category defect --link "$issue" \
  --describe "Given an older fix, when it runs, then it stays fixed." >/dev/null
python3 - <<'PY'
rows = open(".loop/regression.tsv").read().splitlines()
open(".loop/regression.tsv", "w").write("\n".join(r.replace("\t\t", "\t2026-01-01\t", 1) if r.startswith("old-5\t") else r for r in rows) + "\n")
PY
git add -A; git commit -qm "Setup, auto_merge and an old defect row"; git tag v0.1.0; git push -q origin main v0.1.0

echo "== a goal that fixes #5 runs its flow"
$goal new fix5 --here --goal "Fix the median (fixes #5)" --done "calc has fix5 (fixes #5)" >/dev/null || bad "goal new"
printf '\n\ndef fix5():\n    return 5\n' >> calc.py
git add calc.py; git commit -qm "Fix the median"
python3 - <<'PY'
path = ".loop/goals/fix5.md"
text = open(path).read().replace("## Verify by hand\n", "## Verify by hand\n\n1. Open calc.py.\n   Expect: it has fix5.\n", 1)
open(path, "w").write(text)
PY
git commit -qam "Verify steps for fix5"
bash "$here/dev/toy/flow-done.sh" fix5 && ok "the flow ran idea to ship with the fake agent" || bad "flow"
# Value: protects=an old defect row merely present on the base does not count as this goal's proof (E-10);
# fails_when=defect.owed accepts any passing row linked to the issue; why_new=owed never compared with the merge-base;
# seam=none; no_claim=the pr lane's own rows
$goal pr fix5 2>&1 | grep -q "no passing defect test, seen failing, for #5" && ok "pr refuses while only an old row guards #5" \
  || bad "pr accepted the old row as proof"

echo "== the goal adds its defect row, proves it red, and opens its pull request"
$reg add fix5-5 --level land --command 'grep -q "def fix5" calc.py' --goal - --category defect --link "$issue" \
  --describe "Given the median fix, when calc.py is read, then fix5 is there." >/dev/null
git add -A; git commit -qm "Defect row for #5"
$reg red fix5-5 --break "sed -i.bak '/def fix5/d' calc.py" | grep -q "SEEN RED" && ok "the defect row is seen failing" || bad "red"
git add -A; git commit -qm "fix5-5 seen failing"
out=$($goal pr fix5 2>&1); grep -q "^PR " <<<"$out" && ok "goal.py pr opens the pull request" || bad "pr: $out"
# Value: protects=the pull request shows which rows its pr lane ran and why (DX-21); fails_when=the lane part is dropped
# from the body; why_new=the body listed only the flow steps; seam=none; no_claim=GitHub's rendering of <details>
body=$(cat "$FAKE_GH_DIR"/body-* 2>/dev/null)
grep -q "^### Regression lane" <<<"$body" && grep -q "^LANE pr " <<<"$body" && grep -q "<summary>Rows and why they ran</summary>" <<<"$body" \
  && ok "the pull request body carries the pr lane's LANE line and each row with why it ran" || bad "pr body lane part: $(grep -c LANE <<<"$body")"
git push -q origin loop/fix5 2>/dev/null || true

echo "== merge.py merges and releases with the Fixes line"
out=$(FAKE_GH_PR_STATE=OPEN FAKE_GH_MERGE_BRANCH=loop/fix5 python3 "$here/skills/workflow-release/scripts/merge.py" fix5 2>&1)
grep -q "^RELEASED v0.1.1" <<<"$out" && ok "merged and released v0.1.1" || bad "merge: $out"
seen=$(awk -F'\t' '$1 == "fix5-5" {print $5}' .loop/regression.tsv)
want="Fixes #5: test fix5-5, seen failing $seen, passing"
# Value: protects=the published release note lists each issue the goal fixed with its defect test (REG-6, C-A3);
# fails_when=autorelease drops the Fixes lines or lists a row the branch did not prove; why_new=no end-to-end run reached
# the release; seam=none; no_claim=GitHub's real release page (fakegh records the notes)
grep -qxF -- "- $want" "$FAKE_GH_DIR/notes.log" && ! grep -q "old-5" "$FAKE_GH_DIR/notes.log" \
  && ok "the release note lists $want" || bad "release note: $(cat "$FAKE_GH_DIR/notes.log" 2>/dev/null)"
# Value: protects=the CHANGELOG entry on the base lists the same Fixes line (REG-6); fails_when=push_release_commit
# writes the bullets without it; why_new=as above; seam=none; no_claim=the CHANGELOG's other sections
git fetch -q origin; log=$(git show origin/main:CHANGELOG.md)
grep -qxF -- "- $want" <<<"$log" && ok "the CHANGELOG lists $want" || bad "CHANGELOG: $log"

[ "$fails" = 0 ] && echo "ALL PASS" || { echo "$fails FAILED"; exit 1; }
