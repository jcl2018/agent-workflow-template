#!/usr/bin/env python3
"""Mail the owner one digest per round: the text of the digest comment this run posted, at most once.

usage: mail.py send   mail this run's digest comment (the Email the digest step; GH_TOKEN and DIGEST_RUN set)
       mail.py test   send one fixed test mail through the configured sender (the Mail test workflow)

digest_mail in .loop/config.json picks the sender: cloudflare (default; Cloudflare Email Service's REST send API), smtp
(smtp_host, default smtp.gmail.com, and smtp_port, 465 or 587) or off. The address and keys come only from the secrets
DIGEST_TO, DIGEST_FROM, CLOUDFLARE_ACCOUNT_ID, CLOUDFLARE_EMAIL_TOKEN, DIGEST_SMTP_USER, DIGEST_SMTP_PASSWORD; no line
this prints ever holds their values. With no mail secret set at all, send says so and writes nothing (exit 0); with
some but not all, it names the missing ones (exit 1). The mail is the comment by github-actions[bot] whose marker says
run=DIGEST_RUN; the comment's marker gains `mailing` before the send and `mailed` after it, so no rerun sends twice.
Every outcome is one `MAIL:` line ending in a code, also written to the run summary.
"""
import argparse
import html
import json
import os
import re
import smtplib
import socket
import subprocess
import sys
import time
import traceback
import urllib.error
import urllib.request
from email.message import EmailMessage

os.environ.update(GIT_TERMINAL_PROMPT="0", GH_PROMPT_DISABLED="1", GIT_EDITOR="true", GIT_ASKPASS="true", SSH_ASKPASS="true")
if not sys.stdin or not sys.stdin.isatty():
    os.dup2(os.open(os.devnull, os.O_RDONLY), 0)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rounds  # noqa: E402

# Cloudflare Email Service REST API (its docs: Email Service, Send emails, REST API), read 2026-11-10:
CF_API = "https://api.cloudflare.com/client/v4"
CF_PATH = "/accounts/%s/email/sending/send"  # POST {to, from, subject, text, html}, Authorization: Bearer <token>
CF_RETRY = (429, 503)  # 10004 throttled, 10100 auth upstream: the mail was not accepted, so one retry is safe
ADDR = ("DIGEST_TO", "DIGEST_FROM")
SENDERS = {"cloudflare": ("CLOUDFLARE_ACCOUNT_ID", "CLOUDFLARE_EMAIL_TOKEN"), "smtp": ("DIGEST_SMTP_USER", "DIGEST_SMTP_PASSWORD")}
ALL = ADDR + SENDERS["cloudflare"] + SENDERS["smtp"]
LOCAL = ("127.0.0.1", "localhost")
FIX_SECRETS = "gh secret set %s (or Settings, Secrets and variables, Actions), then rerun"


class Stop(Exception):
    def __init__(self, code, text, status=1):
        Exception.__init__(self, text)
        self.code, self.text, self.status = code, text, status


def say(text, code):
    line = "MAIL: %s (%s)" % (scrub(text), code)
    print(line)
    rounds.summary(line)


def scrub(text):
    """Every secret value and the owner's address (with its local part), case-insensitively, become ***."""
    out = str(text)
    values = [os.environ.get(name) or "" for name in ALL]
    owner = values[0].split("@")[0] if "@" in values[0] else ""  # the owner's address alone: its local part too
    values += [owner] if len(owner) > 3 else []
    for value in sorted(set(v for v in values if len(v) > 2), key=len, reverse=True):
        out = re.sub(re.escape(value), "***", out, flags=re.I)
    return out


def config(root):
    try:
        with open(os.path.join(root, ".loop", "config.json")) as handle:
            data = json.load(handle)
            return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def settings(root):
    """(mode, host, port, retry wait); a bad setting stops before any work."""
    cfg = config(root)
    mode = cfg.get("digest_mail") or "cloudflare"
    if mode not in ("cloudflare", "smtp", "off"):
        raise Stop("MAIL_SETTING", "digest_mail is %r; it must be cloudflare, smtp or off. Fix: edit .loop/config.json" % mode)
    host, port = cfg.get("smtp_host") or "smtp.gmail.com", cfg.get("smtp_port") or 465
    test_port = os.environ.get("DIGEST_SMTP_TEST_PORT") or ""
    if test_port:
        if host not in LOCAL or not test_port.isdigit():
            raise Stop("MAIL_SETTING", "DIGEST_SMTP_TEST_PORT is for local tests only (smtp_host 127.0.0.1 or localhost). "
                       "Fix: unset it")
        port = int(test_port)
    elif port not in (465, 587):
        raise Stop("MAIL_SETTING", "smtp_port is %r; it must be 465 or 587. Fix: edit .loop/config.json" % port)
    wait = os.environ.get("DIGEST_MAIL_RETRY_SECONDS", "30")
    if not wait.isdigit() or int(wait) > 30:
        raise Stop("MAIL_SETTING", "DIGEST_MAIL_RETRY_SECONDS is %r; it must be 0 to 30. Fix: unset it" % wait)
    api = os.environ.get("DIGEST_MAIL_API") or ""
    if api and not re.match(r"http://(127\.0\.0\.1|localhost):\d+(/|$)", api):
        shown = re.match(r"^([a-z]+://[^/:@]*)", api)
        raise Stop("MAIL_TEST_URL", "DIGEST_MAIL_API must be a local test server, not %s. Fix: unset DIGEST_MAIL_API"
                   % (shown.group(1) if shown else "that value"))
    return mode, host, port, int(wait), api or CF_API


