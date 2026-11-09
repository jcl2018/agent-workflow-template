#!/bin/bash
# Adopt a fake repo with CI tests, a bare agent command, its own feature list and a blocking .gitignore. No model is called.
set -u
unset LOOP_SESSION_TOOL LOOP_OPERATION_SESSION  # a toy test never reaches a real session tool
here=$(cd "$(dirname "$0")/../.." && pwd)
d=$(mktemp -d); trap 'rm -rf "$d"' EXIT
export HOME="$d/home"; mkdir -p "$HOME"
no() { echo "FAIL setup-fit: $1"; exit 1; }
setup="python3 $here/skills/workflow-setup/scripts/setup.py"

"$here/dev/toy/make.sh" "$d/toy" >/dev/null || exit 1
cd "$d/toy/repo" || exit 1
rm -f test_calc.py VERSION
mkdir -p .github/workflows scripts tests billing search
cat > .github/workflows/ci.yml <<'Y'
name: ci
on: [push]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install pytest
      - run: bash scripts/run-tests.sh
      - run: bash scripts/missing-test.sh
      - run: npm test
Y
printf '#!/bin/bash\npython3 -m unittest discover -s tests\n' > scripts/run-tests.sh
printf 'import unittest\nclass T(unittest.TestCase):\n    def test_a(self): self.assertTrue(True)\n' > tests/test_a.py
printf 'def a():\n    return 1\n' > billing/a.py; printf 'def b():\n    return 2\n' > billing/b.py
printf 'def c():\n    return 3\n' > search/c.py; printf 'def d():\n    return 4\n' > search/d.py
printf 'def e():\n    return 5\n' > calc2.py
printf '# Roadmap\n\n## Milestone 1: Billing\n\nText.\n\n## Track B - Search\n\nText.\n' > ROADMAP.md
printf '{"scripts": {"test": "echo \\"Error: no test specified\\" && exit 1"}}\n' > package.json
printf '# Changelog\n\n## [1.2.0] - 2026-01-01\n\n- x\n' > CHANGELOG.md
printf '.loop/\n' > .gitignore
git add -A; git commit -qm "Fake repo"
mkdir -p "$d/bin"; printf '#!/bin/bash\nexit 0\n' > "$d/bin/claude"; chmod +x "$d/bin/claude"; export PATH="$d/bin:$PATH"

# Line 4 (gitignore): the dry run names the exact exception, and a real run refuses and writes nothing.
out=$($setup --dry-run); echo "$out" | grep -q 'Add this line to .gitignore: !.loop/' || no "no .gitignore exception printed"
$setup >/dev/null && no "setup wrote past a blocking .gitignore"
[ ! -d .loop ] || no "a refused run wrote files"
printf '!.loop/\n' >> .gitignore; git commit -qam "Allow .loop"

# Line 1 (tests): the CI command that runs tests is kept; the missing script and the placeholder npm test are dropped.
out=$($setup --dry-run)
echo "$out" | grep -q "checks \['bash scripts/run-tests.sh'\]" || no "real CI test command not found: $(echo "$out" | head -3)"
echo "$out" | grep -q "dropped CI command 'bash scripts/missing-test.sh'" || no "missing script not reported"
echo "$out" | grep -q "dropped CI command 'npm test'" || no "placeholder npm test not reported"

# Line 3 (features): milestone and track headings, not every folder.
echo "$out" | grep -q "areas Billing, Search" || no "features are not the roadmap's: $(echo "$out" | head -1)"
echo "$out" | grep -q "Calc2" && no "a single-file folder became a page"

# Line 2 (bare agent): refuses to finish, prints the line to add.
echo "$out" | grep -q 'REFUSED to call this done.*"agent_command": \["claude", "-p", "--allowedTools"' || no "bare agent_command not refused with the line"
$setup >"$d/run.txt"; rc=$?
[ $rc -ne 0 ] || no "bare agent_command finished with exit 0"
git branch | grep -q workflow-setup || no "the branch was not written before the refusal"

# Line 4 (habit): the changelog style is reported.
grep -q "entries read like '## \[1.2.0\]" "$d/run.txt" || no "changelog habit not reported"
grep -q "no changelog" "$d/run.txt" && no "existing changelog missed"

# Line 3 (docs check): a page set that is not the fixed one passes the docs check.
grep -qP '^(Billing|Search)\t' .loop/docs.tsv 2>/dev/null || grep -q '^Billing' .loop/docs.tsv || no "docs.tsv lacks the features"
python3 "$here/skills/workflow-docs/scripts/docs.py" check 2>&1 | grep -q "not allowed" && no "docs check rejects the feature list"
grep -q 'BIL-1' docs/wiki/Billing.md || no "feature page has no criterion"
grep -q '^## Problem$' docs/wiki/Billing.md && grep -q '^Review: \*\*Unreviewed\*\*$' docs/wiki/Billing.md || no "seeded page is not a PRD"
python3 -c "import json; c = json.load(open('.loop/config.json')); c['criteria'] = True; json.dump(c, open('.loop/config.json', 'w'))"
out=$(python3 "$here/skills/workflow-docs/scripts/docs.py" audit --dry-run 2>&1)
grep -q "SECTIONS" <<<"$out" && no "seeded pages fail the PRD sections: $(grep SECTIONS <<<"$out" | head -1)"
grep -q "SCENARIO" <<<"$out" && no "seed rows are not Given/When/Then: $(grep SCENARIO <<<"$out" | head -1)"
git checkout -q -- .loop/config.json 2>/dev/null || true

# Line 1 (regression row): the row runs the real test command.
grep -q 'bash scripts/run-tests.sh' .loop/regression.tsv || no "regression row lacks the real command"

# Line 2 (idempotent): a rerun still refuses.
$setup >/dev/null; [ $? -ne 0 ] || no "second run lost the refusal"

# Line 5 (leak scan): a prefix from the private setting blocks the package.
cd "$here"; mkdir -p "$d/pk"; cp -R skills listing.json README.md LICENSE VERSION CHANGELOG.md "$d/pk/"
python3 dev/package.py --root "$d/pk" --out "$d/ok.zip" >/dev/null || no "clean package refused"
printf '{"leak_prefixes": ["zzprivate", "qq-[0-9]+"]}\n' > "$HOME/leak.json"
export LOOP_FLOW="$HOME/leak.json"
python3 dev/package.py --root "$d/pk" --out "$d/ok2.zip" >/dev/null || no "package refused with no match"
echo 'see QQ-42 here' >> "$d/pk/skills/workflow-setup/SKILL.md"
python3 dev/package.py --root "$d/pk" --out "$d/bad.zip" | grep -q "FAIL Safety: private prefix 'qq-\[0-9\]+'" || no "second prefix not blocked"
echo "PASS setup-fit: tests from CI, bare agent refused, features, .gitignore, habit, leak prefixes"
