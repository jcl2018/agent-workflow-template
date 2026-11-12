#!/bin/bash
# reads: skills/ skills/workflow-health/scripts/health.py skills/workflow-health/scripts/issues.py
# reads: skills/workflow-health/scripts/report.py skills/workflow-health/scripts/controls.py
# reads: skills/workflow-setup/scripts/setup.py skills/workflow-health/scripts/
# Test that health never asks for a milestone: an open issue with none gives no docs row, no unread row, no gh call and an
# unchanged verdict, on a toy repo with a fake gh. usage: test-health-issues.sh [DIR]
set -u
unset LOOP_SESSION_TOOL LOOP_OPERATION_SESSION  # a toy test never reaches a real session tool
here=$(cd "$(dirname "$0")/../.." && pwd)
. "$here/dev/toy/reap.sh"
export HOME=$(mktemp -d)  # setup.py writes the private settings under HOME
d=${1:-$(mktemp -d)}; rm -rf "$d"; mkdir -p "$d"
"$here/dev/toy/make.sh" "$d" || exit 1
export LOOP_FLOW="$d/flow.json"
export PATH="$here/dev/toy/fakegh:$PATH" FAKE_GH_DIR="$d/gh"
unset GH_TOKEN GITHUB_TOKEN FAKE_GH_LIST_FAIL
health="python3 $here/skills/workflow-health/scripts/health.py"
cd "$d/repo" || exit 1
python3 "$here/skills/workflow-setup/scripts/setup.py" --bare >/dev/null
git switch -q main; git merge -q --no-edit workflow-setup
printf 'Calc\tcalc.py\n' > .loop/docs.tsv
mkdir -p docs/wiki; printf '<!-- workflow-docs -->\n# Calc\n\n## Summary\n\nCalc adds two numbers and prints the sum for the user.\n' > docs/wiki/Calc.md
git add -A; git commit -qm "Map the Calc page"; git push -q origin main
git remote add github https://github.com/toy/toy.git  # a GitHub remote: only then are issues read; never pushed to
fails=0
ok() { echo "PASS: $1"; }
bad() { echo "FAIL: $1"; fails=$((fails + 1)); }
mkdir -p "$FAKE_GH_DIR"
put() { python3 -c "import json,sys; json.dump(json.loads(sys.argv[1]), open(sys.argv[2], 'w'))" "$1" "$FAKE_GH_DIR/issues.json"; }

echo "== baseline: no open issue"
put '[]'
out=$($health check --group docs); base_rc=$?; echo "$out"; base=$(tail -1 <<<"$out")
! grep -q "milestone" <<<"$out" && ok "no open issues: no issue row" || bad "baseline"

echo "== open issues with and without a milestone, and a closed one: no row names any, the verdict is unchanged"
put '[{"number": 3, "title": "Loose ends", "state": "OPEN", "milestone": null},
      {"number": 4, "title": "Placed", "state": "OPEN", "milestone": {"title": "v1.0"}},
      {"number": 5, "title": "Old and closed", "state": "CLOSED", "milestone": null}]'
: > "$FAKE_GH_DIR/calls.log"
out=$($health check --group docs); rc=$?; echo "$out"
! grep -q "#3\|#4\|#5\|Loose ends" <<<"$out" && ! grep -q "milestone" <<<"$out" && ok "no docs row names an issue with no milestone" || bad "a row names an issue"
[ $rc = "$base_rc" ] && [ "$(tail -1 <<<"$out")" = "$base" ] && ok "the verdict and exit code are as with no issues" || bad "verdict moved"
! grep -q "issue list" "$FAKE_GH_DIR/calls.log" && ok "the docs check reads no issue list from gh" || bad "gh issue list called"

echo "== gh failing or a thousand issues: no unread row either"
out=$(FAKE_GH_LIST_FAIL="HTTP 401: Bad credentials" $health check --group docs); rc=$?
! grep -q "^UNREAD" <<<"$out" && [ $rc = "$base_rc" ] && [ "$(tail -1 <<<"$out")" = "$base" ] && ok "gh failing gives no row and no change" || bad "gh fails"
python3 -c "import json,sys; json.dump([{'number': n, 'title': 't%d' % n, 'state': 'OPEN', 'milestone': None} for n in range(1, 1201)], open(sys.argv[1], 'w'))" "$FAKE_GH_DIR/issues.json"
out=$($health check --group docs); rc=$?
! grep -q "^UNREAD\|^FAIL docs #" <<<"$out" && [ $rc = "$base_rc" ] && [ "$(tail -1 <<<"$out")" = "$base" ] && ok "a thousand issues give no row and no change" || bad "truncated"

echo "== the removed rule has no control and no leftover name"
python3 "$here/skills/workflow-health/scripts/controls.py" run docs-issues >/dev/null 2>&1; [ $? = 2 ] && ok "controls.py no longer knows docs-issues" || bad "control remains"
! grep -rn "issues\.\(rows\|unread\|on_github\|LIMIT\|RULE\|FIX_UNREAD\)" "$here/skills" "$here/dev" --include=*.py --include=*.sh | grep -v "test-health-issues.sh" | grep -q . && ok "no module still names the removed helpers" || bad "dangling name"
for m in health issues controls report file automation judge workflows milestone; do (cd "$here/skills/workflow-health/scripts" && python3 -B -c "import $m") 2>/dev/null || bad "$m does not import"; done
for f in health issues controls report; do [ "$(wc -c < "$here/skills/workflow-health/scripts/$f.py")" -lt 18432 ] || bad "size of $f.py"; done; ok "health scripts import and are under the WARN line"
[ "$fails" = 0 ] && echo "PASS milestone-freeform:no-milestone-issue-ok"

echo "repo: $d/repo"
[ "$fails" = 0 ] && echo "ALL PASS" || { echo "$fails FAILED"; exit 1; }
