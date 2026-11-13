# reply-deps-complete design

Problem: the owner wants the check-in Dependencies graph to show the whole picture. M9 checked the == repo == blocks only; a reply could still drop a running, holding or queued goal.

Approaches: (1) a new reply_deps.py that compares the reply's Dependencies section with checkin.expected(), the live goals and queued lines read from the run records and queue files (chosen: deterministic, outside the near-cap reply_hook.py); (2) ask the model to self-check (not enforceable).

Done line: a reply whose Dependencies drops a goal is flagged by name; a complete reply passes.

Scope note: the expected set is every live goal and queued line the check-in itself draws (running, holding, silent, waiting, awaiting merge, queued), per repo block. Idle pool sessions with no goal are not goals and are not required.

Open questions: none.
