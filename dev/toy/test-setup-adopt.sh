#!/bin/bash
# reads: skills/workflow-setup/scripts/setup.py skills/workflow-setup/scripts/settings.py
# reads: skills/workflow-health/scripts/health.py skills/workflow-docs/scripts/docs.py
# Proves setup's adoption: health first and last, no blocking, no unrelated writes after a refusal, issues for what does
# not fit, the docs format, the settings layers, the dry run list, private values, --from and the zero-test check.
# One case per regression row id. usage: test-setup-adopt.sh [ROW-ID]   no ID runs every case. No model is called, and
# issues go only to the stand-in gh (dev/toy/fakegh).
set -u
unset GITHUB_SERVER_URL GITHUB_REPOSITORY GITHUB_RUN_ID LOOP_SESSION_TOOL LOOP_OPERATION_SESSION
here=$(cd "$(dirname "$0")/../.." && pwd); only=${1:-}
. "$here/dev/toy/reap.sh"
d=$(mktemp -d); toy_on_exit 'chmod -R u+w "$d" 2>/dev/null; rm -rf "$d"'
export HOME="$d/home"; mkdir -p "$HOME"
printf '# a toy: no private names\n' > "$d/names"; export LOOP_PRIVATE_NAMES="$d/names"
no() { echo "FAIL ${only:-setup-adopt}: $1"; exit 1; }
want() { [ -z "$only" ] || [ "$only" = "$1" ]; }
S="$here/skills/workflow-setup/scripts"; setup="python3 $S/setup.py"
mkdir -p "$d/bin"; printf '#!/bin/bash\nexit 0\n' > "$d/bin/claude"; chmod +x "$d/bin/claude"; export PATH="$d/bin:$PATH"

mk() { # mk NAME: a toy repo with a code folder and a test, at $d/NAME/repo
  "$here/dev/toy/make.sh" "$d/$1" >/dev/null || no "make.sh failed"
  cd "$d/$1/repo" || exit 1
  mkdir -p engine; printf 'def run():\n    return 1\n' > engine/core.py
  git add -A; git commit -qm "Code folder"
}
state() { # a hash of the tree, the index, the branches, the stash and the home folder
  (cd "$1" && { git rev-parse HEAD; git branch -a; git stash list; git write-tree; git status --porcelain=v2 --untracked-files=all
    find . -path ./.git -prune -o -type f -print0 | sort -z | xargs -0 shasum; } | shasum
   find "$HOME" -type f -print0 2>/dev/null | sort -z | xargs -0 shasum 2>/dev/null | shasum) | tr -d ' \n-'
}
tracked() { git ls-tree -r --name-only "$1"; }

# SET-1 health first and last: HEALTH START before the first write line, the verdict last with each gap's fix.
if want set1-health-bracket; then
  mk hb; unset LOOP_NO_HEALTH
  out=$($setup 2>&1); rc=$?; export LOOP_NO_HEALTH=1
  [ $rc = 0 ] || no "setup exited $rc: $(echo "$out" | tail -3)"
  start=$(echo "$out" | grep -n '^HEALTH START:' | head -1 | cut -d: -f1); wrote=$(echo "$out" | grep -n '^WROTE' | head -1 | cut -d: -f1); first=$(echo "$out" | grep -n '^add:' | head -1 | cut -d: -f1)
  [ -n "$start" ] && [ -n "$wrote" ] && [ "$start" -lt "$first" ] && [ "$start" -lt "$wrote" ] || no "HEALTH START does not come first: $(echo "$out" | head -8)"
  [ "$(echo "$out" | tail -1 | cut -c1-17)" = "ADOPTION VERDICT:" ] || no "the verdict is not the last line: $(echo "$out" | tail -2)"
  echo "$out" | tail -1 | grep -q '^ADOPTION VERDICT: GAPS' || no "rows never seen failing are not named as gaps: $(echo "$out" | tail -2)"
  echo "$out" | grep -E '^(FAIL|WARN|UNREAD) ' | grep -vq -- '-> fix:' && no "a gap line has no fix"
  echo "$out" | grep -q '^FAIL .* -> fix:' || no "the verdict lists no FAIL gap with its fix"
  git log -1 --format=%B | sed -n 2p | grep -q '^HEALTH START:' || no "the start state is not the commit message's second line"
  mk hb2; out=$($setup --no-health 2>&1)
  echo "$out" | grep -q '^HEALTH START: not measured (skipped by --no-health)' && echo "$out" | tail -1 | grep -q '^ADOPTION VERDICT: not measured' || no "--no-health: $(echo "$out" | tail -3)"
  mk hb4; $setup --no-health --strict >/dev/null 2>&1; [ $? = 3 ] || no "--strict does not exit 3 when the verdict is not measured"
  git log -1 --format=%s | grep -q 'Adopt the workflow loop' || no "--strict did not leave the adoption committed"
  mk hb3; unset LOOP_NO_HEALTH
  out=$(LOOP_HEALTH_LIMIT=1 $setup --dry-run 2>&1); export LOOP_NO_HEALTH=1
  echo "$out" | grep -q '^HEALTH START: not measured (the check ran past its time limit)' && echo "$out" | tail -1 | grep -qx 'ADOPTION VERDICT: not run (dry run)' || no "a health run past the limit: $(echo "$out" | head -6)"
  mkdir -p "$d/lone"; cp -R "$here/skills" "$d/lone/skills"; rm -rf "$d/lone/skills/workflow-health"; unset LOOP_NO_HEALTH
  out=$(python3 "$d/lone/skills/workflow-setup/scripts/setup.py" --dry-run 2>&1); export LOOP_NO_HEALTH=1
  echo "$out" | grep -q '^HEALTH START: not measured (workflow-health is not beside workflow-setup)' || no "no workflow-health beside setup: $(echo "$out" | head -6)"
  echo "PASS set1-health-bracket: HEALTH START first, ADOPTION VERDICT last with each gap's fix, not measured says why"
