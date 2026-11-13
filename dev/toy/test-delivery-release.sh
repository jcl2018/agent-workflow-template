#!/bin/bash
# reads: skills/workflow-delivery/scripts/goal.py skills/workflow-delivery/scripts/flow.py skills/workflow-delivery/scripts/fit.py
# reads: skills/workflow-delivery/scripts/private.py skills/workflow-docs/scripts/docs.py
# reads: skills/workflow-release/scripts/autorelease.py skills/workflow-release/scripts/merge.py
# reads: skills/workflow-release/scripts/release.py
# reads: skills/workflow-release/scripts/wiki.py skills/workflow-setup/scripts/setup.py
# reads: skills/workflow-release/SKILL.md skills/workflow-release/references/commands.md skills/ skills/workflow-release/scripts/
# The release half of delivery-prd (DEL-5, DEL-9, issues 129, 134, 154, 170) on a throwaway toy repo, with a
# test-local gh shim (dev/toy/release-gh.py) around dev/toy/fakegh and a pre-receive hook in the toy origin that stands in for a protected main.
# usage: test-delivery-release.sh [CASE]   CASE: patch removed bump protected rules review pending nomatch crash
#        dirty mismatch exists latebump private wikiname firstpage wikinull docs (default: all). Prints PASS:/FAIL: lines; exits non-zero on any FAIL.
unset LOOP_SESSION_TOOL LOOP_OPERATION_SESSION LOOP_BATCH LOOP_PRIVATE_NAMES TOY_PROTECT TOY_PR_MODE
set -u
export LOOP_ROLE=worker
here=$(cd "$(dirname "$0")/../.." && pwd); only=${1:-all}; self="$here/dev/toy/$(basename "$0")"
. "$here/dev/toy/reap.sh"
export HOME=$(mktemp -d)
d=$(mktemp -d); toy_on_exit 'rm -rf "$d" "$HOME"'
"$here/dev/toy/make.sh" "$d" >/dev/null || { echo "FAIL: toy repo"; exit 1; }
export LOOP_FLOW="$d/flow.json" FAKE_GH_DIR="$d/gh" FAKE_GH_ORIGIN="$d/origin.git" TOY_FAKEGH="$here/dev/toy/fakegh/gh"
mkdir -p "$d/shim" "$d/gh"
cp "$here/dev/toy/release-gh.py" "$d/shim/gh.py"  # the test-local gh shim
printf '#!/bin/bash\nexec python3 "%s/shim/gh.py" "$@"\n' "$d" > "$d/shim/gh"; chmod +x "$d/shim/gh"
export PATH="$d/shim:$PATH"
goal="python3 $here/skills/workflow-delivery/scripts/goal.py"
docs="python3 $here/skills/workflow-docs/scripts/docs.py"
wiki="python3 $here/skills/workflow-release/scripts/wiki.py"
cd "$d/repo" || exit 1
python3 "$here/skills/workflow-setup/scripts/setup.py" --bare >/dev/null
git switch -q main; git merge -q --no-edit workflow-setup
python3 - <<'PY'
import json
c = json.load(open(".loop/config.json")); c["auto_merge"] = True
json.dump(c, open(".loop/config.json", "w"), indent=2)
PY
echo old > old.py
$docs add Toy-notes --paths README.md >/dev/null
printf '<!-- workflow-docs -->\n# Toy notes\n\nThe toy is a tiny calculator; its readme says so.\n' > docs/wiki/Toy-notes.md
git add -A; git commit -qm "auto_merge on, old.py, a wiki page"; git push -q origin main
$docs publish >/dev/null
cat > "$d/origin.git/hooks/pre-receive" <<'SH'
#!/bin/bash
{ [ -n "${TOY_SERVER_MERGE:-}" ] || [ -z "${TOY_PROTECT:-}" ]; } && exit 0
while read -r old new ref; do
  if [ "$ref" = refs/heads/main ]; then
    echo refused >> refused.log
    echo "remote: error: ${TOY_HOOK_MSG:-GH006: Protected branch update failed for refs/heads/main.}" >&2; exit 1
  fi