def secrets(mode, test):
    """The needed secrets, or Stop: none set at all is 'not set up' (exit 0 for send), any gap names the missing ones."""
    need = ADDR + SENDERS[mode]
    missing = [name for name in need if not os.environ.get(name)]
    if not missing:
        return {name: os.environ[name] for name in need}
    if not any(os.environ.get(name) for name in ALL) and not test:
        raise Stop("MAIL_NOT_SET_UP", "not set up: no mail secret is set, so nothing was sent or written. Fix: to get the "
                   "round's mail, " + FIX_SECRETS % " ".join(need), status=0)
    raise Stop("MAIL_SECRETS", "%snot sent: missing secrets %s; nothing was written. Fix: %s"
               % ("test " if test else "", ", ".join(missing), FIX_SECRETS % " ".join(missing)))


def inline(text):
    out = []
    for piece in re.split(r"(\[[^\]]*\]\([^)\s]*\))", text):
        link = re.fullmatch(r"\[([^\]]*)\]\(([^)\s]*)\)", piece)
        if link and link.group(2).startswith("https://github.com/"):
            out.append('<a href="%s">%s</a>' % (html.escape(link.group(2), quote=True), html.escape(link.group(1))))
        elif link:
            out.append(html.escape(link.group(1) + " (" + link.group(2) + ")"))
        else:
            out.append(html.escape(piece))
    joined = "".join(out)
    joined = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", joined)
    return re.sub(r"`([^`]+)`", r"<code>\1</code>", joined).replace("**", "")


def to_html(text):
    out, table, items = [], [], []

    def flush():
        if table:
            out.append("<table>" + "".join("<tr>%s</tr>" % "".join("<td>%s</td>" % inline(c.strip()) for c in row)
                                           for row in table) + "</table>")
            table.clear()
        if items:
            out.append("<ul>" + "".join("<li>%s</li>" % inline(i) for i in items) + "</ul>")
            items.clear()
    for line in text.splitlines():
        if line.startswith("|"):
            cells = [c for c in line.strip().strip("|").split("|")]
            if not all(re.fullmatch(r"\s*-+\s*", c) for c in cells):
                table.append(cells)
            continue
        if line.startswith("- "):
            items.append(line[2:])
            continue
        flush()
        if line.startswith("### "):
            out.append("<h3>%s</h3>" % inline(line[4:]))
        elif line.strip():
            out.append("<p>%s</p>" % inline(line))
    flush()
    return "<html><body>%s</body></html>" % "\n".join(out)


def message(body, repo):
    lines = [line for line in body.splitlines() if not rounds.MARK.search(line)]
    if lines:
        lines[0] = re.sub(r"^@[A-Za-z0-9-]+ ", "", lines[0])
    text = "\n".join(lines).strip() + "\n"
    counts = {"New": 0, "Still open": 0, "Fixed": 0}
    for kind, n in re.findall(r"^\*\*(New|Still open|Fixed)\*\* \((\d+)\)", text, re.M):
        counts[kind] += int(n)
    subject = "Automation digest: %d new, %d still open, %d fixed (%s)" % (counts["New"], counts["Still open"], counts["Fixed"], repo)
    return subject, text, to_html(text)


