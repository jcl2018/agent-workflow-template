#!/bin/bash
# reads: skills/workflow-delivery/scripts/flow.py skills/workflow-delivery/scripts/goal.py
# reads: skills/workflow-docs/scripts/criteria.py skills/workflow-docs/scripts/docs.py
# reads: skills/workflow-health/scripts/health.py skills/workflow-regression/scripts/regression.py
# reads: skills/workflow-setup/scripts/setup.py
# reads: skills/ docs/ README.md .loop/regression.tsv .loop/regression-runs.tsv .loop/regression-issues.tsv
# reads: .loop/regression-known.tsv .loop/docs.tsv .loop/config.json
# Prove the defect-tests goal's done lines, and guard the known defects. usage: test-defect.sh [CASE]
# With a CASE it exits non-zero if that case fails (regression rows call it so); with none it prints one PASS per case.
set -u
unset GITHUB_SERVER_URL GITHUB_REPOSITORY GITHUB_RUN_ID  # run cells and rendered Tests never depend on the runner
unset LOOP_SESSION_TOOL LOOP_OPERATION_SESSION  # a toy test never reaches a real session tool
unset LOOP_BATCH
export LOOP_ROLE=worker  # goal.py and flow.py run only in a worker
here=$(cd "$(dirname "$0")/../.." && pwd)
. "$here/dev/toy/reap.sh"
cases="wording flow-steps categories defect-owed health-closed worker-release pr-body pr-body-criterion no-hang known-defects skill-size skill-kept"
if [ $# = 0 ]; then
  fails=0
  for c in $cases; do
    out=$(bash "$0" "$c" 2>&1) && echo "PASS: $c" || { echo "FAIL: $c: $out"; fails=$((fails + 1)); }
  done
  [ "$fails" = 0 ] && echo "ALL PASS" || { echo "$fails FAILED"; exit 1; }
  exit
fi
case=$1
no() { echo "$case: $1"; exit 1; }
d=${TOY_KEEP:-$(mktemp -d)}; [ -n "${TOY_KEEP:-}" ] || toy_on_exit 'rm -rf "$d"'
goal="python3 $here/skills/workflow-delivery/scripts/goal.py"
flow="python3 $here/skills/workflow-delivery/scripts/flow.py"
reg="python3 $here/skills/workflow-regression/scripts/regression.py"
health="python3 $here/skills/workflow-health/scripts/health.py"
toy() { # a toy repo with the loop set up, the stand-in flow and the fake gh
  "$here/dev/toy/make.sh" "$d/toy" >/dev/null || exit 1
  export LOOP_FLOW="$d/toy/flow.json" PATH="$here/dev/toy/fakegh:$PATH" FAKE_GH_DIR="$d/gh"
  cd "$d/toy/repo" || exit 1
  python3 "$here/skills/workflow-setup/scripts/setup.py" >/dev/null || true  # a bare agent_command exits 1 after writing
  git switch -q main; git merge -q --no-edit workflow-setup
  # setup's seeded rows count as seen failing here, so the qa lane (which fails unproven rows) passes for the toy goals
  awk -F'\t' 'BEGIN {OFS = FS} !/^#/ && NF > 4 && $5 == "" {$5 = "2026-01-01"} {print}' .loop/regression.tsv > "$d/rows" \
    && cat "$d/rows" > .loop/regression.tsv && git commit -qam "Seen red" 2>/dev/null; git push -q origin main
}
real() { # a git copy of what the repo-wide checks read (skills, docs, README, the loop's tables); never the repo itself
  mkdir -p "$d/real/.loop" && cp -R "$here/skills" "$here/docs" "$here/README.md" "$d/real/" \
    && cp "$here/.loop/regression.tsv" "$here/.loop/regression-runs.tsv" "$here/.loop/regression-issues.tsv" \
      "$here/.loop/regression-known.tsv" "$here/.loop/docs.tsv" "$here/.loop/config.json" "$d/real/.loop/" \
    && cp -R "$here/.loop/goals" "$d/real/.loop/" \
    && cd "$d/real" && git init -q && git add -A && git -c user.name=t -c user.email=t@t commit -qm copy \
    && { u=$(git -C "$here/." remote get-url origin 2>/dev/null) && git remote add origin "$u" || true; } || no "cannot copy the repo"  # the Tests page links runs to origin; "$here/." not "$here": the plain form is a root runner again (issue 172)
}
finish() { # finish SLUG TEXT: a goal whose flow is done, with a change committed
  $goal new "$1" --here --goal "Add $1" --done "$2" >/dev/null || no "new"
  printf '\n# %s\n' "$1" >> calc.py; git commit -qam "Add $1 to calc"
  bash "$here/dev/toy/flow-done.sh" "$1" || no "flow"
}

case "$case" in
  wording) # done lines 1 and 2: REG-1, REG-2 and DEL-1 carry the owner's words, Reviewed 2026-11-08, seals intact
    python3 - "$here" <<'PY' || no "the wording differs"
