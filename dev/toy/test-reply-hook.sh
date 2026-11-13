#!/bin/bash
# reads: skills/
# Proves the operation session's reply-format Stop hook (reply_hook.py) and its installer (setup.py --reply-hook) with
# made-up transcripts shaped like real Claude Code ones. No model is called and no real session is touched.
# usage: test-reply-hook.sh [DIR]
set -u
unset LOOP_SESSION_TOOL LOOP_OPERATION_SESSION LOOP_ROLE LOOP_REPLY_HOOK  # a toy test never reaches a real session tool
here=$(cd "$(dirname "$0")/../.." && pwd)
. "$here/dev/toy/reap.sh"
T=${1:-$(mktemp -d)}; rm -rf "${T:?}"; mkdir -p "$T"
H="$here/skills/workflow-monitoring/scripts/reply_hook.py"
SETUP="$here/skills/workflow-setup/scripts/setup.py"
export HOME="$T/home"; mkdir -p "$HOME"
export LOOP_BOARD_HEALTH=green PATH="$here/dev/toy/fakegh:$PATH" FAKE_GH_DIR="$T/gh"
fails=0
ok() { echo "PASS: $1"; }
bad() { echo "FAIL: $1"; fails=$((fails + 1)); }
check() { if eval "$2"; then ok "$1"; else bad "$1"; fi; }
"$here/dev/toy/make.sh" "$T" >/dev/null || exit 1
cd "$T/repo" || exit 1
mkdir -p .loop && echo '{"base": "main"}' > .loop/config.json
C=$(cd "$(git rev-parse --git-common-dir)" && pwd -P)
mkdir -p "$C/loop/worktrees/wt" "$T/other"
F="$T/fx"; mkdir -p "$F"
# Check-in replies in the owner's layout (issue 123) and broken ones, then transcripts built around them.
python3 - "$F" <<'PY'
import json, os, sys
F = sys.argv[1]
good = """Two goals moved; one needs you.

## All sessions
| session | repo | for | status | progress | ETA | tokens left | latest |
|---|---|---|---|---|---|---|---|
| worker · alpha | toy | median command | running | build | 20m | 1.2M | built, testing |

## Dependencies
```
== toy ==
[>] alpha
 |
[ ] beta
```

## Needs you
1. Release alpha? Options: cut, leave. Recommended: leave.

## Coming up
- about 18:10: alpha opens its pull request
- you: answer question 1 when it lands
"""
replies = {
    "good": good,
    "noboard": "Two goals moved. I'll check again in 30 minutes.",
    "nosection": good.replace("## Dependencies\n", ""),
    "order": good.replace("## Needs you\n1. Release alpha? Options: cut, leave. Recommended: leave.\n\n", "") +
             "\n## Needs you\n1. Release alpha?\n",
    "noheadline": good.replace("Two goals moved; one needs you.\n\n", ""),
    "twoheadlines": "Status report.\n" + good,
    "emptyneeds": good.replace("1. Release alpha? Options: cut, leave. Recommended: leave.\n", "We will see.\n"),
    "nothing": good.replace("1. Release alpha? Options: cut, leave. Recommended: leave.\n", "Nothing needs you.\n"),
    "bold": good.replace("## All sessions", "**All sessions:**", 1),
    "cased": good.replace("## All sessions", "## All Sessions").replace("## Needs you", "## Needs you (1)").replace(
        "1. Release alpha?", "- Q1. Release alpha?"),
    "fenced": good.replace("## Coming up\n", "```\nComing up\n```\n"),
    "onefence": good.replace("[ ] beta\n```\n", "[ ] beta\n```\n```a -> b```\n"),
    "clock": good.replace("1. Release alpha? Options: cut, leave. Recommended: leave.\n", "- 10:30 standup\n"),
}
for name, text in replies.items():
    open(os.path.join(F, name + ".txt"), "w").write(text)
def tool(i, command, out, error=False, code=True):
    use = {"type": "assistant", "isSidechain": False, "message": {"id": "m%d" % i, "role": "assistant",
           "content": [{"type": "tool_use", "id": "t%d" % i, "name": "Bash", "input": {"command": command}}]}}
    text = ("Exit code 1\n" + out) if error and code else out  # a denied call has no exit code
    res = {"type": "user", "isSidechain": False, "message": {"role": "user", "content": [
           {"type": "tool_result", "tool_use_id": "t%d" % i, "content": text, "is_error": error}]}}
    return [use, res]
