#!/bin/bash
# reads: skills/workflow-monitoring/scripts/watch.py
# Issue 47: watch reads a flow file's suite as goal.py and flow.py do, so an all-built-in suite with no steps is a flow
# that is set and /workflow-monitoring go starts the goal. No model is called. usage: test-builtin-watch.sh
set -u
here=$(cd "$(dirname "$0")/../.." && pwd)
. "$here/dev/toy/reap.sh"
T=$(mktemp -d); toy_on_exit 'rm -rf "$T"'
python3 -c "import json;json.dump({'suite':{s:'built-in' for s in ('idea','plan','review','qa','ship')},'steps':{}},open('$T/flow.json','w'))"
if LOOP_FLOW="$T/flow.json" python3 -c "import sys;sys.path.insert(0,'$here/skills/workflow-monitoring/scripts');import watch;assert watch.flow_set()"; then
  echo "PASS: watch reads the suite too: an all-built-in suite with no steps is a flow that is set"; echo "ALL PASS"
else
  echo "FAIL: watch does not read the suite"; exit 1
fi
