#!/bin/bash
# reads: skills/ docs/wiki/ README.md listing.json dev/toy/
# Checks that read every skill at once: script sizes, SKILL.md lengths and repo-wide greps. They live here, in one
# script that declares all of skills/, so the other toy scripts can declare only the files they run and their rows
# rerun only when those change (see lanes_cli.py check), and the checks of those headers on this repo. No model is
# called. usage: test-tree.sh
set -u
here=$(cd "$(dirname "$0")/../.." && pwd)
fails=0
ok() { echo "PASS: $1"; }
bad() { echo "FAIL: $1"; fails=$((fails + 1)); }
check() { if eval "$2"; then ok "$1"; else bad "$1"; fi; }

echo "== sizes"
check "every script is under 20 KB" '[ -z "$(find "$here/skills" -name "*.py" -size +20479c)" ]'
for f in "$here"/skills/*/scripts/*.py; do [ "$(wc -c < "$f")" -lt 20480 ] && ok "under 20 KB: $(basename "$f")" || bad "over 20 KB: $f"; done
for f in "$here"/skills/*/SKILL.md; do [ "$(wc -l < "$f")" -lt 150 ] && ok "under 150 lines: $(basename "$(dirname "$f")")" || bad "over 150 lines: $f"; done

echo "== repo-wide greps"
[ "$(grep -rlE '"pr", "merge"|gh pr merge' "$here/skills" --include=*.py | xargs -n1 basename | tr '\n' ' ')" = "merge.py " ] && ok "no script calls gh pr merge but the release step's merge.py" || bad "a script merges"
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

[ "$fails" = 0 ] && echo "ALL PASS" || { echo "$fails FAILED"; exit 1; }
