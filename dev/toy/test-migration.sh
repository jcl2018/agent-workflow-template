#!/bin/bash
# reads: skills/workflow-setup/scripts/seed.py skills/workflow-setup/scripts/setup.py skills/workflow-setup/scripts/settings.py
# reads: skills/workflow-setup/scripts/update.py skills/workflow-setup/scripts/sync.py skills/workflow-setup/scripts/agents.py
# reads: skills/workflow-health/scripts/workflows.py skills/workflow-health/scripts/automation.py skills/workflow-delivery/scripts/private.py
# reads: skills/workflow-docs/scripts/render.py skills/workflow-docs/scripts/entry.py dev/toy/fakegh/gh dev/toy/fakegh/fake.py dev/toy/fakegh/launchctl
# reads: docs/wiki/Setup.md
# One command judges a repo's migration (migration-check done lines 1 to 11): toy repos with a bare origin and a bare wiki beside
# them. No network, launchd or gh: gh and launchctl are fakes, every home is a temp folder, and nothing is written outside the temp.
# usage: test-migration.sh [PART]   no part runs every part. Test-only overrides: LOOP_TEST=1 with LOOP_INSTALLED_VERSION,
# LOOP_SCHEDULE_PLATFORM, LOOP_SCHEDULE_HOME. Always run it with stdin closed (< /dev/null).
# Value: protects=a repo is judged fully migrated by one command that names every gap with its fix and writes nothing;
# fails_when=a kind of gap goes unnamed, a clean repo reports one, the check writes, or a migration cannot close its own gaps;
# why_new=adopted repos drifted from the template with nothing to say so; seam=none; no_claim=a live GitHub wiki, launchd, branch protection
set -u
unset GITHUB_SERVER_URL GITHUB_REPOSITORY GITHUB_RUN_ID LOOP_SESSION_TOOL LOOP_OPERATION_SESSION LOOP_BATCH ANTHROPIC_API_KEY CLAUDECODE LOOP_FLOW
here=$(cd "$(dirname "$0")/../.." && pwd); only=${1:-}
. "$here/dev/toy/reap.sh"
S="$here/skills"; SETUP="$S/workflow-setup/scripts"; HEALTH="$S/workflow-health/scripts"; DOCS="$S/workflow-docs/scripts"
d=$(mktemp -d); toy_on_exit 'rm -rf "$d"'
fails=0
ok() { echo "PASS: $1"; }
bad() { echo "FAIL: $1"; fails=$((fails + 1)); }
check() { if eval "$2"; then ok "$1"; else bad "$1"; echo "    out: ${out:-}" | head -12; fi; }
want() { [ -z "$only" ] || [ "$only" = "$1" ]; }
ORIG_PATH="$PATH"
fresh() {  # a new temp HOME, schedule home, fake gh and fake launchctl; the test-only overrides are set here
  export HOME="$d/home$RANDOM"; mkdir -p "$HOME"
  export LOOP_SCHEDULE_HOME="$HOME/sched" LOOP_AGENTS_DIR="$HOME/agents" LOOP_LAUNCHCTL="$here/dev/toy/fakegh/launchctl" LOOP_SCHEDULE_PROGRAM="$HEALTH/automation.py"
  export LOOP_SCHEDULE_PLATFORM=darwin LOOP_TEST=1 LOOP_INSTALLED_VERSION=1.0.0 FAKE_GH_PRIVATE=true
  export FAKE_GH_DIR="$HOME/gh"; mkdir -p "$FAKE_GH_DIR"; export PATH="$here/dev/toy/fakegh:$ORIG_PATH"
  unset LOOP_MIGRATION_ONLINE LOOP_REPO_VISIBILITY FAKE_GH_OFFLINE
}
adopt() {  # NAME: a toy repo set up fully, merged and pushed; prints its path
  "$here/dev/toy/make.sh" "$d/$1" >/dev/null || exit 1
  ( cd "$d/$1/repo" && mkdir -p engine && printf 'def run():\n    return 1\n' > engine/core.py && git add -A && git commit -qm code \
    && python3 "$SETUP/setup.py" >/dev/null 2>&1; git switch -q main; git merge -q --no-edit workflow-setup; git push -q origin main ) >/dev/null 2>&1
  echo "$d/$1/repo"
}
cfgset() {  # REPO PYTHON-STATEMENTS on d (the config dict): edit .loop/config.json
  ( cd "$1" && python3 -c "import json;p='.loop/config.json';d=json.load(open(p));$2;json.dump(d,open(p,'w'),indent=2)" )
}
checkout_apply() { ( cd "$1" && python3 "$SETUP/update.py" --apply 2>&1 ); }

