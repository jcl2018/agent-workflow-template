#!/usr/bin/env python3
"""The one status block: Needs you, Roadmap, Total, Goals, always in that order.

usage: board_status.py [--html]

Prints the block as text, or with --html as a fragment the dashboard and board-artifact.html embed. Report, board and
dashboard all print this same content. Roadmap is a dependency graph of the live goals (status_graph.py): running, queued and waiting goals with their
stage, 10-cell bar and time left, then one line of merged pull request numbers; a goal GitHub says is merged counts as
merged. Total is the longest chain of time left and its finish time, not the sum. Needs you comes first and is never hidden: every
waiting, failed or stopped worker, with the exact words to answer. Estimates come from the median of other runs' steps, read from their logs, and
read "no estimate yet" when there is none. Tokens read "unknown" until a run records them.
"""
import argparse
import datetime
import html
import json
import os
import re
import statistics
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import graph  # noqa: E402
import status_graph  # noqa: E402

STEPS = ("idea", "plan", "build", "review", "qa", "ship", "pr")
ASKING = ("waiting", "failed", "stopped")
TITLES = ("Needs you", "Roadmap", "Total", "Goals")

# No terminal, no waiting: a prompt from git or gh must fail, not block.
os.environ.update(GIT_TERMINAL_PROMPT="0", GH_PROMPT_DISABLED="1", GIT_EDITOR="true", GIT_ASKPASS="true", SSH_ASKPASS="true")


def git(*args, cwd=None):
    done = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    return done.stdout.strip() if done.returncode == 0 else ""


def read_json(path):
    try:
        with open(path) as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return None


def stamp(text):
    try:
        return datetime.datetime.fromisoformat(str(text).split(" ", 1)[0].replace("Z", "+00:00"))
    except ValueError:
        return None


span = status_graph.span


def tok(count):
    return "unknown" if count is None else "%dk" % round(count / 1000) if count >= 1000 else str(count)


def seconds_by_step(run, at):
    """Time each step took, from the gaps before its log entries, plus the gap since the last entry for the current step."""
    found, log = {}, run.get("log") or []
    for before, entry in zip(log, log[1:]):
        word = entry.split(" ", 2)[1] if entry.count(" ") else ""
        a, b = stamp(before), stamp(entry)
        if word in STEPS and a and b:
            found[word] = found.get(word, 0) + (b - a).total_seconds()
    last = stamp(log[-1]) if log else None
    if run.get("status") == "running" and run.get("step") in STEPS and last:
        found[run["step"]] = found.get(run["step"], 0) + max(0, (at - last).total_seconds())
    return found


def tokens_by_step(run):
    value = run.get("tokens")
    return {step: n for step, n in value.items() if step in STEPS and isinstance(n, int)} if isinstance(value, dict) else {}


def usual(runs, mine, step, pick):
    values = [pick(run).get(step) for run in runs if run["slug"] != mine["slug"] and run.get("status") == "done"]
    values = [v for v in values if v]
    return statistics.median(values) if values else None


def left_time(run, runs, at):
    """Seconds a goal still needs, from other runs' step medians: 0 when finished, None when no step has an estimate.
    A goal that has not started needs every step."""
    if run.get("status") == "done":
        return 0
    spent = seconds_by_step(run, at)
    here = -1 if run.get("status") == "queued" else STEPS.index(run["step"]) if run.get("step") in STEPS else 0
    left = [max(0, est - spent.get(step, 0)) if index == here else est
            for index, step in enumerate(STEPS) if index >= here
            for est in [usual(runs, run, step, lambda r: seconds_by_step(r, at))] if est]
    return sum(left) if left else None


def step_lines(run, runs, at):
    spent, used = seconds_by_step(run, at), tokens_by_step(run)
    here = STEPS.index(run["step"]) if run.get("step") in STEPS else 0
    lines, left = [], left_time(run, runs, at)
    for index, step in enumerate(STEPS):
        est_t = usual(runs, run, step, lambda r: seconds_by_step(r, at))
        est_k = usual(runs, run, step, tokens_by_step)
        done = "actual %s, %s tokens" % (span(spent[step]) if step in spent else "-", tok(used.get(step))) if index <= here else "actual -"
        lines.append("    %-6s est %s, %s tokens | %s" % (step, span(est_t) if est_t else "no estimate yet",
                                                         tok(round(est_k)) if est_k else "no estimate yet", done))
    lines.append("    remaining steps: " + ("est %s" % span(left) if left is not None else "no estimate yet"))
    return lines


def goal_lines(run, root):
    path = os.path.join(run.get("worktree") or root, ".loop", "goals", run["slug"] + ".md")
    try:
        with open(path) as handle:
            text = handle.read()
    except OSError:
        text = ""
    lines = re.findall(r"^(\d+)\. (.+)$", text.split("## Verify by hand")[0], re.M)
    met = {int(n) for n, _ in lines} if run.get("status") == "done" else set(run.get("met") or [])
    return ["- %s: %d of %d done lines met" % (run["slug"], len(met & {int(n) for n, _ in lines}), len(lines))] + \
        ["    [%s] %s. %s" % ("x" if int(n) in met else " ", n, line[:90]) for n, line in lines]