fi

# SET-1 never blocks: a bare agent and an ignored *.tsv are gaps and exception lines, the adoption is committed, exit 0.
if want set1-never-blocks; then
  mk nb; printf '*.tsv\n' > .gitignore; mkdir -p docs/wiki; printf '# Engine\n\n## Hand\n\nsections\n' > docs/wiki/Engine.md; git add -A; git commit -qm "Own page and ignore"
  out=$($setup 2>&1); rc=$?
  [ $rc = 0 ] || no "setup exited $rc: $(echo "$out" | tail -4)"
  echo "$out" | grep -q 'REFUSED' && no "a refusal: $(echo "$out" | grep REFUSED)"
  echo "$out" | grep -q '^GAP: agent_command .*Fix: .*"agent_command": \["claude", "-p", "--allowedTools"' || no "the bare agent is not a gap with its fix"
  [ "$(git branch --show-current)" = workflow-setup ] && git log -1 --format=%s | grep -q 'Adopt the workflow loop' || no "the adoption is not committed on the branch"
  git show workflow-setup:.gitignore | grep -qx '!.loop/\*.tsv' || no "no exception line for the ignored .tsv"
  tracked workflow-setup | grep -qx '.loop/docs.tsv' || no "docs.tsv was left out of the commit"
  git show workflow-setup:.loop/findings.md | grep -q '^- \[adoption\] own-sections: docs/wiki/Engine.md\. Fix: ' || no "the page with its own sections is not in findings"
  echo "$out" | grep -q '^NOTE: [0-9]* items left in .loop/findings.md' || no "no gh: no NOTE that items are left"
  # a step after the commit fails: a NOTE, a gap, exit 0, the commit kept, the verdict last
  mk nb2
  out=$(LOOP_FLOW=/dev/null/x/flow.json $setup 2>&1); rc=$?
  [ $rc = 0 ] && echo "$out" | grep -q '^NOTE: private settings failed; the adoption is committed on the branch' || no "a failed step: rc=$rc $(echo "$out" | tail -4)"
  git log -1 --format=%s | grep -q 'Adopt the workflow loop' && [ "$(echo "$out" | tail -1 | cut -c1-17)" = "ADOPTION VERDICT:" ] || no "the commit or the last line after a failed step"
  # --no-issues files nothing even with gh and a GitHub remote
  mk nb3; git remote set-url origin https://github.com/example/toy.git
  export FAKE_GH_DIR="$d/gh-nb"; unset LOOP_NO_ISSUES
  out=$(PATH="$here/dev/toy/fakegh:$PATH" $setup --no-issues 2>&1); export LOOP_NO_ISSUES=1
  grep -q 'issue create' "$FAKE_GH_DIR/calls.log" 2>/dev/null && no "--no-issues filed an issue"
  echo "PASS set1-never-blocks: gaps, exception lines, committed, exit 0; a failed step is a NOTE and a gap"
fi

# SET-1 filing: pages with their own sections are one findings line and one issue each tagged adoption; none on a rerun.
if want set1-no-fit-filed; then
  mk nf; mkdir -p billing search docs/wiki .loop
  printf 'def a():\n    return 1\n' > billing/a.py; printf 'def c():\n    return 3\n' > search/c.py
  printf '# Billing\n\n## Hand\n\nwords\n' > docs/wiki/Billing.md; printf '# Search\n\n## Hand\n\nwords\n' > docs/wiki/Search.md
  printf '{"base": "main", "agent_command": ["claude", "-p", "--allowedTools", "Bash"]}\n' > .loop/config.json
  git add -A; git commit -qm "Two pages with their own sections"; git remote set-url origin https://github.com/example/toy.git
  export FAKE_GH_DIR="$d/gh-nf"; mkdir -p "$FAKE_GH_DIR"; unset LOOP_NO_ISSUES
  export PATH="$here/dev/toy/fakegh:$PATH"
  out=$($setup 2>&1); rc=$?
  [ $rc = 0 ] || no "setup exited $rc: $(echo "$out" | tail -4)"
  [ "$(git show workflow-setup:.loop/findings.md | grep -c '^- \[adoption\]')" = 1 ] || no "not one findings line: $(git show workflow-setup:.loop/findings.md)"
  git show workflow-setup:.loop/findings.md | grep '^- \[adoption\] own-sections:' | grep -q 'docs/wiki/Billing.md, docs/wiki/Search.md' || no "the line does not list both pages"
  n=$(python3 -c "import json,os; print(len(json.load(open(os.environ['FAKE_GH_DIR'] + '/issues.json'))))")
  python3 -c "
