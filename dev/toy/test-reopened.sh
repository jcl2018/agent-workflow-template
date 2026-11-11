#!/bin/bash
# reads: skills/workflow-regression/scripts/tests.py skills/workflow-setup/scripts/setup.py
here=$(cd "$(dirname "$0")/../.." && pwd)
. "$here/dev/toy/reap.sh"
# REG-6: a reopened issue's defect test shows failing until it passes again. tests.py issues takes the reopen time from
# the issue's GitHub timeline (a sampled state can't see close-then-reopen), keeps it across refreshes, and list shows
# "failing (issue reopened)" until the issue closes again or a run on a later day passes.
# Value: protects=a reopened issue's test is marked failing (REG-6); fails_when=the reopen is read from sampled states,
# dropped on the next refresh or never cleared; why_new=issue states had no reopen; seam=none; no_claim=GitHub's
# timeline API (a stub gh answers it)
set -u
export HOME=$(mktemp -d)
d=$(mktemp -d); toy_on_exit 'rm -rf "$d" "$HOME"'
fails=0
ok() { echo "PASS: $1"; }
bad() { echo "FAIL: $1"; fails=$((fails + 1)); }
cd "$d" && git init -q -b main && git commit -q --allow-empty -m init
mkdir -p .loop bin
printf '# id\tlevel\tcommand\tgoal\tseen_red\tdescription\tcategory\tlink\n' > .loop/regression.tsv
printf 'fx\tland\ttrue\t-\t2026-01-01\tGiven the bug, when it runs, then it stays fixed.\tdefect\thttps://github.com/o/r/issues/7\n' >> .loop/regression.tsv
printf '# id\tstatus\tdate\trun\nfx\tPASS\t2026-01-15\t\n' > .loop/regression-runs.tsv
cat > bin/gh <<'G'
#!/bin/bash
case "$1" in
  auth) exit 0 ;;
  issue) echo "$STUB_STATE" ;;
  api) [[ " $* " == *" repos/o/r/issues/7/events "* ]] && echo "${STUB_REOPENED:-null}" ;;
esac
G
chmod +x bin/gh; export PATH="$d/bin:$PATH"
T="python3 $here/skills/workflow-regression/scripts/tests.py"
STUB_STATE=OPEN STUB_REOPENED=$'2025-12-01T09:00:00Z\n2026-02-01T10:00:00Z' $T issues --write >/dev/null  # two pages: the newest wins
out=$($T list --tsv)
grep -qF "failing (issue reopened) 2026-02-01" <<<"$out" && grep -q "issues/7	open	.*	2026-02-01T10:00:00Z" .loop/regression-issues.tsv \
  && ok "a reopened open issue's test shows failing (issue reopened) with the reopen date" || bad "reopened: $out"
STUB_STATE=OPEN STUB_REOPENED=null $T issues --write >/dev/null
grep -q "failing (issue reopened)" <<<"$($T list --tsv)" && ok "a later refresh keeps the reopen" || bad "reopen dropped on refresh"
printf '# id\tstatus\tdate\trun\nfx\tPASS\t2026-02-02\t\n' > .loop/regression-runs.tsv
! grep -q "failing (issue reopened)" <<<"$($T list --tsv)" && ok "a pass on a later day clears it" || bad "not cleared by a later pass"
printf '# id\tstatus\tdate\trun\nfx\tPASS\t2026-02-01\t\n' > .loop/regression-runs.tsv
STUB_STATE=CLOSED $T issues --write >/dev/null
! grep -q "failing (issue reopened)" <<<"$($T list --tsv)" && ok "the issue closing again clears it" || bad "not cleared by a close"
[ "$fails" = 0 ] && echo "ALL PASS" || { echo "$fails FAILED"; exit 1; }
