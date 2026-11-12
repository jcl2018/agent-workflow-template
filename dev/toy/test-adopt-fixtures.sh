#!/bin/bash
# reads: skills/workflow-setup/scripts/setup.py skills/workflow-setup/scripts/settings.py
# reads: skills/workflow-health/scripts/health.py skills/workflow-docs/scripts/docs.py
# Adopts fixture repos shaped like real ones: existing config checks (pull request 83's bug), CI tests with a .gitignore
# blocking *.tsv, a bare agent_command and no CI, features as roadmap milestones and not folders. Each must adopt cleanly.
# usage: test-adopt-fixtures.sh [existing-checks|ci-gitignore|bare-agent|feature-milestones]   no ID runs all four.
# No model is called; GitHub is only the stand-in gh (dev/toy/fakegh).
set -u
unset GITHUB_SERVER_URL GITHUB_REPOSITORY GITHUB_RUN_ID LOOP_SESSION_TOOL LOOP_OPERATION_SESSION
here=$(cd "$(dirname "$0")/../.." && pwd); only=${1:-}
. "$here/dev/toy/reap.sh"
d=$(mktemp -d); toy_on_exit 'rm -rf "$d"'
export HOME="$d/home"; mkdir -p "$HOME"
printf '# a toy: no private names\n' > "$d/names"; export LOOP_PRIVATE_NAMES="$d/names"
no() { echo "FAIL ${only:-adopt-fixtures}: $1"; exit 1; }
want() { [ -z "$only" ] || [ "$only" = "$1" ]; }
cp -R "$here/skills" "$d/skills"  # setup runs from a copy of the skills, as an installed one does
setup="python3 $d/skills/workflow-setup/scripts/setup.py"
mkdir -p "$d/bin"; printf '#!/bin/bash\nexit 0\n' > "$d/bin/claude"; chmod +x "$d/bin/claude"; export PATH="$d/bin:$PATH"

fixture() { # fixture NAME: an empty repo with a bare origin at $d/NAME/repo
  "$here/dev/toy/make.sh" "$d/$1" >/dev/null || no "make.sh failed"
  cd "$d/$1/repo" || exit 1
  git rm -q -f test_calc.py VERSION calc.py
}
unit() { # unit FILE: a real passing unittest test
  mkdir -p "$(dirname "$1")"; printf 'import unittest\n\n\nclass T(unittest.TestCase):\n    def test_ok(self):\n        self.assertTrue(True)\n' > "$1"
}
clean_docs() { # no format gap or broken link after adoption: only pages a person has yet to write
  out=$(python3 "$d/skills/workflow-docs/scripts/docs.py" check 2>&1)
  echo "$out" | grep -E 'DOC-(4|5|7|8)|BROKEN|LINK' && no "a docs-format gap after adoption: $(echo "$out" | head -3)"
  return 0
}

# Pull request 83: a config that lists its own checks keeps them, and the seeded rows run every one.
if want existing-checks; then
  fixture ec; mkdir -p .loop engine; printf 'def a():\n    return 1\n' > engine/a.py; unit tests/test_a.py; unit tests2/test_b.py
  printf '{"base": "main", "checks": ["python3 -m unittest discover -s tests", "python3 -m unittest discover -s tests2"]}\n' > .loop/config.json
  git add -A; git commit -qm "A repo with its own checks"
  out=$($setup 2>&1); rc=$?
  [ $rc = 0 ] || no "setup exited $rc: $(echo "$out" | tail -3)"
  git show workflow-setup:.loop/config.json | python3 -c "
import json, sys
c = json.load(sys.stdin)
assert c['checks'] == ['python3 -m unittest discover -s tests', 'python3 -m unittest discover -s tests2'], c.get('checks')" || no "the written config lost its own checks"
  row=$(awk -F'\t' '$1 ~ /-checks$/ && $2 == "land" {print $3; exit}' .loop/regression.tsv)
  [ "$row" = "python3 -m unittest discover -s tests && python3 -m unittest discover -s tests2" ] || no "the seeded row runs only part of the checks: $row"
  eval "$row" >/dev/null 2>&1 || no "the seeded row does not pass"
  clean_docs
  echo "PASS adopt-fixture existing-checks: the config's checks are kept and the row runs every one"
fi

