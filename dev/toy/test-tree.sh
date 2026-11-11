#!/bin/bash
# reads: skills/ docs/wiki/ README.md listing.json dev/toy/
# Checks that read every skill at once: script sizes, SKILL.md lengths and repo-wide greps. They live here, in one
# script that declares all of skills/, so the other toy scripts can declare only the files they run and their rows
# rerun only when those change (see lanes_cli.py check), and the checks of those headers on this repo. No model is
# called. usage: test-tree.sh
set -u
here=$(cd "$(dirname "$0")/../.." && pwd)
. "$here/dev/toy/reap.sh"
fails=0
ok() { echo "PASS: $1"; }
bad() { echo "FAIL: $1"; fails=$((fails + 1)); }
check() { if eval "$2"; then ok "$1"; else bad "$1"; fi; }

echo "== sizes"
check "every skill Python script is under 20 KB" '[ -z "$(find "$here/skills" -name "*.py" -size +20479c)" ]'
for f in "$here"/skills/*/scripts/*.py; do [ "$(wc -c < "$f")" -lt 20480 ] && ok "under 20 KB: $(basename "$f")" || bad "over 20 KB: $f"; done
for f in "$here"/skills/*/SKILL.md; do [ "$(wc -l < "$f")" -lt 150 ] && ok "under 150 lines: $(basename "$(dirname "$f")")" || bad "over 150 lines: $f"; done

echo "== repo-wide greps"
[ "$(grep -rlE '"pr", "merge"|gh pr merge' "$here/skills" --include=*.py | xargs -n1 basename | sort | tr '\n' ' ')" = "merge.py " ] && ok "no script calls gh pr merge but the release step's merge.py (which also merges its release PR)" || bad "a script merges"
check "a grep finds nothing for the old upgrade paths" '[ -z "$(grep -rniE --exclude=test-workers.sh --exclude=test-tree.sh -- "--session|board.py take|session (add|update|remove) |visible session|hand_over|sessions\.json|taken over" "$here/skills" "$here/docs/wiki" "$here/README.md" "$here/listing.json" "$here/dev/toy")" ]'

L="python3 $here/skills/workflow-regression/scripts/lanes_cli.py"
echo "== the repo's # reads: headers"
check "every test script a row of this repo names has a valid # reads: header (lanes_cli.py check)" '(cd "$here" && $L check >/dev/null)'
# Value: protects=done line 2 on the real table; fails_when=a header widens or the narrow closure regresses; why_new=no
# repo-level narrowing check; seam=none; no_claim=runtime savings (the PR table measures them)
out=$(cd "$here" && $L affected skills/workflow-monitoring/scripts/batch.py)
total=$(awk -F'\t' '!/^#/ && $2 == "land"' "$here/.loop/regression.tsv" | wc -l | tr -d ' ')
got=$(sed -n 's/^AFFECTED \([0-9]*\) of.*/\1/p' <<<"$out")
missing=$(cd "$here" && for s in $(grep -l "^# reads:.*skills/workflow-monitoring/scripts/batch.py" dev/toy/test-*.sh); do awk -F'\t' -v s="$s" '$2 == "land" && index($3, s) {print $1}' .loop/regression.tsv; done | while read -r id; do grep -qw "$id" <<<"$out" || echo "$id"; done)
check "on this repo a one-file change reruns fewer than half the land rows and every row whose script declares it" '[ -n "$got" ] && [ "$got" -lt $((total / 2)) ] && [ -z "$missing" ]'
# Value: protects=test-summary's and test-defect's rows rerun only on what they read (issue 172); fails_when=either stands in
# the repo root again (ROOT_RUN: every change reruns it); why_new=both ran there; seam=none; no_claim=skill changes (both read skills/)
out=$(cd "$here" && $L affected dev/toy/test-wiki.sh)
theirs=$(awk -F'\t' '$2 == "land" && $3 ~ /dev\/toy\/test-(summary|defect)\.sh/ {print $1}' "$here/.loop/regression.tsv")
hit=$(sed -n '1s/^AFFECTED [0-9]* of [0-9]* rows (\(.*\))$/\1/p' <<<"$out" | tr ',' '\n' | tr -d ' ' | grep -Fx -f <(echo "$theirs"))
check "on this repo a change to a script test-summary and test-defect never read reruns none of their rows" '[ -n "$theirs" ] && [ -z "$hit" ] && grep -q "^AFFECTED" <<<"$out"'
# Value: protects=a full clone (CI: .git a folder, its index naming every file) maps rows as a worktree does (issue 178);
# fails_when=lanes.py resolves a .git/ path again; why_new=only worktrees, where .git is a file, were checked; seam=none;
# no_claim=other untracked files in the tree
t=$(mktemp -d); toy_on_exit 'rm -rf "$t"'
git clone -q --depth 1 "file://$here" "$t/clone" 2>/dev/null
printf '#!/bin/bash\n# reads: skills/workflow-regression/scripts/tests.py\ngrep -q "/\\.git/" "$1"\n' > "$t/clone/dev/toy/test-zz.sh"  # lanes: no read (toy script)
deps=$($L deps --root "$t/clone" "bash dev/toy/test-zz.sh")
check "in a full clone a script naming .git/ gets no dependency inside git's store and is not run on every change" '[ -d "$t/clone/.git" ] && grep -qx "skills/workflow-regression/scripts/tests.py" <<<"$deps" && ! grep -q "^\.git\|^ALWAYS" <<<"$deps"'

echo "== this repo stays green: no docs check line but CHANGED, no health FAIL but a docs changed row"
# STALE and TESTS are left out too: a goal's own run or code change makes them mid-goal, and its release step fixes them.
out=$(cd "$here" && python3 skills/workflow-docs/scripts/docs.py check 2>&1)
! grep -Ev "^(CHANGED|STALE|TESTS) " <<<"$out" | grep -qv "^DOCS OK" && ok "this repo's docs check has no line other than CHANGED" || bad "repo docs: $out"
out=$(cd "$here" && python3 skills/workflow-health/scripts/health.py check 2>&1)
! grep "^FAIL" <<<"$out" | grep -Eqv "^FAIL docs \S+ (changed|tests)" && ok "this repo's health has no FAIL other than a docs changed row" || bad "repo health: $(grep '^FAIL' <<<"$out")"

[ "$fails" = 0 ] && echo "ALL PASS" || { echo "$fails FAILED"; exit 1; }
