#!/bin/bash
# reads: skills/workflow-health/scripts/workflows.py skills/workflow-health/scripts/automation.py skills/workflow-health/scripts/rounds.py
# reads: skills/workflow-health/scripts/rules.py skills/workflow-regression/scripts/regression.py skills/workflow-regression/scripts/tiers.py
# reads: skills/workflow-setup/scripts/seed.py skills/workflow-setup/scripts/setup.py skills/workflow-setup/scripts/settings.py
# reads: skills/workflow-delivery/scripts/private.py dev/toy/fakegh/gh dev/toy/fakegh/fake.py dev/toy/fakegh/launchctl docs/wiki/Health.md
# The local schedule (local-schedule done lines 1 to 6): one user launch agent, a registry outside every repo, a tick that runs
# health with the judge and, for a private repo, the full regression, then posts the digest. No launchctl, no network, no real
# claude: launchctl, gh and the judge are fakes and every home is a temp folder. usage: test-local-schedule.sh [PART]
# Value: protects=a private repo's health, regression and digest run on the owner's Mac and never in GitHub, and a missed run says so;
# fails_when=the plist loads itself, holds a secret, a tick changes issues offline, a child outlives its cap, or a health workflow is written;
# why_new=health and the regression used to run in GitHub Actions; seam=none; no_claim=launchd firing the agent (the owner's kickstart check)
set -u
unset GITHUB_SERVER_URL GITHUB_REPOSITORY GITHUB_RUN_ID LOOP_SESSION_TOOL LOOP_OPERATION_SESSION ANTHROPIC_API_KEY CLAUDECODE
here=$(cd "$(dirname "$0")/../.." && pwd); only=${1:-}
. "$here/dev/toy/reap.sh"
S="$here/skills/workflow-health/scripts"; A="$S/automation.py"
fails=0
ok() { echo "PASS: $1"; }
bad() { echo "FAIL: $1"; fails=$((fails + 1)); }
check() { if eval "$2"; then ok "$1"; else bad "$1"; echo "    out: ${out:-}"; fi; }
want() { [ -z "$only" ] || [ "$only" = "$1" ]; }
d=$(mktemp -d); toy_on_exit 'rm -rf "$d"'
fresh() {  # a new temp HOME, schedule home, agents folder, fake gh and fake launchctl
  export HOME="$d/home$RANDOM"; mkdir -p "$HOME"
  export LOOP_SCHEDULE_HOME="$HOME/sched" LOOP_AGENTS_DIR="$HOME/agents" LOOP_LAUNCHCTL="$here/dev/toy/fakegh/launchctl" LOOP_SCHEDULE_PROGRAM="$A"
  export FAKE_GH_DIR="$HOME/gh"; mkdir -p "$FAKE_GH_DIR"; export PATH="$here/dev/toy/fakegh:$ORIG_PATH"
  unset LOOP_REPO_VISIBILITY FAKE_GH_OFFLINE FAKE_GH_PRIVATE LOOP_SCHEDULE_PLATFORM LOOP_TICK_MINUTES LOOP_TICK_TOTAL_MINUTES
}
ORIG_PATH="$PATH"
toyrepo() {  # NAME [config json]: a toy repo with a bare origin, a failing row, pushed to origin/main; prints its path
  "$here/dev/toy/make.sh" "$d/$1" >/dev/null || exit 1
  ( cd "$d/$1/repo" && mkdir -p .loop && printf '%s\n' "${2:-{\}}" | sed 's/^{/{"base": "main", /; s/{"base": "main", }/{"base": "main"}/' > .loop/config.json \
    && printf '# id\tlevel\tcommand\tgoal\tseen_red\tdescription\tcategory\tlink\nbad-row\tland\tfalse\tx:1\t2026-01-01\tGiven a thing, when it runs, then it fails.\tcriterion\t\n' > .loop/regression.tsv \
    && git add -A && git commit -qm "loop files" && git push -q origin main ) >/dev/null
  echo "$d/$1/repo"
}
install() { ( cd "$1" && python3 "$A" local install ); }
tick() { ( cd "$1" && python3 "$A" local tick --repo "$1" "${@:2}" ); }
reg() { python3 -c "import json,sys; d=json.load(open('$LOOP_SCHEDULE_HOME/repos.json'))['repos']; print(eval(sys.argv[1]))" "$1"; }

if want plist; then fresh; r=$(toyrepo p '{"health_cron": "47 */4 * * *"}')
  out=$(install "$r"); rc=$?
  check "install writes the agent, prints the load and stop lines and loads nothing" '[ $rc = 0 ] && grep -q "^SCHEDULE installed for " <<<"$out" && grep -q "launchctl bootstrap gui/" <<<"$out" && grep -q "launchctl bootout gui/" <<<"$out" && ! grep -q bootstrap "$LOOP_SCHEDULE_HOME/launchctl.log" 2>/dev/null'
  python3 - "$LOOP_AGENTS_DIR/com.workflow-loop.schedule.plist" "$r" "$HOME" > "$d/plist.out" 2>&1 <<'PY'