import json, os
issues = json.load(open(os.environ['FAKE_GH_DIR'] + '/issues.json'))
mine = [i for i in issues if 'no-fit' in i['title']]
assert len(mine) == 1, [i['title'] for i in issues]
assert 'health:adoption' in [l['name'] for l in mine[0]['labels']], mine[0]['labels']" || no "no issue tagged adoption for the findings line"
  export FAKE_GH_DIR="$d/gh-nf2"; mkdir -p "$FAKE_GH_DIR"
  w=$(python3 "$here/skills/workflow-health/scripts/health.py" preview --group adoption 2>&1 | grep -c '^WOULD')
  [ "$w" = "$n" ] || no "filed $n issues, preview says $w"
  export FAKE_GH_DIR="$d/gh-nf"
  before=$(grep -c 'issue create' "$FAKE_GH_DIR/calls.log")
  out=$($setup 2>&1); echo "$out" | grep -q 'NO CHANGE' || no "second run: $(echo "$out" | tail -3)"
  [ "$(grep -c 'issue create' "$FAKE_GH_DIR/calls.log")" = "$before" ] || no "a second run filed issues"
  export LOOP_NO_ISSUES=1
  echo "PASS set1-no-fit-filed: one findings line, one tagged issue, the filed count matches preview, none on a rerun"
fi

# SET-1 docs format: after adoption the docs check has no DOC-4, DOC-5, DOC-7, DOC-8 or link failure, only UNWRITTEN.
if want set1-docs-format; then
  mk df
  $setup >/dev/null 2>&1 || no "setup failed"
  out=$(python3 "$here/skills/workflow-docs/scripts/docs.py" check 2>&1)
  echo "$out" | grep -E 'DOC-(4|5|7|8)|BROKEN|LINK|DANGLING' && no "a docs-format gap after adoption"
  echo "$out" | grep -q '^UNWRITTEN Engine' && echo "$out" | grep -q '^UNWRITTEN Home' || no "the pages are not marked unwritten: $out"
  echo "$out" | grep -vE '^UNWRITTEN' | grep -q . && no "a gap other than unwritten: $(echo "$out" | grep -vE '^UNWRITTEN' | head -3)"
  grep -q '^## How to use' README.md && grep -q '^### How to use Engine' README.md || no "README has no How to use section"
  grep -q 'HOM-1' docs/wiki/*.md .loop/regression.tsv && no "Home still carries HOM-1"
  echo "PASS set1-docs-format: no format gap after adoption, only unwritten pages"
fi

# SET-2 layers: each value with the layer it came from, a local key in the committed config flagged.
if want set2-layers-show; then
  mk ly; mkdir -p .loop; printf '{"base": "main", "parallel": 3, "leak_prefixes": ["zz-1"]}\n' > .loop/config.json
  printf '{"model": "a-model", "env": {"SECRET_NAME": "x"}, "probe_expect": "%s/notes/x"}\n' "$HOME" > "$d/flow.json"; export LOOP_FLOW="$d/flow.json"
  out=$(python3 "$S/settings.py" show 2>&1) || no "show failed: $out"
  echo "$out" | grep -q '^| max_tries | 3 | default |' || no "a default value is not shown as default"
  echo "$out" | grep -q '^| parallel | 3 | repo | .loop/config.json |' || no "a repo value is not shown as repo"
  echo "$out" | grep -q '^| model | a-model | local | \$LOOP_FLOW |' || no "a local value is not shown as local with its home named"
  echo "$out" | grep -q '^| leak_prefixes | .* | repo (local setting in a committed file) |' || no "a local key in the committed config is not flagged"
  echo "$out" | grep -q '^| probe_expect | (withheld: holds a private value) | local |' || no "a value holding the home folder is not withheld"
  echo "$out" | grep -q 'SECRET_NAME' && echo "$out" | grep -q '"x"' && no "env prints its values"
  echo "$out" | grep -q '^NOTE: scripts read repo values directly; a local value wins only where its own home is read$' || no "no NOTE about the readers"
  python3 "$S/settings.py" show --json | python3 -c "
import json, sys
rows = {r['setting']: r for r in json.load(sys.stdin)}
assert rows['parallel']['layer'] == 'repo' and rows['model']['layer'] == 'local' and rows['max_tries']['layer'] == 'default', rows['parallel']" || no "--json differs from the text"
  unset LOOP_FLOW
  echo "PASS set2-layers-show: default, repo and local layers, the committed local key flagged, values withheld"
fi

# SET-7 the dry run lists everything the real run commits, and writes nothing (tree, branches, home folder).
if want set7-dry-run-lists-all; then
  mk dl; printf '*.tsv\n' > .gitignore; mkdir -p docs/wiki; printf '# Engine\n\n## Hand\n\nwords\n' > docs/wiki/Engine.md; git add -A; git commit -qm "x"
  before=$(state "$d/dl/repo")
  out=$($setup --dry-run 2>&1) || no "dry run failed"
  [ "$(state "$d/dl/repo")" = "$before" ] || no "the dry run changed the tree, the branches or the home folder"
  echo "$out" | grep -q '^would add to ' && echo "$out" | grep -q '^convert: .gitignore' && echo "$out" | grep -q 'docs/wiki/Tests.md' || no "the dry run misses the private half, the .gitignore or Tests.md: $out"
  echo "$out" | grep -E '^(add|convert):' | sed -E 's/^(add|convert): ([^ ]+).*/\2/' | sort > "$d/listed"
  $setup >/dev/null 2>&1 || no "setup failed"
  git show --name-only --format= HEAD | sort > "$d/committed"
  extra=$(comm -13 "$d/listed" "$d/committed"); [ -z "$extra" ] || no "the commit holds files the dry run did not list: $extra"
  echo "PASS set7-dry-run-lists-all: the commit is a subset of the dry run's list, the dry run writes nothing"
