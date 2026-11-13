#!/usr/bin/env python3
"""What a goal decides at freeze and reads later (DEL-5 to DEL-8). Pure functions with no guards import, so every script reads them.

Size: a goal is small with at most 3 done lines, no `github:` touch and at most one code area. An area is a touched
path's first two components (`skills/workflow-release`, `src/api`) or a top-level folder; paths under docs/, .loop/,
dev/toy/, test/ and tests/, files at the repo root (VERSION, CHANGELOG.md) and `github:` surfaces are no area. No
touches declared counts as large, and so does a record from before sizing existed.

Depth: the owner's per-goal override wins; else review_depth full holds every goal to full; else (condensed) a small
goal runs condensed and a larger one full.

Owner settings (`goal.py set`) live in the operation sidecar `<runs>/<slug>.extra.json` under its lock, so a worker's
save of the run record can't erase them; `view` merges them over the run record.

Also here, so the package stays under its file cap: the operation's `set` and `queue` commands and what `new`, `record`
and `pr` keep (each takes goal.py's module as g, and imports guards, private and role lazily, since they import fit),
and the pull request body: each step's result, depth, tokens and VERDICT lines (issue 38), the decided depth, the
budget, the private-name scan, GitHub surfaces and scripts that may write back what the goal deletes (issue 117).

And the defect-test check (was defect.py): `fit.py owed SLUG` prints the issues and findings the goal fixes ("fixes #N",
closes, resolves, "fixes finding:ID") that still lack a regression row of category defect linked to them, seen failing
on a date and passing now, and exits 1 if any; the goal's branch must have added that row or set its seen-failing date
(regression.tsv against the merge-base with origin/<base>, E-10: an old row merely edited does not count). goal.py pr
calls owed() and refuses on its answer.
"""
import json
import os
import re
import subprocess
import sys

# No terminal, no waiting: a prompt from git must fail, not block.
os.environ.update(GIT_TERMINAL_PROMPT="0", GH_PROMPT_DISABLED="1", GIT_EDITOR="true", GIT_ASKPASS="true", SSH_ASKPASS="true")

STEPS = ("idea", "plan", "review", "qa", "ship")
NOT_AREAS = ("docs/", ".loop/", "dev/toy/", "test/", "tests/")
SURFACES = ("wiki", "milestones", "projects", "releases", "labels", "issues")
SMALL_DONE = 3


def surface(path):
    """The GitHub surface a `github:` touch names, '' for a repo path, None if bad."""
    if not path.startswith("github:"):
        return ""
    name = path[len("github:"):]
    return name if name in SURFACES else None


def area(path, top=None):
    """The code area a repo path belongs to, or None."""
    clean = path.strip().strip("/")
    if not clean or surface(path) != "" or any((clean + "/").startswith(item) for item in NOT_AREAS):
        return None
    parts = clean.split("/")
    if len(parts) >= 2:
        return "/".join(parts[:2])
    return clean if top and os.path.isdir(os.path.join(top, clean)) else None


def size_of(done_lines, touches, top=None):
    """{"small": bool, "why": str} from the done lines and touches."""
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
    """The owner's settings for a goal ({} when none)."""
    try:
        with open(os.path.join(runs, slug + ".extra.json")) as handle:
            found = json.load(handle)
    except (OSError, ValueError):
        return {}
    got = found.get("set") if isinstance(found, dict) else None
    return got if isinstance(got, dict) else {}


def view(state, runs=None):
    """The run record with the owner's settings merged over it."""
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
    """The repo's time_budget_minutes and token_budget, 0 meaning none set."""
    def number(key):
        value = (cfg or {}).get(key)
        return value if isinstance(value, int) and not isinstance(value, bool) and value > 0 else 0
    return {"minutes": number("time_budget_minutes"), "tokens": number("token_budget")}


def budget(seen, cfg):
    """(budget, source): the goal's budget wins, even 0; else the repo's."""
    held = seen.get("budget")
    if isinstance(held, dict):
        return {"minutes": int(held.get("minutes") or 0), "tokens": int(held.get("tokens") or 0)}, "the goal's budget"
    return budget_of(cfg), "the repo settings"


