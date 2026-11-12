#!/bin/bash
# reads: skills/workflow-docs/scripts/deployments.py skills/workflow-docs/scripts/audit.py skills/workflow-docs/scripts/counting.py skills/workflow-docs/scripts/criteria.py skills/workflow-docs/scripts/docs.py skills/workflow-docs/scripts/entry.py skills/workflow-docs/scripts/pageformat.py skills/workflow-docs/scripts/prd.py skills/workflow-docs/scripts/render.py
# reads: skills/workflow-docs/references/template.md docs/wiki/ .loop/ README.md CLAUDE.md AGENTS.md
# reads: skills/workflow-monitoring/scripts/govern_hook.py skills/workflow-monitoring/scripts/reply_hook.py
# Proves the optional Deployments section (DOC-14) on a copy of this repo's own wiki: a page with or without it passes,
# each malformed table is refused naming the table and column, the section never locks a Reviewed page, review and
# render keep it; and issue 495 (the govern hook passes `git pull --ff-only`, refuses other pulls). No network.
# usage: test-deployments.sh [CASE ...]   cases: section refused locked doc14 pull readme (default: all)
set -u
unset LOOP_ROLE LOOP_GOVERN_HOOK
here=$(cd "$(dirname "$0")/../.." && pwd)
. "$here/dev/toy/reap.sh"
cases=("$@"); [ ${#cases[@]} -eq 0 ] && cases=(section refused locked doc14 pull readme)
T=$(mktemp -d); toy_on_exit 'rm -rf "$T"'
fails=0
ok() { echo "PASS: $1"; }
bad() { echo "FAIL: $1"; fails=$((fails + 1)); }
check() { if eval "$2"; then ok "$1"; else bad "$1"; fi; }
mkdir -p "$T/r" && git -C "$here" ls-files skills docs .loop README.md CLAUDE.md AGENTS.md VERSION listing.json CHANGELOG.md LICENSE |
  tar -C "$here" -cf - -T - | tar -C "$T/r" -xf -
cd "$T/r" || exit 1
git init -q && git add -A && git -c user.email=t@example.test -c user.name=Toy commit -qm base
python3 skills/workflow-docs/scripts/criteria.py render >/dev/null 2>&1  # the generated Tests page follows this copy's history
git add -A && git -c user.email=t@example.test -c user.name=Toy commit -qm render
D="python3 skills/workflow-docs/scripts/docs.py check"
n=$(python3 -c "import sys; sys.path.insert(0, 'skills/workflow-docs/scripts'); import docs; print(len(docs.read_map('.')))")  # the wiki's pages, counted, not remembered
P=docs/wiki/Setup.md; cp "$P" "$T/setup.orig"
GOOD_PAGE='| Page | Link | Access | Shows | Live build |
|---|---|---|---|---|
| Site | https://example.test/app | public | the setup guide | `1a2b3c4d` |'
GOOD_DELIVERY="| Delivery | Channel | Recipients | What's sent | Status |
|---|---|---|---|---|
| Newsletter | email | subscribers | the weekly PDF | live |"
# put SECTION_TEXT as ## Deployments before ## Tests (or, with "early", before ## Success metrics)
place() { python3 - "$P" "$1" "${2:-}" <<'PY'
import sys
p, body, where = sys.argv[1], sys.argv[2], sys.argv[3]
s = open(p).read()
mark = "\n## Success metrics" if where == "early" else "\n## Tests"
i = s.index(mark)
open(p, "w").write(s[:i] + "\n## Deployments\n\n" + body + "\n" + s[i:])
PY
}
reset() { cp "$T/setup.orig" "$P"; }
out() { $D 2>&1; }

case_section() {
  reset; check "a page without Deployments passes" '[ "$(out | tail -1)" = "DOCS OK: $n pages" ]'
  reset; place "$GOOD_PAGE"; check "a page with a good Page table passes" '[ "$(out | tail -1)" = "DOCS OK: $n pages" ]'
  reset; place "$GOOD_DELIVERY"; check "a page with a good Delivery table passes" '[ "$(out | tail -1)" = "DOCS OK: $n pages" ]'
  reset; place "$GOOD_PAGE

$GOOD_DELIVERY"; check "a page with both tables passes" '[ "$(out | tail -1)" = "DOCS OK: $n pages" ]'
  reset; place "$GOOD_PAGE"; python3 - "$P" <<'PY'
import sys
p = sys.argv[1]; s = open(p).read()
if "\n## Usage\n" not in s:
    s = s.replace("\n## Requirements\n", "\n## Usage\n\n- `/workflow-setup settings` — prints the settings table.\n\n## Requirements\n", 1)
open(p, "w").write(s)
PY
  check "a page with both Usage and Deployments passes the order check" '! out | grep -q "^SECTIONS Setup"'
  reset; place "$GOOD_PAGE" early; check "Deployments before Success metrics is refused as out of order" 'out | grep -q "^SECTIONS Setup: .*want .*Success metrics, Deployments, Tests"'
}

refuse() {  # refuse NAME BODY GREP: the body is refused with a DOC-14 line matching GREP
  want="$3"; reset; place "$2"; check "refused, naming it: $1" 'out | grep -qF "Deployments: DOC-14 $want"'
}
case_refused() {
  refuse "prose in the section" "Some words.
$GOOD_PAGE" "only a Page table, a Delivery table and blank lines"
  refuse "an empty section" "" "a Page or Delivery table with at least one row"
  refuse "an unknown header" "| Page | URL | Access | Shows | Live build |
|---|---|---|---|---|
| Site | https://x.test | public | home | \`1a2b3c4\` |" "a table header of exactly the Page or Delivery columns"
  refuse "two Page tables" "$GOOD_PAGE

$GOOD_PAGE" "at most one Page table"
  refuse "a table with no row" "| Page | Link | Access | Shows | Live build |
|---|---|---|---|---|" "at least one row in the Page table"
  refuse "a row with the wrong cell count" "| Page | Link | Access | Shows | Live build |
|---|---|---|---|---|
| Site | https://x.test | public | home |" "5 cells in each Page row"
  refuse "an empty Shows cell" "| Page | Link | Access | Shows | Live build |
|---|---|---|---|---|
| Site | https://x.test | public |  | \`1a2b3c4\` |" "every Page cell filled (got empty Shows)"
  refuse "a Link that is not a URL" "| Page | Link | Access | Shows | Live build |
|---|---|---|---|---|
| Site | x.test/app | public | home | \`1a2b3c4\` |" "Page Link a full https URL"
  refuse "Access that is not public or sign-in" "| Page | Link | Access | Shows | Live build |
|---|---|---|---|---|
| Site | https://x.test | everyone | home | \`1a2b3c4\` |" "Page Access public or sign-in"
  refuse "a Live build that is not a sha" "| Page | Link | Access | Shows | Live build |
|---|---|---|---|---|
| Site | https://x.test | sign-in | home | latest |" "Page Live build a 7 to 40 hex sha in backticks"
  refuse "an http (not https) Link" "| Page | Link | Access | Shows | Live build |
|---|---|---|---|---|
| Site | http://x.test | public | home | \`1a2b3c4\` |" "Page Link a full https URL"
  refuse "a Live build sha without backticks" "| Page | Link | Access | Shows | Live build |
|---|---|---|---|---|
| Site | https://x.test | public | home | 1a2b3c4 |" "Page Live build a 7 to 40 hex sha in backticks"
  refuse "a Link with a user and password" "| Page | Link | Access | Shows | Live build |
|---|---|---|---|---|
| Site | https://bob:hunter2@x.test/app | public | home | \`1a2b3c4\` |" "Page Link a full https URL with no user, password or token"
  check "the refused link is never printed" '! out | grep -q "hunter2"'
  reset; place "see https://x.test/?token=synthetic-demo or write ops@example.test
$GOOD_PAGE"
  check "prose in the section is refused without echoing a token or address" 'o=$(out); echo "$o" | grep -qF "Deployments: DOC-14 only a Page table" && ! echo "$o" | grep -q "synthetic-demo\|ops@example.test"'
  refuse "a table with no separator row" "| Page | Link | Access | Shows | Live build |
| Site | https://x.test | public | home | \`1a2b3c4\` |" "a separator row under the Page header"
  for q in "?access_token=abc" "?api_key=abc" "#access_token=abc" ";token=abc"; do
    refuse "a Link carrying $q" "| Page | Link | Access | Shows | Live build |
|---|---|---|---|---|
| Site | https://x.test/app$q | public | home | \`1a2b3c4\` |" "Page Link a full https URL with no user, password or token"
  done
  refuse "a dotless address in Recipients" "| Delivery | Channel | Recipients | What's sent | Status |
|---|---|---|---|---|
| Newsletter | email | bob@localhost | the PDF | live |" "Delivery Recipients a group, never an address"
  refuse "a Link with a token" "| Page | Link | Access | Shows | Live build |
|---|---|---|---|---|
| Site | https://x.test/app?token=abc123 | public | home | \`1a2b3c4\` |" "Page Link a full https URL with no user, password or token"
  refuse "an email address in another Delivery cell" "| Delivery | Channel | Recipients | What's sent | Status |
|---|---|---|---|---|
| Newsletter | email from ops@example.test | subscribers | the PDF | live |" "Delivery Recipients a group, never an address"
  refuse "an email address in Recipients" "| Delivery | Channel | Recipients | What's sent | Status |
|---|---|---|---|---|
| Newsletter | email | someone@example.test | the PDF | live |" "Delivery Recipients a group, never an address"
  check "the refused address is never printed" '! out | grep -q "someone@example.test"'
}

case_locked() {
  reset; place "$GOOD_PAGE"; o=$(out)
  check "a Deployments section on a Reviewed page is neither LOCKED nor CHANGED" 'echo "$o" | grep -q "^DOCS OK" && ! echo "$o" | grep -q "^LOCKED Setup\|^CHANGED Setup"'
  check "the owner's review works on a page with Deployments" 'LOOP_OWNER_WORDS=toy python3 skills/workflow-docs/scripts/criteria.py review Setup --user 2>&1 | grep -q "REVIEWED PAGE Setup"'
  before=$(sed -n "/^## Deployments/,/^## Tests/p" "$P"); python3 skills/workflow-docs/scripts/criteria.py render >/dev/null 2>&1
  check "render keeps the Deployments section byte for byte" '[ "$(sed -n "/^## Deployments/,/^## Tests/p" "$P")" = "$before" ]'
  python3 - "$P" <<'PY'
import sys
p = sys.argv[1]; s = open(p).read(); head, _, tests = s.partition("\n## Tests\n")
open(p, "w").write(head + "\n## Tests\n" + tests.replace("| requirement |", "| stale |", 1))
PY
  python3 skills/workflow-docs/scripts/criteria.py render >/dev/null 2>&1
  check "render rewrites a stale Tests table on a page with Deployments" '! grep -q "| stale |" "$P" && [ "$(out | tail -1)" = "DOCS OK: $n pages" ]'
}

case_doc14() {
  reset
  check "the Documentation page carries DOC-14, Reviewed, with both owner messages" \
    'grep -q "^- DOC-14: \*\*Reviewed " docs/wiki/Documentation.md && grep -q "or a delivery people receive (for example a scheduled email)" docs/wiki/Documentation.md && grep -q "the live build (the sha in build.txt)" docs/wiki/Documentation.md'
  check "this repo's docs check passes with DOC-14" '[ "$(out | tail -1)" = "DOCS OK: $n pages" ]'
}

pull() { printf '%s' "$1" | python3 skills/workflow-monitoring/scripts/govern_hook.py check; }
case_pull() {
  check "#495: git pull --ff-only passes, also with -C and a remote" '[ "$(pull "git pull --ff-only")" = PASS ] && [ "$(pull "git -C . pull origin main --ff-only")" = PASS ]'
  check "#495 negative control: plain git pull is still refused" '[ "$(pull "git pull")" = "BLOCK: git pull" ]'
  check "#495 negative control: -r, --rebase=merges, --no-ff and --ff-only --rebase are refused" \
    '[ "$(pull "git pull -r")$(pull "git pull --rebase=merges")$(pull "git pull --no-ff")$(pull "git pull --ff-only --rebase")" = "BLOCK: git pullBLOCK: git pullBLOCK: git pullBLOCK: git pull" ]'
  check "#495 negative control: --ff after --ff-only, a +refspec, -f and a -c, --config-env or GIT_CONFIG fetch override are refused (git takes the last flag)" \
    '[ "$(pull "git pull --ff-only --ff")$(pull "git pull --ff-only origin +main:main")$(pull "git pull --ff-only -f")$(pull "git -c remote.origin.fetch=+refs/heads/main:refs/heads/main pull --ff-only origin")$(pull "git --config-env=remote.origin.fetch=V pull --ff-only")$(pull "GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=remote.origin.fetch GIT_CONFIG_VALUE_0=+refs/heads/main:refs/heads/main git pull --ff-only")" = "BLOCK: git pullBLOCK: git pullBLOCK: git pullBLOCK: git pullBLOCK: git pullBLOCK: git pull" ]'
}

case_readme() {
  # every command the README shows in a text block appears in a wiki page's Usage, or the README stops naming it
  missing=$(python3 - <<'PY'
import glob, re
text = open("README.md").read()
want = {m.group(1) for block in re.findall(r"```text\n(.*?)```", text, re.S) for line in block.splitlines()
        for m in [re.match(r"^(/workflow-[a-z]+(?: [a-z-]+)?)", line.strip())] if m}
usage = "".join(open(f).read().partition("## Usage")[2].partition("\n## ")[0] for f in glob.glob("docs/wiki/*.md"))
print(" ".join(sorted(c for c in want if "`" + c not in usage)))
PY
)
  check "every command the README names appears in a page's Usage (missing: ${missing:-none})" '[ -z "$missing" ]'
}

for c in "${cases[@]}"; do "case_$c"; done
[ "$fails" -eq 0 ] && echo "ALL PASS" || echo "$fails FAILED"
[ "$fails" -eq 0 ]
