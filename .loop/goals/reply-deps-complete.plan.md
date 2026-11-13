# reply-deps-complete plan

1. checkin.expected(): (repo, slug) of every live goal and queued line of the pod.
2. reply_deps.py: missing(text, cwd) compares the Dependencies body, block by block, with that set.
3. reply_hook.left_out() calls it in the stop hook and in the check subcommand, failing open; reply_hook.py stays at 20432 bytes (cap 20480).
4. Toy test-reply-deps.py (8 cases), row mon14-reply-deps-whole seen red; Tests tables and wiki current.
Risk: a slow or failing board read; the hook fails open.
