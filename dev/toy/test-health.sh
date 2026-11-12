#!/bin/bash
# reads: skills/workflow-health/scripts/cost.py skills/workflow-health/scripts/health.py
# reads: skills/workflow-health/scripts/enforce.py skills/workflow-setup/scripts/setup.py skills/workflow-health/scripts/
# Test workflow-health on a throwaway toy repo. usage: test-health.sh [DIR]
set -u
unset LOOP_SESSION_TOOL LOOP_OPERATION_SESSION  # a toy test never reaches a real session tool
here=$(cd "$(dirname "$0")/../.." && pwd)
. "$here/dev/toy/reap.sh"
export HOME=$(mktemp -d)  # setup.py writes the private settings under HOME
d=${1:-$(mktemp -d)}; rm -rf "$d"; mkdir -p "$d"
"$here/dev/toy/make.sh" "$d" || exit 1
export LOOP_FLOW="$d/flow.json"
health="python3 $here/skills/workflow-health/scripts/health.py"
cd "$d/repo" || exit 1
python3 "$here/skills/workflow-setup/scripts/setup.py" --bare >/dev/null
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
grep -q "^WARN size skills/x/scripts/near.py scripts: .* -> fix: " <<<"$out" && ok "90 percent of the limit is a WARN with a fix" || bad "size warn"
grep -q "^FAIL size skills/x/scripts/over.py scripts: .* -> fix: " <<<"$out" && ok "over 20 KB is a FAIL with a fix" || bad "size fail"
[ $rc = 1 ] && tail -1 <<<"$out" | grep -q "^HEALTH: not green" && ok "a FAIL makes the verdict not green" || bad "red verdict"
git rm -q skills/x/scripts/over.py; git commit -qm "Drop the big one"
out=$($health check --family size); rc=$?
[ $rc = 0 ] && grep -q "^HEALTH: green (.* 1 warn, 0 fail" <<<"$out" && ok "a WARN alone stays green" || bad "warn green"

echo "== docs and requirements are composed, not re-implemented"
mkdir -p docs/wiki
printf '<!-- workflow-docs -->\n# Calc\n\n## Criteria\n\n- REL-1: **Reviewed 2026-01-01** calc adds.\n' > docs/wiki/Calc.md
printf 'Calc\tcalc.py\nGhost\tghost.py\n' > .loop/docs.tsv
git add -A; git commit -qm "Map pages"
echo "# change" >> calc.py; git commit -qam "Change calc"
out=$($health check --family docs); echo "$out"
grep -q "^WARN docs Calc stale: " <<<"$out" && ok "a stale page shows as a docs row naming it" || bad "stale"
grep -q "^FAIL docs Ghost missing: " <<<"$out" && ok "a missing page shows as a FAIL" || bad "missing"
out=$($health check --family requirements); echo "$out"
grep -q "^FAIL requirements REL-1 rows: not enforced for [0-9]* days since Reviewed 2026-01-01" <<<"$out" && ok "a criterion with no row is a FAIL" || bad "criterion row"
[ "$($health check --family criteria)" = "$out" ] && ok "the old group name criteria still works" || bad "criteria alias"
python3 - <<'PY'
import os
os.makedirs(".loop/goals", exist_ok=True)
open(".loop/goals/old.md", "w").write("# Old\n\n## Done lines\n\nFrozen.\n\n1. Calc adds.\n\n## Design\n")
PY
mkdir -p "$(git rev-parse --git-common-dir)/loop/runs"; echo '{"status": "running"}' > "$(git rev-parse --git-common-dir)/loop/runs/old.json"  # a goal still being built (issue 143)
out=$($health check --family requirements)
grep -q "^WARN requirements done-lines done: [0-9]* done lines have no regression row" <<<"$out" && ok "done lines with no row are one WARN row" || bad "done lines"