def spent_tokens(run):
    """Tokens a goal has spent: per-step values, else the worker's total."""
    value = run.get("tokens") if isinstance(run.get("tokens"), dict) else {}
    steps = [n for key, n in value.items() if key != "total" and isinstance(n, int) and not isinstance(n, bool)]
    if steps:
        return sum(steps)
    total = value.get("total")
    return total if isinstance(total, int) else 0


def tokens_text(run):
    """'1,234 tokens', or 'tokens unread' when no count was recorded (never 0)."""
    value = run.get("tokens") if isinstance(run.get("tokens"), dict) else {}
    return "%s tokens" % format(spent_tokens(run), ",") if any(isinstance(n, int) and n for n in value.values()) else "tokens unread"


def recorded(state, step):
    return str((state.get("flow") or {}).get(step, "")).startswith(("done", "skipped"))


def resume_at(state, moved=None):
    """The step a stopped goal goes on from: build when no commit landed after the plan record, else review."""
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
    """Clear a step and every later step (result, depth, verdicts) for a rerun; returns the steps cleared."""
    later = list(STEPS[STEPS.index(step):])
    cleared = [s for s in later if s in (state.get("flow") or {})]
    for key in ("flow", "depth", "verdicts"):
        held = state.get(key)
        if isinstance(held, dict):
            for s in later:
                held.pop(s, None)
    return cleared


def says_bump(goal):
    """minor or major when the goal text names one (never stored)."""
    found = re.search(r"\b(minor|major)\b", goal or "", re.I)
    return found.group(1).lower() if found else ""


# ---- operation commands and what goal.py keeps (was guards_ops.py)
SET_AFTER_RECORD = "SET_AFTER_RECORD"


def cmd_set(g, args):
    import guards  # noqa: E401 - lazily: they import fit
    guards.operation_only(g, "set", args.slug)
    state = g.load(args.slug)
    if not (args.depth or args.bump or args.budget_minutes is not None or args.budget_tokens is not None):
        g.no("nothing to set. Fix: give --depth, --bump, --budget-minutes or --budget-tokens")
    why = " ".join(args.why.split())
    if args.depth and any(recorded(state, s) for s in ("plan", "review")):
        done = [s for s in ("review", "plan") if recorded(state, s)][-1]
        g.no("%s is already recorded, so a new depth wouldn't bind it; nothing changed. Fix: goal.py set first, then "
             "flow.py %s %s --again (%s)" % (done, args.slug, done, SET_AFTER_RECORD))
    if args.bump and state.get("release") in ("cut", "merged"):
        g.no("%s's release has started; nothing changed (%s)" % (args.slug, SET_AFTER_RECORD))
    runs = g.state_dir()
    if args.depth:
        guards.add_set(runs, args.slug, "depth_override", {"depth": args.depth, "why": why}, "set depth %s: %s" % (args.depth, why))
    if args.bump:
        guards.add_set(runs, args.slug, "bump", args.bump, "set bump %s: %s" % (args.bump, why))
    if args.budget_minutes is not None or args.budget_tokens is not None:
        held, _ = budget(view(state, runs), g.config())
        if args.budget_minutes is not None:
            held["minutes"] = max(0, args.budget_minutes)
        if args.budget_tokens is not None:
            held["tokens"] = max(0, args.budget_tokens)
        guards.add_set(runs, args.slug, "budget", held, "set budget %dm, %d tokens: %s" % (held["minutes"], held["tokens"], why))
    print("SET %s: %s" % (args.slug, ", ".join(
        "%s=%s" % (k, v) for k, v in sidecar(runs, args.slug).items())))
    return 0


def cmd_queue(g, args):
    g.valid(args)
    if any("|" in text for text in [args.goal, args.touches] + args.done):
        g.no("no | in a queue line.")
    path = os.path.join(g.root(), ".loop", "queue.md")
    held = g.read(path) if os.path.exists(path) else ""
    if os.path.exists(g.state_path(args.slug)) or "- slug: %s |" % args.slug in held:
        g.no("%s already exists. Fix: pick a new slug." % args.slug)
    parts = ["slug: " + args.slug]
    if args.touches:
        parts.append("touches: " + args.touches)
    if args.depends_on:
        parts.append("depends-on: " + args.depends_on)
    parts.append("goal: " + " ".join(args.goal.split()))
    parts += ["done: " + " ".join(line.split()) for line in args.done]
    g.write(path, ("" if held.endswith("\n") or not held else "\n") + "- " + " | ".join(parts) + "\n", "a")
    print("QUEUED %s in .loop/queue.md" % args.slug)
    return 0


