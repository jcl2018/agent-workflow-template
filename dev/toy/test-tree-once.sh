#!/bin/bash
# reads: dev/toy/tree-once.sh
# tree-once.sh runs its command once per tree state and replays it, and a lock left by a dead holder is claimed at once
# rather than waited on (a row killed at its limit must not stall the rows after it). A stand-in command; no model.
here=$(cd "$(dirname "$0")/../.." && pwd)
. "$here/dev/toy/reap.sh"
fails=0
ok() { echo "PASS: $1"; }
bad() { echo "FAIL: $1"; fails=$((fails + 1)); }
T=$(mktemp -d); toy_on_exit 'rm -rf "$T"'
export TMPDIR=$T TREE_ONCE_CMD="echo run >> $T/count; echo hello; exit 3"
out=$(bash "$here/dev/toy/tree-once.sh"); rc=$?
out2=$(bash "$here/dev/toy/tree-once.sh"); rc2=$?
[ "$out" = hello ] && [ $rc = 3 ] && [ "$out2" = hello ] && [ $rc2 = 3 ] && [ "$(wc -l < "$T/count" | tr -d ' ')" = 1 ] \
  && ok "the command runs once and a second caller gets its output and exit code replayed" || bad "replay: $out/$rc $out2/$rc2 $(cat "$T/count")"
rm -f "$T"/toy-tree-once-*.rc "$T"/toy-tree-once-*.out "$T/count"; rm -rf "$T"/toy-tree-once-*.lock
( exit 0 ) & dead=$!; wait "$dead"
base=$(TMPDIR=$T bash -c '. /dev/null; here='"$here"'; cd "$here"; key=$( (git rev-parse HEAD; git status --porcelain; git diff HEAD; git ls-files -o --exclude-standard -z | xargs -0 cat) 2>/dev/null | cksum | tr -d " "); echo "$TMPDIR/toy-tree-once-$key"')
mkdir "$base.lock" && echo "$dead" > "$base.lock/pid"
[ -d "$base.lock" ] || bad "the test made no lock at tree-once's own path"
s=$(date +%s); out=$(bash "$here/dev/toy/tree-once.sh"); rc=$?
[ "$out" = hello ] && [ $rc = 3 ] && [ $(( $(date +%s) - s )) -lt 10 ] \
  && [ "$(wc -l < "$T/count" | tr -d ' ')" = 1 ] && ok "a lock whose holder died is claimed at once, not waited on" || bad "takeover: $out/$rc after $(( $(date +%s) - s ))s"
rm -f "$T"/toy-tree-once-*.rc "$T"/toy-tree-once-*.out; rm -rf "$T"/toy-tree-once-*.lock
export TREE_ONCE_CMD="echo SKIP: stand-in; exit 77"
bash "$here/dev/toy/tree-once.sh" >/dev/null; TOY_SKIP_FILE=$T/skip bash "$here/dev/toy/tree-once.sh" >/dev/null; rc=$?
[ $rc = 77 ] && [ -s "$T/skip" ] && ok "a replayed skip (exit 77) writes TOY_SKIP_FILE, so its row reads SKIPPED, not FAIL" || bad "skip replay: rc $rc, file $(cat "$T/skip" 2>/dev/null)"
[ "$fails" = 0 ] && echo "ALL PASS" || { echo "$fails FAILED"; exit 1; }
