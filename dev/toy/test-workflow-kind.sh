#!/bin/bash
# reads: skills/workflow-regression/scripts/regression.py skills/workflow-regression/scripts/tests.py
# reads: skills/workflow-regression/scripts/tiers.py skills/workflow-docs/scripts/criteria.py
# reads: skills/workflow-docs/scripts/render.py skills/workflow-health/scripts/health.py
here=$(cd "$(dirname "$0")/../.." && pwd)
. "$here/dev/toy/reap.sh"
# REG-1 and REG-2 on a throwaway repo: the third test kind `workflow` (an end-to-end run of a whole flow) is accepted
# by add and sync, shown as kind workflow everywhere and as its own part of a page's Tests table, `tests.py list
# --kind` filters by kind, and tests.py summary, the wiki Tests tables and health's TESTS block print the same grouped
# lines for a mix of requirement, workflow and defect tests across two features (A7, S28). usage: test-workflow-kind.sh
set -u
unset GITHUB_SERVER_URL GITHUB_REPOSITORY GITHUB_RUN_ID GH_TOKEN GITHUB_TOKEN
export HOME=$(mktemp -d)
d=$(mktemp -d); toy_on_exit 'rm -rf "$d" "$HOME"'
fails=0
ok() { echo "PASS: $1"; }
bad() { echo "FAIL: $1"; fails=$((fails + 1)); }
reg="python3 -B $here/skills/workflow-regression/scripts/regression.py"
tests="python3 -B $here/skills/workflow-regression/scripts/tests.py"
cri="python3 -B $here/skills/workflow-docs/scripts/criteria.py"
cd "$d" && git init -q -b main && git config user.email t@example.test && git config user.name Toy
mkdir -p .loop docs/wiki
printf '{"wiki_dir": "docs/wiki", "criteria": true}\n' > .loop/config.json
page() {  # NAME ID: a feature page with one requirement and an empty Tests section
  printf '<!-- workflow-docs -->\n# %s\n\nReview: **Unreviewed**\n\n## Problem\n\n- I read the %s page.\n\n## Requirements\n\n### Functional\n\n- %s: **Unreviewed** %s words.\n  - It holds.\n\n### Non-functional\n\nNone\n\n## Non-goals\n\n- None.\n\n## Success metrics\n\n- It passes.\n\n## Tests\n\n' "$1" "$1" "$2" "$1" > "docs/wiki/$1.md"
}
page Alpha AAA-1; page Beta BBB-1
g="Given a toy, when it runs, then it works."
printf '# id\tlevel\tcommand\tgoal\tseen_red\tdescription\tcategory\tlink\n' > .loop/regression.tsv
$reg add aw --level nightly --command true --goal AAA-1 --describe "$g" --category workflow >/dev/null 2>err.txt
added=$?
$reg add a1 --level land --command true --goal AAA-1 --describe "$g" >/dev/null
$reg add ad --level land --command true --goal AAA-1 --describe "$g" --category defect --link https://example.test/o/r/issues/7 >/dev/null
$reg add b1 --level land --command true --goal BBB-1 --describe "$g" >/dev/null
$reg add bw --level nightly --command true --goal BBB-1 --describe "$g" --category workflow >/dev/null 2>&1
$reg add bd --level land --command true --goal BBB-1 --describe "$g" --category defect --link https://example.test/o/r/issues/8 >/dev/null
python3 - <<'PY'
rows = open(".loop/regression.tsv").read().splitlines()
out = [r if r.startswith("#") else "\t".join(c if i != 4 else "2026-11-01" for i, c in enumerate(r.split("\t"))) for r in rows]
open(".loop/regression.tsv", "w").write("\n".join(out) + "\n")
PY
printf '# id\tstatus\tdate\trun\naw\tPASS\t2026-11-09\t\na1\tPASS\t2026-11-09\t\nad\tPASS\t2026-01-15\t\nb1\tFAIL\t2026-11-08\t\nbw\tPASS\t2026-11-08\t\nbd\tPASS\t2026-11-08\t\n' > .loop/regression-runs.tsv
printf '# link\tstate\tdate\treopened_at\nhttps://example.test/o/r/issues/7\topen\t2026-02-01\t2026-02-01T10:00:00Z\nhttps://example.test/o/r/issues/8\tclosed\t2026-11-08\t\n' > .loop/regression-issues.tsv
git add -A && git commit -qm fixture

echo "== the workflow kind (REG-1)"
# Value: protects=a workflow test can be recorded as its own kind (REG-1); fails_when=add or sync refuses category
# workflow; why_new=only criterion and defect were valid; seam=none; no_claim=what a workflow test runs
sync=$($reg sync 2>&1)
[ "$added" = 0 ] && grep -q "	workflow	$" .loop/regression.tsv && ! grep -q "^NOCATEGORY aw" <<<"$sync" \
  && ok "add and sync accept the workflow category" || bad "workflow category: $(cat err.txt) $sync"
