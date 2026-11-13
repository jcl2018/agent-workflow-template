# macOS-only regression rows skip on Linux and Windows instead of failing (#3832)

- Slug: mac-rows-skip
- Touches: dev/toy, .loop/regression.tsv

## Done lines

Frozen. A wrong done line needs a new goal.

1. A macOS-only row run on Linux exits 77 with its reason, and the Linux scheduled run shows no FAIL that is platform-only

## Verify by hand

1. Run `bash dev/toy/test-local-schedule.sh` on a Linux or Windows host.
   Expect: it prints `SKIP: macOS only ...` and exits 77, with no FAIL line.
2. After release, dispatch the `regression` workflow (Actions tab, or `gh workflow run regression.yml`) and open the Linux run.
   Expect: the 15 `ls-*` rows and `aut-email-secrets` show SKIPPED (cannot run here) and open no issue.

<!-- Numbered steps for a person, each with an Expect: line. A release needs this. -->