import plistlib, sys
p = plistlib.load(open(sys.argv[1], "rb"))
hours = sorted({s["Hour"] for s in p["StartCalendarInterval"]}); minutes = {s["Minute"] for s in p["StartCalendarInterval"]}
text = open(sys.argv[1]).read()
assert p["Label"] == "com.workflow-loop.schedule" and p["RunAtLoad"] is False and p["ProcessType"] == "Background", p
assert hours == [0, 4, 8, 12, 16, 20] and minutes == {47}, (hours, minutes)
assert p["ProgramArguments"][1].startswith("/") and p["ProgramArguments"][2:] == ["local", "tick", "--scheduled"], p["ProgramArguments"]
assert "API_KEY" not in text and "TOKEN" not in text and sys.argv[2] not in text, "secret, key name or repo path in the plist"
print("plist ok")
PY
  out=$(cat "$d/plist.out"); check "the plist parses, fires at 0 4 8 12 16 20 on minute 47, runs one absolute program, holds no secret, key name or repo path" 'grep -qx "plist ok" "$d/plist.out"'
  r2=$(toyrepo p2 '{"health_cron": "0 3 * * 1"}'); out=$(install "$r2" 2>&1); rc=$?
  check "a cron that is not an every-N-hours or fixed-hours shape is refused with SCHEDULE_CRON" '[ $rc != 0 ] && grep -q "(SCHEDULE_CRON)" <<<"$out"'
  out=$(( cd "$r" && LOOP_SCHEDULE_PROGRAM= python3 "$A" local install ) 2>&1 | head -2)
  check "the schedule never installs a program path under a worktree or the system temp (SCHEDULE_PROGRAM_PATH)" 'grep -q "(SCHEDULE_PROGRAM_PATH)" <<<"$out"'
fi
if want registry; then fresh; a=$(toyrepo ra '{"health_cron": "47 */4 * * *"}'); b=$(toyrepo rb '{"health_cron": "5 3 * * *"}')
  ( cd "$b" && git remote set-url origin "git@example.test:owner/other.git" ); ( cd "$a" && git remote set-url origin "https://example.test/owner/repo.git" )
  install "$a" >/dev/null; install "$b" >/dev/null
  check "two repos each get their own entry in one registry, mode 0600, outside the repos" '[ "$(reg "len(d)")" = 2 ] && [ "$(stat -f %Lp "$LOOP_SCHEDULE_HOME/repos.json" 2>/dev/null || stat -c %a "$LOOP_SCHEDULE_HOME/repos.json")" = 600 ]'
  check "the agent calendar is the union of both repos' slots" '[ "$(python3 -c "import plistlib; print(len(plistlib.load(open(\"$LOOP_AGENTS_DIR/com.workflow-loop.schedule.plist\",\"rb\"))[\"StartCalendarInterval\"]))")" = 7 ]'
  ( cd "$b" && git remote set-url origin "ssh://git@example.test/owner/repo.git/" ); out=$(install "$b" 2>&1)
  check "the ssh and https forms of one origin give one key: the second clone is refused (SCHEDULE_DUPLICATE_ORIGIN)" 'grep -q "(SCHEDULE_DUPLICATE_ORIGIN)" <<<"$out"'
  ( cd "$b" && git remote set-url origin "git@example.test:owner/other.git" && git remote remove origin ); out=$(install "$b" 2>&1)
  check "a repo with no origin is refused (SCHEDULE_NO_ORIGIN)" 'grep -q "(SCHEDULE_NO_ORIGIN)" <<<"$out"'
  ( cd "$b" && git remote add origin "git@example.test:owner/other.git" )
  out=$(python3 "$A" local plist | grep -c "<integer>47</integer>")
  check "install loads the agent only with --load; without it launchctl bootstrap was never run" '[ ! -f "$LOOP_SCHEDULE_HOME/launchctl.log" ] || ! grep -q bootstrap "$LOOP_SCHEDULE_HOME/launchctl.log"'
  out=$(install_load=1; ( cd "$a" && python3 "$A" local install --load )); check "install --load runs the printed bootstrap line through launchctl" 'grep -q "^bootstrap gui/" "$LOOP_SCHEDULE_HOME/launchctl.log"'
  rm -rf "$b"; out=$(tick "$a" --dry-run 2>&1; python3 "$A" local tick --dry-run 2>&1)
  check "an entry whose path was deleted is named and skipped" 'grep -q "PATH_MISSING" <<<"$out"'
  out=$(cd "$a" && python3 "$A" local uninstall 2>&1); check "uninstall notes the agent stays loaded for the other repo" 'grep -q "stays loaded" <<<"$out" && [ -f "$LOOP_AGENTS_DIR/com.workflow-loop.schedule.plist" ]'
  python3 - "$LOOP_SCHEDULE_HOME/repos.json" <<'PY'
import json, sys
d = json.load(open(sys.argv[1])); d["repos"] = {}; json.dump(d, open(sys.argv[1], "w"))
PY
  c=$(toyrepo rc '{"health_cron": "5 3 * * *"}'); install "$c" >/dev/null; ( cd "$c" && python3 "$A" local uninstall >/dev/null )
  check "the agent file goes with the last repo, and bootout ran" '[ ! -e "$LOOP_AGENTS_DIR/com.workflow-loop.schedule.plist" ] && grep -q "^bootout " "$LOOP_SCHEDULE_HOME/launchctl.log"'
  out=$(python3 - "$S" <<'PY'
import sys
sys.path.insert(0, sys.argv[1]); import workflows as w
print(w.slots("5 3 * * *")[1], w.slots("5 2,14 * * *")[1], w.slots("5 */6 * * *")[1], w.slots("5 */5 * * *"))
PY
  ); check "a single fixed-hour cron has a 24 hour interval; two fixed hours use the largest gap; a step that does not divide 24 is not read" '[ "$out" = "24 12 6 None" ]'
