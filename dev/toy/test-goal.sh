#!/bin/bash
# Test levels, the queue command, version bumps and the governing watch with a fake agent. No model is called.
# usage: test-goal.sh [DIR]
set -u
here=$(cd "$(dirname "$0")/../.." && pwd)
d=${1:-$(mktemp -d)}; rm -rf "$d"; mkdir -p "$d"
"$here/dev/toy/make.sh" "$d" || exit 1
goal="python3 $here/skills/workflow-delivery/scripts/goal.py"
W="python3 $here/skills/workflow-monitoring/scripts/watch.py"
M="python3 $here/skills/workflow-monitoring/scripts/monitor.py"
export PATH="$here/dev/toy/fakegh:$PATH" FAKE_GH_DIR="$d/gh"
cd "$d/repo" || exit 1
python3 "$here/skills/workflow-setup/scripts/setup.py" >/dev/null
git switch -q main; git merge -q --no-edit workflow-setup; git push -q origin main
fails=0
ok() { echo "PASS: $1"; }
bad() { echo "FAIL: $1"; fails=$((fails + 1)); }
C=$(cd "$(git rev-parse --git-common-dir)" && pwd)
field() { python3 -c "import json,sys;print(json.load(open(sys.argv[1])).get(sys.argv[2]))" "$C/loop/runs/$1.json" "$2"; }
cfg() { python3 - "$@" <<'PY'
import json, sys
c = json.load(open(".loop/config.json"))
for pair in sys.argv[1:]:
    key, _, value = pair.partition("=")
    c[key] = json.loads(value)
json.dump(c, open(".loop/config.json", "w"), indent=2)
PY
}

echo "== new needs --here: one session governs"
$goal new blocked --goal "No" --done "no" 2>&1 | grep -q "one session governs" && ok "new refused without --here" || bad "new refused"

echo "== 0 is the default: design, plan, build, checks, no judge"
out=$($goal new low --here --goal "Add low" --done "calc has low"); echo "$out"
grep -q "level=0" <<<"$out" && grep -q "step=design" <<<"$out" && ok "default level 0, starts at design" || bad "level 0 start"
printf '\n\ndef low():\n    return 1\n' >> calc.py; git commit -qam "Add low"
$goal check low | grep -q "NEXT: pr" && ok "level 0 goes from checks to pr" || bad "level 0 next"
$goal pr low | grep -q "^PR " && ok "pr without a judge" || bad "level 0 pr"
grep -q "Not judged (0)" "$FAKE_GH_DIR/calls.log" && ok "pr says not judged" || bad "pr body"
git switch -q main

echo "== risky paths raise 0 to 1"
$goal new risky --here --goal "Touch CI" --done "ci" --touches ".github/x.yml" | grep -q "level=1" && ok "raised at the start" || bad "raise start"
git switch -q main
$goal new sneaky --here --goal "Sneak" --done "ci" >/dev/null
mkdir -p .github; echo x > .github/x.yml; git add -A; git commit -qm "Sneak"
$goal check sneaky | grep -q "NEXT: judge" && ok "raised by the diff" || bad "raise diff"
git switch -q main

echo "== check summarizes every command's exit code first, even past long output"
cp .loop/config.json "$d/cfg.bak"
cfg 'checks=["python3 -c \"print(\\\"x\\\"*20000)\"","exit 3"]'
git commit -qam "Noisy checks"
$goal new loud --here --goal "Loud" --done "loud" >/dev/null
$goal check loud >/dev/null 2>&1
head -c 300 "$C/loop/runs/loud.checks.txt" | grep -q "^CHECK exit 0: python3" && head -c 300 "$C/loop/runs/loud.checks.txt" | grep -q "^CHECK exit 3: exit 3" && ok "summary shows every check at the top" || bad "check summary"
[ "$(wc -c < "$here/skills/workflow-delivery/scripts/goal.py")" -lt 20480 ] && ok "goal.py under 20 KB" || bad "goal.py size"
git switch -q main; git checkout -q -- .loop/config.json 2>/dev/null; cp "$d/cfg.bak" .loop/config.json; git status --porcelain | grep -q config.json && git commit -qam "Restore checks"

echo "== a goal with no change has nothing to judge, and that costs no try"
git switch -q main
$goal new emptyj --here --goal "Empty" --done "empty" --level 1 >/dev/null
$goal check emptyj >/dev/null 2>&1
out=$($goal judge emptyj 2>&1)
grep -q "REFUSED: no change to judge" <<<"$out" && [ "$(field emptyj tries)" = 0 ] && ok "judge refuses an empty diff" || bad "empty diff judged: $out"
git switch -q main

