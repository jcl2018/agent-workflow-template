#!/bin/bash
# reads: dev/toy/test-tree.sh
# Runs dev/toy/test-tree.sh once per tree state and replays its output and exit code to every later caller, so the
# rows that each check one of its lines (lanes-headers, lanes-repo-narrow, one-way-to-run, prd-repo-green and the
# narrow rows) cost one run of it between them, not one each. The tree state is HEAD plus the working tree's changes,
# untracked files included. A caller waits for the one holding the lock (its pid is in the lock) and takes over if
# that process died; it waits at most 13 minutes, inside a row's 15-minute limit. Results older than a day are
# removed. usage: tree-once.sh
set -u
here=$(cd "$(dirname "$0")/../.." && pwd)
dir="${TMPDIR:-/tmp}"
find "$dir" -maxdepth 1 -name 'toy-tree-once-*' -mtime +1 -exec rm -rf {} + 2>/dev/null
key=$( (cd "$here" && git rev-parse HEAD; git status --porcelain; git diff; git ls-files -o --exclude-standard -z | xargs -0 cat) 2>/dev/null | cksum | tr -d ' ')
base="$dir/toy-tree-once-$key"
i=0
while [ ! -s "$base.rc" ]; do
  if mkdir "$base.lock" 2>/dev/null; then
    echo $$ > "$base.lock/pid"
    bash -c "${TREE_ONCE_CMD:-bash \"$here/dev/toy/test-tree.sh\"}" > "$base.out" 2>&1  # TREE_ONCE_CMD: a test's stand-in
    echo $? > "$base.rc"
    break
  fi
  holder=$(cat "$base.lock/pid" 2>/dev/null)
  if [ -n "$holder" ] && ! kill -0 "$holder" 2>/dev/null && [ ! -s "$base.rc" ]; then
    rm -rf "$base.lock"; continue  # the holder died (killed at its row's limit): take over
  fi
  [ "$i" -lt 7800 ] || { echo "FAIL: tree-once: test-tree.sh did not finish in 13 minutes (lock held by pid ${holder:-?})"; exit 1; }
  sleep 0.1; i=$((i + 1))
done
cat "$base.out"
exit "$(cat "$base.rc")"