fi
if want dryrun; then fresh; r=$(toyrepo dr '{"health_cron": "47 */4 * * *"}'); install "$r" >/dev/null
  before=$(cat "$LOOP_SCHEDULE_HOME/repos.json"); out=$(tick "$r" --dry-run 2>&1)
  check "tick --dry-run prints each repo's plan and due state and writes nothing" 'grep -q "^PLAN " <<<"$out" && [ "$before" = "$(cat "$LOOP_SCHEDULE_HOME/repos.json")" ] && [ ! -d "$LOOP_SCHEDULE_HOME/log" -o ! -s "$LOOP_SCHEDULE_HOME/log/tick.log" ]'
  out=$(cd "$r" && python3 "$A" local status 2>&1); check "status lists the repo and prints OK or FIX per check" 'grep -q "last_run never" <<<"$out" && grep -q "^FIX loaded: launchctl bootstrap gui/" <<<"$out" && grep -q "^OK plist" <<<"$out"'
  out=$(cd "$r" && python3 "$A" local status --json); check "status --json prints the same checks as one object" 'python3 -c "import json,sys; d=json.loads(sys.argv[1]); assert \"plist\" in d[\"checks\"] and d[\"repos\"]" "$out"'
  echo "{broken" > "$LOOP_SCHEDULE_HOME/repos.json"; keep=$(cat "$LOOP_SCHEDULE_HOME/repos.json")
  o1=$(tick "$r" 2>&1); o2=$(install "$r" 2>&1); o3=$(cd "$r" && python3 "$A" local uninstall 2>&1)
  check "an unreadable registry stops tick, install and uninstall and is never overwritten (REGISTRY_UNREADABLE)" '[ "$(printf "%s\n%s\n%s\n" "$o1" "$o2" "$o3" | grep -c "(REGISTRY_UNREADABLE)")" = 3 ] && [ "$keep" = "$(cat "$LOOP_SCHEDULE_HOME/repos.json")" ]'
  out=$(cd "$r" && LOOP_SCHEDULE_PLATFORM=linux python3 "$A" local install 2>&1); check "off macOS install refuses with SCHEDULE_PLATFORM" 'grep -q "(SCHEDULE_PLATFORM)" <<<"$out"'
  out=$(cd "$r" && python3 "$A" workflow; echo rc=$?); check "automation.py workflow is removed: it says so and exits 2 (SCHEDULE_REMOVED_WORKFLOW)" 'grep -q "(SCHEDULE_REMOVED_WORKFLOW)" <<<"$out" && grep -q "rc=2" <<<"$out"'
  wt="$d/x/loop/worktrees/y"; mkdir -p "$wt"; cp -R "$S" "$wt/scripts"; out=$(cd "$r" && LOOP_SCHEDULE_PROGRAM= python3 "$wt/scripts/automation.py" local install 2>&1)
  check "install from a copy under loop/worktrees refuses (SCHEDULE_PROGRAM_PATH)" 'grep -q "(SCHEDULE_PROGRAM_PATH)" <<<"$out"'
fi
cfgj() {  # RUNS [extra json members]: a repo config with a fake judge
  printf '{"regression_runs": "%s", "health_cron": "47 */4 * * *", "judge_command": ["bash", "%s/fakeclaude"]%s}' "$1" "$d" "${2:+, $2}"
}
printf '#!/bin/bash\ncat > /dev/null\necho "${ANTHROPIC_API_KEY:-unset} ${CLAUDECODE:-unset}" > "%s/judge-env"\n' "$d" > "$d/fakeclaude"
issues() { python3 -c "import json; print(len(json.load(open('$FAKE_GH_DIR/issues.json'))))" 2>/dev/null || echo 0; }
if want privatetick; then fresh; export FAKE_GH_PRIVATE=true; r=$(toyrepo pt "$(cfgj mac)"); install "$r" >/dev/null
  out=$(tick "$r" 2>&1); rc=$?; [ -z "${DEBUG_TICK:-}" ] || { cat "$FAKE_GH_DIR/calls.log"; cat "$LOOP_SCHEDULE_HOME/log/tick.log"; }
  check "a private repo's tick runs health, the judge and the regression live on the Mac" '[ $rc = 0 ] && grep -q "^JUDGE: ran" <<<"$out" && grep -q "REGRESSION: runs on the Mac" <<<"$out" && grep -q "^SKILLS: " <<<"$out"'
  check "the failing row is filed as one regression issue, and the digest comment is posted" 'grep -q "issue create.*bad-row\|issue create.*regression" "$FAKE_GH_DIR/calls.log" && grep -q "issue comment" "$FAKE_GH_DIR/calls.log"'
  check "the registry records the run: last_run set, last_ok" '[ -n "$(reg "list(d.values())[0][\"last_run\"]")" ]'
