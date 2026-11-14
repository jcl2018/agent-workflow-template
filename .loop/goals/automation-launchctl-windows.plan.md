# Plan: automation-launchctl-windows

1. probe() in audit.py returns None when the program is missing; live() reports unknown. Done.
2. docs.py automation calls audit.live; counting.py loses live(). Done.
3. Toy dev/toy/test-automation-launchctl.py and row launchctl-missing-unknown (seen red). Done.
4. docs check, split toy, package gate, then qa, ship, pr.