def final(text, split=False):
    cut = text.find("\n## Needs you")  # text blocks of one message split at block boundaries, here a line end
    parts = [text[:cut], text[cut + 1:]] if split else [text]
    out = [{"type": "assistant", "isSidechain": False, "message": {"id": "mfinal", "role": "assistant",
            "content": [{"type": "thinking", "thinking": ""}]}}]
    out += [{"type": "assistant", "isSidechain": False, "message": {"id": "mfinal", "role": "assistant",
             "content": [{"type": "text", "text": p}]}} for p in parts]
    return out
noise = [{"type": "attachment"}, {"type": "custom-title", "title": "x"}, {"type": "last-prompt"}, {"type": "agent-name"}]
side = [{"type": "assistant", "isSidechain": True, "message": {"id": "ms", "content": [{"type": "text", "text": "subagent"}]}}]
operate = tool(1, "cd /repo && python3 skills/workflow-monitoring/scripts/operate.py run", "LIVE BOARD  toy ...")
prompt = [{"type": "user", "message": {"role": "user", "content": "check in"}}]
def save(name, items):
    with open(os.path.join(F, name + ".jsonl"), "w") as handle:
        for item in items:
            handle.write(json.dumps(item) + "\n")
save("op-good", prompt + operate + final(good, split=True) + side + noise)
save("op-bad", prompt + operate + final(replies["noboard"]) + noise)
save("op-lag", prompt + operate + final(replies["noboard"]) + tool(2, "ls", "a"))
save("op-bg", prompt + tool(1, "python3 skills/workflow-monitoring/scripts/operate.py run",
                            "Command running in background with ID: b1.") + final(replies["noboard"]) + noise)
save("op-refused-step", prompt + operate + tool(2, "LOOP_ROLE= python3 skills/workflow-delivery/scripts/goal.py step g build",
     "REFUSED: step is worker work; the operation session only assigns, watches and reports.", True) + final(replies["noboard"]))
save("worker-main", prompt + tool(1, "LOOP_ROLE=worker python3 skills/workflow-delivery/scripts/goal.py record g idea --file r",
     "RECORDED idea done") + operate + tool(3, "LOOP_ROLE=worker python3 skills/workflow-delivery/scripts/goal.py step g build",
     "STEP g build") + final(replies["noboard"]) + noise)
save("worker-refused-operate", prompt + tool(1, "python3 skills/workflow-monitoring/scripts/operate.py run",
     "REFUSED: run is not for a worker", True) + final(replies["noboard"]))
save("mention", prompt + tool(1, "grep -n 'operate.py run' skills/workflow-monitoring/SKILL.md", "12: operate.py run") +
     final(replies["noboard"]))
save("plain", prompt + final(replies["noboard"]))
save("board-only", prompt + tool(1, "python3 skills/workflow-monitoring/scripts/board.py board", "LIVE BOARD") + final(replies["noboard"]))
save("op-flags", prompt + tool(1, "cd /r; python3 -u skills/workflow-monitoring/scripts/operate.py --repo . run | tail -3", "x") +
     final(replies["noboard"]))
pending = [{"type": "assistant", "isSidechain": False, "message": {"id": "mlast", "role": "assistant", "content": [
           {"type": "text", "text": "Let me check."}, {"type": "tool_use", "id": "t9", "name": "Bash", "input": {"command": "ls"}}]}}]
save("op-pending", prompt + operate + pending)
synthetic = [{"type": "assistant", "isSidechain": False, "isApiErrorMessage": True, "message": {"id": "merr", "model": "<synthetic>",
              "role": "assistant", "content": [{"type": "text", "text": "API Error: rate limited"}]}}]
save("op-synthetic", prompt + operate + synthetic)
save("op-quoted", prompt + tool(1, "python3 skills/workflow-monitoring/scripts/operate.py run",
     "watch: REFUSED: git fetch: network\nLIVE BOARD  toy") + final(replies["noboard"]))
