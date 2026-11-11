#!/bin/bash
# reads: skills/workflow-delivery/scripts/private.py skills/workflow-setup/scripts/seed.py skills/workflow-setup/scripts/setup.py
# reads: skills/workflow-health/scripts/lean.py skills/workflow-health/scripts/controls.py
# Proves the private-name hooks (DEL-9, SET-8) on throwaway toy repos: the three git hooks setup installs, private.py's hook
# modes, setup's own scan before its commit, and health's hooks rule. The list is a harmless fake token in a temp file
# ($LOOP_PRIVATE_NAMES); the real list is never read; every output of every command is searched for the token at the end.
# usage: test-guard-enforce.sh [SECTION] [DIR]     SECTION: set8 (hooks more setup) | del9 (push limits merge) | one of those | all (default)
set -u
here=$(cd "$(dirname "$0")/../.." && pwd)
. "$here/dev/toy/reap.sh"
unset LOOP_NO_GIT_HOOKS LOOP_SESSION_TOOL LOOP_OPERATION_SESSION GITHUB_ACTIONS LOOP_HEALTH_HOOKS LOOP_HOOK_DEADLINE LOOP_HOOK_RANGE
section=${1:-all}; case "$section" in all|set8|del9|hooks|more|setup|push|limits|merge) shift 2>/dev/null ;; *) section=all ;; esac
want() { case "$section" in all|"$1") return 0 ;; set8) case $1 in hooks|more|setup) return 0 ;; esac ;; del9) case $1 in push|limits|merge) return 0 ;; esac ;; esac; return 1; }
T=${1:-$(mktemp -d)}; rm -rf "${T:?}"; mkdir -p "$T"
TOKEN=zq-guardtest-token
export HOME="$T/home"; mkdir -p "$HOME"
export GIT_CONFIG_GLOBAL="$T/gitconfig" GIT_CONFIG_NOSYSTEM=1 GIT_EDITOR=true GIT_TERMINAL_PROMPT=0; : > "$GIT_CONFIG_GLOBAL"
export PATH="$here/dev/toy/fakegh:$PATH" FAKE_GH_DIR="$T/gh"
printf '# a fake private list for a toy test\n%s\n' "$TOKEN" > "$T/list"
export LOOP_PRIVATE_NAMES="$T/list"
printf '# comments only: off on purpose\n' > "$T/optout"
cp -R "$here/skills" "$T/skills"   # outside loop/worktrees, as an installed copy is
S="$T/skills/workflow-setup/scripts"; PV="$T/skills/workflow-delivery/scripts/private.py"; SETUP="$S/setup.py"
HEALTH="python3 $T/skills/workflow-health/scripts/health.py"
fails=0
ok() { echo "PASS: $1"; }
bad() { echo "FAIL: $1"; fails=$((fails + 1)); }
check() { if eval "$2"; then ok "$1"; else bad "$1"; [ -z "${DEBUG:-}" ] || printf "%s\n" "$out" | tail -8; fi; }
r() { out=$(eval "$@" 2>&1); rc=$?; printf '%s\n' "$out" >> "$T/all.log"; }
has() { grep -q -- "$1" <<<"$out"; }
mk() {  # mk NAME: a repo with one commit on main, and a bare origin
  git init -q --bare -b main "$T/$1.git"; git init -q -b main "$T/$1"
  git -C "$T/$1" config user.email t@example.test; git -C "$T/$1" config user.name Toy
  echo base > "$T/$1/a.txt"; git -C "$T/$1" add -A; git -C "$T/$1" commit -qm base
  git -C "$T/$1" remote add origin "$T/$1.git"; git -C "$T/$1" push -q origin main
}
inst() { python3 "$SETUP" --repo "$T/$1" --git-hooks >/dev/null 2>&1; }
plant() { printf 'one\nline holding %s here\n' "$TOKEN" >> "$T/$1/$2"; }   # the second appended line is the private one
adopt() {  # adopt NAME: a repo ready for setup's default run (hooks not yet installed)
  git init -q -b main "$T/$1"; git -C "$T/$1" config user.email t@example.test; git -C "$T/$1" config user.name Toy
  printf '# Toy\n\n%s\n' "${2:-A calculator.}" > "$T/$1/README.md"; printf 'print(1)\n' > "$T/$1/calc.py"; mkdir "$T/$1/.loop"
  echo '{"agent_command": ["codex", "exec", "--full-auto"]}' > "$T/$1/.loop/config.json"; git -C "$T/$1" add -A; git -C "$T/$1" commit -qm base
}