fi
if want publictick; then fresh; export FAKE_GH_PRIVATE=false; r=$(toyrepo pu "$(cfgj actions)"); install "$r" >/dev/null
  out=$(tick "$r" 2>&1)
  check "a public repo's tick runs health but no regression, and looks for the newest suite-time artifact" 'grep -q "REGRESSION: runs in GitHub Actions" <<<"$out" && ! grep -q "regression.py run\|bad-row" "$FAKE_GH_DIR/calls.log" && grep -q "run list --workflow regression.yml" "$FAKE_GH_DIR/calls.log"'
fi
if want offline; then fresh; export FAKE_GH_OFFLINE=1; r=$(toyrepo of "$(cfgj mac)"); install "$r" >/dev/null
  python3 - "$LOOP_SCHEDULE_HOME/repos.json" <<'PY'
import json, sys
d = json.load(open(sys.argv[1])); list(d["repos"].values())[0]["last_run"] = "2026-01-01T00:00:00Z"; json.dump(d, open(sys.argv[1], "w"))
PY
  out=$(tick "$r" --scheduled 2>&1); rc=$?; o2=$(tick "$r" 2>&1); rc2=$?
  check "offline: SKIPPED with its cause and fix, no issue changed, last_run kept, the skip counted, exit 0 scheduled and 3 by hand" \
    '[ $rc = 0 ] && [ $rc2 = 3 ] && grep -q "SKIPPED .* (SCHEDULE_AUTH)" <<<"$out" && [ "$(issues)" = 0 ] && [ "$(reg "list(d.values())[0][\"last_run\"]")" = 2026-01-01T00:00:00Z ] && [ "$(reg "list(d.values())[0][\"skips\"]")" = 2 ]'
fi
if want missed; then fresh; export FAKE_GH_PRIVATE=false; r=$(toyrepo ms "$(cfgj actions)"); install "$r" >/dev/null
  last() { python3 - "$LOOP_SCHEDULE_HOME/repos.json" "$1" <<'PY'
import datetime, json, sys
d = json.load(open(sys.argv[1])); hours = float(sys.argv[2])
list(d["repos"].values())[0]["last_run"] = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%SZ"); json.dump(d, open(sys.argv[1], "w"))
PY
  }
  compose() { python3 - "$S" "$1" <<'PY'
import os, sys
sys.path.insert(0, sys.argv[1]); import automation
os.environ.update(DIGEST_LAST=sys.argv[2], DIGEST_INTERVAL="4")
print(automation.compose("", "", [("health", "x")], {}, {}, "202611110800")[0])
PY
  }
  out=$(compose "2026-11-10T00:00:00Z"); check "a last run older than the interval plus an hour says Last ran and MISSED" 'grep -q "^Last ran: 2026-11-11 08:00, previous run 2026-11-10 00:00 (32 hours earlier)" <<<"$out" && grep -q "^MISSED: no run for 32 hours (Mac asleep or offline)" <<<"$out"'
  out=$(compose "2026-11-11T05:00:00Z"); check "a recent last run says Last ran and no MISSED" 'grep -q "^Last ran: " <<<"$out" && ! grep -q "MISSED" <<<"$out"'
  python3 - "$S" <<'PY' > "$d/due.out"
import datetime, sys
sys.path.insert(0, sys.argv[1]); import workflows as w
n = w.now(); at = lambda m: {"last_run": (n - datetime.timedelta(minutes=m)).strftime(w.STAMP)}
print(w.due(at(4 * 60 - 20), 4, n), w.due(at(60), 4, n), w.due({}, 4, n), w.due(at(24 * 60 - 59), 24, n))
PY
  out=$(cat "$d/due.out"); check "a repo whose tick began 20 minutes after another's is still due at the next fire; a recent one is not; none ever run is due" '[ "$out" = "True False True True" ]'
  python3 - "$S" <<'PY' > "$d/ids.out"
import sys
sys.path.insert(0, sys.argv[1]); import rounds
print(rounds.is_local("202611110847"), rounds.is_local("302611110847"), rounds.is_local("12345678901"), rounds.order("202611110847") > rounds.order("29999999999"))
PY
  out=$(cat "$d/ids.out"); check "a 12 digit run id starting 20 is a local run, any other number is an Actions id, and local ids sort after Actions ids" '[ "$out" = "True False False True" ]'
  last 1; out=$(tick "$r" --scheduled 2>&1); check "one coalesced fire after sleep runs every overdue repo; a repo run just now is not run again" 'grep -q "NOT DUE" <<<"$out"'
  last 40; out=$(tick "$r" --scheduled 2>&1); check "a repo overdue by more than the interval is run at the next fire" '! grep -q "NOT DUE" <<<"$out" && grep -q "^SKILLS: " <<<"$out"'
  check "the digest of that run said when it last ran, with the gap" 'grep -q "Last ran: " "$FAKE_GH_DIR/calls.log"'