fi

# SET-7 a second run changes nothing: NO CHANGE, a clean tree, no gh write; an untracked working config survives.
if want set7-second-run-nothing; then
  mk sr
  mkdir -p .loop; printf '{"base": "main", "parallel": 7}\n' > .loop/config.json   # a working config nobody committed
  $setup >/dev/null 2>&1 || no "setup failed"
  git show workflow-setup:.loop/config.json | grep -q '"parallel": 7' || no "the working config was overwritten"
  tip=$(git rev-parse HEAD)
  out=$($setup 2>&1); rc=$?
  [ $rc = 0 ] && echo "$out" | grep -q '^NO CHANGE' && [ -z "$(git status --short)" ] && [ "$(git rev-parse HEAD)" = "$tip" ] || no "second run: rc=$rc $(echo "$out" | tail -4) $(git status --short)"
  echo "$out" | grep -q '^HEALTH START:' && echo "$out" | grep -q '^ADOPTION VERDICT:' || no "a no-change run does not print both health lines"
  grep -q '"parallel": 7' .loop/config.json || no "the config lost its own value"
  echo "PASS set7-second-run-nothing: NO CHANGE, a clean tree, the working config kept"
fi

# SET-8 a local setting in the committed config is refused, nothing written.
if want set8-local-setting-refused; then
  mk ls; mkdir -p .loop; printf '{"base": "main", "allowed_tools": ["qz-secret-tool"]}\n' > .loop/config.json
  before=$(state "$d/ls/repo")
  out=$($setup 2>&1); rc=$?
  [ $rc = 1 ] && echo "$out" | grep -q 'REFUSED: .*\.loop/config.json:[0-9]* holds the local setting allowed_tools.*SETUP_PRIVATE_VALUE' || no "not refused: rc=$rc $(echo "$out" | tail -3)"
  echo "$out" | grep -q 'qz-secret-tool' && no "the refusal prints the value"
  [ "$(state "$d/ls/repo")" = "$before" ] || no "the refusal left something written"
  echo "PASS set8-local-setting-refused: a private-home key in the config is refused by name, nothing written"
fi

# SET-8 a home path or a local-layer value on a line the adoption adds is refused by file:line, never printed.
if want set8-private-value-refused; then
  mk pv; mkdir -p docs/wiki; printf '# Engine\n\nSee %s/notes/secret-plan.txt for the plan.\n' "$HOME" > docs/wiki/Engine.md   # an untracked page: every line is added
  before=$(state "$d/pv/repo")
  out=$($setup 2>&1); rc=$?
  [ $rc = 1 ] && echo "$out" | grep -q 'REFUSED: .*docs/wiki/Engine.md:[0-9]* holds a private value.*SETUP_PRIVATE_VALUE' || no "a home path was not refused: rc=$rc $(echo "$out" | tail -3)"
  echo "$out" | grep -q 'secret-plan' && no "the refusal prints the value"
  [ "$(state "$d/pv/repo")" = "$before" ] || no "the refusal left something written"
  mk pv2; mkdir -p docs/wiki; printf '# Engine\n\nUses /srv/data/owner-private-tool.\n' > docs/wiki/Engine.md
  printf '{"model": "/srv/data/owner-private-tool"}\n' > "$d/flow2.json"
  out=$(LOOP_FLOW="$d/flow2.json" $setup 2>&1); rc=$?
  [ $rc = 1 ] && echo "$out" | grep -q 'docs/wiki/Engine.md:[0-9]* holds a private value' || no "a local-layer value was not refused: rc=$rc $(echo "$out" | tail -3)"
  # three non-refusals: private-looking text the repo already had, a value under 8 characters, a template default
  mk pv3; printf 'Contact: %s\n' "$(git config user.email)" >> README.md; git commit -qam "README with an address"
  mkdir -p docs/wiki; printf '# Engine\n\nUses /tmp/x and 17 */4 * * * as shipped.\n' > docs/wiki/Engine.md
  printf '{"model": "/tmp/x", "probe_expect": "17 */4 * * *"}\n' > "$d/flow3.json"
  out=$(LOOP_FLOW="$d/flow3.json" $setup 2>&1); rc=$?
  [ $rc = 0 ] && echo "$out" | grep -q '^WROTE the adoption' || no "an innocent adoption was refused: rc=$rc $(echo "$out" | tail -3)"
  echo "PASS set8-private-value-refused: a home path and a local value refused by file:line, three look-alikes adopted"
fi

