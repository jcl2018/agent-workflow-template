#!/bin/bash
here=$(cd "$(dirname "$0")/../.." && pwd)
. "$here/dev/toy/reap.sh"
# windows: ok
# reads: skills/workflow-health/scripts/health.py skills/workflow-health/scripts/rules.py dev/package.py
# Issue 3125: a Windows CRLF checkout gets the same size verdicts as Linux. A 20,000-byte script (20,3xx on disk
# with CRLF), a 149-line SKILL.md and a 150-line one are judged by their LF bytes and lines in health's size and
# skill-lines rules and in package.py's Scripts rule.
# Value: protects=health and the package check agree between Windows and Linux (issue 3125); fails_when=a size or
# line rule reads the CRLF working tree; why_new=no row wrote CRLF files before judging them; seam=none;
# no_claim=a real Windows checkout
set -u
fails=0
ok() { echo "PASS: $1"; }
bad() { echo "FAIL: $1"; fails=$((fails + 1)); }
out=$(python3 - "$here" <<'PY' 2>&1
import os, sys, tempfile
here = sys.argv[1]
sys.path.insert(0, here + "/skills/workflow-health/scripts"); import health, rules
sys.path.insert(0, here + "/dev"); import package
root = tempfile.mkdtemp()
def put(rel, text):
    path = os.path.join(root, rel); os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as h: h.write(text.replace("\n", "\r\n").encode())
put("skills/x/scripts/a.py", "x = 1\n" * 3350)             # 20,100 LF bytes, 23,450 with CRLF
put("skills/a/SKILL.md", "line\n" * 149)
put("skills/b/SKILL.md", "line\n" * 150)
print("health-size", [r for r in health.size_rows(root) if "FAIL" in str(r)] == [])
print("health-lines", [os.path.basename(os.path.dirname(f)) for f in [os.path.join(root, "skills", n, "SKILL.md") for n in "ab"] if rules.skill_lines(root) and f.endswith(os.path.join("b", "SKILL.md"))] == ["b"], len(rules.skill_lines(root)))
package.failures.clear(); package.fail = lambda rule, text: package.failures.append((rule, text))
package.check_scripts(root, ["skills/x/scripts/a.py"])
print("package", [f for f in package.failures if "bytes" in f[1]] == [])
PY
)
echo "$out" | grep -qx "health-size True" && ok "health's scripts size rule reads LF bytes of a CRLF file" || bad "health size: $(echo "$out" | tail -3)"
echo "$out" | grep -qx "health-lines True 1" && ok "health's skill-lines rule counts LF lines of a CRLF file" || bad "health lines: $(echo "$out" | tail -3)"
echo "$out" | grep -qx "package True" && ok "package.py's Scripts rule reads LF bytes of a CRLF file" || bad "package: $(echo "$out" | tail -3)"
[ "$fails" = 0 ] && echo "ALL PASS"
exit $((fails != 0))