done
SH
chmod +x "$d/origin.git/hooks/pre-receive"
R="$(cd "$(git rev-parse --git-common-dir)" && pwd)/loop/runs"
fails=0
ok() { echo "PASS: $1"; }
bad() { echo "FAIL: $1"; fails=$((fails + 1)); }
want() { [ "$only" = all ] || [ "$only" = "$1" ]; }
state() { python3 -c "import json,sys;print(json.load(open('$R/$1.json')).get('$2',''))"; }
origin_main() { git fetch -q origin; git rev-parse origin/main; }
remote_file() { git fetch -q origin; git show "origin/main:$1"; }
bumped() { python3 -c "import sys;n=[int(x) for x in sys.argv[1].split('.')];i={'major':0,'minor':1}.get(sys.argv[2],2);n[i]+=1;n[i+1:]=[0]*(2-i);print('.'.join(map(str,n)))" "$1" "$2"; }
releases() { python3 -c "import json,sys;print(sum(r['tag']==sys.argv[1] and (len(sys.argv)<3 or r['target']==sys.argv[2]) for r in json.load(open('$d/gh/releases.json'))))" "$@" 2>/dev/null || echo 0; }
merge() { FAKE_GH_PR_STATE=${PRS:-OPEN} FAKE_GH_MERGE_BRANCH=loop/$1 python3 "${MERGE:-$here/skills/workflow-release/scripts/merge.py}" "$1" 2>&1; }
list() { mkdir -p "$HOME/.workflow-loop"; printf '%s\n' "$@" > "$HOME/.workflow-loop/private-names"; }

finish() {  # finish SLUG [LINE]: a done goal with a pull request; PRE runs before the commit
  local slug=$1
  git switch -q main; git pull -q origin main
  $goal new "$slug" --here --goal "Add $slug" --done "calc has $slug" >/dev/null || bad "goal new $slug"
  printf '\n\ndef %s():\n    return 1\n%s\n' "${slug//-/_}" "${2:-}" >> "${FILE:-calc.py}"
  ${PRE:-true}
  git add -A "${FILE:-calc.py}"; git commit -qam "Add $slug to calc"
  python3 - "$slug" <<'PY'
import sys
path = ".loop/goals/%s.md" % sys.argv[1]
text = open(path).read().replace("## Verify by hand\n", "## Verify by hand\n\n1. Open calc.py.\n   Expect: it has the new function.\n", 1)
open(path, "w").write(text)
PY
  git commit -qam "Verify steps for $slug"
  bash "$here/dev/toy/flow-done.sh" "$slug" && $goal pr "$slug" >/dev/null || bad "goal $slug did not reach a pull request"
}

if want patch; then
  echo "== DEL-5: patch by default"
  finish fixone; v=$(remote_file VERSION)
  out=$(merge fixone); echo "$out" | tail -3
  [ "$(state fixone release_part)" = patch ] && [ "$(remote_file VERSION)" = "$(bumped "$v" patch)" ] && grep -q "patch by default" <<<"$(state fixone release_reason)" \
    && ok "DEL-5: a code change releases a patch by default" || bad "DEL-5: patch default"
fi

if want removed; then
  echo "== #170: a removed file is named, never major or ask"
  PRE="git rm -q old.py" finish rmold; v=$(remote_file VERSION)
  out=$(merge rmold); echo "$out" | tail -3
  [ "$(state rmold release_part)" = patch ] && [ "$(remote_file VERSION)" = "$(bumped "$v" patch)" ] && grep -q "removes old.py" <<<"$(state rmold release_reason)" \
    && ok "#170: a removed file releases a patch, the removal named in the reason" || bad "#170: removed file"
fi

if want bump; then
  echo "== DEL-5: the goal's own bump (goal.py set --bump minor writes the sidecar)"
  finish minorone; v=$(remote_file VERSION)
  python3 - "$R/minorone.extra.json" <<'PY'
import json, os, sys
data = json.load(open(sys.argv[1])) if os.path.exists(sys.argv[1]) else {}
data.setdefault("set", {})["bump"] = "minor"
json.dump(data, open(sys.argv[1], "w"))
PY
  out=$(merge minorone); echo "$out" | tail -3
  [ "$(state minorone release_part)" = minor ] && [ "$(remote_file VERSION)" = "$(bumped "$v" minor)" ] \
    && ok "DEL-5: goal.py set --bump minor (the sidecar) releases a minor" || bad "DEL-5: set bump"
fi

if want docsbump; then
  echo "== #3787: the goal's own bump wins on a docs-only goal"
  FILE=notes.md finish docsminor; v=$(remote_file VERSION)
  python3 - "$R/docsminor.extra.json" <<'PY'
