# Plan: lane-skips-node-modules

1. lanes.walk prunes node_modules and __pycache__ from os.walk's dirs. Done.
2. Toy dev/toy/test-lane-skips-node-modules.py and row lane-walk-skips-node-modules (REG-7, seen red). Done.
3. docs check, package gate; then qa, ship, pr; the PR body closes #3939 and #3943.
