#!/bin/bash
# reads: skills/workflow-regression/scripts/regression.py skills/workflow-regression/scripts/lanes.py
# reads: skills/workflow-regression/scripts/narrow.py skills/workflow-regression/scripts/lanes_cli.py
# reads: skills/workflow-setup/scripts/setup.py dev/toy/check-reads.sh
# Proves narrow rows: # reads: headers map a change to only the rows whose closure reaches it, anything the mapping
# cannot work out reruns every time, a table edit reruns only what reads the table, and check-reads.sh fails a run
# that read a skill file outside its row's closure. No model is called. usage: test-narrow.sh [DIR]
set -u
unset GITHUB_SERVER_URL GITHUB_REPOSITORY GITHUB_RUN_ID  # run cells and rendered Tests never depend on the runner
unset LOOP_SESSION_TOOL LOOP_OPERATION_SESSION GH_TOKEN GITHUB_TOKEN
here=$(cd "$(dirname "$0")/../.." && pwd)
. "$here/dev/toy/reap.sh"
export HOME=$(mktemp -d)
d=${1:-$(mktemp -d)}; rm -rf "$d"; mkdir -p "$d"
[ -n "${1:-}" ] || toy_on_exit 'rm -rf "$d" "$HOME"'
"$here/dev/toy/make.sh" "$d" >/dev/null || exit 1
export LOOP_FLOW="$d/flow.json" PATH="$here/dev/toy/fakegh:$PATH" FAKE_GH_DIR="$d/gh" TOY_LOG="$d/ran.log"
reg="python3 $here/skills/workflow-regression/scripts/regression.py"
cd "$d/repo" || exit 1
python3 "$here/skills/workflow-setup/scripts/setup.py" --bare >/dev/null
git switch -q main; git merge -q --no-edit workflow-setup
fails=0
ok() { echo "PASS: $1"; }
bad() { echo "FAIL: $1"; fails=$((fails + 1)); }
check() { if eval "$2"; then ok "$1"; else bad "$1"; fi; }
ran() { sort "$TOY_LOG" 2>/dev/null | tr '\n' ' '; }
fresh() { : > "$TOY_LOG"; }
common=$(cd "$(git rev-parse --git-common-dir)" && pwd)
# Value: protects=a lane on a repo with no rows passes; fails_when=--reuse with no rows exits non-zero like a plain run;
# why_new=every other run has rows; seam=none; no_claim=none beyond protects
out=$($reg run land --reuse); rc=$?
check "a reusing run with no rows passes (NO ROWS, exit 0)" '[ $rc = 0 ] && grep -q "^NO ROWS: nothing to run" <<<"$out"'

# Three rows: a reads src/a.txt, b sources dev/lib.sh which reads src/b.txt, c names no repo path (always runs).
mkdir -p dev src
printf 'ok\n' > src/a.txt; printf 'ok\n' > src/b.txt
printf 'echo a >> "$TOY_LOG"; grep -q ok src/a.txt\n' > dev/a.sh
printf '. dev/lib.sh\necho b >> "$TOY_LOG"\n' > dev/b.sh
printf 'grep -q ok src/b.txt || exit 1\n' > dev/lib.sh
printf '# id\tlevel\tcommand\tgoal\tseen_red\tdescription\tcategory\tlink\n' > .loop/regression.tsv
printf 'a\tland\tbash dev/a.sh\tX-1\t2026-01-01\tA works.\tcriterion\t\n' >> .loop/regression.tsv
printf 'b\tland\tbash dev/b.sh\tX-1\t2026-01-01\tB works.\tcriterion\t\n' >> .loop/regression.tsv
printf 'c\tnightly\techo c >> "$TOY_LOG"\tX-1\t2026-01-01\tC works.\tcriterion\t\n' >> .loop/regression.tsv
git add -A; git commit -qm "Rows"; git push -q origin main