if want hooks; then
echo "== SET-8: setup installs the hooks, and a private line is refused at commit"
mk s1; r "python3 $SETUP --repo $T/s1 --git-hooks"
check "setup --git-hooks writes pre-commit, commit-msg and pre-push" '[ $rc = 0 ] && for h in pre-commit commit-msg pre-push; do grep -q workflow-loop-hook "$T/s1/.git/hooks/$h" && [ -x "$T/s1/.git/hooks/$h" ] && grep -q "private.py" "$T/s1/.git/hooks/$h" || exit 1; done'
r "python3 $SETUP --repo $T/s1 --git-hooks"
check "a second run leaves them as they are" '[ $rc = 0 ] && has "hook pre-commit: installed" && has "^list: PRIVATE LIST: 1 pattern from"'
plant s1 b.txt; git -C "$T/s1" add b.txt; r "git -C $T/s1 commit -m 'add b'"
check "git commit refuses a staged private line, naming file and line" '[ $rc != 0 ] && has "b.txt:2 (staged) matches list line 2" && has "PRIVATE_NAME" && has "nothing was committed" && ! has "$TOKEN"'
check "the refused commit did not happen" '[ "$(git -C $T/s1 rev-list --count HEAD)" = 1 ]'
git -C "$T/s1" reset -q; rm "$T/s1/b.txt"
printf 'fine\n' > "$T/s1/c.txt"; git -C "$T/s1" add c.txt; r "git -C $T/s1 commit -m 'clean change'"
check "a clean commit goes through" '[ $rc = 0 ]'
r "git -C $T/s1 commit --allow-empty -m 'about $TOKEN'"
check "commit-msg refuses a private commit message, naming the message and not the match" '[ $rc != 0 ] && has "commit message matches list line 2" && ! has "$TOKEN"'
printf 'x\n' >> "$T/s1/c.txt"; git -C "$T/s1" add c.txt; r "git -C $T/s1 commit --amend -m 'amended $TOKEN'"
check "an amend with a private message is refused too" '[ $rc != 0 ] && has "commit message matches"'
git -C "$T/s1" reset -q --hard
printf 'line\n' >> "$T/s1/c.txt"; plant s1 c.txt; r "git -C $T/s1 commit -a -m 'with -a'"
check "commit -a is scanned through git's temporary index" '[ $rc != 0 ] && has "c.txt:" && ! has "$TOKEN"'
git -C "$T/s1" checkout -q -- c.txt
printf 'clean part\n' >> "$T/s1/c.txt"; git -C "$T/s1" add c.txt; plant s1 c.txt; r "git -C $T/s1 commit -m partial"
check "partial staging: a private line only in the work tree is not scanned" '[ $rc = 0 ]'
git -C "$T/s1" reset -q --hard
echo "token only in a removed line" > "$T/s1/d.txt"; printf '%s\n' "$TOKEN" >> "$T/s1/d.txt"; git -C "$T/s1" add d.txt; git -C "$T/s1" commit -q --no-verify -m "d with a private line"
printf '#!/bin/sh\n{ echo "clean subject"; cat "$1"; } > "$1.n" && mv "$1.n" "$1"\n' > "$T/ed.sh"; chmod +x "$T/ed.sh"
git -C "$T/s1" rm -q d.txt; r "GIT_EDITOR=$T/ed.sh git -C $T/s1 commit -v"
check "commit -v puts the diff below the scissors line: a removed private line there is not scanned" '[ $rc = 0 ] && ! has "private name"'
printf '%s\nok\n; a comment %s\n; ------------------------ >8 ------------------------\nbelow %s\n' "fine subject" "$TOKEN" "$TOKEN" > "$T/msg1"
r "cd $T/s1 && python3 $PV hook message $T/msg1"
check "the hook strips comment lines of core.commentChar and everything below the scissors line (default #: the ; lines are text)" '[ $rc = 1 ] && has "commit message matches list line 2"'
r "cd $T/s1 && git config core.commentChar ';'; python3 $PV hook message $T/msg1; git config --unset core.commentChar"
check "with core.commentChar set to ; the comment and scissors lines are skipped and the message passes" '[ $rc = 0 ]'
r "cd $T/s1 && git config core.commentChar auto; python3 $PV hook message $T/msg1; git config --unset core.commentChar"
check "core.commentChar=auto does not crash the hook" '[ $rc = 0 ] || [ $rc = 1 ]'
git -C "$T/s1" mv a.txt "$TOKEN-name.txt"; r "git -C $T/s1 commit -m rename"
check "a private file name is refused with the name masked, never echoed" '[ $rc != 0 ] && has "file name <private>-name.txt matches list line 2" && ! has "$TOKEN"'
git -C "$T/s1" reset -q --hard
python3 -c "
import sys
sys.stdout.buffer.write(b'caf\xe9 \xff\xfe $TOKEN \x80\n')" > "$T/s1/bin.txt"; git -C "$T/s1" add bin.txt; r "git -C $T/s1 commit -m latin1"
check "non-UTF-8 content is scanned, not skipped or crashed on" '[ $rc != 0 ] && has "bin.txt:1 (staged)" && ! has "$TOKEN"'
git -C "$T/s1" reset -q; rm "$T/s1/bin.txt"
mkdir -p "$T/s1/odd dir"; plant s1 "odd dir/it's here.txt"; git -C "$T/s1" add -A; r "git -C $T/s1 commit -m odd"
check "a file name with spaces and a quote is scanned" '[ $rc != 0 ] && has "matches list line 2" && ! has "$TOKEN"'
git -C "$T/s1" reset -q; rm -rf "$T/s1/odd dir"

