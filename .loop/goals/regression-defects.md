# Fix the failing regression rows filed as defects: prd-new, wiki-no-report, autorelease-no-report, codex-key-commands, codex-harness, codex-skip-77 (#1388 to #1394)

- Slug: regression-defects
- Touches: dev/toy

## Done lines

Frozen. A wrong done line needs a new goal.

1. Each of those regression rows passes, or is a known failure with a written reason, and its defect issue is closed

## Verify by hand

1. Run `out=$(bash dev/toy/test-prd.sh 2>&1); echo "$out" | grep "PASS: an optional Milestone line goes under the title"`.
   Expect: the PASS line prints, so the `prd-new` row's last check finds its line.
2. Run `python3 dev/toy/reap.py` with no arguments on native Windows.
   Expect: a usage message, not an AttributeError about SIGPIPE.