# CI tests with a .gitignore blocking *.tsv: the exception lines are written and the check comes from CI.
if want ci-gitignore; then
  fixture cg; mkdir -p .github/workflows app; printf 'def a():\n    return 1\n' > app/a.py; unit tests/test_ok.py
  printf 'name: ci\non: [push]\njobs:\n  test:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v4\n      - run: python3 -m unittest discover -s tests\n' > .github/workflows/ci.yml
  printf '*.tsv\n__pycache__/\n' > .gitignore; git add -A; git commit -qm "CI and an ignored tsv"
  out=$($setup 2>&1); rc=$?
  [ $rc = 0 ] && echo "$out" | grep -q '^FOUND: .*checks \["python3 -m unittest discover -s tests"\]\|^FOUND: .*checks \[.python3 -m unittest discover -s tests.\]' || no "the check does not come from CI: rc=$rc $(echo "$out" | head -2)"
  git show workflow-setup:.gitignore | grep -qx '!.loop/\*.tsv' || no "no exception line written"
  git ls-tree -r --name-only workflow-setup | grep -q '^.loop/docs.tsv$' || no ".loop/docs.tsv is not in the commit"
  echo "$out" | grep -q 'REFUSED' && no "a refusal"
  clean_docs
  echo "PASS adopt-fixture ci-gitignore: exception lines written, the check taken from CI"
fi

# A bare agent_command and no CI: adopts, and names the gap with its fix.
if want bare-agent; then
  fixture ba; mkdir -p core; printf 'def a():\n    return 1\n' > core/a.py; unit tests/test_x.py; git add -A; git commit -qm "No CI, a bare agent"
  out=$($setup 2>&1); rc=$?
  [ $rc = 0 ] || no "setup exited $rc: $(echo "$out" | tail -3)"
  echo "$out" | grep -q '^GAP: agent_command \[.claude., .-p.\] grants no tools.*Fix: add to .loop/config.json: "agent_command": \["claude", "-p", "--allowedTools", "Bash,Read,Write,Edit"\]' || no "the gap is not named with its fix: $(echo "$out" | grep -i agent)"
  python3 -c "
import json; c = json.load(open('.loop/config.json')); assert c['agent_command'] == ['claude', '-p'], c['agent_command']" || no "setup changed the agent command (permissions are the owner's)"
  [ "$(git branch --show-current)" = workflow-setup ] || no "not adopted"
  clean_docs
  echo "PASS adopt-fixture bare-agent: adopted, the gap named with its fix, the agent command untouched"
fi

# Features as roadmap milestones, not folders: pages are made for them and no milestone is made or asked for.
if want feature-milestones; then
  fixture fm; unit tests/test_a.py
  printf '# Roadmap\n\n## Milestone 1: Billing\n\nInvoices.\n\n## Track B - Search\n\nQueries.\n' > ROADMAP.md
  git add -A; git commit -qm "Features in a roadmap"; git remote set-url origin https://github.com/example/toy.git
  export FAKE_GH_DIR="$d/gh"; mkdir -p "$FAKE_GH_DIR"; printf '[{"number": 1, "title": "Billing", "state": "open"}, {"number": 2, "title": "Search", "state": "open"}]' > "$FAKE_GH_DIR/milestones.json"
  before=$(shasum < "$FAKE_GH_DIR/milestones.json")
  out=$(PATH="$here/dev/toy/fakegh:$PATH" $setup 2>&1); rc=$?
  [ $rc = 0 ] || no "setup exited $rc: $(echo "$out" | tail -3)"
  [ -f docs/wiki/Billing.md ] && [ -f docs/wiki/Search.md ] && grep -q '^Billing' .loop/docs.tsv || no "the roadmap's features did not become pages: $(echo "$out" | head -2)"
  echo "$out" | grep -qi milestone && no "setup mentions a milestone: $(echo "$out" | grep -i milestone)"
  [ "$(shasum < "$FAKE_GH_DIR/milestones.json")" = "$before" ] && ! grep -qi 'milestone' "$FAKE_GH_DIR/calls.log" 2>/dev/null || no "a milestone was made or read"
  clean_docs
  echo "PASS adopt-fixture feature-milestones: pages for the roadmap's features, no milestone made"
fi

[ -n "$only" ] || echo "ALL PASS"