fi
if want more; then
echo "== SET-8: --remove, foreign hooks, hooksPath, paths, linked worktrees"
mk s2; inst s2; printf '#!/bin/sh\necho mine\n' > "$T/s2/.git/hooks/pre-push"
r "python3 $SETUP --repo $T/s2 --git-hooks --remove"
check "--remove takes out only our hooks" '[ $rc = 0 ] && [ ! -e "$T/s2/.git/hooks/pre-commit" ] && [ ! -e "$T/s2/.git/hooks/commit-msg" ] && grep -q "echo mine" "$T/s2/.git/hooks/pre-push" && has "pre-push: kept, it is not the stub setup writes"'
mk s2b; inst s2b; echo "# the owner added a line" >> "$T/s2b/.git/hooks/pre-commit"
r "python3 $SETUP --repo $T/s2b --git-hooks --remove"
check "--remove leaves a stub the owner edited (not a byte match) and says why" '[ -e "$T/s2b/.git/hooks/pre-commit" ] && has "pre-commit: kept, it is not the stub setup writes"'
mk s3; printf '#!/bin/sh\necho owner hook\n' > "$T/s3/.git/hooks/pre-commit"
r "python3 $SETUP --repo $T/s3 --git-hooks"
check "a foreign hook is left alone: the line to add is printed and the exit is 1" '[ $rc = 1 ] && has "pre-commit: left alone, it is not ours. Add: python3 .*private.py. hook staged" && grep -q "owner hook" "$T/s3/.git/hooks/pre-commit" && ! grep -q workflow-loop-hook "$T/s3/.git/hooks/pre-commit"'
check "the other hooks are still installed beside a foreign one" '[ -x "$T/s3/.git/hooks/pre-push" ] && [ -x "$T/s3/.git/hooks/commit-msg" ]'
printf '#!/bin/sh\npython3 %q hook staged || exit 1\n' "$PV" > "$T/s3/.git/hooks/pre-commit"
r "python3 $SETUP --repo $T/s3 --git-hooks"
check "a hook that already holds the call counts as installed" '[ $rc = 0 ] && has "pre-commit: already calls the scan"'
mk s4; git -C "$T/s4" config core.hooksPath .githooks
r "python3 $SETUP --repo $T/s4 --git-hooks"
check "a core.hooksPath is refused with the lines to add (exit 1, nothing written)" '[ $rc = 1 ] && has "REFUSED: core.hooksPath is set" && has "hook staged" && has "hook message" && [ ! -e "$T/s4/.git/hooks/pre-commit" ]'
mk s5; printf '[core]\n\thooksPath = %s/elsewhere\n' "$T" > "$GIT_CONFIG_GLOBAL"
r "python3 $SETUP --repo $T/s5 --git-hooks"
check "a global core.hooksPath is refused too" '[ $rc = 1 ] && has "core.hooksPath is set" && [ ! -e "$T/s5/.git/hooks/pre-commit" ]'
: > "$GIT_CONFIG_GLOBAL"
mkdir "$T/we%ird" && cp -R "$here/skills" "$T/we%ird/skills"; mk s6
r "python3 '$T/we%ird/skills/workflow-setup/scripts/setup.py' --repo $T/s6 --git-hooks"
check "a path holding a percent sign is refused" '[ $rc = 1 ] && has "percent sign" && [ ! -e "$T/s6/.git/hooks/pre-commit" ]'
mk s7; r "python3 $here/skills/workflow-setup/scripts/setup.py --repo $T/s7 --git-hooks"
check "skills living under loop/worktrees are refused (a goal worktree goes away)" 'case "$here" in */loop/worktrees/*) [ $rc = 1 ] && has "inside a goal" ;; *) true ;; esac'
mk s7b; git -C "$T/s7b" worktree add -q -b side "$T/s7b-side"; r "python3 $SETUP --repo $T/s7b-side --git-hooks"
check "from a linked worktree the hooks land in the common git dir, shared by every worktree" '[ $rc = 0 ] && [ -x "$T/s7b/.git/hooks/pre-commit" ] && [ ! -e "$T/s7b/.git/worktrees/s7b-side/hooks/pre-commit" ]'
mk s7c; git -C "$T/s7c" worktree add -q -b loopwt "$T/s7c/.git/loop/worktrees/g"
r "python3 $SETUP --repo $T/s7c/.git/loop/worktrees/g --git-hooks"
check "a repo that is a goal's worktree under loop/worktrees is refused" '[ $rc = 1 ] && has "inside a goal" && [ ! -e "$T/s7c/.git/hooks/pre-commit" ]'

