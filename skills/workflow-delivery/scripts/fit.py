#!/usr/bin/env python3
"""What a goal decides at freeze and reads later: its size and review depth (DEL-6), its budget (DEL-8), its release
bump (DEL-5), where it resumes (DEL-7) and what a deliberate rerun clears. Pure functions with no guards import, so
role, flow, goal, release and the board can all read them.

Size: a goal is small with at most 3 done lines, no `github:` touch and at most one code area. An area is a touched
path's first two components (`skills/workflow-release`, `src/api`) or a top-level folder; paths under docs/, .loop/,
dev/toy/, test/ and tests/, files at the repo root (VERSION, CHANGELOG.md) and `github:` surfaces are no area. No
touches declared counts as large, and so does a record from before sizing existed.

Depth: the owner's per-goal override wins; else review_depth full holds every goal to full; else (condensed) a small
goal runs condensed and a larger one full.

Owner settings (`goal.py set`) live in the operation sidecar `<runs>/<slug>.extra.json` under its lock, so a worker's
save of the run record can't erase them; `view` merges them over the run record.
"""
import json
import os
import re

STEPS = ("idea", "plan", "review", "qa", "ship")
NOT_AREAS = ("docs/", ".loop/", "dev/toy/", "test/", "tests/")
SURFACES = ("wiki", "milestones", "projects", "releases", "labels", "issues")
SMALL_DONE = 3


def surface(path):
    """The GitHub surface a `github:` touch names, '' for a repo path, None for a bad `github:` entry."""
    if not path.startswith("github:"):
        return ""
    name = path[len("github:"):]
    return name if name in SURFACES else None


def area(path, top=None):
    """The code area a repo path belongs to, or None when it counts for no area."""
    clean = path.strip().strip("/")
    if not clean or surface(path) != "" or any((clean + "/").startswith(item) for item in NOT_AREAS):
        return None
    parts = clean.split("/")
    if len(parts) >= 2:
        return "/".join(parts[:2])
    return clean if top and os.path.isdir(os.path.join(top, clean)) else None


def size_of(done_lines, touches, top=None):
    """{"small": bool, "why": str}, decided from the frozen done lines and the touches."""
    count = len(done_lines)
    if not touches:
        return {"small": False, "why": "large: no touches declared"}
    if any(surface(t) not in ("", None) for t in touches):
        return {"small": False, "why": "large: it touches GitHub (%s)" % ", ".join(t for t in touches if t.startswith("github:"))}
    areas = sorted({a for a in (area(t, top) for t in touches) if a})
    small = count <= SMALL_DONE and len(areas) <= 1
    return {"small": small, "why": "%s: %d done line%s, %s" % (
        "small" if small else "large", count, "" if count == 1 else "s",
        "%d areas (%s)" % (len(areas), ", ".join(areas)) if len(areas) > 1 else "one area" if areas else "no code area")}


def sidecar(runs, slug):
    """The owner's settings for a goal, from the operation sidecar ({} when none)."""
    try:
        with open(os.path.join(runs, slug + ".extra.json")) as handle:
            found = json.load(handle)
    except (OSError, ValueError):
        return {}
    got = found.get("set") if isinstance(found, dict) else None
    return got if isinstance(got, dict) else {}


def view(state, runs=None):
    """The run record with the owner's settings merged over it (settings win)."""
    merged = dict(state or {})
    if runs and merged.get("slug"):
        merged.update(sidecar(runs, merged["slug"]))
    return merged


def depth_for(setting, seen):
    """(depth, why) for a goal: seen is view(state)."""
    over = seen.get("depth_override")
    if isinstance(over, dict) and over.get("depth") in ("full", "condensed"):
        return over["depth"], "owner override: %s" % (over.get("why") or "set per goal")
    if setting != "condensed":
        return "full", "review_depth full holds every goal to full"
    size = seen.get("size") if isinstance(seen.get("size"), dict) else None
    if not size:
        return "full", "large: frozen before goals were sized"
    return ("condensed" if size.get("small") else "full"), size.get("why") or ""


def budget_of(cfg):
    """The repo's budget: time_budget_minutes and token_budget, 0 meaning none set."""
    def number(key):
        value = (cfg or {}).get(key)
        return value if isinstance(value, int) and not isinstance(value, bool) and value > 0 else 0
    return {"minutes": number("time_budget_minutes"), "tokens": number("token_budget")}


def budget(seen, cfg):
    """(budget, source): a budget the goal carries wins, even 0; a record from before budgets uses the repo's."""
    held = seen.get("budget")
    if isinstance(held, dict):
        return {"minutes": int(held.get("minutes") or 0), "tokens": int(held.get("tokens") or 0)}, "the goal's budget"
    return budget_of(cfg), "the repo settings"


def spent_tokens(run):
    """Tokens a goal has spent: the per-step values when any exist, else the total a background worker wrote."""
    value = run.get("tokens") if isinstance(run.get("tokens"), dict) else {}
    steps = [n for key, n in value.items() if key != "total" and isinstance(n, int) and not isinstance(n, bool)]
    if steps:
        return sum(steps)
    total = value.get("total")
    return total if isinstance(total, int) else 0


def recorded(state, step):
    return str((state.get("flow") or {}).get(step, "")).startswith(("done", "skipped"))


def resume_at(state, moved=None):
    """The step a stopped or crashed goal goes on from, read from its record only. With idea and plan recorded and
    review not: build when no commit landed after the plan record (moved False or unknown), else review."""
    left = [step for step in STEPS if not recorded(state, step)]
    if not left:
        return "pr"
    if left[0] == "review" and recorded(state, "plan"):
        return "review" if moved else "build"
    return left[0]


def next_command(state, step):
    slug = state.get("slug", "SLUG")
    return {"pr": "goal.py pr %s" % slug, "build": "goal.py step %s build, then flow.py %s review" % (slug, slug)}.get(
        step, "flow.py %s %s" % (slug, step))


def again(state, step):
    """Clear a step's record and every later step's (result, depth, verdicts) for a deliberate rerun. Tries, tokens,
    size, budget and the owner's settings stay. Returns the steps cleared."""
    later = list(STEPS[STEPS.index(step):])
    cleared = [s for s in later if s in (state.get("flow") or {})]
    for key in ("flow", "depth", "verdicts"):
        held = state.get(key)
        if isinstance(held, dict):
            for s in later:
                held.pop(s, None)
    return cleared


def says_bump(goal):
    """minor or major when the goal text names one (a hint for the operation; never stored)."""
    found = re.search(r"\b(minor|major)\b", goal or "", re.I)
    return found.group(1).lower() if found else ""
