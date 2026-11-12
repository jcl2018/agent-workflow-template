#!/bin/bash
# reads: docs/ROADMAP.md README.md
# Test that docs/ROADMAP.md has a V1 section of seven items, each with a link and a state, and that README's Status line points at it.
set -u
here=$(cd "$(dirname "$0")/../.." && pwd)
sec=$(awk '/^## V1$/{on=1;next} /^## /{on=0} on' "$here/docs/ROADMAP.md")
items=$(grep -c '^- \[[ x]\] \*\*[1-7]\. ' <<<"$sec")
linked=$(grep '^- \[[ x]\] \*\*[1-7]\. ' <<<"$sec" | grep -c 'https://github.com/.*State: ')
if [ "$items" = 7 ] && [ "$linked" = 7 ] && grep -q '#2881' <<<"$sec" && grep -q 'docs/ROADMAP.md#v1' "$here/README.md"; then
  echo "PASS: the V1 section has seven linked items with a state, and README points at it"; echo "ALL PASS"
else
  echo "FAIL: items=$items linked=$linked"; exit 1
fi
