#!/bin/bash
# reads: skills/ dev/toy/make.sh dev/toy/repo/ dev/toy/fakecodex
# SET-3: the template's key commands run in Codex on a clean toy repo with no private settings, and a Codex pod and a
# Claude Code pod running side by side don't collide. Codex gets a plain prompt naming each command and writes each exit
# code and output to .codex-out/; this test checks the files the commands leave and the output they print, never
# Codex's own words. Parts: home (setup under a read-only home, as Codex's sandbox leaves it), collide (two pods at
# once), skip (a row that exits 77 is SKIPPED, never PASS), fake (the harness against a stand-in codex), live (the real
# codex). No part runs all five.
# Exit 77 (SKIPPED, never PASS) when every other part passed but the live part could not run: codex is not installed,
# not signed in, or cannot answer (usage limit, unsupported model). CODEX_BIN names another codex; CODEX_MODEL a model.
# usage: test-codex.sh [home|collide|skip|fake|live]
set -u
unset LOOP_ROLE LOOP_SESSION LOOP_SESSION_TOOL LOOP_OPERATION_SESSION LOOP_FLOW LOOP_LANE_LIMIT
here=$(cd "$(dirname "$0")/../.." && pwd)
. "$here/dev/toy/reap.sh"
only=${1:-}
case "$only" in ""|home|collide|skip|fake|live) ;; *) echo "test-codex.sh: no part '$only'; usage: test-codex.sh [home|collide|skip|fake|live]" >&2; exit 2 ;; esac
want() { [ -z "$only" ] || [ "$only" = "$1" ]; }
export CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"  # codex keeps its own sign-in there; HOME below is the toy's, with no private settings
T=$(mktemp -d); toy_on_exit 'chmod -R u+w "$T" 2>/dev/null; rm -rf "$T"'
export HOME="$T/home" LOOP_BOARD_HEALTH=green; mkdir -p "$HOME"
fails=0; live_skip=""; home_skip=""
ok() { echo "PASS: $1"; }
bad() { echo "FAIL: $1"; fails=$((fails + 1)); }
check() { if eval "$2"; then ok "$1"; else bad "$1"; fi; }
S="$here/skills"
G="python3 $S/workflow-delivery/scripts/goal.py"; SS="python3 $S/workflow-monitoring/scripts/sessions.py"
RG="python3 $S/workflow-regression/scripts/regression.py"

# A toy repo at $1 (repo, origin.git), adopted by setup and merged.
adopted() {
  "$here/dev/toy/make.sh" "$1" >/dev/null || exit 1
  (cd "$1/repo" && python3 "$S/workflow-setup/scripts/setup.py" >/dev/null 2>&1; git switch -q main; git merge -q --no-edit workflow-setup)
}

