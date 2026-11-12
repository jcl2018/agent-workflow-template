#!/bin/bash
# reads: skills/workflow-delivery/scripts/private.py skills/workflow-delivery/scripts/goal.py
# reads: skills/workflow-release/scripts/autorelease.py skills/workflow-release/scripts/merge.py
# reads: dev/toy/fakegh/gh dev/toy/fakegh/fake.py
# Done line 7 of local-schedule: a private repo's pr lane posts its real result as commit statuses named after every
# required check, so its merge needs no click and no bypass. No network: gh is the fake. usage: test-statuses.sh [PART]
# Value: protects=a private repo's pull request merges with no click, and a lane that failed never reads as passed;
# fails_when=a status is success for a failed lane, posted for a public repo or unreadable rules, or missing on a moved head;
# why_new=the lane result only existed locally; seam=none; no_claim=GitHub's own acceptance of a status (the owner's spike)
set -u
unset GITHUB_SERVER_URL GITHUB_REPOSITORY GITHUB_RUN_ID LOOP_SESSION_TOOL LOOP_OPERATION_SESSION
here=$(cd "$(dirname "$0")/../.." && pwd); only=${1:-}
. "$here/dev/toy/reap.sh"
export HOME=$(mktemp -d) PATH="$here/dev/toy/fakegh:$PATH"
d=$(mktemp -d); toy_on_exit 'rm -rf "$d" "$HOME"'
export FAKE_GH_DIR="$d/gh"; mkdir -p "$FAKE_GH_DIR"
unset LOOP_PRIVATE_NAMES
fails=0
ok() { echo "PASS: $1"; }
bad() { echo "FAIL: $1"; fails=$((fails + 1)); }
check() { if eval "$2"; then ok "$1"; else bad "$1"; echo "    out: ${out:-}"; fi; }
want() { [ -z "$only" ] || [ "$only" = "$1" ]; }
P="$here/skills/workflow-delivery/scripts"; M="$here/skills/workflow-release/scripts"
log="$FAKE_GH_DIR/statuses.log"
git init -q --bare -b main "$d/origin.git"
git clone -q "$d/origin.git" "$d/repo" 2>/dev/null; cd "$d/repo"
git config user.email t@example.test; git config user.name Toy
mkdir -p .loop src; printf 'a\n' > src/a.txt; printf '{"base": "main", "auto_merge": true}\n' > .loop/config.json
git add -A; git commit -qm base; git push -q origin main
base=$(git rev-parse HEAD)
git switch -qc loop/g; echo a2 >> src/a.txt; git commit -qam "goal change"; head=$(git rev-parse HEAD)
rules() { printf '%s\n' "$1" > "$FAKE_GH_DIR/rules.json"; }
two='[{"type": "required_status_checks", "parameters": {"required_status_checks": [{"context": "lane-a", "integration_id": null}, {"context": "lane-b"}]}}]'
reset() { rm -f "$log" "$FAKE_GH_DIR"/protection.json "$FAKE_GH_DIR"/status-fail-* "$FAKE_GH_DIR/calls.log"; rules "$two"; unset FAKE_GH_RULES_ERROR FAKE_GH_PROTECTION_ERROR FAKE_GH_REQUIRE; export FAKE_GH_PRIVATE=true; }
lane() {  # OK(1|0) BRANCH HEAD: what goal.py pr calls after the lane
  python3 - "$P" "$1" "$2" "$3" <<'PY'
import sys
sys.path.insert(0, sys.argv[1]); import private
sys.exit(0 if private.pr_result(".", "main", sys.argv[4], sys.argv[3], sys.argv[2] == "1") else 5)
PY
}
count() { [ -f "$log" ] && { grep -c "$1" "$log" || true; } || echo 0; }

if want pass; then reset
  git push -q origin loop/g
  out=$(lane 1 loop/g "$head"); rc=$?
  check "a passed lane posts one success per required check, named after it, with the local run in the description and no target_url" \
    '[ $rc = 0 ] && [ "$(count "\"state\": \"success\"")" = 2 ] && grep -q "\"context\": \"lane-a\"" "$log" && grep -q "\"context\": \"lane-b\"" "$log" && grep -q "local run" "$log" && ! grep -q "\"target\": true" "$log" && grep -q "^STATUSES posted success for lane-a, lane-b on " <<<"$out"'
fi
if want fail; then reset
  git push -q origin --delete loop/g 2>/dev/null
  out=$(lane 0 loop/g "$head"); check "a failed lane on a head that is not on the remote posts nothing" '[ ! -s "$log" ] && grep -q "head not on the remote" <<<"$out"'
  git push -q origin loop/g
  out=$(lane 0 loop/g "$head")
  check "a failed lane posts only failure, one per required check, never success" '[ "$(count "\"state\": \"failure\"")" = 2 ] && [ "$(count "\"state\": \"success\"")" = 0 ]'
