#!/bin/bash
# reads: skills/workflow-regression/scripts/ skills/workflow-delivery/scripts/
# reads: skills/workflow-delivery/scripts/lane.py skills/workflow-delivery/scripts/lanekit.py
# reads: skills/workflow-delivery/scripts/role.py skills/workflow-delivery/scripts/goal.py
# reads: skills/workflow-docs/scripts/criteria.py skills/workflow-docs/scripts/docs.py skills/workflow-setup/scripts/setup.py
# Proves lane-tmpdir (issue 814, REG-8): a lane's TMPDIR is a fresh folder under the system temp, keyed by repo, goal and
# lane, never inside a git checkout; a test that refuses to write inside a checkout passes under the lane; the folder is
# gone when the lane ends; a system temp inside a checkout refuses with LANE_TMPDIR before a job exists. A toy repo whose
# land row is an invented fixture; the real lane, regression.py and slots run. No model is called.
# usage: test-lane-tmpdir.sh [DIR]
set -u
unset LOOP_BATCH LOOP_SESSION_TOOL LOOP_OPERATION_SESSION GH_TOKEN GITHUB_TOKEN _LOOP_LANE_HELD LOOP_LANE_LIMIT
export LOOP_ROLE=worker
here=$(cd "$(dirname "$0")/../.." && pwd)
. "$here/dev/toy/reap.sh"
T=${1:-$(mktemp -d)}; rm -rf "${T:?}"; mkdir -p "$T"
export HOME="$T/home"; mkdir -p "$HOME"
"$here/dev/toy/make.sh" "$T" >/dev/null
export LOOP_FLOW="$T/flow.json"; echo '{"limit": 60}' > "$LOOP_FLOW"
export LOOP_LANES_DIR="$T/lanes" PATH="$here/dev/toy/fakegh:$PATH" FAKE_GH_DIR="$T/gh" REC="$T/rec.txt"
S="$here/skills/workflow-delivery/scripts"; R="$here/skills/workflow-regression/scripts"
reg="python3 $R/regression.py"
cd "$T/repo" || exit 1
python3 "$here/skills/workflow-setup/scripts/setup.py" --bare >/dev/null
git switch -q main; git merge -q --no-edit workflow-setup
RUNS="$(git rev-parse --git-common-dir)/loop/runs"; mkdir -p "$RUNS"; RUNS=$(cd "$RUNS" && pwd)
fails=0
ok() { echo "PASS: $1"; }
bad() { echo "FAIL: $1"; fails=$((fails + 1)); }
check() { if eval "$2" 2>/dev/null; then ok "$1"; else bad "$1"; [ -z "${out:-}" ] || head -3 <<<"$out" | sed "s/^/    out: /"; fi; }
cat > "$T/h.py" <<'PY'
# A harness: call the real lane functions, so a test sees the result and its line.
import json, sys
sys.path.insert(0, sys.argv[1]); import lane
runs, slug, name, what = sys.argv[2:6]
if what == "poll":
    status, line, _ = lane.lane(runs, slug, name, lane.flow_spec(), json.load(open(".loop/config.json")), 0)
    print(status); print(line)
elif what == "rm":  # a record is a JSON object on the command line
    lane.rm_tmp(json.loads(sys.argv[6])); print("ok")
PY
poll() { python3 "$T/h.py" "$S" "$RUNS" "$1" "$2" poll; }
until_done() { for _ in $(seq 600); do out=$(poll "$1" "$2"); case "$(grep -m1 -E '^(running|pass|fail)$' <<<"$out")" in running) sleep 0.3 ;; *) echo "$out"; return 0 ;; esac; done; return 1; }

# The fixture is an invented test: it records its TMPDIR and, like a privacy guard, refuses to run when that folder is inside a git checkout.
cat > "$T/fixture.sh" <<'SH'
#!/bin/sh
echo "$TMPDIR" >> "$REC"
if (cd "$TMPDIR" && git rev-parse --git-dir >/dev/null 2>&1); then echo "refuses: output folder is inside a git checkout"; exit 1; fi
SH
$reg add fx --level land --command "sh $T/fixture.sh" --describe "fixture refuses to write inside a git checkout" >/dev/null
python3 -c "import json;c=json.load(open('.loop/config.json'));c['base']='nobase';json.dump(c,open('.loop/config.json','w'),indent=2)"
python3 - <<'PY'
lines = open(".loop/regression.tsv").read().splitlines()
out = []
for line in lines:
    cells = line.split("\t")
    if not line.startswith("#") and cells[0] == "fx":
        cells += [""] * (8 - len(cells)); cells[4] = "2026-01-01"
    out.append("\t".join(cells))
open(".loop/regression.tsv", "w").write("\n".join(out) + "\n")
PY
git add -A; git commit -qm "fixture row"