save("op-timeout", prompt + tool(1, "python3 skills/workflow-monitoring/scripts/operate.py run", "Exit code 143\nTerminated", True) +
     final(replies["noboard"]))
save("not-op", prompt + tool(1, "python3 skills/workflow-monitoring/scripts/operate.py send g1 run", "SENT") +
     tool(2, "python3 -m py_compile skills/workflow-delivery/scripts/flow.py", "") + final(replies["noboard"]))
save("op-bashc", prompt + tool(1, "bash -c 'cd /r && python3 skills/workflow-monitoring/scripts/operate.py run'", "x") +
     final(replies["noboard"]))
split_use, split_res = tool(1, "python3 skills/workflow-monitoring/scripts/operate.py run", "LIVE BOARD")
save("split-1", prompt + [split_use])
save("split-2", prompt + [split_use, split_res] + final(replies["noboard"]))
save("denied", prompt + operate + tool(2, "python3 skills/workflow-delivery/scripts/goal.py step g build",
     "The user doesn't want to proceed with this tool use. The tool use was rejected.", True, False) + final(replies["noboard"]))
save("grow-1", prompt + operate + final(replies["noboard"]))
save("grow-2", prompt + operate + final(replies["noboard"]) +
     tool(5, "LOOP_ROLE=worker python3 skills/workflow-delivery/scripts/flow.py g qa", "IN SESSION") + final(replies["noboard"]))
PY
hook() {  # hook NAME TRANSCRIPT CWD [ACTIVE] [extra json]: run the Stop hook, output in $F/NAME.out
    printf '{"session_id": "%s", "transcript_path": "%s", "cwd": "%s", "hook_event_name": "Stop", "stop_hook_active": %s%s}' \
        "$1" "$F/$2.jsonl" "$3" "${4:-false}" "${5:-}" | (cd "$T" && python3 "$H") > "$F/$1.out"; echo $? > "$F/$1.code"
}
blocked() { grep -q '"decision": "block"' "$F/$1.out"; }
passed() { [ ! -s "$F/$1.out" ] && [ "$(cat "$F/$1.code")" = 0 ]; }

R="$T/repo"
python3 "$H" check "$F/good.txt" > "$F/check-good.out"; cg=$?
check "check passes a reply in the check-in layout" '[ $cg = 0 ] && [ ! -s "$F/check-good.out" ]'
for name in noboard nosection order noheadline twoheadlines emptyneeds; do
    python3 "$H" check "$F/$name.txt" > "$F/check-$name.out"; eval "c_$name=\$?"
done
check "check finds a reply not in the layout" '[ $c_noboard = 1 ] && grep -q "not in the check-in layout" "$F/check-noboard.out"'
check "check names a missing section" 'grep -q "missing section Dependencies" "$F/check-nosection.out"'
check "check finds Coming up not last" 'grep -q "missing section Coming up (or it is out of order)" "$F/check-order.out"'
check "check finds no headline line" 'grep -q "no headline line" "$F/check-noheadline.out"'
check "check finds more than one headline line" 'grep -q "more than one line before the first section" "$F/check-twoheadlines.out"'
check "check finds Needs you with no numbered question" 'grep -q "Needs you has no numbered question" "$F/check-emptyneeds.out"'
python3 "$H" check "$F/nothing.txt" >/dev/null; cno=$?
check "Nothing needs you passes" '[ $cno = 0 ]'
python3 "$H" check "$F/cased.txt" >/dev/null; cc=$?
check "headings ignore case and a count, and Q1. numbers a question" '[ $cc = 0 ]'
python3 "$H" check "$F/fenced.txt" > "$F/check-fenced.out"
check "a heading inside a code fence does not count" 'grep -q "missing section Coming up" "$F/check-fenced.out"'
python3 "$H" check "$F/onefence.txt" >/dev/null; c1=$?
check "a one-line fence does not hide the sections after it" '[ $c1 = 0 ]'
python3 "$H" check "$F/clock.txt" > "$F/check-clock.out"
check "a clock time is not a numbered question" 'grep -q "Needs you has no numbered question" "$F/check-clock.out"'
python3 "$H" check "$F/bold.txt" >/dev/null; cb=$?
check "a Markdown-bold heading with a colon still counts" '[ $cb = 0 ]'
python3 "$H" check "$T/none.txt" > "$F/check-none.out"; cn=$?
check "check refuses an unreadable file with exit 2" '[ $cn = 2 ] && grep -q "^REFUSED: cannot read" "$F/check-none.out"'