# Value: protects=list, summary and the wiki show kind workflow (REG-1); fails_when=a workflow row shows as requirement
# or sits among the requirement rows of its page; why_new=two kinds before; seam=none; no_claim=the full Tests page layout
list=$($tests list); printf 'aw\tPASS\nbw\tPASS\n' > res.tsv; sum=$($tests summary --results res.tsv --took 5)
$cri render >/dev/null 2>&1
part=$(grep -oE '^\| \[[a-z0-9]+\]\(Tests#t-[a-z0-9]+\) \| [a-z]+ ' docs/wiki/Alpha.md | sed -E 's/^\| \[([a-z0-9]+)\].*\| ([a-z]+) $/\1:\2/' | tr '\n' ,)
grep -qxF "aw | workflow | AAA-1: Alpha words. | $g | nightly | PASS 2026-11-09 | seen failing 2026-11-01" <<<"$list" \
  && grep -qF "| aw | workflow | AAA-1: Alpha words. |" <<<"$sum" && grep -q '^| <a id="t-aw"></a>aw | workflow |' docs/wiki/Tests.md \
  && [ "$part" = "a1:requirement,aw:workflow,ad:defect," ] && ok "list, summary and the wiki show kind workflow, in its own part" \
  || bad "workflow shown: part=$part list=$list"

echo "== list --kind (X5)"
# Value: protects=tests.py list --kind lists only the asked kind; fails_when=the flag is refused or ignored;
# why_new=list had no filter; seam=none; no_claim=run --kind (test-tiers.sh)
names() { $tests list --tsv --kind "$1" 2>&1 | cut -f2 | tr '\n' ,; }
[ "$(names workflow)" = "aw,bw," ] && [ "$(names requirement)" = "a1,b1," ] && [ "$(names defect)" = "ad,bd," ] \
  && [ "$($tests list --tsv | wc -l | tr -d ' ')" = 6 ] && ok "list --kind lists only the asked kind" \
  || bad "list --kind: $(names workflow) / $(names requirement) / $(names defect)"

echo "== one format everywhere (A7, S28)"
# Value: protects=tests.py summary, the wiki Tests tables and health's TESTS block show the same groups, tests, kinds
# and results, a reopened defect included (REG-2); fails_when=one surface drops the workflow kind, the reopened state
# or a row, or orders the groups differently; why_new=no check compared the surfaces; seam=none; no_claim=FLAKY
# (not built in this goal) and the columns only one surface has (checks, runs, run link)
awk -F'\t' '!/^#/ && NF { print $1 "\t" $2 }' .loop/regression-runs.tsv > res.tsv
$tests summary --results res.tsv --took 5 > summary.md
python3 -B "$here/skills/workflow-health/scripts/health.py" check > health.txt 2>/dev/null
python3 - summary.md docs/wiki/Tests.md health.txt docs/wiki/Alpha.md docs/wiki/Beta.md > same.txt <<'PY'
import re, sys
def norm(result):
    return re.sub(r" \d{4}-\d\d-\d\d$", "", result.strip())
def md(path, head):
    out, feature = [], None
    for line in open(path).read().splitlines():
        if line.startswith(head):
            feature = line[len(head):]
        elif feature and line.startswith("| ") and not line.startswith(("| Test |", "|---")):
            cells = [c.strip() for c in line.strip("|").split(" | ")]
            out.append((feature, re.sub(r"<[^>]*>", "", cells[0]), cells[1], norm(cells[-1] if head == "### " else cells[3])))
    return out
def health(path):
    lines = open(path).read().splitlines()
    out, feature = [], None
    for line in lines[lines.index("TESTS") + 1:] if "TESTS" in lines else []:
        if line.startswith("FEATURE "):
            feature = line[8:]
        elif feature and " | " in line:
            cells = line.split(" | ")
            out.append((feature, cells[0], cells[1], norm(cells[5])))
    return out
def page(path, feature):
    rows = [line.strip().strip("|").split(" | ") for line in open(path) if line.startswith("| [")]
    return sorted((feature, re.sub(r"^\[([^]]+)\].*", r"\1", c[0].strip()), c[1].strip(), norm(c[-1])) for c in rows)
summary, wiki, report = md(sys.argv[1], "### "), md(sys.argv[2], "## "), health(sys.argv[3])
pages = page(sys.argv[4], "Alpha") + page(sys.argv[5], "Beta")
print("\n".join("|".join(x) for x in summary))
same = summary == wiki == report and sorted(summary) == sorted(pages) and len(summary) == 6
sys.exit(0 if same else "summary %s\nwiki %s\nhealth %s\npages %s" % (summary, wiki, report, pages))
PY
same=$?
[ "$same" = 0 ] && grep -qx "Alpha|ad|defect|failing (issue reopened)" same.txt && grep -qx "Beta|bw|workflow|PASS" same.txt \
  && ok "summary, the wiki Tests tables and health's TESTS block print the same grouped lines" \
  || bad "surfaces differ: $(cat same.txt)"

[ "$fails" = 0 ] && echo "ALL PASS" || { echo "$fails FAILED"; exit 1; }