import json, os, sys
data = json.load(open(sys.argv[1])) if os.path.exists(sys.argv[1]) else {}
data.setdefault("set", {})["bump"] = "minor"
json.dump(data, open(sys.argv[1], "w"))
PY
  out=$(merge docsminor); echo "$out" | tail -3
  [ "$(state docsminor release_part)" = minor ] && [ "$(remote_file VERSION)" = "$(bumped "$v" minor)" ] \
    && ok "#3787: a docs-only goal with goal.py set --bump minor releases a minor" || bad "#3787: docs-only bump"
fi

if want docspatch; then
  echo "== #3787: a docs-only goal with no bump still releases a patch"
  FILE=notes.md finish docsplain; v=$(remote_file VERSION)
  out=$(merge docsplain); echo "$out" | tail -3
  [ "$(state docsplain release_part)" = patch ] && [ "$(remote_file VERSION)" = "$(bumped "$v" patch)" ] \
    && ok "#3787: a docs-only goal with no bump releases a patch" || bad "#3787: docs-only patch"
fi

if want protected; then
  echo "== #134: a protected main releases through the release PR"
  finish prot; v=$(remote_file VERSION); x=$(bumped "$v" patch)
  out=$(TOY_PROTECT=1 merge prot); echo "$out" | tail -4
  oid=$(origin_main)
  [ "$(remote_file VERSION)" = "$x" ] && remote_file CHANGELOG.md | grep -q "^## v$x " && [ -s "$d/origin.git/refused.log" ] \
    && ok "#134: a protected base lands VERSION and CHANGELOG through the release PR" || bad "#134: release PR landing"
  [ "$(releases "v$x")" = 1 ] && [ "$(releases "v$x" "$oid")" = 1 ] && [ "$(git log -1 --format=%p "$oid" | wc -w)" -eq 2 ] \
    && ok "#134: exactly one GitHub release, at the release PR's merge commit" || bad "#134: one release at the merge commit"
  grep -Eq "^(NO CHANGE|PUBLISHED)" <<<"$out" && [ -z "$(state prot wiki_error)" ] && ok "#134: the wiki publish still runs after the release PR" || bad "#134: wiki publish"
  python3 -c "import json,sys;p=json.load(open('$d/gh/rpr.json'));assert any(v['head']=='release/v$x-prot' and v['title']=='Release v$x (prot)' and v['state']=='MERGED' for v in p.values())" \
    && ok "#134: the release PR is release/vX-<slug>, titled Release vX (<slug>)" || bad "#134: release PR name"
  grep -q "^pr merge https://example.test/pull/1[0-9][0-9] --merge$" "$d/gh/calls.log" && ! grep -q -- "--admin" "$d/gh/calls.log" \
    && ok "#154: the loop merges the release PR itself with gh pr merge --merge, never --admin" || bad "#154: loop merge"
fi

if want rules; then
  echo "== #134: a pull_request rule takes the release PR path up front"
  finish ruled; x=$(bumped "$(remote_file VERSION)" patch); before=$(cat "$d/origin.git/refused.log" 2>/dev/null | wc -l)
  echo '[{"type": "pull_request", "parameters": {}}]' > "$d/gh/rules.json"
  out=$(TOY_PROTECT=1 merge ruled); echo "$out" | tail -3; rm -f "$d/gh/rules.json"
  [ "$(cat "$d/origin.git/refused.log" 2>/dev/null | wc -l)" = "$before" ] && [ "$(remote_file VERSION)" = "$x" ] && [ "$(state ruled release)" = cut ] \
    && ok "#134: a pull_request rule takes the release PR path with no direct push" || bad "#134: rules endpoint"
fi

