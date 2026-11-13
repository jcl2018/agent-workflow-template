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
  ( cd "$d/$1/repo" && python3 "$SETUP/setup.py" >/dev/null 2>&1; git switch -q main; git merge -q --no-edit workflow-setup; git push -q origin main ) >/dev/null 2>&1
  echo "$d/$1/repo"
}
cfgset() {  # REPO PYTHON-STATEMENTS on d (the config dict): edit .loop/config.json
  ( cd "$1" && python3 -c "import json;p='.loop/config.json';d=json.load(open(p));$2;json.dump(d,open(p,'w'),indent=2)" )
}

mig() {  # REPO [flags]: the check run in REPO; output on stdout and stderr, the exit code kept in $rc
  out=$(cd "$1" && python3 "$SETUP/setup.py" migration-check "${@:2}" 2>&1 < /dev/null); rc=$?
}
cleanrepo() {  # NAME [public]: an adopted toy repo that migration-check passes: recorded mac, stamped, blocks in, task registered, wiki published
  local r; r=$(adopt "$1")
  ( cd "$r" && python3 -c "import json;p='.loop/config.json';d=json.load(open(p));d['regression_runs']='mac';d['template_version']='1.0.0';json.dump(d,open(p,'w'),indent=2)" \
    && python3 "$SETUP/settings.py" fill-repo && git rm -q --ignore-unmatch .github/workflows/regression.yml && python3 "$DOCS/render.py" blocks && python3 "$DOCS/entry.py" write && python3 "$SETUP/agents.py" wire \
    && git add -A && git commit -qm "migrate" && git push -q origin main && python3 "$DOCS/docs.py" publish --adopt Home \
    && python3 "$HEALTH/automation.py" local install ) >/dev/null 2>&1
  echo "$r"
}
hold() { ( cd "$1" && git rev-parse HEAD ); }
reset() { ( cd "$1" && git reset -q --hard "$2" && git clean -fdq ); }
wikiedit() {  # REPO SHELL: clone the toy's bare wiki, run SHELL in the clone, push
  local w="$d/wikiclone$RANDOM"; git clone -q "$(dirname "$1")/origin.wiki.git" "$w" 2>/dev/null
  ( cd "$w" && git config user.email t@example.test && git config user.name Toy && eval "$2" && git add -A && git commit -qm edit && git push -q origin HEAD:main ) >/dev/null 2>&1; rm -rf "$w"
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

# clean: a clean private repo and a clean public repo, both recorded mac, pass: MIGRATION OK and exit 0.
if want clean; then fresh
  r=$(cleanrepo cl1); mig "$r"
  check "a clean private repo recorded mac, its task registered, passes with MIGRATION OK and exit 0" '[ $rc = 0 ] && tail -1 <<<"$out" | grep -qx "MIGRATION OK" && ! grep -q "^GAP" <<<"$out"'
  export FAKE_GH_PRIVATE=false; r2=$(cleanrepo cl2); mig "$r2"
  check "a clean public repo recorded mac passes the same way (public repos run regression on the Mac too)" '[ $rc = 0 ] && tail -1 <<<"$out" | grep -qx "MIGRATION OK"'
  check "the run names what it did not check and what it read" 'grep -q "^NOT CHECKED: branch protection (no gh read)" <<<"$out" && grep -q "^CHECKED: installed v1.0.0, repo template_version 1.0.0" <<<"$out" && grep -q "^DOCS: " <<<"$out"'
fi

# gaps-pr: each kind of gap a pull request can close is named by its code with a one-line fix.
if want gaps-pr; then fresh
  r=$(cleanrepo gp); base=$(hold "$r"); n=0
  gap() {  # CODE SUBJECT-PATTERN MUTATION-SHELL (run in the repo): the check names GAP CODE ... Fix: ...
    ( cd "$r" && eval "$3" ) >/dev/null 2>&1; mig "$r" --pr; n=$((n + 1))
    check "gap $n: $1 names $2" "[ \$rc = 1 ] && grep -qE '^GAP $1 .*$2.*Fix: .' <<<\"\$out\""; reset "$r" "$base"
  }
  cf() { echo "cd \"$r\" && python3 -c \"import json;p='.loop/config.json';d=json.load(open(p));$1;json.dump(d,open(p,'w'),indent=2)\""; }
  gap MIG_VERSION "template_version" "$(cf "d.pop('template_version')")"
  gap MIG_VERSION "older|behind" "$(cf "d['template_version']='0.0.5'")"
  gap MIG_VERSION "unparseable" "$(cf "d['template_version']='v1'")"
  gap MIG_VERSION "unparseable" "$(cf "d['template_version']=None")"
  gap MIG_SETTINGS "mend" "$(cf "d.pop('mend')")"
  gap MIG_SETTINGS "legacy_toy_key" "$(cf "d['legacy_toy_key']=1")"
  gap MIG_AUTOMATION "regression_runs" "$(cf "d['regression_runs']='actions'")"
  gap MIG_AUTOMATION "regression_runs" "$(cf "d.pop('regression_runs')")"
  gap MIG_AUTOMATION "health:" "$(cf "d['automation']=[]")"
  gap MIG_AUTOMATION "health_cron" "$(cf "d['health_cron']='off'")"
  gap MIG_AUTOMATION "health_cron" "$(cf "d['health_cron']='47 8 * * 1'")"
  gap MIG_FILES "START.md" "echo '- drift' >> .loop/START.md"
  gap MIG_FILES "queue.md" "rm .loop/queue.md"
  gap MIG_FILES "findings.md" "rm .loop/findings.md"
  gap MIG_FILES "regression.tsv" "rm .loop/regression.tsv"
  gap MIG_FILES "health.yml" "mkdir -p .github/workflows && printf 'name: health\non: schedule\n' > .github/workflows/health.yml"
  gap MIG_FILES "regression.yml" "mkdir -p .github/workflows && printf 'name: regression\non:\n  pull_request:\n' > .github/workflows/regression.yml"
  gap MIG_CHECKS "pull_request" "mkdir -p .github/workflows && printf 'name: regression\non:\n  schedule: []\n' > .github/workflows/regression.yml"
  gap MIG_CHECKS "land row" "printf '# id\tlevel\tcommand\tgoal\tseen_red\tdescription\tcategory\tlink\n' > .loop/regression.tsv"
  gap MIG_BLOCKS "README.md" "python3 - <<'PY'
import re
t = open('README.md').read()
open('README.md', 'w').write(re.sub(r'\n*<!-- (settings|automation|template):begin -->\n.*?<!-- \1:end -->\n', '\n', t, flags=re.S))
PY"
  gap MIG_BLOCKS "Home.md" "python3 - <<'PY'
import re
t = open('docs/wiki/Home.md').read()
open('docs/wiki/Home.md', 'w').write(re.sub(r'\n*<!-- (settings|automation):begin -->\n.*?<!-- \1:end -->\n', '\n', t, flags=re.S))
PY"
  gap MIG_RUNBOOK "Engine" "mkdir -p engine && echo x > engine/core.py && printf 'Engine\tengine\n' >> .loop/docs.tsv && printf '<!-- workflow-docs -->\n# Engine\n\nReview: **Unreviewed**\n\n## Problem\n\n- I run the toy engine, written for this test only.\n\n## Requirements\n\n### Functional\n\n- ENG-1: **Unreviewed** The engine runs.\n  - It holds for every toy run.\n\n### Non-functional\n\nNone\n\n## Non-goals\n\n- No other feature.\n\n## Success metrics\n\n- The toy run passes.\n\n## Tests\n\n' > docs/wiki/Engine.md && printf 'nightly-sync\tEngine\n' > .loop/routines.tsv"
  gap MIG_FORMAT "Home" "echo 'A line the Home page does not know about.' >> README.md && git commit -qam 'change the README without its page'"
  # regression off: no regression.yml, no land row, no mac needed, MIG_CHECKS skipped; the repo still passes the PR-closable half
  ( cd "$r" && eval "$(cf "d['regression_cron']='off'; d['regression_runs']='actions'")" && git rm -q --cached -r . >/dev/null 2>&1; git reset -q ) >/dev/null 2>&1
  ( cd "$r" && printf '# id\tlevel\tcommand\tgoal\tseen_red\tdescription\tcategory\tlink\n' > .loop/regression.tsv ); mig "$r" --pr
  check "regression off (regression_cron off, runs actions, no land row, no regression.yml): no regression gap, MIG_CHECKS skipped" '! grep -qE "^GAP MIG_(CHECKS|AUTOMATION) (regression|\.loop|regression_runs)" <<<"$out" && ! grep -q "^GAP MIG_CHECKS" <<<"$out"'
  reset "$r" "$base"
fi

# gaps-state: each kind of gap only the Mac or the wiki can close is named; the check lists and never deletes.
if want gaps-state; then fresh
  r=$(cleanrepo gs); base=$(hold "$r"); wiki="$d/gs/origin.wiki.git"
  reg() { python3 -c "import json,glob;p='$LOOP_SCHEDULE_HOME/repos.json';d=json.load(open(p));k=list(d['repos'])[0];$1;json.dump(d,open(p,'w'))"; }
  reg "d['repos'][k]['name']='someone-elses-task'"; mig "$r" --offline
  check "a task registered under another name is MIG_TASK, with the install fix" '[ $rc = 1 ] && grep -q "^GAP MIG_TASK .*registered task is named someone-elses-task.*Fix: .*local install" <<<"$out"'
  ( cd "$r" && python3 "$HEALTH/automation.py" local install ) >/dev/null 2>&1; reg "d['repos'][k]['cron']='47 */6 * * *'"; mig "$r" --offline
  check "a task that runs every 6 hours is MIG_TASK (4 hours or sooner is the rule)" '[ $rc = 1 ] && grep -q "^GAP MIG_TASK .*does not run every 4 hours or sooner" <<<"$out"'
  ( cd "$r" && python3 "$HEALTH/automation.py" local uninstall ) >/dev/null 2>&1; mig "$r" --offline
  check "no registered task is MIG_TASK" '[ $rc = 1 ] && grep -q "^GAP MIG_TASK .*no local task is registered.*Fix: .*local install" <<<"$out"'
  out=$(cd "$r" && LOOP_SCHEDULE_PLATFORM=linux python3 "$SETUP/setup.py" migration-check --offline 2>&1 < /dev/null); rc=$?
  check "off a Mac the task check prints SKIP MIG_TASK (not a Mac) and is not counted" '[ $rc = 0 ] && grep -qx "SKIP MIG_TASK (not a Mac)" <<<"$out" && ! grep -q "^GAP MIG_TASK" <<<"$out"'
  out=$(cd "$r" && LOOP_TEST= LOOP_SCHEDULE_PLATFORM=linux python3 "$SETUP/setup.py" migration-check --offline 2>&1 < /dev/null)
  check "the platform override is honoured only with LOOP_TEST=1, so a stray variable cannot hide a real gap" '[ "$(uname)" != Darwin ] || grep -q "^GAP MIG_TASK" <<<"$out"'
  ( cd "$r" && python3 "$HEALTH/automation.py" local install ) >/dev/null 2>&1
  cfgset "$r" "d['regression_cron']='off'"; mig "$r" --offline
  check "regression_cron off with health_cron on owes the task only (registered: no gap)" '! grep -q "^GAP MIG_TASK\|^GAP MIG_CHECKS" <<<"$out"'
  reset "$r" "$base"
  # the published wiki: a retired page marked by this tool, a hand-made one, and a page whose published text differs
  wikiedit "$r" "printf '<!-- workflow-docs -->\n# Retired\n\nold page\n' > Retired.md; printf 'hand made\n' > Notes.md; printf '# Other\n' > _Sidebar.md"
  mig "$r"
  check "a published page with no source page is MIG_WIKI_ORPHAN: a marked one with the git rm step, a hand-made one with the keep-or-remove line; _Sidebar is exempt" \
    '[ $rc = 1 ] && grep -q "^GAP MIG_WIKI_ORPHAN Retired.md: .*Fix: git clone .*git rm -- Retired.md" <<<"$out" && grep -q "^GAP MIG_WIKI_ORPHAN Notes.md: .*Fix: this tool did not write it: keep it" <<<"$out" && ! grep -q "_Sidebar" <<<"$out"'
  check "the orphan gap says owner only, after the merge, and that the removal is irreversible without the wiki history" 'grep "^GAP MIG_WIKI_ORPHAN Retired" <<<"$out" | grep -q "owner only, after the merge.*irreversible without the wiki"'
  check "the check lists and never deletes: the wiki still holds the orphan pages" '[ -n "$(git -C "$wiki" show main:Retired.md 2>/dev/null)" ]'
  wikiedit "$r" "git rm -q Retired.md Notes.md _Sidebar.md; printf 'someone edited this by hand\n' >> Home.md"
  mig "$r"
  check "a source page whose published text differs is MIG_WIKI_STALE, and the orphans are gone" '[ $rc = 1 ] && grep -q "^GAP MIG_WIKI_STALE Home: .*Fix: .*docs.py publish" <<<"$out" && ! grep -q "MIG_WIKI_ORPHAN" <<<"$out"'
  ( cd "$r" && python3 "$DOCS/docs.py" publish --adopt Home ) >/dev/null 2>&1; mig "$r"
  check "after a real docs.py publish into the bare wiki, zero stale and zero orphan (the comparison is publish's own)" '[ $rc = 0 ] && tail -1 <<<"$out" | grep -qx "MIGRATION OK"'
  # hostile names printed sanitized, never inside a runnable command; a page named --force.md; control characters
  wikiedit "$r" "printf x > 'a;b.md'; printf x > 'c\$(touch pwned).md'; printf x > -- '--force.md'; printf x > \$'line\nbreak.md'"
  mig "$r"
  check "hostile page names are printed without a runnable command and never executed" '[ $rc = 1 ] && ! grep -q "touch pwned" <<<"$(grep -v "^GAP MIG_WIKI_ORPHAN a;b" <<<"$out" | grep "git rm -- c")" && [ ! -e "$r/pwned" ] && grep -c "^GAP MIG_WIKI_ORPHAN" <<<"$out" | grep -q "^[1-9]"'
  check "a name starting with a dash, or holding a control character, gets the by-hand fix and no git rm line" '! grep -q "git rm -- --force" <<<"$out" && ! grep -q "git rm -- .*line" <<<"$out" && grep -q "remove it by hand" <<<"$out"'
  wikiedit "$r" "git rm -q -- a\;b.md c\*.md -- --force.md line*.md 2>/dev/null; git rm -q -f . 2>/dev/null; true"
  # an origin with no wiki repo, and an empty wiki: a note, never a gap
  mv "$wiki" "$d/gs/wiki.moved"; mig "$r"
  check "an origin with no wiki repo prints a note and is not a gap" 'grep -q "NOT CHECKED:.*no published wiki yet" <<<"$out" && ! grep -q "^GAP MIG_WIKI" <<<"$out"'
  mv "$d/gs/wiki.moved" "$wiki"; mkdir "$d/gs/empty.git" && git init -q --bare "$d/gs/empty.git" && mv "$wiki" "$d/gs/wiki.moved" && mv "$d/gs/empty.git" "$wiki"; mig "$r"
  check "an empty wiki prints the same note" 'grep -q "NOT CHECKED:.*no published wiki yet" <<<"$out" && ! grep -q "^GAP MIG_WIKI" <<<"$out"'
  rm -rf "$wiki"; mv "$d/gs/wiki.moved" "$wiki"
  # an unreadable wiki is a gap in the CLI (and an INFO row in health); an ext:: origin never runs a command
  ( cd "$r" && git remote set-url origin "https://127.0.0.1:9/o/r.git" ); mig "$r"
  check "an unreadable wiki (nothing listens at the origin) is MIG_WIKI_UNREADABLE with the cause and the retry fix, in under 30 s" '[ $rc = 1 ] && grep -q "^GAP MIG_WIKI_UNREADABLE wiki: can.t read .*Fix: check the origin and sign-in, then rerun; with no network pass --offline" <<<"$out"'
  ( cd "$r" && git remote set-url origin "ext::sh -c touch\ $d/pwned-ext" ); mig "$r"
  check "an ext:: origin gives MIG_WIKI_UNREADABLE and no command is run" '[ $rc = 1 ] && grep -q "^GAP MIG_WIKI_UNREADABLE" <<<"$out" && [ ! -e "$d/pwned-ext" ]'
  ( cd "$r" && git remote remove origin ); mig "$r"
  check "no origin remote: MIG_WIKI_UNREADABLE names it, nothing hangs" '[ $rc = 1 ] && grep -q "^GAP MIG_WIKI_UNREADABLE wiki: the repo has no origin remote" <<<"$out"'
  ( cd "$r" && git remote add origin "$d/gs/origin.git" )
  # a repo with no .loop/docs.tsv has no wiki, blocks, runbook or format codes
  ( cd "$r" && git rm -q .loop/docs.tsv ) >/dev/null 2>&1; mig "$r"
  check "no .loop/docs.tsv: no wiki, blocks, runbook or format code" '! grep -qE "^GAP MIG_(WIKI|BLOCKS|RUNBOOK|FORMAT)" <<<"$out"'
fi

# flags: --pr, --offline, --repo, exit codes and the lines every run carries.
if want flags; then fresh
  r=$(cleanrepo fl); wiki="$d/fl/origin.wiki.git"
  ( cd "$r" && python3 "$HEALTH/automation.py" local uninstall ) >/dev/null 2>&1; wikiedit "$r" "printf 'hand made\n' > Notes.md"
  mig "$r"; full=$out; fullrc=$rc
  check "the full run names the task and the orphan page (two state codes), exits 1, and its last line counts both classes" '[ $fullrc = 1 ] && grep -q "^GAP MIG_TASK" <<<"$full" && grep -q "^GAP MIG_WIKI_ORPHAN" <<<"$full" && tail -1 <<<"$full" | grep -q "^MIGRATION: 2 gap(s) (0 PR-closable, 2 state)$"'
  mig "$r" --pr
  check "--pr lists no state code, exits 0 when only state gaps remain, and its last line says the state codes were not checked" '[ $rc = 0 ] && ! grep -q "^GAP" <<<"$out" && tail -1 <<<"$out" | grep -qx "MIGRATION OK (--pr: state codes not checked)" && grep -q "^NOT CHECKED:.*state codes" <<<"$out"'
  mig "$r" --offline
  check "--offline drops exactly the wiki codes (the task gap stays) and its last line says the wiki was not checked" '[ $rc = 1 ] && grep -q "^GAP MIG_TASK" <<<"$out" && ! grep -q "MIG_WIKI" <<<"$out" && tail -1 <<<"$out" | grep -q "(offline: wiki not checked)$" && grep -q "^NOT CHECKED:.*wiki" <<<"$out"'
  mig "$r" --pr --offline; po=$out; mig "$r" --pr
  check "--pr with --offline is the same as --pr" '[ "$po" = "$out" ]'
  check "the CHECKED line names the versions, platform and mode, and the DOCS line is present" 'grep -q "^CHECKED: installed v1.0.0, repo template_version 1.0.0 (working tree), platform darwin, mode offline" <<<"$out" && grep -q "^DOCS: " <<<"$out"'
  mig "$r" --bogus
  check "an unknown flag exits 2 with the fix on stderr" '[ $rc = 2 ] && grep -q "Fix: run setup.py migration-check --help" <<<"$out"'
  out=$(cd "$d" && python3 "$SETUP/setup.py" migration-check --repo "$d" 2>&1 < /dev/null); rc=$?
  check "--repo that is not a git repo exits 2" '[ $rc = 2 ] && grep -q "not a git repo" <<<"$out"'
  out=$(cd "$d" && python3 "$SETUP/setup.py" migration-check --repo "$r" --pr 2>&1 < /dev/null); rc=$?
  check "--repo runs the check against another directory" '[ $rc = 0 ] && grep -q "MIGRATION OK" <<<"$out"'
  # a missing workflow-health, and an unexpected exception: exit 4, never a traceback, never exit 1
  rm -rf "$d/sk2" "$d/sk3"; cp -R "$S" "$d/sk2"; cp -R "$S" "$d/sk3"; rm -rf "$d/sk2/workflow-health"
  out=$(cd "$r" && python3 "$d/sk2/workflow-setup/scripts/setup.py" migration-check 2>&1 < /dev/null); rc=$?
  check "workflow-health missing beside workflow-setup: REFUSED with the fix and exit 4 (could not run)" '[ $rc = 4 ] && grep -q "^REFUSED: workflow-health is not installed beside workflow-setup; nothing was changed. Fix: install" <<<"$out"'
  printf 'raise RuntimeError("boom")\n' > "$d/sk3/workflow-docs/scripts/entry.py"
  out=$(cd "$r" && python3 "$d/sk3/workflow-setup/scripts/setup.py" migration-check --offline 2>&1 < /dev/null); rc=$?
  trace=$(sed -n 's/.*see \(\/[^;]*\);.*/\1/p' <<<"$out")
  check "an unexpected exception exits 4 with one line naming a private trace file, and no traceback on screen" '[ $rc = 4 ] && grep -q "^INTERNAL ERROR (MIG_INTERNAL): see .*; nothing was changed" <<<"$out" && ! grep -q Traceback <<<"$out" && grep -q boom "$trace"'
  rm -f "$trace"
  # a wiki URL with credentials never reaches stdout, stderr or a health row
  ( cd "$r" && git remote set-url origin "https://user:s3cr3tvalue@127.0.0.1:9/o/r.git" ); mig "$r"
  health=$(cd "$r" && LOOP_MIGRATION_ONLINE=1 python3 "$HEALTH/health.py" check --group adoption 2>&1 < /dev/null)
  check "a credential in the origin URL (user:token@) never appears in the output or in a health row" '! grep -q s3cr3tvalue <<<"$out" && ! grep -q s3cr3tvalue <<<"$health" && grep -q "MIG_WIKI_UNREADABLE" <<<"$out"'
  check "an unreadable wiki is an INFO row in health, never a warning or a crash" 'grep -q "^INFO adoption MIG_WIKI_UNREADABLE wiki migration" <<<"$health"'
  ( cd "$r" && git remote set-url origin "$d/fl/origin.git" )
  # a clone that hangs is killed at 30 s with its whole process group: a fake git sleeps on clone
  mkdir -p "$d/fakegit"; printf '#!/bin/bash\nfor a in "$@"; do [ "$a" = clone ] && { sleep 60; exit 0; }; done\nexec %s "$@"\n' "$(command -v git)" > "$d/fakegit/git"; chmod +x "$d/fakegit/git"
  t0=$(date +%s); out=$(cd "$r" && PATH="$d/fakegit:$PATH" python3 "$SETUP/setup.py" migration-check 2>&1 < /dev/null); rc=$?; t1=$(date +%s)
  check "a clone that hangs is cut at 30 s: MIG_WIKI_UNREADABLE says it timed out and the run ends soon after" '[ $rc = 1 ] && grep -q "^GAP MIG_WIKI_UNREADABLE wiki: timed out after 30 s" <<<"$out" && [ $((t1 - t0)) -lt 45 ] && ! ls "${TMPDIR:-/tmp}"/migration-wiki-* >/dev/null 2>&1'
fi

# writes-nothing: the check changes no file, index, branch, stash, home folder or registry, and removes its wiki clone.
if want writes-nothing; then fresh
  r=$(cleanrepo wn); ( cd "$r" && git stash list >/dev/null ); wikiedit "$r" "printf 'hand made\n' > Notes.md"; export TMPDIR="$d/tmp"; mkdir -p "$TMPDIR"
  cfgset "$r" "d['legacy_toy_key']=1"; printf 'scratch\n' > "$r/untracked.txt"
  state() {  # the repo's whole tree and git state, the home folder and the schedule registry, as one text
    ( cd "$1" && git status --porcelain --ignored; git ls-files -s; git for-each-ref; git stash list; git worktree list; find . -path ./.git -prune -o -type f -print0 | sort -z | xargs -0 shasum; find .git -type f -not -name '*.lock' | sort | xargs shasum 2>/dev/null | grep -v "index$"; find "$HOME" -type f | sort | xargs shasum 2>/dev/null; ls "$TMPDIR" )
  }
  before=$(state "$r"); mig "$r"; after=$(state "$r")
  check "a full online run with gaps leaves the tree, index, branches, stash, .git files, home folder and temp folder as they were" '[ $rc = 1 ] && [ "$before" = "$after" ]'
  check "the wiki clone's temp folder is gone after the run" '[ -z "$(ls "$TMPDIR" 2>/dev/null)" ]'
  mig "$r" --pr; mig "$r" --offline; after2=$(state "$r")
  check "--pr and --offline write nothing either" '[ "$before" = "$after2" ]'
fi

# health-same: health's Adoption group runs the same check; WARN rows never turn the verdict red; the tick files them as issues.
if want health-same; then fresh
  r=$(cleanrepo hs); cfgset "$r" "d.pop('template_version'); d['legacy_toy_key']=1"
  mig "$r" --offline; cli=$(grep -o "^GAP MIG_[A-Z_]*" <<<"$out" | sort -u | sed 's/GAP //' | tr '\n' ' ')
  health=$(cd "$r" && python3 "$HEALTH/health.py" check --group adoption 2>&1 < /dev/null)
  rows=$(grep -o " MIG_[A-Z_]* " <<<"$(grep '^WARN adoption MIG_' <<<"$health" | awk '{print $3}' | sed 's/^/ /;s/$/ /')" | tr -d ' ' | sort -u | tr '\n' ' ')
  check "health's Adoption group prints the same codes through the migration rule (MIG_VERSION through the template-version row)" '[ "$cli" = "MIG_FILES MIG_SETTINGS MIG_VERSION " ] || [ "$cli" = "MIG_FILES MIG_VERSION MIG_SETTINGS " ] || [ "${cli%%MIG_VERSION*}" != "$cli" ]; for c in $cli; do case $c in MIG_VERSION) grep -q "^WARN adoption template_version template-version.*MIG_VERSION" <<<"$health";; *) grep -q "^WARN adoption $c .* migration" <<<"$health";; esac || exit 1; done'
  check "health reports the mode in each migration row and says what it did not check" 'grep "^WARN adoption MIG_" <<<"$health" | grep -q "\[offline\]" && grep -q "^INFO adoption migration migration: not checked here: the published wiki (offline)" <<<"$health"'
  check "WARN rows never turn the health verdict red" 'grep -q "^HEALTH: green" <<<"$health"'
  out=$(cd "$r" && python3 "$HEALTH/health.py" preview --group adoption 2>&1 < /dev/null)
  check "health preview shows WOULD open for the template-version row and for a migration row (the 4-hourly run files both)" 'grep -q "WOULD open issue .health: adoption template_version template-version" <<<"$out" && grep -q "WOULD open issue .health: adoption MIG_" <<<"$out"'
  health=$(cd "$r" && python3 "$HEALTH/health.py" check --group controls 2>&1 < /dev/null)
  check "the migration rule has a negative control that fires" 'grep -q "^PASS controls migration control: fires on its fixture" <<<"$health"'
fi

# robustness: odd trees, odd files and two runs at once end as named gaps or notes, never a traceback, never a leftover temp folder.
if want robustness; then fresh
  r=$(cleanrepo rb); base=$(hold "$r"); export TMPDIR="$d/tmp2"; mkdir -p "$TMPDIR"
  sane() { [ "$rc" != 4 ] && ! grep -q Traceback <<<"$out" && tail -1 <<<"$out" | grep -q "^MIGRATION"; }
  ( cd "$r" && git worktree add -q --detach "$d/rb/wt" HEAD ); mig "$d/rb/wt" --offline
  check "a linked worktree on a detached HEAD (where .git is a file) is checked like the main tree" 'sane && [ $rc = 0 ]'
  out=$(cd "$r/.loop" && python3 "$SETUP/setup.py" migration-check --offline 2>&1 < /dev/null); rc=$?
  check "run from a subdirectory it checks the whole repo" 'sane && [ $rc = 0 ]'
  rm "$r/.loop/config.json"; mig "$r" --offline
  check "a missing .loop/config.json is a named gap, not a crash" 'sane && grep -q "^GAP MIG_SETTINGS .loop/config.json: is missing or not valid JSON" <<<"$out"'
  reset "$r" "$base"; printf '{not json' > "$r/.loop/config.json"; mig "$r" --offline
  check "a malformed .loop/config.json is the same named gap" 'sane && grep -q "^GAP MIG_SETTINGS .loop/config.json: is missing or not valid JSON" <<<"$out"'
  reset "$r" "$base"; printf '\xff\xfe\x00bad\n' > "$r/.loop/regression.tsv"; mig "$r" --offline
  check "a corrupt regression.tsv is handled (a land-row gap, no crash)" 'sane'
  reset "$r" "$base"; printf '\xff\xfe\x00bad\n' > "$r/.loop/docs.tsv"; mig "$r" --offline
  check "an unparseable .loop/docs.tsv is handled (no crash)" 'sane'
  reset "$r" "$base"; wikiedit "$r" "printf x > 'é.md'"; mig "$r"
  check "a page named with a non-ASCII character is listed as unprintable with the by-hand fix and no command" 'sane && grep -q "^GAP MIG_WIKI_ORPHAN (a page whose name this check will not print).*Fix: remove it by hand" <<<"$out"'
  ( mig "$r" --offline; echo "$out" > "$d/rb/o1" ) & ( out=$(cd "$r" && python3 "$SETUP/setup.py" migration-check 2>&1 < /dev/null); echo "$out" > "$d/rb/o2" ) & wait
  check "two runs at once both finish with a verdict, and no temp folder is left" 'tail -1 "$d/rb/o1" | grep -q "^MIGRATION" && tail -1 "$d/rb/o2" | grep -q "^MIGRATION" && [ -z "$(ls "$TMPDIR" 2>/dev/null)" ]'
fi

# lag-line: entry.py lag prints the one line when a repo is behind the installed template, and the version table governs it.
if want lag-line; then fresh
  r=$(cleanrepo ll); L="python3 $DOCS/entry.py lag --repo $r"
  line="this repo is at v1.0.0, the template is at v1.2.3, run the migrate goal (slug migrate-repo)"
  rm -rf "$d/inst"; cp -R "$S" "$d/inst"; echo '{"version": "1.2.3"}' > "$d/inst/workflow-package.json"
  out=$(LOOP_TEST= LOOP_INSTALLED_VERSION= python3 "$d/inst/workflow-docs/scripts/entry.py" lag --repo "$r" 2>&1); rc=$?
  check "through a fake install folder (workflow-package.json) the exact line is printed, exit 0" '[ $rc = 0 ] && [ "$out" = "$line" ]'
  out=$(LOOP_INSTALLED_VERSION=1.2.3 $L 2>&1)
  check "through the test override (LOOP_TEST=1) the same line is printed" '[ "$out" = "$line" ]'
  out=$(LOOP_TEST= LOOP_INSTALLED_VERSION=9.9.9 $L 2>&1)
  check "the override is ignored without LOOP_TEST=1" '[ -z "$out" ]'
  mig_pr() { out=$(cd "$r" && LOOP_TEST= LOOP_INSTALLED_VERSION= python3 "$d/inst/workflow-setup/scripts/setup.py" migration-check --pr 2>&1 < /dev/null); rc=$?; }
  mig_pr
  check "MIG_VERSION is exercised through the real resolver too: v1.0.0 is behind the fake install at v1.2.3" '[ $rc = 1 ] && grep -q "^GAP MIG_VERSION template_version: v1.0.0 is behind the template at v1.2.3" <<<"$out"'
  out=$(cd "$here" && python3 "$DOCS/entry.py" lag 2>&1); rc=$?
  check "in a tree that holds the skills there is no installed version to be behind: nothing printed" '[ $rc = 0 ] && [ -z "$out" ]'
  mig "$here" --pr --offline
  check "and MIG_VERSION never fires there" '! grep -q "MIG_VERSION" <<<"$out"'
  v() {  # JSON-VALUE-OF-template_version-or-ABSENT EXPECT(line|none) [--new SLUG EXPECTED-EXIT]: the version table
    local t="$d/vt$RANDOM"; VT="$t"; mkdir -p "$t/.loop"; if [ "$1" = ABSENT ]; then echo '{}' > "$t/.loop/config.json"; else echo "{\"template_version\": $1}" > "$t/.loop/config.json"; fi
    got=$(LOOP_INSTALLED_VERSION=1.2.3 python3 "$DOCS/entry.py" lag --repo "$t" ${3:+--new $3} 2>&1); grc=$?
  }
  v ABSENT; check "version absent: behind (read as v0), never refused" '[ "$got" != "" ] && [ $grc = 0 ] && grep -q "this repo is at v0, the template is at v1.2.3" <<<"$got"'
  v '"v1"'; check "version v1 (unparseable): behind, never refused" '[ $grc = 0 ] && grep -q "this repo is at v0" <<<"$got"'
  v null; check "version null: behind, never refused" '[ $grc = 0 ] && grep -q "this repo is at v0" <<<"$got"'
  v '"1.2"'; check "version 1.2 (two numbers): unparseable, behind, never refused" '[ $grc = 0 ] && grep -q "this repo is at v0" <<<"$got"'
  v '"1.0.0"'; check "version older, same major: one warning line, exit 0" '[ $grc = 0 ] && grep -q "this repo is at v1.0.0, the template is at v1.2.3" <<<"$got"'
  v '"1.2.3"'; check "version equal: nothing" '[ $grc = 0 ] && [ -z "$got" ]'
  v '"1.9.0"'; check "version newer than installed: nothing (repo ahead)" '[ $grc = 0 ] && [ -z "$got" ]'
  v '"0.9.0"' "" ; v '"0.9.0"' x; got=$(LOOP_INSTALLED_VERSION=1.2.3 python3 "$DOCS/entry.py" lag --repo "$VT" --new some-goal 2>&1); grc=$?
  check "a differing major refuses a new goal: exit 3 and REFUSED with the fix" '[ $grc = 3 ] && grep -q "^REFUSED: this repo is at v0.9.0 and the template at v1.2.3 (different major). Fix: start it as a migrate-.* goal; nothing was changed" <<<"$got"'
  got=$(LOOP_INSTALLED_VERSION=1.2.3 python3 "$DOCS/entry.py" lag --repo "$VT" --new migrate-app 2>&1); grc=$?
  check "a migrate- slug passes a differing major (the migration is its own way out)" '[ $grc = 0 ] && grep -q "run the migrate goal" <<<"$got"'
fi

# major-refused: goal.py new warns and never blocks, refuses a differing major with exit 2 and no goal state, and lets migrate- slugs through.
if want major-refused; then fresh
  r=$(cleanrepo mr); export LOOP_FLOW="$d/mr/flow.json" LOOP_ROLE=worker; G="python3 $S/workflow-delivery/scripts/goal.py"
  C=$(cd "$r" && cd "$(git rev-parse --git-common-dir)" && pwd)
  out=$(cd "$r" && LOOP_INSTALLED_VERSION=2.0.0 $G new wrongmajor --here --goal "g" --done "d" 2>&1 < /dev/null); rc=$?
  check "goal.py new refuses a differing major with exit 2, prints the recovery line, and creates no goal state or branch" '[ $rc = 2 ] && grep -q "REFUSED: this repo is at v1.0.0 and the template at v2.0.0 (different major). Fix: start it as a migrate-" <<<"$out" && [ ! -e "$C/loop/runs/wrongmajor.json" ] && [ -z "$(git -C "$r" branch --list loop/wrongmajor)" ]'
  out=$(cd "$r" && LOOP_INSTALLED_VERSION=2.0.0 $G new migrate-mr --here --goal "g" --done "d" 2>&1 < /dev/null); rc=$?
  check "a migrate- slug is let through a differing major (it prints the version line and freezes the goal)" '[ $rc = 0 ] && grep -q "^this repo is at v1.0.0, the template is at v2.0.0, run the migrate goal" <<<"$out" && grep -q "^FROZEN migrate-mr" <<<"$out"'
  ( cd "$r" && git switch -q main )
  out=$(cd "$r" && LOOP_INSTALLED_VERSION=1.5.0 $G new warned --here --goal "g" --done "d" 2>&1 < /dev/null); rc=$?
  check "an older repo of the same major only gets the warning line: the goal is created" '[ $rc = 0 ] && grep -q "^this repo is at v1.0.0, the template is at v1.5.0, run the migrate goal" <<<"$out" && grep -q "^FROZEN warned" <<<"$out"'
  ( cd "$r" && git switch -q main ); rm -rf "$d/sk4"; cp -R "$S" "$d/sk4"; rm -rf "$d/sk4/workflow-docs"
  out=$(cd "$r" && python3 "$d/sk4/workflow-delivery/scripts/goal.py" new nonag --here --goal "g" --done "d" 2>&1 < /dev/null); rc=$?
  check "with entry.py missing it prints a NOTE on stderr and never blocks" '[ $rc = 0 ] && grep -q "^NOTE: entry.py not found beside workflow-delivery, so the template version was not checked. Fix: reinstall the skills from one release" <<<"$out" && grep -q "^FROZEN nonag" <<<"$out"'
fi

# queue: the operation session queues one migrate-<repo> goal for each followed repo behind the template, once, in a safe place.
if want queue; then fresh
  want_v=$(cat "$here/VERSION")  # the baseline of a checkout is its VERSION
  mkq() {  # NAME [template_version]: a set-up toy repo folder named NAME, on main, stamped
    "$here/dev/toy/make.sh" "$d/q$1" >/dev/null || exit 1; mkdir -p "$d/qq"; mv "$d/q$1/repo" "$d/qq/$1"; cp "$d/q$1/flow.json" "$d/qq/flow-$1.json" 2>/dev/null
    ( cd "$d/qq/$1" && python3 "$SETUP/setup.py" >/dev/null 2>&1; git switch -q main; git merge -q --no-edit workflow-setup
      python3 -c "import json;p='.loop/config.json';d=json.load(open(p));d['template_version']='${2:-0.0.1}';json.dump(d,open(p,'w'),indent=2)" && git commit -qam stamp && git push -q origin main ) >/dev/null 2>&1
  }
  mkq app; mkq app.v2; mkq app-api; mkq current "$want_v"; export LOOP_FLOW="$d/qq/flow-app.json"
  mkdir -p "$HOME/.workflow-loop"; printf '%s\n' "$d/qq/app.v2" "$d/qq/app-api" "$d/qq/current" > "$HOME/.workflow-loop/repos"
  pass() { out=$(cd "$d/qq/app" && python3 "$S/workflow-monitoring/scripts/board_page.py" migrate 2>&1 < /dev/null); }
  queue_of() { cat "$d/qq/$1/.loop/queue.md" 2>/dev/null; }
  nomig() { ! grep -q "slug: migrate-" "$d/qq/$1/.loop/queue.md" 2>/dev/null; }
  pass
  check "repos app, app.v2 and app-api, all behind, each get exactly their own migrate- line (no slug matches another repo's)" 'grep -c "^- slug: migrate-app |" <<<"$(queue_of app)" | grep -qx 1 && grep -c "slug: migrate-" <<<"$(queue_of app)" | grep -qx 1 && grep -q "^- slug: migrate-app-v2 |" <<<"$(queue_of app.v2)" && grep -c "slug: migrate-" <<<"$(queue_of app.v2)" | grep -qx 1 && grep -q "^- slug: migrate-app-api |" <<<"$(queue_of app-api)"'
  check "a repo that is current is left alone" 'nomig current'
  check "the queued goal has one done line, the pull-request check, and states both halves" 'grep "^- slug: migrate-app |" "$d/qq/app/.loop/queue.md" | grep -q "done: setup.py migration-check --pr exits 0" && grep "slug: migrate-app |" "$d/qq/app/.loop/queue.md" | grep -q "the owner then closes the Mac and wiki gaps and runs the full migration-check"'
  pass; check "a second pass queues nothing more and prints no guard complaint (the queued slug is found before the guard is read)" '[ "$(grep -c "slug: migrate-" "$d/qq/app/.loop/queue.md")" = 1 ] && [ -z "$out" ]'
  # the state table: a finished goal for this version is an Issues line; a finished one for an older version allows the suffixed slug
  git -C "$d/qq/app" checkout -q -- .loop/queue.md; C=$(cd "$d/qq/app" && cd "$(git rev-parse --git-common-dir)" && pwd); mkdir -p "$C/loop/runs"
  printf '{"slug": "migrate-app", "status": "merged", "goal": "Migrate app to template v%s: x"}\n' "$want_v" > "$C/loop/runs/migrate-app.json"; pass
  check "a finished migrate goal for this version with the repo still behind is an Issues line, not requeued" 'grep -q "^- app: migrate goal for v$want_v finished, repo still behind" <<<"$out" && nomig app'
  printf '{"slug": "migrate-app", "status": "merged", "goal": "Migrate app to template v0.0.9: x"}\n' > "$C/loop/runs/migrate-app.json"; pass
  check "a finished one for an older version allows the version-suffixed slug" 'grep -q "^- slug: migrate-app-v$(tr . - <<<"$want_v") |" "$d/qq/app/.loop/queue.md"'
  git -C "$d/qq/app" checkout -q -- .loop/queue.md; printf '{"slug": "migrate-app", "status": "running", "goal": "Migrate app"}\n' > "$C/loop/runs/migrate-app.json"; pass
  check "a running or waiting migrate goal skips the repo" 'nomig app && [ -z "$out" ]'
  rm -f "$C/loop/runs/migrate-app.json"
  # where it will not write: a checkout on another branch, a modified queue file
  git -C "$d/qq/app-api" checkout -q -- .loop/queue.md; git -C "$d/qq/app-api" switch -q -c side; pass
  check "a followed repo on another branch gets an Issues line saying why nothing was queued" 'grep -q "^- app-api: behind v$want_v, nothing was queued: its checkout is not on main" <<<"$out" && nomig app-api'
  git -C "$d/qq/app-api" switch -q main; printf '\n' >> "$d/qq/app-api/.loop/queue.md"; pass
  check "a modified queue file gets an Issues line and the file is left as it was" 'grep -q "^- app-api: behind v$want_v, nothing was queued: .loop/queue.md has uncommitted changes" <<<"$out" && ! grep -q "slug: migrate-app-api" "$d/qq/app-api/.loop/queue.md"'
  git -C "$d/qq/app-api" checkout -q -- .loop/queue.md
  # two passes at once queue one line
  ( cd "$d/qq/app-api" && python3 "$S/workflow-monitoring/scripts/board_page.py" migrate >/dev/null 2>&1 < /dev/null ) & sleep 0.4
  ( cd "$d/qq/app-api" && python3 "$S/workflow-monitoring/scripts/board_page.py" migrate >/dev/null 2>&1 < /dev/null ) & wait
  check "two passes at once queue exactly one migrate line" '[ "$(grep -c "slug: migrate-app-api" "$d/qq/app-api/.loop/queue.md")" = 1 ]'
  check "the lag text for the board is unchanged: a stamped-old repo prints its two Issues lines" 'out=$(cd "$d/qq/app" && python3 "$S/workflow-monitoring/scripts/board_page.py" lag); grep -q "^- app runs template v0.0.1, older than v$want_v" <<<"$out" && grep -q "^    fix: ask for workflow-setup update in that repo" <<<"$out"'
fi

# fix-sched-task (#3780): a Mac's per-repo scheduled task <repo>-health-regression counts as the local task
if want fix-sched-task; then fresh
  r=$(cleanrepo fx); label=$(python3 -c "import sys;sys.path.insert(0,'$HEALTH');import workflows;print(workflows.task_name('$r'))")
  ( cd "$r" && python3 "$HEALTH/automation.py" local uninstall ) >/dev/null 2>&1; mig "$r" --offline
  check "with no registered task and no scheduled task folder the task gap stays" '[ $rc = 1 ] && grep -q "^GAP MIG_TASK" <<<"$out"'
  mkdir -p "$HOME/tasks/$label"; export LOOP_SCHEDULED_TASKS_DIR="$HOME/tasks"; mig "$r" --offline
  check "a scheduled task folder named <repo>-health-regression is no MIG_TASK gap" '! grep -q "^GAP MIG_TASK" <<<"$out"'
  unset LOOP_SCHEDULED_TASKS_DIR
fi

# fix-mac-no-yml (#3780): a regression_runs mac repo is not asked for pull_request in regression.yml
if want fix-mac-no-yml; then fresh
  r=$(cleanrepo fy)
  ( cd "$r" && mkdir -p .github/workflows && printf 'name: regression
on:
  schedule: []
' > .github/workflows/regression.yml ); mig "$r" --offline
  check "a regression_runs mac repo whose regression.yml has no pull_request is asked nothing" '! grep -q "^GAP MIG_CHECKS" <<<"$out"'
  cfgset "$r" "d['regression_runs']='actions'"; mig "$r" --offline
  check "a regression_runs actions repo is still asked for pull_request" '[ $rc = 1 ] && grep -q "^GAP MIG_CHECKS .*pull_request" <<<"$out"'
fi

# v1: the format changes and the owner steps (migration-v1). A repo missing a feature the template carries is named with its code and fix and
# exits 1; with every feature present it exits 0, and what only the owner can do prints as OWNER STEP with its instruction (never a gap).
if want v1; then fresh
  r=$(cleanrepo v1)
  export LOOP_TEMPLATE_HAS=usage-kept; mig "$r" --offline
  check "a clean toy whose template carries no new feature exits 0 and prints no new gap" '[ $rc = 0 ] && ! grep -qE "^GAP MIG_(USAGE|RULES|ROUTINES|HOOKS)" <<<"$out"'
  check "the clean toy still lists what only the owner can do, as OWNER STEP lines with their instruction" 'grep -q "^OWNER STEP hook reply_hook.py: run .*--reply-hook" <<<"$out" && grep -q "^CHECKLIST: " <<<"$out"'
  export LOOP_TEMPLATE_HAS=usage-kept,health-rules; mig "$r" --offline
  check "a template that carries .loop/health-rules.json: its absence is a gap with its fix, exit 1" '[ $rc = 1 ] && grep -q "^GAP MIG_RULES .loop/health-rules.json: missing. Fix: run workflow-setup" <<<"$out"'
  echo "{}" > "$r/.loop/health-rules.json"; mig "$r" --offline
  check "with .loop/health-rules.json present the gap is gone and the check exits 0" '[ $rc = 0 ] && ! grep -q "MIG_RULES" <<<"$out"'
  export LOOP_TEMPLATE_HAS=""; page="$r/docs/wiki/Calc.md"
  { echo "# Calc"; echo; echo "## Usage"; echo; echo "- a command"; } > "$page"; mig "$r" --offline
  check "a template that dropped Usage: a feature page still holding a Usage section is a gap naming the page, exit 1" '[ $rc = 1 ] && grep -q "^GAP MIG_USAGE $(basename "$page"): still has a Usage section" <<<"$out"'
  export LOOP_TEMPLATE_HAS=usage-kept,runbook-pointer; reset "$r" HEAD
  cfgset "$r" "d['automation']=[{'name':'health','runs':'x','prompt':'do a long thing'+chr(10)+'over two lines'}]"; mig "$r" --offline
  check "a template with Runbook-pointer prompts: a two-line routine prompt is a MIG_ROUTINES gap, exit 1" '[ $rc = 1 ] && grep -q "^GAP MIG_ROUTINES health: its prompt is not a one-line Runbook pointer" <<<"$out"'
  reset "$r" HEAD; export LOOP_TEMPLATE_HAS=usage-kept,backlog; mig "$r" --offline
  check "a template with the Backlog milestones: the approval is an OWNER STEP that does not fail the check" '[ $rc = 0 ] && grep -q "^OWNER STEP milestones Backlog: approve the Backlog milestones" <<<"$out"'
  export LOOP_TEMPLATE_HAS=usage-kept; mkdir -p "$r/.claude"; printf '{"hooks":{"Stop":[{"command":"reply_hook.py"},{"command":"reply_hook.py"}]}}' > "$r/.claude/settings.local.json"; mig "$r" --offline
  check "a hook installed twice is a MIG_HOOKS gap with its fix, exit 1; govern_hook.py not installed is an OWNER STEP" '[ $rc = 1 ] && grep -q "^GAP MIG_HOOKS reply_hook.py: is installed 2 times" <<<"$out" && grep -q "^OWNER STEP hook govern_hook.py" <<<"$out"'
  mig "$r" --offline --pr
  check "--pr (the gaps a pull request can close) prints no hook gap or owner step" '! grep -qE "MIG_HOOKS|^OWNER STEP" <<<"$out"'
  unset LOOP_TEMPLATE_HAS
fi

[ "$fails" = 0 ] && echo "ALL PASS" || { echo "$fails FAILED"; exit 1; }