echo "== SET-8: a stub fails closed and says how to repair"
mk s8; inst s8; sed -i.b "s|^P='[^']*'|P='/nowhere/python3'|" "$T/s8/.git/hooks/pre-commit"; rm -f "$T/s8/.git/hooks/pre-commit.b"
r "env PATH=$T/nopath /bin/sh $T/s8/.git/hooks/pre-commit"
check "with python3 gone and off PATH the hook refuses, names the rerun command and git's own --no-verify" '[ $rc = 1 ] && has "python3 is not on PATH" && has "Fix: python3 .*setup.py. --git-hooks" && has "no-verify"'
mkdir "$T/sk2" && cp -R "$here/skills" "$T/sk2/skills"; mk s9
python3 "$T/sk2/skills/workflow-setup/scripts/setup.py" --repo "$T/s9" --git-hooks >/dev/null 2>&1; rm -rf "$T/sk2"
echo x > "$T/s9/x.txt"; git -C "$T/s9" add x.txt; r "git -C $T/s9 commit -m x"
check "a stub whose private.py moved refuses the commit and names the rerun command, never 'a private name'" '[ $rc != 0 ] && has "private.py is gone" && has "setup.py. --git-hooks" && ! has "would be"'
git -C "$T/s9" reset -q
r "cd $T/s8 && python3 $PV hook bogus"
check "an unknown hook mode is exit 64 with the usage line" '[ $rc = 64 ] && has "usage: private.py hook staged"'
mk s8b; inst s8b; sed -i.b 's/^run staged$/run bogus/' "$T/s8b/.git/hooks/pre-commit"; rm -f "$T/s8b/.git/hooks/pre-commit.b"
echo x > "$T/s8b/x.txt"; git -C "$T/s8b" add x.txt; r "git -C $T/s8b commit -m x"
check "a stub wired to a bad mode (exit 64) says the hook is wired wrong and names the repair" '[ $rc != 0 ] && has "wired wrong" && has "setup.py. --git-hooks"'
mk s10; inst s10; printf '(a+)+$\n' > "$T/slow"; python3 -c "print('a' * 40 + 'b')" > "$T/s10/slow.txt"; git -C "$T/s10" add slow.txt
r "LOOP_PRIVATE_NAMES=$T/slow LOOP_HOOK_DEADLINE=1 git -C $T/s10 commit -m slow"
check "a catastrophic pattern is killed by the alarm and the hook fails closed with the too-slow message" '[ $rc != 0 ] && has "took too long" && has "too slow" && [ "$(git -C $T/s10 rev-list --count HEAD)" = 1 ]'
r "cd $T/s10 && LOOP_PRIVATE_NAMES=$T/slow LOOP_HOOK_DEADLINE=1 sh -c 'python3 $PV hook staged; echo exit=\$?'"
check "the engine itself is ended by the kernel (exit 142)" 'has "exit=142"'
git -C "$T/s10" reset -q
printf 'fine\n%s(\n' "$TOKEN" > "$T/badre"
echo x > "$T/s10/x.txt"; git -C "$T/s10" add x.txt; r "LOOP_PRIVATE_NAMES=$T/badre git -C $T/s10 commit -m x"
check "a broken list refuses the commit with PRIVATE_LIST naming the list line, never its text" '[ $rc != 0 ] && has "PRIVATE_LIST" && has "line 2" && has "nothing was committed" && ! has "$TOKEN" && [ "$(git -C $T/s10 rev-list --count HEAD)" = 1 ]'
r "LOOP_PRIVATE_NAMES=$T/nope git -C $T/s10 commit -m x"
check "a named list file that does not exist is PRIVATE_LIST too" '[ $rc != 0 ] && has "PRIVATE_LIST"'
printf 'a*\n' > "$T/emptyre"
r "LOOP_PRIVATE_NAMES=$T/emptyre git -C $T/s10 commit -m x"
check "a pattern that matches the empty string (or ordinary text) is a broken list, not a flag on every line" '[ $rc != 0 ] && has "PRIVATE_LIST" && has "line 1 matches ordinary text"'
r "LOOP_PRIVATE_NAMES=$T/optout git -C $T/s10 commit -m x"
check "a comment-only list is off on purpose and the commit goes through" '[ $rc = 0 ]'
r "env -u LOOP_PRIVATE_NAMES HOME=$T/nohome git -C $T/s10 commit --allow-empty -m y"
check "no list at all passes the commit silently" '[ $rc = 0 ]'

