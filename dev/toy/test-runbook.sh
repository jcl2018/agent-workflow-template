#!/bin/bash
# reads: skills/workflow-docs/scripts/criteria.py skills/workflow-docs/scripts/docs.py skills/workflow-docs/references/template.md docs/wiki/ .loop/ README.md CLAUDE.md AGENTS.md
# Proves the optional Runbook section (DOC-16) on a copy of this repo's own wiki: a good runbook passes, each missing or
# stray part is refused naming the page, routine and field, a routine in .loop/routines.tsv with no runbook on its page
# is refused, a Reviewed page that gains a Runbook is not locked, and this repo's Health and Regression pages carry the
# runbooks for the health round and the regression round. No network, no model.
# usage: test-runbook.sh [CASE ...]   cases: good refused registry locked repo (default: all)
set -u
unset LOOP_ROLE
here=$(cd "$(dirname "$0")/../.." && pwd)
. "$here/dev/toy/reap.sh"
cases=("$@"); [ ${#cases[@]} -eq 0 ] && cases=(good refused registry locked repo)
T=$(mktemp -d); toy_on_exit 'rm -rf "$T"'
fails=0
ok() { echo "PASS: $1"; }
bad() { echo "FAIL: $1"; fails=$((fails + 1)); }
check() { if eval "$2"; then ok "$1"; else bad "$1"; fi; }
mkdir -p "$T/r" && git -C "$here" ls-files -co --exclude-standard skills docs .loop README.md CLAUDE.md AGENTS.md VERSION listing.json CHANGELOG.md LICENSE |
  tar -C "$here" -cf - -T - | tar -C "$T/r" -xf -
cd "$T/r" || exit 1
git init -q && git add -A && git -c user.email=t@example.test -c user.name=Toy commit -qm base
python3 skills/workflow-docs/scripts/criteria.py render >/dev/null 2>&1
git add -A && git -c user.email=t@example.test -c user.name=Toy commit -qm render
D="python3 skills/workflow-docs/scripts/docs.py check"
P=docs/wiki/Setup.md; cp "$P" "$T/setup.orig"; cp .loop/routines.tsv "$T/routines.orig"
BASE=$($D 2>&1 | sort)  # the copy's own check output (another page may be CHANGED for its owner): a good change adds nothing to it
GOOD='### setup-nightly
- **Serves:** SET-1, SET-7.
- **Schedule:** every night at 02:00, and by hand.
- **Steps:** run the setup check command from the repo root.
- **Full run:** reads the live repo and writes the real report, never a dry run or a fixture.
- **Output:** one report comment on the pinned issue.
- **Never:** never post a sample in place of the report.
- **Check:** the comment names this run and its time.'
# put the text as a ## Runbook section before ## Requirements (after Problem)
place() { python3 - "$P" "$1" <<'PY'
import sys
p, body = sys.argv[1], sys.argv[2]
s = open(p).read()
i = s.index("\n## Requirements")
open(p, "w").write(s[:i] + "\n## Runbook\n\n" + body + "\n" + s[i:])
PY
}
reset() { cp "$T/setup.orig" "$P"; cp "$T/routines.orig" .loop/routines.tsv; }
out() { $D 2>&1; }
without() { printf '%s\n' "$GOOD" | grep -v "^- \*\*$1:\*\*"; }

case_good() {
  reset; check "a page with no Runbook passes" '[ "$(out | sort)" = "$BASE" ]'
  reset; place "$GOOD"; check "a page with a good Runbook passes" '[ "$(out | sort)" = "$BASE" ]'
  reset; place "$GOOD"; check "the Runbook sits in order after Problem and before Requirements" '! out | grep -q "^SECTIONS Setup"'
  reset; python3 - "$P" "$GOOD" <<'PY'
import sys
p, body = sys.argv[1], sys.argv[2]
s = open(p).read()
i = s.index("\n## Problem")
open(p, "w").write(s[:i] + "\n## Runbook\n\n" + body + "\n" + s[i:])
PY
  check "a Runbook before Problem is refused as out of order" 'out | grep -q "^SECTIONS Setup"'
}

refuse() {  # refuse NAME BODY GREP: the body is refused with a DOC-16 line matching GREP
  want=$3; reset; place "$2"; check "refused, naming it: $1" 'out | grep -qF "Runbook: DOC-16 $want"'
}
case_refused() {
  refuse "no Full run field" "$(without 'Full run')" "a 'Full run' field of 5 characters or more under setup-nightly"
  refuse "no Output field" "$(without Output)" "a 'Output' field of 5 characters or more under setup-nightly"
  refuse "a field too short" "$(printf '%s\n' "$GOOD" | sed 's/^- \*\*Never:\*\* .*/- **Never:** no./')" "a 'Never' field of 5 characters or more under setup-nightly"
  refuse "an unknown field" "$GOOD
- **Extra:** something an agent does not need" "only the fields Serves, Schedule, Steps, Full run, Output, Never, Check"
  refuse "prose outside the fields" "$GOOD
Some loose words." "only '- **Field:** text' lines, with indented continuation"
  refuse "no subsection" "- **Serves:** SET-1 alone, with no routine heading" "a '### <routine>' heading before any field"
  refuse "a field given twice" "$GOOD
- **Output:** a second output line that should not be here" "each field once under setup-nightly"
  refuse "a routine given twice" "$GOOD

$GOOD" "each routine once"
  refuse "a short Serves is still accepted but an empty one is not" "$(printf '%s\n' "$GOOD" | sed 's/^- \*\*Serves:\*\* .*/- **Serves:**/')" "a 'Serves' field of 5 characters or more under setup-nightly"
  refuse "an unknown Serves id" "$(printf '%s\n' "$GOOD" | sed 's/^- \*\*Serves:\*\* .*/- **Serves:** ZZZ-99 nonsense./')" "a Serves id that a page defines"
  refuse "a Serves field with no id" "$(printf '%s\n' "$GOOD" | sed 's/^- \*\*Serves:\*\* .*/- **Serves:** whatever it needs./')" "a Serves field naming a requirement id"
  reset; place "$(printf '%s\n' "$GOOD" | sed 's/^- \*\*Serves:\*\* .*/- **Serves:** the setup checks, see\n  SET-1 and SET-7./')"
  check "an id on a continuation line of Serves counts" '[ "$(out | sort)" = "$BASE" ]'
  reset; place "$GOOD"; printf '\n## After\n' >> docs/wiki/Regression.md
  check "a misordered page gives its SECTIONS finding and no false Serves finding" 'out | grep -q "^SECTIONS Regression" && ! out | grep -q "a Serves id"'
  git checkout -q docs/wiki/Regression.md
  refuse "a bad routine name" "$(printf '%s\n' "$GOOD" | sed 's/^### setup-nightly/### Setup Nightly/')" "a routine name of lowercase letters, digits and hyphens"
  reset; place "$GOOD"; python3 - "$P" <<'PY'
import sys
p = sys.argv[1]; s = open(p).read()
i = s.index("\n## Runbook"); j = s.index("\n## Requirements")
book = s[i:j]; s = s[:i] + s[j:]
k = s.index("\n## Tests")
open(p, "w").write(s[:k] + book + s[k:] + "\n## After\n")
PY
  check "a section placed after Tests is refused as out of order, and only once: not also reported as no runbook" 'out | grep -q "^SECTIONS Setup" && ! out | grep -q "got none"'
  cp "$P" "$T/after.md"; python3 skills/workflow-docs/scripts/criteria.py render >/dev/null 2>&1
  check "a render leaves a page with a section after Tests as it was, never cutting it off" 'grep -q "^## Runbook" "$P" && grep -q "^## After" "$P"'
  reset; place ""; check "an empty section is refused" 'out | grep -qF "Runbook: DOC-16 at least one"'
  reset; place "$(printf '%s\n' "$GOOD" | sed 's/^- \*\*Steps:\*\* .*/- **Steps:** run the check\n  and read its output to the end./')"
  check "an indented line continues a field and passes" '[ "$(out | sort)" = "$BASE" ]'
}

case_registry() {
  reset; printf 'setup-nightly\tSetup\n' >> .loop/routines.tsv
  check "a routine in the registry with no runbook on its page is refused" 'out | grep -qF "Setup:1: Runbook: DOC-16 a '"'"'### setup-nightly'"'"' runbook"'
  place "$GOOD"; check "the same routine passes once its page carries the runbook" '[ "$(out | sort)" = "$BASE" ]'
  reset; printf 'setup-nightly\tSetup\nsetup-nightly\tSetup\n' >> .loop/routines.tsv; place "$GOOD"
  check "a routine listed twice in the registry is refused" 'out | grep -qF "routines.tsv:" && out | grep -qF "each routine once"'
  reset; printf '# comment\n' >> .loop/routines.tsv; printf 'setup-nightly\tSetup\n' >> .loop/routines.tsv; place "  ### setup-nightly
$(printf '%s\n' "$GOOD" | sed 1d)"
  check "an indented heading inside another block does not count as the runbook" 'out | grep -qF "a '"'"'### setup-nightly'"'"' runbook"'
  reset; printf 'ghost-routine\tNoSuchPage\n' >> .loop/routines.tsv
  check "a registry row naming no page is refused" 'out | grep -qF "Runbook: DOC-16 a routine on a feature page"'
  reset; rm -f .loop/routines.tsv; check "with no registry file the check still passes" '[ "$(out | sort)" = "$BASE" ]'
}

case_locked() {
  M=docs/wiki/Monitoring.md; cp "$M" "$T/mon.orig"
  python3 - "$M" "$GOOD" <<'PY'
import sys
p, body = sys.argv[1], sys.argv[2]
s = open(p).read()
i = s.index("\n## Requirements")
open(p, "w").write(s[:i] + "\n## Runbook\n\n" + body + "\n" + s[i:])
PY
  check "a Reviewed page that gains a Runbook is not locked, marked changed or called out of order" 'grep -q "^## Runbook" "$M" && [ "$(out | grep -E "^(LOCKED|CHANGED|SECTIONS) Monitoring" | sort)" = "$(grep -E "^(LOCKED|CHANGED|SECTIONS) Monitoring" <<<"$BASE")" ]'
  python3 - "$M" <<'PY'
import sys
p = sys.argv[1]; s = open(p).read()
open(p, "w").write(s.replace("\n## Runbook\n", "\n## Requirements\n", 1))
PY
  check "positive control: the same page with its sections broken is called out" 'out | grep -q "^SECTIONS Monitoring"'
  cp "$T/mon.orig" "$M"
}

case_repo() {
  for pair in "Health:health-round" "Regression:regression-round"; do
    page=${pair%%:*}; routine=${pair##*:}
    check "$page carries the $routine runbook with every field" "python3 - $here/docs/wiki/$page.md $routine <<'PY'
import re, sys
text = open(sys.argv[1]).read()
sec = text.split('\n## Runbook\n', 1)[1].split('\n## ', 1)[0]
sub = sec.split('### ' + sys.argv[2] + '\n', 1)[1].split('\n### ', 1)[0]
for field in ('Serves', 'Schedule', 'Steps', 'Full run', 'Output', 'Never', 'Check'):
    assert re.search(r'^- \*\*' + field + r':\*\* \S', sub, re.M), field
PY"
    check "$page's $routine runbook says a full run is live and a fixture never stands in" "python3 - $here/docs/wiki/$page.md $routine <<'PY'
import re, sys
sub = open(sys.argv[1]).read().split('### ' + sys.argv[2] + '\n', 1)[1].split('\n### ', 1)[0].split('\n## ', 1)[0]
full = re.search(r'^- \*\*Full run:\*\* (.*)', sub, re.M).group(1).lower()
never = re.search(r'^- \*\*Never:\*\* (.*)', sub, re.M).group(1).lower()
assert 'live' in full or 'every' in full
assert 'fixture' in never or 'dry run' in never or 'subset' in never
need = {'health-round': ('anthropic_api_key', 'judge_command', 'feature_labels', 'not run on the runner'), 'regression-round': ('exits 77', 'not a full run', 'feature_labels', 'draft and covered')}[sys.argv[2]]
missing = [word for word in need if word not in (full + ' ' + sub.lower())]
assert not missing, missing
PY"
  done
  check "the registry names both routines on their pages" 'grep -q "^health-round[[:space:]]Health$" '"$here"'/.loop/routines.tsv && grep -q "^regression-round[[:space:]]Regression$" '"$here"'/.loop/routines.tsv'
}

for c in "${cases[@]}"; do
  case "$c" in good|refused|registry|locked|repo) "case_$c" ;; *) echo "test-runbook.sh: no case '$c'; usage: test-runbook.sh [good|refused|registry|locked|repo]" >&2; exit 2 ;; esac
done
[ $fails = 0 ] || { echo "$fails FAILED"; exit 1; }
echo "ALL PASS"