if want review; then
  echo "== #154: a release PR needing review is the owner's"
  finish revw; x=$(bumped "$(remote_file VERSION)" patch)
  out=$(TOY_PROTECT=1 TOY_PR_MODE=review merge revw); rc=$?; echo "$out" | tail -2
  err=$(state revw release_error); n=$(state revw release_pr); n=${n##*/}
  [ $rc -ne 0 ] && grep -q "(RELEASE_PR_BLOCKED)" <<<"$err" && grep -q "gh pr merge $n --merge, then merge.py revw" <<<"$err" \
    && [ "$(state revw release_tries)" = 1 ] && [ "$(releases "v$x")" = 0 ] \
    && ok "#154: a release PR needing review records RELEASE_PR_BLOCKED with the owner's command" || bad "#154: blocked"
  gh pr merge "$n" --merge >/dev/null 2>&1
  out=$(TOY_PROTECT=1 PRS=MERGED merge revw); echo "$out" | tail -2
  grep -q "^RELEASED v$x" <<<"$out" && [ "$(releases "v$x")" = 1 ] && [ -z "$(state revw release_error)" ] \
    && ok "#154: after the owner merges, merge.py creates the release" || bad "#154: owner merged"
fi

if want pending; then
  echo "== #154: pending checks wait"
  finish pend; x=$(bumped "$(remote_file VERSION)" patch)
  out=$(TOY_PROTECT=1 TOY_PR_MODE=pending merge pend); rc=$?; echo "$out" | tail -2
  [ $rc -eq 0 ] && [ -n "$(state pend release_pr_waiting)" ] && [ -z "$(state pend release_error)" ] && [ "$(releases "v$x")" = 0 ] \
    && ok "#154: pending checks wait (release_pr_waiting), no error, no release" || bad "#154: pending"
  out=$(TOY_PROTECT=1 PRS=MERGED merge pend); echo "$out" | tail -2
  grep -q "^RELEASED v$x" <<<"$out" && [ -z "$(state pend release_pr_waiting)" ] && ok "#154: the next merge.py run merges the waiting release PR" || bad "#154: retry"
fi

if want nomatch; then
  echo "== #134: a refusal that is not protection keeps the three tries"
  finish other; prs=$(grep -c "head release/" "$d/gh/calls.log")
  out=$(TOY_PROTECT=1 TOY_HOOK_MSG="disk quota exceeded" merge other); rc=$?; echo "$out" | tail -2
  [ $rc -ne 0 ] && grep -q "rejected 3 times" <<<"$(state other release_error)" && [ "$(grep -c "head release/" "$d/gh/calls.log")" = "$prs" ] \
    && ok "#134: a push refused for another reason opens no release PR" || bad "#134: non-matching refusal"
fi

if want crash; then
  echo "== DEL-5: a crash after release create is adopted"
  finish crsh; x=$(bumped "$(remote_file VERSION)" patch)
  TOY_CRASH_CREATE=1 merge crsh >/dev/null && bad "the crash was not seen"
  out=$(PRS=MERGED merge crsh); echo "$out" | tail -2
  grep -q "^ADOPTED" <<<"$out" && grep -q "^RELEASED v$x" <<<"$out" && [ "$(releases "v$x")" = 1 ] \
    && ok "DEL-5: a crash after release create is adopted on the rerun, one release" || bad "DEL-5: crash adopted"
fi

if want dirty; then
  echo "== DEL-5: a release PR behind a moved VERSION is closed and restarted once"
  finish drty; x=$(bumped "$(remote_file VERSION)" patch)
  out=$(TOY_PROTECT=1 TOY_PR_MODE=dirty merge drty); echo "$out" | tail -2
  first=$(grep -m1 "^pr close " "$d/gh/calls.log")
  grep -q "^RESTART the release pull request: .*behind the base" <<<"$out" && [ -n "$first" ] && grep -q "^RELEASED v$x" <<<"$out" \
    && [ "$(releases "v$x")" = 1 ] && ok "DEL-5: a conflicting release PR is closed and restarted once, one release" || bad "DEL-5: dirty restart"
fi

if want mismatch; then
  echo "== DEL-5: a merged release PR whose VERSION is not vX makes no release"
  finish mism; x=$(bumped "$(remote_file VERSION)" patch)
  out=$(TOY_PROTECT=1 TOY_PR_MODE=mismatch merge mism); rc=$?; echo "$out" | tail -1
  [ $rc -ne 0 ] && grep -q "(RELEASE_VERSION_MISMATCH)" <<<"$(state mism release_error)" && [ "$(releases "v$x")" = 0 ] \
    && ok "DEL-5: VERSION mismatch at the merge commit records RELEASE_VERSION_MISMATCH, no release" || bad "DEL-5: mismatch"
  git switch -q main; git pull -q origin main; echo "$x" > VERSION; git commit -qam "VERSION by hand"; TOY_SERVER_MERGE=1 git push -q origin main
  out=$(TOY_PROTECT=1 PRS=MERGED merge mism); echo "$out" | tail -1
  grep -q "^RELEASED v$x" <<<"$out" && [ "$(releases "v$x" "$(origin_main)")" = 1 ] \
    && ok "DEL-5: after the owner sets VERSION on the base, the rerun releases at its tip" || bad "DEL-5: mismatch fix"
fi

if want exists; then
  echo "== DEL-5: a release vX made elsewhere is never replaced"
  finish exst; x=$(bumped "$(remote_file VERSION)" patch)
  python3 -c "import json,os,sys;p='$d/gh/releases.json';r=json.load(open(p)) if os.path.exists(p) else [];r.append({'tag':'v$x','target':'0000000'});json.dump(r,open(p,'w'))"
  out=$(merge exst); rc=$?; echo "$out" | tail -1
  [ $rc -ne 0 ] && grep -q "(RELEASE_EXISTS)" <<<"$(state exst release_error)" && [ "$(releases "v$x")" = 1 ] && [ "$(releases "v$x" 0000000)" = 1 ] \
    && ok "DEL-5: an existing release vX at another commit records RELEASE_EXISTS and stays the only one" || bad "DEL-5: exists"
fi

if want latebump; then
  echo "== DEL-5: a bump set after a refused merge.py still binds"
  finish late "# owner: late-secret-zz"; list "late-secret-zz"; merge late >/dev/null
  rm -f "$HOME/.workflow-loop/private-names"; v=$(remote_file VERSION)
  python3 -c "import json,os;p='$R/late.extra.json';x=json.load(open(p)) if os.path.exists(p) else {};x.setdefault('set',{})['bump']='minor';json.dump(x,open(p,'w'))"
  out=$(merge late); echo "$out" | tail -1
  [ "$(state late release_part)" = minor ] && [ "$(remote_file VERSION)" = "$(bumped "$v" minor)" ] \
    && ok "DEL-5: goal.py set --bump after a refused merge.py releases the bump set" || bad "DEL-5: late bump"
fi

if want private; then
  echo "== DEL-9: the scan before merge.py merges"
  finish leaky "# owner: acme-corp-secret"; before=$(origin_main); url=$(state leaky pr)
  list "# private names" "acme-corp-secret"
  out=$(merge leaky); rc=$?; echo "$out" | tail -1
  [ $rc -ne 0 ] && grep -q "(PRIVATE_NAME)" <<<"$out" && ! grep -q "acme-corp-secret" <<<"$(state leaky release_error)" && [ "$(origin_main)" = "$before" ] \
    && ! grep -qx "pr merge $url --merge" "$d/gh/calls.log" && ok "DEL-9: a private name in the branch refuses merge.py, nothing merged" || bad "DEL-9: private name"
  list "ok-name" "bad(pattern"
  out=$(merge leaky); rc=$?; echo "$out" | tail -1
  [ $rc -ne 0 ] && grep -q "(PRIVATE_LIST)" <<<"$out" && grep -q "line 2" <<<"$out" && [ "$(origin_main)" = "$before" ] \
    && ok "DEL-9: a broken list (invalid pattern) refuses merge.py, nothing merged" || bad "DEL-9: broken list"
  rm -f "$HOME/.workflow-loop/private-names"
  cp -R "$here/skills" "$d/skills"; rm "$d/skills/workflow-delivery/scripts/private.py"
  out=$(MERGE="$d/skills/workflow-release/scripts/merge.py" merge leaky); rc=$?; echo "$out" | tail -1
  [ $rc -ne 0 ] && grep -q "(PRIVATE_MODULE)" <<<"$out" && grep -q "workflow-delivery/scripts/private.py" <<<"$out" && [ "$(origin_main)" = "$before" ] \
    && ! grep -qx "pr merge $url --merge" "$d/gh/calls.log" && ok "DEL-9: private.py moved away refuses with PRIVATE_MODULE, nothing merged" || bad "DEL-9: module missing"
fi

if want wikiname || want firstpage || want wikinull; then
  git switch -q main; git pull -q origin main
  $goal new wk --here --goal "Wiki checks" --done "the wiki is checked" >/dev/null
fi

if want wikiname; then
  echo "== DEL-9: wiki publish scans every page"
  git switch -q main; git pull -q origin main
  printf 'Someone else wrote this page.\nIt mentions plantedname-x9 by mistake.\n' > docs/wiki/Other.md
  git add docs/wiki/Other.md; git commit -qm "A page the goal never touched"; TOY_SERVER_MERGE=1 git push -q origin main
  list "plantedname-x9"; head=$(git --git-dir="$d/origin.wiki.git" rev-parse main)
  out=$($wiki publish wk 2>&1); rc=$?; echo "$out" | tail -1
  err=$(state wk wiki_error)
  [ $rc -ne 0 ] && grep -q "wiki:Other:2" <<<"$err" && grep -q "(PRIVATE_NAME)" <<<"$err" && ! grep -q plantedname <<<"$err" \
    && [ "$(git --git-dir="$d/origin.wiki.git" rev-parse main)" = "$head" ] && ok "DEL-9: wiki publish stops on a planted name in an untouched page" || bad "DEL-9: wiki scan"
  rm -f "$HOME/.workflow-loop/private-names"
  git rm -q docs/wiki/Other.md; git commit -qm "Drop the page"; TOY_SERVER_MERGE=1 git push -q origin main
fi

if want firstpage; then
  echo "== #129: a wiki with no first page names the fix"
  mv "$d/origin.wiki.git" "$d/aside.wiki.git"
  out=$($wiki publish wk 2>&1); rc=$?; echo "$out" | tail -1
  mv "$d/aside.wiki.git" "$d/origin.wiki.git"
  [ $rc -ne 0 ] && grep -q "create the first page in the repo's Wiki tab, then run merge.py wk again" <<<"$(state wk wiki_error)" \
    && ok "#129: a wiki with no first page names the fix" || bad "#129: first page"
fi

if want wikinull; then
  echo "== a wiki refusal never crashes on a goal state with no usable report"
  for kind in null str; do
    case $kind in null) value=null ;; str) value='"an old note"' ;; esac
    python3 - "$R/wk.json" "$value" <<'PY'
