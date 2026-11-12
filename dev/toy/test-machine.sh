#!/bin/bash
# reads: skills/workflow-setup/scripts/machine.py docs/wiki/Setup.md README.md
# reads: skills/workflow-monitoring/references/operation.md skills/workflow-regression/scripts/actions.py
# Proves the machine setup (SET-11, SET-12): a dry run, apply, a check that writes nothing, a Windows-shaped home, the
# no-prompt rule, the two layers, the unattended mailer and the caps. One case per regression row id.
# usage: test-machine.sh [ROW-ID]   no ID runs every case. No model, no network and no real mail are used.
set -u
here=$(cd "$(dirname "$0")/../.." && pwd); only=${1:-}
. "$here/dev/toy/reap.sh"
d=$(mktemp -d); toy_on_exit 'rm -rf "$d"'
no() { echo "FAIL ${only:-machine}: $1"; exit 1; }
want() { [ -z "$only" ] || [ "$only" = "$1" ]; }
printf '# a toy: no private names\n' > "$d/names"; export LOOP_PRIVATE_NAMES="$d/names"
mkdir -p "$d/clone"; cp -R "$here/skills" "$d/clone/"; find "$d/clone" -name __pycache__ -type d -prune -exec rm -r {} +  # a clone has none  # a copy outside any goal worktree, as a real clone is
M="python3 $d/clone/skills/workflow-setup/scripts/machine.py"
mk() { "$here/dev/toy/make.sh" "$d/$1" >/dev/null || no "make.sh failed"; git -C "$d/$1/repo" remote set-url origin "https://example.test/o/$1-repo.git"; }
sums() { find "$1" -type f -print0 2>/dev/null | sort -z | xargs -0 shasum 2>/dev/null | shasum | tr -d ' -'; }
ready() { # ready HOME REPO [flags]: apply, record both modes, add the owner's two mail files
  h=$1; r=$2; shift 2
  $M apply --home "$h" --repo "$r" "$@" >/dev/null || return 1
  for t in $(ls "$h/.claude/scheduled-tasks"); do $M record-task "$t" bypass --home "$h" --repo "$r" >/dev/null; done
  printf 'SMTP_USER=toy\nSMTP_PASSWORD=toy-pass-0000\n' > "$h/.workflow-loop/mail.env"; chmod 600 "$h/.workflow-loop/mail.env"; printf 'owner@example.test\n' > "$h/.workflow-loop/mail-to"
}

# done 1: a dry run writes nothing; apply installs the links, the private-names file, the mailer and the tasks.
if want machine-apply-installs; then
  mk a; h="$d/ha"; mkdir -p "$h"; before=$(sums "$h")
  out=$($M plan --home "$h" --repo "$d/a/repo") || no "plan failed"
  echo "$out" | grep -q '^DRY RUN: nothing written' || no "plan did not say it is a dry run"
  [ "$(sums "$h")" = "$before" ] || no "plan wrote into the home folder"
  $M apply --home "$h" --repo "$d/a/repo" >/dev/null || no "apply failed"
  [ -e "$h/.claude/skills/workflow-setup" ] && [ -f "$h/.workflow-loop/private-names" ] && [ -f "$h/.workflow-loop/routines/send-mail.py" ] \
    && [ -f "$h/.claude/scheduled-tasks/a-repo-health-regression/SKILL.md" ] || no "apply left an item out"
  [ "$(wc -c < "$h/.workflow-loop/private-names" | tr -d " ")" = 0 ] || no "the private-names file is not empty"
  grep -q 'workflow-loop-hook' "$d/a/repo/.git/hooks/pre-commit" 2>/dev/null || no "the git hook is missing or not ours"
  grep -q '^model: ' "$h/.claude/scheduled-tasks/a-repo-health-regression/SKILL.md" || no "the task has no model"
  [ ! -d "$d/clone/skills/workflow-setup/scripts/__pycache__" ] || no "a run left bytecode beside the scripts"
  $M record-task nope bypass --home "$h" --repo "$d/a/repo" | grep -q '^REFUSED' || no "record-task took an unknown task name"
  printf '[1]' > "$h/.workflow-loop/machine.json"; $M check --home "$h" --repo "$d/a/repo" >/dev/null 2>&1; [ $? -le 1 ] || no "a bad state file crashed check"
  echo "PASS: a dry run writes nothing and apply installs the skills, hooks, names file, mailer and tasks"