import re, sys
want = {
 "docs/wiki/Regression.md": {
  "REG-1": "Two kinds of tests. The suite has two categories: criteria tests, which prove each Reviewed criterion, and defect tests, one for every finding, issue or bug that gets fixed, which prove it stays fixed. A criterion with no passing test shows as not enforced, and a fix isn't finished until its defect test exists and passes.",
  "REG-2": "Test format. Every test is listed in one fixed format, grouped by feature, wherever tests are shown (the wiki, the GitHub run summary, the health report): its category (requirement or defect); what it guards (the requirement's ID and words, or a link to the issue or finding it came from, with that issue's state); what it checks in one plain line; when it runs; its last result and date; and whether it has been seen failing once."},  # reworded by the owner 2026-11-08 (goal regression-summary)
 "docs/wiki/Delivery.md": {
  "DEL-1": "The loop. I give one sentence and the done lines, and a worker runs it unattended through these steps, in order: freeze the done lines, office-hours (shape the idea), plan, build, review, qa, ship, pull request, release. Review is the only gate. Each step can be mapped to any skill or plugin I choose, in a private setting outside the repo, and my preferred skill suite is the default; each step runs that skill in its unattended mode. It won't start without the flow set up, and it stops and says why after 3 failed tries."}}
for page, ids in want.items():
    text = open("%s/%s" % (sys.argv[1], page)).read()
    for key, words in ids.items():
        assert re.search(r"^- %s: \*\*Reviewed \d{4}-\d\d-\d\d\*\* \S.* <!-- reviewed \w+ -->$" % key, text, re.M), key  # the owner's latest words, sealed
