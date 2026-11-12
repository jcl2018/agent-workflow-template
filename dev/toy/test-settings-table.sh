#!/bin/bash
# reads: skills/workflow-docs/scripts/criteria.py skills/workflow-docs/scripts/docs.py skills/workflow-docs/scripts/entry.py
# reads: skills/workflow-docs/scripts/pageformat.py skills/workflow-docs/scripts/render.py
# reads: skills/workflow-docs/scripts/prd.py skills/workflow-docs/scripts/counting.py
# reads: skills/workflow-docs/references/template.md skills/workflow-health/scripts/judge.py
# reads: skills/workflow-regression/scripts/regression.py skills/workflow-regression/scripts/tests.py
# reads: skills/workflow-setup/scripts/setup.py skills/workflow-setup/scripts/settings.py
# Test the Settings and Automation blocks on Home and the README: one overridden setting shows exactly that one marked, the
# README names and links the template repo with no local path, a changed setting makes check say STALE and render or publish
# refresh it, Automation shows on or off, cadence words and where it runs, START.md names the sections. usage: test-settings-table.sh [DIR]
set -u
unset LOOP_SESSION_TOOL LOOP_OPERATION_SESSION LOOP_BATCH  # a toy test never reaches a real session tool
unset GITHUB_SERVER_URL GITHUB_REPOSITORY GITHUB_RUN_ID
here=$(cd "$(dirname "$0")/../.." && pwd)
. "$here/dev/toy/reap.sh"
export HOME=$(mktemp -d)  # setup.py writes the private settings under HOME
export LOOP_OWNER_WORDS='"review it" (the toy owner)'  # review --user with no terminal needs the owner's words
d=${1:-$(mktemp -d)}; rm -rf "$d"; mkdir -p "$d"
"$here/dev/toy/make.sh" "$d" >/dev/null || exit 1
export LOOP_FLOW="$d/flow.json" PATH="$here/dev/toy/fakegh:$PATH" FAKE_GH_DIR="$d/gh" PYTHONDONTWRITEBYTECODE=1
unset GH_TOKEN GITHUB_TOKEN
docs="python3 $here/skills/workflow-docs/scripts/docs.py"
cri="python3 $here/skills/workflow-docs/scripts/criteria.py"
prd="python3 $here/skills/workflow-docs/scripts/prd.py"
reg="python3 $here/skills/workflow-regression/scripts/regression.py"
cd "$d/repo" || exit 1
python3 "$here/skills/workflow-setup/scripts/setup.py" --bare >/dev/null
git switch -q main; git merge -q --no-edit workflow-setup
python3 -c "import json; c = json.load(open('.loop/config.json')); c['criteria'] = True; c.pop('criteria_max', None); json.dump(c, open('.loop/config.json', 'w'), indent=2)"
mkdir -p "$FAKE_GH_DIR" docs/wiki skills/toy
printf '## Command map\n\n| Ask | Runs |\n|---|---|\n| `/toy median LIST` | `python3 scripts/calc.py median LIST` |\n' > skills/toy/SKILL.md
printf 'Delivery\tcalc.py\nHome\tREADME.md\n' > .loop/docs.tsv
fails=0
ok() { echo "PASS: $1"; }
bad() { echo "FAIL: $1"; fails=$((fails + 1)); }
printf '<!-- workflow-docs -->\n# Toy\n\n## Features\n\n| Feature | What it does | How to use | Milestone |\n|---|---|---|---|\n' > docs/wiki/Home.md
printf '# Toy\n\nA toy repo.\n\n## How to use\n\nSay things.\n' > README.md
printf 'Home\tREADME.md\n' > .loop/docs.tsv
python3 - <<'PY'
import json
c = json.load(open('.loop/config.json'))
c = {k: v for k, v in c.items() if k in ('base', 'wiki_dir', 'criteria', 'version_file')}; c['parallel'] = 3  # every other setting at its default
json.dump(c, open('.loop/config.json', 'w'), indent=2)
PY
$cri render >/dev/null 2>&1
H=docs/wiki/Home.md
over=$(sed -n '/settings:begin/,/settings:end/p' $H | grep -c 'overridden')
grep -q '^| `parallel` .*overridden:\*\* `3`' $H && [ "$over" = 1 ] && ok "one overridden setting shows exactly that one marked, with its value" || bad "overridden rows: $over: $(grep -c . $H)"
grep -q '^| `base` | .* | set "base" in .loop/config.json | `main` | default |' $H && ok "a setting at its default shows the name, meaning, how to set it, the default and 'default'" || bad "default row missing"
grep -q '^Built with the \[[A-Za-z0-9_.-]*/[A-Za-z0-9_.-]*\](https://github.com/[A-Za-z0-9_.-]*/[A-Za-z0-9_.-]*) workflow loop\.$' README.md && ! grep -q -E '/(Users|home)/' README.md $H && ok "the README names and links the template repo and holds no local path" || bad "template line: $(sed -n 1,5p README.md)"
sed -n '/settings:begin/,/settings:end/p' README.md | grep -q '`parallel`' && ok "the README carries the Settings section too" || bad "README settings"
check() { $docs check 2>&1; }
check | grep -q '^STALE' && bad "fresh blocks reported stale: $(check | grep STALE)" || ok "freshly rendered blocks are not stale"
python3 -c "import json; c = json.load(open('.loop/config.json')); c['parallel'] = 5; json.dump(c, open('.loop/config.json', 'w'), indent=2)"
check | grep -q '^STALE Settings: ' && ok "a changed setting value makes docs check say STALE Settings" || bad "no STALE after a change: $(check)"
$cri render >/dev/null 2>&1
grep -q 'overridden:\*\* `5`' $H && ! check | grep -q '^STALE Settings' && ok "render refreshes the block and the staleness clears" || bad "render did not refresh"
python3 -c "import json; c = json.load(open('.loop/config.json')); c['parallel'] = 7; json.dump(c, open('.loop/config.json', 'w'), indent=2)"
$docs publish --dry-run >/dev/null 2>&1
grep -q 'overridden:\*\* `7`' $H && ok "publish refreshes the block before it copies the pages" || bad "publish left the block stale"
a=$(sed -n '/automation:begin/,/automation:end/p' $H)
grep -q '^| health | .* | off | every 4 hours | not deployed | docs.py automation | run workflow-setup to write .github/workflows/health.yml |' <<<"$a" && ok "Automation says on, the cadence in words, not deployed and the step owed when the workflow file is missing" || bad "automation health row: $(grep '^| health' <<<"$a")"
mkdir -p .github/workflows; : > .github/workflows/health.yml
python3 -c "import json; c = json.load(open('.loop/config.json')); c['health_cron'] = '30 6 * * *'; c['automation'] = [{'name': 'money brief', 'does': 'Mails a daily money brief.', 'cadence': '0 7 * * *', 'runs': 'mac:com.example.brief'}]; json.dump(c, open('.loop/config.json', 'w'), indent=2)"
$cri render >/dev/null 2>&1
a=$(sed -n '/automation:begin/,/automation:end/p' $H)
grep -q '^| health | .* | on | daily at 06:30 | GitHub Actions (health.yml) | docs.py automation | none |' <<<"$a" && grep -q '^| money brief | Mails a daily money brief. | on (declared) | daily at 07:00 | this Mac (launch agent com.example.brief) | docs.py automation |' <<<"$a" && ok "Automation reads a daily cron in words, where it runs from the workflow file, and a routine added as one config entry" || bad "automation rows: $a"
$docs automation 2>&1 | grep -q '^money brief: not loaded$' && ok "docs.py automation reports a launch agent entry as not loaded when it is not" || bad "live status: $($docs automation 2>&1)"
python3 -c "import json; c = json.load(open('.loop/config.json')); c['health_cron'] = 'off'; json.dump(c, open('.loop/config.json', 'w'), indent=2)"
$cri render >/dev/null 2>&1
sed -n '/automation:begin/,/automation:end/p' $H |  grep -q '^| health | .* | off | off |' && ok "a routine turned off reads off" || bad "off row"
python3 $here/skills/workflow-docs/scripts/entry.py write >/dev/null 2>&1
grep -q 'Settings section' .loop/START.md && grep -q 'Automation section' .loop/START.md && grep -q 'README' .loop/START.md && ok "the adoption entry names the Home Settings and Automation sections and the README line" || bad "START.md"
[ "$fails" = 0 ] && echo "ALL PASS" || { echo "$fails FAILED"; exit 1; }
