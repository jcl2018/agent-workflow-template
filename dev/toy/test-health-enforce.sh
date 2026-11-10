#!/bin/bash
# reads: skills/workflow-health/scripts/enforce.py skills/workflow-health/scripts/health.py
# Test the not-enforced grace (HLT-2, REG-1, DOC-1; issue 118): a requirement with no regression row warns when it is
# Unreviewed or Reviewed at most 7 days ago, and fails once it has stayed not enforced longer.
set -u
here=$(cd "$(dirname "$0")/../.." && pwd)
fails=0
ok() { echo "PASS: $1"; }
bad() { echo "FAIL: $1"; fails=$((fails + 1)); }
r=$(mktemp -d); trap 'rm -rf "$r"' EXIT
mkdir -p "$r/docs/wiki" "$r/.loop"
today=$(date +%Y-%m-%d); old=$(python3 -c 'import datetime; print(datetime.date.today() - datetime.timedelta(days=8))')
printf '{"wiki_dir": "docs/wiki"}\n' > "$r/.loop/config.json"
printf -- '- TOY-1: **Reviewed %s** New today\n- TOY-2: **Reviewed %s** Old\n- TOY-3: **Unreviewed** Draft\n' "$today" "$old" > "$r/docs/wiki/Toy.md"
state() { python3 - "$here/skills/workflow-health/scripts" "$r" "$1" <<'PY'
import sys
sys.path.insert(0, sys.argv[1])
import enforce
print(enforce.row(sys.argv[2], sys.argv[3], lambda *a: a)[0])
PY
}
[ "$(state TOY-1)" = WARN ] && ok "a Reviewed requirement with no test warns as not enforced within 7 days (issue 118)" || bad "new reviewed: $(state TOY-1)"
[ "$(state TOY-2)" = FAIL ] && ok "a Reviewed requirement not enforced for 8 days fails (issue 118)" || bad "old reviewed: $(state TOY-2)"
[ "$(state TOY-3)" = WARN ] && ok "an Unreviewed requirement with no test warns, never fails (issue 118)" || bad "unreviewed: $(state TOY-3)"
[ "$(state TOY-9)" = FAIL ] && ok "a requirement on no page still fails" || bad "no page: $(state TOY-9)"
[ "$fails" = 0 ] && echo "ALL PASS" || { echo "$fails FAILED"; exit 1; }
