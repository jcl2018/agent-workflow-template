#!/bin/bash
# Run every step of a goal's skill flow through flow.py and goal.py record, with the stand-in flow make.sh writes.
# usage: flow-done.sh SLUG   (from the goal's worktree, with LOOP_FLOW set)
here=$(cd "$(dirname "$0")/../.." && pwd); slug=${1:?usage: flow-done.sh SLUG}
runs="$(cd "$(git rev-parse --git-common-dir)" && pwd)/loop/runs"
for step in idea plan review qa ship; do
  python3 "$here/skills/workflow-delivery/scripts/flow.py" "$slug" $step --wait 5 >/dev/null || exit 1
  python3 "$here/skills/workflow-delivery/scripts/flow.py" "$slug" $step --wait 10 >/dev/null || exit 1
  python3 "$here/skills/workflow-delivery/scripts/goal.py" record "$slug" $step --file "$runs/$slug.$step.txt" >/dev/null || exit 1
done