def cmd_adopt(g, args):
    """Run record for a goal another machine pushed: idea to review done there; qa, ship and pr run here."""
    slug, branch = args.slug, "loop/" + args.slug
    old, note = g.state_path(slug), ""
    if not g.SLUG.match(slug):
        g.no("bad slug.")
    if os.path.exists(old):
        was = json.loads(g.read(old))
        if was.get("status") != "running" or was.get("pid") or was.get("flow"):
            g.no("%s has a live, started or finished run record here." % slug)
        g.SEEN[slug], note = json.dumps(was), "; replaced a stale record: running, no pid, no steps"
    if g.git("branch", "--show-current") != branch:
        g.no("not on %s. Fix: run this in its worktree." % branch)
    if g.run(["git", "fetch", "origin", branch]).returncode or g.run(["git", "merge-base", "--is-ancestor", "FETCH_HEAD", "HEAD"]).returncode:
        g.no("%s is not on origin, or this worktree lacks its commits. Fix: push, then fetch." % branch)
    sha, lines, text = g.git("rev-parse", "--short", "FETCH_HEAD"), g.done_lines(slug), g.read(g.goal_file(slug))
    seen = g.run(["gh", "pr", "view", branch, "--json", "url,state"])
    info = json.loads(seen.stdout) if seen.returncode == 0 else {}
    if not lines or info.get("state") != "OPEN":
        g.no("%s needs done lines and an open pull request." % slug)
    found = re.search(r"^- Touches: (.*)$", text, re.M)
    touches = [t.strip() for t in found.group(1).split(",") if t.strip() != "not declared"] if found else []
    args.goal = text.splitlines()[0].lstrip("# ")
    state = dict(slug=slug, goal=args.goal, status="running", step="qa", tries=0, branch=branch, worktree=g.root(), touches=touches,
                 pid=None, pr=info["url"], batch=False, done_sha=g.done_sha(lines), release="", waiting=None, finding="", log=[],
                 flow={s: "done on another machine: " + sha for s in g.FLOW[:3]}, **frozen_fields(g, args, lines, touches))
    g.guards.stamp(state, "qa")
    g.pods and g.pods.stamp(state)
    g.save(state, "adopted from origin/%s @ %s (%s)%s" % (branch, sha, info["url"], note))
    print("ADOPTED %s at qa from origin/%s @ %s%s; qa, ship and pr run here" % (slug, branch, sha, note))
    return 0


def keep(g, state, step, text):
    """What record keeps from a done, skipped or auto-approved reply: its verdicts (issue 38) and, for plan, the HEAD
    it was recorded at (resume_at tells build from review by commits after it)."""
    state.setdefault("verdicts", {})[step] = verdicts(text)
    if step == "plan":
        state["plan_head"] = g.git("rev-parse", "HEAD")


def nag(g, args):
    """The template-version line `new` prints (entry.py lag): it warns and never blocks, but a differing major refuses with exit 2
    and creates nothing (a migrate- slug passes)."""
    tool = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "workflow-docs", "scripts", "entry.py")
    if not os.path.exists(tool):
        return print("NOTE: entry.py not found beside workflow-delivery, so the template version was not checked. Fix: reinstall the skills from one release", file=sys.stderr)
    seen = g.run([sys.executable, tool, "lag", "--new", args.slug, "--repo", g.root()])
    sys.stdout.write(seen.stdout)
    sys.stderr.write(seen.stderr)
    seen.returncode == 3 and sys.exit(2)


def frozen_fields(g, args, lines, touches):
    """The goal's size and budget, recorded beside the done lines."""
    bad = [t for t in touches if surface(t) is None]
    if bad:
        g.no("%s isn't a GitHub surface. Fix: one of github:%s" % (", ".join(bad), ", github:".join(SURFACES)))
    if says_bump(args.goal):
        print("WARN: the goal text says %s; the operation records it with goal.py set %s --bump %s --why ..." % (
            says_bump(args.goal), args.slug, says_bump(args.goal)))
    return {"size": size_of(lines, touches, g.root()), "budget": budget_of(g.config())}


