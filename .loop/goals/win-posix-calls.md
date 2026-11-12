# Make lanes, slots and step timeouts work on native Windows Python (issue #1396): no os.getuid, os.O_NOFOLLOW or os.killpg crash

- Slug: win-posix-calls
- Touches: skills/workflow-delivery/scripts, skills/workflow-monitoring/scripts, skills/workflow-regression/scripts

## Done lines

Frozen. A wrong done line needs a new goal.

1. On Windows, lanekit.port_base() and slots.port_base() return a port base instead of raising AttributeError
2. On Windows, a step or child stopped for a timeout or a mend takes its whole process tree with it
3. On Linux the regression land tests still pass

## Verify by hand

1. On a Windows PC with native Python (no WSL), from the repo root run `cd skills/workflow-regression/scripts` and then
   `python -c "import slots; print(slots.port_base())"`.
   Expect: it prints a pair like `(3, 20000)`, not an AttributeError about getuid or O_NOFOLLOW.
2. In the same folder run `python -c "import subprocess, sys, time, proctree; p = subprocess.Popen([sys.executable, '-c', 'import subprocess, sys, time; subprocess.Popen([sys.executable, \"-c\", \"import time; time.sleep(60)\"]); time.sleep(60)']); time.sleep(2); proctree.kill(p.pid)"`
   and watch Task Manager (or `tasklist | findstr python`) while it runs.
   Expect: the two sleeping python processes it started are gone right after it returns.
