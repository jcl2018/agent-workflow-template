#!/bin/bash
# Test the Cost rule and the judge of workflow-health with a stand-in judge. usage: test-health-judge.sh [DIR]
set -u
here=$(cd "$(dirname "$0")/../.." && pwd)
d=${1:-$(mktemp -d)}; rm -rf "$d"; mkdir -p "$d"
"$here/dev/toy/make.sh" "$d" || exit 1
export LOOP_FLOW="$d/flow.json" LOOP_HEALTH="$d/none.json"
health="python3 $here/skills/workflow-health/scripts/health.py"
cd "$d/repo" || exit 1
python3 "$here/skills/workflow-setup/scripts/setup.py" --bare >/dev/null
git switch -q main; git merge -q --no-edit workflow-setup
fails=0
ok() { echo "PASS: $1"; }
bad() { echo "FAIL: $1"; fails=$((fails + 1)); }
runs="$(git rev-parse --absolute-git-dir)/loop/runs"; mkdir -p "$runs"

# a finished goal: fast and cheap, slow, or costly. Steps take the gap before their log entry.
goal() { python3 - "$runs" "$@" <<'PY'
import json, sys
runs, slug, minutes, tokens = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
log = ["2026-11-0%dT10:00:00Z queued" % (1 + len(slug) % 5)]
day = log[0][:11]
log += ["%s%02d:%02d:00Z %s" % (day, 10 + (minutes * i // len(("idea", "build", "qa")) // 60), (minutes * i // 3) % 60, step)
        for i, step in enumerate(("idea", "build", "qa"), 1)]
state = {"slug": slug, "status": "done", "updated": "2026-11-08T12:00:00Z", "log": log}
if tokens:
    state["tokens"] = {"idea": tokens // 10, "build": tokens - tokens // 10}
json.dump(state, open("%s/%s.json" % (runs, slug), "w"))
PY
}
setcfg() { python3 - "$@" <<'PY'
import json, sys
c = json.load(open(".loop/config.json"))
for pair in sys.argv[1:]:
    key, _, value = pair.partition("=")
    c[key] = json.loads(value) if value else None
    if not value: c.pop(key)
json.dump(c, open(".loop/config.json", "w"))
PY
}

echo "== Cost: no budget set"
goal quick 6 100
out=$($health check --family cost); echo "$out"
grep -q "^INFO cost budgets cost: " <<<"$out" && ok "no budget set is INFO" || bad "info"

echo "== Cost: over a time and a token budget"
setcfg time_budget_minutes=30 token_budget=1000
goal slowone 90 5000
out=$($health check --family cost); echo "$out"
grep -q "^WARN cost slowone time: .*over 30 min; slowest: " <<<"$out" && ok "a goal over the time budget warns and names its slowest steps" || bad "time"
grep -q "^WARN cost slowone tokens: 5000 tokens, over 1000; costliest: build 4500" <<<"$out" && ok "a goal over the token budget warns and names its costliest step" || bad "tokens"
! grep -q "cost quick " <<<"$out" && ok "a goal within both budgets is not named" || bad "quick named"
[ "$(tail -1 <<<"$out" | cut -c1-12)" = "HEALTH: gree" ] && ok "cost warnings never turn the verdict red" || bad "cost red"

echo "== Cost: no tokens recorded"
rm "$runs"/*.json; goal notokens 90 0
out=$($health check --family cost); rc=$?; echo "$out"
grep -q "^UNREAD cost tokens cost: no tokens recorded" <<<"$out" && [ $rc = 1 ] && ok "no tokens recorded prints UNREAD" || bad "unread"
grep -q "^WARN cost notokens time: " <<<"$out" && ok "time is still judged" || bad "time without tokens"
rm "$runs"/*.json; goal slowone 90 5000

echo "== the judge: a stand-in, after the rules"
cat > "$d/judge.sh" <<'SH'
#!/bin/bash
echo x >> "$JUDGE_CALLS"
cat > /dev/null
echo "preamble the judge was not asked for"
echo "CRITERION HLT-1 | too vague to test | One command prints one verdict, twice the same"
echo "TEST same-lines | only compares two runs | add a run with a changed file"
echo "SAVES 10 | the plan step rereads every skill file | pass a summary"
echo "SAVES 40 | review reruns checks after every skill | run checks once after review"
SH
printf '#!/bin/bash\ncat > /dev/null\necho boom >&2\nexit 3\n' > "$d/broken.sh"
printf '#!/bin/bash\ncat > /dev/null\necho "FAIL everything is on fire"\necho "HEALTH: green (0 pass)"\n' > "$d/garbage.sh"
chmod +x "$d"/*.sh; export JUDGE_CALLS="$d/calls"
setcfg "judge_command=[\"$d/judge.sh\"]"
a=$($health check); b=$($health check); rc_check=$?
[ "$a" = "$b" ] && ok "check gives the same answer twice" || bad "check differs"
[ ! -e "$JUDGE_CALLS" ] && ok "check never calls the judge" || bad "check called the judge"
out=$($health judge); rc=$?; echo "$out"
[ $rc = $rc_check ] && ok "stand-in judge: same exit code as check" || bad "exit code with judge"
[ -e "$JUDGE_CALLS" ] && ok "judge calls the judge command" || bad "judge not called"
[ "$(sed -n '1,/^$/p' <<<"$out" | sed '$d')" = "$a" ] && ok "the rules and the verdict print first, as check prints them" || bad "rules first"
sec=$(sed -n '/^JUDGE (suggestions, never part of the verdict)$/,$p' <<<"$out")
[ -n "$sec" ] && ok "the judge section is marked as suggestions" || bad "judge heading"
for h in "criteria quality" "test quality" "performance and tokens, ranked by savings" "Needs you" "candidate goals" "next steps"; do
  grep -q "^== $h ==$" <<<"$sec" && ok "section: $h" || bad "section $h"
done
needs=$(sed -n '/^== Needs you ==$/,/^== candidate goals ==$/p' <<<"$sec")
grep -q "reword HLT-1: One command prints one verdict" <<<"$needs" && ok "suggested criterion wording lands under Needs you" || bad "needs you"
cands=$(sed -n '/^== candidate goals ==$/,/^== next steps ==$/p' <<<"$sec")
grep -q "strengthen test same-lines" <<<"$cands" && ok "a weak test is a candidate goal" || bad "weak test"
[ "$(grep -n 'save 40%' <<<"$cands" | cut -d: -f1)" -lt "$(grep -n 'save 10%' <<<"$cands" | cut -d: -f1)" ] && ok "savings are ranked, biggest first" || bad "ranking"
grep -q "^next 1: " <<<"$sec" && ok "ranked next steps end the section" || bad "next steps"
! grep -q "preamble" <<<"$out" && ok "untagged judge text is ignored" || bad "untagged"

echo "== the verdict never depends on the judge"
verdict() { grep -m1 "^HEALTH: " <<<"$1"; }
v0=$(verdict "$a")
[ "$(verdict "$out")" = "$v0" ] && ok "stand-in judge: same verdict line" || bad "verdict with judge"
setcfg "judge_command=[\"$d/broken.sh\"]"
out2=$($health judge); rc2=$?
grep -q "^JUDGE UNAVAILABLE: the judge exited 3" <<<"$out2" && [ "$(verdict "$out2")" = "$v0" ] && [ $rc2 = $rc_check ] && ok "a failing judge: unavailable, same verdict and exit code" || bad "broken judge"
setcfg "judge_command=[\"$d/garbage.sh\"]"
out3=$($health judge); rc3=$?
grep -q "^JUDGE UNAVAILABLE: the answer had no tagged line" <<<"$out3" && [ "$(grep -c '^HEALTH: ' <<<"$out3")" = 1 ] && [ "$(verdict "$out3")" = "$v0" ] && [ $rc3 = $rc_check ] && ok "a garbage judge cannot change the verdict" || bad "garbage judge"
setcfg judge_command=
out4=$($health judge); grep -q "^JUDGE UNAVAILABLE: no judge_command" <<<"$out4" && ok "no judge_command: unavailable" || bad "no command"
$health suggest | grep -q "^JUDGE UNAVAILABLE" && ok "suggest is kept as an alias of judge" || bad "alias"

echo "== no model in the rules"
grep -qn "claude\|anthropic\|urllib\|http" "$here/skills/workflow-health/scripts/cost.py" && bad "model or network in cost.py" || ok "cost.py calls no model"
echo "== size"
for f in "$here"/skills/workflow-health/scripts/*.py; do [ "$(wc -c < "$f")" -lt 20480 ] || bad "size of $f"; done; ok "every health script is under 20 KB"
echo "repo: $d/repo"
[ "$fails" = 0 ] && echo "ALL PASS" || { echo "$fails FAILED"; exit 1; }