# The commands the prompt names, one "NAME: COMMAND" line each, in order; the codex run and the stand-in run the same.
commands() {
  echo "setup: LOOP_NO_GIT_HOOKS=1 python3 $S/workflow-setup/scripts/setup.py"
  echo "merge: git switch -q main && git merge -q --no-edit workflow-setup"
  echo "go: LOOP_ROLE=worker python3 $S/workflow-delivery/scripts/goal.py new codex-toy --here --goal 'Add a subtract function' --done 'calc.py has subtract(a, b) returning a - b'"
  echo "board: python3 $S/workflow-monitoring/scripts/monitor.py report"
  echo "health: python3 $S/workflow-health/scripts/health.py check"
  echo "regression: python3 $S/workflow-regression/scripts/regression.py run land"
}
prompt() {
  echo "You are running the workflow template's commands in this git repo, one after another, to prove they work. Run each command below exactly as written, from this repo's root. After each one write its output to .codex-out/NAME.txt and its exit code to .codex-out/NAME.rc, like: CMD > .codex-out/NAME.txt 2>&1; echo \$? > .codex-out/NAME.rc . Do not edit any file yourself and do not stop on a failing command. Commands, in order, each line NAME: COMMAND:"
  commands
  echo "When all are done, reply with one line: DONE."
}
# What the commands must have left, checked from the files and never from what the agent said ($1 names the run).
verify() {
  local O="$2/.codex-out" n
  for n in setup merge go board health regression; do [ -f "$O/$n.rc" ] || { bad "$1: $n ran and left its result"; return; }; done
  check "$1: setup adopts the repo on branch workflow-setup" "grep -q '^WROTE the adoption on branch workflow-setup' $O/setup.txt"
  # with claude or codex on PATH, setup refuses to call a bare agent command done (exit 1, a REFUSED line); with neither it exits 0
  if command -v claude >/dev/null 2>&1 || command -v codex >/dev/null 2>&1; then
    check "$1: setup exits 1 with its REFUSED line about the agent command, as it does on any first run" "[ \"\$(cat $O/setup.rc)\" = 1 ] && grep -q '^REFUSED to call this done: agent_command' $O/setup.txt"
  else
    check "$1: setup exits 0 when no agent is installed" "[ \"\$(cat $O/setup.rc)\" = 0 ]"
  fi
  check "$1: the adoption merges into main" "[ \"\$(cat $O/merge.rc)\" = 0 ]"
  check "$1: go freezes the goal" "grep -q '^FROZEN codex-toy' $O/go.txt && [ -f $2/.loop/goals/codex-toy.md ]"
  check "$1: the live board lists the goal" "grep -q codex-toy $O/board.txt && [ \"\$(cat $O/board.rc)\" = 0 ]"
  check "$1: health check prints its verdict" "grep -q '^HEALTH: ' $O/health.txt"
  check "$1: regression run prints its result with no failed row" "grep -q '^RESULT [0-9]* passed.* 0 failed' $O/regression.txt"
}
# Run $2 (a codex, or the stand-in) as `codex exec` on a fresh toy repo named $1.
as_codex() {
  "$here/dev/toy/make.sh" "$T/$1" >/dev/null || exit 1
  local R="$T/$1/repo"; mkdir -p "$R/.codex-out"; echo ".codex-out/" >> "$R/.git/info/exclude"
  (cd "$R" && "$2" exec --skip-git-repo-check -s workspace-write \
     -c "sandbox_workspace_write.writable_roots=[\"$(git rev-parse --absolute-git-dir)\",\"$T/$1/origin.git\",\"$HOME/.workflow-loop\"]" \
     -c model_reasoning_effort=low ${3:+-m $3} "$(prompt)" </dev/null > "$T/$1.log" 2>&1)
  [ -z "${KEEP:-}" ] || cp "$T/$1.log" "$KEEP"
}

if want home && [ "$(id -u)" = 0 ]; then
  home_skip="root ignores a read-only folder, so the home part cannot show the sandbox case"; echo "SKIPPED: home: $home_skip"
elif want home; then
  adopted_home="$T/h"; "$here/dev/toy/make.sh" "$adopted_home" >/dev/null || exit 1
  mkdir -p "$HOME"; chmod 555 "$HOME"  # what Codex's workspace-write sandbox leaves of the home folder
  out=$(cd "$adopted_home/repo" && python3 "$S/workflow-setup/scripts/setup.py" 2>&1); code=$?
  chmod 755 "$HOME"
  check "home: setup with a read-only home folder does not crash" "! grep -q Traceback <<<\"\$out\""
  check "home: it says the private settings were not written and still adopts the repo" "grep -q '^PRIVATE_NOT_WRITTEN: private settings not written' <<<\"\$out\" && grep -q '^WROTE the adoption' <<<\"\$out\""
  rm -rf "$HOME/.workflow-loop"
fi

