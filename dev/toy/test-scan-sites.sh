#!/bin/bash
# reads: skills/workflow-delivery/scripts/ skills/workflow-release/scripts/ skills/workflow-monitoring/scripts/
# DEL-9 negative control: every function in the delivery, release and monitoring scripts that pushes or writes to
# GitHub (git push, gh pr create/merge/comment/edit, gh release create) calls the private-name scan first, so a new
# unscanned push site fails here. Reads the code only; no repo, no model.
# usage: test-scan-sites.sh
set -u
here=$(cd "$(dirname "$0")/../.." && pwd)
. "$here/dev/toy/reap.sh"
fails=0
ok() { echo "PASS: $1"; }
bad() { echo "FAIL: $1"; fails=$((fails + 1)); }
python3 - "$here"/skills/workflow-delivery/scripts/*.py "$here"/skills/workflow-release/scripts/*.py "$here"/skills/workflow-monitoring/scripts/*.py <<'PY' && ok "every push or GitHub write in delivery, release and monitoring calls the scan first" || bad "an unscanned push site"
import ast, os, sys
skip = {"private.py"}
bad = []
for path in sys.argv[1:]:
    name = os.path.basename(path)
    if True:
        if name in skip:
            continue
        tree = ast.parse(open(path).read())
        for fn in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
            text = ast.unparse(fn)
            q = text.replace('"', "'")  # ast.unparse prints single quotes
            writes = ("'push'" in q and "'git'" in q) or any("'%s', '%s'" % pair in q for pair in (
                ("pr", "create"), ("release", "create"), ("pr", "merge"), ("pr", "comment"), ("pr", "edit")))
            called = {(c.func.attr if isinstance(c.func, ast.Attribute) else getattr(c.func, "id", "")) for c in ast.walk(fn) if isinstance(c, ast.Call)}
            if writes and not called & {"scan", "private_check", "check", "pr_text"}:
                bad.append("%s:%s" % (name, fn.name))
if bad:
    print("unscanned: " + ", ".join(bad)); sys.exit(1)
PY

for f in "$here"/skills/workflow-delivery/scripts/*.py "$here"/skills/workflow-release/scripts/*.py "$here"/skills/workflow-monitoring/scripts/*.py; do
  [ "$(wc -c < "$f")" -lt 20480 ] || bad "$(basename "$f") is over 20 KB"
done
ok "every delivery, release and monitoring script stays under 20 KB"
[ "$fails" = 0 ] || exit 1
echo "ALL PASS"
