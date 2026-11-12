#!/bin/bash
# reads: skills/
# Proves lanes-abs-path (REG-4): a lane's reach analysis never walks a folder outside the repo. A script that quotes an
# absolute folder (os.path.join(root, "/abs/dir") is "/abs/dir") once had that whole folder walked, per row; the analysis now
# skips it, and the paths a row reaches are the same as for the same repo without the quoted folder. Invented files in a
# toy folder; no repo, no model. usage: test-lanes-abs-path.sh [DIR] [SCRIPTS]  (SCRIPTS: lanes.py's folder, default this repo's)
set -u
here=$(cd "$(dirname "$0")/../.." && pwd)
T=${1:-$(mktemp -d)}; rm -rf "${T:?}"; S=${2:-$here/skills/workflow-regression/scripts}
mkdir -p "$T/outside/deep" "$T/a/dev/toy" "$T/a/skills/workflow-x/scripts" "$T/a/skills/workflow-x/data"
echo x > "$T/outside/deep/file.txt"; echo x > "$T/a/skills/workflow-x/data/d.txt"
printf '#!/bin/bash\n# reads: skills/workflow-x/scripts/\npython3 skills/workflow-x/scripts/x.py\n' > "$T/a/dev/toy/test-a.sh"
printf 'import os\nprint(os.listdir("skills/workflow-x/data"))\n' > "$T/a/skills/workflow-x/scripts/x.py"
cp -R "$T/a" "$T/b"
printf 'print(open("%s/outside/deep/file.txt").read(), "%s/outside/deep", "%s/outside/")\n' "$T" "$T" "$T" >> "$T/b/skills/workflow-x/scripts/x.py"
cp -R "$T/a" "$T/c"; cp -R "$T/a" "$T/d"
printf 'print(open("skills/../../outside/deep/file.txt").read(), "skills/../../outside/deep")\n' >> "$T/c/skills/workflow-x/scripts/x.py"
printf 'ls skills/../../outside/deep/*\n' >> "$T/d/dev/toy/test-a.sh"
fails=0
ok() { echo "PASS: $1"; }
bad() { echo "FAIL: $1"; fails=$((fails + 1)); }
cat > "$T/h.py" <<'PY'
# Walk spy: run the real analysis and report every folder os.walk or an isdir probe was given outside the repo, and the reach.
import json, os, sys
sys.path.insert(0, sys.argv[1]); import lanes
root, command = sys.argv[2:4]
inside = os.path.realpath(root); seen = []; real = os.walk
def out(path): p = os.path.realpath(path); return not (p == inside or p.startswith(inside + os.sep))
def spy(top, *a, **k):
    if out(top): seen.append(top)
    return real(top, *a, **k)
os.walk = spy
for fn in (lanes.closure, lanes.wide_closure):
    del seen[:]  # each closure reports its own walks
    deps, always = fn(root, command, {})
    print(json.dumps({"walked_outside": seen, "deps": sorted(deps), "always": bool(always)}))
PY
run() { python3 "$T/h.py" "$S" "$T/$1" "bash dev/toy/test-a.sh"; }
a=$(run a); b=$(run b); c=$(run c); d=$(run d)
field() { python3 -c "import json,sys; print(json.loads(sys.argv[1].splitlines()[int(sys.argv[3])])[sys.argv[2]])" "$1" "$2" "$3"; }
for i in 0 1; do kind=$([ "$i" = 0 ] && echo narrow || echo wide)
  [ "$(field "$b" walked_outside "$i")" = "[]" ] && ok "$kind: a script that quotes an absolute folder outside the repo is not walked" || bad "$kind: walked outside: $(field "$b" walked_outside "$i")"
  [ "$(field "$a" deps "$i")" = "$(field "$b" deps "$i")" ] && ok "$kind: the reach is the same with and without the quoted outside folder" || bad "$kind: reach differs: $(field "$a" deps "$i") vs $(field "$b" deps "$i")"
done
for v in c d; do for i in 0 1; do kind=$([ "$i" = 0 ] && echo narrow || echo wide); val=$([ "$v" = c ] && echo "$c" || echo "$d")
  [ "$(field "$val" walked_outside "$i")" = "[]" ] && ok "$kind: a .. path that leaves the repo ($v) is not walked" || bad "$kind: walked outside via $v: $(field "$val" walked_outside "$i")"
done; done
case "$(field "$a" deps 0)" in *workflow-x/scripts/x.py*) ok "the in-repo file a script reads is still reached";; *) bad "in-repo reach lost: $(field "$a" deps 0)";; esac
[ "$fails" = 0 ] && echo "ALL PASS" || { echo "$fails FAILED"; exit 1; }
