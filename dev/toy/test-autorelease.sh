#!/bin/bash
# reads: skills/workflow-delivery/scripts/goal.py skills/workflow-monitoring/scripts/board_status.py
# reads: skills/workflow-monitoring/scripts/graph.py skills/workflow-monitoring/scripts/live_board.py
# reads: skills/workflow-monitoring/scripts/board_page.py skills/workflow-release/scripts/merge.py
# reads: skills/workflow-setup/scripts/setup.py
unset LOOP_SESSION_TOOL LOOP_OPERATION_SESSION  # a toy test never reaches a real session tool
# Proves the automatic release on a throwaway toy repo with a fake gh. usage: test-autorelease.sh [DIR]
unset LOOP_BATCH LOOP_PRIVATE_NAMES
set -e
unset GITHUB_SERVER_URL GITHUB_REPOSITORY GITHUB_RUN_ID  # run cells and rendered Tests never depend on the runner
export LOOP_ROLE=worker  # goal.py and flow.py run only in a worker
here=$(cd "$(dirname "$0")/../.." && pwd)
. "$here/dev/toy/reap.sh"
export HOME=$(mktemp -d)  # setup.py writes the private settings under HOME
d=${1:-$(mktemp -d)}; rm -rf "$d"; mkdir -p "$d"
"$here/dev/toy/make.sh" "$d"
export LOOP_FLOW="$d/flow.json"
export PATH="$here/dev/toy/fakegh:$PATH" FAKE_GH_DIR="$d/gh" FAKE_GH_ORIGIN="$d/origin.git"
goal="python3 $here/skills/workflow-delivery/scripts/goal.py"
merge() { FAKE_GH_PR_STATE=${PRS:-OPEN} python3 "$here/skills/workflow-release/scripts/merge.py" "$@"; }
cd "$d/repo"
python3 "$here/skills/workflow-setup/scripts/setup.py" --bare >/dev/null
git switch -q main; git merge -q --no-edit workflow-setup
python3 - <<'PY'
import json
c = json.load(open(".loop/config.json")); c["auto_merge"] = True
json.dump(c, open(".loop/config.json", "w"), indent=2)
PY
git commit -qam "Turn auto_merge on"; git push -q origin main
fails=0
ok() { echo "PASS: $1"; }
bad() { echo "FAIL: $1"; fails=$((fails + 1)); }
state() { python3 -c "import json,sys;print(json.load(open('$(git rev-parse --git-common-dir)/loop/runs/$1.json')).get('$2',''))"; }
remote_file() { git fetch -q origin; git show "origin/main:$1"; }

finish() {  # finish SLUG: a done goal with a pull request; MSG sets the commit subject
  local slug=$1
  git switch -q main; git pull -q origin main
  $goal new "$slug" --here --goal "Add $slug" --done "calc has $slug" >/dev/null
  printf '\n\ndef %s():\n    return 1\n' "${slug//-/_}" >> calc.py
  git add calc.py; git commit -qm "${MSG:-Add ${slug} to calc}"
  python3 - "$slug" <<'PY'
import sys
path = ".loop/goals/%s.md" % sys.argv[1]
text = open(path).read().replace("## Verify by hand\n", "## Verify by hand\n\n1. Open calc.py.\n   Expect: it has the new function.\n", 1)
open(path, "w").write(text)
PY
  git commit -qam "Verify steps for $slug"
  bash "$here/dev/toy/flow-done.sh" "$slug" && $goal pr "$slug" >/dev/null
  git push -q origin "loop/$slug" 2>/dev/null || true
}

echo "== 1. a merged goal bumps the version once, writes the changelog and a published release, with no question"
finish one
export FAKE_GH_MERGE_BRANCH=loop/one
out=$(merge one); echo "$out"
grep -q "^RELEASED v0.1.1" <<<"$out" && ok "released v0.1.1" || bad "released"
[ "$(remote_file VERSION)" = "0.1.1" ] && ok "VERSION on origin/main" || bad "VERSION"
remote_file CHANGELOG.md | grep -q "^## v0.1.1 - $(date -u +%F)" && remote_file CHANGELOG.md | grep -q "Expect: it has the new function" \
  && ok "CHANGELOG has the note and verify steps" || bad "CHANGELOG"
grep -q "^release create v0.1.1 --title v0.1.1 " "$FAKE_GH_DIR/calls.log" && ! grep -Eq "^release create .*--draft" "$FAKE_GH_DIR/calls.log" \
  && ok "published release, no draft" || bad "release call"