echo "== narrow: # reads: headers map a change to the rows whose closure reaches it"
L="python3 $here/skills/workflow-regression/scripts/lanes_cli.py"
n="$d/narrow"; mkdir -p "$n/skills/a/scripts" "$n/skills/b/scripts" "$n/dev" "$n/tools" "$n/.loop"
printf 'open("data.md")\n' > "$n/skills/a/scripts/a.py"; printf 'data\n' > "$n/skills/a/scripts/data.md"
printf 'import helper\n' > "$n/skills/b/scripts/b.py"; printf 'X = 1\n' > "$n/skills/b/scripts/helper.py"
printf 'Y = 1\n' > "$n/skills/b/scripts/solo.py"; printf 'x\n' > "$n/tools/x.txt"
printf 'echo common\n' > "$n/dev/common.sh"; printf 'm=skills/b/scripts\n' > "$n/dev/tm-lib.sh"
printf '#!/bin/bash\n# reads: skills/a/scripts/a.py\n. dev/common.sh; python3 skills/a/scripts/a.py\n' > "$n/dev/ta.sh"  # lanes: no read (toy repo file)
printf '#!/bin/bash\n# reads: skills/b/scripts/b.py\n. dev/common.sh; python3 skills/b/scripts/b.py\n' > "$n/dev/tb.sh"  # lanes: no read (toy repo file)
printf '#!/bin/bash\n# reads: skills/b/scripts/b.py\n. dev/common.sh; . dev/tm-lib.sh\npython3 $m/b.py; python3 $m/solo.py\n' > "$n/dev/tm.sh"  # lanes: no read (toy repo file)
printf '#!/bin/bash\n# reads: skills/a/scripts/gone.py\n. dev/common.sh\n' > "$n/dev/tx.sh"  # lanes: no read (toy repo file)
printf '#!/bin/bash\n# reads: skills/a/scripts/a.py\n. dev/common.sh; (cd skills/b/scripts && true); python3 skills/a/scripts/a.py\n' > "$n/dev/tf.sh"  # lanes: no read (toy repo file)
printf '#!/bin/bash\n. dev/common.sh; python3 skills/a/scripts/a.py\n' > "$n/dev/tu.sh"  # lanes: no read (toy repo file)
printf '#!/bin/bash\n# reads: skills/a/scripts/data.md\n. dev/common.sh; for f in tools/*; do cat "$f"; done\n' > "$n/dev/th.sh"  # lanes: no read (toy repo file)
printf '# id\tlevel\tcommand\n' > "$n/.loop/regression.tsv"
for r in ta tb tm tx tf tu th; do printf '%s\tland\tbash dev/%s.sh\n' $r $r >> "$n/.loop/regression.tsv"; done
aff() { $L affected --root "$n" "$@" | head -1 | sed 's/^AFFECTED [0-9]* of [0-9]* rows (\(.*\))$/\1/'; }
# Value: protects=a declared script's rows rerun on its declared file and not on another skill's file; fails_when=the
# narrow closure widens to the skill folder or drops declared files; why_new=every earlier lanes check is wide; seam=none;
# no_claim=real repo scripts (toy stand-ins)
check "a change to a declared skill file reruns only the rows whose closure reaches it" '[ "$(aff skills/a/scripts/a.py)" = "ta, tf, tu, tx" ] && [ "$(aff skills/a/scripts/data.md)" = "ta, tf, th, tu, tx" ]'
check "a change to another skill's file does not rerun a declared script's rows" '! aff skills/b/scripts/helper.py | grep -qw ta && [ "$(aff skills/b/scripts/helper.py)" = "tb, tf, tm, tx" ]'
# Value: protects=a file used through a folder variable set in another file still reruns its row; fails_when=the
# base-name rule is dropped or reads only the declaring script; why_new=no folder-variable case; seam=none; no_claim=names built at run time
check "an undeclared file used through a folder variable set in another file reruns its row" '[ "$(aff skills/b/scripts/solo.py)" = "tf, tm, tx" ]'
# Value: protects=a row whose declaration cannot be resolved reruns on a mapped change that does not touch it;
# fails_when=a declaration problem stops making the row always; why_new=new rule; seam=none; no_claim=none beyond protects
check "a row whose declaration cannot be resolved reruns on a change that does not touch it" 'out=$($L affected --root "$n" tools/x.txt); [ "$(aff tools/x.txt)" = "tf, th, tx" ] && grep -q "^ALWAYS tx: LANES-DECL-MISSING" <<<"$out" && grep -q "^ALWAYS tf: LANES-DECL-FOLDER" <<<"$out"'
# Value: protects=a change every row reaches reruns all, an unread file is a full run; fails_when=the narrow branch
# drops sourced helpers or the UNMAPPED rule; why_new=only the wide branch had these; seam=none; no_claim=none beyond protects
check "a narrow change reruns only its rows and a change every row reaches reruns all" '[ "$(aff skills/b/scripts/solo.py)" = "tf, tm, tx" ] && [ "$(aff dev/common.sh)" = "ta, tb, tf, th, tm, tu, tx" ]'
printf 'new\n' > "$n/src.txt"
check "a file no row reads is a full run (UNMAPPED)" '$L affected --root "$n" src.txt | grep -q "^UNMAPPED src.txt: the rows that name it"'
out=$($L check --root "$n" dev/tx.sh dev/tf.sh dev/tu.sh); rc=$?
check "lanes_cli.py check names each problem with its code, file:line and a fix line" '[ $rc = 1 ] && grep -q "^LANES-DECL-MISSING dev/tx.sh:2: declared path does not exist: skills/a/scripts/gone.py" <<<"$out" && grep -q "^LANES-DECL-FOLDER dev/tf.sh:3: names skills/b/scripts/" <<<"$out" && grep -q "^LANES-DECL-NONE dev/tu.sh:1" <<<"$out" && [ "$(grep -c "^fix: " <<<"$out")" = 3 ]'
check "deps --why prints the chain from the command to a file" '[ "$($L deps --root "$n" "bash dev/tm.sh" --why skills/b/scripts/helper.py)" = "dev/tm.sh -> skills/b/scripts/b.py -> skills/b/scripts/helper.py" ]'
# Value: protects=glob reads and split quoting are seen; fails_when=the "$here"/ form or the glob rule is dropped;
# why_new=no test used them; seam=none; no_claim=bash reads by names built at run time
printf '#!/bin/bash\n# reads: skills/b/scripts/b.py\nhere=.; for f in "$here"/skills/b/scripts/*.py; do wc -c < "$f"; done\n' > "$n/dev/tg.sh"  # lanes: no read (toy repo file)
printf '#!/bin/bash\n# reads: skills/a/scripts/\npython3 skills/a/scripts/a.py\n' > "$n/dev/tv.sh"  # lanes: no read (toy repo file)
printf '#!/bin/bash\n. dev/common.sh\n# reads: skills/a/scripts/a.py\n' > "$n/dev/tp.sh"  # lanes: no read (toy repo file)
out=$($L check --root "$n" dev/tg.sh dev/tv.sh dev/tp.sh)
check "a glob over a skill folder must declare that folder; an unbacked folder or a late header is refused" 'grep -q "^LANES-DECL-GLOB dev/tg.sh" <<<"$out" && grep -q "^LANES-DECL-FOLDER-UNBACKED dev/tv.sh:2" <<<"$out" && grep -q "^LANES-DECL-PLACE dev/tp.sh:3" <<<"$out"'
printf '#!/bin/bash\n# reads: skills/b/scripts/\nhere=.; for f in "$here"/skills/b/scripts/*.py; do wc -c < "$f"; done\n' > "$n/dev/tg.sh"  # lanes: no read (toy repo file)
check "a declared globbed folder is a prefix: a new file in it is a dependency" '$L deps --root "$n" "bash dev/tg.sh" | grep -qx "skills/b/scripts/" && [ -z "$($L check --root "$n" dev/tg.sh)" ]'
# Value: protects=every refusal code and the read shapes that must stay wide; fails_when=a pattern, escape, tree,
# recursive-read or repo-root rule is dropped; why_new=review found them untested or missing; seam=none; no_claim=none beyond protects
printf '#!/bin/bash\n# reads: skills/a/scripts/*.py /etc/hosts\n:\n' > "$n/dev/tz.sh"  # lanes: no read (toy repo file)
printf '#!/bin/bash\n# reads: skills/a/scripts/a.py\nfor f in skills/*; do :; done\n' > "$n/dev/tw.sh"  # lanes: no read (toy repo file)
printf '#!/bin/bash\n# reads: skills/a/scripts/a.py\n! grep -R BAD skills/a/scripts\n' > "$n/dev/tr.sh"  # lanes: no read (toy repo file)
out=$($L check --root "$n" dev/tz.sh dev/tw.sh dev/tr.sh)
check "a glob or escaping declared path, an undeclared glob of every skill and a recursive grep are refused" 'grep -q "^LANES-DECL-PATTERN dev/tz.sh:2" <<<"$out" && grep -q "^LANES-DECL-ESCAPE dev/tz.sh:2: declared path leaves the repo: /etc/hosts" <<<"$out" && grep -q "^LANES-DECL-TREE dev/tw.sh" <<<"$out" && grep -q "^LANES-DECL-GLOB dev/tr.sh:3: reads skills/a/scripts/ as a whole" <<<"$out"'
printf '#!/bin/bash\n# reads: skills/b/scripts/b.py\nls skills/b/scripts | wc -l\n' > "$n/dev/t1.sh"  # lanes: no read (toy repo file)
printf '#!/bin/bash\n# reads: skills/b/scripts/b.py\nd=$here/skills/b/scripts\ngrep -r foo "$d"\n' > "$n/dev/t2.sh"  # lanes: no read (toy repo file)
printf '#!/bin/bash\n# reads: skills/b/scripts/b.py\nmkdir -p /tmp/o && cp -R skills/b/scripts /tmp/o/\n' > "$n/dev/t3.sh"  # lanes: no read (toy repo file)
printf '#!/bin/bash\n# reads: skills/b/scripts/b.py\nPYTHONPATH=skills/b/scripts python3 -c "import os; os.listdir(\\"skills/b/scripts\\")"\n' > "$n/dev/t4.sh"  # lanes: no read (toy repo file)
printf '#!/bin/bash\n# reads: skills/b/scripts/b.py\n(cd skills/b/scripts && grep -r Y .)\n' > "$n/dev/t5.sh"  # lanes: no read (toy repo file)
printf '#!/bin/bash\n# reads: skills/b/scripts/b.py\nd=skills/b; grep -r Y $d/scripts\n' > "$n/dev/t6.sh"  # lanes: no read (toy repo file)
printf '#!/bin/bash\n# reads: skills/b/scripts/b.py\n. dev/tm-lib.sh; ls $m | wc -l\n' > "$n/dev/t7.sh"  # lanes: no read (toy repo file)
out=$($L check --root "$n" dev/t1.sh dev/t2.sh dev/t3.sh dev/t4.sh dev/t5.sh dev/t6.sh dev/t7.sh)
check "a skill folder read as a whole, literally or through a variable, needs the folder declared" '[ "$(grep -c "^LANES-DECL-GLOB dev/t[1-7].sh" <<<"$out")" = 7 ]'
printf '#!/bin/bash\n# reads: skills/a/scripts/a.py\nhere=$(pwd); (cd "$here" && cat tools/x.txt)\n' > "$n/dev/tq.sh"  # lanes: no read (toy repo file)
check "a script that runs tools on the repo's own files reruns on every change" '$L deps --root "$n" "bash dev/tq.sh" | grep -q "^ALWAYS bash dev/tq.sh: runs tools on this repo.s own files"'
printf 'import os, helper\n' > "$n/skills/b/scripts/b2.py"; printf '#!/bin/bash\n# reads: skills/b/scripts/b2.py\npython3 skills/b/scripts/b2.py\n' > "$n/dev/tl.sh"
check "every module of an import list is followed" '$L deps --root "$n" "bash dev/tl.sh" | grep -qx "skills/b/scripts/helper.py"'
check "affected picks the rows naming a deleted file, never a full run, and a table edit is never unmapped" '$L affected --root "$n" skills/a/scripts/nope.py | grep -q "^DELETED skills/a/scripts/nope.py: the rows that name it" && ! $L affected --root "$n" .loop/regression.tsv | grep -q UNMAPPED'
# Value: protects=headerless rows keep today's mapping exactly; fails_when=the shared helpers change wide behavior;
# why_new=parity oracle for the refactor (E7); seam=LANES_WIDE; no_claim=none beyond protects
w2=$(LANES_WIDE=1 $L affected --root "$n" skills/a/scripts/a.py 2>&1)
check "LANES_WIDE=1 maps every row wide, as before headers" '[ "$(aff skills/a/scripts/a.py)" = "ta, tf, tu, tx" ] && grep -q "^AFFECTED 4 of 7 rows (ta, tf, th, tu)$" <<<"$w2"'
cd "$d/repo" 2>/dev/null && git switch -q main 2>/dev/null
p1=$($L affected src/a.txt 2>&1); p2=$(LANES_WIDE=1 $L affected src/a.txt 2>&1)
check "with no headers, affected is the same with and without LANES_WIDE (wide mapping unchanged)" '[ "$p1" = "AFFECTED 1 of 2 rows (a)" ] && [ "$p1" = "$p2" ]'
# Value: protects=a deleted helper picks the rows that name or map it, never a full run; fails_when=deletions are treated as
# edits; why_new=no deletion case existed; seam=none; no_claim=renames outside skills/ and dev/
mkdir -p skills/k/scripts; printf 'import kh\n' > skills/k/scripts/k.py; printf 'Z = 1\n' > skills/k/scripts/kh.py
printf '#!/bin/bash\n# reads: skills/k/scripts/k.py\nprintf "k\\n" >> "$TOY_LOG"\n' > dev/k.sh  # lanes: no read (toy repo file)
printf '#!/bin/bash\n# reads: skills/k/\nfor f in skills/k/*; do :; done; printf "w\\n" >> "$TOY_LOG"\n' > dev/w.sh  # lanes: no read (toy repo file)
printf 'k\tland\tbash dev/k.sh\tX-1\t2026-01-01\tK.\tcriterion\t\nw\tland\tbash dev/w.sh\tX-1\t2026-01-01\tW.\tcriterion\t\n' >> .loop/regression.tsv
git add -A; git commit -qm "Rows k and w"; $reg run land --reuse >/dev/null
fresh; out=$($reg run land --reuse); echo "$out"
check "a reusing run reuses declared rows when nothing changed" 'grep -q "^REUSED" <<<"$out" && [ -z "$(ran)" ]'
printf 'Z = 2\n' > skills/k/scripts/kh.py; git commit -qam "Change kh"
fresh; out=$($reg run land --reuse); echo "$out"
check "a run reruns a declared row whose imported module changed, and the broad row" 'grep -q "^AFFECTED 2 of" <<<"$out" && [ "$(ran)" = "k w " ]'
# Value: protects=a table edit reruns only the edited row and the rows that read this repo's table; fails_when=the
# narrow table rule goes back to every row reaching regression.py, or drops root-running scripts; why_new=the old rule
# reran nearly every row on any goal's table edit; seam=none; no_claim=toy scripts that name a toy .loop/regression.tsv
printf '#!/bin/bash\n# reads: skills/k/scripts/k.py\nhere=.; (cd "$here" && true); printf "t\\n" >> "$TOY_LOG"\n' > dev/t.sh  # lanes: no read (toy repo file)
mkdir -p skills/workflow-regression/scripts; printf 'print(1)\n' > skills/workflow-regression/scripts/regression.py
printf '#!/bin/bash\n# reads: skills/workflow-regression/scripts/regression.py\ncd "$TOY_LOG.d" 2>/dev/null; printf "r\\n" >> "$TOY_LOG"\n' > dev/r.sh  # lanes: no read (toy repo file)
printf 't\tland\tbash dev/t.sh\tX-1\t2026-01-01\tT.\tcriterion\t\nr\tland\tbash dev/r.sh\tX-1\t2026-01-01\tR.\tcriterion\t\n' >> .loop/regression.tsv
git add -A; git commit -qm "Rows t and r"; $reg run land --reuse >/dev/null
awk -F'\t' 'BEGIN {OFS = FS} $1 == "k" {$6 = "K again."} {print}' .loop/regression.tsv > "$d/rows" && cat "$d/rows" > .loop/regression.tsv
git commit -qam "Edit row k"
fresh; out=$($reg run land --reuse); echo "$out"
check "a table edit reruns the edited declared row and the rows that run tools on the repo root, not every row" '[ "$(ran)" = "k t " ]'
git rm -q skills/k/scripts/kh.py; git commit -qm "Delete kh"
fresh; out=$($reg run land --reuse); echo "$out"
check "a deleted skill file selects the rows that name or reach it, not a full run" '! grep -q "^FULL" <<<"$out" && grep -q "^UNMAPPED skills/k/scripts/kh.py" <<<"$out" && [ "$(ran)" = "k r t w " ]'
rm skills/k/scripts/k.py
fresh; out=$($reg run land --reuse 2>&1); echo "$out"
check "an uncommitted deletion selects rows the same way" '! grep -q "^FULL" <<<"$out" && grep -q "^UNMAPPED skills/k/scripts/k.py" <<<"$out" && [ "$(ran)" = "k r t w " ]'
git checkout -q -- skills/k/scripts/k.py
echo "== check-reads.sh: runtime reads outside a row's closure fail the trace"
c="$d/trace"; mkdir -p "$c/dev/toy" "$c/skills/workflow-regression/scripts" "$c/skills/a/scripts" "$c/.loop"
cp "$here/dev/toy/check-reads.sh" "$c/dev/toy/"; cp "$here/skills/workflow-regression/scripts/lanes.py" "$here/skills/workflow-regression/scripts/narrow.py" \
  "$here/skills/workflow-regression/scripts/lanes_cli.py" "$c/skills/workflow-regression/scripts/"