echo "== SET-8: health reports the hooks"
r "cd $T/s10 && $HEALTH check --group hygiene"
check "health passes a repo with the hooks installed" 'has "^PASS hygiene hooks hooks: the private-name hooks are installed"'
python3 "$SETUP" --repo "$T/s10" --git-hooks --remove >/dev/null 2>&1
r "cd $T/s10 && $HEALTH check --group hygiene"
check "health WARNs a repo with the hooks removed, naming each, with no home path" 'has "^WARN hygiene hooks hooks: commit-msg: missing; pre-commit: missing; pre-push: missing" && ! has "$HOME"'
r "cd $T/s10 && GITHUB_ACTIONS=true $HEALTH check --group hygiene"
check "the rule is skipped on GitHub Actions" 'has "^PASS hygiene hooks hooks: skipped on GitHub Actions"'
r "cd $T/s10 && GITHUB_ACTIONS=true $HEALTH check --group controls"
check "its negative control still fires on Actions" 'has "^PASS controls hooks control: fires on its fixture"'
r "cd $T/s9 && $HEALTH check --group hygiene"
check "a stub whose private.py moved is a stale WARN before it blocks a commit" 'has "pre-commit: stale"'
mk s11; inst s11; r "cd $T/s11 && LOOP_PRIVATE_NAMES=$T/badre $HEALTH check --group hygiene"
check "a broken list is a WARN that names the way to see the line, never the pattern" 'has "WARN hygiene hooks hooks: the private-name list is broken" && ! has "$TOKEN"'
r "cd $T/s11 && env -u LOOP_PRIVATE_NAMES HOME=$T/nohome $HEALTH check --group hygiene"
check "no list is not a health finding (the board lists it)" 'has "^PASS hygiene hooks hooks: the private-name hooks are installed"'
mkdir -p "$T/old/skills"; cp -R "$here/skills/." "$T/old/skills/"; printf 'import sys\nsys.exit(2)\n' > "$T/old/skills/workflow-setup/scripts/setup.py"
r "cd $T/s11 && python3 $T/old/skills/workflow-health/scripts/health.py check --group hygiene"
check "an old setup.py beside the new health is one WARN to update the skills" 'has "cannot read the hook state" && has "update the skills so setup.py has --git-hooks --check"'
r "python3 $SETUP --repo $T/s11 --git-hooks --check --json"
check "--check --json carries a schema version, the list state and each hook, no pattern" 'has "\"version\": 1" && has "\"list\": \"on\"" && has "\"pre-commit\": \"installed\"" && ! has "$TOKEN"'
r "LOOP_PRIVATE_NAMES=$T/badre python3 $SETUP --repo $T/s11 --git-hooks --check --json"
check "--check --json reports a broken list as broken (exit 1), still no pattern" '[ $rc = 1 ] && has "\"list\": \"broken\"" && ! has "$TOKEN"'

