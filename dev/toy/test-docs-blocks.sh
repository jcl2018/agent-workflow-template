#!/bin/bash
# reads: skills/workflow-docs/scripts/render.py skills/workflow-docs/scripts/docs.py skills/workflow-docs/scripts/counting.py
# reads: skills/workflow-docs/scripts/criteria.py skills/workflow-docs/scripts/pageformat.py
# reads: skills/workflow-setup/scripts/setup.py skills/workflow-setup/scripts/seed.py skills/workflow-setup/scripts/settings.py
# The generated Settings, Automation and template blocks (render.py): setup inserts them where the page format allows,
# a render only refreshes blocks whose markers already exist, and a commit that only refreshes them stales no page.
# usage: test-docs-blocks.sh [no-insert|format|no-cascade]   no ID runs every part. No model is called.
set -u
unset LOOP_SESSION_TOOL LOOP_OPERATION_SESSION LOOP_BATCH GITHUB_SERVER_URL GITHUB_REPOSITORY GITHUB_RUN_ID
here=$(cd "$(dirname "$0")/../.." && pwd); only=${1:-}
. "$here/dev/toy/reap.sh"
d=${TOY_KEEP:-$(mktemp -d)}; [ -n "${TOY_KEEP:-}" ] || toy_on_exit 'rm -rf "$d"'
export HOME="$d/home" PYTHONDONTWRITEBYTECODE=1; mkdir -p "$HOME"  # setup writes private settings under HOME
want() { [ -z "$only" ] || [ "$only" = "$1" ]; }
fails=0
ok() { echo "PASS: $1"; }
bad() { echo "FAIL: $1"; fails=$((fails + 1)); }
docs="python3 $here/skills/workflow-docs/scripts/docs.py"
render="python3 $here/skills/workflow-docs/scripts/criteria.py render"
"$here/dev/toy/make.sh" "$d/toy" >/dev/null || exit 1
cd "$d/toy/repo" || exit 1
mkdir engine; printf 'def run():\n    return 1\n' > engine/core.py; git add -A; git commit -qm "A code folder"
python3 "$here/skills/workflow-setup/scripts/setup.py" >/dev/null 2>&1  # criteria on (no --bare)
git switch -q main && git merge -q --no-edit workflow-setup || { echo "FAIL: setup did not merge"; exit 1; }
H=docs/wiki/Home.md
marks() { grep -c -e '<!-- settings:begin -->' -e '<!-- automation:begin -->' "$1"; }

# format: setup inserts the blocks into the README and the DOC-4 Home, and the page format passes them.
if want format; then
  [ "$(marks README.md)" = 2 ] && [ "$(marks $H)" = 2 ] && grep -q '<!-- template:begin -->' README.md \
    && ok "setup inserts the blocks into README and Home" || bad "setup did not insert the blocks (README $(marks README.md), Home $(marks $H))"
  [ -z "$(git status --short)" ] && ok "setup leaves the tree clean" || bad "setup left $(git status --short | tr '\n' ' ')"
  out=$($docs check 2>&1)
  grep -E "^(FORMAT (README|Home)|STALE (Settings|Automation|README line))" <<<"$out" && bad "docs.py check refuses the blocks setup inserted" \
    || ok "docs.py check passes the page format on the inserted blocks"
  got=$(cd "$here/skills/workflow-docs/scripts" && python3 - "$d/toy/repo" <<'PY'
import os, sys
import pageformat, render
root = sys.argv[1]  # a README that opens with How to use: the template line lands inside it, which the format must allow
text = "## How to use\n\n### How to use Engine\n\nAsk.\n\n| You say | What happens |\n|---|---|\n| \"Show me engine\" | It shows. |\n"
blocks = dict(render.front_files(root))["README.md"]
print(pageformat.frontdoor(render.with_blocks(text, blocks, True), ["Engine"]) or "clean")
PY
)
  [ "$got" = clean ] && ok "a README with no title paragraph still passes DOC-5 with the blocks in" || bad "DOC-5 on a title-less README: $got"
fi

# no-insert: a repo adopted before the blocks (no markers): a render leaves README and Home byte-identical and check is quiet.
if want no-insert; then
  python3 - README.md $H <<'PY'
import re, sys
for path in sys.argv[1:]:
    text = open(path).read()
    open(path, "w").write(re.sub(r"\n*<!-- (settings|automation|template):begin -->\n.*?<!-- \1:end -->\n", "\n", text, flags=re.S))
PY
  git commit -qam "Adopted before the Settings and Automation blocks"
  cp README.md "$d/readme.before"; cp $H "$d/home.before"
  out=$($render 2>&1) || bad "render failed: $out"
  cmp -s README.md "$d/readme.before" && cmp -s $H "$d/home.before" && ok "a render leaves an unmarked README and Home byte-identical" \
    || bad "a render inserted into an unmarked page: $(git diff --stat | tr '\n' ' ')"
  out=$($docs check 2>&1)
  grep -E "^STALE (Settings|Automation|README line)" <<<"$out" && bad "docs.py check calls a missing block STALE" \
    || ok "docs.py check says nothing of blocks a repo never had"
  git checkout -q -- .
  git reset -q --hard HEAD~1
fi

# no-cascade: a page mapped to README stays fresh after a commit that only refreshes the blocks; a real edit stales it.
if want no-cascade; then
  printf 'Engine\tengine,README.md\nHome\tREADME.md\n' > .loop/docs.tsv
  git commit -qm "Engine also describes the README" -- .loop/docs.tsv
  python3 -c "import json; c = json.load(open('.loop/config.json')); c['health_cron'] = '5 */6 * * *'; json.dump(c, open('.loop/config.json', 'w'), indent=2)"
  git commit -qam "Health every six hours"
  $render >/dev/null 2>&1
  [ -n "$(git status --short README.md)" ] || bad "the render did not refresh the README's Automation block"
  git commit -qm "Refresh the generated blocks" -- README.md $H
  out=$($docs check 2>&1)
  grep -q "^STALE Engine" <<<"$out" && bad "a block-only commit staled Engine: $(grep '^STALE Engine' <<<"$out")" \
    || ok "a commit that only refreshes the blocks leaves README-mapped pages fresh"
  printf '\nA hand-written line.\n' >> README.md; git commit -qm "A real README change" -- README.md
  $docs check 2>&1 | grep -q "^STALE Engine" && ok "a real README change still stales Engine" || bad "a real README change did not stale Engine"
fi
[ "$fails" = 0 ] && echo "ALL PASS" || { echo "$fails FAILED"; exit 1; }
