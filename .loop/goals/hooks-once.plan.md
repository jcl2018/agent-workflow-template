# hooks-once plan

Files (confirmed): skills/workflow-setup/scripts/agents.py reply_hook (the `mine` matcher); setup.py --reply-hook/--govern-hook call it (unchanged); new dev/toy/test-hooks-once.py; row set13-hooks-once.

Steps: 1. normalize backslashes in `mine` (done). 2. Toy: reply, govern, reply, govern leave one each; a repeat prints "already installed"; a file with two govern hooks ends with one. 3. Row seen red (the toy failed with the matcher unchanged on this PC).

Could break: the matcher is used for --remove too, which now also finds Windows entries (wanted). Out of scope: workflow-monitoring hooks themselves.
