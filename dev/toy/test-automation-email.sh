#!/bin/bash
# reads: skills/workflow-health/scripts/ skills/workflow-regression/scripts/regression.py skills/workflow-regression/scripts/actions.py dev/toy/fakegh/ .loop/docs.tsv
# Test the round's mail, feature milestones and round cost with a stub gh, a local Cloudflare stub and a local SMTP stub.
# usage: test-automation-email.sh GROUP   (mail secrets retry mailtest digest rounds file regression upgrade, or all)
# Exits 0 only when every case in the group passes, so each regression row runs one group.
set -u
group=${1:-all}
here=$(cd "$(dirname "$0")/../.." && pwd)
. "$here/dev/toy/reap.sh"
S=$here/skills/workflow-health/scripts
mail="python3 -B $S/mail.py"; auto="python3 -B $S/automation.py"
unset GH_TOKEN GITHUB_TOKEN GITHUB_ACTIONS GITHUB_STEP_SUMMARY DIGEST_RUN DIGEST_MAIL_API DIGEST_SMTP_TEST_PORT MAIL_ADDR_SET MAIL_CF_SET MAIL_SMTP_SET
unset DIGEST_TO DIGEST_FROM CLOUDFLARE_ACCOUNT_ID CLOUDFLARE_EMAIL_TOKEN DIGEST_SMTP_USER DIGEST_SMTP_PASSWORD
pass=0; fail=0
ok() { echo "PASS: $1"; pass=$((pass + 1)); }
bad() { echo "FAIL: $1"; fail=$((fail + 1)); }
want() { [ "$group" = all ] || [ "$group" = "$1" ]; }
ADDR=owner.fixture@example.test; TOKEN=cf-token-fixture-7Q2; SMTPPW=app-password-fixture-9

G=$(mktemp -d); export STUB="$G"; toy_on_exit 'rm -rf "$G"'  # reap.sh stops the stub servers
cat > "$G/gh" <<'PYGH'
#!/usr/bin/env python3
"""A stub gh: logs calls, serves issues, comments, milestones and runs from $STUB, and applies writes to them."""
import json, os, re, sys
d, a = os.environ["STUB"], sys.argv[1:]
open(os.path.join(d, "calls.log"), "a").write(" ".join(a) + "\n")
def load(name, default):
    try:
        return json.load(open(os.path.join(d, name)))
    except (OSError, ValueError):
        return default
def save(name, data):
    json.dump(data, open(os.path.join(d, name), "w"))
def fail(var):
    if os.environ.get(var):
        sys.stderr.write("HTTP 502 for %s\n" % var); sys.exit(1)
def flag(name):
    return a[a.index(name) + 1] if name in a else None
if a[:2] == ["issue", "list"]:
    fail("STUB_LIST_FAIL")
    label = flag("--label")
    print(json.dumps(load(label + ".json", [])))
elif a[:2] == ["issue", "create"]:
    print("https://github.com/o/r/issues/77")
elif a[:2] == ["issue", "comment"]:
    fail("STUB_COMMENT_FAIL")
    c = load("comments.json", [])
    c.append({"id": 900 + len(c), "user": {"login": "github-actions[bot]"}, "body": flag("--body"),
              "created_at": "2026-11-10T12:%02d:00Z" % len(c), "html_url": "https://github.com/o/r/issues/77#c%d" % len(c)})
    save("comments.json", c)
elif a[:2] == ["issue", "edit"]:
    if flag("--body") is not None:
        fail("STUB_EDIT_FAIL")
        open(os.path.join(d, "body-%s.md" % a[2]), "w").write(flag("--body"))
        issues = load("automation.json", [])
        for i in issues:
            if str(i["number"]) == a[2]:
                i["body"] = flag("--body")
        save("automation.json", issues)
elif a[:2] == ["repo", "view"]:
    print("toy-owner")
elif a[0] == "api" and a[1].startswith("users/"):
    print("User")
elif a[0] == "api" and "PATCH" in a and os.environ.get("STUB_ISSUE_PATCH_FAIL") and "/issues/comments/" not in " ".join(a):
    sys.stderr.write("HTTP 502\n"); sys.exit(1)
elif a[0] == "api" and "PATCH" in a and "/issues/comments/" in " ".join(a):
    n = load("patches.json", 0) + 1; save("patches.json", n)
    if str(n) in (os.environ.get("STUB_PATCH_FAIL") or "").split(","):
        sys.stderr.write("HTTP 502\n"); sys.exit(1)
    cid = int(re.search(r"/issues/comments/(\d+)", " ".join(a)).group(1))
    body = next(x[5:] for x in a if x.startswith("body="))
    c = load("comments.json", [])
    for item in c:
        if item["id"] == cid:
            item["body"] = body
    save("comments.json", c)
elif a[0] == "api" and any("/comments" in x for x in a):
    fail("STUB_COMMENTS_FAIL")
    c = load("comments.json", [])
    split = int(os.environ.get("STUB_PAGE", "0") or 0)
    print(json.dumps([c[:split], c[split:]] if split else [c]))
elif a[0] == "api" and any("milestones" in x for x in a):
    print(json.dumps([load("milestones.json", [])]))
elif a[:2] == ["run", "view"]:
    run = load("runs.json", {}).get(a[2])
    if run is None:
        sys.exit(1)
    print(run["createdAt"] if "createdAt" in a else json.dumps({"jobs": run.get("jobs", [])}))
elif a[:2] == ["run", "list"]:
    if not (flag("--limit") or "").isdigit():
        sys.stderr.write("invalid argument for --limit\n"); sys.exit(1)
    wf, after = flag("--workflow"), (flag("--created") or ">=")[2:]
    runs = [dict(r, databaseId=int(k)) for k, r in load("runs.json", {}).items() if r.get("workflow") == wf and r["createdAt"] >= after]
    runs.sort(key=lambda r: r["createdAt"], reverse=True)
    print(json.dumps(runs))
PYGH
chmod +x "$G/gh"; export PATH="$G:$PATH"