if want collide; then
  adopted "$T/c1"; adopted "$T/c2"; R1="$T/c1/repo"; R2="$T/c2/repo"
  # Two pods queue goals and bind workers in the same repo at the same moment.
  for i in 1 2 3 4; do
    pod=$([ $((i % 2)) = 0 ] && echo codex || echo claude)
    (cd "$R1" && LOOP_OPERATION_SESSION=$pod-pod $G queue q$i --goal "queued $i" --done "done $i" > "$T/q$i.out" 2>&1; echo $? >> "$T/q$i.out") &
  done; wait
  check "collide: four goals queued at once by two pods all land, none lost" "[ \$(cat $T/q?.out | grep -c '^QUEUED') = 4 ] && [ \"\$(grep -o 'q[1-4]' $R1/.loop/queue.md | sort -u | wc -l | tr -d ' ')\" = 4 ]"
  for i in 1 2 3 4; do
    tool=$([ $((i % 2)) = 0 ] && echo codex || echo claude)
    (cd "$R1" && LOOP_SESSION_TOOL=$tool $SS bind q$i local_pod$i > "$T/b$i.out" 2>&1; echo $? >> "$T/b$i.out") &
  done; wait
  pool=$(cd "$R1" && $SS list)
  check "collide: four workers bound at once, the pool maps each session to its own goal" "[ \$(for i in 1 2 3 4; do grep -c \"^local_pod\$i .* q\$i\\\$\" <<<\"\$pool\"; done | tr -d '\\n') = 1111 ]"
  (cd "$R1" && $G queue q1 --goal "again" --done "x" > "$T/dup.out" 2>&1; echo $? >> "$T/dup.out")
  check "collide: a second queue of the same slug is refused, not merged" "grep -q 'REFUSED' $T/dup.out && ! grep -q Traceback $T/dup.out"
  # Two pods run a full lane each, in two repos, with one lane slot: one waits, both finish.
  for r in c1 c2; do
    (cd "$T/$r/repo" && $RG add slow-$r --level land --command 'sleep 3; true' --goal HOM-1 --describe "Given a slow row, when it runs, then it passes." >/dev/null 2>&1; git add -A; git commit -qm row)
  done
  for r in c1 c2; do
    (cd "$T/$r/repo" && LOOP_LANE_LIMIT=1 LOOP_SESSION_TOOL=$([ $r = c1 ] && echo claude || echo codex) $RG run land --reuse > "$T/$r.lane" 2>&1; echo rc=$? >> "$T/$r.lane") &
  done; wait
  check "collide: with one lane slot, both pods' lanes finish and one waited its turn" "grep -q '^PASS slow-c1' $T/c1.lane && grep -q '^PASS slow-c2' $T/c2.lane && cat $T/c1.lane $T/c2.lane | grep -q '^LANE_WAIT'"
  check "collide: each lane keeps its own run record" "[ \$(ls $R1/.git/loop/tests | wc -l) -ge 1 ] && [ \$(ls $T/c2/repo/.git/loop/tests | wc -l) -ge 1 ]"
  # Each pod points at its own private flow file, so a Codex pod's settings and a Claude pod's never meet.
  (cd "$R1" && python3 $S/workflow-setup/scripts/settings.py fill-private --file "$T/flow-claude.json" >/dev/null 2>&1; python3 $S/workflow-setup/scripts/settings.py fill-private --file "$T/flow-codex.json" >/dev/null 2>&1)
  check "collide: two pods with their own private flow files write two separate files" "[ -f $T/flow-claude.json ] && [ -f $T/flow-codex.json ]"
fi

