#!/bin/bash
# reads: dev/toy/plan-fixture.py dev/toy/plan-golden.txt skills/workflow-regression/scripts/ skills/workflow-regression/references/commands.md
# reads: dev/package.py dev/toy/reap.sh
# Proves the lane planner's cost and its row set (issue 710): `golden` the planned rows equal the v0.27.6 planner's on fixture
# repos; `calls` planning git calls and os.walk calls stay flat as rows grow. More modes arrive with the cache (identity,
# key, sizes, seconds). All fixtures are synthetic (dev/toy/plan-fixture.py) and no model is called.
# usage: test-plan-cache.sh golden|calls|identity|key|sizes|seconds|all
set -u
here=$(cd "$(dirname "$0")/../.." && pwd)
. "$here/dev/toy/reap.sh"
mode=${1:-all}
S="$here/skills/workflow-regression/scripts"
F="$here/dev/toy/plan-fixture.py"
G="$here/dev/toy/plan-golden.txt"
unset GITHUB_SERVER_URL GITHUB_REPOSITORY GITHUB_RUN_ID LOOP_SESSION_TOOL LOOP_OPERATION_SESSION GH_TOKEN GITHUB_TOKEN
unset LANES_WIDE LANES_NO_CACHE _LOOP_LANE_LABEL _LOOP_LANE_HELD
export HOME=$(mktemp -d) PYTHONDONTWRITEBYTECODE=1 GIT_AUTHOR_NAME=T GIT_AUTHOR_EMAIL=t@example.com GIT_COMMITTER_NAME=T GIT_COMMITTER_EMAIL=t@example.com
d=$(mktemp -d)
toy_on_exit 'rm -rf "$d" "$HOME"'
REALGIT=$(command -v git)
fails=0
ok() { echo "PASS: $1"; }
bad() { echo "FAIL: $1"; fails=$((fails + 1)); }
# fail NAME EXPECTED ACTUAL: the one failure format, with the line that reruns it
fail() { bad "$1"; echo "    expected: $2"; echo "    actual:   $3"; echo "    rerun: bash dev/toy/test-plan-cache.sh ${cur:-$mode}"; }
nocache() { grep -v '^PLAN_CACHE:'; }

m_golden() { cur=golden
  echo "== golden: the planned rows equal the v0.27.6 planner's"
  # Value: protects=a lane's planned row set is the one the v0.27.6 planner chose (done line 2); fails_when=a planner change adds, drops or re-words a selected row on any fixture case; why_new=nothing compared plans across planner versions; seam=none; no_claim=the repo's own rows (they move with HEAD)
  mkdir -p "$d/g"
  local got
  got=$(LANES_NO_CACHE=1 python3 -B "$F" golden "$S" "$d/g" | nocache)
  if [ "$got" = "$(cat "$G")" ]; then ok "every fixture case plans exactly as the committed golden"; else
    fail "golden plans" "plan-golden.txt" "$(diff <(echo "$got") "$G" | head -20)"; fi
  # Value: protects=the committed golden holds no machine path; fails_when=a temp or home path is in plan-golden.txt; why_new=goldens are committed text; seam=none; no_claim=none
  if grep -Eq '/(Users|home|private|var|tmp)/' "$G"; then fail "golden has no machine path" "none" "$(grep -E '/(Users|home|private|var|tmp)/' "$G" | head -3)"; else ok "plan-golden.txt names no machine path"; fi
  # Value: protects=the golden really came from the v0.27.6 planner, never regenerated from new code; fails_when=a fresh run of the v0.27.6 scripts differs from plan-golden.txt; why_new=the identity proof compares new code with old code, not new with new; seam=git history; no_claim=none
  if git -C "$here" cat-file -e '6b0f23c^{commit}' 2>/dev/null; then
    mkdir -p "$d/old" "$d/og"
    git -C "$here" archive 6b0f23c skills/workflow-regression/scripts | tar -x -C "$d/old"
    local was
    was=$(python3 -B "$F" golden "$d/old/skills/workflow-regression/scripts" "$d/og")
    if [ "$was" = "$(cat "$G")" ]; then ok "plan-golden.txt equals a fresh run of the v0.27.6 scripts"; else
      fail "golden is v0.27.6 output" "equal" "$(diff <(echo "$was") "$G" | head -20)"; fi
  else
    echo "SKIP: golden-vs-v0.27.6 proof (6b0f23c absent; run git fetch --unshallow)"
    [ "${STRICT:-}" != 1 ] || bad "golden-vs-v0.27.6 proof skipped under STRICT=1"
  fi
}

# plan_counts ROWS: git calls and os.walk calls of one cold plan (no cache, no record), after the fixture is built
plan_counts() {
  local repo="$d/n$1" log="$d/git$1.log"
  python3 -B "$F" gen "$repo" --rows "$1" --skills 4 --modules 5 --docs 5 --app 6
  mkdir -p "$d/shim"
  printf '#!/bin/sh\necho "$1" >> "$GITLOG"\nexec "%s" "$@"\n' "$REALGIT" > "$d/shim/git"; chmod +x "$d/shim/git"
  : > "$log"
  GITLOG="$log" PATH="$d/shim:$PATH" LANES_NO_CACHE=1 python3 -B "$F" walks "$S" "$repo" > /dev/null 2> "$d/walk$1.txt"
  CALLS=$(wc -l < "$log" | tr -d ' ')
  WALKS=$(awk '/^WALKS/ {print $2}' "$d/walk$1.txt")
  TALLY=$(sort "$log" | uniq -c | sort -rn | awk '{printf "%s=%s ", $2, $1}')
}