# SET-9 --from borrows the portable settings and the page shape, holds the unattended ones, keeps this repo's own.
model() { # model NAME: an adopted-looking repo with a distinctive config
  rm -rf "$d/$1"; mkdir -p "$d/$1/.loop"; (cd "$d/$1" && git init -q -b main)
  python3 - "$d/$1" <<'PY'
import json, sys
json.dump({"base": "trunk", "agent_command": ["other", "-p", "--allowedTools", "X"], "version_file": "V.txt", "parallel": 4, "max_tries": 5,
           "criteria_max": 7, "feature_labels": True, "risky_paths": ["^infra/"], "auto_merge": True, "reply_hook": False, "cadence": "12",
           "milestones": [{"title": "Old milestone"}]}, open(sys.argv[1] + "/.loop/config.json", "w"), indent=2)
PY
  printf 'Home\tREADME.md\nBilling\tbilling\n' > "$d/$1/.loop/docs.tsv"
}
if want set9-from-borrows; then
  model m1; msum=$(cd "$d/m1" && find . -path ./.git -prune -o -type f -print0 | sort -z | xargs -0 shasum | shasum)
  mk fb
  out=$($setup --dry-run --from "$d/m1" 2>&1) || no "dry run with --from failed: $out"
  for line in 'borrow: parallel = 4' 'borrow: max_tries = 5' 'borrow: risky_paths = ' 'borrow: feature_labels = true' 'held: auto_merge = true (unattended or runs code; add --allow auto_merge to take it)' 'held: reply_hook = false' 'skip: milestone Old milestone (free form, none made)' 'adapt: ' 'NOTE: your local layer already applies here'; do
    echo "$out" | grep -qF "$line" || no "the plan lacks '$line': $(echo "$out" | grep -E 'borrow|held|skip|adapt|NOTE' | head -12)"
  done
  $setup --from "$d/m1" >/dev/null 2>&1 || no "setup --from failed"
  python3 - <<'PY' || no "the written config does not borrow, keep and hold right"
import json
c = json.load(open(".loop/config.json"))
assert c["parallel"] == 4 and c["max_tries"] == 5 and c["criteria_max"] == 7 and c["feature_labels"] is True and c["risky_paths"] == ["^infra/"], c
assert c["base"] == "main" and c["agent_command"] == ["claude", "-p"] and c.get("version_file") != "V.txt", (c["base"], c["agent_command"])
assert c["auto_merge"] is False and c["reply_hook"] is True and c["cadence"] == "12", (c["auto_merge"], c["reply_hook"])
PY
  out=$($setup --from "$d/m1" 2>&1); echo "$out" | grep -q '^NO CHANGE' || no "a second run with --from changed something: $(echo "$out" | tail -3)"
  [ "$msum" = "$(cd "$d/m1" && find . -path ./.git -prune -o -type f -print0 | sort -z | xargs -0 shasum | shasum)" ] || no "the model repo was changed"
  mk fb2; $setup --from "$d/m1" --allow auto_merge,reply_hook >/dev/null 2>&1 || no "setup --allow failed"
  python3 -c "
import json; c = json.load(open('.loop/config.json')); assert c['auto_merge'] is True and c['reply_hook'] is False, c" || no "--allow did not take the held keys"
  mk fb3; before=$(state "$d/fb3/repo")
  out=$($setup --from "$d/nowhere" 2>&1); rc=$?
  [ $rc = 1 ] && echo "$out" | grep -q '^REFUSED: --from .*nowhere is not an adopted repo' && [ "$(state "$d/fb3/repo")" = "$before" ] || no "a bad --from path: rc=$rc $out"
  out=$($setup --dry-run --from "$d/m1" --allow nope 2>&1); echo "$out" | grep -q '^NOTE: nope is not held; nothing to allow' || no "an --allow of a key that is not held"
  echo "PASS set9-from-borrows: borrowed, kept, held until allowed, second run NO CHANGE, the model untouched"
fi

# SET-9 a model value holding a home path or an email is skipped and appears nowhere.
if want set9-from-no-values; then
  model m2
  python3 - "$d/m2" "$HOME" <<'PY'
import json, sys
path = sys.argv[1] + "/.loop/config.json"
c = json.load(open(path)); c["cadence"] = sys.argv[2] + "/priv"; c["digest_mail"] = "owner@example.com"; c["auto_merge"] = sys.argv[2] + "/x"
json.dump(c, open(path, "w"))
PY
  mk nv
  out=$($setup --from "$d/m2" --allow auto_merge 2>&1) || no "setup failed: $out"
  echo "$out" | grep -q '^skip: cadence holds a private value' && echo "$out" | grep -q '^skip: digest_mail holds a private value' && echo "$out" | grep -q '^held: auto_merge (holds a private value; not shown)' || no "the private values are not skipped: $(echo "$out" | grep -E 'skip|held')"
  echo "$out" | grep -qE 'owner@example.com|/priv' && no "a private value was printed"
  git grep -qE 'owner@example.com|/priv' workflow-setup -- . && no "a private value was written to the repo"
  grep -q '"auto_merge": false' .loop/config.json || no "a held value with a private value was taken"
  echo "PASS set9-from-no-values: private values are skipped, never printed, never written"
fi