fi

# done 2: a fresh machine fails the check with each gap named; a set-up one passes; the check writes nothing.
if want machine-check-gaps; then
  mk b; h="$d/hb"; mkdir -p "$h"; before=$(sums "$h")
  out=$($M check --home "$h" --repo "$d/b/repo"); rc=$?
  [ $rc != 0 ] || no "a fresh machine passed the check"
  for g in skills private-names mailer hooks task:operation-checkin mail.env mail-to "mode:b-repo-health-regression"; do
    echo "$out" | grep -q "^GAP $g" || no "gap $g not named"; done
  [ "$(echo "$out" | grep -c '^GAP')" = "$(echo "$out" | grep '^GAP' | grep -c -- '-> run:')" ] || no "a gap line has no fix"
  [ "$(sums "$h")" = "$before" ] || no "check wrote into the home folder"
  ready "$h" "$d/b/repo" || no "ready failed"
  $M check --home "$h" --repo "$d/b/repo" | grep -q '^MACHINE OK' || no "a set-up machine did not pass"
  echo "PASS: a fresh machine fails with each gap named and a set-up machine passes, and check writes nothing"
fi

# done 3: the operation guide carries the conventions; the check-in routine file is only a pointer.
if want machine-operation-guide; then
  g="$here/skills/workflow-monitoring/references/operation.md"
  for s in "Check-in prompt" "Full-auto rules" "Decision log" "Held lines"; do grep -q "^#.*$s" "$g" || no "operation.md has no section $s"; done
  mk c; h="$d/hc"; ready "$h" "$d/c/repo" || no "ready failed"
  [ "$(wc -l < "$h/.workflow-loop/routines/operation-checkin.md")" -le 3 ] || no "the check-in routine file is more than a pointer"
  printf 'one\ntwo\nthree\nfour\n' > "$h/.workflow-loop/routines/operation-checkin.md"
  $M check --home "$h" --repo "$d/c/repo" | grep -q '^GAP check-in' || no "a bloated check-in file was not flagged"
  echo "PASS: the operation guide holds the check-in layout, full-auto rules, decision log and held lines, and the prompt is a pointer"
fi

# done 4: setup refuses to write a private value; the refusal names the line and kind, never the value.
if want machine-no-private; then
  mk e; r="$d/e/repo"; h="$d/he"; mkdir -p "$h"; cd "$r" || exit 1
  mkdir -p routines; printf 'send to owner@example.test and read /Us%sers/someone/notes\n' "" > routines/mail.md
  mkdir -p .loop; printf '{"machine_setup":[{"kind":"routine","name":"mail","file":"routines/mail.md"}]}\n' > .loop/config.json; git add routines/mail.md
  out=$($M apply --home "$h" --repo "$r"); rc=$?
  [ $rc != 0 ] || no "a private value was written"
  echo "$out" | grep -q '^REFUSED' || no "no refusal printed"
  echo "$out" | grep -q 'owner@example.test\|someone' && no "the refusal echoed the value"
  ls "$h/.workflow-loop/routines/"*mail.md >/dev/null 2>&1 && no "the refused routine was still written"
  echo "$out" | grep -q 'holds a address\|holds a home path' || no "the refusal does not name the kind"
  cd "$here"; mk f; out=$($M apply --home "$d/f/repo/home" --repo "$d/f/repo"); rc=$?
  [ $rc != 0 ] && echo "$out" | grep -q 'is inside a repo' || no "a write inside a repo was not refused"
  [ ! -e "$d/f/repo/home/.workflow-loop/routines/send-mail.py" ] || no "a file was written inside a repo"
  echo "PASS: setup refuses a text holding an address or home path, and a write inside a repo, without echoing the value"
fi