m_calls() { cur=calls
  echo "== calls: planning cost stays flat as rows grow"
  plan_counts 20; local c20=$CALLS w20=$WALKS t20=$TALLY
  plan_counts 120; local c120=$CALLS w120=$WALKS t120=$TALLY
  echo "    20 rows: $c20 git calls, $w20 os.walk calls ($t20)"
  echo "    120 rows: $c120 git calls, $w120 os.walk calls ($t120)"
  # Value: protects=planning time does not grow with the number of rows (issue 710: one git diff and git status per row); fails_when=git calls at 120 rows exceed those at 20 by more than 2, or 20 rows take more than 30 calls; why_new=the per-row eager setdefault in tiers.changed was never measured; seam=PATH shim logging every git call; no_claim=wall seconds (they move with load; the nightly seconds row measures them)
  if [ $((c120 - c20)) -le 2 ] && [ "$c20" -le 30 ]; then ok "git calls: $c20 at 20 rows, $c120 at 120 rows"; else
    fail "git calls flat in rows" "calls(120)-calls(20) <= 2 and calls(20) <= 30" "calls(20)=$c20 calls(120)=$c120"; fi
  # Value: protects=a folder shared by many rows is listed once per plan (issue 710 part 2); fails_when=os.walk calls at 120 rows exceed those at 20 by more than 2; why_new=lanes.walk was called per row; seam=os.walk wrapped in the plan driver; no_claim=the number of walks at 20 rows
  if [ $((w120 - w20)) -le 2 ]; then ok "os.walk calls: $w20 at 20 rows, $w120 at 120 rows"; else
    fail "os.walk calls flat in rows" "walks(120)-walks(20) <= 2" "walks(20)=$w20 walks(120)=$w120"; fi
}

# case_golden NAME: that case's block of plan-golden.txt, without its "== NAME" line
case_golden() { awk -v n="== $1" '$0 == n {on = 1; next} /^== / {on = 0} on' "$G"; }
CASES="narrow wide mixed root unmapped deleted merged record norecord nobase detached"

# plan_case NAME [ENV...]: one plan of a case repo, the PLAN_CACHE lines and all
plan_case() { local name=$1; shift; env "$@" python3 -B "$F" plan "$S" "$CD/$name" 2>&1; }

m_identity() {
  m_golden
  cur=identity
  echo "== identity: cold, warm and off plans equal the golden"
  CD="$d/g"  # the cases golden built (planned with the cache off, so none has a cache file yet)
  local name want off cold warm cold_all warm_all
  for name in $CASES; do
    want=$(case_golden "$name")
    off=$(plan_case "$name" LANES_NO_CACHE=1 | nocache)
    cold_all=$(plan_case "$name" X=1); cold=$(nocache <<<"$cold_all")
    warm_all=$(plan_case "$name" X=1); warm=$(nocache <<<"$warm_all")
    # Value: protects=the planned row set never depends on the cache state (done line 2); fails_when=a cold, warm or uncached plan of a fixture case differs from the v0.27.6 golden; why_new=a stale or wrong closure would skip a row and pass a lane falsely; seam=none; no_claim=real repos (the repo's own rows move with HEAD)
    if [ "$off" = "$want" ] && [ "$cold" = "$want" ] && [ "$warm" = "$want" ]; then ok "case $name: golden = off = cold = warm"; else
      local which=off got=$off
      [ "$cold" = "$want" ] || { which=cold; got=$cold; }
      [ "$warm" = "$want" ] || { which=warm; got=$warm; }
      fail "case $name ($which)" "golden" "$(diff <(echo "$got") <(echo "$want") | head -20)"; fi
    # Value: protects=each case reaches the cache state it should and says so on the first line; fails_when=a cold plan is not a miss (absent) or a warm one is not a hit (a detached HEAD has no cache: none, a plan with no merge-base keeps nothing to reuse: partial); why_new=the PLAN_CACHE line is the owner's only view of the cache; seam=none; no_claim=the wording of other lines
    local c1 c2; c1=$(head -1 <<<"$cold_all"); c2=$(head -1 <<<"$warm_all")
    case "$name" in
      detached) [ "$c1" = "PLAN_CACHE: none (no branch)" ] && [ "$c2" = "$c1" ] ;;
      nobase) [ "$c1" = "PLAN_CACHE: miss (absent)" ] && [[ "$c2" == "PLAN_CACHE: miss (partial 0 of "* ]] ;;
      *) [ "$c1" = "PLAN_CACHE: miss (absent)" ] && [[ "$c2" == "PLAN_CACHE: hit ("* ]] ;;
    esac
    if [ $? = 0 ]; then ok "case $name: states '$c1' then '$c2'"; else fail "case $name states" "cold miss (absent), then hit" "'$c1' then '$c2'"; fi
  done
  # Value: protects=LANES_NO_CACHE turns the cache off for 1, true and yes in any case and for nothing else; fails_when=a value of 0 or empty turns it off, or one of 1, true, yes does not; why_new=the owner's escape hatch is an env switch; seam=none; no_claim=LANES_WIDE (it keeps its literal 1)
  local v line
  for v in 1 true yes TRUE Yes; do
    line=$(plan_case narrow LANES_NO_CACHE=$v | head -1)
    [ "$line" = "PLAN_CACHE: off (LANES_NO_CACHE=1)" ] && ok "LANES_NO_CACHE=$v is off" || fail "LANES_NO_CACHE=$v" "off (LANES_NO_CACHE=1)" "$line"
  done
  for v in 0 ""; do
    line=$(plan_case narrow LANES_NO_CACHE=$v | head -1)
    case "$line" in "PLAN_CACHE: off"*) fail "LANES_NO_CACHE='$v'" "not off" "$line" ;; *) ok "LANES_NO_CACHE='$v' is not off" ;; esac
  done
}