for f in a b c e; do printf 'NAME = "%s"\nopen(__file__).read()\n' "$f" > "$c/skills/a/scripts/$f.py"; done
printf 'import os\nopen(os.path.join(os.path.dirname(__file__), "c" + ".py")).read()\n' > "$c/skills/a/scripts/g.py"
printf 'import os, shutil, subprocess, sys, tempfile\nt = tempfile.mkdtemp(); shutil.copy(os.path.join(os.path.dirname(__file__), "e" + ".py"), t + "/x.py")\nsubprocess.run(["python3", t + "/x.py"], check=True)\n' > "$c/skills/a/scripts/k.py"
printf '#!/bin/bash\n# reads: skills/a/scripts/a.py\npython3 skills/a/scripts/a.py\n' > "$c/dev/t1.sh"  # lanes: no read (toy repo file)
printf '#!/bin/bash\n# reads: skills/a/scripts/g.py\npython3 skills/a/scripts/g.py\n' > "$c/dev/t2.sh"  # lanes: no read (toy repo file)
printf '#!/bin/bash\n# reads: skills/a/scripts/a.py skills/a/scripts/b.py\npython3 skills/a/scripts/a.py; python3 -I skills/a/scripts/b.py\n' > "$c/dev/t3.sh"  # lanes: no read (toy repo file)
printf '#!/bin/bash\n# reads: skills/a/scripts/k.py\npython3 skills/a/scripts/k.py\n' > "$c/dev/t4.sh"  # lanes: no read (toy repo file)
printf '# id\tlevel\tcommand\n' > "$c/.loop/regression.tsv"
for r in 1 2 3 4; do printf 'r%s\tland\tbash dev/t%s.sh\n' $r $r >> "$c/.loop/regression.tsv"; done
out=$(bash "$c/dev/toy/check-reads.sh" 2>&1); rc=$?; echo "$out"
# Value: protects=a row's runtime Python reads outside its closure fail the nightly trace; fails_when=the hook or the
# closure comparison is dropped; why_new=new tool; seam=sitecustomize + PATH shim; no_claim=bash-only reads
check "check-reads passes a row whose runtime reads are inside its closure" 'grep -q "^PASS r1" <<<"$out"'
check "check-reads fails a row that reads a skill file its closure misses, with the line to add" '[ $rc = 1 ] && grep -q "^LANES-TRACE-UNDECLARED r2 skills/a/scripts/c.py" <<<"$out" && grep -q "^fix: # reads: skills/a/scripts/c.py" <<<"$out"'
check "check-reads fails a row with a Python launch the hook never saw (python3 -I)" 'grep -q "^LANES-TRACE-NOHOOK r3: 2 Python launches, 1 hooked" <<<"$out"'
check "check-reads maps a read of a copied skill file back to the repo file" 'grep -q "^LANES-TRACE-UNDECLARED r4 skills/a/scripts/e.py" <<<"$out"'

[ $fails = 0 ] && echo "ALL PASS" || { echo "$fails FAILED"; exit 1; }