# done 5: Setup gains a New machine section linked from the README, and the new requirements are Unreviewed.
if want machine-new-machine-docs; then
  grep -q 'New machine, in order' "$here/docs/wiki/Setup.md" || no "Setup has no New machine steps"
  grep -q 'New machine steps under' "$here/README.md" || no "README does not link the New machine steps"
  for id in SET-11 SET-12; do grep -q "^- $id: \*\*Unreviewed\*\*" "$here/docs/wiki/Setup.md" || no "$id is not listed Unreviewed"; done
  echo "PASS: Setup has a New machine section linked from the README and the new requirements are Unreviewed"
fi

# done 6: each machine row is listed in the Setup Tests table.
if want machine-rows-listed; then
  for row in machine-apply-installs machine-check-gaps machine-operation-guide machine-no-private machine-new-machine-docs machine-windows machine-task-layout machine-no-prompt-mode machine-custom-items machine-mailer machine-caps machine-done-1 machine-done-12; do
    grep -qF "[$row](Tests#t-$row)" "$here/docs/wiki/Setup.md" || no "row $row is not in the Setup Tests table"; done
  echo "PASS: every machine row is listed in the Setup Tests table"
fi

# done 7: a Windows-shaped home passes beside the Mac one.
if want machine-windows; then
  mk w; r="$d/w/repo"; h="$d/winhome/profile/toy"; mkdir -p "$h"
  out=$($M plan --home "$h" --repo "$r" --platform windows); echo "$out" | grep -q '^WINDOWS:' || no "no Windows banner"
  echo "$out" | grep -q 'unverified on Windows' || no "no item is marked unverified"
  ready "$h" "$r" --platform windows || no "ready failed"
  [ -f "$h/.claude/skills/workflow-setup/SKILL.md" ] || no "the Windows skills form (a copy) is missing"
  grep -q 'py -3' "$h/.workflow-loop/routines/w-repo-health-regression.md" || no "the routine does not use the Windows launcher"
  $M check --home "$h" --repo "$r" --platform windows | grep -q '^MACHINE OK' || no "the Windows home did not pass"
  $M check --home "$h" --repo "$r" | grep -q '^MACHINE OK' || no "the same home does not pass as a Mac home"
  $M check --home "$d/winhome/profile/none" --repo "$r" --platform windows | grep -q '^GAP' || no "a fresh Windows home passed"
  echo "PASS: a Windows-shaped home and a Mac home both pass and a fresh one fails"
fi