echo "== Mine: the owner's own rules, from a private setting outside the repo"
export LOOP_HEALTH="$d/health.json"
out=$($health check --family mine); echo "$out"
grep -q "^INFO mine setting mine: no private rules set" <<<"$out" && ok "no private setting: Mine says so and stays green" || bad "mine none"
printf '#!/bin/bash\nexit 0\n' > "$d/pass.sh"; printf '#!/bin/bash\necho broke\nexit 1\n' > "$d/fail.sh"
printf '#!/bin/bash\nexit 2\n' > "$d/warn.sh"; chmod +x "$d"/*.sh
cat > "$LOOP_HEALTH" <<JSON
{"rules": [{"name": "good", "command": ["$d/pass.sh"]}, {"name": "bad", "command": ["$d/fail.sh"], "fix": "fix bad"},
 {"name": "meh", "command": ["$d/warn.sh"], "fix": "look at meh"}, {"name": "gone", "command": ["$d/nope.sh"]}]}
JSON
out=$($health check --family mine); rc=$?; echo "$out"
grep -qx "== Mine (my private angle) ==" <<<"$out" && grep -q "^PASS mine good mine: " <<<"$out" && ok "a passing own rule is PASS" || bad "mine pass"
grep -q "^FAIL mine bad mine: broke -> fix: fix bad" <<<"$out" && grep -q "^WARN mine meh mine: .* -> fix: look at meh" <<<"$out" && ok "exit 1 is FAIL and exit 2 is WARN, each with its fix" || bad "mine fail/warn"
grep -q "^UNREAD mine gone mine: could not run" <<<"$out" && [ $rc = 1 ] && tail -1 <<<"$out" | grep -q "^HEALTH: not green" && ok "a rule that cannot run is UNREAD and never green" || bad "mine unread"
echo "{ not json" > "$LOOP_HEALTH"
out=$($health check --family mine); rc=$?
grep -q "^UNREAD mine setting mine: " <<<"$out" && [ $rc = 1 ] && ok "an unreadable setting is UNREAD" || bad "mine setting"
rm -f "$LOOP_HEALTH"

echo "== one fixed template"
out=$($health check); echo "$out" | head -3
[ "$(head -1 <<<"$out")" = "HEALTH REPORT" ] && ok "starts with the title" || bad "title"
[ "$(grep '^== ' <<<"$out" | sed 's/^== \([^(]*\) (.*$/\1/' | tr '\n' ',')" = "Requirements,Traceability,Consistency,Docs,Freshness,Tests,Performance,Security and privacy,Size,Hygiene,Adoption,Mine,Controls," ] \
  && grep -qx "== Requirements (my angle: is every promise I approved proven?) ==" <<<"$out" && grep -qx "== Mine (my private angle) (skipped) ==" <<<"$out" \
  && ok "groups come in a fixed order, each with its angle" || bad "group order"
[ "$(grep -c '^HEALTH: ' <<<"$out")" = 1 ] && tail -1 <<<"$out" | grep -q "^HEALTH: " && ok "exactly one verdict line, last" || bad "one verdict"
awk '/^TESTS$/{t=1; next} t && /^$/{t=0; next} !t' <<<"$out" | grep -v '^\(HEALTH\|==\|groups run:\)' | grep -v '^\(PASS\|WARN\|FAIL\|UNREAD\|INFO\) [a-z]* ' | grep -q . && bad "a line outside the template" || ok "every line is a title, group, finding or verdict"

echo "== judge hints: plain text matching, model-free, kept as input for the judge"
cat >> docs/wiki/Calc.md <<'MD'
- REL-2: Calc never rounds the sum of two numbers.
- REL-3: Calc rounds the sum of two numbers.
MD
printf 'Calc\tcalc.py\nGhost\tghost.py\nEmpty\tempty.py\n' > .loop/docs.tsv
printf '<!-- workflow-docs -->\n# Empty\n' > docs/wiki/Empty.md
hints() { python3 -c "
import sys; sys.path.insert(0, '$here/skills/workflow-health/scripts')
import judge; l, s = judge.suggestions('.', [{'state': 'FAIL', 'family': 'x', 'subject': 'y', 'fix': 'z'}])
print('\n'.join(l + s))"; }
a=$(hints); b=$(hints); echo "$a"
grep -q "^conflict: REL-2 and REL-3 " <<<"$a" && ok "conflicting criteria are found" || bad "conflict"
grep -q "^missing: feature Empty has no requirement" <<<"$a" && ok "a feature with no criterion is found" || bad "missing criterion"
grep -q "^next 1: FAIL " <<<"$a" && ok "next steps are ranked, failures first" || bad "ranked"
[ "$a" = "$b" ] && ok "hints repeat exactly" || bad "hints differ"
c=$($health check); e=$($health check); [ "$c" = "$e" ] && ! grep -q "JUDGE" <<<"$c" && ok "check stays apart from the judge and repeats" || bad "check same"
grep -rn "claude\|anthropic\|urllib\|http" "$here"/skills/workflow-health/scripts/cost.py "$here"/skills/workflow-health/scripts/enforce.py >/dev/null && bad "model or network in a rule module" || ok "no model or network call in the rule modules"

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
PATH="$d/bin:$PATH" $health check >/dev/null
[ "$(cat "$d/gh-calls" 2>/dev/null)" = 'api --paginate --slurp repos/{owner}/{repo}/issues?state=all&per_page=100' ] && ok "check reads gh once, read-only" || bad "check gh calls: $(cat "$d/gh-calls" 2>/dev/null)"
for f in health enforce judge cost; do [ "$(wc -c < "$here/skills/workflow-health/scripts/$f.py")" -lt 20480 ] || bad "size of $f.py"; done; ok "health scripts under 20 KB"

echo "repo: $d/repo"
[ "$fails" = 0 ] && echo "ALL PASS" || { echo "$fails FAILED"; exit 1; }
