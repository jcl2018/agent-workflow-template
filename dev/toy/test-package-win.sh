#!/bin/bash
# reads: dev/package.py skills/ listing.json README.md LICENSE VERSION CHANGELOG.md
# Prove dev/package.py gives a Windows checkout the Linux verdict (issue #1397). usage: test-package-win.sh [CASE]
# parity: a CRLF copy of the tree, an ASCII locale and a script whose --help prints non-ASCII give the same FAIL lines as LF.
# no-stdin: a script whose --help waits on stdin doesn't hold the run while stdin stays open.
set -u
here=$(cd "$(dirname "$0")/../.." && pwd)
cases="parity no-stdin"
if [ $# = 0 ]; then
  fails=0
  for c in $cases; do
    out=$(bash "$0" "$c" 2>&1) && echo "PASS: $c" || { echo "FAIL: $c: $out"; fails=$((fails + 1)); }
  done
  [ "$fails" = 0 ] && echo "ALL PASS" || { echo "$fails FAILED"; exit 1; }
  exit
fi
case=$1
no() { echo "$case: $1"; exit 1; }
d=$(mktemp -d); trap 'rm -rf "$d"' EXIT
export HOME="$d/home"  # no private flow file: only the built-in scans run
copy() { mkdir -p "$1"; (cd "$here" && cp -R skills listing.json README.md LICENSE VERSION CHANGELOG.md "$1/"); }
verdict() { # tree: its sorted FAIL lines, run under an ASCII locale (no UTF-8 mode, no locale coercion)
  PYTHONUTF8=0 PYTHONCOERCECLOCALE=0 LC_ALL=C LANG=C python3 "$here/dev/package.py" --root "$1" --out "$1.zip" 2>&1 | grep -E "^FAIL|Error" | sort; }
case $case in
parity)
  copy "$d/lf"
  printf 'import sys\nsys.stdout.buffer.write("caf\\u00e9 \\u4e2d\\n".encode("utf-8"))\n' > "$d/lf/skills/workflow-setup/scripts/accent.py"
  cp -R "$d/lf" "$d/crlf"
  python3 - "$d/crlf" <<'EOF' || no "could not write the CRLF copy"
import os, sys
for here, _, names in os.walk(sys.argv[1]):
    for name in names:
        path = os.path.join(here, name)
        data = open(path, "rb").read()
        if b"\0" not in data:
            open(path, "wb").write(data.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n"))
EOF
  lf=$(verdict "$d/lf"); crlf=$(verdict "$d/crlf")
  echo "$lf$crlf" | grep -q "Error" && no "package.py raised: $(echo "$lf$crlf" | grep Error | head -2)"
  [ "$lf" = "$crlf" ] || no "CRLF verdict differs: $(diff <(echo "$lf") <(echo "$crlf") | head -6)"
  ;;
no-stdin)
  copy "$d/t"
  printf 'import sys\nsys.stdin.read()\n' > "$d/t/skills/workflow-setup/scripts/waits.py"
  # stdin is a pipe nobody closes for 150 s; a check that inherits it waits that long
  out=$( { sleep 150 & echo $! > "$d/sleeper"; wait; } | {
    start=$(date +%s); timeout 140 python3 "$here/dev/package.py" --root "$d/t" --out "$d/t.zip" 2>&1
    echo "TOOK $(( $(date +%s) - start ))"; kill "$(cat "$d/sleeper")" 2>/dev/null; })
  took=$(echo "$out" | sed -n 's/^TOOK //p')
  [ "${took:-999}" -lt 120 ] || no "took ${took:-?}s with stdin open"
  if echo "$out" | grep -q "FAIL Scripts: skills/workflow-setup/scripts/waits.py"; then no "a script that reads stdin failed: $(echo "$out" | grep waits.py)"; fi
  ;;
*) no "unknown case" ;;
esac