fi
if want judge; then fresh; export FAKE_GH_PRIVATE=false; export ANTHROPIC_API_KEY=sk-ant-toykey CLAUDECODE=1
  r=$(toyrepo jd "$(cfgj actions)"); install "$r" >/dev/null; out=$(tick "$r" 2>&1)
  check "the tick starts the judge with no ANTHROPIC_API_KEY and no CLAUDECODE, so it uses the owner's login and never an API key" '[ "$(cat "$d/judge-env" 2>/dev/null)" = "unset unset" ] && grep -q "^JUDGE: ran" <<<"$out"'
  unset ANTHROPIC_API_KEY CLAUDECODE
  ( cd "$r" && python3 "$A" local uninstall >/dev/null )
  r=$(toyrepo jm '{"regression_runs": "actions", "health_cron": "47 */4 * * *", "judge_command": ["no-such-claude-program"]}'); install "$r" >/dev/null
  out=$(tick "$r" 2>&1); check "a missing claude program makes the judge skipped, the log says so" 'grep -q "^JUDGE: skipped" <<<"$out"'
  tick "$r" >/dev/null 2>&1; out=$(tick "$r" 2>&1); check "the third consecutive skipped judge puts JUDGE_SKIPPED in status" '[ "$(reg "list(d.values())[0][\"judge_skipped\"]")" = 3 ] && ( cd "$r" && python3 "$A" local status ) | grep -q "JUDGE_SKIPPED 3 ticks"'
  check "the default judge_command grants no tools (--tools \"\")" 'python3 -c "import json; c=json.load(open(\"$here/.loop/config.json\"))[\"judge_command\"]; assert c[-2:] == [\"--tools\", \"\"], c"'
  check "no code reads or passes an API key variable except the tick dropping it" '! grep -n "judge_env\|judge_setup\|secrets\.ANTHROPIC" "$S/workflows.py" "$S/automation.py"'
fi
if want digest; then fresh; export FAKE_GH_PRIVATE=false; r=$(toyrepo dg "$(cfgj actions)"); install "$r" >/dev/null
  out=$(tick "$r" 2>&1); body=$(sed -n '/^issue comment/,$p' "$FAKE_GH_DIR/calls.log")
  check "the digest comment has the regression, health, round cost and email rows and a Last ran line" 'grep -q "| regression |" <<<"$body" && grep -q "| health |" <<<"$body" && grep -q "| round cost |" <<<"$body" && grep -q "| email |" <<<"$body" && grep -q "Last ran: " <<<"$body"'
  check "the round cost reads local run, N min, 0 Actions minutes, and the email row says it is not set up" 'grep -q "local run, [0-9]* min, 0 Actions minutes" <<<"$body" && grep -q "not set up (MAIL_NOT_SET_UP)" <<<"$body"'
fi
if want logtrim; then fresh; export FAKE_GH_PRIVATE=false; r=$(toyrepo lt "$(cfgj actions)"); install "$r" >/dev/null
  mkdir -p "$LOOP_SCHEDULE_HOME/log"; head -c 300000 /dev/zero | tr '\0' 'x' > "$LOOP_SCHEDULE_HOME/log/tick.log"
  printf 'DIGEST_TO=a@example.test\nDIGEST_FROM=b@example.test\nCLOUDFLARE_ACCOUNT_ID=toyid\nCLOUDFLARE_EMAIL_TOKEN=toytoken\n' > "$LOOP_SCHEDULE_HOME/mail.env"; chmod 644 "$LOOP_SCHEDULE_HOME/mail.env"
  out=$(tick "$r" 2>&1); size=$(wc -c < "$LOOP_SCHEDULE_HOME/log/tick.log")
  check "the tick log is trimmed to its last 200 KB at the start of a tick, and a mail.env of the wrong mode sends nothing (MAIL_ENV_MODE)" '[ "$size" -lt 260000 ] && grep -q "MAIL_ENV_MODE" "$FAKE_GH_DIR/calls.log" && ! grep -rq toytoken "$FAKE_GH_DIR" "$LOOP_SCHEDULE_HOME/log"'
  rm -f "$FAKE_GH_DIR/calls.log"; python3 - "$LOOP_SCHEDULE_HOME/repos.json" <<'PY'
import json, sys
d = json.load(open(sys.argv[1])); list(d["repos"].values())[0]["last_run"] = ""; json.dump(d, open(sys.argv[1], "w"))
PY
  out=$(LOOP_TICK_MINUTES=0 tick "$r" 2>&1)
  check "with a zero-minute cap health and mail are skipped (cap reached), the digest still posts, and last_ok is false" '[ "$(grep -c "(cap reached)" <<<"$out")" -ge 2 ] && grep -q "issue comment" "$FAKE_GH_DIR/calls.log" && [ "$(reg "list(d.values())[0][\"last_ok\"]")" = False ]'
fi
if want hungchild; then fresh; r=$(toyrepo hc "$(cfgj actions)"); install "$r" >/dev/null
  python3 - "$S" "$d" <<'PY' > "$d/hung.out" 2>&1
import os, subprocess, sys, time
sys.path.insert(0, sys.argv[1]); import workflows as w
d = sys.argv[2]; log = open(d + "/hung.log", "a")
code, text = w.child(["bash", "-c", "sleep 300 & echo $! > %s/sleeper.pid; wait" % d], d, dict(os.environ), 1, log)
time.sleep(0.3)
pid = int(open(d + "/sleeper.pid").read())
try:
    os.kill(pid, 0); print("sleeper alive")
except ProcessLookupError:
    print("group gone")