hook s-bad op-bad "$R"
check "an operation reply not in the layout is blocked" 'blocked s-bad'
check "the block says what is missing and the layout to use" 'grep -q "REPLY FORMAT (MON-5): it is not in the check-in layout" "$F/s-bad.out" && grep -q "and last, Coming up" "$F/s-bad.out"'
hook s-good op-good "$R"
check "an operation reply in the check-in layout passes" 'passed s-good'
hook s-msg op-bad "$R" false ", \"last_assistant_message\": $(python3 -c 'import json,sys;print(json.dumps(open(sys.argv[1]).read()))' "$F/good.txt")"
check "last_assistant_message is checked when the hook gets it" 'passed s-msg'
hook s-msg2 op-good "$R" false ', "last_assistant_message": "no board here"'
check "last_assistant_message wins over the transcript" 'blocked s-msg2'
hook s-lag op-lag "$R"
check "a transcript whose last entry is not the reply lets the stop through" 'passed s-lag'
hook s-bg op-bg "$R"
check "a background operate launch marks the operation session" 'blocked s-bg'
hook s-refstep op-refused-step "$R"
check "an operation session with a refused goal step is still checked" 'blocked s-refstep'
hook w-wt op-bad "$C/loop/worktrees/wt"
check "a worker session in a goal worktree is never checked" 'passed w-wt'
hook w-main worker-main "$R"
check "a worker session in the main checkout is never checked after a flow step" 'passed w-main'
hook w-refop worker-refused-operate "$R"
check "a refused operate run does not make an operation session" 'passed w-refop'
hook s-mention mention "$R"
check "a command that only mentions operate.py does not count" 'passed s-mention'
hook s-plain plain "$R"
check "a session that never ran operate is not checked" 'passed s-plain'
hook s-other op-bad "$T/other"
check "a session outside this repo is never checked" 'passed s-other'
hook s-bad2 op-bad "$R"
check "the session kind is kept with how far the transcript was read" 'grep -q "\"kind\": \"operation\"" "$C/loop/reply-hook/s-bad2.kind" && grep -q "\"kind\": \"worker\"" "$C/loop/reply-hook/w-main.kind" && grep -q "\"offset\": [1-9]" "$C/loop/reply-hook/s-bad2.kind"'
hook s-board board-only "$R"
check "running board.py board alone does not make an operation session" 'passed s-board'
hook s-flags op-flags "$R"
check "operate run with flags before the script or the subcommand still counts" 'blocked s-flags'
hook s-quoted op-quoted "$R"
check "a refusal quoted inside operate's output still marks the operation session" 'blocked s-quoted'
hook s-timeout op-timeout "$R"
check "an operate run that timed out still marks the operation session" 'blocked s-timeout'
hook s-notop not-op "$R"
check "operate send and compiling flow.py are no signal" 'passed s-notop && grep -q "\"kind\": \"\"" "$C/loop/reply-hook/s-notop.kind"'
hook s-bashc op-bashc "$R"
check "operate run inside bash -c counts" 'blocked s-bashc'
cp "$F/split-1.jsonl" "$F/split.jsonl"; hook s-split split "$R"
cp "$F/split-2.jsonl" "$F/split.jsonl"; hook s-split split "$R"
check "a call whose result lands after a stop is still read at the next stop" 'blocked s-split'
hook s-denied denied "$R"
check "a goal step the user denied does not make a worker" 'blocked s-denied'
hook s-pending op-pending "$R"
check "a last message that still calls a tool is not checked as the reply" 'passed s-pending'
hook s-synth op-synthetic "$R"
check "an API error notice is not checked as a reply" 'passed s-synth'
cp "$F/grow-1.jsonl" "$F/grow.jsonl"; hook s-grow grow "$R"; g1=$(cat "$F/s-grow.out")
cp "$F/grow-2.jsonl" "$F/grow.jsonl"; hook s-grow grow "$R"
check "a later flow step turns an operation session into a worker, reading only the new lines" '[ -n "$g1" ] && passed s-grow && grep -q "\"kind\": \"worker\"" "$C/loop/reply-hook/s-grow.kind"'
printf 'garbage' | (cd "$T" && python3 "$H") > "$F/garbage.out"; gc=$?
check "malformed input lets the stop through silently" '[ $gc = 0 ] && [ ! -s "$F/garbage.out" ]'
hook s-badtx plain "$R" false ', "transcript_path": 5'
check "a broken transcript path fails open" 'passed s-badtx'
hook "../x" op-bad "$R"
check "a session id that is not a plain name is never used in a path" '[ ! -e "$C/loop/x.kind" ] && [ ! -s "$F/../x.out" ]'
hook g1 op-bad "$R" false; hook g1 op-bad "$R" true; c2=$(cat "$C/loop/reply-hook/g1.count" 2>/dev/null); hook g1 op-bad "$R" true
check "the third block in a row lets the reply through and logs it" '[ "$c2" = 2 ] && passed g1 && grep -q "let-through g1 after 2 blocks" "$C/loop/reply-hook/log" && [ ! -e "$C/loop/reply-hook/g1.count" ]'
hook g1 op-bad "$R" false
check "a new turn starts the count again" 'blocked g1 && [ "$(cat "$C/loop/reply-hook/g1.count")" = 1 ]'
LOOP_REPLY_HOOK=0 hook e1 op-bad "$R"
check "LOOP_REPLY_HOOK=0 turns the hook off for one session" 'passed e1'
echo '{"base": "main", "reply_hook": false}' > .loop/config.json
hook off1 op-bad "$R"
check "reply_hook false in the config turns the hook off" 'passed off1'
echo '{"base": "main", "reply_hook": "false"}' > .loop/config.json
hook off2 op-bad "$R"
check "reply_hook written as the string false also turns it off" 'passed off2'
echo '{"base": "main"}' > .loop/config.json