# mac-kept: a public repo recorded regression_runs mac keeps it through a setup re-run (the owner's rule: public repos run
# regression on the Mac too), and the tick prints no DRIFT and fetches only origin/<base>, never a pull-request or fork ref.
if want mac-kept; then fresh; export FAKE_GH_PRIVATE=false
  r=$(adopt mk); cfgset "$r" "d['regression_runs']='mac'"; ( cd "$r" && git commit -qam "mac" && git push -q origin main )
  out=$(cd "$r" && python3 "$SETUP/setup.py" 2>&1); rc=$?
  check "a public toy recorded mac keeps regression_runs mac through a setup re-run" '[ $rc = 0 ] && grep -q "\"regression_runs\": \"mac\"" "$r/.loop/config.json" && ! git -C "$r" show workflow-setup:.loop/config.json 2>/dev/null | grep -q "\"regression_runs\": \"actions\""'
  ( cd "$r" && python3 "$HEALTH/automation.py" local install ) >/dev/null 2>&1
  out=$(cd "$r" && python3 "$HEALTH/automation.py" local tick --repo "$r" 2>&1)
  check "the tick prints no DRIFT for a public repo recorded mac and says it runs on the Mac" '! grep -q DRIFT <<<"$out" && grep -q "REGRESSION: runs on the Mac" <<<"$out"'
  out=$(grep -n '"fetch"' "$HEALTH/workflows.py"; grep -c 'refs/pull' "$HEALTH/workflows.py")
  check "the tick fetches only origin/<base> (no pull-request or fork ref is ever fetched or run)" 'grep -q "\"fetch\", \"origin\", base" <<<"$out" && [ "$(tail -1 <<<"$out")" = 0 ]'
fi

# base-config: update.py --check reads the base branch's config from origin/<base> first, never the checkout it is on.
if want base-config; then fresh
  r=$(adopt bc); cfgset "$r" "d.pop('template_version',None)"; ( cd "$r" && git commit -qam "no stamp" && git push -q origin main )
  U="python3 $SETUP/update.py"; word="^REPO: template_version"
  ( cd "$r" && git switch -q -c early main~3 )
  out=$(cd "$r" && $U --check 2>&1); check "from a branch cut before setup (no config in the checkout) it reports the base config" 'grep -q "$word" <<<"$out" && ! grep -q "no .loop/config.json" <<<"$out"'
  ( cd "$r" && git branch -q -D main )
  out=$(cd "$r" && $U --check 2>&1); check "with no local main branch at all it reads origin/main" 'grep -q "$word" <<<"$out" && ! grep -q "no .loop/config.json" <<<"$out"'
  git clone -q "$d/bc/origin.git" "$d/bc/clone" 2>/dev/null; ( cd "$d/bc/clone" && git switch -q -c work && git branch -q -D main )
  out=$(cd "$d/bc/clone" && $U --check 2>&1); check "from a fresh clone with only a work branch (origin/HEAD set) it reports the base config" 'grep -q "$word" <<<"$out"'
  "$here/dev/toy/make.sh" "$d/tr" >/dev/null; ( cd "$d/tr/repo" && git branch -q -m main trunk && git push -q origin trunk && git -C "$d/tr/origin.git" symbolic-ref HEAD refs/heads/trunk \
    && git push -q origin --delete main && git branch -q -u origin/trunk && python3 "$SETUP/setup.py" >/dev/null 2>&1; git switch -q trunk; git merge -q --no-edit workflow-setup; git push -q origin trunk; git switch -q -c side trunk ) >/dev/null 2>&1
  out=$(cd "$d/tr/repo" && git remote set-head origin -d >/dev/null 2>&1; $U --check 2>&1); check "a default branch that is neither main nor master, with origin/HEAD unset, reports from the checkout's own config" 'grep -q "$word" <<<"$out"'
  ( cd "$r" && git switch -q -c stale origin/main 2>/dev/null; git branch -q main origin/main~1 2>/dev/null )
  out=$(cd "$r" && $U --check 2>&1); check "a stale local main does not hide the newer origin/main config" 'grep -q "$word" <<<"$out"'
fi

# blocks-inserted: a repo adopted before v0.27.17 gets its Settings and Automation blocks and README line from update --apply.
if want blocks-inserted; then fresh
  r=$(adopt bi)
  python3 - "$r/README.md" "$r/docs/wiki/Home.md" <<'PY'
import re, sys
for path in sys.argv[1:]:
    text = open(path).read()
    open(path, "w").write(re.sub(r"\n*<!-- (settings|automation|template):begin -->\n.*?<!-- \1:end -->\n", "\n", text, flags=re.S))
PY
  cfgset "$r" "d.pop('template_version',None); d.pop('automation',None)"
  ( cd "$r" && git commit -qam "adopted before the blocks" && git push -q origin main )
  marks() { grep -c -e '<!-- settings:begin -->' -e '<!-- automation:begin -->' -e '<!-- template:begin -->' "$1" 2>/dev/null; }
  [ "$(marks "$r/README.md")" = 0 ] || { echo "FAIL: the strip left blocks in the README"; exit 1; }
  out=$(checkout_apply "$r"); br=$(cd "$r" && git branch --list 'workflow-update-*' | tr -d ' *'); readme=$(cd "$r" && git show "$br:README.md"); home=$(cd "$r" && git show "$br:docs/wiki/Home.md")
  check "update --apply inserts the Settings and Automation blocks and the template line into the README" 'grep -q "<!-- settings:begin -->" <<<"$readme" && grep -q "<!-- automation:begin -->" <<<"$readme" && grep -q "<!-- template:begin -->" <<<"$readme"'
  check "update --apply inserts the Settings and Automation blocks into Home" 'grep -q "<!-- settings:begin -->" <<<"$home" && grep -q "<!-- automation:begin -->" <<<"$home"'
  check "update --apply stamps template_version and declares the three routines" '( cd "$r" && git show "$br:.loop/config.json" | python3 -c "import json,sys; d=json.load(sys.stdin); assert d[\"template_version\"] and len(d[\"automation\"]) == 3" )'
fi

[ "$fails" = 0 ] && echo "ALL PASS" || { echo "$fails FAILED"; exit 1; }