print("code", code)
PY
  out=$(cat "$d/hung.out"); check "a child that spawns a sleeper is killed with its whole process group at the cap" 'grep -q "group gone" <<<"$out" && grep -q "code 124" <<<"$out"'
  mkdir -p "$LOOP_SCHEDULE_HOME/$(reg "list(d)[0]").lock" 2>/dev/null; key=$(reg "list(d)[0]")
  sleep 30 & holder=$!; echo $holder > "$LOOP_SCHEDULE_HOME/$key.lock/pid"
  out=$(tick "$r" 2>&1); check "a second tick during the first skips with locked by pid" 'grep -q "SKIPPED $key (locked by pid $holder)" <<<"$out"'
  kill $holder; wait $holder 2>/dev/null; out=$(tick "$r" --dry-run 2>&1)
  export FAKE_GH_OFFLINE=1; out=$(tick "$r" 2>&1); check "a stale lock whose pid is dead is taken over" '! grep -q "locked by pid" <<<"$out" && grep -q "SKIPPED $key (gh auth status failed)" <<<"$out" && [ ! -d "$LOOP_SCHEDULE_HOME/$key.lock" ]'
fi
if want nothing; then fresh; export FAKE_GH_PRIVATE=false; r=$(toyrepo nt "$(cfgj actions)"); install "$r" >/dev/null; tick "$r" >/dev/null 2>&1; ( cd "$r" && python3 "$A" local status >/dev/null )
  check "install, status and a tick leave the repo clean and put no temp home path or token in any file of it" '[ -z "$(cd "$r" && git status --porcelain)" ] && ! grep -rIl -e "$HOME" -e "gh[pousr]_" -e "sk-ant-" "$r" --exclude-dir=.git'
fi
if want size; then
  out=$(cd "$here" && for f in skills/workflow-health/scripts/workflows.py skills/workflow-health/scripts/automation.py skills/workflow-health/scripts/rounds.py skills/workflow-delivery/scripts/private.py skills/workflow-delivery/scripts/goal.py skills/workflow-release/scripts/merge.py skills/workflow-release/scripts/autorelease.py skills/workflow-regression/scripts/regression.py skills/workflow-regression/scripts/tiers.py skills/workflow-regression/scripts/actions.py skills/workflow-setup/scripts/seed.py skills/workflow-setup/scripts/setup.py skills/workflow-setup/scripts/settings.py skills/workflow-health/scripts/rules.py; do
      now=$(wc -c < "$f"); was=$(git show "origin/main:$f" 2>/dev/null | wc -c); [ "$was" = 0 ] && was=$now
      if [ "$now" -ge 20480 ] || { [ "$now" -ge 18432 ] && { [ "$was" -lt 18432 ] || [ $((now - was)) -gt 400 ]; }; }; then echo "OVER $f $was -> $now"; fi; done)
  check "each touched script is under the WARN line unless it started over it and grew by at most 400 bytes, and under the FAIL line" '[ -z "$out" ]'
  if git -C "$here" rev-parse -q --verify origin/main >/dev/null; then
    check "skills holds no more files than origin/main" '[ "$(git -C "$here" ls-files skills | wc -l)" -le "$(git -C "$here" ls-tree -r --name-only origin/main -- skills | wc -l)" ]'
  else echo "SKIP size baseline (no origin/main)"; fi
  check "the package holds at most 99 files" 'python3 "$here/dev/package.py" >/dev/null 2>&1 || true; [ "$(git -C "$here" ls-files skills listing.json README.md LICENSE | wc -l)" -le 99 ]'
fi
setup() { ( cd "$1" && shift && python3 "$here/skills/workflow-setup/scripts/setup.py" "$@" 2>&1 ); }
bare() {  # NAME: a toy repo with no loop files yet, pushed
  "$here/dev/toy/make.sh" "$d/$1" >/dev/null || exit 1; echo "$d/$1/repo"
}
rules_bound='[{"type": "required_status_checks", "parameters": {"required_status_checks": [{"context": "lane-a"}, {"context": "bound-x", "integration_id": 15368}]}}, {"type": "merge_queue", "parameters": {}}, {"type": "pull_request", "parameters": {"required_approving_review_count": 1}}]'
if want noworkflow; then fresh
  check "the template has no health.yml and no mail-test.yml, and its health workflow text is gone" '[ ! -e "$here/.github/workflows/health.yml" ] && [ ! -e "$here/.github/workflows/mail-test.yml" ] && ! grep -q "name: health" "$S/workflows.py"'
  for vis in true false; do export FAKE_GH_PRIVATE=$vis; r=$(bare nw$vis)
    out=$(setup "$r" --dry-run); o2=$(setup "$r")
    check "setup (private=$vis) plans and writes no health.yml or mail-test.yml, and plans the local schedule" '! grep -q "health.yml\|mail-test" <<<"$out$o2" && [ ! -e "$r/.github/workflows/health.yml" ] && [ ! -e "$r/.github/workflows/mail-test.yml" ] && grep -q "^add: local schedule" <<<"$out"'
    check "setup (private=$vis) registered the repo in the local registry, loaded nothing" '[ "$(reg "len(d)")" -ge 1 ] && ! grep -q "^bootstrap" "$LOOP_SCHEDULE_HOME/launchctl.log" 2>/dev/null'
  done
  out=$(cd "$r" && python3 "$A" workflow; echo rc=$?); check "automation.py workflow exits 2 with SCHEDULE_REMOVED_WORKFLOW" 'grep -q "rc=2" <<<"$out" && grep -q "(SCHEDULE_REMOVED_WORKFLOW)" <<<"$out"'