# done 8: one task per repo named <repo>-health-regression, every 4 hours, staggered; no double schedule; public workflow trimmed.
if want machine-task-layout; then
  mk t1; mk t2; h="$d/ht"; mkdir -p "$h"
  $M apply --home "$h" --repo "$d/t1/repo" >/dev/null || no "apply t1 failed"; $M apply --home "$h" --repo "$d/t2/repo" >/dev/null || no "apply t2 failed"
  a="$h/.claude/scheduled-tasks/t1-repo-health-regression/SKILL.md"; b="$h/.claude/scheduled-tasks/t2-repo-health-regression/SKILL.md"
  [ -f "$a" ] && [ -f "$b" ] || no "a repo has no <repo>-health-regression task"
  out=$($M plan --home "$h" --repo "$d/t1/repo"); echo "$out" | grep -q '\*/4' || echo "$out" | grep -q 'every 4 hours' || no "the cadence is not every 4 hours"
  m1=$(echo "$out" | grep -o 'register task t1-repo-health-regression in the app at "[0-9]* \*/4' | grep -o '"[0-9]*'); m2=$($M plan --home "$h" --repo "$d/t2/repo" | grep -o 'register task t2-repo-health-regression in the app at "[0-9]* \*/4' | grep -o '"[0-9]*')
  [ -n "$m1" ] && [ "$m1" != "$m2" ] || no "the starts are not staggered"
  grep -q 'health.py check --group' "$h/.workflow-loop/routines/t1-repo-health-regression.md" && grep -q 'regression.py run nightly' "$h/.workflow-loop/routines/t1-repo-health-regression.md" || no "the routine does not run health and the full regression"
  mkdir -p "$h/.workflow-loop/schedule"; printf '{"repos":{"k":{"path":"%s"}}}\n' "$(cd "$d/t1/repo" && pwd -P)" > "$h/.workflow-loop/schedule/repos.json"
  $M check --home "$h" --repo "$d/t1/repo" | grep -q '^GAP local-schedule' || no "a repo with two 4-hourly runs was not flagged"
  $M apply --home "$h" --repo "$d/t1/repo" >/dev/null
  $M check --home "$h" --repo "$d/t1/repo" | grep -q '^GAP local-schedule' && no "apply left the launch agent registry entry"
  grep -q '^  pull_request:' "$here/.github/workflows/regression-pr.yml" && grep -q '^  push:' "$here/.github/workflows/regression-pr.yml" || no "the public workflow lacks push and pull_request tests"
  grep -q '^  schedule:' "$here/.github/workflows/regression.yml" "$here/.github/workflows/regression-pr.yml" && no "a public workflow still schedules a run"
  [ "$(python3 -c "import json;print(json.load(open('$here/.loop/config.json')).get('regression_cron'))")" = off ] || no "regression_cron is not off here"
  ! LOOP_NO_HEALTH=1 python3 "$here/skills/workflow-health/scripts/health.py" check --group adoption 2>&1 | grep -q 'regression.yml.*scheduled\|scheduled.*has no schedule' || no "health calls the unscheduled public workflow a gap"
  mk t3; mkdir -p "$d/t3b"; "$here/dev/toy/make.sh" "$d/t3b" >/dev/null; git -C "$d/t3b/repo" remote set-url origin "https://example.test/o/t3-repo.git"
  $M apply --home "$h" --repo "$d/t3/repo" >/dev/null; $M apply --home "$h" --repo "$d/t3b/repo" >/dev/null
  [ "$(ls "$h/.claude/scheduled-tasks" | grep -c '^t3-repo')" = 2 ] || no "two alike repos share one task"
  echo "PASS: one staggered 4-hourly task per repo named <repo>-health-regression, no double schedule, and a public workflow with only push and pull request tests"
fi

# done 9: a routine that would stop to ask fails the check.
if want machine-no-prompt-mode; then
  mk p; r="$d/p/repo"; h="$d/hp"; ready "$h" "$r" || no "ready failed"
  $M record-task p-repo-health-regression default --home "$h" --repo "$r" >/dev/null
  $M check --home "$h" --repo "$r" | grep -q '^GAP mode:p-repo-health-regression: mode default would stop to ask' || no "a prompting mode passed"
  rm -f "$h/.workflow-loop/machine.json"; ready "$h" "$r" >/dev/null
  $M record-task p-repo-health-regression bypass --home "$h" --repo "$r" >/dev/null
  $M check --home "$h" --repo "$r" | grep -q '^MACHINE OK' || no "the no-prompt mode did not pass"
  echo "PASS: a task with no recorded no-prompt mode fails the check and one on bypass passes"
fi

# done 10: a repo's own custom list is applied, listed and checked; a repo without one gets nothing.
if want machine-custom-items; then
  mk x; mk y; h="$d/hx"; mkdir -p "$h"; r="$d/x/repo"; cd "$r" || exit 1; mkdir -p .loop routines
  printf 'Send the report.\n' > routines/news.md; git add routines/news.md
  printf '{"machine_setup":[{"kind":"allow","name":"mailtool","rule":"mcp__toy__send"},{"kind":"routine","name":"news","file":"routines/news.md","cron":"0 * * * *"},{"kind":"allow","name":"wild","rule":"Bash(*)"},{"kind":"routine","name":"escape","file":"../x.md"},{"kind":"secret","name":"toykey","path":"%s/toy.env"}]}\n' "$d" > .loop/config.json
  cd "$here"
  $M plan --home "$h" --repo "$r" | grep -q 'allow rule mailtool' || no "plan does not list the custom items"
  $M apply --home "$h" --repo "$r" >/dev/null
  grep -q 'mcp__toy__send' "$h/.claude/settings.json" || no "the allow rule was not written"
  [ -f "$h/.claude/scheduled-tasks/x-repo-custom-news/SKILL.md" ] || no "the repo routine has no task"
  $M plan --home "$h" --repo "$r" | grep -q 'at "0 \* \* \* \*"' || no "the routine's own cron is not shown"
  grep -q 'Bash' "$h/.claude/settings.json" && no "a wildcard allow rule was written"
  $M apply --home "$h" --repo "$r" | grep -q 'REFUSED custom:allow:wild' || no "the wildcard rule was not refused"
  [ ! -e "$h/.claude/scheduled-tasks/x-repo-custom-escape" ] || no "a routine file outside the repo was read"
  $M check --home "$h" --repo "$r" | grep -q '^GAP custom:secret:toykey' || no "the missing secret file was not flagged"
  h2="$d/hy"; mkdir -p "$h2"; $M apply --home "$h2" --repo "$d/y/repo" >/dev/null
  [ ! -e "$h2/.claude/settings.json" ] && ! $M plan --home "$h2" --repo "$d/y/repo" | grep -q 'custom:' || no "a repo without custom items got some"
  echo "PASS: a custom item is applied, listed and checked and a repo without one gets nothing"