echo "== queue adds a line a watcher can read, and poc stays read-only"
$goal queue fix-a --goal "Fix a" --done "a is fixed" --level 0 --touches "a.py" | grep -q QUEUED && ok "queued" || bad "queue"
grep -q '^- slug: fix-a | level: 0 | touches: a.py | goal: Fix a | done: a is fixed$' .loop/queue.md && ok "valid line" || bad "queue line"
$goal queue fix-a --goal "Fix a" --done "x" 2>&1 | grep -q "already exists" && ok "duplicate refused" || bad "duplicate"
$goal queue pipe --goal "a|b" --done "x" 2>&1 | grep -q "no |" && ok "pipe refused" || bad "pipe"
$M report | grep -q "fix-a" && ok "report reads it" || bad "report queue"
git checkout -q -- .loop/queue.md

echo "== the old level names are refused, naming the new levels"
$goal new oldname --here --goal "Old" --done "old" --level standard 2>&1 | grep -q "use 0 (no judge), 1 (one judge) or 2 (adds a design review)" && ok "old name refused" || bad "old name"
$goal queue oldq --goal "Old" --done "old" --level quick 2>&1 | grep -q "use 0 (no judge), 1 (one judge) or 2 (adds a design review)" && ok "old queue level refused" || bad "old queue level"
[ -z "$(ls .loop/goals 2>/dev/null | grep oldname)" ] && ok "refused goal not created" || bad "old goal created"

echo "== level 2 design review says which ran, and the private setting picks the skill"
git switch -q main
$goal new dskill --here --goal "Skilled" --done "skilled" --level 2 >/dev/null
HOME="$d/home" $goal judge dskill --design 2>&1 | grep -q "DESIGN REVIEW: built-in (no design skill set)" && ok "built-in review named" || bad "built-in review"
mkdir -p "$d/home/.claude/skills/my-design"; echo "Review like this." > "$d/home/.claude/skills/my-design/SKILL.md"
HOME="$d/home" LOOP_DESIGN_SKILL=my-design $goal judge dskill --design 2>&1 | grep -q "DESIGN REVIEW: using skill my-design" && ok "private skill used" || bad "private skill"
HOME="$d/home" LOOP_DESIGN_SKILL=missing-one $goal judge dskill --design 2>&1 | grep -q "built-in (skill missing-one not found)" && ok "missing skill falls back" || bad "missing skill"
git ls-files | grep -q design-skill && bad "setting in repo" || ok "setting is not in the repo"
git switch -q main

echo "== a failed design review stays at the design; the plan isn't reviewed yet"
git switch -q main
$goal new drev --here --goal "Review" --done "reviewed" --level 2 >/dev/null
echo "VERDICT: fail" > "$d/vf"
$goal verdict drev --file "$d/vf" --design > "$d/dr"
grep -q "NEXT: rewrite the design" "$d/dr" && [ "$(field drev step)" = design ] && [ "$(field drev tries)" = 1 ] && ok "design failure goes back to the design" || bad "design failure"
grep -q "design and plan" "$here/skills/workflow-delivery/scripts/goal.py" && bad "review prompt" || ok "review prompt doesn't ask about the plan"
git switch -q main

echo "== evidence needs new checks, and a verdict failed on proof alone costs a try"
$goal new proof --here --goal "Add proof" --done "calc has proof" --level 1 >/dev/null
printf '\n\ndef proof():\n    return 1\n' >> calc.py; git commit -qam "Add proof"
$goal check proof >/dev/null
printf '\n## Evidence\n\nsome output\n' >> .loop/goals/proof.md; git commit -qam "Evidence"
$goal judge proof 2>&1 | grep -q "checks have not passed on this commit" && ok "judge refuses evidence the checks missed" || bad "evidence commit"
$goal check proof >/dev/null
printf 'FAIL 1: no proof in the evidence\nVERDICT: fail\n' > "$d/vf"
$goal verdict proof --file "$d/vf" | grep -q "NEXT: fix it, then run check again" && [ "$(field proof tries)" = 1 ] && [ "$(field proof step)" = build ] && ok "failed on proof: one try, back to build" || bad "proof verdict"
printf 'PASS 1: ok\nVERDICT: pass\n' > "$d/vf"
$goal check proof >/dev/null; $goal verdict proof --file "$d/vf" >/dev/null; $goal pr proof >/dev/null
grep -q "^## Result" "$FAKE_GH_DIR/calls.log" && [ "$(grep -c '^## Evidence' "$FAKE_GH_DIR/calls.log")" = 1 ] && ok "pr body keeps one Evidence section" || bad "pr body sections"
git switch -q main