cat > "$G/cf.py" <<'PYCF'
"""A local Cloudflare Email Service stub: answers each request with the next status in $STUB/cf_mode (200 when empty)."""
import http.server, json, os, sys
d = sys.argv[1]
class H(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        body = self.rfile.read(int(self.headers.get("Content-Length") or 0))
        with open(os.path.join(d, "cf_requests.log"), "a") as h:
            h.write(json.dumps({"path": self.path, "auth": self.headers.get("Authorization"), "body": json.loads(body)}) + "\n")
        modes = open(os.path.join(d, "cf_mode")).read().split() if os.path.exists(os.path.join(d, "cf_mode")) else []
        code = int(modes.pop(0)) if modes else 200
        open(os.path.join(d, "cf_mode"), "w").write(" ".join(modes))
        to = json.loads(body).get("to", "")
        reply = {"success": True, "errors": [], "result": {"delivered": [to], "permanent_bounces": [], "queued": []}} if code == 200 else \
            {"success": False, "errors": [{"code": {429: 10004, 401: 10101, 503: 10100}.get(code, 10002), "message": "refused for %s" % to.upper()}], "result": None}
        out = json.dumps(reply).encode()
        self.send_response(code); self.send_header("Content-Length", str(len(out))); self.end_headers(); self.wfile.write(out)
    def log_message(self, *args):
        pass
server = http.server.HTTPServer(("127.0.0.1", 0), H)
open(os.path.join(d, "cf_port"), "w").write(str(server.server_address[1]))
server.serve_forever()
PYCF
cat > "$G/smtp.py" <<'PYSMTP'
"""A plain local SMTP stub: logs each message; $STUB/smtp_mode holds RCPT reply codes to give first (e.g. 451)."""
import os, socketserver, sys
d = sys.argv[1]
class H(socketserver.StreamRequestHandler):
    def handle(self):
        self.wfile.write(b"220 toy\r\n"); data, lines = False, []
        for raw in self.rfile:
            line = raw.decode(errors="replace").rstrip("\r\n")
            if data:
                if line == ".":
                    data = False; open(os.path.join(d, "smtp.log"), "a").write("\n".join(lines) + "\n=====\n"); self.wfile.write(b"250 ok\r\n")
                else:
                    lines.append(line)
                continue
            cmd = line[:4].upper()
            if cmd in ("EHLO", "HELO"):
                self.wfile.write(b"250 toy\r\n")
            elif cmd == "RCPT":
                p = os.path.join(d, "smtp_mode"); modes = open(p).read().split() if os.path.exists(p) else []
                code = modes.pop(0) if modes else "250"; open(p, "w").write(" ".join(modes))
                self.wfile.write(("%s rcpt\r\n" % code).encode())
            elif cmd == "DATA":
                data = True; self.wfile.write(b"354 go\r\n")
            elif cmd == "QUIT":
                self.wfile.write(b"221 bye\r\n"); return
            else:
                self.wfile.write(b"250 ok\r\n")
server = socketserver.TCPServer(("127.0.0.1", 0), H)
open(os.path.join(d, "smtp_port"), "w").write(str(server.server_address[1]))
server.serve_forever()
PYSMTP
python3 "$G/cf.py" "$G" & python3 "$G/smtp.py" "$G" &
for _ in $(seq 50); do [ -s "$G/cf_port" ] && [ -s "$G/smtp_port" ] && break; sleep 0.1; done
CF="http://127.0.0.1:$(cat "$G/cf_port")"; SMTPPORT=$(cat "$G/smtp_port")

r=$(mktemp -d); cd "$r" && git init -q && mkdir -p .loop docs/wiki
cfg() { printf '%s\n' "$1" > .loop/config.json; }
cfg '{"digest_mail": "cloudflare"}'
reset() { rm -f "$G"/calls.log "$G"/cf_requests.log "$G"/cf_mode "$G"/patches.json "$G"/smtp.log "$G"/smtp_mode "$G"/body-*.md; : > "$r/sum.md"; }
cf_env() { env DIGEST_TO=$ADDR DIGEST_FROM=digest@mail.example.test CLOUDFLARE_ACCOUNT_ID=acct123 CLOUDFLARE_EMAIL_TOKEN=$TOKEN \
  DIGEST_MAIL_API=$CF DIGEST_MAIL_RETRY_SECONDS=0 GITHUB_STEP_SUMMARY=$r/sum.md GITHUB_REPOSITORY=o/r GH_TOKEN=x "$@"; }
issue() {  # issue BODYMARKER: the bot-authored digest issue
  printf '[{"number": 77, "title": "Automation digest", "author": {"login": "app/github-actions"}, "body": "intro\\n\\n%s"}]\n' "$1" > "$G/automation.json"; }
comment() {  # comment RUN [AUTHOR] [FLAGS] [TIME]: one digest comment
  python3 - "$G/comments.json" "$@" <<'PY'
import json, os, sys
p, run = sys.argv[1], sys.argv[2]
author = sys.argv[3] if len(sys.argv) > 3 and sys.argv[3] else "github-actions[bot]"
flags = sys.argv[4] if len(sys.argv) > 4 else ""
when = sys.argv[5] if len(sys.argv) > 5 else "2026-11-10T12:00:00Z"
c = json.load(open(p)) if os.path.exists(p) else []
body = ("@toy-owner Automation round, 2026-11-10 12:00 UTC\n\n| Routine | Result |\n|---|---|\n| regression | success ([run](https://github.com/o/r/actions/runs/1)) |\n"
        "| health | HEALTH: green |\n\n### Automation\n\n**New** (1): [#12](https://github.com/o/r/issues/12)\n\n**Still open** (0): none\n\n"
        "**Fixed** (1): #5\n\n- [#12](https://github.com/o/r/issues/12): `/workflow-delivery go \"Fix #12\"`\n- [x](javascript:alert(1))\n\n"
        "<!-- automation-digest run=%s open=12:10%s -->\n" % (run, (" " + flags) if flags else ""))
if author != "github-actions[bot]":
    body = body.replace("**New** (1)", "**New** (9) CLICK https://evil.example.test")
c.append({"id": 500 + len(c), "user": {"login": author}, "body": body, "created_at": when, "html_url": "https://github.com/o/r/issues/77#c%d" % len(c)})
json.dump(c, open(p, "w"))
PY
}
runs() { printf '{"201": {"workflow": "health.yml", "createdAt": "2026-11-10T11:47:00Z", "jobs": [{"startedAt": "2026-11-10T11:48:00Z", "completedAt": "2026-11-10T11:55:00Z"}]}}\n' > "$G/runs.json"; }
cfreq() { [ -f "$G/cf_requests.log" ] && wc -l < "$G/cf_requests.log" | tr -d ' ' || echo 0; }
flags_of() { python3 -c "import json,sys; print(json.load(open('$G/comments.json'))[int(sys.argv[1])]['body'].rstrip().splitlines()[-1])" "$1"; }

if want mail; then
  echo "== mail: the round's comment, mailed once"
  reset; rm -f "$G/comments.json"; runs; issue "<!-- automation-digest run=201 open=12:10 -->"; comment 201
  out=$(cf_env DIGEST_RUN=201 $mail send); rc=$?
  python3 - "$G/cf_requests.log" <<'PY' && [ $rc = 0 ] && grep -q "^MAIL: sent for run 201 (MAIL_SENT)" <<<"$out" && flags_of 0 | grep -q " mailed -->" \
    && ok "one mail goes out with the comment's text for this run, and the comment is marked mailed" || bad "send one mail"
import json, sys
req = json.loads(open(sys.argv[1]).readline())
b = req["body"]
assert req["path"] == "/accounts/acct123/email/sending/send" and req["auth"] == "Bearer cf-token-fixture-7Q2"
assert b["subject"] == "Automation digest: 1 new, 0 still open, 1 fixed (o/r)", b["subject"]
assert b["text"].startswith("Automation round, 2026-11-10") and "**New** (1): [#12]" in b["text"] and "automation-digest" not in b["text"]
assert "<h3>Automation</h3>" in b["html"] and '<a href="https://github.com/o/r/issues/12">#12</a>' in b["html"]
for left in ("**", "](", "|---|"):
    assert left not in b["html"], left
assert "<a href=\"javascript" not in b["html"] and "javascript:alert(1)" in b["html"]
PY
  reset; out=$(cf_env DIGEST_RUN=201 $mail send); rc=$?
  [ $rc = 0 ] && grep -q "(MAIL_ALREADY)" <<<"$out" && [ "$(cfreq)" = 0 ] && ok "a rerun after the mail went out sends nothing" || bad "rerun sends twice"
  reset; rm -f "$G/comments.json"; comment 201; comment 201 "someone-else" "" "2026-11-10T12:30:00Z"
  out=$(cf_env DIGEST_RUN=201 $mail send)
  ! grep -q "evil.example.test" "$G/cf_requests.log" && grep -q "(MAIL_SENT)" <<<"$out" && ok "a look-alike comment by another author is never mailed" || bad "look-alike mailed"
  reset; rm -f "$G/comments.json"; comment 201 "" "" "2026-11-10T12:00:00Z"; comment 201 "" "" "2026-11-10T12:20:00Z"
  out=$(cf_env DIGEST_RUN=201 $mail send)
  flags_of 1 | grep -q " mailed -->" && ! flags_of 0 | grep -q "mailed" && ok "the newest of two bot comments for the run is the one mailed" || bad "newest comment"
  reset; rm -f "$G/comments.json"; for i in 1 2 3; do comment 199; done; comment 201
  out=$(STUB_PAGE=3 cf_env DIGEST_RUN=201 $mail send)
  grep -q "(MAIL_SENT)" <<<"$out" && ok "a comment on the second page of results is still found" || bad "paged lookup"
  reset; rm -f "$G/comments.json"; comment 201
  out=$(STUB_PATCH_FAIL=2 cf_env DIGEST_RUN=201 $mail send); rc=$?
  reset; out2=$(cf_env DIGEST_RUN=201 $mail send); rc2=$?
  [ $rc = 1 ] && grep -q "(MAIL_MARKED_LATE)" <<<"$out" && [ $rc2 = 1 ] && grep -q "(MAIL_UNKNOWN)" <<<"$out2" && grep -q "delete the word mailing" <<<"$out2" \
    && [ "$(cfreq)" = 0 ] && ok "a send whose mailed mark fails never sends a second mail on a rerun" || bad "crash after send"
  reset; rm -f "$G/comments.json"; comment 201; echo 401 > "$G/cf_mode"
  out=$(cf_env DIGEST_RUN=201 $mail send); rc=$?
  [ $rc = 1 ] && grep -q "(MAIL_REFUSED)" <<<"$out" && grep -q "Email Sending send permission" <<<"$out" && ! flags_of 0 | grep -q "mail" \
    && [ "$(cfreq)" = 1 ] && ok "a refused send is not retried, writes no mailed and clears the sending mark" || bad "refused send"
  reset; rm -f "$G/comments.json"; comment 201; echo 401 > "$G/cf_mode"
  out=$(STUB_PATCH_FAIL=2 cf_env DIGEST_RUN=201 $mail send); rc=$?
  [ $rc = 1 ] && grep -q "(MAIL_CLEAR_FAILED)" <<<"$out" && ok "a refused send whose sending mark can't be cleared names the edit to make" || bad "clear failed"
  reset; rm -f "$G/comments.json"; comment 201; echo 500 > "$G/cf_mode"
  out=$(cf_env DIGEST_RUN=201 $mail send); rc=$?
  [ $rc = 1 ] && grep -q "(MAIL_UNKNOWN)" <<<"$out" && flags_of 0 | grep -q " mailing -->" && [ "$(cfreq)" = 1 ] \
    && ok "a 500 is not retried and keeps the run marked mailing" || bad "500"
  reset; rm -f "$G/comments.json"; comment 200
  out=$(cf_env DIGEST_RUN=201 $mail send); rc=$?
  [ $rc = 1 ] && grep -q "no digest comment for run 201" <<<"$out" && grep -q "(MAIL_NO_COMMENT)" <<<"$out" && [ "$(cfreq)" = 0 ] \
    && ok "with no digest comment for the run nothing is sent and the step fails" || bad "no comment"
  reset; rm -f "$G/comments.json"; comment 201 "" mailed; comment 202 "" mailed; issue "<!-- automation-digest run=202 open=12:10 -->"
  out=$(cf_env DIGEST_RUN=201 $mail send); rc=$?
  [ $rc = 0 ] && grep -q "(MAIL_STALE)" <<<"$out" && [ "$(cfreq)" = 0 ] && ok "rerunning an old round's job after a newer round sends nothing" || bad "old run rerun"
  reset; rm -f "$G/comments.json"; comment 201; issue "<!-- automation-digest run=200 open=5:0 -->"
  out=$(cf_env DIGEST_RUN=201 $mail send)
  grep -q "run=201 open=12:10 -->" "$G/body-77.md" && ok "a send repairs a body still holding the previous round" || bad "body repair"
  reset; rm -f "$G/comments.json"; comment 201
  out=$(STUB_PATCH_FAIL=1 cf_env DIGEST_RUN=201 $mail send); rc=$?
  [ $rc = 1 ] && grep -q "(MAIL_MARK)" <<<"$out" && [ "$(cfreq)" = 0 ] && ! flags_of 0 | grep -q mail \
    && ok "when the sending mark can't be written nothing is sent and the comment stays unmarked" || bad "mark fails"
  reset; rm -f "$G/comments.json"; comment 201; issue "<!-- automation-digest run=205 open=12:10 -->"
  out=$(cf_env DIGEST_RUN=203 $mail send); rc=$?
  [ $rc = 0 ] && grep -q "(MAIL_STALE)" <<<"$out" && [ "$(cfreq)" = 0 ] && ok "a late rerun of an older round has nothing to mail and stays green" || bad "stale mail"
  out=$(cf_env DIGEST_RUN=201 $mail send); rc=$?
  [ $rc = 0 ] && grep -q "(MAIL_STALE)" <<<"$out" && [ "$(cfreq)" = 0 ] && ok "a rerun of an older round that has its comment mails nothing once a later round posted" || bad "stale with comment"
  issue "<!-- automation-digest run=201 open=12:10 -->"
  reset; rm -f "$G/comments.json"; comment 201; cfg '{"digest_mail": "smtp", "smtp_host": "127.0.0.1"}'
  out=$(env DIGEST_TO=$ADDR DIGEST_FROM=digest@mail.example.test DIGEST_SMTP_USER=u DIGEST_SMTP_PASSWORD=$SMTPPW DIGEST_SMTP_TEST_PORT=$SMTPPORT \
    DIGEST_MAIL_RETRY_SECONDS=0 GH_TOKEN=x GITHUB_REPOSITORY=o/r DIGEST_RUN=201 $mail send); cfg '{"digest_mail": "cloudflare"}'
  grep -q "(MAIL_SENT)" <<<"$out" && grep -q "^Subject: Automation digest: 1 new" "$G/smtp.log" && ok "the SMTP sender sends the same digest" || bad "smtp"
fi

if want secrets; then
  echo "== secrets: only by name, and none of their values anywhere"
  runs; issue "<!-- automation-digest run=201 open=12:10 -->"
  reset; rm -f "$G/comments.json"; comment 201
  out=$(GH_TOKEN=x GITHUB_STEP_SUMMARY=$r/sum.md DIGEST_RUN=201 $mail send); rc=$?
  [ $rc = 0 ] && grep -q "(MAIL_NOT_SET_UP)" <<<"$out" && [ ! -s "$G/calls.log" ] && [ "$(cfreq)" = 0 ] && grep -q "MAIL_NOT_SET_UP" "$r/sum.md" \
    && ok "with no mail secret set the step writes nothing and says what is missing" || bad "not set up"
  reset; out=$(env DIGEST_TO=$ADDR GH_TOKEN=x DIGEST_RUN=201 $mail send); rc=$?
  [ $rc = 1 ] && grep -q "missing secrets DIGEST_FROM, CLOUDFLARE_ACCOUNT_ID, CLOUDFLARE_EMAIL_TOKEN" <<<"$out" && grep -q "(MAIL_SECRETS)" <<<"$out" \
    && [ ! -s "$G/calls.log" ] && ok "with some secrets missing it names them, fails and writes nothing" || bad "partial secrets"
  grep -q "gh secret set DIGEST_FROM; gh secret set CLOUDFLARE_ACCOUNT_ID; gh secret set CLOUDFLARE_EMAIL_TOKEN" <<<"$out" \
    && ok "the Fix line gives one gh secret set per missing secret" || bad "fix commands"
  reset; rm -f "$G/comments.json"; comment 201; echo 401 > "$G/cf_mode"
  out=$(cf_env DIGEST_RUN=201 $mail send 2>&1); cf_env DIGEST_RUN=201 $mail send >/dev/null 2>&1
  shopt -s nullglob; files=("$r/sum.md" "$G/comments.json" "$G"/body-*.md); shopt -u nullglob
  ! grep -qi -e "$ADDR" -e "$TOKEN" -e "owner.fixture" <<<"$out" && ! grep -qi -e "$ADDR" -e "$TOKEN" -e "owner.fixture" "${files[@]}" \
    && grep -q "\*\*\*" <<<"$out" && ok "no secret or address reaches the log, the summary, the comment or the issue body" || bad "leak"
  reset; out=$(cf_env DIGEST_MAIL_API=https://attacker.example.test DIGEST_RUN=201 $mail send); rc=$?
  [ $rc = 1 ] && grep -q "(MAIL_TEST_URL)" <<<"$out" && grep -q "https://attacker.example.test" <<<"$out" && [ "$(cfreq)" = 0 ] \
    && ok "a non-local DIGEST_MAIL_API is refused before anything is sent" || bad "test url"
  ! grep -rq -e DIGEST_MAIL_API -e DIGEST_SMTP_TEST_PORT "$here/.github/workflows" "$S/workflows.py" \
    && ! grep -E " (DIGEST_TO|DIGEST_FROM|CLOUDFLARE_ACCOUNT_ID|CLOUDFLARE_EMAIL_TOKEN|DIGEST_SMTP_USER|DIGEST_SMTP_PASSWORD):" "$here/.github/workflows/health.yml" "$here/.github/workflows/mail-test.yml" | grep -v '\${{ secrets\.' | grep -q . \
    && ok "the workflows hold the mail secrets only as secrets, and never set a test override" || bad "workflow secrets"
  bads=0; for c in '{"digest_mail": "pigeon"}' '{"digest_mail": "smtp", "smtp_port": 25}'; do
    cfg "$c"; out=$(cf_env DIGEST_RUN=201 $mail send); [ $? = 1 ] && grep -q "(MAIL_SETTING)" <<<"$out" || bads=1; done
  cfg '{"digest_mail": "cloudflare"}'; out=$(cf_env DIGEST_MAIL_RETRY_SECONDS=99 DIGEST_RUN=201 $mail send); grep -q "(MAIL_SETTING)" <<<"$out" || bads=1
  [ $bads = 0 ] && ok "a bad digest_mail, smtp_port or retry wait is refused before any work" || bad "settings"
  out=$(cd "$S" && cf_env python3 -B -c "
import sys, rounds, mail
rounds.digest_issue = lambda: (_ for _ in ()).throw(RuntimeError('boom at $ADDR'))
sys.argv = ['mail.py', 'send', '--root', '$r']; import os; os.environ['DIGEST_RUN'] = '201'
sys.exit(mail.main())" 2>&1); rc=$?
  [ $rc = 1 ] && grep -q "(MAIL_FAILED)" <<<"$out" && grep -q "mail.py:[0-9]* in cmd_send" <<<"$out" && ! grep -q "Traceback" <<<"$out" && ! grep -qi "$ADDR" <<<"$out" \
    && ok "an unexpected error prints one scrubbed line with its frame, never a traceback" || bad "crash line"
  for code in $(grep -o '"MAIL_[A-Z_]*"' "$S/mail.py" | tr -d '"' | sort -u); do grep -q "$code" "$here/docs/wiki/Automation.md" || { bads=2; echo "missing $code"; }; done
  [ "$bads" != 2 ] && ok "every MAIL code is in the wiki's troubleshooting table" || bad "codes documented"
fi

if want retry; then
  echo "== retry: once, and only when the provider can't have accepted the mail"
  runs; issue "<!-- automation-digest run=201 open=12:10 -->"
  reset; rm -f "$G/comments.json"; comment 201; echo 429 > "$G/cf_mode"
  out=$(cf_env DIGEST_RUN=201 $mail send); rc=$?
  [ $rc = 0 ] && grep -q "sent for run 201 (after 1 retry) (MAIL_SENT)" <<<"$out" && [ "$(cfreq)" = 2 ] && ok "a 429 is retried once and the mail goes out once" || bad "429 retry"
  reset; rm -f "$G/comments.json"; comment 201; echo "429 429" > "$G/cf_mode"
  out=$(cf_env DIGEST_RUN=201 $mail send); rc=$?
  [ $rc = 1 ] && [ "$(cfreq)" = 2 ] && grep -q "(MAIL_REFUSED)" <<<"$out" && ok "a second 429 gives up after one retry" || bad "retry bound"
  reset; rm -f "$G/comments.json"; comment 201; cfg '{"digest_mail": "smtp", "smtp_host": "127.0.0.1"}'; echo 451 > "$G/smtp_mode"
  out=$(env DIGEST_TO=$ADDR DIGEST_FROM=d@mail.example.test DIGEST_SMTP_USER=u DIGEST_SMTP_PASSWORD=$SMTPPW DIGEST_SMTP_TEST_PORT=$SMTPPORT \
    DIGEST_MAIL_RETRY_SECONDS=0 GH_TOKEN=x DIGEST_RUN=201 $mail send); cfg '{"digest_mail": "cloudflare"}'
  grep -q "(after 1 retry) (MAIL_SENT)" <<<"$out" && [ "$(grep -c '^=====' "$G/smtp.log")" = 1 ] && ok "an SMTP 4xx before DATA is retried once" || bad "smtp retry"
  out=$(cd "$S" && python3 -B -c "
import smtplib, mail
calls = []
import ssl
class Fake:
    def __init__(self, host, port, timeout=None, context=None):
        calls.append(('open', type(self).__name__, port)); self.ctx = context
        if context is not None: calls.append('verified' if context.verify_mode == ssl.CERT_REQUIRED and context.check_hostname else 'unverified')
    def __enter__(self): return self
    def __exit__(self, *a): pass
    def starttls(self, context=None): calls.append('starttls ' + ('verified' if context is not None and context.verify_mode == ssl.CERT_REQUIRED else 'unverified'))
    def login(self, u, p): calls.append('login')
    def send_message(self, m): calls.append('send')
class SSL(Fake): pass
class Plain(Fake): pass
smtplib.SMTP_SSL, smtplib.SMTP = SSL, Plain
keys = {'DIGEST_TO': 'a@b.test', 'DIGEST_FROM': 'c@d.test', 'DIGEST_SMTP_USER': 'u', 'DIGEST_SMTP_PASSWORD': 'p'}
mail.send_smtp(keys, 's', 't', '<p>t</p>', 'smtp.example.test', 465); print(calls); calls.clear()
mail.send_smtp(keys, 's', 't', '<p>t</p>', 'smtp.example.test', 587); print(calls)")
  head -1 <<<"$out" | grep -q "('open', 'SSL', 465), 'verified', 'login', 'send'" && tail -1 <<<"$out" | grep -q "('open', 'Plain', 587), 'starttls verified', 'login', 'send'" \
    && ok "port 465 uses TLS from the start and 587 calls STARTTLS before login, both verifying the server's certificate" || bad "tls choice"
  out=$(cd "$S" && python3 -B -c "
import smtplib, ssl, socket, io, json, urllib.request, urllib.error, mail
class Quit:
    def __init__(self, *a, **k): pass
    def __enter__(self): return self
    def __exit__(self, *a): raise smtplib.SMTPServerDisconnected('gone at QUIT')
    def starttls(self, context=None): pass
    def login(self, u, p): pass
    def send_message(self, m): pass
smtplib.SMTP = Quit
keys = {'DIGEST_TO': 'a@b.test', 'DIGEST_FROM': 'c@d.test', 'DIGEST_SMTP_USER': 'u', 'DIGEST_SMTP_PASSWORD': 'p',
        'CLOUDFLARE_ACCOUNT_ID': 'x', 'CLOUDFLARE_EMAIL_TOKEN': 't'}
print('quit', mail.send_smtp(keys, 's', 't', '<p/>', 'smtp.example.test', 587)[0])
def answer(fn):
    urllib.request.urlopen = fn
    return mail.send_cloudflare(keys, 's', 't', '<p/>', 'https://api.example.test')[0]
def tls(*a, **k): raise urllib.error.URLError(ssl.SSLError('bad cert'))
def slow(*a, **k): raise socket.timeout('timed out')
class Reply(io.BytesIO):
    def __enter__(self): return self
    def __exit__(self, *a): pass
def bounce(*a, **k): return Reply(json.dumps({'success': True, 'result': {'permanent_bounces': ['a@b.test']}}).encode())
print('tls', answer(tls)); print('timeout', answer(slow)); print('bounce', answer(bounce))
")
  grep -q "^quit ok$" <<<"$out" && ok "an SMTP error at QUIT after the server took the message counts as sent" || bad "smtp quit"
  grep -q "^tls refused$" <<<"$out" && grep -q "^timeout unknown$" <<<"$out" && grep -q "^bounce refused$" <<<"$out" \
    && ok "Cloudflare: a TLS failure is refused, a timeout after sending is unknown, a permanent bounce is refused" || bad "cloudflare outcomes"
  cfg '{"digest_mail": "cloudflare", "smtp_port": 25}'; out=$(cd "$S" && python3 -B -c "import mail; print(mail.settings('$r')[0])" 2>&1)
  cfg '{"digest_mail": "smtp", "smtp_port": "587"}'; out2=$(cd "$S" && python3 -B -c "import mail; print(mail.settings('$r')[2])" 2>&1); cfg '{"digest_mail": "cloudflare"}'
  [ "$out" = cloudflare ] && [ "$out2" = 587 ] && ok "smtp_port is checked only when smtp sends, and a quoted port is read as a number" || bad "smtp settings"
fi

if want mailtest; then
  echo "== mail test: one fixed mail, by hand only"
  reset; out=$(cf_env $mail test); rc=$?
  [ $rc = 0 ] && grep -q "test sent (MAIL_SENT)" <<<"$out" && [ "$(cfreq)" = 1 ] && [ ! -s "$G/calls.log" ] \
    && grep -q '"subject": "Automation digest: test from o/r"' "$G/cf_requests.log" && ok "the Mail test sends one mail and touches no issue" || bad "mail test"
  reset; out=$(env DIGEST_TO=$ADDR $mail test); rc=$?
  [ $rc = 1 ] && grep -q "test not sent: missing secrets" <<<"$out" && ok "a Mail test with a missing secret fails and names it" || bad "test missing"
  reset; out=$(env $mail test); rc=$?
  [ $rc = 1 ] && grep -q "(MAIL_SECRETS)" <<<"$out" && ok "a Mail test with no secret at all fails instead of passing green" || bad "test none"
  cfg '{"digest_mail": "off"}'; out=$(cf_env $mail test); rc=$?; cfg '{"digest_mail": "cloudflare"}'
  [ $rc = 1 ] && grep -q "(MAIL_OFF)" <<<"$out" && [ "$(cfreq)" = 0 ] && ok "a Mail test with digest_mail off fails and says why" || bad "test off"
  W=$here/.github/workflows/mail-test.yml
  grep -q "^  workflow_dispatch:" "$W" && ! grep -q "schedule:" "$W" && ! grep -q "issues: write" "$W" && grep -q "contents: read" "$W" \
    && diff -q <(cd "$S" && python3 -B -c "import workflows; print(workflows.mail_test(), end='')") "$W" >/dev/null \
    && ok "mail-test.yml is dispatch-only, read-only, and equals what automation.py writes" || bad "mail-test workflow"
fi

if want digest; then
  echo "== digest: grouped by milestone, never posted twice or out of order"
  printf '[{"number": 10, "title": "Automation"}, {"number": 2, "title": "Backlog"}, {"number": 11, "title": "Ops, team: A"}]\n' > "$G/milestones.json"
  printf '[{"number": 12, "url": "https://github.com/o/r/issues/12", "milestone": {"number": 10}}, {"number": 14, "url": "https://github.com/o/r/issues/14", "milestone": {"number": 11}}]\n' > "$G/regression.json"
  printf '[{"number": 9, "url": "https://github.com/o/r/issues/9", "milestone": null}]\n' > "$G/health.json"
  dg() { env GH_TOKEN=x GITHUB_ACTIONS=true DIGEST_REPO_OWNER=toy-owner GITHUB_STEP_SUMMARY=$r/sum.md "$@" $auto digest; }
  reset; rm -f "$G/comments.json"; runs; issue "<!-- automation-digest open=5,9 run=200 -->"
  out=$(dg DIGEST_RUN=201); c=$(python3 -c "import json;print(json.load(open('$G/comments.json'))[-1]['body'])")
  python3 - "$c" <<'PY' && grep -q "run=201 open=9:0,12:10,14:11 -->" "$G/body-77.md" && ok "the digest groups new, still-open and fixed issues by milestone, features first" || bad "grouping"
import sys
c = sys.argv[1]
heads = [l for l in c.splitlines() if l.startswith("### ")]
assert heads == ["### Automation", "### Ops, team: A", "### No milestone"], heads
auto = c.split("### Automation")[1].split("###")[0]
assert "**New** (1): [#12]" in auto and '- [#12](https://github.com/o/r/issues/12): `/workflow-delivery go "Fix #12"`' in auto
nom = c.split("### No milestone")[1]
assert "**Still open** (1): [#9]" in nom and "**Fixed** (1): #5" in nom
assert c.count("Ops, team: A") == 1
PY
  grep -qF "| round cost | round 7 min of job time (regression: no run found, health 7 min so far" <<<"$c" && grep -q "^## Round" "$r/sum.md" \
    && ok "the digest shows the round's cost and writes it to the run summary" || bad "cost row"
  reset; issue "<!-- automation-digest open=12:10 run=205 -->"; n=$(python3 -c "import json;print(len(json.load(open('$G/comments.json'))))")
  out=$(dg DIGEST_RUN=201)
  grep -q "(DIGEST_STALE)" <<<"$out" && [ "$n" = "$(python3 -c "import json;print(len(json.load(open('$G/comments.json'))))")" ] && [ ! -f "$G/body-77.md" ] \
    && ok "an older run never posts or rewinds the issue's state" || bad "stale"
  reset; rm -f "$G/comments.json"; comment 203; issue "<!-- automation-digest run=202 open=5:0 -->"
  out=$(dg DIGEST_RUN=203)
  grep -q "(DIGEST_REPAIRED)" <<<"$out" && [ "$(python3 -c "import json;print(len(json.load(open('$G/comments.json'))))")" = 1 ] && grep -q "run=203 open=12:10" "$G/body-77.md" \
    && ok "a rerun after a failed state save repairs the state from its comment, posting nothing" || bad "repair"
  reset; rm -f "$G/comments.json"; comment 202 "" mailed; issue "<!-- automation-digest run=202 open=12:10 -->"
  out=$(dg DIGEST_RUN=204 MAIL_ADDR_SET=true MAIL_CF_SET=true MAIL_SMTP_SET=false); c=$(python3 -c "import json;print(json.load(open('$G/comments.json'))[-1]['body'])")
  grep -qF "| email | previous round: sent |" <<<"$c" && ok "the email row shows the previous round's mail" || bad "email sent row"
  reset; rm -f "$G/comments.json"; comment 202 "" mailing; issue "<!-- automation-digest run=202 open=12:10 -->"
  out=$(dg DIGEST_RUN=204 MAIL_ADDR_SET=true MAIL_CF_SET=false MAIL_SMTP_SET=false); c=$(python3 -c "import json;print(json.load(open('$G/comments.json'))[-1]['body'])")
  grep -qF "| email | not set up (add the DIGEST_TO, DIGEST_FROM, CLOUDFLARE_ACCOUNT_ID, CLOUDFLARE_EMAIL_TOKEN secrets) |" <<<"$c" \
    && ok "the email row says which secrets the chosen sender still needs" || bad "email not set up row"
  reset; rm -f "$G/comments.json"; comment 202 "" mailing; issue "<!-- automation-digest run=202 open=12:10 -->"
  out=$(dg DIGEST_RUN=204 MAIL_ADDR_SET=true MAIL_CF_SET=true MAIL_SMTP_SET=false); c=$(python3 -c "import json;print(json.load(open('$G/comments.json'))[-1]['body'])")
  grep -qF "| email | previous round: may have been sent |" <<<"$c" && ok "the email row flags a round whose mail may have been sent" || bad "email unknown row"
  cfg '{"digest_mail": "off"}'; reset; issue "<!-- automation-digest run=204 open=12:10 -->"
  out=$(dg DIGEST_RUN=206 MAIL_ADDR_SET=false); c=$(python3 -c "import json;print(json.load(open('$G/comments.json'))[-1]['body'])"); cfg '{"digest_mail": "cloudflare"}'
  grep -qF "| email | off (digest_mail in .loop/config.json) |" <<<"$c" && ok "with mail off and no secrets the email row says off, not missing" || bad "email off row"
  reset; rm -f "$G/comments.json"; issue "<!-- automation-digest run=206 open=12:10 -->"
  out=$(env GH_TOKEN=x DIGEST_REPO_OWNER=toy-owner $auto digest); c=$(python3 -c "import json;print(json.load(open('$G/comments.json'))[-1]['body'])")
  grep -q "run=206 open=" "$G/body-77.md" && grep -q "run=local open=" <<<"$c" && grep -qF "| round cost | not read (only read in Actions) (ROUND_UNREAD) |" <<<"$c" \
    && ok "a digest run by hand keeps the last Actions run on the issue and says the cost is only read in Actions" || bad "local digest"
  python3 -B -c "
import sys; sys.path.insert(0, '$S'); import automation, mail_render
c, _ = automation.compose('', '', [], {3: ('u3', 99), 4: ('u4', 0), 5: ('u5', 10)}, {}, '7', {10: 'Automation'})
heads = [l for l in c.splitlines() if l.startswith('### ')]
assert heads == ['### Automation', '### No milestone'], heads
assert '**New** (2): [#3](u3), [#4](u4)' in c.split('### No milestone')[1]
c, _ = automation.compose('', '', [('health', 'a | b')], {}, {}, '7', {})
page = mail_render.to_html(c)
assert '<td>a | b</td>' in page, page
" && ok "an unknown milestone joins the one No milestone section, and an escaped pipe stays in its cell" || bad "no milestone section"
  python3 -B -c "
import sys; sys.path.insert(0, '$S'); import rounds
a = rounds.parse('x <!-- automation-digest open=5,9 run=7 -->'); b = rounds.parse('<!-- automation-digest mailed open=5:2 run=8 -->')
c = rounds.parse('<!-- automation-digest open= run=none -->'); d = rounds.parse('<!-- automation-digest run=1; open=1 -->')
assert a['open'] == {5: 0, 9: 0} and a['run'] == '7' and b['flags'] == {'mailed'} and b['open'] == {5: 2} and c['open'] == {} and d is None
assert rounds.parse(rounds.marker('9', {3: 11}, {'mailing'})) == {'run': '9', 'open': {3: 11}, 'flags': {'mailing'}}
" && ok "the state marker reads the old form, any key order and an empty open list, and refuses a malformed one" || bad "marker grammar"
fi

if want rounds; then
  echo "== rounds: job time, spend and the 45-minute flag"
  printf '%s\n' '{"300": {"workflow": "health.yml", "createdAt": "2026-11-10T12:47:00Z", "jobs": [{"startedAt": "2026-11-10T12:48:00Z", "completedAt": "2026-11-10T12:58:10Z"}]},
 "299": {"workflow": "regression.yml", "createdAt": "2026-11-10T12:17:00Z", "status": "completed", "url": "u299", "jobs": [{"startedAt": "2026-11-10T12:18:00Z", "completedAt": "2026-11-10T12:58:30Z"}]},
 "298": {"workflow": "regression.yml", "createdAt": "2026-11-10T10:00:00Z", "status": "completed", "jobs": [{"startedAt": "2026-11-10T10:01:00Z", "completedAt": "2026-11-10T10:02:01Z"}]},
 "250": {"workflow": "health.yml", "createdAt": "2026-11-10T08:47:00Z", "jobs": [{"startedAt": "2026-11-10T08:48:00Z", "completedAt": "2026-11-10T08:55:00Z"}]}}' > "$G/runs.json"
  rc() { python3 -B -c "
import sys, datetime; sys.path.insert(0, '$S'); import rounds
now = datetime.datetime(2026, 11, 10, 13, 0, tzinfo=datetime.timezone.utc)
c = rounds.round_cost('$1', '$2' or None, now); print(rounds.line(c)); print(c.get('seconds'), c.get('minutes'), c.get('over'), c.get('first'))"; }
  out=$(rc 300 250)
  head -1 <<<"$out" | grep -q "^OVER 45 min: slow a routine down or turn it off. round 51 min of job time (regression 40 min, health 10 min so far" \
    && tail -1 <<<"$out" | grep -q "^3040 54 True False$" && ok "job time sums the round's runs and a round over 45 minutes is flagged" || bad "sum and flag"
  head -1 <<<"$out" | grep -q "54 Actions minutes of runs started since the last round" && ok "the spend counts every run started since the last round, minutes rounded up per job" || bad "spend"
  out=$(rc 300 "")
  tail -1 <<<"$out" | grep -q " 52 True True$" && grep -q "(first round counted)" <<<"$out" && ok "with no previous round the spend is the round's own two runs" || bad "first round"
  python3 - "$G/runs.json" <<'PY'
import json, sys
d = json.load(open(sys.argv[1])); d["299"]["status"] = "in_progress"; d["299"]["jobs"][0]["completedAt"] = None
json.dump(d, open(sys.argv[1], "w"))
PY
  out=$(rc 300 250); grep -q "regression still running, partial 42 min" <<<"$out" && ok "a regression run still going is counted as partial" || bad "partial"
  grep -q "^run list --workflow regression.yml --limit 200 --json databaseId,createdAt,status,url --created >=" "$G/calls.log" \
    && ok "the spend lists runs since the last round with a well-formed gh run list" || bad "run list args"
  python3 - "$G/runs.json" <<'PY'
import json, sys
d = json.load(open(sys.argv[1])); d["299"]["jobs"][0]["completedAt"] = "0001-01-01T00:00:00Z"; json.dump(d, open(sys.argv[1], "w"))
PY
  out=$(rc 300 250); grep -q "regression still running, partial 42 min" <<<"$out" && ok "gh's year-1 completedAt for an unfinished job counts to now, not as negative time" || bad "zero time"
  python3 - "$G/runs.json" <<'PY'
import json, sys
d = json.load(open(sys.argv[1])); del d["299"]; json.dump(d, open(sys.argv[1], "w"))
PY
  out=$(rc 300 250); grep -q "^round 11 min of job time (regression 1 min" <<<"$out" && ok "a by-hand or tag regression run inside the window is the round's run" || bad "other run"
  python3 - "$G/runs.json" <<'PY'
import json, sys
d = json.load(open(sys.argv[1])); del d["298"]; json.dump(d, open(sys.argv[1], "w"))
PY
  out=$(rc 300 250); grep -q "regression: no run found" <<<"$out" && ok "with no regression run in the window the round is health only" || bad "no regression"
  out=$(rc local ""); grep -q "^not read (no run id) (ROUND_UNREAD)" <<<"$out" && ok "outside Actions the cost says why it wasn't read" || bad "unread"
fi

if want file; then
  echo "== file: findings on their feature's milestone, and the owner's moves stay"
  export FAKE_GH_DIR="$G/fake"; mkdir -p "$FAKE_GH_DIR"; F=$here/dev/toy/fakegh
  printf 'Automation\tskills/workflow-health/scripts/automation.py,.github/workflows\nHealth\tskills/workflow-health\nOld\tskills/old\n' > .loop/docs.tsv
  printf '[{"number": 1, "title": "Backlog", "state": "open"}, {"number": 2, "title": "Automation", "state": "open"}, {"number": 3, "title": "Old", "state": "closed"}]\n' > "$FAKE_GH_DIR/milestones.json"
  fl() { (cd "$S" && PATH="$F:$PATH" python3 -B -c "
import json, sys, file
rows = [dict(state='WARN', family='size', subject=s, rule='limit', detail='big', fix='') for s in sys.argv[1:]]
issues, why = file.held('$r'); acts = file.plan(rows, issues, ['size'], root='$r'); file.apply(acts, '$r', ['size'])" "$@"); }
  : > "$FAKE_GH_DIR/issues.json"; rm -f "$FAKE_GH_DIR/calls.log"
  out=$(fl skills/workflow-health/scripts/automation.py skills/nowhere/x.py)
  python3 - "$FAKE_GH_DIR/issues.json" <<'PY' && ok "a finding goes on its feature's milestone, and one no feature claims goes on Backlog" || bad "placement"
import json, sys
i = {x["title"].split()[2]: x for x in json.load(open(sys.argv[1]))}
assert i["skills/workflow-health/scripts/automation.py"]["milestone"]["title"] == "Automation"
assert i["skills/nowhere/x.py"]["milestone"]["title"] == "Backlog"
assert "placed=Automation -->" in i["skills/workflow-health/scripts/automation.py"]["body"]
PY
  out=$(fl skills/workflow-health/scripts/automation.py skills/nowhere/x.py)
  [ "$(python3 -c "import json;print(len(json.load(open('$FAKE_GH_DIR/issues.json'))))")" = 2 ] && grep -q "^SAME" <<<"$out" && ok "a second run duplicates no open issue" || bad "duplicate"
  python3 - "$FAKE_GH_DIR/issues.json" <<'PY'
import json, sys
d = json.load(open(sys.argv[1]))
for x in d:
    if "automation.py" in x["title"]:
        x["milestone"] = {"title": "Backlog"}  # the owner moved it to Backlog
d.append({"number": 3, "title": "health: size skills/old/y.py limit", "state": "OPEN", "labels": [{"name": "health"}, {"name": "health:size"}],
          "milestone": {"title": "Backlog"}, "body": "<!-- loop-health size:.github/workflows/x.yml:limit -->\n\nold"})
json.dump(d, open(sys.argv[1], "w"))
PY
  out=$(fl skills/workflow-health/scripts/automation.py .github/workflows/x.yml)
  python3 - "$FAKE_GH_DIR/issues.json" <<'PY' && ok "an issue the owner moved to Backlog stays there, and an older Backlog issue moves to its feature" || bad "owner move"
import json, sys
i = {x["number"]: x for x in json.load(open(sys.argv[1]))}
assert i[1]["milestone"]["title"] == "Backlog", i[1]
assert i[3]["milestone"]["title"] == "Automation", i[3]
PY
  out=$(fl skills/old/z.py)
  grep -q "^api -X PATCH repos/{owner}/{repo}/issues/4 -F milestone=3" "$FAKE_GH_DIR/calls.log" && ok "a finding for a feature whose milestone is closed is set on it by number" || bad "closed milestone"
  (cd "$S" && PATH="$F:$PATH" python3 -B -c "
import file, subprocess
real, seen = file.run, []
def run(args, root):
    seen.append(args)
    if args[:3] == ['api', '-X', 'PATCH']:
        return subprocess.CompletedProcess(args, 1, '', 'HTTP 502')
    return real(args, root)
file.run = run
row = dict(state='WARN', family='size', subject='skills/old/w.py', rule='limit', detail='big', fix='')
issues, why = file.held('$r'); acts = file.plan([row], issues, ['size'], root='$r'); file.apply(acts, '$r', ['size'])
print([a for a in seen if a[:2] == ['issue', 'edit']])
" ) > "$G/patch.out" 2>&1
  grep -q "placed= -->" "$G/patch.out" && grep -q "^FAILED open issue" "$G/patch.out" \
    && ok "a new issue whose closed-milestone set fails gets placed= empty, so the next run places it" || bad "closed patch failure"
  python3 -c "import json; d=json.load(open('$FAKE_GH_DIR/milestones.json')); json.dump([m for m in d if m['title'] != 'Backlog'], open('$FAKE_GH_DIR/milestones.json', 'w'))"
  out=$(fl skills/nowhere/v.py)
  python3 - "$FAKE_GH_DIR/issues.json" "$FAKE_GH_DIR/milestones.json" <<'PY2' && ok "a missing Backlog is made once for a finding no feature claims" || bad "backlog made"
import json, sys
i = [x for x in json.load(open(sys.argv[1])) if "nowhere/v.py" in x["title"]]
assert len(i) == 1 and i[0]["milestone"]["title"] == "Backlog" and "placed=Backlog -->" in i[0]["body"], i
assert [m["title"] for m in json.load(open(sys.argv[2]))].count("Backlog") == 1
PY2
  python3 - "$FAKE_GH_DIR/issues.json" <<'PY2'
import json, sys
d = json.load(open(sys.argv[1]))
d.append({"number": 9, "title": "health: size .github/workflows/q.yml limit", "state": "OPEN", "labels": [{"name": "health"}, {"name": "health:size"}],
          "milestone": {"title": "Old"}, "body": "<!-- loop-health size:.github/workflows/q.yml:limit placed=Automation -->\n\nq"})
d.append({"number": 10, "title": "health: size .github/workflows/r.yml limit", "state": "OPEN", "labels": [{"name": "health"}, {"name": "health:size"}],
          "milestone": None, "body": "<!-- loop-health size:.github/workflows/r.yml:limit placed=Automation -->\n\nr"})
json.dump(d, open(sys.argv[1], "w"))
PY2
  out=$(fl .github/workflows/q.yml .github/workflows/r.yml)
  python3 - "$FAKE_GH_DIR/issues.json" <<'PY2' && ok "an issue the owner moved to another milestone, or off every milestone, stays where it is" || bad "owner moved elsewhere"
import json, sys
i = {x["number"]: x for x in json.load(open(sys.argv[1]))}
assert i[9]["milestone"]["title"] == "Old" and i[10]["milestone"] is None, (i[9]["milestone"], i[10]["milestone"])
assert "placed=Automation -->" in i[9]["body"] and "placed=Automation -->" in i[10]["body"]
PY2
  (cd "$S" && PATH="$F:$PATH" python3 -B -c "
import file, subprocess
real, seen = file.run, []
def run(args, root):
    seen.append(args)
    if args[:2] == ['issue', 'edit'] and '--milestone' in args:
        return subprocess.CompletedProcess(args, 1, '', 'HTTP 502')
    return real(args, root)
file.run = run
held = 'size:skills/workflow-health/scripts/automation.py:limit'
issues = {held: dict(number=11, state='OPEN', labels=[{'name': 'health:size'}], milestone={'title': 'Backlog'}, placed='Backlog', body='old')}
row = dict(state='WARN', family='size', subject='skills/workflow-health/scripts/automation.py', rule='limit', detail='big', fix='')
acts = file.plan([row], issues, ['size'], root='$r'); file.apply(acts, '$r', ['size'])
bodies = [a[a.index('--body') + 1] for a in seen if a[:3] == ['issue', 'edit', '11'] and '--body' in a]
print([a['kind'] for a in acts]); print(bodies)
" ) > "$G/keep.out" 2>&1
  grep -q "'move'" "$G/keep.out" && grep -q "placed=Backlog -->" "$G/keep.out" && ! grep -q "placed=Automation -->" "$G/keep.out" \
    && ok "a move that fails leaves the old placed= so the next run tries again" || bad "move failure placement"
  python3 -B -c "
import sys; sys.path.insert(0, '$S'); import milestone
assert milestone.page_of('$here', 'skills/workflow-health/scripts/mail.py') == 'Automation'
assert milestone.page_of('$here', 'skills/workflow-health/scripts/health.py') == 'Health'
assert milestone.page_of('$here', 'nowhere.txt') == ''" && ok "mail.py maps to Automation and health.py to Health (longest path wins)" || bad "page_of"
  (cd "$S" && PATH="$F:$PATH" python3 -B -c "
import file, subprocess
real = file.run
def run(args, root):
    if args[:2] == ['api', '--paginate'] and any('milestones' in a for a in args):
        return subprocess.CompletedProcess(args, 1, '', 'HTTP 502')
    return real(args, root)
file.run = run
held = 'size:skills/workflow-health/scripts/automation.py:limit'
issues = {held: dict(number=12, state='OPEN', labels=[{'name': 'health:size'}], milestone={'title': 'Automation'}, placed='Automation', body='x')}
row = dict(state='WARN', family='size', subject='skills/workflow-health/scripts/automation.py', rule='limit', detail='big', fix='')
new = dict(row, subject='skills/workflow-health/scripts/rounds.py')
acts = file.plan([row, new], issues, ['size'], root='$r')
print(sorted((a['kind'], a.get('milestone')) for a in acts))
" ) > "$G/blind.out" 2>&1
  grep -q "('open', 'Health'), ('update', 'Automation')" "$G/blind.out" && ! grep -q "'move'" "$G/blind.out" && ! grep -q "Backlog" "$G/blind.out" \
    && ok "when milestones can't be read a finding keeps its feature and no issue is moved" || bad "health blind"
  rm -f .loop/docs.tsv; unset FAKE_GH_DIR
fi

if want regression; then
  echo "== regression: defect issues on their feature's milestone"
  step() { python3 - "$1" "$2" "$3" <<'PY'
import sys
text, name, out = open(sys.argv[1]).read(), sys.argv[2], sys.argv[3]
block = text.split("- name: " + name, 1)[1].split("run: |\n", 1)[1]
lines = []
for line in block.split("\n"):
    if line.strip() and not line.startswith("          "):
        break
    lines.append(line[10:])
open(out, "w").write("\n".join(lines).rstrip() + "\n")
PY
  }
  cfg '{}'; printf 'Alpha\tsrc/alpha\n' > .loop/docs.tsv
  printf '# Alpha\n\n## Requirements\n\n- AAA-1: **Reviewed 2026-11-08** Alpha words.\n' > docs/wiki/Alpha.md
  printf '# Beta\n\n## Requirements\n\n- BBB-1: **Reviewed 2026-11-08** Beta words.\n' > docs/wiki/Beta.md
  printf '# id\tlevel\tcommand\tgoal\tseen_red\tdescription\tcategory\tlink\nred\tland\tfalse\tAAA-1\t2026-01-01\tGiven a, when b, then c.\tcriterion\t\nblue\tland\tfalse\tBBB-1\t2026-01-01\tGiven d, when e, then f.\tcriterion\t\n' > .loop/regression.tsv
  python3 -B "$here/skills/workflow-regression/scripts/regression.py" workflow >/dev/null; step .github/workflows/regression.yml "Run the rows, and keep one issue per failing row" rows.sh
  printf '[{"number": 2, "title": "Backlog", "state": "open"}]\n' > "$G/milestones.json"; printf '[]\n' > "$G/regression.json"
  rows() { reset; PATH="$G:$PATH" GH_TOKEN=x REGRESSION_RESULTS="$r/res.tsv" RUNNER_TEMP="$r" bash rows.sh 2>&1; }
  cat > "$G/ghwrap" <<'SH'
#!/bin/bash
case "$*" in *"-X POST repos/{owner}/{repo}/milestones -f title=Alpha"*) echo "$*" >> "$STUB/calls.log"; echo '{"number": 8}'; exit 0;; esac
[ -n "${STUB_ISSUE_FAIL:-}" ] && [ "$1 $2" = "issue create" ] && { echo "$*" >> "$STUB/calls.log"; echo "HTTP 502" >&2; exit 1; }
exec "$STUB/gh.real" "$@"
SH
  mv "$G/gh" "$G/gh.real"; mv "$G/ghwrap" "$G/gh"; chmod +x "$G/gh"
  out=$(rows); rc=$?
  grep -q "^api -X POST repos/{owner}/{repo}/milestones -f title=Alpha" "$G/calls.log" && grep -q "^issue create --title Regression: red --label regression --label defect --body <!-- loop-regression red placed=Alpha -->" "$G/calls.log" && grep -qx " --milestone Alpha" "$G/calls.log" \
    && ok "a failing test's defect issue goes on its feature's milestone, made once if missing" || bad "defect milestone"
  grep -q "^issue create --title Regression: blue .*placed=Backlog -->" "$G/calls.log" && grep -qx " --milestone Backlog" "$G/calls.log" && ! grep -q "title=Beta" "$G/calls.log" \
    && ok "a test whose page is no docs.tsv feature goes on Backlog, and no other milestone is made" || bad "backlog fallback"
  printf '[{"number": 31, "state": "OPEN", "body": "<!-- loop-regression red placed=Alpha -->", "labels": [{"name": "defect"}], "milestone": {"title": "Backlog"}},
 {"number": 32, "state": "OPEN", "body": "<!-- loop-regression blue -->", "labels": [{"name": "defect"}], "milestone": null}]\n' > "$G/regression.json"
  printf 'Alpha\tsrc/alpha\nBeta\tsrc/beta\n' > .loop/docs.tsv
  printf '[{"number": 2, "title": "Backlog", "state": "open"}, {"number": 8, "title": "Alpha", "state": "open"}, {"number": 9, "title": "Beta", "state": "open"}]\n' > "$G/milestones.json"
  out=$(rows)
  ! grep -q "^issue edit 31 --body" "$G/calls.log" && grep -q "^issue edit 32 --body <!-- loop-regression blue placed=Beta --> --milestone Beta" "$G/calls.log" \
    && ok "an issue the owner moved stays, and an older unplaced one moves to its feature" || bad "regression owner move"
  printf '[]\n' > "$G/regression.json"; out=$(STUB_ISSUE_FAIL=1 rows); rc=$?
  [ $rc = 1 ] && grep -q "FAILED issue for red" <<<"$out" && grep -q "FILED .* FAILED 2" <<<"$out" && ok "a filing that fails is named and fails the step" || bad "filing failure"
  printf '[]\n' > "$G/regression.json"; printf 'Alpha\tsrc/alpha\n' > .loop/docs.tsv
  printf '[{"number": 2, "title": "Backlog", "state": "open"}, {"number": 8, "title": "Alpha", "state": "closed"}]\n' > "$G/milestones.json"
  out=$(rows)
  grep -q "^issue create --title Regression: red .*placed=Alpha -->" "$G/calls.log" && ! grep -qx " --milestone Alpha" "$G/calls.log" \
    && grep -q "^api -X PATCH repos/{owner}/{repo}/issues/77 -F milestone=8" "$G/calls.log" \
    && ok "a failing row whose feature milestone is closed is set on it by number and records placed=Alpha" || bad "regression closed milestone"
  printf '[{"number": 41, "state": "OPEN", "body": "<!-- loop-regression red placed= -->", "labels": [{"name": "defect"}], "milestone": null}]\n' > "$G/regression.json"
  out=$(STUB_ISSUE_PATCH_FAIL=1 rows); cp "$G/calls.log" "$G/calls.log.prev"; printf '[]\n' > "$G/regression.json"; out2=$(STUB_ISSUE_PATCH_FAIL=1 rows); rc=$?
  grep -q "^issue edit 41 --body <!-- loop-regression red placed= -->$" "$G/calls.log.prev" && grep -q "^issue edit 77 --body <!-- loop-regression red placed= -->" "$G/calls.log" && [ $rc = 1 ] \
    && ok "a closed-milestone set that fails puts back the old placed= on a moved issue and an empty one on a new issue" || bad "by_number failure"
  rm -f "$G/milestones.json"; printf '#!/bin/bash\ncase "$*" in *milestones*) [ "$2" = "--paginate" ] && { echo "HTTP 502" >&2; exit 1; };; esac\nexec "$STUB/gh.real" "$@"\n' > "$G/gh.ms"
  chmod +x "$G/gh.ms"; cp "$G/gh" "$G/gh.keep"; cp "$G/gh.ms" "$G/gh"; out=$(rows); cp "$G/gh.keep" "$G/gh"
  ! grep -q -- "-X POST repos/{owner}/{repo}/milestones" "$G/calls.log" && grep -qx " --milestone Alpha" "$G/calls.log" \
    && ok "when milestones can't be read none is created and gh places the issue by title" || bad "unreadable milestones"
  cat > "$G/gh.ms2" <<'SH'
#!/bin/bash
case "$*" in *milestones*) [ "$2" = "--paginate" ] && { echo "HTTP 502" >&2; exit 1; };; esac
case "$1 $2" in "issue create") case "$*" in *--milestone*) echo "$*" >> "$STUB/calls.log"; echo "milestone not found" >&2; exit 1;; esac;; esac
exec "$STUB/gh.real" "$@"
SH
  chmod +x "$G/gh.ms2"; cp "$G/gh.ms2" "$G/gh"; out=$(rows); rc=$?; cp "$G/gh.keep" "$G/gh"
  grep -q "^issue create --title Regression: red .*placed= -->" "$G/calls.log" && ! grep -q "FAILED issue for red" <<<"$out" \
    && ok "when milestones can't be read and the feature has none yet, the issue is still filed, on no milestone" || bad "blind create fallback"
  W=$here/.github/workflows/regression.yml
  grep -q 'cron: "17 \*/4 \* \* \*"' "$W" && grep -q 'tags: \["v\*"\]' "$W" && grep -q "issues: write" "$W" \
    && ok "the full suite runs every 4 hours by default and on every release tag, with issue write access" || bad "schedule"
  mv "$G/gh.real" "$G/gh"; rm -f .loop/docs.tsv
  printf 'flag\tland\tfalse\tAAA-1\t2026-01-01\tGiven a, when b, then d.\tcriterion\t\n' >> .loop/regression.tsv
  git add -A >/dev/null; git -c user.email=t@example.test -c user.name=Toy commit -qm rows >/dev/null
  mkdir -p "$G/fake"; : > "$G/fake/calls.log"
  PATH="$here/dev/toy/fakegh:$PATH" FAKE_GH_DIR="$G/fake" FAKE_GH_ISSUE_OPEN=1 FAKE_GH_ISSUE_PLACED=1 \
    python3 -B "$here/skills/workflow-regression/scripts/regression.py" run flag --live >/dev/null 2>&1
  ! grep -q "^issue create" "$G/fake/calls.log" && grep -q "^issue comment 7" "$G/fake/calls.log" \
    && ok "a local live run finds the issue the scheduled run placed on a milestone, opening no duplicate" || bad "local run duplicate"
fi

if want upgrade; then
  echo "== upgrade: a workflow older than the skills is reported"
  x=$(mktemp -d); mkdir -p "$x/.loop"; printf '{}\n' > "$x/.loop/config.json"
  out=$($auto workflow --check --root "$x"); rc=$?
  [ $rc = 1 ] && [ "$(grep -c '(STALE_WORKFLOW)' <<<"$out")" = 2 ] && grep -q "is missing" <<<"$out" && ok "missing workflows are reported with the command that writes them" || bad "missing"
  $auto workflow --root "$x" >/dev/null; out=$($auto workflow --check --root "$x"); rc=$?
  [ $rc = 0 ] && [ -z "$out" ] && ok "current workflows pass the check" || bad "current"
  printf '\n# edited\n' >> "$x/.github/workflows/health.yml"; out=$($auto workflow --check --root "$x"); rc=$?
  [ $rc = 1 ] && grep -q "health.yml differs from what automation.py writes" <<<"$out" && ok "a stale health.yml is reported" || bad "stale"
  printf 'name: mine\n' > "$x/.github/workflows/mail-test.yml"; $auto workflow --root "$x" >/dev/null 2>&1; out=$($auto workflow --check --root "$x")
  grep -q "(NOT_OURS)" <<<"$out" && [ "$(cat "$x/.github/workflows/mail-test.yml")" = "name: mine" ] && ok "a hand-written workflow is never checked or rewritten" || bad "not ours"
  T=$(mktemp -d); python3 -B -c "import sys; sys.path.insert(0, '$S'); import workflows; open('$T/h.yml','w').write(workflows.health('47 */4 * * *','ANTHROPIC_API_KEY'))"
  python3 - "$T/h.yml" "$T/check.sh" <<'PY'
import sys
text = open(sys.argv[1]).read()
block = text.split("- name: Check the routine", 1)[1].split("run: |\n", 1)[1]
lines = []
for line in block.split("\n"):
    if line.strip() and not line.startswith("          "):
        break
    lines.append(line[10:])
open(sys.argv[2], "w").write("\n".join(lines).rstrip() + "\n")
PY
  (cd "$x" && mkdir -p skills/workflow-health && ln -s "$S" skills/workflow-health/scripts && printf '\n# drift\n' >> .github/workflows/health.yml && : > o.txt && : > s.txt \
    && EVENT=schedule GITHUB_OUTPUT=o.txt GITHUB_STEP_SUMMARY=s.txt bash -e "$T/check.sh" >out.txt 2>&1)
  grep -q "^::warning::STALE_WORKFLOW" "$x/out.txt" && grep -q "^STALE_WORKFLOW" "$x/s.txt" && grep -qx "on=true" "$x/o.txt" \
    && ok "each health run warns about a stale workflow and still runs" || bad "run warns"
  rm -rf "$x" "$T"
fi

echo "== $pass passed, $fail failed"
[ $fail = 0 ] && [ $pass -gt 0 ]
