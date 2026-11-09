#!/bin/bash
# Test the formal health report and filing by group on a toy repo with a fake gh. usage: test-health-report.sh [DIR]
set -u
here=$(cd "$(dirname "$0")/../.." && pwd)
export HOME=$(mktemp -d)  # setup.py writes the private settings under HOME
d=${1:-$(mktemp -d)}; rm -rf "$d"; mkdir -p "$d"
"$here/dev/toy/make.sh" "$d" || exit 1
export LOOP_FLOW="$d/flow.json"
export PATH="$here/dev/toy/fakegh:$PATH" FAKE_GH_DIR="$d/gh"
unset GH_TOKEN GITHUB_TOKEN
health="python3 $here/skills/workflow-health/scripts/health.py"
cd "$d/repo" || exit 1
python3 "$here/skills/workflow-setup/scripts/setup.py" --bare >/dev/null
git switch -q main; git merge -q --no-edit workflow-setup
export LOOP_HEALTH="$d/none.json"  # after setup: no private rules
mkdir -p docs/wiki skills/x/scripts; mkdir -p "$FAKE_GH_DIR"; : > "$FAKE_GH_DIR/calls.log"
printf '<!-- workflow-docs -->\n# Calc\n\n## Summary\n\nCalc adds numbers.\n\n## Criteria\n\n- REL-1: **Unreviewed** calc adds.\n' > docs/wiki/Calc.md
printf 'Calc\tcalc.py\nGhost\tghost.py\n' > .loop/docs.tsv
python3 -c "print('# pad\n' * 3400)" > skills/x/scripts/near.py
git add -A; git commit -qm "Findings in several groups"; git push -q origin main; git branch loop/old
fails=0
ok() { echo "PASS: $1"; }
bad() { echo "FAIL: $1"; fails=$((fails + 1)); }
issues() { python3 -c "import json,os;print(json.dumps(json.load(open(os.environ['FAKE_GH_DIR']+'/issues.json'))))" 2>/dev/null || echo "[]"; }
writes() { grep -cE "^(issue (create|edit|close|reopen)|label create)" "$FAKE_GH_DIR/calls.log" 2>/dev/null || true; }
count() { python3 -c "import json,sys;print(sum(1 for i in json.loads(sys.argv[1]) if sys.argv[2] in [l['name'] for l in i['labels']] and (len(sys.argv) < 4 or i['state'] == sys.argv[3])))" "$(issues)" "$@"; }

echo "== the formal report"
out=$($health check); echo "$out"
[ "$(sed -n 1p <<<"$out")" = "HEALTH REPORT" ] && sed -n 2p <<<"$out" | grep -q "^groups run: size, criteria, docs, hygiene, performance; skipped: Mine (no private rules set)$" \
  && ok "the header names every group run and the one skipped" || bad "header"
[ "$(grep -n '^== ' <<<"$out" | sed 's/^[0-9]*:== \(.*\) ==$/\1/' | tr '\n' ' ')" = "size criteria docs hygiene performance Mine (skipped) " ] && ok "groups in the fixed order, Cost shown as performance" || bad "order"
for g in size:limit criteria:rows criteria:defect-tests docs:"(check|missing)" hygiene:findings hygiene:waiting hygiene:"(branches|branch)" performance:cost; do
  grep -Eq "^(PASS|WARN|FAIL|UNREAD|INFO) ${g%%:*} [^ ]+ ${g##*:}:" <<<"$out" || bad "rule missing from the report: $g"
done; ok "every rule of every group is listed with a state"
grep -E "^(WARN|FAIL|UNREAD)" <<<"$out" | grep -qv -e "-> fix: " && bad "a non-pass line has no fix" || ok "each non-pass line carries its fix"
grep -q "^WARN size skills/x/scripts/near.py" <<<"$out" && grep -q "^FAIL docs Ghost missing" <<<"$out" && grep -q "^WARN hygiene loop/old branch" <<<"$out" \
  && grep -q "^FAIL criteria REL-1 rows" <<<"$out" && ok "findings from four groups show" || bad "findings"
[ "$(grep -c '^HEALTH: ' <<<"$out")" = 1 ] && tail -1 <<<"$out" | grep -q "^HEALTH: not green" && ok "one verdict, last" || bad "verdict"
grep -q "^[A-Z]* cost " <<<"$out" && bad "cost leaked into a line" || ok "no line says cost"
lone="$d/lone/skills/workflow-health"; mkdir -p "$lone"; cp -R "$here/skills/workflow-health/scripts" "$lone/"
out=$(python3 "$lone/scripts/health.py" check --group docs); rc=$?
grep -q "^UNREAD docs docs check: " <<<"$out" && ! grep -q "^PASS docs" <<<"$out" && [ $rc = 1 ] && ok "a rule that cannot read its data is UNREAD, never pass" || bad "unread"
$health check --group nothing 2>&1 | grep -q "^REFUSED: unknown group" && ok "an unknown group is refused" || bad "unknown group"