def pr_text(g, state):
    """The pull request body, after the private-name scan of the branch, the title and the body (DEL-9): a hit or a
    broken list refuses with no try, before anything is pushed."""
    import guards, private, role  # noqa: E401 - lazily: they import fit
    base, cfg = g.base_ref(state), g.config()
    body = pr_body(g.read(g.goal_file(state["slug"])), view(state, g.state_dir()), cfg, role.setting_of(cfg),
                          "", regen_warnings(g.root(), base))
    found = private.scan(g.root(), base, {"pr-title": state["goal"][:70], "pr-body": body})
    stop = private.refusal(found, base)
    if stop:
        guards.refuse_no_try(state, stop[0], stop[1], stop[2], g.save)
    if found["state"] == "none":
        state.setdefault("log", []).append("%s %s" % (guards.now(), found["note"]))
    return body.replace("\n## Result\n", "\n## Result\n\n" + found["note"] + "\n", 1)


# ---- the pull request body (was prbody.py)
VERDICT = re.compile(r"^\W*VERDICT:\s*(.+?)\s*$", re.M)


def verdicts(text):
    """The `VERDICT: <who>: <verdict>` lines of a step reply, at most 12."""
    return [" ".join(item.split())[:200] for item in VERDICT.findall(text or "")][:12]


def step_line(step, seen):
    flow = seen.get("flow") or {}
    tokens = (seen.get("tokens") or {}).get(step)
    line = "\n- %s: %s" % (step, flow.get(step, "not run"))
    if isinstance(tokens, int) and tokens:
        line += " (%s tokens)" % format(tokens, ",")
    for item in ((seen.get("verdicts") or {}).get(step) or []):
        line += "\n  - verdict: " + item
    return line


def regen_warnings(top, base):
    """For each deleted file, tracked scripts and workflows that name its path."""
    def git(*args):
        done = subprocess.run(["git"] + list(args), cwd=top, capture_output=True, text=True)
        return done.stdout if done.returncode == 0 else ""
    gone = [line for line in git("diff", "--name-only", "--diff-filter=D", "--no-renames", base + "...HEAD").splitlines() if line]
    scripts = [p for p in git("ls-files").splitlines() if p.endswith((".py", ".sh")) or p.startswith(".github/workflows/")]
    found = []
    for path in gone:
        named = git("grep", "-l", "-F", path, "--", *scripts).split() if scripts else []
        for script in named:
            found.append("WARN: %s names %s, which this goal deletes; it may write it back. Fix: update or delete %s in "
                         "this goal, or ask the operation session to widen touches" % (script, path, script))
    return found


def pr_body(goal_text, seen, cfg, setting, scan_note, warnings, base_note=""):
    """The pull request body; keeps `## Result` and the `Skill flow:` lines."""
    depth, why = depth_for(setting, seen)
    held, source = budget(seen, cfg)
    parts = ["%dm" % held["minutes"] if held["minutes"] else "", "%s tokens" % format(held["tokens"], ",") if held["tokens"] else ""]
    body = goal_text + "\n## Result\n\nSkill flow:" + "".join(step_line(step, seen) for step in STEPS) + "\n"
    body += seen.get("pr_lane", "")  # the lane's results (lanekit.record)
    body += "\nReview depth: %s (%s).\n" % (depth, why)
    body += "Budget: %s (%s); spent: %s.\n" % (", ".join(p for p in parts if p) or "none set", source, tokens_text(seen))
    body += scan_note + "\n"
    surfaces = [t for t in (seen.get("touches") or []) if t.startswith("github:")]
    if surfaces:
        body += "GitHub surfaces this goal changes: %s.\n" % ", ".join(surfaces)
    if base_note:
        body += base_note + "\n"
    if warnings:
        body += "\n" + "\n".join("- " + w for w in warnings) + "\n"
    return body