fi
if want noprivatewf; then fresh; export FAKE_GH_PRIVATE=true; r=$(bare np)
  out=$(setup "$r"); check "a private repo gets no regression.yml and no regression-pr.yml; setup says why" '[ ! -e "$r/.github/workflows/regression.yml" ] && [ ! -e "$r/.github/workflows/regression-pr.yml" ] && grep -q "a private repo.s regression runs on the Mac" <<<"$out"'
  out=$(cd "$r" && python3 "$here/skills/workflow-regression/scripts/regression.py" workflow); check "regression.py workflow on a private repo prints NOT WRITTEN" 'grep -q "^NOT WRITTEN: this repo is private" <<<"$out"'
  mkdir -p "$r/.github/workflows"; printf '# Written by workflow-regression\nname: regression\n' > "$r/.github/workflows/regression.yml"
  out=$(cd "$r" && python3 "$here/skills/workflow-regression/scripts/regression.py" workflow); check "a regression.yml of ours in a private repo is named REMOVABLE and never deleted" 'grep -q "^REMOVABLE: .github/workflows/regression.yml" <<<"$out" && [ -f "$r/.github/workflows/regression.yml" ]'
  export FAKE_GH_PRIVATE=error; r=$(bare np2)
  out=$(cd "$r" && python3 "$here/skills/workflow-regression/scripts/regression.py" workflow); check "an unreadable visibility writes nothing and says why" '[ ! -e "$r/.github/workflows/regression.yml" ] && grep -q "visibility could not be read" <<<"$out"'
fi
if want blocks; then fresh; export FAKE_GH_PRIVATE=true; r=$(bare bl); rules_json() { printf '%s\n' "$1" > "$FAKE_GH_DIR/rules.json"; }; rules_json "$rules_bound"
  out=$(setup "$r"); check "setup names the bound check, the approving-review rule and the merge queue as BLOCKS" '[ "$(grep -c "^BLOCKS: " <<<"$out")" -ge 3 ] && grep -q "^BLOCKS: bound-x" <<<"$out" && grep -q "BLOCKS: .*merge_queue\|BLOCKS: .*merge queue\|BLOCKS: .*a merge" <<<"$out"'
  check "setup posted no status and wrote no ruleset or protection (only reads reached gh)" '! grep -q "statuses" "$FAKE_GH_DIR/calls.log" && ! grep -Eq "api (-X|--method) (PUT|PATCH|POST|DELETE)" "$FAKE_GH_DIR/calls.log"'
fi
if want triggers; then fresh; r=$(bare tr); W="$here/skills/workflow-regression/scripts/regression.py"
  mkdir -p "$r/skills/workflow-regression/scripts"; : > "$r/skills/workflow-regression/scripts/regression.py"
  ( cd "$r" && python3 "$W" workflow --visibility public ) >/dev/null 2>&1; cp "$r/.github/workflows/regression.yml" "$d/reg1.yml"; ( cd "$r" && python3 "$W" workflow --visibility public ) >/dev/null 2>&1
  pr="$r/.github/workflows/regression-pr.yml"
  check "a public repo with the skills folder gets regression-pr.yml with pull_request and a branch push, fetch-depth 0, the narrow command, and no tag, schedule, token or issue step" \
    'cmp -s "$d/reg1.yml" "$r/.github/workflows/regression.yml" && grep -q "^  pull_request:" "$pr" && grep -q "branches-ignore" "$pr" && grep -q "fetch-depth: 0" "$pr" && grep -q "run nightly --reuse --tier goal" "$pr" && ! grep -qi "schedule:\|tags:\|GH_TOKEN\|secrets\.\|issue" "$pr" && grep -q "^  schedule:" "$r/.github/workflows/regression.yml"'
  rm -rf "$r/skills" "$r/.github"; ( cd "$r" && python3 "$W" workflow --visibility public ) >/dev/null 2>&1
  check "a repo without the skills folder gets regression.yml only" '[ -f "$r/.github/workflows/regression.yml" ] && [ ! -e "$r/.github/workflows/regression-pr.yml" ]'
  ( cd "$r" && rm -rf .github && python3 "$W" workflow --visibility private ) >/dev/null 2>&1; check "a private repo gets neither file" '[ ! -e "$r/.github/workflows/regression.yml" ] && [ ! -e "$r/.github/workflows/regression-pr.yml" ]'
  # the narrow command in a fresh clone selects the reached rows and not FULL
  g=$(toyrepo nr '{}'); ( cd "$g" && mkdir -p src && printf 'a\n' > src/a.txt && printf 'b\n' > src/b.txt && printf '#!/bin/bash\n# reads: src/a.txt\ntrue\n' > src/ta.sh && printf '#!/bin/bash\n# reads: src/b.txt\ntrue\n' > src/tb.sh \
    && printf '# id\tlevel\tcommand\tgoal\tseen_red\tdescription\tcategory\tlink\nta\tland\tbash src/ta.sh\tx:1\t2026-01-01\tGiven a, when it runs, then it passes.\tcriterion\t\ntb\tland\tbash src/tb.sh\tx:1\t2026-01-01\tGiven b, when it runs, then it passes.\tcriterion\t\n' > .loop/regression.tsv \
    && git add -A && git commit -qm rows && git push -q origin main )
  git clone -q "$d/nr/origin.git" "$d/fresh" 2>/dev/null; ( cd "$d/fresh" && git config user.email t@example.test && git config user.name Toy && git switch -qc feature && echo a2 >> src/a.txt && git commit -qam change )
  out=$(cd "$d/fresh" && python3 "$W" run nightly --reuse --tier goal 2>&1); check "the narrow command in a fresh clone selects the reached row only, not FULL" 'grep -q "^AFFECTED 1 of 2 rows (ta)" <<<"$out" && ! grep -q "^FULL" <<<"$out"'