fi

# done 11: the mailer reads only the local files, prints no secret and names no other recipient.
if want machine-mailer; then
  mk m; h="$d/hm"; ready "$h" "$d/m/repo" || no "ready failed"; S="$h/.workflow-loop/routines/send-mail.py"; export HOME="$h"
  python3 "$S" --to someone@example.test --subject s --body-file /dev/null 2>&1 | grep -q 'unrecognized arguments' || no "the mailer accepts a recipient option"
  printf 'SMTP_USER=toy\nSMTP_PASSWORD=toy-pass-0000\nSMTP_HOST=127.0.0.1\nSMTP_PORT=1\n' > "$h/.workflow-loop/mail.env"
  out=$(python3 "$S" --check 2>&1); echo "$out" | grep -q '^ERROR' || no "a failed login was not an ERROR line"
  echo "$out" | grep -q 'toy-pass-0000\|owner@example' && no "the mailer printed a secret or the address"
  printf 'a@example.test b@example.test\n' > "$h/.workflow-loop/mail-to"
  python3 "$S" --check 2>&1 | grep -q 'exactly one address' || no "two recipients were accepted"
  awk '/^```text template=mailer/{f=1;next} /^```$/{f=0} f' "$here/skills/workflow-monitoring/references/operation.md" | grep -q '@[a-z0-9-]*\.[a-z]' && no "the template holds an address"
  printf 'a@example.test,b@example.test\n' > "$h/.workflow-loop/mail-to"; python3 "$S" --check 2>&1 | grep -q 'exactly one address' || no "a comma list was accepted"
  chmod 644 "$h/.workflow-loop/mail.env"; python3 "$S" --check 2>&1 | grep -q 'mode 600' || no "a loose mail.env was accepted"
  chmod 600 "$h/.workflow-loop/mail.env"; printf 'owner@example.test\n' > "$h/.workflow-loop/mail-to"
  python3 "$S" --subject s --body-file "$h/.workflow-loop/mail.env" 2>&1 | grep -q 'holds a secret' || no "the secrets file was accepted as a body"
  rm -f "$h/.workflow-loop/mail.env"; python3 "$S" --check 2>&1 | grep -q '^ERROR' || no "a missing secrets file was not an ERROR line"
  echo "PASS: the mailer reads only the local files, prints no secret and names no other recipient"
fi

# done 12: machine.py is under the script cap and the only new file under skills/.
if want machine-caps; then
  [ "$(wc -c < "$here/skills/workflow-setup/scripts/machine.py")" -lt 20480 ] || no "machine.py is 20,480 bytes or more"
  for f in $(cd "$here" && git ls-files skills | grep '\.py$'); do [ "$(wc -c < "$here/$f")" -lt 20480 ] || no "$f is over the script cap"; done
  if git -C "$here" rev-parse -q --verify origin/main >/dev/null; then
    new=$(git -C "$here" diff --name-only --diff-filter=A "$(git -C "$here" merge-base HEAD origin/main)" -- skills | grep -v machine.py | wc -l | tr -d ' ')
    [ "$new" = 0 ] || no "more than one new file under skills/"
  fi
  echo "PASS: machine.py and every script stay under the byte cap and machine.py is the only new skills/ file"
fi
exit 0