# ---- key mode: one small repo, copied per check
P() { local repo=$1; shift; env "${@:-X=1}" python3 -B "$F" plan "$S" "$repo" 2>&1; }
newrepo() { rm -rf "$d/k/$1"; mkdir -p "$d/k"; cp -R "$d/kbase" "$d/k/$1"; echo "$d/k/$1"; }
planfile() { ls "$1"/.git/loop/plans/*.json 2>/dev/null | head -1; }
keyof() { python3 -B -c 'import sys; sys.path.insert(0, sys.argv[1]); import tiers; print(tiers.key(sys.argv[2])[0])' "$1" "$2"; }
# same NAME REPO TOKEN-GLOB [ENV...]: a plan in that cache state starts with a PLAN_CACHE line matching the glob and
# the rest equals the uncached plan of the same repo
same() {
  local name=$1 repo=$2 want=$3; shift 3
  local off got tok
  off=$(P "$repo" LANES_NO_CACHE=1 "$@" | nocache)
  got=$(P "$repo" "$@")
  tok=$(head -1 <<<"$got")
  # shellcheck disable=SC2053
  if [[ "$tok" == $want ]] && [ "$(nocache <<<"$got")" = "$off" ]; then ok "$name: $tok"; else
    fail "$name" "first line '$want' and the uncached plan" "'$tok'; $(diff <(nocache <<<"$got") <(echo "$off") | head -20)"; fi
}

m_key() {
  cur=key
  echo "== key: HEAD or the row file changes the key; a bad file or a dirty tree never changes the plan"
  python3 -B "$F" gen "$d/kbase" --rows 12 --skills 3 --modules 3 --docs 3 --app 4
  cat > "$d/mut.py" <<'EOF'
import json, sys, zlib
f, kind = sys.argv[1:3]
raw = open(f, "rb").read()
if kind == "truncated": out = raw[:20]
elif kind == "empty": out = b""
elif kind == "garbled":
    b = bytearray(raw); mid = len(b) // 2
    b[mid:mid + 8] = bytes(x ^ 255 for x in b[mid:mid + 8]); out = bytes(b)
elif kind == "nonzlib": out = b'{"v": 1}'
elif kind == "bomb": out = zlib.compress(b"0" * (100 << 20), 1)
elif kind == "deep": out = zlib.compress(b"[" * 200000)
else:
    d = json.loads(zlib.decompress(raw))
    first = sorted(d["rows"])[0]
    if kind == "version": d["v"] = 2
    elif kind == "flipkey": d["key"] = "0" * 64
    elif kind == "shape": d["rows"] = []
    elif kind == "index": d["rows"][first][0] = [len(d["paths"]) + 5]
    elif kind == "nonstring": d["paths"][0] = 5
    elif kind == "absolute": d["paths"][0] = "/etc/passwd"
    elif kind == "dotdot": d["paths"][0] = "a/../b"
    elif kind == "half": d["rows"] = {c: d["rows"][c] for c in sorted(d["rows"])[::2]}
    out = zlib.compress(json.dumps(d, sort_keys=True).encode())
open(f, "wb").write(out)
EOF
  local r f kind out

  # Value: protects=a moved HEAD gives a fresh plan, never the old closures (done line 3); fails_when=a plan after HEAD moved reads the cache written at the old HEAD, or the first differing key part is not named; why_new=a stale closure would skip a row that now reaches a changed file; seam=none; no_claim=a move that changes nothing a row reads
  r=$(newrepo head)
  P "$r" > /dev/null
  sed -i.bak '2s|$| app/b.txt|' "$r/dev/toy/t0.sh"; rm "$r/dev/toy/t0.sh.bak"
  git -C "$r" -c core.hooksPath=/dev/null commit -qam "t0 now reads app/b.txt" 2>&1 | head -2
  printf 'b2\n' > "$r/app/b.txt"; git -C "$r" -c core.hooksPath=/dev/null commit -qam "app/b.txt changes" 2>&1 | head -2
  same "HEAD moved" "$r" "PLAN_CACHE: miss (key-head)"
  P "$r" LANES_NO_CACHE=1 | grep -q '^SELECTED t0: reaches app/b.txt$' && ok "t0 is selected because it now reaches app/b.txt" || bad "t0 reaches app/b.txt after the HEAD move"

  # Value: protects=every part of the key changes it: HEAD, the row file, the planner code, LANES_WIDE, the loop files (done line 3); fails_when=one of them leaves the key equal; why_new=a part missing from the key is a stale hit; seam=a copy of the scripts folder; no_claim=ignored files (not in the key, a documented limit)
  r=$(newrepo parts)
  local k0 k1 k2 k3 k4 k5
  k0=$(keyof "$S" "$r"); k1=$(keyof "$S" "$r")
  git -C "$r" -c core.hooksPath=/dev/null commit -q --allow-empty -m "head moves" 2>&1 | head -2; k2=$(keyof "$S" "$r")
  echo "# a comment" >> "$r/.loop/regression.tsv"; k3=$(keyof "$S" "$r")
  rm -rf "$d/sc"; cp -R "$S" "$d/sc"; echo "# one byte" >> "$d/sc/tiers.py"; k4=$(keyof "$d/sc" "$r")
  k5=$(LANES_WIDE=1 keyof "$S" "$r")
  if [ "$k0" = "$k1" ] && [ "$k0" != "$k2" ] && [ "$k2" != "$k3" ] && [ "$k3" != "$k4" ] && [ "$k0" != "$k4" ] && [ "$k0" != "$k5" ] && [ -n "$k0" ]; then
    ok "key: same twice; changes with HEAD, the row file, the planner code and LANES_WIDE"
  else fail "key parts" "all different" "same-twice=$([ "$k0" = "$k1" ] && echo y || echo n) head=$([ "$k0" != "$k2" ] && echo y || echo n) rows=$([ "$k2" != "$k3" ] && echo y || echo n) code=$([ "$k3" != "$k4" ] && echo y || echo n) wide=$([ "$k0" != "$k5" ] && echo y || echo n)"; fi
  local e; e="$d/empty"; mkdir -p "$e"; git -C "$e" init -q -b main
  [ -n "$(keyof "$S" "$e")" ] && ok "key of a repo with no commit is still a digest" || bad "key of an empty repo"

  # Value: protects=a damaged cache file is ignored, never trusted and never an error (fail open); fails_when=a bad file changes a plan or the token is not miss (corrupt); why_new=a half-written or edited file must not mis-plan a lane; seam=dev/toy mutation of a real cache file; no_claim=a file a valid writer made for another key
  r=$(newrepo bad)
  P "$r" > /dev/null; f=$(planfile "$r"); cp "$f" "$d/valid.bin"
  rm "$f"; same "file absent" "$r" "PLAN_CACHE: miss (absent)"
  for kind in truncated empty garbled nonzlib bomb deep version flipkey shape index nonstring absolute dotdot; do
    cp "$d/valid.bin" "$f"; python3 -B "$d/mut.py" "$f" $kind
    same "bad file ($kind)" "$r" "PLAN_CACHE: miss (corrupt)"
  done
  cp "$d/valid.bin" "$f"; python3 -B "$d/mut.py" "$f" half
  same "half the rows" "$r" "PLAN_CACHE: miss (partial 6 of 12)"
  same "the file those plans wrote loads" "$r" "PLAN_CACHE: hit (12 rows)"

  # Value: protects=a decompression bomb is cut off at 64 MB and read as corrupt, never inflated whole (review F5); fails_when=loading a 200 MB zlib stream allocates more than 120 MB or does not answer miss (corrupt); why_new=a damaged file must not exhaust memory; seam=tracemalloc around narrow.warm; no_claim=the speed of the inflate
  cat > "$d/bomb.py" <<'EOF'
import sys, tracemalloc, zlib
sys.path.insert(0, sys.argv[1])
import narrow
path = sys.argv[2]
open(path, "wb").write(zlib.compress(b"0" * (200 << 20), 1))
tracemalloc.start()
state = narrow.warm(path, ("k", ["1"] * 6), [], {})
print(state, "small" if tracemalloc.get_traced_memory()[1] < (120 << 20) else "BIG")
EOF
  local res; res=$(python3 -B "$d/bomb.py" "$S" "$d/bomb.bin")
  [ "$res" = "miss (corrupt) small" ] && ok "a 200 MB bomb is miss (corrupt) within the memory cap" || fail "bomb" "miss (corrupt) small" "$res"

  # Value: protects=what the cache saves is what the cache loads (done line 2); fails_when=closure, why and table values change on a store and a warm; why_new=the null table case has a different default in lanes.reads_table; seam=python call of narrow.store and narrow.warm; no_claim=the file's bytes
  cat > "$d/rt.py" <<'EOF'
import os, sys
sys.path.insert(0, sys.argv[1]); os.chdir(sys.argv[2])
import lanes, narrow, regression, tiers
from runs import chosen
root = sys.argv[2]
rows = chosen(regression.read_rows(root), "land")
cache = {}
for row in rows:
    lanes.closure(root, row["command"], cache)
key, path = tiers.key(root), os.path.join(sys.argv[3], "x.json")
assert narrow.store(path, key, cache) is None
fresh = {}
state = narrow.warm(path, key, rows, fresh)
want = {k: v for k, v in cache.items() if isinstance(k, tuple) and k[0] in ("closure", "why", "table")}
print("equal" if want == fresh and state.startswith("hit") else "differ: %s" % state)
EOF
  r=$(newrepo trip)
  local res; res=$(python3 -B "$d/rt.py" "$S" "$r" "$d")
  [ "$res" = equal ] && ok "warm(store(cache)) gives the cache back" || fail "round trip" "equal" "$res"

  # Value: protects=a tree with changes the key cannot see never reads or writes the cache; fails_when=a stray untracked file leaves the plan with a hit or a miss, or a file is written; why_new=closures read working-tree files; seam=none; no_claim=bookkeeping files (they are exempt on purpose)
  r=$(newrepo stray)
  P "$r" > /dev/null; rm "$(planfile "$r")"
  echo stray > "$r/stray.txt"
  same "stray untracked file" "$r" "PLAN_CACHE: dirty (1 paths, cache not used)"
  [ -z "$(planfile "$r")" ] && ok "a dirty plan wrote no cache file" || bad "a dirty plan wrote a cache file"

  # Value: protects=an uncommitted edit to a loop bookkeeping file (git status leaves them out) never lets a stale closure be served, while the row stays cached; fails_when=a row reading .loop/goals/ is dropped from the file, an edit there still hits, or the edited plan differs from the uncached one; why_new=every row of a large repo can reach .loop/goals/, so skipping those rows would leave the cache empty; seam=none; no_claim=rows that read other .loop files
  r=$(newrepo book)
  mkdir -p "$r/.loop/goals"; echo goal > "$r/.loop/goals/g.md"
  printf '#!/bin/bash\n# reads: .loop/goals/g.md\ncat .loop/goals/g.md\n' > "$r/dev/toy/bk.sh"
  printf 'bk\tland\tbash dev/toy/bk.sh\tX-1\t2026-01-01\tBk.\tcriterion\t\n' >> "$r/.loop/regression.tsv"
  git -C "$r" add -A; git -C "$r" -c core.hooksPath=/dev/null commit -qm "bookkeeping row" 2>&1 | head -2
  P "$r" > /dev/null; f=$(planfile "$r")
  local held; held=$(python3 -B -c 'import json,sys,zlib; print("bash dev/toy/bk.sh" in json.loads(zlib.decompress(open(sys.argv[1],"rb").read()))["rows"])' "$f")
  [ "$held" = True ] && ok "a row reaching .loop/goals/ is cached" || fail "bookkeeping row cached" "True" "$held"
  same "no edit under .loop/goals/" "$r" "PLAN_CACHE: hit (13 rows)"
  echo "edited" >> "$r/.loop/goals/g.md"
  same "uncommitted edit under .loop/goals/" "$r" "PLAN_CACHE: miss (key-loop)"
  same "the same edit, planned again" "$r" "PLAN_CACHE: hit (13 rows)"
  local kl1 kl2
  kl1=$(keyof "$S" "$r"); echo "more" >> "$r/.loop/goals/g.md"; kl2=$(keyof "$S" "$r")
  [ "$kl1" != "$kl2" ] && ok "the key follows the content of an edited bookkeeping file" || fail "key follows bookkeeping content" "different keys" "equal"

  # Value: protects=a key that changes between the read and the write stops the write; fails_when=a cache is written under a key that no longer matches the tree; why_new=the tree can move while a plan runs; seam=PLAN_KEY_FLIP hook in the plan driver; no_claim=a move after the write
  r=$(newrepo flip)
  P "$r" PLAN_KEY_FLIP=1 > /dev/null
  if [ -z "$(planfile "$r")" ] && ! ls "$r"/.git/loop/plans/*.tmp > /dev/null 2>&1; then ok "a key that changed during the plan writes nothing"; else bad "a changed key still wrote a file"; fi

  # Value: protects=a closure that read a git-ignored file is never saved, because neither HEAD nor git status sees that file change (review F1); fails_when=a plan after an ignored file a row names changed gets a hit with the old closure, or the first plan saves a file; why_new=ignored files are the one input the key cannot hold; seam=a row naming .local/x.sh with .local/ ignored; no_claim=an ignored file that does not exist yet
  r=$(newrepo ign)
  git -C "$r" switch -q main  # the row and the ignore rule are on main, so the row is not new on the feature branch
  mkdir -p "$r/.local"; echo '.local/' > "$r/.gitignore"; printf '#!/bin/bash\nls skills/s1/ > /dev/null\n' > "$r/.local/x.sh"
  printf 'loc\tland\tbash .local/x.sh\tX-1\t2026-01-01\tLocal.\tcriterion\t\n' >> "$r/.loop/regression.tsv"
  git -C "$r" add -A; git -C "$r" -c core.hooksPath=/dev/null commit -qm "ignored dir and a row naming it" 2>&1 | head -2
  git -C "$r" switch -q feat/plan; git -C "$r" merge -q --no-edit main 2>&1 | head -2
  echo "more" >> "$r/skills/s2/SKILL.md"
  git -C "$r" commit -qam "s2 changes" 2>&1 | head -2
  out=$(P "$r")
  if [ "$(head -1 <<<"$out")" = "PLAN_CACHE: miss (absent)" ] && grep -qx "PLAN_CACHE: not saved (ignored file read)" <<<"$out" && [ -z "$(planfile "$r")" ]; then ok "an ignored file in a closure: not saved (ignored file read)"; else fail "ignored file read" "miss (absent) ... not saved (ignored file read), no file" "$(head -1 <<<"$out") / $(grep PLAN_CACHE <<<"$out" | tail -1) / file=$(planfile "$r")"; fi
  printf '#!/bin/bash\nls skills/s2/ > /dev/null\n' > "$r/.local/x.sh"
  same "ignored file changed between plans" "$r" "PLAN_CACHE: miss (absent)"
  P "$r" LANES_NO_CACHE=1 | grep -q '^SELECTED loc: reaches skills/s2/SKILL.md$' && ok "row loc is selected because the ignored script now reaches skills/s2/" || bad "row loc selected after the ignored file changed"

  # Value: protects=a non-ASCII bookkeeping file counts in the key like any other (review F2: git status quotes such paths); fails_when=editing .loop/goals/<non-ASCII name>.md leaves the key equal; why_new=a quoted path could not be opened and was skipped; seam=none; no_claim=other encodings
  r=$(newrepo uni)
  mkdir -p "$r/.loop/goals"; echo one > "$r/.loop/goals/caf$(printf '\303\251').md"
  local ku1 ku2; ku1=$(keyof "$S" "$r"); echo two > "$r/.loop/goals/caf$(printf '\303\251').md"; ku2=$(keyof "$S" "$r")
  [ "$ku1" != "$ku2" ] && ok "editing a non-ASCII bookkeeping file changes the key" || fail "non-ASCII bookkeeping key" "different keys" "equal"

  # Value: protects=a git status that fails never reads as a clean tree (review F3); fails_when=a plan whose git status fails gets hit or miss, or writes a file; why_new=an empty answer and a failed one looked alike; seam=a git shim that fails status; no_claim=other failing git calls
  r=$(newrepo nostat)
  P "$r" > /dev/null; rm "$(planfile "$r")"
  mkdir -p "$d/sh2"; printf '#!/bin/sh\n[ "$1" = status ] && exit 1\n[ "$1" = -c ] && [ "$3" = status ] && exit 1\nexec "%s" "$@"\n' "$REALGIT" > "$d/sh2/git"; chmod +x "$d/sh2/git"
  same "git status fails" "$r" "PLAN_CACHE: dirty (git status failed, cache not used)" PATH="$d/sh2:$PATH"
  [ -z "$(planfile "$r")" ] && ok "a failed git status wrote no cache file" || bad "a failed git status wrote a file"

  # Value: protects=an edit made while the plan runs is never cached (review F4); fails_when=a file that appears during the plan still gets a cache file; why_new=the key was rechecked but the tree was not; seam=PLAN_STRAY hook in the plan driver; no_claim=an edit made during the write
  r=$(newrepo during)
  P "$r" PLAN_STRAY=1 > /dev/null
  [ -z "$(planfile "$r")" ] && ok "a file that appeared during the plan was not cached" || bad "a plan with an edit during it wrote a file"

  # Value: protects=rows planned for one level survive a plan of another level (land, then nightly, then land); fails_when=the nightly plan drops the land closures or the next land plan misses; why_new=one file per branch serves every target; seam=PLAN_TARGET in the plan driver; no_claim=the order of nightly rows
  r=$(newrepo levels)
  printf '#!/bin/bash\n# reads: skills/s1/scripts/m0.py\npython3 skills/s1/scripts/m0.py\n' > "$r/dev/toy/n1.sh"
  printf 'n1\tnightly\tbash dev/toy/n1.sh\tX-1\t2026-01-01\tNightly.\tcriterion\t\n' >> "$r/.loop/regression.tsv"
  git -C "$r" add -A; git -C "$r" -c core.hooksPath=/dev/null commit -qm "nightly row" 2>&1 | head -2
  P "$r" > /dev/null
  same "nightly after land" "$r" "PLAN_CACHE: miss (partial 12 of 13)" PLAN_TARGET=nightly
  same "land after nightly" "$r" "PLAN_CACHE: hit (12 rows)"

  # Value: protects=four lanes planning at once leave one loadable cache file and no temp file; fails_when=the folder holds a partial file, a leftover .tmp or none; why_new=lanes of one branch can plan together; seam=background plans; no_claim=which writer wins
  r=$(newrepo race)
  local n; for n in 1 2 3 4; do P "$r" > "$d/race$n.txt" & done; wait
  local files tmps; files=$(ls "$r"/.git/loop/plans/*.json 2>/dev/null | wc -l | tr -d ' '); tmps=$(ls "$r"/.git/loop/plans/*.tmp 2>/dev/null | wc -l | tr -d ' ')
  if [ "$files" = 1 ] && [ "$tmps" = 0 ]; then ok "four parallel plans leave one file and no temp file"; else fail "parallel plans" "1 json, 0 tmp" "$files json, $tmps tmp"; fi
  same "the file four writers left loads" "$r" "PLAN_CACHE: hit (12 rows)"

  # Value: protects=a cache that cannot be written never fails or changes a lane; fails_when=an unwritable plans folder changes the plan, hides the not-saved line or the exit status; why_new=a read-only store must stay harmless; seam=a regular file where the folder should be; no_claim=the message wording of the OS error
  mkdir -p "$d/c2"; python3 -B "$F" cases "$d/c2" --scripts "$S"
  r="$d/c2/narrow"; mkdir -p "$r/.git/loop"; : > "$r/.git/loop/plans"
  out=$(P "$r")
  if [ "$(nocache <<<"$out")" = "$(case_golden narrow)" ] && grep -q '^PLAN_CACHE: not saved (FileExistsError)$' <<<"$out"; then ok "unwritable plans: the plan equals the golden and says 'not saved (FileExistsError)'"; else
    fail "unwritable plans" "golden plus the not-saved line" "$(diff <(nocache <<<"$out") <(case_golden narrow) | head -10)"; fi

  # Value: protects=a real lane on a clean tree leaves it clean, so the next lane at the same HEAD hits (done lines 1 and 3 in use); fails_when=the first run leaves paths in git status or the second is not a hit; why_new=lanes.dirty must stay empty after a lane for the cache to be reachable; seam=two real regression.py runs with LOOP_LANES_DIR; no_claim=a real large repo
  r=$(newrepo real)
  local reg="python3 -B $S/regression.py run land --reuse --tier goal"
  (cd "$r" && LOOP_LANES_DIR="$d/lanes" LOOP_ROLE=worker $reg > "$d/real1.txt" 2>&1)
  local left; left=$(git -C "$r" status --porcelain)
  (cd "$r" && LOOP_LANES_DIR="$d/lanes" LOOP_ROLE=worker $reg > "$d/real2.txt" 2>&1)
  if [ -z "$left" ] && head -1 "$d/real1.txt" | grep -q '^PLAN_CACHE: miss' && head -1 "$d/real2.txt" | grep -q '^PLAN_CACHE: hit ('; then ok "two real lane runs: clean tree after the first, hit on the second"; else
    fail "two real lanes" "clean, then hit" "status='$left' first='$(head -1 "$d/real1.txt")' second='$(head -1 "$d/real2.txt")'"; fi
}

m_seconds() {
  cur=seconds
  local rows=${PLAN_ROWS:-1500} limit=${PLAN_SECONDS_LIMIT:-60}
  echo "== seconds: $rows rows plan in under $limit s with 20 busy loops running (nightly)"
  local tmo; tmo=$(command -v timeout || command -v gtimeout)
  if [ -z "$tmo" ]; then
    echo "SKIP: seconds needs GNU timeout (or gtimeout); install coreutils"
    [ "${STRICT:-}" != 1 ] || bad "seconds skipped under STRICT=1"
    return
  fi
  python3 -B "$F" gen "$d/big" --rows "$rows" --skills 40 --modules 30 --docs 200 --app 3000
  local me=$$ n
  for n in $(seq 20); do (while kill -0 "$me" 2>/dev/null; do :; done) & done
  toy_on_exit 'kill $(jobs -p) 2>/dev/null'
  local t0 t1 off cold warm size
  t0=$(python3 -c 'import time; print(time.time())')
  LANES_NO_CACHE=1 "$tmo" $((limit * 4)) python3 -B "$F" plan "$S" "$d/big" > "$d/off.txt" 2>&1; local rc_off=$?
  t1=$(python3 -c 'import time; print(time.time())'); off=$(awk -v a="$t0" -v b="$t1" 'BEGIN {printf "%.1f", b - a}')
  t0=$t1
  "$tmo" $((limit + 10)) python3 -B "$F" plan "$S" "$d/big" > "$d/cold.txt" 2>&1; local rc_cold=$?
  t1=$(python3 -c 'import time; print(time.time())'); cold=$(awk -v a="$t0" -v b="$t1" 'BEGIN {printf "%.1f", b - a}')
  t0=$t1
  "$tmo" $((limit + 10)) python3 -B "$F" plan "$S" "$d/big" > "$d/warm.txt" 2>&1; local rc_warm=$?
  t1=$(python3 -c 'import time; print(time.time())'); warm=$(awk -v a="$t0" -v b="$t1" 'BEGIN {printf "%.1f", b - a}')
  size=$(wc -c < "$(ls "$d"/big/.git/loop/plans/*.json | head -1)" | tr -d ' ')
  echo "    $rows rows, load: 20 busy loops: off $off s, cold $cold s, warm $warm s, cold minus off $(awk -v a="$off" -v b="$cold" 'BEGIN {printf "%.1f", b - a}') s, cache file $size bytes"
  # Value: protects=a lane plans a large repo in well under a minute under load (done line 1); fails_when=the cold plan takes the limit or longer, the cache file is 2 MB or more, or the three plans differ; why_new=the v0.27.6 planner took 111 s on this fixture at load 13 to 29; seam=20 busy loops; no_claim=the real large repo (the by-hand step measures it)
  if [ "$rc_off" != 0 ] || [ "$rc_cold" != 0 ] || [ "$rc_warm" != 0 ]; then fail "plans ran to the end" "exit 0 (124 is a timeout)" "off=$rc_off cold=$rc_cold warm=$rc_warm"; return; fi
  if awk -v c="$cold" -v l="$limit" 'BEGIN {exit !(c < l)}'; then ok "cold plan of $rows rows in $cold s (limit $limit)"; else fail "cold plan seconds" "< $limit" "$cold"; fi
  [ "$size" -lt 2097152 ] && ok "cache file is $size bytes (under 2 MB)" || fail "cache size" "< 2097152" "$size"
  if [ "$(nocache < "$d/off.txt")" = "$(nocache < "$d/cold.txt")" ] && [ "$(nocache < "$d/off.txt")" = "$(nocache < "$d/warm.txt")" ]; then ok "off, cold and warm plans are equal"; else fail "big plans equal" "equal" "$(diff <(nocache < "$d/off.txt") <(nocache < "$d/cold.txt") | head -10)"; fi
}

m_sizes() {
  cur=sizes
  echo "== sizes: the files this goal edits stay inside their ceilings, the package stays at 99 files"
  local r="$here/skills/workflow-regression/scripts" size
  # Value: protects=the planner change stays inside the size budget (done line 5, read as: lanes.py does not grow past 19,559; tiers.py and narrow.py stay under 18,432); fails_when=lanes.py grows or tiers.py or narrow.py reaches the health warn line; why_new=the cache code lives in scripts near their ceilings; seam=none; no_claim=files this goal does not edit, and the literal done-line text (27 scripts already exceed 18 KB)
  size=$(wc -c < "$r/lanes.py" | tr -d ' ')
  if [ "$size" -le 19559 ]; then ok "lanes.py is $size bytes (ceiling 19559)"; else fail "lanes.py size" "<= 19559" "$size"; fi
  for f in tiers.py narrow.py; do
    size=$(wc -c < "$r/$f" | tr -d ' ')
    if [ "$size" -lt 18432 ]; then ok "$f is $size bytes (under 18432)"; else fail "$f size" "< 18432" "$size"; fi
  done
  # Value: protects=the shipped package passes its own scan with at most 99 files; fails_when=package.py fails or counts more than 99 files; why_new=the cache must fit in existing scripts; seam=dev/package.py with its ZIP in a temp folder; no_claim=the new files under dev/toy (not shipped)
  local out count
  mkdir -p "$d/pkgroot" && git -C "$here" archive HEAD | tar -x -C "$d/pkgroot"  # the committed files only: a stray __pycache__ in the worktree is not shipped
  out=$(python3 -B "$here/dev/package.py" --root "$d/pkgroot" --out "$d/pkg.zip" </dev/null 2>&1)
  count=$(sed -n 's/^PASS: \([0-9]*\) files.*/\1/p' <<<"$out")
  if [ -n "$count" ] && [ "$count" -le 99 ]; then ok "package.py passes with $count files"; else fail "package.py" "PASS with <= 99 files" "$(tail -3 <<<"$out")"; fi
  # Value: protects=the owner can look up every PLAN_CACHE state in commands.md; fails_when=a state token the planner prints is missing from its Plan cache section; why_new=tokens are the owner's only view of the cache; seam=none; no_claim=the table's wording
  local section missing="" token
  section=$(awk '/^## Plan cache/ {on = 1; next} /^## / {on = 0} on' "$here/skills/workflow-regression/references/commands.md")
  for token in "hit (N rows)" "miss (absent)" "miss (corrupt)" "miss (key-head)" "miss (key-rows)" "miss (key-runner)" "miss (key-wide)" "miss (key-loop)" \
    "miss (partial M of N)" "dirty (N paths, cache not used)" "dirty (git status failed" "not saved (ignored file read)" "off (LANES_NO_CACHE=1)" "none (no branch)" "not saved (<error class>)" \
    LANES_NO_CACHE "loop/plans"; do
    grep -qF "$token" <<<"$section" || missing="$missing [$token]"
  done
  if [ -z "$missing" ]; then ok "commands.md ## Plan cache names every state"; else fail "commands.md ## Plan cache" "every token" "missing:$missing"; fi
}

case "$mode" in
  golden) m_golden ;;
  calls) m_calls ;;
  identity) m_identity ;;
  key) m_key ;;
  sizes) m_sizes ;;
  seconds) m_seconds ;;
  all) m_calls; m_identity; m_key; m_sizes ;;
  *) echo "usage: test-plan-cache.sh golden|calls|identity|key|sizes|seconds|all"; exit 2 ;;
esac
if [ "$fails" = 0 ]; then echo "ALL PASS"; else echo "FAILED: $fails"; exit 1; fi
