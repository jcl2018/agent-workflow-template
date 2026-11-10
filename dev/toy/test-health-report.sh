#!/bin/bash
# reads: skills/workflow-health/scripts/health.py skills/workflow-setup/scripts/setup.py
# reads: skills/workflow-health/scripts/
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
printf '<!-- workflow-docs -->\n# Calc\n\n## Summary\n\nCalc adds numbers.\n\n## Criteria\n\n- REL-1: **Reviewed 2026-01-01** calc adds.\n' > docs/wiki/Calc.md
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
[ "$(sed -n 1p <<<"$out")" = "HEALTH REPORT" ] && sed -n 2p <<<"$out" | grep -q "^groups run: size, criteria, docs, hygiene, performance, controls; skipped: Mine (no private rules set)$" \
  && ok "the header names every group run and the one skipped" || bad "header"
[ "$(grep -n '^== ' <<<"$out" | sed 's/^[0-9]*:== \(.*\) ==$/\1/' | tr '\n' ' ')" = "size criteria docs hygiene performance Mine (skipped) controls " ] && ok "groups in the fixed order, Cost shown as performance" || bad "order"
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
# Value: protects=a docs check problem of any kind is never also shown as a passing docs check; fails_when=rule_of maps
#   only some docs kinds to check, so complete() pads PASS docs check beside a FAIL; why_new=the report test only had a
#   missing page, which was mapped; seam=none; no_claim=none beyond protects
cp .loop/docs.tsv "$d/docs.tsv"; printf 'Calc\tcalc.py\n' > .loop/docs.tsv; printf '<!-- workflow-docs -->\n# Extra\n' > docs/wiki/Extra.md
out=$($health check --group docs); rm docs/wiki/Extra.md; cp "$d/docs.tsv" .loop/docs.tsv
grep -q "^FAIL docs Extra unmapped" <<<"$out" && ! grep -q "^PASS docs" <<<"$out" && ok "a docs problem of any kind shows no passing docs check" || bad "docs pass beside a fail"
# Value: protects=a rule that shares an unreadable source is UNREAD, never a pass; fails_when=complete() pads done-lines
#   as PASS when regression sync could not be read; why_new=the lone test only ran the docs group; seam=none;
#   no_claim=none beyond protects
out=$(python3 "$lone/scripts/health.py" check --group criteria)
grep -q "^UNREAD criteria done-lines" <<<"$out" && ! grep -q "^PASS criteria done-lines" <<<"$out" && ok "an unread source leaves its other rule UNREAD" || bad "unread padding"
# Value: protects=check --json rows agree with its counts, padded PASS rows included; fails_when=report() hands back the
#   raw rows; why_new=no JSON shape test; seam=none; no_claim=none beyond protects
$health check --json | python3 -c "import json,sys; d=json.load(sys.stdin); c=d['counts']; sys.exit(0 if sum(1 for r in d['rows'] if r['state'] in c) == sum(c.values()) else 1)" \
  && ok "json rows match counts" || bad "json rows and counts disagree"
# Value: protects=a repeated group name runs once, so file never opens twin issues; fails_when=groups_of keeps repeats;
#   why_new=no test names a group twice; seam=none; no_claim=none beyond protects
[ "$($health check --group cost,performance | grep -c '^[A-Z]* performance ')" = "$($health check --group performance | grep -c '^[A-Z]* performance ')" ] \
  && ok "a group named twice runs once" || bad "repeated group ran twice"
# Value: protects=a check of named groups lists the rest as skipped and shows no rule of theirs as passing; fails_when=
#   complete() pads groups that did not run, or the header drops "not asked"; why_new=only the full check header is
#   asserted; seam=none; no_claim=none beyond protects
out=$($health check --group docs)
sed -n 2p <<<"$out" | grep -q "^groups run: docs; skipped: size (not asked), criteria (not asked), hygiene (not asked), performance (not asked), Mine (not asked), controls (not asked)$" \
  && ! grep -Eq "^PASS (size|criteria|hygiene|performance) " <<<"$out" && ok "a named group run lists the rest as skipped, none shown passing" || bad "named group header"

echo "== preview writes nothing"
before=$(writes)
out=$($health preview); echo "$out"
grep -q "^WOULD open issue 'health: size skills/x/scripts/near.py limit' on Backlog \[health:size\]" <<<"$out" \
  && grep -q "^WOULD open issue 'health: docs Ghost missing' on Backlog \[health:docs\]" <<<"$out" \
  && grep -q "\[health:hygiene\]" <<<"$out" && grep -q "\[health:criteria\]" <<<"$out" && ok "each issue it would open shows with its tag" || bad "preview lines"
