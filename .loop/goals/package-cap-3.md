# main packages again: dev/package.py passes on main at or under the 100-file Agensi cap with the listing matching, and lanes_cli.py check passes; new modules fold into existing ones with no behaviour change

- Slug: package-cap-3
- Touches: .loop/regression-known.tsv, skills, dev/package.py, dev/toy, .loop/regression.tsv, docs/wiki/Tests.md, docs/wiki/Delivery.md

## Done lines

Frozen. A wrong done line needs a new goal.

1. dev/package.py passes on main at or under 100 files with the listing matching
2. lanes_cli.py check passes
3. the native-Windows lock behaviour from #1398 is kept and its test still passes
4. rows defect-categories, skill-size and size-140 pass on main and any .loop/regression-known.tsv entries for them are removed
5. rows lanes-headers, lanes-repo-narrow, narrow-root-172, prd-repo-green, plan-sizes, pods-size, sync-check-preview and sync-board-lag pass on main and their known entries are removed, or each is handed to a named goal
6. no new file under skills/

## Verify by hand

<!-- Numbered steps for a person, each with an Expect: line. A release needs this. -->