# Issue 119: a *_test.py repo gets a check that finds a test; no proof gives no check and a finding; a held check is kept.
if want setup-zero-tests-119; then
  mk zt; git rm -q test_calc.py; mkdir -p tests
  printf 'import unittest\n\n\nclass CalcTest(unittest.TestCase):\n    def test_one(self):\n        self.assertEqual(1, 1)\n' > tests/calc_test.py
  git add -A; git commit -qm "Tests with a suffix name"
  cmd=$($setup --dry-run 2>&1 | grep '^FOUND' | python3 -c "import ast, re, sys; print(ast.literal_eval(re.search(r'checks (\[.*?\]), areas', sys.stdin.read()).group(1))[0])")
  [ "$cmd" = "python3 -m unittest discover -s tests -p '*_test.py'" ] || no "the check is not the suffix-pattern command: $cmd"
  eval "$cmd" 2>&1 | grep -qE '^Ran [1-9][0-9]* test' || no "the proposed command finds no test"
  mk zt2; git rm -q test_calc.py; git commit -qm "No tests"
  out=$($setup 2>&1)
  echo "$out" | grep -q '^no fit: .loop/regression.tsv (no check command found' || no "no proof gave no fit line: $(echo "$out" | head -8)"
  git show workflow-setup:.loop/findings.md | grep -q '^- \[adoption\] no-check: .loop/regression.tsv' || no "no no-check finding"
  mk zt3; mkdir -p .loop; printf '{"base": "main", "checks": ["python3 -m unittest discover -s nowhere"]}\n' > .loop/config.json
  out=$($setup 2>&1)
  echo "$out" | grep -q '^NOTE: python3 -m unittest discover -s nowhere finds no test files' && git show workflow-setup:.loop/config.json | grep -q 'unittest discover -s nowhere' || no "a held check that fails the proof is not kept and noted"
  mk zt4; git rm -q test_calc.py; printf 'def test_one():\n    assert True\n' > calc_test.py; git add -A; git commit -qm "pytest style"
  mkdir -p "$d/min"; ln -sf "$(command -v python3)" "$d/min/python3"; ln -sf "$(command -v git)" "$d/min/git"
  out=$(PATH="$d/min:/usr/bin:/bin" $setup --dry-run 2>&1)
  echo "$out" | grep -q 'unittest' && no "a pytest style file got a unittest command: $(echo "$out" | head -3)"
  echo "$out" | grep -q '^no fit: .loop/regression.tsv' || no "pytest style without pytest is not no fit: $(echo "$out" | head -4)"
  echo "PASS setup-zero-tests-119: a check that finds a test, no fit without proof, a held check kept and noted"
fi