[ "$(writes)" = "$before" ] && [ ! -f "$FAKE_GH_DIR/issues.json" ] && ok "preview made no write call" || bad "preview wrote"
GH_TOKEN=x $health preview >/dev/null; [ "$(writes)" = "$before" ] && ok "a token does not make preview write" || bad "token"
# Value: protects=the old run --live (cron, habit) now only previews and writes nothing; fails_when=run is pointed back at
#   file or --live regains a write path; why_new=no test calls run or --live since the rename; seam=none; no_claim=none beyond protects
$health run --live | grep -q "^PREVIEW: " && [ "$(writes)" = "$before" ] && ok "the old run --live only previews, writes nothing" || bad "run alias"
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
# Value: protects=an issue filed before tags (plain health label) gains its health:<group> tag; fails_when=plan() stops
#   updating an issue whose body matches but whose tag is missing; why_new=every other issue here is born tagged;
#   seam=none; no_claim=real gh label semantics (fake gh)
python3 - <<'PYEND'
import json, os
p = os.environ["FAKE_GH_DIR"] + "/issues.json"; issues = json.load(open(p))
for i in issues:
    if "size:" in i["body"]: i["labels"] = [{"name": "health"}]
json.dump(issues, open(p, "w"))
PYEND
$health preview --group size | grep -q "^WOULD update #2 size:.* \[health:size\]" && $health file --group size >/dev/null && [ "$(count health:size OPEN)" = 1 ] \
  && ok "an untagged old issue is updated to carry its group tag" || bad "tag backfill"
git rm -q skills/x/scripts/near.py; git commit -qm "Fixed"
$health file --group size | grep -q "^DONE close #2" && ok "a fix closes it" || bad "close"
mkdir -p skills/x/scripts; python3 -c "print('# pad\n' * 3600)" > skills/x/scripts/near.py; git add -A; git commit -qm "Back"
$health file --group size | grep -q "^DONE reopen #2" && [ "$(count health:size OPEN)" = 1 ] && ok "a return reopens it" || bad "reopen"
$health file --group hygiene >/dev/null; git branch -q -d loop/old
$health file --group hygiene | grep -q "^DONE close .* \[health:hygiene\]" && [ "$(count health:hygiene CLOSED)" = 1 ] && ok "a fixed hygiene finding closes its issue" || bad "hygiene close"
$health preview --group mine | grep -q "^PREVIEW:" && ok "mine can be previewed when named" || bad "mine"
# Value: protects=a mine issue stays open when the private rules are missing, and never carries private output;
#   fails_when=plan() counts an all-INFO mine group as ran, or body_of files the rule's detail; why_new=mine was only
#   previewed; seam=none; no_claim=real private rules (a stand-in rule printing a marker)
printf '{"rules": [{"name": "secretcheck", "command": ["sh", "-c", "echo PRIVATE-OUTPUT; exit 2"]}]}' > "$d/mine.json"
LOOP_HEALTH="$d/mine.json" $health file --group mine >/dev/null
grep -q "PRIVATE-OUTPUT" "$FAKE_GH_DIR/issues.json" && bad "mine output filed" || ok "a filed mine issue carries no private output"
[ "$(count health:mine OPEN)" = 1 ] && LOOP_HEALTH="$d/none.json" $health file --group mine >/dev/null \
  && [ "$(count health:mine OPEN)" = 1 ] && ok "missing private rules close no mine issue" || bad "mine closed on missing rules"
# Value: protects=when gh cannot list the health issues, preview and file refuse and write nothing; fails_when=held() falls
#   back to an empty list, so every finding reopens as a duplicate; why_new=the fake gh always answers; seam=none;
#   no_claim=real gh error text (a stand-in gh that prints no JSON)
mkdir -p "$d/badgh"; printf '#!/bin/bash\necho "$*" >> "%s/badgh/calls"\necho "HTTP 502" >&2; exit 1\n' "$d" > "$d/badgh/gh"; chmod +x "$d/badgh/gh"
p=$(PATH="$d/badgh:$PATH" $health preview --group size 2>&1); f=$(PATH="$d/badgh:$PATH" $health file --group size 2>&1)
grep -q "^REFUSED: could not read the health issues: HTTP 502" <<<"$p" && grep -q "^REFUSED: could not read the health issues" <<<"$f" \
  && ! grep -qEv "^issue list " "$d/badgh/calls" && ok "an unreadable issue list refuses, writes nothing" || bad "gh unreadable"
[ "$(cd "$here/skills/workflow-health/scripts" && python3 -c "import file; print(file.tag_of('cost'))")" = health:performance ] && ok "the Cost group is tagged health:performance" || bad "performance tag"
for f in health report file; do [ "$(wc -c < "$here/skills/workflow-health/scripts/$f.py")" -lt 18432 ] && ok "$f.py under the size warning" || bad "$f.py size"; done

echo "repo: $d/repo"
[ "$fails" = 0 ] && echo "ALL PASS" || { echo "$fails FAILED"; exit 1; }