fi
if want public; then reset; export FAKE_GH_PRIVATE=false; git push -q origin loop/g
  out=$(lane 1 loop/g "$head"); check "a public repo gets no status at all" '[ ! -s "$log" ] && grep -q "public or unreadable" <<<"$out"'
fi
if want unreadable; then reset; export FAKE_GH_PRIVATE=error; git push -q origin loop/g
  out=$(lane 1 loop/g "$head"); check "a visibility that cannot be read posts nothing" '[ ! -s "$log" ]'
  export FAKE_GH_PRIVATE=true FAKE_GH_RULES_ERROR=1
  out=$(lane 1 loop/g "$head"); check "rules that cannot be read post nothing and name the cause and fix" '[ ! -s "$log" ] && grep -q "(STATUSES_UNREADABLE)" <<<"$out" && grep -q "gh auth refresh" <<<"$out"'
  unset FAKE_GH_RULES_ERROR; export FAKE_GH_PROTECTION_ERROR=1
  out=$(lane 1 loop/g "$head"); check "a classic protection read that fails (not a 404) posts nothing" '[ ! -s "$log" ]'
fi
if want rerun; then reset; git push -q origin loop/g
  lane 1 loop/g "$head" >/dev/null; lane 0 loop/g "$head" >/dev/null
  out=$(for c in lane-a lane-b; do grep "\"context\": \"$c\"" "$log" | tail -1; done)
  check "a rerun of a pushed head that now fails posts failure, which replaces the earlier success" '[ "$(grep -c "\"state\": \"failure\"" <<<"$out")" = 2 ] && [ "$(count "\"state\": \"success\"")" = 2 ]'
fi
if want union; then reset; git push -q origin loop/g
  rules '[{"type": "required_status_checks", "parameters": {"required_status_checks": [{"context": "lane-a"}, {"context": "bound-x", "integration_id": 15368}]}}, {"type": "merge_queue", "parameters": {}}, {"type": "pull_request", "parameters": {"required_approving_review_count": 1}}]'
  printf '{"required_status_checks": {"strict": true, "checks": [{"context": "lane-a", "app_id": null}, {"context": "lane-c", "app_id": -1}]}, "required_linear_history": {"enabled": true}}\n' > "$FAKE_GH_DIR/protection.json"
  out=$(python3 "$P/private.py" required); echo "$out" > "$d/req.txt"
  check "the contexts are the deduplicated union of the ruleset and classic protection" '[ "$(grep -vc "^BLOCKS" "$d/req.txt")" = 2 ] && grep -qx lane-a "$d/req.txt" && grep -qx lane-c "$d/req.txt" && ! grep -qx bound-x "$d/req.txt"'
  check "a check bound to an app, a merge queue, approving reviews, strict branches and linear history are named BLOCKS" \
    'grep -q "^BLOCKS: bound-x" "$d/req.txt" && grep -q "merge_queue" "$d/req.txt" && grep -q "required_approving_review_count" "$d/req.txt" && grep -q "strict" "$d/req.txt" && grep -q "required_linear_history" "$d/req.txt"'
  out=$(lane 1 loop/g "$head"); check "a bound check is never posted" '! grep -q bound-x "$log" && [ "$(count "\"state\": \"success\"")" = 2 ]'
fi
if want postfails; then reset; git push -q origin loop/g
  echo "500 1" > "$FAKE_GH_DIR/status-fail-lane-a"; echo "422 9" > "$FAKE_GH_DIR/status-fail-lane-b"
  out=$(lane 1 loop/g "$head"); rc=$?
  check "a 5xx is retried and posts; a 4xx is not retried, is named in posted k of n, and the lane returns failure to the caller" \
    '[ $rc = 5 ] && grep -q "\"context\": \"lane-a\", \"state\": \"success\"" "$log" && ! grep -q "lane-b" "$log" && grep -q "STATUS_FAILED posted 1 of 2; failed: lane-b" <<<"$out" && [ "$(grep -c "statuses/$head.*context=lane-b" "$FAKE_GH_DIR/calls.log")" = 1 ]'
  # goal.py pr exits 5 and records statuses: failed (the PR is created once, a rerun reuses it)
  grep -q 'return 5 \* (state\["statuses"\] == "failed")' "$P/goal.py"; check "goal.py pr ends with exit 5 when a status failed to post, and records it" '[ $? = 0 ] && grep -q "state\[\"statuses\"\] = \"ok\" if private.pr_result" "$P/goal.py"'