def queued(root, runs):
    """Queued goals, as queue.md lines parsed by graph.parse: the ones with no run record yet."""
    by_slug = {run["slug"] for run in runs}
    try:
        with open(os.path.join(root, ".loop", "queue.md")) as handle:
            return [item for item in map(graph.parse, handle.read().splitlines()) if item and item["slug"] not in by_slug]
    except OSError:
        return []


def github_merged(url, cwd):
    """True only when gh says the pull request is MERGED; any doubt (no gh, no answer, open, closed) is False."""
    try:
        done = subprocess.run(["gh", "pr", "view", url, "--json", "state"], cwd=cwd, capture_output=True, text=True, timeout=20)
        return done.returncode == 0 and json.loads(done.stdout).get("state", "").upper() == "MERGED"
    except (OSError, ValueError, AttributeError, subprocess.SubprocessError):
        return False


def merged_now(run, root):
    """Merged by the record, or done with a pull request that GitHub says is merged."""
    return graph.merged(run) or (run.get("status") == "done" and bool(run.get("pr")) and github_merged(run["pr"], root))


def pr_number(run):
    found = re.search(r"/pull/(\d+)", str(run.get("pr") or "")) or re.search(r"(\d+)\s*$", str(run.get("pr") or ""))
    return "#" + found.group(1) if found else "#" + run["slug"]


def sections(root=None, at=None):
    root = root or git("rev-parse", "--show-toplevel")
    at = at or datetime.datetime.now(datetime.timezone.utc)
    folder = os.path.join(os.path.abspath(os.path.join(root, git("rev-parse", "--git-common-dir", cwd=root))), "loop", "runs")
    runs = [read_json(os.path.join(folder, name)) for name in sorted(os.listdir(folder)) if name.endswith(".json")] if os.path.isdir(folder) else []
    runs = [run for run in runs if isinstance(run, dict) and run.get("slug") and run.get("status") != "retired"]
    needs, under = [], {}
    gone = {run["slug"] for run in runs if merged_now(run, root)}
    for run in runs:
        report = (run.get("report") or {}).get("text", "") or ((run.get("reports") or [{}])[-1].get("text", "") if run.get("status") == "running" else "")
        if run.get("wiki_error") and run["slug"] not in gone:
            needs.append("- %s (wiki not published): %s" % (run["slug"], " ".join(str(run["wiki_error"]).split())[:200]))
        if run.get("release_error") and run["slug"] not in gone:
            needs.append("- %s (release failed): %s" % (run["slug"], " ".join(str(run["release_error"]).split())[:200]))
        if run.get("status") in ASKING:
            ask = run.get("waiting") or {}
            words = ask.get("words") or ["resume " + run["slug"]]
            needs.append("- %s (%s): %s" % (run["slug"], run["status"], " ".join(str(ask.get("ask") or report or run.get("finding") or "see its log").split())[:200]))
            needs += ["    answer: " + w for w in words]
        elif run.get("status") == "running":
            under[run["slug"]] = ["    step %s%s" % (run.get("step") or "-", (" - " + report) if report else "")] + step_lines(run, runs, at)
        elif run.get("status") == "done" and run["slug"] not in gone:
            under[run["slug"]] = ["    waiting to merge: %s" % (report or "pull request %s" % (run.get("pr") or "open"))]
    items = [dict(slug=run["slug"], mark=status_graph.mark(run.get("status"), run["slug"] in gone), depends=[d for d in run.get("waits_on") or [] if d not in gone],
                  stage=STEPS.index(run["step"]) + 1 if run.get("step") in STEPS else 0, left=left_time(run, runs, at)) for run in runs]
    items += [dict(slug=goal["slug"], mark="queued", depends=[d for d in goal["depends"] if d not in gone], stage=0,
                   left=left_time({"slug": goal["slug"], "status": "queued"}, runs, at)) for goal in queued(root, runs)]
    live = [item for item in items if item["mark"] != "merged"]
    prs = sorted((pr_number(run) for run in runs if run["slug"] in gone), key=lambda n: (len(n), n))
    road = status_graph.render_text(live, under) + [status_graph.merged_line(prs)]
    goals = [line for run in runs for line in goal_lines(run, root)]
    return list(zip(TITLES, [needs or ["(nothing needs you)"], road,
                             [status_graph.total(live, at)], goals or ["(no goals)"]]))


def text(parts):
    return "\n".join("== %s ==\n%s\n" % (title, "\n".join(lines)) for title, lines in parts)


def fragment(parts):
    e = html.escape
    return "".join("<section%s><h2>%s</h2><pre>%s</pre></section>" % (" class=wait" if title == "Needs you" else "", e(title), e("\n".join(lines)))
                   for title, lines in parts)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--html", action="store_true")
    args = parser.parse_args()
    parts = sections()
    sys.stdout.write(fragment(parts) if args.html else text(parts))
    return 0


if __name__ == "__main__":
    sys.exit(main())