if want skip; then
  adopted "$T/s"; R="$T/s/repo"
  # Both rows read calc.py, so neither is an always-run row: the PASS row is reusable and the SKIPPED row must still run again.
  printf 'pass-here\tland\tcat calc.py >/dev/null\tHOM-1\t2026-11-11\tGiven a row that passes, when it runs, then it is PASS.\tcriterion\t\n' >> "$R/.loop/regression.tsv"
  printf 'cannot-run-here\tland\tcat calc.py >/dev/null; exit 77\tHOM-1\t2026-11-11\tGiven a row that cannot run on this machine, when it exits 77, then it is SKIPPED.\tcriterion\t\n' >> "$R/.loop/regression.tsv"
  (cd "$R" && git add -A && git commit -qm rows && $RG run land > "$T/skip.out" 2>&1; echo "rc=$?" >> "$T/skip.out"
   git add -A && git commit -qm ledger && $RG run land --reuse > "$T/skip2.out" 2>&1; $RG run land --reuse > "$T/skip3.out" 2>&1)
  check "skip: a row that exits 77 is reported SKIPPED, not PASS or FAIL, and the lane is not failed by it" "grep -q '^SKIPPED cannot-run-here' $T/skip.out && ! grep -q '^PASS cannot-run-here' $T/skip.out && ! grep -q '^FAIL cannot-run-here' $T/skip.out && grep -q ', 1 skipped\$' $T/skip.out"
  check "skip: it is saved as SKIPPED in the run ledger and opens no issue" "grep -q '^cannot-run-here	SKIPPED' $R/.loop/regression-runs.tsv && ! grep -q 'cannot-run-here' <(grep 'WOULD open' $T/skip.out)"
  check "skip: a later lane reuses the PASS row and runs the SKIPPED row again" "grep -q '^SKIPPED cannot-run-here' $T/skip3.out && ! grep -q '^PASS pass-here' $T/skip3.out && grep -q '(1 reused)' $T/skip3.out"
  printf 'flips\tland\ttest -f .skip-now && exit 77; cat calc.py >/dev/null\tHOM-1\t2026-11-11\tGiven a row that passed, when a later run cannot run it, then the ledger keeps its PASS.\tcriterion\t\n' >> "$R/.loop/regression.tsv"
  (cd "$R" && git add -A && git commit -qm flips && $RG run land > /dev/null 2>&1; touch .skip-now; $RG run land > "$T/skip4.out" 2>&1)
  check "skip: a skip never overwrites the row's last PASS in the run ledger" "grep -q '^SKIPPED flips' $T/skip4.out && grep -q '^flips	PASS' $R/.loop/regression-runs.tsv"
  check "skip: red refuses a break run that exits 77" "(cd $R && $RG red cannot-run-here --break true 2>&1 | grep -q '^REFUSED: the row exited 77')"
fi

if want fake; then
  as_codex fake "$here/dev/toy/fakecodex"; verify fake "$T/fake/repo"
fi

if want live; then
  bin=${CODEX_BIN:-codex}
  if ! command -v "$bin" >/dev/null 2>&1; then live_skip="codex is not installed on this machine"
  elif ! "$bin" login status >/dev/null 2>&1; then live_skip="codex is not signed in on this machine"
  else
    model=${CODEX_MODEL:-$(python3 - <<'PY' 2>/dev/null
import json, os
slugs = [m["slug"] for m in json.load(open(os.path.join(os.environ["CODEX_HOME"], "models_cache.json")))["models"] if m.get("visibility") == "list"]
print(next((s for s in slugs if "luna" in s), slugs[0] if slugs else ""))
PY
)}
    probe=$(cd "$T" && "$bin" exec --skip-git-repo-check -s read-only -c model_reasoning_effort=low ${model:+-m $model} "reply with the word OK" </dev/null 2>&1); pc=$?
    if [ $pc != 0 ] || ! grep -qi 'ok' <<<"$probe"; then
      live_skip="codex cannot answer here: $(grep -m1 'ERROR' <<<"$probe" | cut -c1-160)"
    else
      as_codex live "$bin" "$model"; verify live "$T/live/repo"
    fi
  fi
  [ -z "$live_skip" ] || echo "SKIPPED: live: $live_skip"
fi

[ $fails = 0 ] || { echo "$fails FAILED"; exit 1; }
[ -z "$live_skip$home_skip" ] || { echo "SKIPPED: every part that could run passed; $live_skip$home_skip"; exit 77; }
echo "ALL PASS"
