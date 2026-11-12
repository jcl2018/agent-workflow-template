#!/bin/bash
# reads: skills/workflow-delivery/scripts/private.py skills/workflow-setup/scripts/seed.py skills/workflow-setup/scripts/setup.py skills/workflow-delivery/references/commands.md
# reads: skills/
# The worker push guard: a goal worker's git push may only update refs/heads/loop/<its slug>. Runs real pushes under the
# real pre-push hook (installed by setup --git-hooks) from a goal worktree under <common>/loop/worktrees/, and from the
# main checkout. A mistake guard, not enforcement (--no-verify skips it).
# usage: test-push-guard.sh [GROUP] [DIR]     GROUP: refuse | allow | where | all (default)
set -u
here=$(cd "$(dirname "$0")/../.." && pwd)
. "$here/dev/toy/reap.sh"
unset LOOP_NO_GIT_HOOKS LOOP_SESSION_TOOL LOOP_OPERATION_SESSION GITHUB_ACTIONS LOOP_HEALTH_HOOKS LOOP_HOOK_DEADLINE LOOP_HOOK_RANGE LOOP_ROLE
group=${1:-all}; case "$group" in all|refuse|allow|where) shift 2>/dev/null ;; *) group=all ;; esac
want() { [ "$group" = all ] || [ "$group" = "$1" ]; }
T=${1:-$(mktemp -d)}; rm -rf "${T:?}"; mkdir -p "$T"
export HOME="$T/home"; mkdir -p "$HOME"
export GIT_CONFIG_GLOBAL="$T/gitconfig" GIT_CONFIG_NOSYSTEM=1 GIT_EDITOR=true GIT_TERMINAL_PROMPT=0; : > "$GIT_CONFIG_GLOBAL"
export LOOP_PRIVATE_NAMES="$T/none"; printf '# comments only\n' > "$T/none"
cp -R "$here/skills" "$T/skills"
PV="$T/skills/workflow-delivery/scripts/private.py"
fails=0
ok() { echo "PASS: $1"; }
bad() { echo "FAIL: $1"; fails=$((fails + 1)); }
check() { if eval "$2"; then ok "$1"; else bad "$1"; [ -z "${DEBUG:-}" ] || printf "%s\n" "$out" | tail -8; fi; }
r() { out=$(eval "$@" 2>&1); rc=$?; }
has() { grep -q -- "$1" <<<"$out"; }
git init -q --bare -b main "$T/origin.git"; git init -q -b main "$T/m"
git -C "$T/m" config user.email t@example.test; git -C "$T/m" config user.name Toy
echo base > "$T/m/a.txt"; git -C "$T/m" add -A; git -C "$T/m" commit -qm base
git -C "$T/m" remote add origin "$T/origin.git"; git -C "$T/m" push -q origin main
python3 "$T/skills/workflow-setup/scripts/setup.py" --repo "$T/m" --git-hooks >/dev/null 2>&1
W="$T/m/.git/loop/worktrees/demo"; mkdir -p "$T/m/.git/loop/worktrees"
git -C "$T/m" worktree add -q -b loop/demo "$W" main
echo work > "$W/b.txt"; git -C "$W" add -A; git -C "$W" commit -qm work
remote_has() { git -C "$T/origin.git" rev-parse -q --verify "$1" >/dev/null; }

