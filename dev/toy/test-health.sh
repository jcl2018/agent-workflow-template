#!/bin/bash
# Test workflow-health on a throwaway toy repo. usage: test-health.sh [DIR]
set -u
here=$(cd "$(dirname "$0")/../.." && pwd)
d=${1:-$(mktemp -d)}; rm -rf "$d"; mkdir -p "$d"
"$here/dev/toy/make.sh" "$d" || exit 1
export LOOP_FLOW="$d/flow.json"
health="python3 $here/skills/workflow-health/scripts/health.py"
cd "$d/repo" || exit 1
python3 "$here/skills/workflow-setup/scripts/setup.py" >/dev/null
git switch -q main; git merge -q --no-edit workflow-setup
fails=0
ok() { echo "PASS: $1"; }
bad() { echo "FAIL: $1"; fails=$((fails + 1)); }
pad() { python3 -c "import sys; sys.stdout.write('# pad\n' * (int(sys.argv[1]) // 6))" "$1"; }

echo "== same repo, same answer"
mkdir -p skills/x/scripts; pad 1000 > skills/x/scripts/small.py
git add -A; git commit -qm "Small script"
a=$($health check); b=$($health check); echo "$a"
[ "$a" = "$b" ] && ok "two runs print the same lines" || bad "runs differ"
tail -1 <<<"$a" | grep -q "^HEALTH: " && ok "one HEALTH verdict line" || bad "verdict line"
$health check --json | python3 -c "
import json, sys
d = json.load(sys.stdin)
sys.exit(0 if d['rows'] and d['verdict'].startswith('HEALTH:') and all(k in d['rows'][0] for k in ('state', 'family', 'subject', 'rule', 'detail', 'fix')) else 1)" \
  && ok "json prints the rows as records" || bad "json"

echo "== size: a script near and over 20 KB"
pad 19000 > skills/x/scripts/near.py; pad 21000 > skills/x/scripts/over.py
git add -A; git commit -qm "Big scripts"
out=$($health check --family size); rc=$?; echo "$out"
grep -q "^WARN size skills/x/scripts/near.py limit: .* -> fix: " <<<"$out" && ok "90 percent of the limit is a WARN with a fix" || bad "size warn"
grep -q "^FAIL size skills/x/scripts/over.py limit: .* -> fix: " <<<"$out" && ok "over 20 KB is a FAIL with a fix" || bad "size fail"
[ $rc = 1 ] && tail -1 <<<"$out" | grep -q "^HEALTH: not green" && ok "a FAIL makes the verdict not green" || bad "red verdict"
git rm -q skills/x/scripts/over.py; git commit -qm "Drop the big one"
out=$($health check --family size); rc=$?
[ $rc = 0 ] && grep -q "^HEALTH: green (.* 1 warn, 0 fail" <<<"$out" && ok "a WARN alone stays green" || bad "warn green"

echo "== docs and criteria are composed, not re-implemented"
mkdir -p docs/wiki
printf '<!-- workflow-docs -->\n# Calc\n\n## Criteria\n\n- REL-1: **Unreviewed** calc adds.\n' > docs/wiki/Calc.md
printf 'Calc\tcalc.py\nGhost\tghost.py\n' > .loop/docs.tsv
git add -A; git commit -qm "Map pages"
echo "# change" >> calc.py; git commit -qam "Change calc"
out=$($health check --family docs); echo "$out"
grep -q "^WARN docs Calc stale: " <<<"$out" && ok "a stale page shows as a docs row naming it" || bad "stale"
grep -q "^FAIL docs Ghost missing: " <<<"$out" && ok "a missing page shows as a FAIL" || bad "missing"
out=$($health check --family criteria); echo "$out"
grep -q "^FAIL criteria REL-1 rows: criterion has no regression row" <<<"$out" && ok "a criterion with no row is a FAIL" || bad "criterion row"
python3 - <<'PY'
import os
os.makedirs(".loop/goals", exist_ok=True)
open(".loop/goals/old.md", "w").write("# Old\n\n## Done lines\n\nFrozen.\n\n1. Calc adds.\n\n## Design\n")
PY
out=$($health check --family criteria)
grep -q "^WARN criteria done-lines rows: [0-9]* done lines have no regression row" <<<"$out" && ok "done lines with no row are one WARN row" || bad "done lines"

echo "== a rule that cannot read says UNREAD, never green"
lone=$(mktemp -d); cp "$here/skills/workflow-health/scripts/health.py" "$lone/"
out=$(python3 "$lone/health.py" check --family docs); rc=$?; echo "$out"
grep -q "^UNREAD docs docs check: " <<<"$out" && [ $rc = 1 ] && tail -1 <<<"$out" | grep -q "^HEALTH: not green (.* 1 unread" \
  && ok "no sibling script: UNREAD and not green" || bad "unread"

echo "== read-only"
git add -A; git commit -qm "Fixtures"
git clone -q "$d/repo" "$d/fresh"; cd "$d/fresh" || exit 1
before="$(git status --porcelain --ignored)|$(git rev-parse HEAD)|$(git branch | wc -l)|$(git stash list | wc -l)"
$health check >/dev/null; $health check --json >/dev/null
after="$(git status --porcelain --ignored)|$(git rev-parse HEAD)|$(git branch | wc -l)|$(git stash list | wc -l)"
[ "$before" = "$after" ] && ok "check writes no file and makes no commit" || bad "check changed the repo"
mkdir -p "$d/bin"; printf '#!/bin/bash\necho "$*" >> "%s/gh-calls"\nexit 1\n' "$d" > "$d/bin/gh"; chmod +x "$d/bin/gh"
PATH="$d/bin:$PATH" $health check >/dev/null; [ ! -e "$d/gh-calls" ] && ok "check makes no gh call" || bad "check called gh"
[ "$(wc -c < "$here/skills/workflow-health/scripts/health.py")" -lt 20480 ] && ok "health.py under 20 KB" || bad "size of health.py"

echo "repo: $d/repo"
[ "$fails" = 0 ] && echo "ALL PASS" || { echo "$fails FAILED"; exit 1; }
