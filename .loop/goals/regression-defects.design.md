# Design: regression-defects

Six rows were filed as defects. Five (codex-skip-77, codex-harness, codex-key-commands, autorelease-no-report, wiki-no-report) were filed because a CI run ran out of job time ("skipped: out of job time"), not because a test failed; they pass again on a normal Linux run and their issues close on the next passing run. prd-new really failed: it greps a PASS line, "the audit's Milestone fix goes under the title", that milestone-freeform renamed to "an optional Milestone line goes under the title".

Approaches: (A) point the stale row at the renamed line, and make dev/toy/reap.py portable to native Windows so the codex parts can run here; (B) also port slots.py and the other POSIX calls. B belongs to the win-posix-calls work and touches skills/, outside this goal's `dev/toy` touches, so A.

Done line 1: prd-new passes locally (verified). The five skipped rows cannot be run to completion on this Windows PC (os.getuid in slots.py, ps -o in Git Bash), so they are not claimed as passed here; the CI run on Linux decides, and their issues stay open until a passing run closes them.

Open questions: none for the owner.