# Value: protects=a test that refuses to write inside a git checkout passes under the lane (issue 814); fails_when=the lane's TMPDIR is under .git/loop/runs or any checkout; why_new=the lane's temp folder sat inside the repo; seam=none; no_claim=none beyond protects
out=$(until_done ta qa)
check "the fixture that refuses a TMPDIR inside a git checkout passes under the lane" 'grep -qx pass <<<"$out"'
a=$(head -1 "$REC" 2>/dev/null)
check "its TMPDIR is a loop-lane folder keyed by repo, goal and lane (crc32, goal, lane), under the system temp" 'case "$a" in "$(python3 -c "import os,tempfile;print(os.path.realpath(tempfile.gettempdir()))")"/loop-lane-????????-ta-qa-*) true ;; *) false ;; esac'
check "the folder is gone when the lane has ended (finalize removed it)" '[ -n "$a" ] && [ ! -e "$a" ]'
# Value: protects=two lanes of different goals never share a temp folder (REG-8); fails_when=the name omits the goal or the lane, or is reused; why_new=names were base+.tmp; seam=none; no_claim=none beyond protects
out=$(until_done tb qa); b=$(sed -n 2p "$REC" 2>/dev/null)
check "another goal's lane gets a different folder, with its own goal in the name" '[ -n "$b" ] && [ "$a" != "$b" ] && case "$b" in */loop-lane-????????-tb-qa-*) true ;; *) false ;; esac'
# Value: protects=the fixture really fails inside a checkout, so the pass above proves the move (issue 814); fails_when=the fixture ignores where TMPDIR is; why_new=red proof; seam=none; no_claim=none beyond protects
mkdir -p "$RUNS/old.tmp"; out=$(TMPDIR="$RUNS/old.tmp" sh "$T/fixture.sh" 2>&1); rc=$?
check "the same fixture under the old TMPDIR, inside the repo's .git/loop/runs, fails" '[ $rc = 1 ] && grep -q "inside a git checkout" <<<"$out"'
# Value: protects=a system temp inside a checkout is refused before a job exists, never written through (issue 814); fails_when=the lane starts with a folder in a checkout; why_new=refusal is new; seam=none; no_claim=none beyond protects
mkdir -p "$T/outer/.git" "$T/outer/tmp" "$T/wt/tmp"; echo "gitdir: $T/outer/.git" > "$T/wt/.git"
for where in "$T/repo/sub" "$T/outer/tmp" "$T/wt/tmp"; do
  mkdir -p "$where"; out=$(TMPDIR="$where" poll tc qa)
  check "a system temp in a checkout ($(basename "$(dirname "$where")")/$(basename "$where")) refuses with LANE_TMPDIR and its fix, and leaves no job" 'grep -qx fail <<<"$out" && grep -q "^LANE_TMPDIR: .* is in a git checkout. Fix: set TMPDIR to a folder outside any repo" <<<"$out" && [ ! -e "$RUNS/tc.qa-lane.job" ]'
done
# Value: protects=removal touches only a lane folder and never fails the lane (issue 814); fails_when=a record can point rm at any path; why_new=guarded removal is new; seam=none; no_claim=none beyond protects
mkdir -p "$T/keep" "$T/loop-lane-12345678-x-qa-zz"; touch "$T/keep/f"; ln -s "$T/keep" "$T/loop-lane-link"
out=$(python3 "$T/h.py" "$S" "$RUNS" x qa rm "{\"tmp\": \"$T/keep\"}"; python3 "$T/h.py" "$S" "$RUNS" x qa rm "{\"tmp\": \"$T/loop-lane-link\"}"; python3 "$T/h.py" "$S" "$RUNS" x qa rm '{}'; python3 "$T/h.py" "$S" "$RUNS" x qa rm "{\"tmp\": \"$T/loop-lane-12345678-x-qa-zz\"}")
check "removal skips a path outside loop-lane-*, a symlink and a record with no tmp, and removes a lane folder, with no error" '[ "$(grep -c "^ok" <<<"$out")" = 4 ] && [ -f "$T/keep/f" ] && [ ! -e "$T/loop-lane-12345678-x-qa-zz" ]'
out=$(python3 "$T/h.py" "$S" "$RUNS" x qa rm "{\"tmp\": \"$T/missing/loop-lane-gone\"}")
check "removing a folder that is already gone is not an error" 'grep -qx ok <<<"$out"'
check "lane.py and lanekit.py stay under the 20 KB script cap" '[ "$(wc -c < "$S/lane.py")" -lt 20480 ] && [ "$(wc -c < "$S/lanekit.py")" -lt 20480 ]'

[ "$fails" = 0 ] && echo "ALL PASS" || { echo "$fails FAILED"; exit 1; }
