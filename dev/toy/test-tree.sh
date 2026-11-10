#!/bin/bash
# reads: skills/ docs/wiki/ README.md listing.json dev/toy/
# Checks that read every skill at once: script sizes, SKILL.md lengths and repo-wide greps. They live here, in one
# script that declares all of skills/, so the other toy scripts can declare only the files they run and their rows
# rerun only when those change (see lanes_cli.py check). No model is called. usage: test-tree.sh
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

[ "$fails" = 0 ] && echo "ALL PASS" || { echo "$fails FAILED"; exit 1; }
