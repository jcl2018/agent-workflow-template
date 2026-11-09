#!/usr/bin/env python3
"""Draw the live board from board.json: board.html and board-artifact.html.

usage: board_page.py [--in FILE] [--out DIR]

Reads board.json (default <git common dir>/loop/board.json) and writes both pages beside it, or into --out. Both show the live
board that live_board.py prints, so the page and the text agree. board-artifact.html has no doctype, html, head or body tags.
The pages have no scripts and load nothing from the network.
"""
import argparse
import html
import json
import os
import subprocess
import sys

# No terminal, no waiting: a prompt from git or gh must fail, not block.
os.environ.update(GIT_TERMINAL_PROMPT="0", GH_PROMPT_DISABLED="1", GIT_EDITOR="true", GIT_ASKPASS="true", SSH_ASKPASS="true")
if not sys.stdin or not sys.stdin.isatty():
    os.dup2(os.open(os.devnull, os.O_RDONLY), 0)

DARK = "--bg:#141414;--fg:#eee;--mute:#aaa;--line:#333"
CSS = ":root{--bg:#fff;--fg:#1b1b1b;--mute:#666;--line:#ddd}\n" \
      "@media (prefers-color-scheme:dark){:root:not([data-theme=light]){%s}}\n:root[data-theme=dark]{%s}\n" % (DARK, DARK) + """\
body{background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,sans-serif;margin:0 auto;max-width:1000px;padding:16px}
h1{font-size:22px}.mute{color:var(--mute)}pre{font:14px/1.5 ui-monospace,monospace;white-space:pre-wrap;overflow-wrap:anywhere;margin:0}"""


def esc(value):
    return html.escape(str(value if value is not None else ""), quote=True)


def page(doc, bare=False):
    name, style = "<title>Operation board</title>", "<style>%s</style>" % CSS
    out = [name + style + "<h1>Operation board</h1>"] if bare else [
        "<!doctype html><html lang=en><head><meta charset=utf-8>",
        "<meta name=viewport content='width=device-width,initial-scale=1'>" + name,
        style + "</head><body><h1>Operation board</h1>"]
    every = doc["cadence"] + " min" if doc["cadence"] != "off" else "never (off)"
    out.append("<p class=mute>%s. Written %s. Check in every %s.%s</p>" % (
        esc(doc["digest"]), esc(doc["generated"]), esc(every), esc(" Next check-in " + doc["next_at"] + "." if doc["next_at"] else "")))
    helper = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "live_board.py")
    if os.path.exists(helper):
        out.append(subprocess.run([sys.executable, helper, "--html"], capture_output=True, text=True).stdout)
    return "\n".join(out) + ("" if bare else "</body></html>") + "\n"


def write(path, text):
    temp = path + ".%d.tmp" % os.getpid()
    with open(temp, "w") as handle:
        handle.write(text)
    os.replace(temp, path)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--in", dest="source", default="")
    parser.add_argument("--out", default="")
    args = parser.parse_args()
    found = subprocess.run(["git", "rev-parse", "--git-common-dir"], capture_output=True, text=True).stdout.strip()
    path = os.path.abspath(args.source or os.path.join(found, "loop", "board.json"))
    try:
        with open(path) as handle:
            doc = json.load(handle)
    except (OSError, ValueError):
        sys.exit("REFUSED: no readable %s. Fix: run board.py board first." % path)
    folder = os.path.abspath(args.out) if args.out else os.path.dirname(path)
    os.makedirs(folder, exist_ok=True)
    write(os.path.join(folder, "board.html"), page(doc))
    write(os.path.join(folder, "board-artifact.html"), page(doc, True))
    for name, file in (("HTML", "board.html"), ("ARTIFACT", "board-artifact.html")):
        print(name, os.path.join(folder, file))
    return 0


if __name__ == "__main__":
    sys.exit(main())