if want refuse; then
echo "== a worker may push only loop/<slug>"
r "git -C $W push origin HEAD:refs/heads/main"
check "a worker's push to main is refused naming the code, and main on origin is unchanged" '[ $rc != 0 ] && has "WORKER_PUSH" && [ "$(git -C $T/origin.git rev-parse main)" = "$(git -C $T/m rev-parse main)" ]'
r "git -C $W push origin HEAD:refs/heads/other"
check "a worker's push to another branch is refused" '[ $rc != 0 ] && has "WORKER_PUSH" && ! remote_has refs/heads/other'
git -C "$W" tag v9.9.9
r "git -C $W push origin v9.9.9"
check "a worker's tag push is refused" '[ $rc != 0 ] && has "WORKER_PUSH" && ! remote_has refs/tags/v9.9.9'
r "git -C $W push origin HEAD:refs/heads/loop/other"
check "a worker's push to another goal's loop branch is refused" '[ $rc != 0 ] && has "WORKER_PUSH" && ! remote_has refs/heads/loop/other'
git -C "$W" push -q origin HEAD:refs/heads/loop/demo 2>/dev/null
r "git -C $W push origin :refs/heads/loop/demo"
check "a worker's deletion of its own branch is refused" '[ $rc != 0 ] && has "WORKER_PUSH" && has "deletion of" && remote_has refs/heads/loop/demo'
r "git -C $W push origin HEAD:refs/heads/loop/demo HEAD:refs/heads/main"
check "a push of two refs with one bad is refused whole" '[ $rc != 0 ] && has "WORKER_PUSH" && [ "$(git -C $T/origin.git rev-parse main)" = "$(git -C $T/m rev-parse main)" ]'
r "git -C $W push --follow-tags origin HEAD:refs/heads/main"
check "--follow-tags to main is refused" '[ $rc != 0 ] && has "WORKER_PUSH"'
r "cd $W && echo 'junk' | python3 $PV hook push"
check "a ref line the guard cannot read is refused as WORKER_PUSH_INTERNAL" '[ $rc = 2 ] && has "WORKER_PUSH_INTERNAL"'
fi

if want allow; then
echo "== what is allowed"
echo more >> "$W/b.txt"; git -C "$W" commit -qam more
r "git -C $W push origin HEAD:refs/heads/loop/demo"
check "a worker pushes its own loop/<slug> branch (forced update too)" '[ $rc = 0 ] && [ "$(git -C $T/origin.git rev-parse loop/demo)" = "$(git -C $W rev-parse HEAD)" ]'
r "git -C $W push --force origin HEAD:refs/heads/loop/demo"
check "a forced push of its own branch is allowed" '[ $rc = 0 ]'
r "git -C $W push origin HEAD:refs/heads/loop/demo"
check "an up-to-date push (empty stdin) is allowed" '[ $rc = 0 ]'
echo m2 >> "$T/m/a.txt"; git -C "$T/m" commit -qam m2
r "LOOP_ROLE=worker git -C $T/m push origin main"
check "the main checkout may push main even with LOOP_ROLE=worker (location, not role)" '[ $rc = 0 ] && [ "$(git -C $T/origin.git rev-parse main)" = "$(git -C $T/m rev-parse main)" ]'
r "git -C $T/m push origin main:refs/heads/release/v1-demo"
check "the main checkout may push a release branch" '[ $rc = 0 ]'
r "printf '' | python3 $PV hook push"
check "empty input is allowed" '[ $rc = 0 ]'
fi

if want where; then
echo "== where"
r "cd $W && python3 $PV where"
check "where names the slug in a worktree" '[ $rc = 0 ] && has "^WORKER demo$"'
mkdir -p "$W/sub/dir"; r "cd $W/sub/dir && python3 $PV where"
check "where names the slug from a subdirectory" 'has "^WORKER demo$"'
r "cd $T/m && python3 $PV where"
check "where says NOT A WORKER in the main checkout" '[ $rc = 0 ] && has "^NOT A WORKER"'
r "cd $T && python3 $PV where"
check "where says UNKNOWN (exit 1) outside a repo, never a guess" '[ $rc = 1 ] && has "^UNKNOWN"'
mkdir -p "$T/links"; ln -s "$T/m" "$T/links/mlink"
r "cd $T/links/mlink/.git/loop/worktrees/demo && python3 $PV where"
check "where sees through a symlinked path" 'has "^WORKER demo$"'
r "grep -c 'WORKER_PUSH' $here/skills/workflow-delivery/references/commands.md"
check "commands.md lists both worker push codes" '[ "$(grep -c "^| .WORKER_PUSH" $here/skills/workflow-delivery/references/commands.md)" -ge 1 ] && grep -q "WORKER_PUSH_INTERNAL" $here/skills/workflow-delivery/references/commands.md'
fi
[ "$fails" = 0 ] || exit 1
echo "ALL PASS"