fi
if want setup; then
echo "== SET-8: setup scans its own staged adoption files before it commits"
adopt a1 "This is $TOKEN itself."
r "cd $T/a1 && python3 $SETUP"
check "setup refuses to commit an adoption file holding a private line (exit 1, nothing committed)" '[ $rc = 1 ] && has "matches list line 2" && has "REFUSED: a staged adoption file holds a private name" && ! git -C $T/a1 log --oneline 2>/dev/null | grep -q Adopt'
check "the setup refusal output never holds the match" '! has "$TOKEN"'
adopt a2; r "cd $T/a2 && python3 $SETUP"
check "the default adoption run installs the three hooks, after its commit" '[ $rc = 0 ] && has "WROTE the adoption" && [ -x "$T/a2/.git/hooks/pre-commit" ] && [ -x "$T/a2/.git/hooks/commit-msg" ] && [ -x "$T/a2/.git/hooks/pre-push" ]'
adopt a3; r "cd $T/a3 && LOOP_NO_GIT_HOOKS=1 python3 $SETUP"
check "LOOP_NO_GIT_HOOKS=1 skips the hook install" '[ $rc = 0 ] && [ ! -e "$T/a3/.git/hooks/pre-commit" ]'
adopt a3b; r "cd $T/a3b && python3 $SETUP --no-git-hooks"
check "--no-git-hooks skips the hook install" '[ $rc = 0 ] && [ ! -e "$T/a3b/.git/hooks/pre-commit" ]'
adopt a4; r "cd $T/a4 && python3 $here/skills/workflow-setup/scripts/setup.py"
check "the default run from skills under loop/worktrees writes no hooks, prints a NOTE and exits 0" 'case "$here" in */loop/worktrees/*) [ $rc = 0 ] && has "NOTE: private.py or the repo is inside a goal" && [ ! -e "$T/a4/.git/hooks/pre-commit" ] ;; *) true ;; esac'
fi

