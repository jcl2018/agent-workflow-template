# wiki-catchup: plan

1. `skills/workflow-docs/scripts/docs.py` `problems()`: read a page's judged commits with `git rev-list --no-merges --full-history`. Done.
2. `dev/toy/test-docs-edit-revert.py`: a repo whose branch edits a page, puts it back and is merged must not be STALE, and a later
   code change must stale it. Row `docs-edit-revert-merged` (land, DOC-9, defect, #3875), seen failing 2026-11-13 by restoring the
   old `rev-list` line. Done.
3. Ship: the release publishes Documentation after the merge (`docs.py publish` from origin/main), which catches the wiki up.
4. Test per done line: line 1 by the toy and by `docs.py check` on the merged head reporting no STALE; line 2 by the toy (its
   wording about a Tests-intro line cannot be met, since Tests is generated; raised with the operation session).