PY
    out=$(real && python3 skills/workflow-docs/scripts/docs.py check 2>&1); grep -q "LOCKED" <<<"$out" && no "a reviewed criterion's seal is broken"
    exit 0;;
  flow-steps) # done line 3: no checks step; every step can be mapped, with a default suite and per-step overrides
    toy
    $goal check x 2>&1 | grep -q "invalid choice" || no "goal.py still has check"
    [ -z "$(real && git grep -l "require_checks" -- skills docs README.md .loop/config.json)" ] || no "require_checks is still named"
    grep -q '"checks"' "$here/.loop/config.json" && no "the config still has checks"
    steps=$(python3 -c "
import re; print(re.search(r'^STEPS = \((.*)\)', open('$here/skills/workflow-delivery/scripts/flow.py').read(), re.M).group(1))")
    for step in idea plan build review qa ship pr release; do
      grep -q "\"$step\"" <<<"$steps" || no "flow.py has no $step step"
    done
    printf '#!/bin/bash\necho "$1" > "%s/prompt-$(date +%%s%%N)"\necho "DEPTH: full"\necho "STEP: done"\n' "$d" > "$d/say.sh"
    python3 - "$d" <<'PY'
import json, sys
d = sys.argv[1]
suite = {s: "suite-" + s for s in ("idea", "plan", "build", "review", "qa", "ship", "pr", "release")}
base = {"command": ["bash", d + "/say.sh"], "env": {"FAKE_MODE": "unattended"}, "probe": ["bash", "-c", "echo $FAKE_MODE"], "probe_expect": "unattended"}
json.dump(dict(base, suite=suite, steps={"review": "own-review"}), open(d + "/mapped.json", "w"))
json.dump(dict(base, suite={s: suite[s] for s in ("idea", "plan", "review", "qa", "ship")}), open(d + "/five.json", "w"))
PY
    $goal new fs --here --goal "Map" --done "mapped" >/dev/null || no "new"
    for step in build review; do
      LOOP_FLOW="$d/mapped.json" $flow fs $step --wait 5 >/dev/null; LOOP_FLOW="$d/mapped.json" $flow fs $step --wait 10 >/dev/null
    done
    grep -l "Use the suite-build skill" "$d"/prompt-* >/dev/null || no "build did not use the default suite"
    grep -l "Use the own-review skill" "$d"/prompt-* >/dev/null && ! grep -l "Use the suite-review skill" "$d"/prompt-* >/dev/null || no "the override did not win"
    LOOP_FLOW="$d/five.json" $flow fs release 2>&1 | grep -q "no skill is mapped to the release step" || no "an unmapped step ran"
    exit 0;;
  categories) # done line 4: every row has a category, defect rows link their issue, the page shows defect tests with their kind
    awk -F'\t' '/^#/ || NF == 0 {next} $7 != "criterion" && $7 != "workflow" && $7 != "defect" {print $1; bad = 1} $7 == "defect" && $8 == "" {print $1; bad = 1} END {exit bad}' "$here/.loop/regression.tsv" || no "a row has no category, or a defect has no link"
    toy
    $reg add dd --level land --command true --category defect 2>&1 | grep -q "links to its issue or finding" || no "a defect row without a link was added"
    $reg add dd --level land --command true --category defect --link https://example.test/issues/1 >/dev/null || no "add defect"
    awk -F'\t' '$1 == "dd" && $7 == "defect" && $8 ~ /issues\/1$/ {ok = 1} END {exit !ok}' .loop/regression.tsv || no "the row lost its category or link"
    $reg add cc --level land --command true >/dev/null; awk -F'\t' '$1 == "cc" && $7 == "criterion" {ok = 1} END {exit !ok}' .loop/regression.tsv || no "no default category"
    python3 - "$here" <<'PY' || no "the page shows no defect rows"
import sys
text = open(sys.argv[1] + "/docs/wiki/Delivery.md").read()
rows = text.split("\n## Tests", 1)[1].splitlines()
assert any("issues/35" in r and "| defect |" in r for r in rows), "no defect row"
assert [r for r in rows if "scripts-no-hang" in r] and all("| defect |" in r for r in rows if "scripts-no-hang" in r)
PY
    (real && python3 skills/workflow-docs/scripts/criteria.py render --check >/dev/null) || no "the Tests tables are stale"
    exit 0;;
  defect-owed) # done line 5: a goal that fixes an issue cannot open its pull request without a defect test seen failing
    toy
    finish fixit "calc has fixit (fixes #77)"
    $goal pr fixit 2>&1 | grep -q "no passing defect test, seen failing, for #77" || no "pr opened with no defect test"
    $reg add fixit-77 --level land --command 'test -f calc.py' --goal - --category defect --link https://github.com/o/r/issues/77 --describe "calc.py stays" >/dev/null
    $goal pr fixit 2>&1 | grep -q "no passing defect test, seen failing, for #77" || no "pr accepted a defect row never seen failing"
    awk -F'\t' 'BEGIN{OFS="\t"} $1=="fixit-77"{$5="-"} {print}' .loop/regression.tsv > "$d/rows" && cat "$d/rows" > .loop/regression.tsv
    $goal pr fixit 2>&1 | grep -q "no passing defect test, seen failing, for #77" || no "pr accepted a defect row dated -"
    # Generated by /ship coverage audit. Value: protects=a defect row whose seen_red is words, not a date, does not pay the debt;
    #   fails_when=defect.py checks only "" and "-" instead of a date; why_new=only "-" is tried above; seam=none; no_claim=other date shapes
    awk -F'\t' 'BEGIN{OFS="\t"} $1=="fixit-77"{$5="n/a"} {print}' .loop/regression.tsv > "$d/rows" && cat "$d/rows" > .loop/regression.tsv
    $goal pr fixit 2>&1 | grep -q "no passing defect test, seen failing, for #77" || no "pr accepted a defect row dated with words"
    git add -A; git commit -qm "Defect row"
    $reg red fixit-77 --break 'rm calc.py' | grep -q "SEEN RED" || no "red"
    git add -A; git commit -qm "Seen failing"
    $goal pr fixit 2>&1 | grep -q "^PR " || no "pr refused with a defect test seen failing and passing"
    exit 0;;
  health-closed) # done line 6: health flags a closed issue or finding with no defect test
    toy
    mkdir -p .loop/goals; printf '# Goal\n\n## Done lines\n\n1. fixes #78 here\n' > .loop/goals/old.md
    printf -- '- bar: Failed 3 tries [closed]\n' >> .loop/findings.md
    git add -A; git commit -qm "Closed work"
    out=$($health check --family traceability)
    grep -q "^FAIL traceability #78 defect-tests: closed by old" <<<"$out" && grep -q "^FAIL traceability finding:bar defect-tests" <<<"$out" || no "closed work with no defect test was not flagged: $out"
    $reg add old-78 --level land --command true --goal - --category defect --link https://github.com/o/r/issues/78 >/dev/null
    $reg add bar --level land --command true --goal - --category defect --link finding:bar >/dev/null
    out=$($health check --family traceability)
    grep -q "^PASS traceability defect-tests defect-tests: " <<<"$out" || no "the defect-tests rule did not run: $out"
    grep -Eq "^(WARN|FAIL|UNREAD) .*defect-tests" <<<"$out" && no "a guarded issue is still flagged: $out"
    exit 0;;
  worker-release) # done line 7, and the release step that pull requests 61 and 62 skipped
    toy
    finish w "calc has w"; $goal pr w >/dev/null || no "pr"
    python3 - "$here" <<'PY' || no "the worker did not run the release step"