echo "== preview writes nothing"
before=$(writes)
out=$($health preview); echo "$out"
grep -q "^WOULD open issue 'health: size skills/x/scripts/near.py limit' on Backlog \[health:size\]" <<<"$out" \
  && grep -q "^WOULD open issue 'health: docs Ghost missing' on Backlog \[health:docs\]" <<<"$out" \
  && grep -q "\[health:hygiene\]" <<<"$out" && grep -q "\[health:criteria\]" <<<"$out" && ok "each issue it would open shows with its tag" || bad "preview lines"
[ "$(writes)" = "$before" ] && [ ! -f "$FAKE_GH_DIR/issues.json" ] && ok "preview made no write call" || bad "preview wrote"
GH_TOKEN=x $health preview >/dev/null; [ "$(writes)" = "$before" ] && ok "a token does not make preview write" || bad "token"
$health file 2>&1 | grep -q "^REFUSED: file needs --group" && [ "$(writes)" = "$before" ] && ok "file with no group refuses and writes nothing" || bad "file no group"

echo "== file --group writes only the named groups"
$health file --group docs >/dev/null
[ "$(count health:docs OPEN)" = 1 ] && [ "$(count health)" = 1 ] && ok "file --group docs opened only the docs issue" || bad "docs only"
$health file --group size | tee "$d/out" ; python3 - <<'PYEND' && ok "size issue: tagged health:size, on Backlog" || bad "size issue"
import json, os
issues = json.load(open(os.environ["FAKE_GH_DIR"] + "/issues.json"))
size = [i for i in issues if "size:" in i["body"]]
assert len(size) == 1 and size[0]["milestone"]["title"] == "Backlog"
names = [l["name"] for l in size[0]["labels"]]
assert "health:size" in names and "health" in names and "health:docs" not in names, names
assert len(issues) == 2
PYEND
grep -q "^DONE open issue" "$d/out" && ! grep -q "docs\|hygiene\|criteria" "$d/out" && ok "filing size printed only size work" || bad "size output"
# fix the docs finding; filing size must leave the docs issue alone, and filing docs then closes it
printf 'Calc\tcalc.py\n' > .loop/docs.tsv; git commit -qam "Drop Ghost"
$health file --group size >/dev/null
[ "$(count health:docs OPEN)" = 1 ] && ok "file --group size left the fixed docs issue open" || bad "other group touched"
out=$($health preview --group docs); grep -q "^WOULD close #1 .* \[health:docs\]" <<<"$out" && ok "preview shows the docs issue would close" || bad "preview close"
$health file --group docs >/dev/null
[ "$(count health:docs CLOSED)" = 1 ] && [ "$(count health:size OPEN)" = 1 ] && ok "file --group docs closed the docs issue only" || bad "docs close"
python3 -c "print('# pad\n' * 3500)" > skills/x/scripts/near.py; git commit -qam "Bigger"
$health file --group size | grep -q "^SAME\|^DONE update" && [ "$(count health:size)" = 1 ] && ok "a repeat updates its issue, opens no second" || bad "repeat"
git rm -q skills/x/scripts/near.py; git commit -qm "Fixed"
$health file --group size | grep -q "^DONE close #2" && ok "a fix closes it" || bad "close"
mkdir -p skills/x/scripts; python3 -c "print('# pad\n' * 3600)" > skills/x/scripts/near.py; git add -A; git commit -qm "Back"
$health file --group size | grep -q "^DONE reopen #2" && [ "$(count health:size OPEN)" = 1 ] && ok "a return reopens it" || bad "reopen"
$health file --group hygiene >/dev/null; git branch -q -d loop/old
$health file --group hygiene | grep -q "^DONE close .* \[health:hygiene\]" && [ "$(count health:hygiene CLOSED)" = 1 ] && ok "a fixed hygiene finding closes its issue" || bad "hygiene close"
$health preview --group mine | grep -q "^PREVIEW:" && ok "mine can be previewed when named" || bad "mine"
[ "$(cd "$here/skills/workflow-health/scripts" && python3 -c "import file; print(file.tag_of('cost'))")" = health:performance ] && ok "the Cost group is tagged health:performance" || bad "performance tag"
for f in health report file; do [ "$(wc -c < "$here/skills/workflow-health/scripts/$f.py")" -lt 18432 ] && ok "$f.py under the size warning" || bad "$f.py size"; done

echo "repo: $d/repo"
[ "$fails" = 0 ] && echo "ALL PASS" || { echo "$fails FAILED"; exit 1; }
