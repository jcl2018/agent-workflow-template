import re

LAST = 40  # lines of a failing row's output an issue carries (defect 3789)
QUIET = re.compile(r"\|\s*grep\s+-\w*q\w*\s+(?:\"[^\"]*\"|'[^']*'|\S+)")  # `| grep -q PATTERN` hides the stream it checks


def again(command):
    """The row's command with each `| grep -q PATTERN` made `| cat`, or None when it has none: the same run, its text kept."""
    loud = QUIET.sub("| cat", command)
    return loud if loud != command else None


def shown(run, command, code, text):
    """What a failing row's issue shows: its last LAST lines, never empty. A row that printed nothing runs once more with
    the quiet stage made loud (run is the caller's (code, text) runner); its verdict stays the first run's."""
    if not text.strip() and again(command):
        text = run(again(command))[1]
    lines = [line[:400] for line in text.rstrip().splitlines()[-LAST:]]
    return "\n".join(lines).replace("`" * 3, "'" * 3) or "(the row printed nothing; it exited %s)" % code
