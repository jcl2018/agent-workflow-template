#!/bin/bash
# Run every step of a goal's skill flow through flow.py and goal.py record, with the stand-in flow make.sh writes.
# It also writes one Verify by hand step, as the build step would, unless the goal already has one.
# usage: flow-done.sh SLUG   (from the goal's worktree, with LOOP_FLOW set)
here=$(cd "$(dirname "$0")/../.." && pwd); slug=${1:?usage: flow-done.sh SLUG}
runs="$(cd "$(git rev-parse --git-common-dir)" && pwd)/loop/runs"
file=".loop/goals/$slug.md"
if ! grep -q "Expect:" "$file"; then
  python3 - "$file" <<'PY'
import sys
p = sys.argv[1]; t = open(p).read().replace("## Verify by hand\n", "## Verify by hand\n\n1. Open calc.py.\n   Expect: the change is there.\n", 1)
open(p, "w").write(t)
PY
  git commit -qm "Verify by hand: $slug" -- "$file"
fi
for step in idea plan review qa ship; do
  python3 "$here/skills/workflow-delivery/scripts/flow.py" "$slug" $step --wait 5 >/dev/null || exit 1
  python3 "$here/skills/workflow-delivery/scripts/flow.py" "$slug" $step --wait 10 >/dev/null || exit 1
  python3 "$here/skills/workflow-delivery/scripts/goal.py" record "$slug" $step --file "$runs/$slug.$step.txt" >/dev/null || exit 1
done