fi
if want wikehead; then reset
  git push -q origin loop/g
  mkdir -p docs/wiki; echo page > docs/wiki/Page.md; git add docs/wiki/Page.md; git commit -qm "wiki page"; wiki=$(git rev-parse HEAD); git push -q origin loop/g
  common=$(git rev-parse --git-common-dir); mkdir -p "$common/loop/runs"
  echo "{\"slug\": \"g\", \"branch\": \"loop/g\", \"status\": \"done\", \"pr\": \"https://example.test/pull/1\", \"pr_base\": \"$base\", \"pr_head\": \"$head\"}" > "$common/loop/runs/g.json"
  export FAKE_GH_REQUIRE=lane-a,lane-b FAKE_GH_PR_STATE=OPEN FAKE_GH_PR_HEAD=$wiki
  out=$(python3 "$M/merge.py" g 2>&1)
  check "a head moved by a wiki-only commit gets the lane's statuses before the merge, and the branch rule lets the merge through" \
    '[ "$(grep -c "\"sha\": \"$wiki\".*\"state\": \"success\"" "$log")" = 2 ] && grep -q "^MERGED https://example.test/pull/1" <<<"$out"'
  unset FAKE_GH_REQUIRE FAKE_GH_PR_STATE FAKE_GH_PR_HEAD
fi
if want release; then reset
  git push -q origin loop/g
  mkdir -p "$d/rel"; cd "$d/rel"; git clone -q "$d/origin.git" t 2>/dev/null; cd t; git config user.email t@example.test; git config user.name Toy
  printf '#!/bin/bash\n# reads: src/a.txt\ntest ! -e src/broken\n' > src/row.sh
  printf '# id\tlevel\tcommand\tgoal\tseen_red\tdescription\tcategory\tlink\nrow-a\tland\tbash src/row.sh\tg:1\t2026-01-01\tGiven a row, when it runs, then it passes.\tcriterion\t\n' > .loop/regression.tsv
  git add -A; git commit -qm rows; git push -q origin main
  git switch -qc release/v1-g; echo 1 > VERSION; git add VERSION; git commit -qm "Release v1 (g)"; good=$(git rev-parse HEAD); git push -q origin release/v1-g
  git switch -q main; git switch -qc release/v2-g; echo 2 >> src/a.txt; touch src/broken; git add -A; git commit -qm "Release v2 (g)"; bro=$(git rev-parse HEAD); git push -q origin release/v2-g
  rel() {  # SHA BRANCH
    python3 - "$M" "$1" "$2" <<'PY'
import json, sys
sys.path.insert(0, sys.argv[1]); import autorelease
state = {}
autorelease.release_statuses(".", {"base": "main"}, state, sys.argv[3], sys.argv[2])
print("release_status=" + state.get("release_status", "none"))
PY
  }
  out=$(rel "$good" release/v1-g); check "a release PR head that reaches no row gets a real success from the affected-rows run" 'grep -q "release_status=success" <<<"$out" && grep -q "\"sha\": \"$good\".*\"state\": \"success\"" "$log"'
  out=$(rel "$bro" release/v2-g); check "a release PR head that fails a row gets failure, never success" 'grep -q "release_status=failure" <<<"$out" && grep -q "\"sha\": \"$bro\".*\"state\": \"failure\"" "$log" && ! grep -q "\"sha\": \"$bro\".*\"state\": \"success\"" "$log"'
  cd "$d/repo"
  grep -q "autorelease.release_statuses(top, cfg, state" "$M/merge.py"; check "merge.py advance runs it before it merges the release PR" '[ $? = 0 ]'
fi
if want nobypass; then reset
  check "merge.py carries no --admin and no --auto on any gh call" '! grep -n -e "\"--admin\"" -e "\"--auto\"" "$M/merge.py" "$M/autorelease.py"'
  check "both merge calls are plain --merge" '[ "$(grep -c "\"--merge\"" "$M/merge.py")" = 2 ]'
fi
if want readonly; then reset; git push -q origin loop/g
  "$here/dev/toy/make.sh" "$d/setup" >/dev/null; printf '%s\n' '[{"type": "required_status_checks", "parameters": {"required_status_checks": [{"context": "lane-a"}]}}, {"type": "merge_queue", "parameters": {}}]' > "$FAKE_GH_DIR/rules.json"
  printf '{"required_status_checks": {"checks": [{"context": "lane-b", "app_id": null}]}}\n' > "$FAKE_GH_DIR/protection.json"
  export LOOP_SCHEDULE_HOME="$d/sched" LOOP_AGENTS_DIR="$d/agents" LOOP_LAUNCHCTL="$here/dev/toy/fakegh/launchctl"
  out=$(cd "$d/setup/repo" && python3 "$here/skills/workflow-setup/scripts/setup.py" 2>&1)
  check "setup reads the rulesets and protection and writes neither: no write call to rules or protection and no status reaches gh" \
    'grep -q "rules/branches" "$FAKE_GH_DIR/calls.log" && grep -q "protection" "$FAKE_GH_DIR/calls.log" && ! grep -Eq "api (-X|--method) (PUT|PATCH|POST|DELETE)" "$FAKE_GH_DIR/calls.log" && [ ! -s "$log" ]'
fi
[ "$fails" = 0 ] && echo "ALL PASS" || { echo "$fails FAILED"; exit 1; }
