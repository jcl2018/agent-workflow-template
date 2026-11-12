#!/usr/bin/env python3
"""Send one routine email over SMTP, unattended (no mail tool that stops to ask).

usage: send-mail.py --subject S --body-file F   sends one email
       send-mail.py --check                     logs in only, sends nothing

Credentials come only from ~/.workflow-loop/mail.env (SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD).
The one recipient comes only from ~/.workflow-loop/mail-to. Neither file is ever printed, and there is
no option to name another recipient. Both files are yours to create; the template never holds a value.
"""
import argparse
import os
import smtplib
import ssl
import sys
from email.message import EmailMessage

HOME = os.path.join(os.path.expanduser("~"), ".workflow-loop")
SECRETS, TO_FILE = os.path.join(HOME, "mail.env"), os.path.join(HOME, "mail-to")


def die(text):
    print("ERROR " + text)
    sys.exit(1)


def load():
    vals = {}
    try:
        for line in open(SECRETS):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                vals[key.strip()] = value.strip().strip("\"'")
        to = [word for word in open(TO_FILE).read().split() if word]
    except OSError:
        die("a local mail file is missing (names: mail.env, mail-to in the .workflow-loop folder)")
    if not vals.get("SMTP_USER") or not vals.get("SMTP_PASSWORD"):
        die("SMTP_USER or SMTP_PASSWORD is not set in mail.env")
    if len(to) != 1 or "@" not in to[0]:
        die("mail-to must hold exactly one address")
    return vals, to[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--subject")
    ap.add_argument("--body-file")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    vals, to = load()
    msg = EmailMessage()
    msg["From"], msg["To"] = vals["SMTP_USER"], to
    try:
        with smtplib.SMTP_SSL(vals.get("SMTP_HOST") or "smtp.gmail.com", int(vals.get("SMTP_PORT") or 465),
                              context=ssl.create_default_context(), timeout=60) as server:
            server.login(vals["SMTP_USER"], vals["SMTP_PASSWORD"])
            if args.check:
                print("OK login works; nothing sent")
                return 0
            if not args.subject or not args.body_file:
                die("--subject and --body-file are both needed")
            msg["Subject"] = args.subject
            msg.set_content(open(args.body_file).read())
            server.send_message(msg)
    except (OSError, smtplib.SMTPException, ValueError) as error:
        die("send failed (%s)" % type(error).__name__)  # the class only: a message can echo the login
    print("OK sent one email")
    return 0


if __name__ == "__main__":
    sys.exit(main())