echo "== the Delivery page names every goal.py command and flag"
missing=""
for word in $(python3 "$here/skills/workflow-delivery/scripts/goal.py" -h | sed -n '/^  new /,/^  show /p' | awk '{print $1}') $(grep -oE 'add_argument\("--[a-z]+"' "$here/skills/workflow-delivery/scripts/goal.py" | cut -d'"' -f2 | sort -u); do
  grep -q -- "$word" "$here/docs/wiki/Delivery.md" || missing="$missing $word"
done
[ -z "$missing" ] && ok "page lists them" || bad "page lacks:$missing"
grep -q "Done lines a judge can prove" "$here/skills/workflow-delivery/SKILL.md" && ok "skill says how to write done lines" || bad "done line guidance"

echo "== pr_bumps_version moves the last number once"
echo 1.3.3.3 > VERSION; git add -A; git commit -qm "Version"; git push -q origin main
cfg 'pr_bumps_version=true'; git commit -qam "Bump config"; git push -q origin main
$goal new bump --here --goal "Add bump" --done "calc has bump" >/dev/null
printf '\n\ndef bump():\n    return 1\n' >> calc.py; git commit -qam "Add bump"
$goal check bump >/dev/null; $goal pr bump >/dev/null
[ "$(cat VERSION)" = "1.3.3.4" ] && ok "VERSION bumped" || bad "bump: $(cat VERSION)"
[ "$(git log -1 --format=%s)" = "Bump version to 1.3.3.4" ] && ok "bump commit" || bad "bump commit"
[ "$(git show origin/loop/bump:VERSION)" = "1.3.3.4" ] && ok "bump pushed" || bad "bump push"
[ "$(field bump checks_sha)" = "$(git rev-parse HEAD)" ] && ok "checks stay valid" || bad "checks sha"
$goal pr bump >/dev/null; [ "$(cat VERSION)" = "1.3.3.4" ] && ok "second pr doesn't bump again" || bad "double bump"
git switch -q main
cfg 'pr_bumps_version=false'; git commit -qam "Bump off"; git push -q origin main

echo "== a failed push is retried, and a final failure prints git's error"
hook="$d/origin.git/hooks/pre-receive"
printf '#!/bin/bash\n[ -e "%s/pushed-once" ] && exit 0\ntouch "%s/pushed-once"\necho "busy, try again" >&2\nexit 1\n' "$d" "$d" > "$hook"
chmod +x "$hook"
$goal new retry --here --goal "Add retry" --done "calc has retry" >/dev/null
printf '\n\ndef retry():\n    return 1\n' >> calc.py; git commit -qam "Add retry"
$goal check retry >/dev/null
$goal pr retry | grep -q "^PR " && ok "second push worked" || bad "retry"
git switch -q main
printf '#!/bin/bash\necho "the remote said no" >&2\nexit 1\n' > "$hook"
$goal new nopush --here --goal "Add nopush" --done "calc has nopush" >/dev/null
printf '\n\ndef nopush():\n    return 1\n' >> calc.py; git commit -qam "Add nopush"
$goal check nopush >/dev/null
$goal pr nopush > "$d/np" 2>&1; rc=$?
[ $rc != 0 ] && grep -q "the remote said no" "$d/np" && ok "final failure prints git's error" || bad "push error"
rm -f "$hook"; git switch -q main