# The installer: merges into the machine-local settings, keeps what is there, ignores the file, and runs again safely.
mkdir -p .claude && echo '{"permissions": {"allow": ["Bash(ls)"]}, "hooks": {"Stop": [{"hooks": [{"type": "command", "command": "echo mine"}]}]}}' > .claude/settings.local.json
python3 "$SETUP" --reply-hook > "$F/i1.out" 2>&1; i1=$?
python3 "$SETUP" --reply-hook > "$F/i2.out" 2>&1
check "setup --reply-hook adds the Stop hook" '[ $i1 = 0 ] && grep -q "^HOOK: added" "$F/i1.out" && grep -q "reply_hook.py" .claude/settings.local.json'
check "setup --reply-hook keeps the other settings and hooks" 'grep -q "Bash(ls)" .claude/settings.local.json && grep -q "echo mine" .claude/settings.local.json'
check "a second setup --reply-hook changes nothing" 'grep -q "^HOOK: already installed" "$F/i2.out" && [ "$(grep -c reply_hook.py .claude/settings.local.json)" = 1 ]'
check "git ignores the machine-local settings file" 'git check-ignore -q .claude/settings.local.json && [ -z "$(git status --porcelain .claude)" ]'
cmd=$(python3 -c "import json;print([h['command'] for g in json.load(open('.claude/settings.local.json'))['hooks']['Stop'] for h in g['hooks'] if 'reply_hook' in h['command']][0])")
printf '{"session_id": "inst", "transcript_path": "%s", "cwd": "%s", "stop_hook_active": false}' "$F/op-bad.jsonl" "$R" | sh -c "$cmd" > "$F/inst.out"
check "the installed command runs the hook" 'grep -q "\"decision\": \"block\"" "$F/inst.out"'
echo '{}' | sh -c "$(echo "$cmd" | sed "s#'[^']*reply_hook.py'#'/gone/reply_hook.py'#g")"; gone=$?
check "a moved hook script lets every stop through" '[ $gone = 0 ]'
python3 - <<'PY'
import json; p = ".claude/settings.local.json"; d = json.load(open(p))
for g in d["hooks"]["Stop"]:
    for h in g["hooks"]:
        h["command"] = h["command"].replace("/scripts/reply_hook.py", "/old/reply_hook.py")