fi
if want scheduledrule; then fresh; r=$(toyrepo sr '{}'); H="python3 $S/health.py check --group adoption"
  ( cd "$r" && mkdir -p .github/workflows && printf 'name: health\n' > .github/workflows/health.yml ); out=$(cd "$r" && $H 2>&1)
  check "a leftover health.yml is a WARN naming git rm" 'grep -q "WARN adoption health.yml scheduled: has no job: health runs on the Mac now -> fix: git rm .github/workflows/health.yml" <<<"$out"'
  ( cd "$r" && rm -rf .github ); out=$(cd "$r" && $H 2>&1); check "regression_runs unset (actions) with no regression.yml still WARNs" 'grep -q "WARN adoption regression.yml scheduled" <<<"$out"'
  ( cd "$r" && printf '{"base": "main", "regression_runs": "mac"}\n' > .loop/config.json ); out=$(cd "$r" && $H 2>&1); check "regression_runs mac with no regression.yml is no WARN" '! grep -q "regression.yml scheduled" <<<"$out"'
  out=$(cd "$r" && python3 "$S/health.py" check --group controls 2>&1); check "the scheduled rule's negative control fires" 'grep -q "PASS controls scheduled control: fires on its fixture" <<<"$out"'
fi
if want setting; then fresh
  for vis in true false error; do export FAKE_GH_PRIVATE=$vis; r=$(bare st$vis); out=$(setup "$r"); cfg=$(cat "$r/.loop/config.json" 2>/dev/null)
    case $vis in true) want_v='"regression_runs": "mac"';; false) want_v='"regression_runs": "actions"';; *) want_v="";; esac
    check "setup (visibility $vis) records regression_runs: $want_v" '{ [ -z "$want_v" ] && ! grep -q regression_runs <<<"$cfg"; } || grep -q "$want_v" <<<"$cfg"'
  done
  check "setup names the cause when visibility is unreadable" 'grep -q "visibility unreadable" <<<"$out"'
  out=$(python3 "$here/skills/workflow-setup/scripts/settings.py" reference); check "settings lists regression_runs with its default" 'grep -q "regression_runs" <<<"$out" && grep -q "actions" <<<"$out"'
  export FAKE_GH_PRIVATE=false; r=$(toyrepo dr "$(cfgj mac)"); install "$r" >/dev/null; out=$(tick "$r" 2>&1)
  check "the tick prints DRIFT when live visibility disagrees with regression_runs, and the setting still decides what runs" 'grep -q "DRIFT: regression_runs says mac but the repo is public" <<<"$out" && grep -q "bad-row" "$FAKE_GH_DIR/calls.log"'
fi
if want usage; then H="$here/docs/wiki/Health.md"
  check "the Health page Usage names install, the launchctl bootstrap and bootout lines, uninstall and tick" 'grep -q "local install" "$H" && grep -q "launchctl bootstrap gui/" "$H" && grep -q "launchctl bootout gui/" "$H" && grep -q "local uninstall" "$H" && grep -q "local tick" "$H" && grep -q "claude. must be logged in once" "$H"'
  out=$(python3 "$A" --help 2>&1; python3 "$A" local --help 2>&1); missing=""
  for c in $(grep -o "workflow-health local [a-z]*" "$H" | sort -u | awk '{print $3}'); do grep -q "$c" <<<"$out" || missing="$missing $c"; done
  check "every local command the page names exists in automation.py --help" '[ -z "$missing" ]'
  check "the Usage states the trust model once and that no API key secret exists" 'grep -q "the Mac is the CI" "$H" && grep -q "no API key secret" "$H"'
fi
if want messages; then H="$here/docs/wiki/Health.md"; miss=""
  for code in SCHEDULE_CRON SCHEDULE_PROGRAM_PATH SCHEDULE_DUPLICATE_ORIGIN SCHEDULE_NO_ORIGIN SCHEDULE_PLATFORM SCHEDULE_REMOVED_WORKFLOW SCHEDULE_AUTH SCHEDULE_OFFLINE REGISTRY_UNREADABLE MAIL_ENV_MODE TICK_CRASH STATUS_FAILED STATUSES_UNREADABLE BLOCKS DRIFT JUDGE_SKIPPED PROGRAM_MISSING ORIGIN_CHANGED PATH_MISSING; do
    grep -q "\`$code\` .*(exit" "$H" || miss="$miss table:$code"
    grep -q "$code" "$S/workflows.py" "$S/automation.py" "$here/skills/workflow-delivery/scripts/private.py" || miss="$miss print:$code"
  done
  out="$miss"; check "every code the scripts print has a Messages row with its meaning, exit status and fix, and every printed line ends with its code" '[ -z "$miss" ]'
  check "goal.py pr exit 5 is documented" 'grep -q "goal.py. pr. exits 5\|goal.py pr exits 5" "$H"'
fi
[ "$fails" = 0 ] && echo "ALL PASS" || { echo "$fails FAILED"; exit 1; }
