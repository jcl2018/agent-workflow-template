#!/bin/bash
# reads: dev/toy/adoption-golden.tsv docs/wiki/Setup.md
# Test SET-11's golden first adoption: the fixture holds exactly steps 1 to 8 in order, each with a check, a golden
# result and a fix, names no machine path or account, and SET-11 names it. usage: test-adoption-golden.sh
set -e
here=$(cd "$(dirname "$0")/../.." && pwd)
gold="$here/dev/toy/adoption-golden.tsv"; page="$here/docs/wiki/Setup.md"
fails=0
ok() { echo "PASS: $1"; }
bad() { echo "FAIL: $1"; fails=$((fails + 1)); }
[ -f "$gold" ] || { echo "FAIL: $gold is missing"; exit 1; }
rows=$(grep -v '^#' "$gold" | tr -d '\r')
[ "$(cut -f1 <<<"$rows" | tr '\n' ' ')" = "1 2 3 4 5 6 7 8 " ] && ok "steps 1 to 8 in order" || bad "steps are not exactly 1 to 8 in order"
[ "$(awk -F'\t' 'NF != 4 || $2 == "" || $3 == "" || $4 == ""' <<<"$rows")" = "" ] && ok "each step has a check, golden result and fix" \
  || bad "a step lacks a check, golden result or fix"
! grep -qiE '[A-Z]:\|/Users/|/home/|@[a-z0-9-]+\.[a-z]' "$gold" && ok "no machine path or account" || bad "the fixture names a machine path or account"
req=$(awk '/^- SET-11:/{on=1; print; next} on && /^- [A-Z]+-[0-9]+:/{exit} on' "$page")
grep -q 'Unreviewed' <<<"$req" && grep -q 'dev/toy/adoption-golden.tsv' <<<"$req" && grep -q 'first mismatch' <<<"$req" \
  && ok "SET-11 names the fixture and stops at the first mismatch" || bad "SET-11 does not name the fixture or its stop rule"
[ "$fails" = 0 ] && echo "ALL PASS" || { echo "FAILED $fails"; exit 1; }
