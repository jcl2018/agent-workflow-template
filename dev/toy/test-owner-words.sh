#!/bin/bash
here=$(cd "$(dirname "$0")/../.." && pwd)
. "$here/dev/toy/reap.sh"
# windows: ok
# reads: skills/workflow-monitoring/scripts/sessions.py skills/workflow-monitoring/scripts/ownerwords.py
# reads: skills/workflow-docs/scripts/criteria.py skills/workflow-docs/scripts/ownerrec.py
# DOC-2 with a relay: the operation session records the owner's exact message for the requirement IDs it covers; a worker
# reviews or un-reviews with --owner-record for those IDs only, once per command; a worker cannot write a record.
# Value: protects=only the owner's recorded words change a review, for the IDs they name (DOC-2); fails_when=a worker
# writes a record, a record covers an ID it does not list, or a record is used twice for one command; why_new=a worker
# needed the owner to type in its own chat; seam=none; no_claim=that the operation session quotes the owner truthfully
set -u
unset LOOP_SESSION_TOOL LOOP_OPERATION_SESSION LOOP_OWNER_WORDS
d=$(mktemp -d); toy_on_exit 'rm -rf "$d"'
fails=0
ok() { echo "PASS: $1"; }
bad() { echo "FAIL: $1"; fails=$((fails + 1)); }
sess="python3 $here/skills/workflow-monitoring/scripts/sessions.py"
cri="python3 $here/skills/workflow-docs/scripts/criteria.py"
cd "$d" && git init -q . && git config user.email t@t && git config user.name t
mkdir -p docs/wiki .loop && echo '{"base":"main"}' > .loop/config.json
printf '<!-- workflow-docs -->\n# Foo\n\nReview: **Unreviewed**\n\n## Problem\n- p\n\n## Requirements\n\n### Functional\n- FOO-1: **Unreviewed** First\n  - sub\n- FOO-2: **Unreviewed** Second\n  - sub\n\n### Non-functional\n\nNone\n' > docs/wiki/Foo.md
git add -A && git commit -qm init
words=$'Review FOO-1 \t "now"\nplease'
echo "== the record"
LOOP_ROLE=worker $sess owner-words "x" --ids FOO-1 >/dev/null 2>&1 && bad "a worker wrote an owner-words record" || ok "a worker cannot write an owner-words record"
[ ! -s .git/loop/owner-words.tsv ] && ok "the refused worker wrote nothing" || bad "the refused worker left a record"
env -u LOOP_ROLE $sess owner-words "$words" --ids FOO-1 | grep -q "OWNER-WORDS o1 covers FOO-1" && ok "the operation role records the owner's message" || bad "no record written"
python3 - <<'PY' && ok "the record keeps the exact text, tabs, quotes and new line" || bad "record text changed"
import json
row = open(".git/loop/owner-words.tsv", encoding="utf-8").read().rstrip("\n").split("\t")
assert len(row) == 5 and row[0] == "o1" and row[2] == "operation" and row[4] == "FOO-1"
assert json.loads(row[3]) == 'Review FOO-1 \t "now"\nplease'
PY
echo "== using it"
LOOP_ROLE=worker $cri review FOO-2 --user --owner-record o1 </dev/null >/dev/null 2>&1 && bad "a record covered an ID it does not list" || ok "an ID the record does not cover is refused"
grep -q "FOO-2: \*\*Unreviewed\*\*" docs/wiki/Foo.md && ok "the refused review changed nothing" || bad "refused review changed the page"
LOOP_ROLE=worker $cri review FOO-1 --user --owner-record o9 </dev/null >/dev/null 2>&1 && bad "a missing record was accepted" || ok "a missing record is refused"
LOOP_ROLE=worker $cri review FOO-1 --user --owner-record o1 </dev/null | grep -q "REVIEWED FOO-1" && ok "a worker reviews FOO-1 with the record" || bad "review with record failed"
grep -q "FOO-1: \*\*Reviewed" docs/wiki/Foo.md && ok "FOO-1 is Reviewed" || bad "FOO-1 not reviewed"
tail -1 .git/loop/reviews.tsv | grep -q $'review\tFOO-1\trecord o1: Review FOO-1 "now" please' && ok "reviews.tsv names the record and the owner's words" || bad "reviews.tsv line"
LOOP_ROLE=worker $cri review FOO-1 --user --owner-record o1 </dev/null >/dev/null 2>&1 && bad "a record was used twice for review" || ok "a record is used once for one command"
LOOP_ROLE=worker $cri unreview FOO-1 --user --owner-record o1 </dev/null | grep -q "UNREVIEWED FOO-1" && ok "the same record may un-review its ID once" || bad "unreview with record failed"
[ "$fails" = 0 ] && echo "ALL PASS" || { echo "FAILED $fails"; exit 1; }
