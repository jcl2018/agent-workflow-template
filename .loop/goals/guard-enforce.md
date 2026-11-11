# The private-name scan the template promises actually runs: setup installs a commit and pre-push check in every loop repo that scans the change against the repo's private pattern, and a push that skips the hooks is caught, so DEL-9 and SET-8 move from not enforced to enforced (owner, 2026-11-11: "create that milestone and plan ... deliver it as fast as possible"; guardrails-prd found DEL-9 and SET-8 not enforced)

- Slug: guard-enforce
- Touches: skills/workflow-setup, skills/workflow-delivery, dev/toy, .loop/regression.tsv, docs/wiki/Setup.md, docs/wiki/Delivery.md, skills/workflow-release, skills/workflow-health, listing.json, docs/wiki/Tests.md

## Done lines

Frozen. A wrong done line needs a new goal.

1. Setup installs a pre-commit and a pre-push hook that refuse a change whose added lines match the repo's private pattern, naming the file and line but never printing the match, and the pattern itself stays out of the repo
2. A push made with hooks skipped is caught before merge: the operation's merge step (merge.py) reruns the same scan on the pull request diff and refuses with a fix line
3. The hooks and the merge-step scan are installed by setup and checked by health, which flags a loop repo missing them
4. DEL-9 and SET-8 each have a regression row seen failing on a planted private line, then passing, and their Tests rows read enforced

## Verify by hand

<!-- Numbered steps for a person, each with an Expect: line. A release needs this. -->