if want push; then
echo "== DEL-9: the pre-push hook and the push scan"
mk p1; inst p1; git -C "$T/p1" checkout -q -b feat; echo ok > "$T/p1/ok.txt"; git -C "$T/p1" add -A; git -C "$T/p1" commit -qm ok
r "git -C $T/p1 push origin feat"
check "a clean new branch is pushed through the pre-push hook" '[ $rc = 0 ] && git -C $T/p1 ls-remote --exit-code origin feat >/dev/null'
plant p1 b.txt; git -C "$T/p1" add -A; git -C "$T/p1" commit -q --no-verify -m "plant"
r "git -C $T/p1 push origin feat"
check "an update of an existing branch with a planted line is refused by the pre-push hook, naming file and line" '[ $rc != 0 ] && has "b.txt:2 (commit:" && has "nothing was pushed" && ! has "$TOKEN"'
check "nothing reached the remote" '[ "$(git -C $T/p1 rev-parse origin/feat)" = "$(git -C $T/p1 ls-remote origin feat | cut -f1)" ] && [ "$(git -C $T/p1 rev-parse feat)" != "$(git -C $T/p1 ls-remote origin feat | cut -f1)" ]'
git -C "$T/p1" checkout -q main; git -C "$T/p1" checkout -q -b fresh; plant p1 f.txt; git -C "$T/p1" add -A; git -C "$T/p1" commit -q --no-verify -m "plant"
r "git -C $T/p1 push origin fresh"
check "a new branch holding a planted line is refused: the hook really receives git's ref lines" '[ $rc != 0 ] && has "f.txt:2 (commit:" && ! git -C $T/p1 ls-remote --exit-code origin fresh >/dev/null 2>&1'
r "cd $T/p1 && echo \"refs/heads/fresh $(git -C $T/p1 rev-parse fresh) refs/heads/fresh 1111111111111111111111111111111111111111\" | python3 $PV hook push"
check "a remote sha git cannot resolve (a force push, an unfetched ref) still scans the commits on no remote, never failing open" '[ $rc = 1 ] && has "f.txt:2 (commit:"'
r "cd $T/p1 && echo \"(delete) 0000000000000000000000000000000000000000 refs/heads/gone $(git -C $T/p1 rev-parse main)\" | python3 $PV hook push"
check "a deletion push is skipped" '[ $rc = 0 ]'
r "git -C $T/p1 push origin :feat"
check "git push of a deletion goes through the hook and is allowed" '[ $rc = 0 ]'
git -C "$T/p1" checkout -q main; git -C "$T/p1" checkout -q -b two; plant p1 c.txt; git -C "$T/p1" add -A; git -C "$T/p1" commit -q --no-verify -m "add"
git -C "$T/p1" rm -q c.txt; git -C "$T/p1" commit -q --no-verify -m "remove"
r "git -C $T/p1 push origin two"
check "a line added in one commit and removed in the next is still caught by the push scan" '[ $rc != 0 ] && has "c.txt:2 (commit:"'
git -C "$T/p1" checkout -q main; git -C "$T/p1" checkout -q -b msgb; git -C "$T/p1" commit -q --no-verify --allow-empty -m "has $TOKEN"
r "git -C $T/p1 push origin msgb"
check "a private commit message stops the push" '[ $rc != 0 ] && has "message matches list line 2" && ! has "$TOKEN"'
git -C "$T/p1" tag -a -m "tag" v1 msgb 2>/dev/null; r "git -C $T/p1 push origin v1"
check "a tag push scans the commits the tag adds" '[ $rc != 0 ] && has "message matches"'
fi
if want limits; then
[ -d "$T/p1" ] || { mk p1; inst p1; }
git -C "$T/p1" checkout -q main; git -C "$T/p1" checkout -q -b "br-$TOKEN"; echo e > "$T/p1/e.txt"; git -C "$T/p1" add -A; git -C "$T/p1" commit -qm e
r "git -C $T/p1 push origin HEAD"
check "a private branch name is refused as a ref name, masked" '[ $rc != 0 ] && has "ref name refs/heads/br-<private> matches" && ! has "$TOKEN"'
git -C "$T/p1" checkout -q main; git -C "$T/p1" checkout -q -b long; c=$(git -C "$T/p1" rev-parse HEAD); tr=$(git -C "$T/p1" rev-parse 'HEAD^{tree}')
for i in $(seq 505); do c=$(git -C "$T/p1" commit-tree "$tr" -p "$c" -m "n$i"); done; git -C "$T/p1" update-ref refs/heads/long "$c"
r "cd $T/p1 && echo \"refs/heads/long $c refs/heads/long 0000000000000000000000000000000000000000\" | python3 $PV hook push"
check "a push of more than 500 commits fails closed, naming the bound and LOOP_HOOK_RANGE" '[ $rc = 2 ] && has "over the 500 limit" && has "LOOP_HOOK_RANGE"'
r "cd $T/p1 && echo \"refs/heads/long $c refs/heads/long 0000000000000000000000000000000000000000\" | LOOP_HOOK_RANGE=$(git -C $T/p1 rev-parse long~5) python3 $PV hook push"
check "LOOP_HOOK_RANGE=<rev> scans from that rev for one push" '[ $rc = 0 ]'
r "cd $T/p1 && echo \"refs/heads/long $(printf '%040d' 7) refs/heads/long 0000000000000000000000000000000000000000\" | python3 $PV hook push"
check "a local object that is missing fails closed (exit 2), not open" '[ $rc = 2 ]'
git -C "$T/p1" checkout -q main
fi
if want merge; then
mk p2; git -C "$T/p2" checkout -q -b feat; plant p2 b.txt; git -C "$T/p2" add -A; git -C "$T/p2" commit -q --no-verify -m "plant"
r "git -C $T/p2 push origin feat"
check "with no hooks installed the same push goes through (the merge step is what then refuses it)" '[ $rc = 0 ]'
r "bash $here/dev/toy/test-delivery-release.sh private"
check "the merge step then refuses the pushed planted line (delivery-prd's merge refusal, run here)" 'has "PASS: DEL-9: a private name in the branch refuses merge.py, nothing merged"'
fi

echo "== no output of any command held the token"
if grep -q -- "$TOKEN" "$T/all.log"; then bad "the token appeared in output"; else ok "the token never appeared in any stdout or stderr"; fi
[ "$fails" = 0 ] && { echo "ALL PASSED"; rm -rf "$T"; exit 0; }
echo "$fails FAILED (kept $T)"; exit 1