# Issue 120: every refusal leaves the tree, the branches, the index and the home folder as they were.
if want setup-refusal-writes-120; then
  same() { [ "$(state "$1")" = "$2" ] || no "$3: something stayed written"; }
  # a private name in a staged adoption file
  mk rf1; mkdir -p docs/wiki; printf '# Engine\n\nA zzprivate word.\n' > docs/wiki/Engine.md; printf 'zzprivate\n' > "$d/names1"
  b=$(state "$d/rf1/repo"); out=$(LOOP_PRIVATE_NAMES="$d/names1" $setup 2>&1); rc=$?
  [ $rc = 1 ] && echo "$out" | grep -q 'REFUSED: a staged adoption file holds a private name.*nothing written' || no "private name: rc=$rc $(echo "$out" | tail -3)"
  same "$d/rf1/repo" "$b" "a private name"
  # the setup branch existed before (at HEAD): it is kept at its old tip
  mk rf2; git branch workflow-setup; mkdir -p docs/wiki; printf '# Engine\n\nA zzprivate word.\n' > docs/wiki/Engine.md
  b=$(state "$d/rf2/repo"); LOOP_PRIVATE_NAMES="$d/names1" $setup >/dev/null 2>&1
  same "$d/rf2/repo" "$b" "an existing setup branch"
  # the repo's own commit hook refuses
  mk rf3; printf '#!/bin/sh\necho "hook says: tracked tsv files are refused" >&2\nexit 1\n' > .git/hooks/pre-commit; chmod +x .git/hooks/pre-commit
  b=$(state "$d/rf3/repo"); out=$($setup 2>&1); rc=$?
  [ $rc = 1 ] && echo "$out" | grep -q 'hook says: tracked tsv files are refused' && echo "$out" | grep -q 'REFUSED: the repo.s own commit hook refused.*SETUP_HOOK_REFUSED' || no "commit hook: rc=$rc $(echo "$out" | tail -4)"
  same "$d/rf3/repo" "$b" "a refused commit hook"
  # prechecks: a merge in progress, a detached HEAD, a diverged setup branch, the branch in another worktree
  mk rf4; touch .git/MERGE_HEAD; b=$(state "$d/rf4/repo"); out=$($setup 2>&1); rc=$?
  [ $rc = 1 ] && echo "$out" | grep -q 'SETUP_REPO_STATE' || no "merge in progress: rc=$rc $out"; same "$d/rf4/repo" "$b" "a merge in progress"
  mk rf5; git checkout -q --detach; b=$(state "$d/rf5/repo"); out=$($setup 2>&1); rc=$?
  [ $rc = 1 ] && echo "$out" | grep -q 'SETUP_REPO_STATE' || no "detached HEAD: rc=$rc $out"; same "$d/rf5/repo" "$b" "a detached HEAD"
  mk rf6; git checkout -q -b workflow-setup; echo x > extra.txt; git add -A; git commit -qm "ahead"; git checkout -q main
  b=$(state "$d/rf6/repo"); out=$($setup 2>&1); rc=$?
  [ $rc = 1 ] && echo "$out" | grep -q 'SETUP_BRANCH_DIVERGED' || no "diverged branch: rc=$rc $out"; same "$d/rf6/repo" "$b" "a diverged setup branch"
  mk rf7; git worktree add -q -b workflow-setup "$d/rf7/wt" >/dev/null 2>&1; b=$(state "$d/rf7/repo"); out=$($setup 2>&1); rc=$?
  [ $rc = 1 ] && echo "$out" | grep -q 'SETUP_REPO_STATE' || no "branch in another worktree: rc=$rc $out"; same "$d/rf7/repo" "$b" "a branch in another worktree"
  # a dirty planned path is refused (exit 2); a dirty unrelated file and a staged unrelated change are left alone
  mk rf8; echo "more" >> README.md; b=$(state "$d/rf8/repo"); out=$($setup 2>&1); rc=$?
  [ $rc = 2 ] && echo "$out" | grep -q 'SETUP_PLANNED_PATH_DIRTY' || no "dirty planned path: rc=$rc $(echo "$out" | tail -3)"; same "$d/rf8/repo" "$b" "a dirty planned path"
  mk rf9; echo "staged" > staged.txt; git add staged.txt; echo "dirty" >> calc.py
  $setup >/dev/null 2>&1 || no "an adoption beside unrelated work failed"
  git diff --cached --name-only | grep -qx staged.txt && ! git show --name-only --format= HEAD | grep -qx staged.txt && ! git show --name-only --format= HEAD | grep -qx calc.py && tail -1 calc.py | grep -qx dirty || no "the unrelated staged or dirty work was touched"
  # a signal during a blocking hook rolls back (exit 130); a kill -9 leaves a journal the next run recovers
  mk rfA; printf '#!/bin/sh\necho $$ > "%s/hook.pid"\nsleep 60\n' "$d" > .git/hooks/pre-commit; chmod +x .git/hooks/pre-commit
  b=$(state "$d/rfA/repo"); rm -f "$d/hook.pid"
  $setup >"$d/sig.out" 2>&1 & sp=$!
  for _ in $(seq 1 120); do [ -s "$d/hook.pid" ] && break; sleep 0.5; done; [ -s "$d/hook.pid" ] || no "the hook never started"
  kill -TERM $sp; wait $sp; rc=$?
  [ $rc = 130 ] || no "a signal exits $rc, not 130: $(tail -3 "$d/sig.out")"
  same "$d/rfA/repo" "$b" "a signal during a hook"
  mk rfB; printf '#!/bin/sh\necho $$ > "%s/hook.pid"\nsleep 60\n' "$d" > .git/hooks/pre-commit; chmod +x .git/hooks/pre-commit
  b=$(state "$d/rfB/repo"); rm -f "$d/hook.pid"
  $setup >"$d/kill.out" 2>&1 & sp=$!
  for _ in $(seq 1 120); do [ -s "$d/hook.pid" ] && break; sleep 0.5; done; [ -s "$d/hook.pid" ] || no "the second hook never started"
  kill -9 $sp; wait $sp 2>/dev/null; pkill -P "$(cat "$d/hook.pid")" 2>/dev/null; kill "$(cat "$d/hook.pid")" 2>/dev/null; sleep 2
  [ -f .git/workflow-setup-txn/journal.json ] || no "a killed run left no journal"
  rm -f .git/hooks/pre-commit; rm -f .git/index.lock
  out=$($setup 2>&1); rc=$?
  [ $rc = 0 ] && echo "$out" | grep -q 'SETUP_RECOVERED' && git log -1 --format=%s | grep -q 'Adopt the workflow loop' || no "the next run did not recover and adopt: rc=$rc $(echo "$out" | head -3)"
  # a failed git call mid-adoption (setup's git() exits) rolls back like any refusal
  mk rfD; mkdir -p "$d/shim"; real=$(command -v git); printf '#!/bin/bash\n[[ " $* " == *" add -A "* ]] && { echo "fatal: simulated" >&2; exit 128; }\nexec %s "$@"\n' "$real" > "$d/shim/git"; chmod +x "$d/shim/git"
  b=$(state "$d/rfD/repo"); out=$(PATH="$d/shim:$PATH" $setup 2>&1); rc=$?
  [ $rc = 1 ] && echo "$out" | grep -q 'rolled back, nothing written' || no "a failed git call: rc=$rc $(echo "$out" | tail -3)"
  same "$d/rfD/repo" "$b" "a failed git call"
  # a wiki_dir that is not a folder inside the repo is refused before anything is copied or written
  mk rfE; mkdir -p .loop; printf '{"wiki_dir": "."}\n' > .loop/config.json; git add -A; git commit -qm "odd wiki_dir"
  b=$(state "$d/rfE/repo"); out=$($setup 2>&1); rc=$?
  [ $rc = 1 ] && echo "$out" | grep -q 'SETUP_WIKI_DIR' || no "wiki_dir .: rc=$rc $(echo "$out" | tail -3)"; same "$d/rfE/repo" "$b" "a wiki_dir of ."
  [ ! -d .git/workflow-setup-txn ] || no "a refused wiki_dir left a journal"
  # the journal does not outlive the commit, and a stale one whose HEAD moved is dropped, never restored over newer work
  mk rfF; $setup >/dev/null 2>&1 || no "rfF adoption failed"
  [ ! -d .git/workflow-setup-txn ] || no "a committed adoption left its journal"
  mkdir -p .git/workflow-setup-txn; python3 - "$(git rev-parse HEAD~1)" <<'PY' || no "could not write a stale journal"
