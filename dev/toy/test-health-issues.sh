#!/bin/bash
# reads: skills/workflow-health/scripts/health.py skills/workflow-health/scripts/issues.py
# reads: skills/workflow-health/scripts/report.py skills/workflow-health/scripts/controls.py
# reads: skills/workflow-setup/scripts/setup.py skills/workflow-health/scripts/
# Test DOC-10: health's docs-check flags an open issue with no milestone, on a toy repo with a fake gh. usage: test-health-issues.sh [DIR]
set -u
unset LOOP_SESSION_TOOL LOOP_OPERATION_SESSION  # a toy test never reaches a real session tool
here=$(cd "$(dirname "$0")/../.." && pwd)
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

echo "== an open issue with no milestone FAILs naming it; one with a milestone and a closed one pass"
put '[{"number": 3, "title": "Loose ends", "state": "OPEN", "milestone": null},
      {"number": 4, "title": "Placed", "state": "OPEN", "milestone": {"title": "Calc"}},
      {"number": 5, "title": "Old and closed", "state": "CLOSED", "milestone": null}]'
out=$($health check --group docs); rc=$?; echo "$out"
grep -q "^FAIL docs #3 milestone: Loose ends -> fix: gh issue edit 3 --milestone <Feature|Backlog>$" <<<"$out" && [ $rc = 1 ] \
  && ok "an open issue with no milestone FAILs naming #3" || bad "loose issue"
! grep -q "#4" <<<"$out" && ok "an issue with a milestone passes" || bad "placed issue"
! grep -q "#5" <<<"$out" && ok "closed issues are ignored" || bad "closed issue"
grep -q -e "issue list --state open --limit 1000 --json number,title,milestone" "$FAKE_GH_DIR/calls.log" && ok "reads open issues with one gh issue list" || bad "gh call"

echo "== gh fails: one UNREAD row, and HEALTH is not red from it"
put '[]'
out=$(FAKE_GH_LIST_FAIL="HTTP 401: Bad credentials" $health check --group docs); rc=$?; echo "$out"
grep -q "^UNREAD docs issues milestone: HTTP 401: Bad credentials -> fix: gh auth login, then rerun health.py check$" <<<"$out" \
  && [ "$(grep -c '^UNREAD' <<<"$out")" = 1 ] && ok "gh failing gives one UNREAD row with gh's first error line" || bad "gh fails"
[ $rc = "$base_rc" ] && [ "$(tail -1 <<<"$out")" = "$base" ] && tail -1 <<<"$out" | grep -q " 0 unread)$" \
  && ok "an unread issue list leaves the HEALTH verdict and exit code as they were, 0 unread" || bad "unread red"
out=$(PATH="/usr/bin:/bin" $health check --group docs 2>&1); rc=$?
grep -q "^UNREAD docs issues milestone: .*'gh'" <<<"$out" && [ $rc = "$base_rc" ] && [ "$(tail -1 <<<"$out")" = "$base" ] && ok "gh not installed gives UNREAD, not red" || bad "no gh"

echo "== exactly 1000 open issues: UNREAD truncated"
python3 -c "import json,sys; json.dump([{'number': n, 'title': 't%d' % n, 'state': 'OPEN', 'milestone': None} for n in range(1, 1201)], open(sys.argv[1], 'w'))" "$FAKE_GH_DIR/issues.json"
out=$($health check --group docs); rc=$?; echo "$out" | tail -3
grep -q "^UNREAD docs issues milestone: truncated at 1000 open issues -> fix: gh auth login, then rerun health.py check$" <<<"$out" \
  && ! grep -q "^FAIL docs #" <<<"$out" && [ $rc = "$base_rc" ] && [ "$(tail -1 <<<"$out")" = "$base" ] && ok "exactly 1000 issues gives UNREAD truncated" || bad "truncated"

echo "== no GitHub remote: no gh call, no row"
git remote remove github; : > "$FAKE_GH_DIR/calls.log"; put '[{"number": 3, "title": "Loose ends", "state": "OPEN", "milestone": null}]'
out=$($health check --group docs); rc=$?
[ $rc = "$base_rc" ] && ! grep -q "milestone" <<<"$out" && ! grep -q "number,title,milestone" "$FAKE_GH_DIR/calls.log" && ok "a repo with no GitHub remote reads no issues" || bad "no remote"

echo "== the negative control fires"
out=$(python3 "$here/skills/workflow-health/scripts/controls.py" run docs-issues); echo "$out"
grep -q "^PASS controls docs-issues: fires on its fixture" <<<"$out" && ok "the docs-issues negative control fires" || bad "control"
for f in health issues controls report; do [ "$(wc -c < "$here/skills/workflow-health/scripts/$f.py")" -lt 18432 ] || bad "size of $f.py"; done; ok "health scripts under the WARN line"

echo "repo: $d/repo"
[ "$fails" = 0 ] && echo "ALL PASS" || { echo "$fails FAILED"; exit 1; }