import argparse, json, subprocess, sys
sys.path.insert(0, sys.argv[1] + "/skills/workflow-monitoring/scripts")
import worker
real, calls = subprocess.run, []
def fake(argv, **kw):
    if any("merge.py" in str(part) for part in argv):
        calls.append(argv)
        return subprocess.CompletedProcess(argv, 0, "merged", "")
    return real(argv, **kw)
worker.subprocess.run = fake
def ends(auto, landed):
    path = worker.path_of("w")
    state = json.load(open(path)); state.update(status="done", pr="https://x/pull/1"); json.dump(state, open(path, "w"))
    cfg = json.load(open(".loop/config.json")); cfg["auto_merge"] = auto; json.dump(cfg, open(".loop/config.json", "w"))
    worker.merged = lambda url: landed
    del calls[:]
    worker.cmd_loop(argparse.Namespace(slug="w", command=["true"]))
    return len(calls)
assert ends(True, False) == 1, "a worker that ended with its pull request waiting did not run merge.py"
assert ends(True, True) == 0, "ran the release step on a merged pull request"
assert ends(False, False) == 0, "ran the release step with auto_merge off"
PY
    exit 0;;
  pr-body) # the pull request body that said checks passed with no checks
    toy
    finish pb "calc has pb"; $goal pr pb >/dev/null || no "pr"
    sed '/<details>/,/<\/details>/d' "$d/gh/body-1" | grep -qi "checks" && no "the body talks about checks"  # the folded lane rows list row ids, some named *checks
    grep -q "Skill flow:" "$d/gh/body-1" || no "the body lists no steps"
    exit 0;;
  pr-body-criterion) # DEL-4: the body carries the title, the done lines, the verify steps and each step's result
    toy
    finish pc "calc has pc"
    python3 - <<'PY'
