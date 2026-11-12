"""Rows a lane could not run here that are also unproven (REG-10): the goal waits for off-platform red proof, not a failed try.

A row that exits 77 is SKIPPED on this platform and, never seen failing, UNPROVEN. When those are the only reasons a lane
failed, the proof is owed from a Linux or Mac runner (regression.py red --off-platform); a real FAIL still costs a try.
"""
import re


def rows(text, ids):
    """The ids to wait on: the lane failed only on UNPROVEN rows that were also SKIPPED, else []."""
    skipped = set(re.findall(r"^SKIPPED (\S+)", text, re.M))
    bad = set(re.findall(r"^FAIL (\S+)", text, re.M))
    unproven = re.findall(r"^UNPROVEN ([^\s:]+)", text, re.M)
    return unproven if unproven and not bad and set(unproven) <= skipped else []


def line(text, ids):
    return "\nLANE_OWED %s: skipped on this platform and never seen failing" % ", ".join(rows(text, ids))


def reply(lane_line):
    """The step reply for a lane line that carries LANE_OWED, else ''."""
    found = re.search(r"^LANE_OWED (.+?):", lane_line, re.M)
    if not found:
        return ""
    return ("%s\nPENDING: waiting for off-platform proof of %s. On a Linux or Mac runner run, for each row, "
            "python3 skills/workflow-regression/scripts/regression.py red ID --break \"<command that breaks it>\", then on this branch "
            "regression.py red ID --off-platform --runner NAME --commit SHA; then answer go on\nSTEP: pending\n"
            % (lane_line, found.group(1)))
