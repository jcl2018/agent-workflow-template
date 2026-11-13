# monitoring-v1 plan

1. reply_hook.problems flags a Dependencies body with no == repo == line (REPO regex); the shell fixture gains == toy ==.
2. fresh.py: refresh(common, base) fast-forwards the main checkout; operate.one_pass calls it first and prints its line.
3. Python toys: test-reply-repo-blocks.py, test-silent-worker.py, test-fresh-checkout.py; rows mon14-reply-repo-blocks, mon8-silent-worker, operation-checkout-ff, each seen red with a break.
4. Tests tables re-rendered; wiki current. reply_hook.py stays under 20480 bytes (20219).
Risk: the checkout moving under a running session; it only fast-forwards and never over uncommitted work.