echo "== go starts a background agent; the governing process writes no code"
cat > "$d/agent.sh" <<'A'
#!/bin/bash
# A stand-in agent. It records its prompt, then does what the files in $d say.
prompt=${!#}
slug=$(grep -oE 'Slug: [a-z0-9-]+' <<<"$prompt" | head -1 | cut -d' ' -f2)
[ -n "$slug" ] || slug=$(grep -oE 'goal [a-z0-9-]+ in this git' <<<"$prompt" | head -1 | cut -d' ' -f2)
n=$(ls "$FAKE_AGENT"/prompt-"$slug"-* 2>/dev/null | wc -l | tr -d ' ')
printf '%s' "$prompt" > "$FAKE_AGENT/prompt-$slug-$n"
pwd > "$FAKE_AGENT/pwd-$slug"
b="$FAKE_AGENT/behave-$slug"
if [ -f "$b" ] && [ "$(sed -n "$((n + 1))p" "$b")" = fail ]; then echo "agent crashed: it could not find calc"; exit 1; fi
if [ -f "$b" ] && [ "$(sed -n "$((n + 1))p" "$b")" = limit ]; then echo "error: usage limit reached"; exit 1; fi
python3 - "$COMMON/loop/runs/$slug.json" <<'PY'
import json, sys
s = json.load(open(sys.argv[1])); s["status"] = "done"; s["step"] = "release"; s["pr"] = "https://example.test/pull/1"
json.dump(s, open(sys.argv[1], "w"))
PY
A
export FAKE_AGENT="$d/fake" COMMON="$C"; mkdir -p "$FAKE_AGENT"
cfg "agent_command=[\"bash\", \"$d/agent.sh\"]" 'parallel=2'
git commit -qam "Agent"; git push -q origin main
head0=$(git rev-parse HEAD)
$W go "Add alpha" --done "alpha works" --touches a.py --slug alpha | tee "$d/g1"
grep -q "STARTED alpha" "$d/g1" && ok "go started it" || bad "go"
$W go "Add beta" --done "beta works" --touches b.py --slug beta >/dev/null
$W go "Add gamma" --done "gamma works" --touches c.py --slug gamma >/dev/null
$W go "Add delta please" --done "delta works" --touches c.py >/dev/null
grep -q '^- slug: add-delta-please |' .loop/queue.md && ok "slug made from the goal" || bad "slug"
$W go "Bad" 2>&1 | grep -q "REFUSED" && ok "go needs a done line" || bad "go done"
$W watch --interval 0.2 --skill-dir "$here/skills" | tee "$d/w1"
grep -q "NOTHING LEFT" "$d/w1" && ok "watch ended by itself" || bad "watch end"
for s in alpha beta gamma add-delta-please; do [ "$(field $s status)" = done ] || bad "$s status"; done
ok "every goal finished"
[ "$(git rev-parse HEAD)" = "$head0" ] && [ -z "$(git status --porcelain -- calc.py)" ] && ok "governing checkout wrote no code" || bad "governor wrote code"
[ "$(cat "$FAKE_AGENT/pwd-alpha")" != "$(cat "$FAKE_AGENT/pwd-beta")" ] && ok "each goal has its own worktree" || bad "worktree"
case "$(cat "$FAKE_AGENT/pwd-alpha")" in */loop/worktrees/alpha) ok "worktree under loop/";; *) bad "worktree path";; esac
grep -q "Start at step 2 (Design)" "$FAKE_AGENT/prompt-alpha-0" && ok "level 0 starts at Design" || bad "prompt step"

echo "== mender: one fresh agent, told only the finding and the log"
printf 'fail\nfail\nfail\n' > "$FAKE_AGENT/behave-mendme"
cfg 'mend=true' 'mend_wait=0'
$W go "Mend me" --done "mended" --slug mendme >/dev/null
$W watch --interval 0.2 --skill-dir "$here/skills" | tee "$d/w2"
[ "$(ls "$FAKE_AGENT"/prompt-mendme-* | wc -l | tr -d ' ')" = 2 ] && ok "one mend, then it stops" || bad "mend count"
grep -q "could not find calc" "$FAKE_AGENT/prompt-mendme-1" && grep -q "WHY IT STOPPED" "$FAKE_AGENT/prompt-mendme-1" && ok "mender got the finding and log" || bad "mend prompt"
grep -q "NEEDS YOU mendme" "$d/w2" && ok "still failed goal reported" || bad "needs you"
printf 'fail\nok\n' > "$FAKE_AGENT/behave-mendok"
$W go "Mend ok" --done "mended" --slug mendok >/dev/null
$W watch --interval 0.2 --skill-dir "$here/skills" >/dev/null
[ "$(field mendok status)" = done ] && [ "$(field mendok mended)" = True ] && ok "mended goal finished" || bad "mend ok"

echo "== usage limit: waits, resumes, and doesn't use up the mend"
printf 'limit\nok\n' > "$FAKE_AGENT/behave-limited"
cfg 'mend=false' 'resume_on_limit=true' 'limit_wait=2'
$W go "Limited" --done "resumed" --slug limited >/dev/null
sleep 1
$W watch --once --skill-dir "$here/skills" | tee "$d/w3"
[ "$(field limited status)" = failed ] && grep -q "usage limit" "$d/w3" && ok "first pass waits" || bad "limit wait"
$W watch --interval 0.3 --skill-dir "$here/skills" | tee "$d/w4"
[ "$(field limited status)" = done ] && [ "$(field limited limit_resumes)" = 1 ] && ok "resumed after the wait" || bad "limit resume"
[ "$(field limited mended)" = None ] && ok "limit didn't use the mend" || bad "limit mend"
printf 'fail\n' > "$FAKE_AGENT/behave-off"
cfg 'resume_on_limit=false'
$W go "Off" --done "x" --slug off >/dev/null
$W watch --interval 0.2 --skill-dir "$here/skills" >/dev/null
[ "$(ls "$FAKE_AGENT"/prompt-off-* | wc -l | tr -d ' ')" = 1 ] && ok "both off: no relaunch" || bad "off"

echo "== report still works beside watch"
$M report | grep -q "alpha" && ok "report" || bad "report"
$M dashboard >/dev/null && ok "dashboard" || bad "dashboard"

[ "$fails" = 0 ] && echo "ALL PASS" || { echo "$fails FAILED"; exit 1; }