import json, sys
json.dump({"branch": "workflow-setup", "tops": [".loop", ".github/workflows", ".gitignore", "README.md"], "orig": "main", "head": sys.argv[1], "tip": "", "tree": "", "files": {}}, open(".git/workflow-setup-txn/journal.json", "w"))
PY
  b=$(state "$d/rfF/repo"); out=$($setup 2>&1); rc=$?
  [ $rc = 0 ] && echo "$out" | grep -q 'SETUP_RECOVERED' && [ -f .loop/config.json ] && [ "$(state "$d/rfF/repo")" = "$b" ] || no "a stale journal with a moved HEAD: rc=$rc $(echo "$out" | head -3)"
  # a worktree on a branch that only starts with the setup branch's name is not the branch in another worktree
  mk rfG; git worktree add -q -b workflow-setup-2 "$d/rfG/wt2" >/dev/null 2>&1; out=$($setup 2>&1); rc=$?
  [ $rc = 0 ] && git log -1 --format=%s | grep -q 'Adopt the workflow loop' || no "a prefix-named worktree branch refused the adoption: rc=$rc $(echo "$out" | head -3)"
  # a restore that cannot finish is half undone (exit 4)
  mk rfC; mkdir -p docs/wiki; printf '# Notes\n' > docs/wiki/Notes.md; git add -A; git commit -qm "wiki"; chmod a-w docs/wiki
  out=$($setup 2>&1); rc=$?; chmod -R u+w docs
  [ $rc = 4 ] && echo "$out" | grep -q 'SETUP_HALF_UNDONE' && echo "$out" | grep -q 'Side effects: partial' || no "half undone: rc=$rc $(echo "$out" | tail -4)"
  echo "PASS setup-refusal-writes-120: every refusal, signal and kill leaves nothing written or recovers"
fi

# Issue 127: the ignored .tsv is exempted by a written line; a hook that rejects .tsv is named with its exemption.
if want setup-tsv-guard-127; then
  mk tg; printf '*.tsv\n' > .gitignore; git add -A; git commit -qm "Ignore tsv"
  out=$($setup --dry-run 2>&1); echo "$out" | grep -q '^convert: .gitignore (adds !.loop/\*.tsv)' || no "the dry run does not plan the exception: $(echo "$out" | grep -i gitignore)"
  $setup >/dev/null 2>&1 || no "an ignored .tsv blocked the adoption"
  tracked workflow-setup | grep -q '^.loop/docs.tsv$' || no ".loop/docs.tsv is not in the commit"
  git show workflow-setup:.gitignore | grep -qx '!.loop/\*.tsv' || no "no exception line written"
  git show workflow-setup:.gitignore | grep -q '^# workflow-setup' || no "the exception has no comment"
  mk tg2; mkdir -p .githooks; git config core.hooksPath .githooks
  printf '#!/bin/sh\nif git diff --cached --name-only | grep -q "\\.tsv$"; then echo "tracked .tsv files are refused" >&2; exit 1; fi\n' > .githooks/pre-commit; chmod +x .githooks/pre-commit
  git add -A; git commit -qm "A privacy guard" 2>/dev/null
  out=$($setup --dry-run 2>&1); echo "$out" | grep -q '^GUARD: .githooks/pre-commit mentions .tsv; if it refuses tracked data files, exempt .loop/\*.tsv' || no "no GUARD line: $(echo "$out" | head -8)"
  b=$(state "$d/tg2/repo"); out=$($setup 2>&1); rc=$?
  [ $rc = 1 ] && echo "$out" | grep -q 'tracked .tsv files are refused' && echo "$out" | grep -q 'exempt .loop/\*.tsv' || no "the guard's refusal: rc=$rc $(echo "$out" | tail -4)"
  [ "$(state "$d/tg2/repo")" = "$b" ] || no "the guard's refusal left something written"
  git diff --quiet HEAD -- .githooks || no "setup edited the guard"
  printf '#!/bin/sh\nif git diff --cached --name-only | grep -v "^.loop/" | grep -q "\\.tsv$"; then echo refused >&2; exit 1; fi\n' > .githooks/pre-commit; git commit -qam "Exempt the loop files"
  $setup >/dev/null 2>&1 || no "after the exemption setup still fails"
  echo "PASS setup-tsv-guard-127: the ignore is exempted by a written line, a guard is named and never edited"
fi

[ -n "$only" ] || echo "ALL PASS"