import json, sys
state = json.load(open(sys.argv[1])); state["report"] = json.loads(sys.argv[2]); state.pop("wiki_error", None)
json.dump(state, open(sys.argv[1], "w"), indent=2)
PY
    mv "$d/origin.wiki.git" "$d/aside.wiki.git"
    rc=0; out=$($wiki publish wk 2>"$d/wiki-err.txt") || rc=$?
    mv "$d/aside.wiki.git" "$d/origin.wiki.git"
    [ $rc -eq 1 ] && grep -q "^WIKI REFUSED wk: .*create the first page in the repo's Wiki tab, then run merge.py wk again" <<<"$out" && ! grep -qE "Traceback|AttributeError" <<<"$out$(cat "$d/wiki-err.txt")" \
      && ok "a $kind report: the wiki refusal prints WIKI REFUSED on stdout with its fix, exit 1, no traceback" || bad "a $kind report: wiki refusal crashed or lost its text ($rc: ${out:0:160})"
    python3 - "$R/wk.json" "$kind" <<'PY' && ok "a $kind report: the wiki failure is recorded in a dict report" || bad "a $kind report: wiki failure not recorded"
import json, sys
state = json.load(open(sys.argv[1])); report = state["report"]
assert isinstance(report, dict) and "Wiki not published:" in report["text"] and state["wiki_error"]
if sys.argv[2] == "str":
    assert "the stored report was a str and was reset" in report["text"]
