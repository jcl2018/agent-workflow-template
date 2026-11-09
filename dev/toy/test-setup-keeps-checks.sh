#!/bin/bash
# Adopt a repo whose own .loop/config.json already lists checks, one of which the survey cannot find. No model is called.
set -u
here=$(cd "$(dirname "$0")/../.." && pwd)
d=$(mktemp -d); trap 'rm -rf "$d"' EXIT
export HOME="$d/home"; mkdir -p "$HOME"
no() { echo "FAIL setup-keeps-checks: $1"; exit 1; }
setup="python3 $here/skills/workflow-setup/scripts/setup.py"

"$here/dev/toy/make.sh" "$d/toy" >/dev/null || exit 1
cd "$d/toy/repo" || exit 1
mkdir -p .loop scripts
printf '#!/bin/bash\nexit 0\n' > scripts/check-demo-site.sh
cat > .loop/config.json <<'J'
{
  "base": "main",
  "checks": ["python3 -m unittest", "bash scripts/check-demo-site.sh"],
  "agent_command": ["claude", "-p", "--allowedTools", "Bash,Read"],
  "mend": true,
  "max_tries": 5
}
J
git add -A; git commit -qm "Hand-tuned loop config"
cp .loop/config.json "$d/before.json"

out=$($setup --dry-run) || no "dry run failed: $out"
echo "$out" | grep -q "check-demo-site.sh" || no "the dry run does not use the configured checks: $(echo "$out" | head -1)"
$setup >"$d/run.txt" 2>&1 || no "setup failed: $(tail -3 "$d/run.txt")"

# Every key the user set is still there with the same value, checks included.
python3 - "$d/before.json" .loop/config.json <<'PY' || no "a user-set config key was dropped or changed"
import json, sys
before, after = (json.load(open(p)) for p in sys.argv[1:])
lost = {k: v for k, v in before.items() if after.get(k) != v}
assert not lost, lost
PY
git show HEAD:.loop/config.json | grep -q "check-demo-site.sh" || no "the adoption commit dropped the second check"

# The regression rows run every configured check, not only the first.
grep -q "python3 -m unittest && bash scripts/check-demo-site.sh" .loop/regression.tsv || no "regression rows lack the second check"

# A second run changes nothing.
out=$($setup 2>&1); echo "$out" | grep -q "NO CHANGE" || no "second run was not NO CHANGE: $(echo "$out" | grep -v NOTE | head -5)"
echo "PASS setup-keeps-checks: configured checks kept in the config and run by the rows, second run NO CHANGE"