[ "$(state one release)" = cut ] && ok "recorded as cut" || bad "state"
out=$(PRS=MERGED merge one); grep -q "^ALREADY" <<<"$out" && [ "$(remote_file VERSION)" = "0.1.1" ] && ok "a second run bumps nothing" || bad "twice"
[ "$(git log origin/main --format=%s | grep -c '^Release ')" = 1 ] && ok "one release commit" || bad "release commits"

echo "== 2. a breaking change releases a patch with no question, the reason named"
MSG="feat!: drop the old API" finish brk
export FAKE_GH_MERGE_BRANCH=loop/brk
out=$(merge brk); echo "$out"
grep -q "^RELEASED v0.1.2" <<<"$out" && [ "$(state brk release_part)" = patch ] && state brk release_reason | grep -q "a commit says breaking" \
  && ok "breaking released as a patch, named in the reason" || bad "breaking"
(cd "$here" && python3 - <<'PY'
import sys; sys.path.insert(0, "skills/workflow-release/scripts")
import autorelease as a
assert a.next_version("1.2.3", "major") == "2.0.0" and a.next_version("0.4.1", "major") == "0.5.0" and a.next_version("1.2.3", "patch") == "1.2.4"
PY
) && ok "major after 1.0, minor before" || bad "next_version"

echo "== 3. a failing routine refuses the merge and shows under Needs you"
python3 - <<'PY'
import json
c = json.load(open(".loop/config.json")); c["routines"] = ["touch ../routine-ran", "false"]  # outside the repo, so later goals start clean
json.dump(c, open(".loop/config.json", "w"), indent=2)
PY
git switch -q main; git pull -q origin main; git commit -qam "Add routines"; git push -q origin main
finish rtn
export FAKE_GH_MERGE_BRANCH=loop/rtn
before=$(git rev-parse origin/main)
merge rtn && bad "merged past a failing routine" || ok "failing routine refused"
[ -f ../routine-ran ] && ok "the owner's routine ran" || bad "routine ran"
git fetch -q origin; [ "$(git rev-parse origin/main)" = "$before" ] && ok "nothing merged" || bad "merged"
state rtn release_error | grep -q "routine false" && ok "failure recorded on the goal" || bad "release_error"
(cd "$here" && python3 - "$d/repo" <<'PY'
import sys; sys.path.insert(0, "skills/workflow-monitoring/scripts")
import os
os.environ["LOOP_BOARD_HEALTH"] = "green"
import live_board
text = "\n".join(live_board.render(sys.argv[1]))
assert "Issues" in text and "rtn: the release failed" in text, text
PY
) && ok "shows under Issues" || bad "needs you"

echo "== 4. a failed merge is recorded and shown"
python3 - <<'PY'
import json
c = json.load(open(".loop/config.json")); c["routines"] = ["true"]
json.dump(c, open(".loop/config.json", "w"), indent=2)
PY
git switch -q main; git pull -q origin main; git commit -qam "Routines pass"; git push -q origin main
finish mrg
FAKE_GH_MERGE_FAIL=1 merge mrg && bad "merge failure ignored" || ok "failed merge refused"
state mrg release_error | grep -q "could not merge" && ok "merge failure recorded" || bad "merge error record"

echo "== 5. a release that fails after the push does not bump twice on retry"
finish half
export FAKE_GH_MERGE_BRANCH=loop/half
FAKE_GH_RELEASE_FAIL=1 merge half && bad "release failure ignored" || ok "failed release refused"
v=$(remote_file VERSION)
state half release_error | grep -q "gh release create" && ok "release failure recorded" || bad "release record"
PRS=MERGED merge half | grep -q "^RELEASED" && [ "$(remote_file VERSION)" = "$v" ] && ok "retry only created the release" || bad "retry"

echo "== 6. a stale page refuses the merge"
git switch -q main; git pull -q origin main; mkdir -p docs/wiki; echo page > docs/wiki/Calc.md; printf 'Calc\tcalc.py\n' > .loop/docs.tsv
git add -A; git commit -qm "Map the Calc page"; git push -q origin main
finish stale
FAKE_GH_MERGE_BRANCH=loop/stale merge stale && bad "merged past a stale page" || ok "stale page refused"
state stale release_error | grep -q "stale wiki pages" && ok "stale refusal recorded" || bad "stale record"

echo "== 7. the pull request body says nothing about checks"
! grep -qi "checks" "$FAKE_GH_DIR"/body-1 && grep -q "Skill flow:" "$FAKE_GH_DIR"/body-1 && ok "honest PR body" || bad "PR body"

echo "repo: $d/repo"
[ "$fails" = 0 ] && echo "ALL PASS" || { echo "$fails FAILED"; exit 1; }
