"""The round's mail from its digest comment: subject, plain text and a small escaped HTML part (mail.py sends it).

Links become anchors only for https://github.com/ URLs; everything else is escaped text.
"""
import html
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rounds  # noqa: E402


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