path = ".loop/goals/pc.md"
text = open(path).read().replace("## Verify by hand\n", "## Verify by hand\n\n1. Open calc.py.\n   Expect: it has pc.\n", 1)
open(path, "w").write(text)
PY
    git commit -qam "Verify steps for pc"
    $goal pr pc >/dev/null || no "pr"
    body="$d/gh/body-1"
    grep -q "^# Add pc" "$body" || no "the body has no goal"
    grep -q "calc has pc" "$body" || no "the body has no done line"
    grep -q "Open calc.py" "$body" || no "the body has no verify step"
    for step in idea plan review qa ship; do grep -q "^- $step: " "$body" || no "the body has no result for $step"; done
    exit 0;;
  no-hang) # issue 35: scripts fail with an error instead of hanging with no terminal
    bash "$here/dev/toy/test-rows.sh" DEL-10 || no "a script can prompt"
    exit 0;;
  known-defects) # done line 8: defect tests exist, linked and seen failing, for issues 35 and 58 and the two worker defects
    for want in "scripts-no-hang issues/35" "wiki-release-pycache issues/58" "worker-runs-release pull/61" "pr-body-no-checks pull/62"; do
      set -- $want
      awk -F'\t' -v id="$1" -v link="$2" '$1 == id && $7 == "defect" && $8 ~ link && $5 != "" {ok = 1} END {exit !ok}' "$here/.loop/regression.tsv" || no "no defect row $1 linked to $2, seen failing"
    done
    exit 0;;
  skill-size) # issue 116: every SKILL.md stays under test-board's 150-line limit
    for f in "$here"/skills/*/SKILL.md; do [ "$(wc -l < "$f")" -lt 150 ] || no "$f is $(wc -l < "$f") lines"; done
    exit 0;;
  skill-kept) # issue 116: what left the two SKILL.md files is kept word for word in their references, and they point there
    while IFS='|' read -r skill phrase; do
      grep -qF -- "$phrase" "$here/skills/$skill/references/commands.md" || no "$skill/references lost: $phrase"
    done <<'KEPT'
workflow-delivery|input + output + cache-creation
workflow-delivery|tests the committed HEAD only: an unclean tree fails it (`LANE_DIRTY`).
workflow-delivery|until a qa lane passed on HEAD (`LANE_MISSING`; start one with `role.py lane <slug> qa`), except for a reply whose last
workflow-delivery|`STEP:` line is `failed` and that has no `PENDING:` line, which records as a failed try.
workflow-delivery|only the rows the change can affect. The release step itself (merge.py) doesn't rerun it; GitHub Actions still runs the
workflow-delivery|With `pr_bumps_version` on, it moves the last number of the version file once on this branch first, unless the
workflow-delivery|branch already changed it. It retries a failed push twice, then prints git's full error.
workflow-delivery|- `"auto_approve": true`: `record` approves what a step leaves for the owner, logs it as auto-approved, and goes on.
workflow-delivery|merges the pull request, bumps the version once and publishes a GitHub release with a CHANGELOG entry.
workflow-docs|2. `## Problem`: who it's for and what it solves, at most `problem_lines` lines;
workflow-docs|5. `## Non-goals`: at least one line; `## Success metrics`: one to `metrics_lines` measurable lines;
workflow-docs|   when no row passes; then the workflow tests, then the defect tests, in the same table.
workflow-docs|`NONGOALS`, `METRICS`, `CRITERION`, `CAP`, `SCRIPT`, `USAGE`, `TESTS` (run `render`), `LOCKED`, `CHANGED`.
workflow-docs|Usage. After it, a change to any of the first four is `LOCKED` (check, audit and release fail); a change to Usage alone
workflow-docs|owner un-reviews that requirement and the PRD, then reviews both again.
workflow-docs|`Given <context>, when <action>, then <outcome>.`; `audit` lists any other as `SCENARIO` and the release step blocks on
workflow-docs|`regression.py sync` reports an id with no row, and `release.py cut` refuses while any of its rows is missing, a draft
workflow-docs|is `UNWRITTEN` until then) and add its requirement's regression row in the same pull request (it needs one before the
workflow-docs|`convert --write` does it (Summary becomes Problem, Criteria Requirements, every stamp kept, placeholder Non-goals and
KEPT
    for skill in workflow-delivery workflow-docs; do
      grep -q "references/commands.md" "$here/skills/$skill/SKILL.md" || no "$skill/SKILL.md does not point to its references"
      grep -q "^## Command map" "$here/skills/$skill/SKILL.md" || no "$skill/SKILL.md lost its Command map"
    done
    grep -q "governance only" "$here/skills/workflow-delivery/SKILL.md" || no "workflow-delivery/SKILL.md lost its governance line"
    grep -q "Never review or unreview on a goal's own initiative" "$here/skills/workflow-docs/SKILL.md" || no "workflow-docs/SKILL.md lost its review rule"
    exit 0;;
  *) no "unknown case";;
esac