json.dump(d, open(p, "w"))
PY
python3 "$SETUP" --reply-hook > "$F/i3.out" 2>&1
check "an entry with an old path is updated" 'grep -q "^HOOK: updated" "$F/i3.out" && ! grep -q "/old/reply_hook.py" .claude/settings.local.json && [ "$(grep -c reply_hook.py .claude/settings.local.json)" = 1 ]'
(cd "$T" && python3 "$H" status) > "$F/st0.out"; python3 "$H" status > "$F/st.out"
check "status says whether the hook is installed and on" 'grep -q "installed, setting on, script found, let-throughs logged 1" "$F/st.out" && grep -q "off here" "$F/st0.out"'
python3 "$SETUP" --reply-hook --remove > "$F/r1.out" 2>&1; python3 "$SETUP" --reply-hook --remove > "$F/r2.out" 2>&1
check "setup --reply-hook --remove takes out only the hook" 'grep -q "^HOOK: removed" "$F/r1.out" && grep -q "^HOOK: not installed" "$F/r2.out" && ! grep -q reply_hook.py .claude/settings.local.json && grep -q "echo mine" .claude/settings.local.json && grep -q "Bash(ls)" .claude/settings.local.json'
echo '{not json' > .claude/settings.local.json
python3 "$SETUP" --reply-hook > "$F/i4.out" 2>&1; i4=$?
check "invalid settings JSON is refused and left as it was" '[ $i4 = 1 ] && grep -q "^REFUSED: .*not valid JSON" "$F/i4.out" && [ "$(cat .claude/settings.local.json)" = "{not json" ]'
echo '{"hooks": {"Stop": "x"}}' > .claude/settings.local.json
python3 "$SETUP" --reply-hook > "$F/i5.out" 2>&1; i5=$?
check "a hooks shape it can't edit is refused" '[ $i5 = 1 ] && grep -q "^REFUSED: .*shape" "$F/i5.out"'
rm -rf .claude
mkdir -p .claude && echo '{}' > .claude/settings.local.json && git add -f .claude/settings.local.json && git commit -qm tracked
python3 "$SETUP" --reply-hook > "$F/i7.out" 2>&1; i7=$?
check "a committed settings.local.json is refused" '[ $i7 = 1 ] && grep -q "^REFUSED: .*is committed" "$F/i7.out" && [ "$(cat .claude/settings.local.json)" = "{}" ]'
python3 "$SETUP" --reply-hook --remove > "$F/i8.out" 2>&1; i8=$?
check "--remove still works on a committed settings file" '[ $i8 = 0 ] && grep -q "^HOOK: not installed" "$F/i8.out"'
git rm -q --cached .claude/settings.local.json && git commit -qm untrack && rm -rf .claude
python3 "$SETUP" --reply-hook >/dev/null 2>&1; python3 "$SETUP" --reply-hook --remove >/dev/null 2>&1; python3 "$SETUP" --reply-hook >/dev/null 2>&1
check "the ignore line is written once" '[ "$(grep -c "^/.claude/settings.local.json$" "$(git rev-parse --git-path info/exclude)")" = 1 ]'
rm -rf .claude
WT="$C/loop/worktrees/copy"; rm -rf "$WT"; mkdir -p "$WT"; cp -R "$here/skills" "$WT/skills"
python3 "$WT/skills/workflow-setup/scripts/setup.py" --reply-hook > "$F/i6.out" 2>&1; i6=$?
check "setup refuses to install a hook from a goal worktree's copy" '[ $i6 = 1 ] && grep -q "^REFUSED: .*worktree" "$F/i6.out" && [ ! -e .claude/settings.local.json ]'
check "every script stays under 20 KB" '[ $(wc -c < "$H") -lt 20480 ] && [ $(wc -c < "$SETUP") -lt 20480 ]'

[ $fails = 0 ] && echo "ALL PASS" || echo "$fails FAILED"
[ $fails = 0 ]