# ---- fixes without a defect test (was defect.py)
VERB = r"\b(?:fix(?:es|ed)?|close[sd]?|resolve[sd]?)\s+"
def off_rows(text):
    """REG-10: the UNPROVEN rows a lane failed on when each was also SKIPPED here and nothing else failed, else []."""
    bad, un = re.findall(r"^FAIL (\S+)", text, re.M), re.findall(r"^UNPROVEN ([^\s:]+)", text, re.M)
    return un if un and not bad and set(un) <= set(re.findall(r"^SKIPPED (\S+)", text, re.M)) else []


def off_line(text):
    return "\nLANE_OWED %s: skipped on this platform and never seen failing" % ", ".join(off_rows(text))


def off_reply(lane_line):
    """A step reply that waits for off-platform red proof (no failed try) when the lane line carries LANE_OWED, else ''."""
    m = re.search(r"^LANE_OWED (.+?):", lane_line, re.M)
    return m and ("%s\nPENDING: waiting for off-platform proof of %s. On a Linux or Mac runner run regression.py red ID --break "
                  "CMD for each, then here regression.py red ID --off-platform --runner NAME --commit SHA; then answer go on\nSTEP: pending\n"
                  % (lane_line, m.group(1))) or ""


SEEN = re.compile(r"\d{4}-\d{2}-\d{2}$")  # seen_red counts only as a date
FIXES = re.compile(VERB + r"(?:issue\s+)?#(\d+)|" + VERB + r"finding:([a-z0-9][a-z0-9-]*)", re.I)


def rows(root):
    """Defect rows as (id, command, seen_red, link)."""
    try:
        with open(os.path.join(root, ".loop", "regression.tsv")) as handle:
            cells = [line.rstrip("\n").split("\t") + [""] * 8 for line in handle if line.strip() and line[0] != "#"]
    except OSError:
        return []
    return [(c[0], c[2], c[4], c[7]) for c in cells if c[6] == "defect"]


def has(link, ref):
    return re.search(r"(?:issues/|#)%s\b" % re.escape(ref), link) if ref.isdigit() else re.search(r"finding:%s(?![\w-])" % re.escape(ref), link)


def before(root):
    """{row id: seen_red} at the merge-base with origin/<base>; None if none."""
    try:
        with open(os.path.join(root, ".loop", "config.json")) as handle:
            base = json.load(handle).get("base") or "main"
    except (OSError, ValueError):
        base = "main"
    git = lambda *a: subprocess.run(("git",) + a, cwd=root, capture_output=True, text=True, env=dict(os.environ, LC_ALL="C"))
    found = next((x for x in (git("merge-base", "HEAD", ref).stdout.strip() for ref in ("origin/" + base, base)) if x), "")
    shown = git("show", found + ":.loop/regression.tsv") if found else None
    if not shown or shown.returncode and "exists on disk" not in shown.stderr and "does not exist" not in shown.stderr:
        return None
    return {c[0]: (c + [""] * 5)[4] for c in (line.split("\t") for line in shown.stdout.splitlines()) if c[0][:1] not in ("", "#")}


def owed(root, text):
    """The refs the text fixes with no defect row proved on this branch (E-10)."""
    owe, old = [], before(root)
    for number, finding in FIXES.findall(text):
        ref = number or finding.lower()
        if not any(SEEN.match(seen) and has(link, ref) and (old is None or old.get(name) != seen)
                   and subprocess.run(command, shell=True, cwd=root, capture_output=True).returncode == 0
                   for name, command, seen, link in rows(root)):
            owe.append(("#" if number else "finding ") + ref)
    return owe


if __name__ == "__main__":
    import sys
    if len(sys.argv) == 3 and sys.argv[1] == "owed":
        top = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True).stdout.strip()
        try:
            with open(os.path.join(top, ".loop", "goals", sys.argv[2] + ".md")) as handle:
                left = owed(top, handle.read())
        except OSError:
            print("REFUSED: no goal file for %s on this branch. Fix: run it from the goal's worktree (NO_GOAL_FILE)" % sys.argv[2])
            sys.exit(2)
        print("\n".join("OWED %s: no defect test seen failing and passing" % ref for ref in left) or "NONE OWED")
        sys.exit(1 if left else 0)
    print("usage: fit.py owed SLUG   the issues and findings a goal fixes that still lack a defect test")
    sys.exit(0 if sys.argv[1:] in ([], ["-h"], ["--help"]) else 2)