def send_cloudflare(keys, subject, text, page, api):
    """('ok'|'retry'|'refused'|'unknown', detail)."""
    data = json.dumps({"to": keys["DIGEST_TO"], "from": keys["DIGEST_FROM"], "subject": subject, "text": text, "html": page}).encode()
    request = urllib.request.Request(api + CF_PATH % keys["CLOUDFLARE_ACCOUNT_ID"], data=data, method="POST", headers={
        "Authorization": "Bearer " + keys["CLOUDFLARE_EMAIL_TOKEN"], "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=30) as reply:
            answer = json.loads(reply.read() or b"{}")
    except urllib.error.HTTPError as err:
        try:
            first = (json.loads(err.read() or b"{}").get("errors") or [{}])[0]
        except ValueError:
            first = {}
        detail = "HTTP %d %s %s" % (err.code, first.get("code", ""), first.get("message", ""))
        if err.code in CF_RETRY:
            return "retry", detail
        return ("unknown" if err.code >= 500 else "refused"), detail
    except urllib.error.URLError as err:  # no connection: nothing reached Cloudflare
        if isinstance(err.reason, (socket.timeout, TimeoutError)):
            return "unknown", "timed out after the request was sent"
        return "retry", "couldn't connect: %s" % err.reason
    except (socket.timeout, TimeoutError):
        return "unknown", "timed out after the request was sent"
    result = answer.get("result") or {}
    if not answer.get("success") or [a for a in result.get("permanent_bounces") or [] if a]:
        return "refused", "Cloudflare did not accept it: %s" % (answer.get("errors") or "permanent bounce")
    return "ok", ""


def send_smtp(keys, subject, text, page, host, port):
    mail = EmailMessage()
    mail["Subject"], mail["From"], mail["To"] = subject, keys["DIGEST_FROM"], keys["DIGEST_TO"]
    mail.set_content(text)
    mail.add_alternative(page, subtype="html")
    try:
        if os.environ.get("DIGEST_SMTP_TEST_PORT"):
            server = smtplib.SMTP(host, port, timeout=30)  # local test server only (settings checks the host)
        elif port == 465:
            server = smtplib.SMTP_SSL(host, port, timeout=30)
        else:
            server = smtplib.SMTP(host, port, timeout=30)
            server.starttls()
        with server:
            if not os.environ.get("DIGEST_SMTP_TEST_PORT"):
                server.login(keys["DIGEST_SMTP_USER"], keys["DIGEST_SMTP_PASSWORD"])
            server.send_message(mail)
    except smtplib.SMTPAuthenticationError as err:
        return "refused", "login refused (%s)" % err.smtp_code
    except (smtplib.SMTPSenderRefused, smtplib.SMTPRecipientsRefused, smtplib.SMTPHeloError) as err:
        code = getattr(err, "smtp_code", 0) or min([c for c, _ in getattr(err, "recipients", {}).values()] or [500])
        return ("retry" if 400 <= code < 500 else "refused"), "%s %s" % (type(err).__name__, code)
    except (smtplib.SMTPDataError, smtplib.SMTPServerDisconnected) as err:
        return "unknown", "%s after the message started" % type(err).__name__
    except (smtplib.SMTPConnectError, ConnectionRefusedError, socket.gaierror) as err:
        return "retry", "couldn't connect: %s" % type(err).__name__
    return "ok", ""


def deliver(mode, keys, subject, text, page, opts):
    """(outcome, detail, retried): one retry, only when the provider cannot have accepted the mail."""
    host, port, wait, api = opts
    for attempt in (0, 1):
        if mode == "cloudflare":
            outcome, detail = send_cloudflare(keys, subject, text, page, api)
        else:
            outcome, detail = send_smtp(keys, subject, text, page, host, port)
        if outcome != "retry" or attempt:
            return ("refused" if outcome == "retry" else outcome), detail, attempt
        time.sleep(wait)


def refused_fix(mode, detail):
    if mode == "smtp" and "login" in detail:
        return "use an app password (Gmail: 2-step verification, then an app password) in DIGEST_SMTP_PASSWORD"
    if re.search(r"HTTP 40[13]", detail):
        return "check that CLOUDFLARE_EMAIL_TOKEN has the Email Sending send permission and CLOUDFLARE_ACCOUNT_ID is right"
    if "sender" in detail.lower() or "domain" in detail.lower():
        return "onboard DIGEST_FROM's domain to Cloudflare Email Sending"
    return "check the secrets and the provider's status"


def cmd_test(args):
    mode, host, port, wait, api = settings(args.root)
    if mode == "off":
        raise Stop("MAIL_OFF", "test not sent: digest_mail is off. Fix: set digest_mail to cloudflare or smtp in "
                   ".loop/config.json, then run the Mail test workflow again")
    keys = secrets(mode, True)
    repo = os.environ.get("GITHUB_REPOSITORY") or "this repo"
    text = "This is a test of the Automation digest mail for %s. The round's mail will look like the digest comment.\n" % repo
    outcome, detail, retried = deliver(mode, keys, "Automation digest: test from %s" % repo, text, to_html(text),
                                       (host, port, wait, api))
    if outcome != "ok":
        raise Stop("MAIL_REFUSED", "test not sent: %s refused it: %s. Fix: %s, then run the Mail test workflow again"
                   % (mode, detail, refused_fix(mode, detail)))
    say("test sent%s" % (" (after 1 retry)" if retried else ""), "MAIL_SENT")
    return 0


def cmd_send(args):
    mode, host, port, wait, api = settings(args.root)
    if mode == "off":
        raise Stop("MAIL_OFF", "off: digest_mail is off in .loop/config.json, so nothing was sent", status=0)
    keys = secrets(mode, False)
    run = os.environ.get("DIGEST_RUN") or ""
    if not run.isdigit():
        raise Stop("MAIL_NO_COMMENT", "no run id (DIGEST_RUN), so nothing was sent. Fix: run this from the health workflow")
    found = rounds.digest_issue()
    if found is None:
        raise Stop("MAIL_GH", "gh couldn't read the digest issue, so nothing was sent. Fix: rerun this job (safe: nothing was sent)")
    number, body = found
    comment = rounds.run_comment(number, run) if number is not None else None
    if comment is False:
        raise Stop("MAIL_GH", "gh couldn't read the digest comments, so nothing was sent. Fix: rerun this job (safe: nothing was sent)")
    if not comment:
        raise Stop("MAIL_NO_COMMENT", "no digest comment for run %s, so nothing was sent. Fix: see the Post the digest step; "
                   "rerun this job once it has posted (safe: nothing was sent)" % run)
    state, flags = comment["state"], set(comment["state"]["flags"])
    if "mailed" in flags:
        raise Stop("MAIL_ALREADY", "already sent for run %s" % run, status=0)
    if "mailing" in flags:
        raise Stop("MAIL_UNKNOWN", "a mail for run %s may already have been sent: an earlier attempt stopped after sending "
                   "began (side effects: unknown). Fix: check your inbox for \"Automation digest\"; if none arrived, delete "
                   "the word mailing from the last line of %s and rerun this job" % (run, comment["url"]))
    if not rounds.save_comment(comment["id"], rounds.with_marker(comment["body"], state, {"mailing"})):
        raise Stop("MAIL_MARK", "couldn't mark run %s as sending on %s, so nothing was sent. Fix: rerun this job (safe: "
                   "nothing was sent)" % (run, comment["url"]))
    subject, text, page = message(comment["body"], os.environ.get("GITHUB_REPOSITORY") or "this repo")
    outcome, detail, retried = deliver(mode, keys, subject, text, page, (host, port, wait, api))
    if outcome == "refused":
        if not rounds.save_comment(comment["id"], rounds.with_marker(comment["body"], state, set())):
            raise Stop("MAIL_CLEAR_FAILED", "refused (%s) and couldn't clear the sending mark on %s. Fix: delete the word "
                       "mailing from that comment's last line, then rerun this job (nothing was sent)" % (detail, comment["url"]))
        raise Stop("MAIL_REFUSED", "%s refused it: %s; nothing was sent. Fix: %s, then rerun this job (safe)"
                   % (mode, detail, refused_fix(mode, detail)))
    if outcome == "unknown":
        raise Stop("MAIL_UNKNOWN", "%s may have accepted the mail for run %s: %s (side effects: unknown); it stays marked "
                   "mailing so no rerun sends twice. Fix: check your inbox for \"Automation digest\"; if none arrived, "
                   "delete the word mailing from the last line of %s and rerun this job" % (mode, run, detail, comment["url"]))
    if not rounds.save_comment(comment["id"], rounds.with_marker(comment["body"], state, {"mailed"})):
        raise Stop("MAIL_MARKED_LATE", "sent for run %s, but couldn't mark the comment mailed; it keeps mailing, so a rerun "
                   "won't send again. Fix: nothing to do" % run)
    body_state = rounds.parse(body)
    if body_state and rounds.order(body_state["run"]) < rounds.order(run):  # the digest couldn't save its state
        rounds.gh("issue", "edit", str(number), "--body", body.split("<!-- automation-digest")[0].rstrip() + "\n\n"
                  + rounds.marker(run, state["open"]))
    say("sent for run %s%s" % (run, " (after 1 retry)" if retried else ""), "MAIL_SENT")
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    for name, func in (("send", cmd_send), ("test", cmd_test)):
        item = sub.add_parser(name)
        item.add_argument("--root", default="")
        item.set_defaults(func=func)
    args = parser.parse_args()
    if not args.root:
        top = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True)
        args.root = top.stdout.strip() or os.getcwd()
    try:
        return args.func(args)
    except Stop as stop:
        say(stop.text, stop.code)
        return stop.status
    except Exception as err:  # never a traceback: it could hold a URL or an address
        frames = traceback.extract_tb(err.__traceback__)
        ours = [f for f in frames if os.path.basename(f.filename) in ("mail.py", "rounds.py")]
        frame = (ours or frames)[-1]
        say("failed: %s: %s at %s:%d in %s. Fix: rerun this job; if it fails again, report this line"
            % (type(err).__name__, str(err)[:200], os.path.basename(frame.filename), frame.lineno, frame.name), "MAIL_FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())