PY
  done
fi

if want docs; then
  echo "== #129: the docs say merge.py publishes"
  S="$here/skills/workflow-release/SKILL.md"; C="$here/skills/workflow-release/references/commands.md"
  ! grep -iE "merge\.py[^.]*\bdrafts? (a|the) release" "$S" "$C" && grep -q "publishes the release (no draft)" "$S" && grep -q "publishes the release (no draft)" "$C" \
    && grep -q "release PR" "$S" && grep -q "goal.py set SLUG --bump" "$S" && [ "$(wc -l < "$S")" -lt 150 ] \
    && ok "#129: the docs say merge.py publishes (no draft) and only cut drafts" || bad "#129: docs"
  was=$fails
  for code in PRIVATE_NAME PRIVATE_LIST PRIVATE_MODULE RELEASE_PR_BLOCKED RELEASE_VERSION_MISMATCH RELEASE_EXISTS REQUIREMENT_MISSING; do
    grep -q "| \`$code\`" "$C" || bad "codes table lacks $code"
  done
  for f in "$here"/skills/workflow-release/scripts/*.py "$self"; do
    [ "$(wc -c < "$f")" -lt 20480 ] || bad "$(basename "$f") is over 20 KB"
  done
  [ "$fails" = "$was" ] && ok "the release codes table and every release script under 20 KB"
fi

[ "$fails" = 0 ] || { echo "$fails FAILED"; exit 1; }
echo "ALL PASS"
